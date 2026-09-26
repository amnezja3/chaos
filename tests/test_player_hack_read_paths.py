import os
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import run
from database import (UserStore, UserIdentityProjectionStore, UserCapabilityProjectionStore, PlayerInventoryStore,
                      PlayerHackAccessStore, SystemMessageStore, db_connect,
                      reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics)
from session_generation_fixture import SessionGenerationFixture
from test_ghostnetwork_suite_snapshot import valid_profile


class PlayerHackReadPathsTest(unittest.TestCase):
    def test_read_tools_show_used_buttons_and_reject_repeat(self):
        self.seed()
        for tool_id in ('systemLogReader', 'securityPanelProxy'):
            if not self.inventory.has_app('attacker', tool_id):
                self.inventory.install_app('attacker', {'id': tool_id, 'name': tool_id}, purchase_key=tool_id)
            payload = {'tool_id': tool_id, 'victim_username': 'victim'}
            first = self.client.post('/api/player-hack/tool/use', json=payload)
            self.assertEqual(first.status_code, 200, first.json)
            tool = next(t for t in first.json['access']['tools'] if t['id'] == tool_id)
            self.assertFalse(tool['enabled'])
            self.assertTrue(tool['used'])
            second = self.client.post('/api/player-hack/tool/use', json=payload)
            self.assertEqual(second.status_code, 409)
            self.assertEqual(second.json['reason'], 'tool_already_used')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'game.sqlite3')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.users = UserStore(self.path)
        self.identity = UserIdentityProjectionStore(self.path)
        self.capabilities = UserCapabilityProjectionStore(self.path)
        self.inventory = PlayerInventoryStore(self.path)
        self.access = PlayerHackAccessStore(self.path)
        self.messages = SystemMessageStore(self.path)
        for key, store in [('user_store', self.users), ('identity_projection_store', self.identity),
                           ('capability_projection_store', self.capabilities),
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
                self.assertEqual({t['id'] for t in response.json['tools']}, {'systemLogReader'})
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

    def test_cleaner_atomic_uninstall_heavy_profiles_and_retry(self):
        self.seed(big_attacker=True, big_victim=True)
        self.inventory.install_app('attacker', {'id': 'arsenalCleaner', 'name': 'Arsenal Cleaner'}, purchase_key='cleaner')
        target = {'id': 'removable', 'name': 'Removable Tool', 'storage_size': 5}
        self.inventory.install_app('victim', target, purchase_key='target')
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO player_tool_files (username, tool_id, app_id, tool_json, version, updated_at) VALUES ('victim', 'legacy-tool', '', ?, 1, '2026-09-16')",
                         ('{"name":"Removable Tool.sh","file_size":3}',))
            conn.execute("INSERT INTO player_tool_files (username, tool_id, app_id, tool_json, version, updated_at) VALUES ('victim', 'other-tool', 'other-app', ?, 1, '2026-09-16')",
                         ('{"name":"Removable Tool.sh","file_size":2}',))
        payload = {'tool_id': 'arsenalCleaner', 'victim_username': 'victim'}
        access = self.access.get_active_access('attacker', 'victim')
        original = self.inventory.uninstall_app
        def fail_after_uninstall(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('simulated crash before commit')
        with patch.object(self.inventory, 'uninstall_app', side_effect=fail_after_uninstall):
            with self.assertRaises(RuntimeError):
                self.inventory.apply_arsenal_cleaner(self.access, access, 'attacker', 'victim', 'removable', 'removed')
        self.assertTrue(self.inventory.has_app('victim', 'removable'))
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM game_state_deltas WHERE username='victim' AND type='apps.app_uninstalled'").fetchone()[0], 0)
            self.assertIsNotNone(conn.execute("SELECT 1 FROM player_tool_files WHERE tool_id='legacy-tool' AND username='victim'").fetchone())
        self.assertFalse(self.access.has_tool_usage(access, 'attacker', 'victim', 'arsenalCleaner'))
        with patch('database.GameStateDeltaBus.record_change', side_effect=RuntimeError('delta failure')):
            with self.assertRaises(RuntimeError):
                self.inventory.apply_arsenal_cleaner(self.access, access, 'attacker', 'victim', 'removable', 'removed')
        self.assertTrue(self.inventory.has_app('victim', 'removable'))
        self.assertFalse(self.access.has_tool_usage(access, 'attacker', 'victim', 'arsenalCleaner'))
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('heavy revision')), \
             patch.object(self.users, 'patch_profile_guarded', side_effect=AssertionError('profile write')), \
             patch.object(run, 'choice', return_value=target), patch.object(run, 'randint', return_value=1):
            response = self.client.post('/api/player-hack/tool/use', json=payload)
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertTrue(response.json['removed'])
            self.assertFalse(self.inventory.has_app('victim', 'removable'))
            with db_connect(self.path) as conn:
                import json
                event = conn.execute("SELECT payload_json FROM game_state_deltas WHERE username='victim' AND type='apps.app_uninstalled'").fetchone()
                self.assertIsNotNone(event)
                projection = json.loads(event['payload_json'])
                self.assertEqual(projection['removed_app_ids'], ['removable'])
                self.assertIn('legacy-tool', [tool['tool_id'] for tool in projection['removed_tools']])
                self.assertNotIn('apps', projection)
                self.assertNotIn('files', projection)
                self.assertIsNone(conn.execute("SELECT 1 FROM player_tool_files WHERE tool_id='legacy-tool' AND username='victim'").fetchone())
                self.assertIsNotNone(conn.execute("SELECT 1 FROM player_tool_files WHERE tool_id='other-tool' AND username='victim'").fetchone())
            receipt = self.access.get_tool_usage(access, 'attacker', 'victim', 'arsenalCleaner')
            self.assertEqual((receipt['result'], receipt['amount']), ('removed', 1))
            self.assertEqual(self.client.post('/api/player-hack/tool/use', json=payload).status_code, 409)
        replay = self.inventory.apply_arsenal_cleaner(self.access, access, 'attacker', 'victim', 'removable', 'removed')
        self.assertTrue(replay['duplicate'])

    def test_cleaner_no_apps_and_failed_roll(self):
        self.seed()
        self.inventory.install_app('attacker', {'id': 'arsenalCleaner', 'name': 'Arsenal Cleaner'}, purchase_key='cleaner')
        payload = {'tool_id': 'arsenalCleaner', 'victim_username': 'victim'}
        # Core apps remain protected even when the canonical inventory contains them.
        for item in self.inventory.desktop_apps('victim'):
            self.inventory.uninstall_app('victim', app_id=item['id'])
        self.inventory.install_app('victim', {'id': 'core-test', 'name': 'Core', 'category': 'core'}, purchase_key='core')
        response = self.client.post('/api/player-hack/tool/use', json=payload)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertFalse(response.json['removed'])
        self.assertEqual(response.json['chance'], 0)
        self.assertTrue(self.inventory.has_app('victim', 'core-test'))
        with db_connect(self.path) as conn:
            conn.execute('DELETE FROM player_hack_tool_usage')
        self.inventory.install_app('victim', {'id': 'target', 'name': 'Target'}, purchase_key='target')
        with patch.object(run, 'randint', return_value=100), patch.object(run, 'random', return_value=1):
            response = self.client.post('/api/player-hack/tool/use', json=payload)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertFalse(response.json['removed'])
        self.assertFalse(response.json['detected'])
        self.assertTrue(self.inventory.has_app('victim', 'target'))

    def test_cleaner_concurrent_use_removes_only_one_app(self):
        from concurrent.futures import ThreadPoolExecutor
        self.seed()
        for app_id in ('one', 'two'):
            self.inventory.install_app('victim', {'id': app_id, 'name': app_id}, purchase_key=app_id)
        access = self.access.get_active_access('attacker', 'victim')
        def attempt(app_id):
            return self.inventory.apply_arsenal_cleaner(self.access, access, 'attacker', 'victim', app_id, 'removed')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ('one', 'two')))
        self.assertEqual(sum(bool(r['duplicate']) for r in results), 1)
        self.assertEqual(sum(self.inventory.has_app('victim', app_id) for app_id in ('one', 'two')), 1)

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
