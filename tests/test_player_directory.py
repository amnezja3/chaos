import unittest
from unittest.mock import patch
import run
from database import db_connect, MailStore
import communication_safety as safety
import test_identity_gateway_web as gateway
from test_ghostnetwork_suite_snapshot import valid_profile


class PlayerDirectoryTests(unittest.TestCase):
    setUp=gateway.GatewayWebTests.setUp
    authenticate=gateway.GatewayWebTests.authenticate
    post=gateway.GatewayWebTests.post

    def search(self,query):
        with self.client.session_transaction() as sess:generation=sess.get(run.SESSION_GENERATION_KEY,'')
        return self.client.get('/api/players/search',query_string={'q':query},headers={'X-Chaos-Session-Generation':generation})

    def seed(self,username,nick):
        profile=valid_profile(username)
        profile.update(nick=nick,email=username+'@private.example.test',password='')
        self.users.save_profile(profile)

    def test_all_gateway_accounts_search_by_nick_and_handle_without_private_data(self):
        self.authenticate()
        for provider in ('google','discord','steam','github'):
            username='id_'+provider+'_fixture'
            self.seed(username,'Żółw '+provider)
            response=self.search('ŻÓŁW '+provider)
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['players'],[dict(username=username,nick='Żółw '+provider,handle='@'+username)])
            by_handle=self.search('@'+username)
            self.assertEqual(by_handle.json['players'],response.json['players'])
            self.assertNotIn('private@',response.text)
            self.assertEqual(run.identity_projection_store.resolve_player('@'+username),username)

    def test_ambiguity_rename_literal_wildcards_and_bounds(self):
        self.seed('id_one','Neo');self.seed('id_two','NEO')
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            run.identity_projection_store.resolve_player('neo')
        self.assertEqual(run.identity_projection_store.resolve_player('@id_one'),'id_one')
        row=self.users.get_profile_with_revision('id_one')
        self.users.patch_profile_guarded('id_one',{'nick':'Trinity'},expected_revision=row['profile_revision'],source='test.rename')
        self.assertEqual(run.identity_projection_store.resolve_player('TRINITY'),'id_one')
        self.assertEqual(run.identity_projection_store.find_players('%_'),[])
        self.authenticate()
        self.assertEqual(self.search('a').status_code,400)
        self.assertEqual(self.search('x'*101).status_code,400)
        self.assertEqual(self.search('private.example.test').json['players'],[])
        for i in range(23):self.seed('sample_'+str(i),'Sample '+str(i))
        result=self.search('sample').json
        self.assertEqual(len(result['players']),20);self.assertTrue(result['truncated'])

    def test_anonymous_search_is_not_public(self):
        response=self.client.get('/api/players/search?q=alice')
        self.assertIn(response.status_code,(401,302))

    def test_isolated_restart_gate_requires_current_epoch(self):
        self.assertEqual(run.ghostsignal_show_db_path,self.path)
        self.assertIsNone(run.get_ghostsignal_show_service().restart_projection())
        self.authenticate()
        with patch.object(run.GhostSignalShowService,'restart_projection',return_value={'epoch':'directory-test-epoch'}):
            response=self.search('alice')
            self.assertEqual(response.status_code,423,response.json)
            self.assertEqual(response.json['error'],'ghostsystem_restart_required')
            with self.client.session_transaction() as sess:
                generation=sess[run.SESSION_GENERATION_KEY]
            response=self.client.get('/api/players/search?q=alice',headers={
                'X-Chaos-Session-Generation':generation,
                'X-Chaos-Ghost-Epoch':'directory-test-epoch'})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['players'][0]['username'],'alice')

    def test_safety_invite_by_nick_then_handle_duplicate_block_and_csrf(self):
        self.seed('id_google_fixture','Trinity')
        self.stack.enter_context(patch.dict(run.app.config,CHAOS_COMMUNICATION_SAFETY_ENABLED=True,CHAOS_AGE_POLICY_ENABLED=False))
        self.stack.enter_context(patch.object(run,'mail_store',MailStore(self.path)))
        with db_connect(self.path) as c:safety.initialize(c)
        self.authenticate()
        result=self.post('/api/safety/invite',{'username':'trinity'})
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.post('/api/safety/invite',{'username':'@id_google_fixture'}).json['status'],'already_pending')
        self.assertEqual(self.client.post('/api/safety/invite',json={'username':'Trinity'}).status_code,403)
        self.authenticate('id_google_fixture')
        self.assertEqual(self.post('/api/safety/invite/answer',{'username':'alice','accept':True}).status_code,200)
        self.assertTrue(run.mail_store.is_accepted_contact('alice','id_google_fixture'))
        self.assertEqual(self.post('/api/safety/block',{'username':'@alice','blocked':True}).status_code,200)
        self.authenticate()
        self.assertEqual(self.post('/api/safety/invite',{'username':'@id_google_fixture'}).status_code,400)

    def test_legacy_contact_resolves_to_account_not_nickname(self):
        self.seed('id_github_fixture','Octocat')
        self.stack.enter_context(patch.dict(run.app.config,CHAOS_COMMUNICATION_SAFETY_ENABLED=False))
        self.stack.enter_context(patch.object(run,'mail_store',MailStore(self.path)))
        self.authenticate()
        result=self.post('/api/contacts',{'name':'Octocat'})
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(run.mail_store.is_contact('alice','id_github_fixture'))
        self.assertFalse(run.mail_store.is_contact('alice','Octocat'))
