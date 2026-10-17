import copy
from contextlib import ExitStack
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.parse import urlsplit,parse_qs

import run
from database import UserStore, UserIdentityProjectionStore, db_connect, atomic_runtime_transaction
from session_generation_store import SessionGenerationStore
from identity_gateway.config import load_config
from identity_gateway.store import initialize
from identity_gateway import service, providers
from test_ghostnetwork_suite_snapshot import valid_profile


class GatewayWebTests(unittest.TestCase):
    def test_smtp_rate_limit_returns_retry_after_without_secrets(self):
        self.authenticate('admin')
        from identity_gateway.store import digest
        import time
        with db_connect(self.path) as conn:
            user_id=service.account(conn,'admin')[0]
            conn.execute('INSERT OR REPLACE INTO identity_rate_limits VALUES (?,?,?)',
                         (digest('mail-test:'+str(user_id)),int(time.time()),5))
        result=self.post('/api/admin/identity/mail/test',{'recipient':'test@example.test'})
        self.assertEqual(result.status_code,429)
        self.assertEqual(result.json['error'],'rate_limited')
        self.assertTrue(0<int(result.headers['Retry-After'])<=3600)
        self.assertEqual(result.json['retry_after_seconds'],int(result.headers['Retry-After']))
        self.assertNotIn('password',result.json)

    def test_account_can_embed_same_origin_only(self):
        self.authenticate()
        result=self.client.get('/account/identity?embedded=1')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.headers['X-Frame-Options'],'SAMEORIGIN')
        self.assertIn('no-store',result.headers['Cache-Control'])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        self.path=str(Path(self.tmp.name)/'game.sqlite3')
        self.users=UserStore(self.path, seed_path=str(Path(self.tmp.name)/'no-seed.json'))
        self.sessions=SessionGenerationStore(self.path)
        for name in ('admin','alice','bob'):
            profile=valid_profile(name)
            profile.update(nick=name,email=name+'@example.test',password='Secret123')
            self.users.save_profile(profile)
        with db_connect(self.path) as conn:
            initialize(conn)
        self.stack.enter_context(patch.object(run,'user_store',self.users))
        self.stack.enter_context(patch.object(run,'authenticate_user',side_effect=self.users.authenticate))
        self.stack.enter_context(patch.object(run,'session_generation_store',self.sessions))
        self.stack.enter_context(patch.object(run,'identity_projection_store',UserIdentityProjectionStore(self.path)))
        env={'CHAOS_IDENTITY_ENABLED':'1','CHAOS_IDENTITY_PUBLIC_ORIGIN':'http://localhost',
             'CHAOS_IDENTITY_REGISTRATION_ENABLED':'1','CHAOS_IDENTITY_LINKING_ENABLED':'1','CHAOS_IDENTITY_MAIL_MODE':'mock'}
        for provider in ('GOOGLE','GITHUB','DISCORD','STEAM'):
            env.update({f'CHAOS_IDENTITY_{provider}_ENABLED':'1',f'CHAOS_IDENTITY_{provider}_CLIENT_ID':'client',
                        f'CHAOS_IDENTITY_{provider}_CLIENT_SECRET':'secret'})
        self.config=load_config(env,testing=True)
        self.stack.enter_context(patch.dict(run.app.config,TESTING=True,IDENTITY_TEST_CONFIG=self.config,
                                          IDENTITY_TEST_OUTBOX=[],CHAOS_LAUNCH_CONTROLLER_ENABLED=False))
        template=valid_profile('template')
        resources=Mock()
        resources.get.return_value=template
        self.stack.enter_context(patch.object(run,'resources_store',resources))
        self.stack.enter_context(patch.object(run,'get_start_location_by_ip',return_value={'lat':52.2,'lng':21.0,'city':'test'}))
        self.stack.enter_context(patch.object(run,'resolve_first_respawn_outside_controlled_territory',return_value={'position':{'lat':52.2,'lng':21.0}}))
        self.client=run.app.test_client()

    def authenticate(self,name='alice'):
        with run.app.test_request_context('/'):
            run.begin_authenticated_session(name)
            values=dict(run.session)
        with self.client.session_transaction() as sess:
            sess.clear()
            sess.update(values)

    def post(self,path,data):
        with self.client.session_transaction() as sess:
            csrf=sess.get('session_csrf') or sess.get('identity_csrf','')
            generation=sess.get(run.SESSION_GENERATION_KEY,'')
        return self.client.post(path,json=data,headers={'Origin':'http://localhost','X-Chaos-CSRF':csrf,
                                                       'X-Chaos-Session-Generation':generation})

    def grant(self,action):
        result=self.post('/api/account/reauth',{'action':action,'password':'Secret123'})
        self.assertEqual(result.status_code,200,result.json)
        return result.json['grant']

    def start(self,provider='google',subject='new',email='new@example.test',verified=True):
        response=self.client.get('/auth/'+provider+'?locale=en')
        self.assertEqual(response.status_code,302)
        query=parse_qs(urlsplit(response.location).query)
        state=query.get('state') or parse_qs(urlsplit(query['openid.return_to'][0]).query)['state']
        with patch.object(providers,'resolve',return_value=dict(provider=provider,subject=subject,email=email,email_verified=verified)):
            result=self.client.get('/auth/'+provider+'/callback',query_string={'state':state[0],'code':'test'})
        return result,state[0]

    def test_four_provider_registration_login_same_account_and_replay(self):
        for index,provider in enumerate(('google','github','discord','steam')):
            self.client=run.app.test_client()
            email=f'new{index}@example.test'
            response,state=self.start(provider,email=email)
            self.assertEqual(response.location,'/auth/register')
            page=self.client.get(response.location)
            self.assertEqual(page.status_code,200)
            self.assertIn(b'data-setup-step="1"',page.data)
            self.assertIn(b'faction-3.png',page.data)
            self.assertNotIn(b'<select name="faction"',page.data)
            data=dict(nick=f'new{index}',email=email,faction='3',role='2',terms='157-v1')
            result=self.post('/auth/complete-registration',data)
            self.assertEqual(result.status_code,200,result.json)
            with self.client.session_transaction() as sess:
                username=sess['user']
            profile=self.users.get_profile(username)
            self.assertEqual(profile['nick'],data['nick'])
            self.assertEqual(profile['hackcoins'],1000)
            self.assertEqual(profile['desktop_settings']['locale'],'en')
            self.assertFalse(self.users.authenticate(username,''))
            self.client=run.app.test_client()
            response,_=self.start(provider,email=email)
            self.assertEqual(response.status_code,302)
            with self.client.session_transaction() as sess:
                self.assertEqual(sess['user'],username)
            replay=self.client.get('/auth/'+provider+'/callback',query_string={'state':state,'code':'test'})
            self.assertEqual(replay.status_code,400)

    def test_unverified_email_requires_code_no_account_until_complete(self):
        response,_=self.start('steam',verified=False)
        self.client.get(response.location)
        data=dict(nick='new',email='new@example.test',faction='3',role='1',terms='157-v1')
        result=self.post('/auth/complete-registration',data)
        self.assertEqual(result.json['error'],'email_verification_required')
        self.assertEqual(self.post('/auth/register/email',{'email':data['email']}).status_code,200)
        code=run.app.config['IDENTITY_TEST_OUTBOX'][-1]['code']
        confirmed=self.post('/auth/register/email',{'email':data['email'],'code':code})
        self.assertEqual(confirmed.status_code,200)
        self.assertEqual(confirmed.json['verified_email'],data['email'])
        self.assertEqual(self.post('/auth/complete-registration',data).status_code,200)

    def test_mail_settings_admin_only_encrypted_and_preserved(self):
        self.authenticate('bob')
        self.assertEqual(self.client.get('/api/admin/identity').status_code,403)
        self.authenticate('admin')
        data=dict(mode='smtp',host='smtp.example.test',sender='chaos@example.test',port=587,tls='starttls',
                  username='mailer',password='mail-password',grant=self.grant('mail_settings'))
        result=self.post('/api/admin/identity/mail',data)
        self.assertEqual(result.status_code,200,result.json)
        self.assertNotIn('mail-password',result.get_data(as_text=True))
        with db_connect(self.path) as conn:
            raw=conn.execute('SELECT password_ciphertext FROM identity_mail_settings').fetchone()[0]
            self.assertNotIn('mail-password',raw)
        data.update(password='',grant=self.grant('mail_settings'))
        self.assertTrue(self.post('/api/admin/identity/mail',data).json['mail']['password_configured'])
        self.assertEqual(self.post('/api/admin/identity/mail',data).json['error'],'reauth_required')

    def test_csrf_grants_and_last_method(self):
        self.authenticate()
        self.assertEqual(self.client.post('/api/account/reauth',json={'password':'Secret123'}).json['error'],'csrf_rejected')
        with atomic_runtime_transaction(self.path,foreign_keys=True) as conn:
            user_id=service.account(conn,'alice')[0]
            service.link(conn,user_id,dict(provider='google',subject='alice'))
            conn.execute('UPDATE identity_account_security SET local_password_enabled=0 WHERE user_id=?',(user_id,))
            with self.assertRaises(service.IdentityError):
                service.unlink(conn,user_id,'google')

    def test_failed_link_rolls_back_full_registration(self):
        response,_=self.start()
        self.client.get(response.location)
        before=len(self.users.list_profiles())
        with patch.object(service,'link',side_effect=service.IdentityError('identity_collision')):
            result=self.post('/auth/complete-registration',dict(nick='new',email='new@example.test',faction='3',role='1',terms='157-v1'))
        self.assertEqual(result.status_code,400)
        self.assertEqual(len(self.users.list_profiles()),before)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM identity_tickets').fetchone()[0],1)

    def test_email_collision_does_not_link_existing_account(self):
        response,_=self.start(email='alice@example.test')
        self.client.get(response.location)
        result=self.post('/auth/complete-registration',dict(nick='new',email='alice@example.test',faction='3',role='1',terms='157-v1'))
        self.assertEqual(result.json['error'],'identity_collision')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM user_identities').fetchone()[0],0)

    def test_link_unlink_and_stale_callback_generation(self):
        self.authenticate()
        result=self.post('/api/account/identities/github/link',{'grant':self.grant('link')})
        self.assertEqual(result.status_code,200,result.json)
        state=parse_qs(urlsplit(result.json['redirect']).query)['state'][0]
        with patch.object(providers,'resolve',return_value=dict(provider='github',subject='linked',email=None,email_verified=False)):
            result=self.client.get('/auth/github/callback',query_string={'state':state,'code':'test'})
        self.assertEqual(result.status_code,302)
        self.assertEqual(len(self.client.get('/api/account/identities').json['identities']),1)
        result=self.post('/api/account/identities/github/unlink',{'grant':self.grant('unlink')})
        self.assertEqual(result.status_code,200,result.json)
        result=self.post('/api/account/identities/google/link',{'grant':self.grant('link')})
        state=parse_qs(urlsplit(result.json['redirect']).query)['state'][0]
        self.authenticate('bob')
        with patch.object(providers,'resolve') as resolve:
            result=self.client.get('/auth/google/callback',query_string={'state':state,'code':'test'})
            resolve.assert_not_called()
        self.assertEqual(result.status_code,400)

    def test_password_revokes_session_and_keeps_profile(self):
        self.authenticate()
        before=self.users.get_profile('alice')
        result=self.post('/api/account/password',{'password':'Changed123','confirm':'Changed123','grant':self.grant('password')})
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(self.users.authenticate('alice','Changed123'))
        self.assertFalse(self.users.authenticate('alice','Secret123'))
        self.assertEqual(self.users.get_profile('alice')['hackcoins'],before['hackcoins'])
        with self.client.session_transaction() as sess:self.assertNotIn('user',sess)

    def test_verify_email_then_reauth_code_and_guess_limit(self):
        self.authenticate()
        result=self.post('/api/account/email',{'email':'newalice@example.test','grant':self.grant('email')})
        self.assertEqual(result.status_code,200,result.json)
        code=run.app.config['IDENTITY_TEST_OUTBOX'][-1]['code']
        result=self.post('/api/account/email',{'code':code})
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.client.get('/api/account/identities').json['verified_email'],'newalice@example.test')
        self.assertEqual(self.post('/api/account/reauth',{'action':'link'}).status_code,200)
        code=run.app.config['IDENTITY_TEST_OUTBOX'][-1]['code']
        wrong='00000000' if code!='00000000' else '11111111'
        for _ in range(5):self.assertEqual(self.post('/api/account/reauth',{'action':'link','code':wrong}).json['error'],'invalid_code')
        self.assertEqual(self.post('/api/account/reauth',{'action':'link','code':code}).json['error'],'invalid_code')

    def test_delete_retires_provider_without_removing_other_profile(self):
        self.authenticate()
        with atomic_runtime_transaction(self.path,foreign_keys=True) as conn:
            user_id=service.account(conn,'alice')[0]
            service.link(conn,user_id,dict(provider='google',subject='deleted'))
            conn.execute("""INSERT INTO chat_messages(owner_username,scope,peer_name,sender,body,created_at)
                VALUES ('bob','private','alice','alice','preserve-peer-copy','2026-10-16')""")
        before=self.users.get_profile('bob')
        result=self.post('/api/account/delete',{'username':'alice','confirm':'alice','grant':self.grant('delete')})
        self.assertEqual(result.status_code,200,result.json)
        self.assertFalse(self.users.has_user('alice'))
        self.assertEqual(self.users.get_profile('bob'),before)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT body FROM chat_messages WHERE owner_username='bob'").fetchone()[0],'preserve-peer-copy')
        response,_=self.start(subject='deleted')
        self.assertEqual(response.status_code,400)

    def test_registration_disabled_existing_provider_still_logs_in(self):
        with atomic_runtime_transaction(self.path,foreign_keys=True) as conn:
            service.link(conn,service.account(conn,'alice')[0],dict(provider='google',subject='existing'))
        run.app.config['IDENTITY_TEST_CONFIG']=replace(self.config,registration_enabled=False)
        response,_=self.start(subject='existing')
        self.assertEqual(response.status_code,302)
        with self.client.session_transaction() as sess:self.assertEqual(sess['user'],'alice')

    def test_link_callback_does_not_extend_reauth_deadline(self):
        self.authenticate()
        result=self.post('/api/account/identities/google/link',{'grant':self.grant('link')})
        state=parse_qs(urlsplit(result.json['redirect']).query)['state'][0]
        from identity_gateway.store import digest
        with db_connect(self.path) as conn:
            row=conn.execute('SELECT data_json FROM identity_flow_data WHERE token_hash=?',(digest(state),)).fetchone()
            flow=json.loads(row[0]);flow['reauth_expires']=1
            conn.execute('UPDATE identity_flow_data SET data_json=? WHERE token_hash=?',(json.dumps(flow),digest(state)))
        with patch.object(providers,'resolve') as resolve:
            result=self.client.get('/auth/google/callback',query_string={'state':state,'code':'test'})
            resolve.assert_not_called()
        self.assertEqual(result.status_code,400)

    def test_enabled_local_registration_is_atomic_and_email_login_verified_only(self):
        result=self.client.post('/api/register-finalize',json=dict(username='localnew',password='Secret123',
            faction='3',role='1',nick='Local new',email='localnew@example.test',locale='en'))
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(self.users.authenticate('localnew','Secret123'))
        self.client=run.app.test_client()
        result=self.client.post('/',data={'username':'localnew@example.test','password':'Secret123'})
        with self.client.session_transaction() as sess:self.assertNotIn('user',sess)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE identity_account_security SET verified_email='localnew@example.test',email_verified_at=1 WHERE user_id=(SELECT id FROM users WHERE username='localnew')")
        result=self.client.post('/',data={'username':'localnew@example.test','password':'Secret123'})
        self.assertEqual(result.status_code,302)
        with self.client.session_transaction() as sess:self.assertEqual(sess['user'],'localnew')
