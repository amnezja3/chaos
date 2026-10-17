import copy
import sqlite3
from unittest.mock import patch
import run
from database import db_connect
from identity_gateway import adult_policy, service
import test_identity_gateway_web as gateway_tests


class AdultPolicyTests(gateway_tests.GatewayWebTests):
    # Inherit fixture helpers, not the legacy-policy tests.
    def setUp(self):
        super().setUp()
        self.stack.enter_context(patch.dict(run.app.config, CHAOS_ADULT_POLICY_ENABLED=True))

    def agreement(self):
        return dict(age_confirmed=True, age_statement_version=adult_policy.AGE_VERSION,
                    terms=adult_policy.TERMS_VERSION)

    def local(self):
        return dict(username='adultnew',password='Secret123',faction='3',role='1',
                    nick='Adult new',email='adult@example.test',locale='en',**self.agreement())

    def test_local_requires_both_strict_declarations_and_saves_atomically(self):
        data=self.local()
        for field, invalid in [('age_confirmed',False),('age_confirmed','true'),('age_confirmed',1),
                               ('age_statement_version','old'),('terms','157-v1'),('terms',None)]:
            candidate={**data,field:invalid}
            result=self.client.post('/api/register-finalize',json=candidate)
            self.assertEqual(result.status_code,400,result.json)
            self.assertFalse(self.users.has_user('adultnew'))
        with patch.object(adult_policy,'record',side_effect=ValueError('rollback')):
            self.assertEqual(self.client.post('/api/register-finalize',json=data).status_code,400)
        self.assertFalse(self.users.has_user('adultnew'))
        result=self.client.post('/api/register-finalize',json=data)
        self.assertEqual(result.status_code,200,result.json)
        with db_connect(self.path) as conn:
            row=conn.execute('SELECT age_confirmed,age_statement_version,accepted_at FROM identity_consents').fetchone()
            self.assertEqual(tuple(row[:2]),(1,adult_policy.AGE_VERSION))
            self.assertGreater(row[2],0)

    def test_each_provider_requires_explicit_age_and_terms(self):
        for provider in ('google','github','discord','steam'):
            self.client=run.app.test_client()
            email=provider+'@example.test'
            result,_=self.start(provider,email=email)
            self.client.get(result.location)
            data=dict(nick=provider,email=email,faction='3',role='1',**self.agreement())
            before=len(self.users.list_profiles())
            for field,value in [('age_confirmed',False),('age_confirmed','on'),('age_confirmed',None),
                                 ('terms',None),('terms','157-v1'),('age_statement_version',None)]:
                denied=self.post('/auth/complete-registration',{**data,field:value})
                self.assertEqual(denied.status_code,400,denied.json)
                self.assertEqual(len(self.users.list_profiles()),before)
            self.assertEqual(self.post('/auth/complete-registration',data).status_code,200)

    def test_existing_account_old_terms_and_warm_session_gate_every_gameplay_entry(self):
        self.authenticate()
        original=copy.deepcopy(self.users.get_profile('alice'))
        with db_connect(self.path) as conn:
            uid=service.account(conn,'alice')[0]
            conn.execute('INSERT INTO identity_consents(user_id,terms_version,accepted_at) VALUES (?, ?,1)',(uid,'157-v1'))
        for url in ('/launch','/desktop','/map','/dev'):
            result=self.client.get(url)
            self.assertEqual(result.status_code,302,url)
            self.assertEqual(result.location,'/account/terms')
        for method,url in [('get','/api/profile'),('get','/api/session/status'),('post','/api/session/bootstrap'),
                           ('get','/api/desktop-shell'),('post','/command'),('get','/api/state/changes')]:
            result=getattr(self.client,method)(url,json={} if method=='post' else None)
            self.assertEqual(result.status_code,403,url)
            self.assertEqual(result.json['error'],'adult_acceptance_required')
        for url in ('/account/terms','/account/identity','/privacy?locale=en','/terms?locale=pl'):
            self.assertEqual(self.client.get(url).status_code,200,url)
        self.assertEqual(self.post('/api/account/terms',{}).status_code,400)
        self.assertEqual(self.post('/api/account/terms/decline',{}).status_code,200)
        self.assertEqual(self.users.get_profile('alice'),original)
        self.assertEqual(self.client.get('/api/profile').status_code,403)
        self.assertEqual(self.post('/api/account/terms',self.agreement()).status_code,200)
        self.assertEqual(self.post('/api/account/terms',self.agreement()).status_code,200)
        with db_connect(self.path) as conn:
            self.assertEqual(adult_policy.state(conn,'alice'),'')
            self.assertEqual(conn.execute('SELECT count(*) FROM identity_consents WHERE user_id=?',(uid,)).fetchone()[0],2)
        # Accepted user now reaches the underlying view (without booting the world).
        with patch.dict(run.app.view_functions,launch=lambda:'accepted'):
            self.assertEqual(self.client.get('/launch').data,b'accepted')
        self.authenticate()
        with patch.dict(run.app.view_functions,launch=lambda:'accepted'):
            self.assertEqual(self.client.get('/launch').data,b'accepted')

    def test_stale_second_device_cannot_accept(self):
        self.authenticate()
        old=self.client
        self.client=run.app.test_client()
        self.authenticate()
        current=self.client
        self.client=old
        self.assertNotEqual(self.post('/api/account/terms',self.agreement()).status_code,200)
        self.client=current
        self.assertEqual(self.post('/api/account/terms',self.agreement()).status_code,200)

    def test_underage_remains_restricted_and_can_delete(self):
        self.authenticate()
        self.assertEqual(self.post('/api/account/terms/decline',{'underage':True}).status_code,200)
        result=self.post('/api/account/terms',self.agreement())
        self.assertEqual(result.json['error'],'age_restricted')
        self.assertEqual(self.client.get('/api/profile').json['error'],'age_restricted')
        result=self.post('/api/account/delete',{'username':'alice','confirm':'alice','grant':self.grant('delete')})
        self.assertEqual(result.status_code,200,result.json)
        self.assertFalse(self.users.has_user('alice'))
        self.assertTrue(self.users.has_user('bob'))

    def test_csrf_required_and_logout_without_consent(self):
        self.authenticate()
        self.assertEqual(self.client.post('/api/account/terms',json=self.agreement()).json['error'],'csrf_rejected')
        self.assertEqual(self.post('/logout',{}).status_code,200)
        with self.client.session_transaction() as sess:
            self.assertNotIn('user',sess)

    def test_missing_schema_fails_closed(self):
        self.authenticate()
        with db_connect(self.path) as conn:
            conn.execute('ALTER TABLE identity_consents RENAME TO missing_consents')
        self.assertEqual(self.client.get('/api/profile').status_code,503)

    def test_migration_preserves_old_consent_profiles_and_is_idempotent(self):
        from tools.identity_157_migrate import migrate, check
        from tools.ghost_content_155_migrate import snapshot
        with db_connect(self.path) as conn:
            uid=service.account(conn,'alice')[0]
            conn.execute('INSERT INTO identity_consents(user_id,terms_version,accepted_at) VALUES (?, ?,123)',(uid,'157-v1'))
            conn.execute('ALTER TABLE identity_consents DROP COLUMN age_confirmed')
            conn.execute('ALTER TABLE identity_consents DROP COLUMN age_statement_version')
            conn.execute('ALTER TABLE identity_account_security DROP COLUMN age_restricted')
        with db_connect(self.path) as conn:
            before=snapshot(conn)
        self.assertEqual(migrate(self.path)['status'],'dry_run')
        with db_connect(self.path) as conn:
            self.assertNotIn('age_confirmed',{r[1] for r in conn.execute('PRAGMA table_info(identity_consents)')})
        self.assertEqual(migrate(self.path,True)['status'],'migrated')
        self.assertEqual(migrate(self.path,True)['status'],'already_migrated')
        self.assertTrue(check(self.path)['ok'])
        with db_connect(self.path) as conn:
            self.assertEqual(snapshot(conn,before),before)
            self.assertEqual(adult_policy.state(conn,'alice'),'adult_acceptance_required')

    def test_operator_restriction_and_release_never_create_agreement(self):
        from tools.identity_18_access import change
        change(self.path,'alice',True)
        self.authenticate()
        self.assertEqual(self.client.get('/api/profile').json['error'],'age_restricted')
        change(self.path,'alice',False)
        self.assertEqual(self.client.get('/api/profile').json['error'],'adult_acceptance_required')

    def test_age_page_and_public_documents_bilingual_even_when_identity_disabled(self):
        from dataclasses import replace
        self.authenticate()
        with patch.dict(run.app.config,IDENTITY_TEST_CONFIG=replace(self.config,enabled=False)):
            for lang in ('pl','en'):
                with self.client.session_transaction() as sess:
                    sess['identity_locale']=lang
                page=self.client.get('/account/terms')
                self.assertEqual(page.status_code,200)
                html=page.get_data(as_text=True)
                self.assertIn('name="age_confirmed"',html)
                self.assertNotIn(' checked',html)
                for path in ('/privacy','/terms'):
                    response=self.client.get(path+'?locale='+lang)
                    self.assertEqual(response.status_code,200)
                    self.assertIn('18',response.get_data(as_text=True))
                    self.assertNotIn('13+',response.get_data(as_text=True))

    def test_existing_local_and_provider_login_do_not_grant_gameplay(self):
        from database import atomic_runtime_transaction
        result=self.client.post('/',data={'username':'alice','password':'Secret123'})
        self.assertEqual(result.status_code,302)
        self.assertEqual(self.client.get(result.location).location,'/account/terms')
        with atomic_runtime_transaction(self.path,foreign_keys=True) as conn:
            uid=service.account(conn,'alice')[0]
            service.link(conn,uid,dict(provider='google',subject='existing-adult',email='alice@example.test',email_verified=True))
        self.client=run.app.test_client()
        result,_=self.start('google',subject='existing-adult',email='alice@example.test')
        self.assertEqual(result.status_code,302)
        self.assertEqual(self.client.get(result.location).location,'/account/terms')
        self.assertEqual(self.post('/api/account/terms',self.agreement()).status_code,200)
        self.client=run.app.test_client()
        self.start('google',subject='existing-adult',email='alice@example.test')
        with patch.dict(run.app.view_functions,launch=lambda:'accepted'):
            self.assertEqual(self.client.get('/launch').data,b'accepted')


# Do not rerun inherited tests which intentionally post the legacy 157-v1 contract.
for name in list(gateway_tests.GatewayWebTests.__dict__):
    if name.startswith('test_') and name not in AdultPolicyTests.__dict__:
        setattr(AdultPolicyTests,name,None)
