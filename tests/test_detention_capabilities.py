import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from database import db_connect, MailStore, CybernerWorldStore, CybernerClanStore
from response_network.capabilities import DetentionDenied, snapshot, require_request, require_world
from response_network.chat_delivery import deliver
from response_network.consequence_table import plan_consequence
from tests import test_detention_transport as fixture


class DetentionCapabilitiesTest(unittest.TestCase):
    seed_actor = fixture.DetentionTransportTest.seed_actor
    candidate = fixture.DetentionTransportTest.candidate
    rows = fixture.DetentionTransportTest.rows

    def setUp(self):
        fixture.DetentionTransportTest.setUp(self)
        self.mail = MailStore(self.path)
        self.clan = CybernerClanStore(self.path)
        self.world = CybernerWorldStore(self.path)

    def sentence(self, stage=6):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.sentence_row, _ = self.service.sanctions.impose(conn, encounter_id='sentence',
                actor_id='alice', incident_id='incident', plan=plan_consequence(2, stage-1), now=self.now)

    def send(self, channel, key, body='hello'):
        route = {'channel': channel, 'channel_key': 'test'}
        def writer(conn):
            if channel == 'world':
                return self.world.add_message('alice', body, client_message_id=key, conn=conn)
            if channel == 'clan':
                return self.clan.add_message('team', 'alice', body, client_message_id=key, conn=conn)
            self.mail.add_message('alice', 'direct', 'bob', 'alice', body, conn=conn)
            return dict(conn.execute("SELECT * FROM chat_messages WHERE owner_username='alice' ORDER BY id DESC LIMIT 1").fetchone()), True
        return deliver(self.path, 'alice', route, body, '', key, writer)

    def test_stage_matrix_private_read_essential_and_default_deny(self):
        for stage in range(6, 10):
            with self.subTest(stage=stage):
                self.sentence(stage)
                with db_connect(self.path) as conn:
                    state = snapshot(conn, 'alice')
                    self.assertEqual(state['private_messages_remaining'], 1)
                    for path, method in [('/api/chats/messages','GET'),('/api/chats/messages','POST'),
                                         ('/api/response/detention/bail','POST'),('/logout','GET'),
                                         ('/api/radio/channels','GET'),('/api/googleplex/news','GET')]:
                        require_request(conn,'alice',path,method)
                    for path, method in [('/command','POST'),('/gonna-win','POST'),('/hack-action','POST'),
                                         ('/map-action','POST'),('/api/ghostlab/projects','GET'),
                                         ('/api/new-unclassified-feature','GET')]:
                        if stage == 9:
                            with self.assertRaises(DetentionDenied): require_request(conn,'alice',path,method)
                        else: require_request(conn,'alice',path,method)
                    for sending in (False, True):
                        if stage >= 8 or (stage == 7 and sending):
                            with self.assertRaises(DetentionDenied): require_world(conn,'alice',sending=sending)
                        else: require_world(conn,'alice',sending=sending)
                    conn.execute('DELETE FROM response_sanctions')
                    conn.execute('DELETE FROM response_sanction_events')

    def test_one_shared_send_under_concurrency_and_retry(self):
        self.sentence(9)
        def try_send(channel):
            try: return self.send(channel, channel), channel
            except DetentionDenied: return None, channel
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(try_send, ['direct','clan']))
        successful = [(result, channel) for result,channel in results if result]
        self.assertEqual(len(successful), 1)
        result, channel = successful[0]
        retry, created = self.send(channel, channel)
        self.assertFalse(created)
        self.assertEqual(retry, result[0])
        with self.assertRaises(ValueError): self.send(channel, channel, 'changed body')
        with self.assertRaises(DetentionDenied): self.send('direct','new-key')
        # Receiving is untouched, including after consuming the allowance.
        self.mail.add_message('bob','direct','alice','bob','reply')
        self.assertTrue(any(m['body']=='reply' for m in self.mail.list_messages('alice','direct','bob')))

    def test_delivery_failure_preserves_allowance_and_world_does_not_consume_it(self):
        self.sentence()
        for key in ['world1','world2']: self.send('world', key)
        def broken(conn):
            self.mail.add_message('alice','direct','bob','alice','rollback',conn=conn)
            raise RuntimeError('delivery failed')
        with self.assertRaises(RuntimeError):
            deliver(self.path,'alice',{'channel':'direct','channel_key':'bob'},'rollback','','fail',broken)
        with db_connect(self.path) as conn:
            self.assertEqual(snapshot(conn,'alice')['private_messages_remaining'],1)
            self.assertEqual(conn.execute('SELECT count(*) FROM chat_messages').fetchone()[0],0)
        self.send('direct','success')

    def test_http_gate_blocks_direct_actions_but_allows_private_reads(self):
        import run
        from tests import test_target_persistence as http_fixture
        self.sentence(9)
        http_fixture.setUpModule(); self.addCleanup(http_fixture.tearDownModule)
        with patch.object(run,'detention_service',self.service):
            client = run.app.test_client()
            with client.session_transaction() as session: session['user']='alice'
            for path in ['/command','/gonna-win','/hack-action','/api/player-contact/request']:
                response = client.post(path,json={})
                self.assertEqual(response.status_code,403,response.json)
                self.assertIn('detention',response.json)
            response = client.get('/api/response/detention')
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['detention']['stage'],9)

    def test_real_cyberner_router_direct_clan_and_world(self):
        import run
        self.sentence(8)
        with patch.object(run,'detention_service',self.service), patch.object(run,'mail_store',self.mail), \
             patch.object(run,'cyberner_clan_store',self.clan), patch.object(run,'cyberner_world_store',self.world), \
             patch.object(run,'cyberner_message_recipients',return_value=['bob']), \
             patch.object(run,'cyberner_shared_store_enabled',side_effect=lambda channel: channel in {'world','clan'}):
            route = run.normalize_cyberner_route('direct','bob',{'username':'alice'})
            first, created = run.cyberner_store_message('alice',{},route,'message',client_message_id='direct-key')
            self.assertTrue(created)
            second, created = run.cyberner_store_message('alice',{},route,'message',client_message_id='direct-key')
            self.assertFalse(created); self.assertEqual(first,second)
            clan = {'channel':'clan','channel_key':'clan:team','store_key':'team','scope':'clan','peer':'clan:team'}
            with self.assertRaises(DetentionDenied): run.cyberner_store_message('alice',{},clan,'second')
            world = run.normalize_cyberner_route('group','global',{})
            with self.assertRaises(DetentionDenied): run.cyberner_list_route_messages('alice',world)
            with self.assertRaises(DetentionDenied): run.cyberner_store_message('alice',{},world,'public')
