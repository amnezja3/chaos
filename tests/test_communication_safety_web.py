from unittest.mock import patch
import run
from database import db_connect, MailStore
import communication_safety as safety
import test_identity_gateway_web as gateway


class SafetyWebTests(gateway.GatewayWebTests):
    def setUp(self):
        super().setUp()
        self.stack.enter_context(patch.dict(run.app.config,CHAOS_COMMUNICATION_SAFETY_ENABLED=True,CHAOS_AGE_POLICY_ENABLED=False))
        self.mail=MailStore(self.path)
        self.stack.enter_context(patch.object(run,'mail_store',self.mail))
        with db_connect(self.path) as conn:
            safety.initialize(conn)
        self.authenticate()

    def test_invitation_acceptance_block_and_unblock_http(self):
        self.assertEqual(self.post('/api/safety/invite',{'username':'bob'}).status_code,200)
        self.authenticate('bob')
        result=self.client.get('/api/safety')
        self.assertEqual(result.json['invites'][0]['username'],'alice')
        self.assertEqual(self.post('/api/safety/invite/answer',{'username':'alice','accept':True}).status_code,200)
        self.assertEqual(self.post('/api/safety/block',{'username':'alice','blocked':True}).status_code,200)
        self.assertEqual(self.client.get('/api/safety').json['blocks'],['alice'])
        self.assertEqual(self.post('/api/safety/block',{'username':'alice','blocked':False}).status_code,200)
        self.assertFalse(self.mail.is_accepted_contact('alice','bob'))

    def test_csrf_stale_and_moderator_authorization(self):
        self.assertEqual(self.client.post('/api/safety/block',json={'username':'bob','blocked':True}).status_code,403)
        self.assertEqual(self.client.get('/api/safety/moderation').status_code,403)
        self.assertEqual(self.post('/api/safety/moderation',{'id':1,'action':'hide','reason':'reason'}).status_code,403)

    def test_report_decision_appeal_and_private_reporter(self):
        result=self.post('/api/safety/report',{'kind':'profile','key':'bob','category':'harassment','details':'Repeated contact'})
        self.assertEqual(result.status_code,200,result.json)
        report_id=result.json['id']
        self.authenticate('admin')
        result=self.post('/api/safety/moderation',{'id':report_id,'action':'restrict','reason':'Reviewed conduct','hours':1})
        self.assertEqual(result.status_code,200,result.json)
        self.authenticate('bob')
        rows=self.client.get('/api/safety').json['reports']
        self.assertEqual(len(rows),1)
        self.assertNotIn('reporter_id',rows[0])
        self.assertNotIn('details',rows[0])
        self.assertEqual(self.post('/api/safety/appeal',{'id':report_id,'reason':'Please review'}).status_code,200)

    def test_safety_page_bilingual_and_private(self):
        result=self.client.get('/account/safety')
        self.assertEqual(result.status_code,200)
        self.assertIn(b'communication_safety.js',result.data)
        self.assertNotIn(b'id="moderation"',result.data)
        self.authenticate('admin')
        self.assertIn(b'id="moderation"',self.client.get('/account/safety').data)

    def test_unreadable_message_not_reportable_and_schema_failure_closed(self):
        self.assertEqual(self.post('/api/safety/report',{'kind':'message','key':'private','scope':'clan','peer':'clan:other','category':'privacy'}).status_code,400)
        with db_connect(self.path) as conn:
            conn.execute('DROP TABLE communication_blocks')
        self.assertEqual(self.client.get('/api/safety').status_code,503)

    def test_real_message_writer_checks_permission_inside_transaction(self):
        route={'channel':'direct','scope':'direct','peer':'bob','channel_key':'direct:bob'}
        profile=self.users.get_profile('alice')
        with run.app.test_request_context('/'), patch.object(run.detention_service,'db_path',self.path), patch('response_network.chat_delivery.snapshot',return_value=None):
            with self.assertRaisesRegex(ValueError,'contact_unavailable'):
                run.cyberner_store_message('alice',profile,route,'not accepted',client_message_id='a')
            with db_connect(self.path) as conn:
                safety.invite(conn,'alice','bob')
                safety.answer_invite(conn,safety.uid(conn,'bob'),'alice',True)
            message,created=run.cyberner_store_message('alice',profile,route,'accepted',client_message_id='b')
            self.assertTrue(created)
            self.assertEqual(message['body'],'accepted')
            with db_connect(self.path) as conn:
                safety.set_block(conn,safety.uid(conn,'bob'),'alice',True)
            with self.assertRaisesRegex(ValueError,'contact_unavailable'):
                run.cyberner_store_message('alice',profile,route,'blocked',client_message_id='c')
            with db_connect(self.path) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM chat_messages WHERE body='blocked'").fetchone()[0],0)

    def test_replayed_communication_filter_preserves_pvp_payload(self):
        with db_connect(self.path) as conn:
            safety.set_block(conn,safety.uid(conn,'alice'),'bob',True)
        with run.app.test_request_context('/api/state/changes'):
            run.session['user']='alice'
            from flask import jsonify
            handler=next(f for f in run.app.after_request_funcs[None] if f.__name__=='filter_delivery')
            result=handler(jsonify(events=[
                {'scope':'territory','type':'conflict.updated','payload':{'sender':'bob','body':'battle'}},
                {'scope':'mail','type':'cyberner.message_created','payload':{'message':{'sender':'bob','body':'private'}}}]))
            self.assertEqual(result.json['events'][0]['payload'],{'sender':'bob','body':'battle'})
            self.assertNotIn('private',result.get_data(as_text=True))

    def test_migration_dry_run_apply_idempotence_preserve_baseline(self):
        from tools import identity_157_migrate as migration
        from tools.safety_157_8_migrate import initialize
        from tools.ghost_content_155_migrate import snapshot
        with db_connect(self.path) as conn:
            before=snapshot(conn)
        with patch.object(migration,'initialize',initialize):
            self.assertEqual(migration.migrate(self.path)['status'],'dry_run')
            self.assertTrue(migration.migrate(self.path,apply=True)['original_data_unchanged'])
            self.assertEqual(migration.migrate(self.path,apply=True)['status'],'already_migrated')
        with db_connect(self.path) as conn:
            self.assertEqual(snapshot(conn,before),before)


for name in gateway.GatewayWebTests.__dict__:
    if name.startswith('test_') and name not in SafetyWebTests.__dict__:
        setattr(SafetyWebTests,name,None)
