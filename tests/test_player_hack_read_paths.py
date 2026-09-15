import os
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import run
from database import (UserStore, UserIdentityProjectionStore, PlayerInventoryStore,
                      PlayerHackAccessStore, SystemMessageStore, db_connect,
                      reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics)
from session_generation_fixture import SessionGenerationFixture
from test_ghostnetwork_suite_snapshot import valid_profile


class PlayerHackReadPathsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'game.sqlite3')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.users = UserStore(self.path)
        self.identity = UserIdentityProjectionStore(self.path)
        self.inventory = PlayerInventoryStore(self.path)
        self.access = PlayerHackAccessStore(self.path)
        self.messages = SystemMessageStore(self.path)
        for key, store in [('user_store', self.users), ('identity_projection_store', self.identity),
                           ('player_inventory_store', self.inventory), ('player_hack_access_store', self.access),
                           ('system_message_store', self.messages)]:
            self.stack.enter_context(patch.object(run, key, store))
        self.generation = SessionGenerationFixture().start()
        self.addCleanup(self.generation.stop)
        self.client = run.app.test_client()
        self.generation.authenticate(self.client, 'attacker')

    def seed(self, big_attacker=False, big_victim=False):
        for username, big in [('attacker', big_attacker), ('victim', big_victim)]:
            profile = valid_profile(username, padding='x' * (35 * 1024 * 1024 if big else 0))
            profile['nick'] = username
            profile['system_messages'] = [{'text': 'stale profile mirror'}]
            self.users.save_profile(profile)
            self.inventory.seed_from_profile(username, valid_profile(username))
        self.inventory.install_app('attacker', {'id': 'systemLogReader', 'name': 'System Log Reader'}, purchase_key='test-log')
        self.inventory.install_app('attacker', {'id': 'victimPicker', 'name': 'Victim Picker'}, purchase_key='test-picker')
        self.access.grant_access('attacker', 'victim')

    def check_http_access_and_logs(self, big_attacker, big_victim):
        self.seed(big_attacker=big_attacker, big_victim=big_victim)
        for i in range(8):
            self.messages.add_message('victim', {'id': str(i), 'title': str(i), 'text': 'z' * 5000,
                                               'created_at': f'2026-09-15T12:00:0{i}'})
        self.messages.add_message('other', {'text': 'private-other'})
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('heavy revision')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            token = reset_hot_path_metrics()
            try:
                response = self.client.get('/api/player-hack/access')
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual({t['id'] for t in response.json['tools']}, run.PLAYER_HACK_TOOL_IDS)
                response = self.client.post('/api/player-hack/tool/use', json={'tool_id': 'systemLogReader', 'victim_username': 'victim'})
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual([m['title'] for m in response.json['logs']], ['3', '4', '5', '6', '7'])
                self.assertTrue(all(len(m['text']) == 4096 and m['truncated'] for m in response.json['logs']))
                self.assertEqual(get_hot_path_metrics().get('profile_bytes', 0), 0)
            finally:
                restore_hot_path_metrics(token)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM system_messages WHERE username='victim' AND status='pending'").fetchone()[0], 8)

    def test_small_accounts(self):
        self.check_http_access_and_logs(False, False)

    def test_heavy_attacker(self):
        self.check_http_access_and_logs(True, False)

    def test_heavy_victim(self):
        self.check_http_access_and_logs(False, True)

    def test_heavy_both_accounts(self):
        self.check_http_access_and_logs(True, True)

    def test_unsupported_tool_expiry_wrong_victim_and_security_gate(self):
        self.seed()
        response = self.client.post('/api/player-hack/tool/use', json={'tool_id': 'victimPicker', 'victim_username': 'victim'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['reason'], 'unsupported_player_hack_tool')
        with patch.object(run, 'load_profile_write_record', side_effect=AssertionError('must reject before profile read')):
            for route, payload in [('update', {'key': 'firewall', 'value': False}), ('preset', {'preset': 'all_off'})]:
                response = self.client.post('/api/player-hack/security/' + route, json={'victim_username': 'victim', **payload})
                self.assertEqual(response.status_code, 403, response.get_json())
                self.assertEqual(response.json['reason'], 'tool_not_installed')
        response = self.client.post('/api/player-hack/tool/use', json={'tool_id': 'systemLogReader', 'victim_username': 'other'})
        self.assertEqual(response.status_code, 403)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01T00:00:00'")
        response = self.client.post('/api/player-hack/tool/use', json={'tool_id': 'systemLogReader', 'victim_username': 'victim'})
        self.assertEqual(response.status_code, 403)

    def test_stale_generation_and_invalid_projection_fail_closed(self):
        self.seed()
        response = self.client.get('/api/player-hack/access', headers={run.SESSION_GENERATION_HEADER: 'old'})
        self.assertEqual(response.status_code, 409)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET source_profile_revision=0 WHERE username='victim'")
        response = self.client.get('/api/player-hack/access')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json['error'], 'profile_recovery_required')
