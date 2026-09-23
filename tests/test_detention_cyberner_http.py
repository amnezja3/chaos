import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import run
from database import db_connect, WalletBalanceStore
from session_generation_store import SessionGenerationStore
from response_network.detention import DetentionService
from response_network.consequence_table import plan_consequence
from tests import test_cyberner_channel_routing as fixture


class DetentionCybernerHTTPTest(unittest.TestCase):
    client_for = fixture.CybernerChannelRoutingTest.client_for

    def setUp(self):
        fixture.CybernerChannelRoutingTest.setUp(self)
        self.addCleanup(lambda: fixture.CybernerChannelRoutingTest.tearDown(self))
        SessionGenerationStore(self.db_path)
        self.detention = DetentionService(self.db_path, WalletBalanceStore(self.db_path), self.system_store, self.delta_bus)
        guard = patch.object(run, 'detention_service', self.detention)
        guard.start(); self.addCleanup(guard.stop)

    def sentence(self, stage):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.detention.sanctions.impose(conn, encounter_id='sentence', actor_id='alice',
                incident_id='incident', plan=plan_consequence(2,stage-1), now=datetime.now(timezone.utc))

    def test_world_hidden_bootstrap_history_and_live_private_still_delivered(self):
        bob = self.client_for('bob')
        bob.post('/api/chats/messages', json={'scope':'world','body':'secret world preview','client_message_id':'world'})
        self.sentence(8)
        alice = self.client_for('alice')
        response = alice.get('/api/mail/bootstrap')
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['group_messages'],[])
        self.assertFalse(response.json['channel_states']['world']['available'])
        response = alice.get('/api/chats/messages?scope=group&peer=global')
        self.assertEqual(response.status_code,403,response.json)
        self.delta_bus.record_change('alice','mail','cyberner.message_created',
            {'channel':'world','message':{'body':'world live'}},entity_id='world')
        self.delta_bus.record_change('alice','mail','cyberner.message_created',
            {'channel':'direct','message':{'body':'private live'}},entity_id='direct')
        response = alice.get('/api/state/changes?since=0')
        self.assertEqual(response.status_code,200,response.json)
        self.assertNotIn('world live',str(response.json))
        self.assertIn('private live',str(response.json))
        response = alice.get('/system-messages')
        self.assertNotIn('secret world preview',str(response.json))
        bob.post('/api/chats/messages',json={'scope':'direct','peer':'alice','body':'incoming','client_message_id':'incoming'})
        response = alice.get('/api/chats/messages?scope=direct&peer=bob')
        self.assertEqual(response.status_code,200,response.json)
        self.assertIn('incoming',str(response.json))

    def test_stage_nine_shared_allowance_self_error_retry_and_receiving(self):
        self.sentence(9)
        alice = self.client_for('alice')
        response = alice.post('/api/chats/messages',json={'scope':'direct','peer':'alice','body':'invalid'})
        self.assertEqual(response.status_code,400,response.json)
        payload={'scope':'direct','peer':'bob','body':'please pay bail','client_message_id':'one'}
        response=alice.post('/api/chats/messages',json=payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['detention']['private_messages_remaining'],0)
        received = self.client_for('bob').get('/api/chats/messages?scope=direct&peer=alice')
        notice = next(m for m in received.json['messages'] if m['body']=='please pay bail')['detention_notice']
        self.assertEqual(notice['actor_id'],'alice')
        self.assertEqual(notice['bail_hc'],1000000)
        self.assertTrue(notice['sanction_id'])
        response=alice.post('/api/chats/messages',json=payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertTrue(response.json['idempotent_replay'])
        for scope,peer in [('clan','clan:virex'),('channel','friends'),('direct','carol')]:
            response=alice.post('/api/chats/messages',json={'scope':scope,'peer':peer,'body':'second','client_message_id':peer})
            self.assertEqual(response.status_code,403,response.json)
        self.mail_store.add_message('bob','direct','alice','bob','received after allowance')
        response=alice.get('/api/chats/messages?scope=direct&peer=bob')
        self.assertEqual(response.status_code,200,response.json)
        self.assertIn('received after allowance',str(response.json))

    def test_notice_shared_world_and_clan_survives_history_and_cannot_be_forged(self):
        alice = self.client_for('alice')
        forged = alice.post('/api/chats/messages',json={'scope':'world','body':'ordinary',
            'client_message_id':'fake','detention_notice':{'sanction_id':'fake','bail_hc':1}})
        self.assertEqual(forged.status_code,200,forged.json)
        self.sentence(6)
        for scope,peer in [('world','global'),('clan','clan:virex')]:
            result = alice.post('/api/chats/messages',json={'scope':scope,'peer':peer,'body':'help '+scope,'client_message_id':scope})
            self.assertEqual(result.status_code,200,result.json)
            history = alice.get('/api/chats/messages',query_string={'scope':scope,'peer':peer})
            message = next(m for m in history.json['messages'] if m['body']=='help '+scope)
            self.assertEqual(message['detention_notice']['bail_hc'],250000)
            self.assertEqual(message['detention_notice']['actor_id'],'alice')
            for m in history.json['messages']:
                if m['body']=='ordinary': self.assertFalse(m.get('detention_notice'))

    def test_world_read_only_and_clan_authorization_survive(self):
        self.sentence(7)
        alice=self.client_for('alice')
        self.assertEqual(alice.get('/api/chats/messages?scope=world').status_code,200)
        response=alice.post('/api/chats/messages',json={'scope':'world','body':'not allowed'})
        self.assertEqual(response.status_code,403,response.json)
        self.assertEqual(response.json['reason'],'detention_world_read_only')
        response=alice.post('/api/chats/messages',json={'scope':'clan','peer':'clan:sentinel_order','body':'foreign'})
        self.assertEqual(response.status_code,400,response.json)
        response=alice.post('/api/chats/messages',json={'scope':'clan','peer':'clan:virex','body':'own clan'})
        self.assertEqual(response.status_code,200,response.json)

    def test_sentence_after_preflight_rejects_gameplay_commit(self):
        alice = self.client_for('alice')
        with db_connect(self.db_path) as conn:
            conn.execute('CREATE TABLE detention_race_probe (value INTEGER)')
        endpoint = next(rule.endpoint for rule in run.app.url_map.iter_rules() if rule.rule == '/command')
        def racing_action():
            with ThreadPoolExecutor(max_workers=1) as worker:
                worker.submit(self.sentence, 9).result()  # Outside request context, as in the worker.
            with db_connect(self.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('INSERT INTO detention_race_probe VALUES (1)')
            return {'ok':True}
        with patch.dict(run.app.view_functions,{endpoint:racing_action}):
            response=alice.post('/command',json={'command':'hack'})
        self.assertEqual(response.status_code,403,response.json)
        self.assertEqual(response.json['reason'],'detention_app_blocked')
        self.assertNotIn('X-Chaos-Session-Error', response.headers)
        with db_connect(self.db_path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM detention_race_probe').fetchone()[0],0)
            self.assertIsNotNone(self.detention.sanctions.active_for(conn,'alice'))
