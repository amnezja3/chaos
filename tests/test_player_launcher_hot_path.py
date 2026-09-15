import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import run
import test_player_target_selection as selection
from database import (AppActionReceiptStore, PlayerOperationStore, db_connect, ProfileRecoveryRequired,
                      reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics)
from tools.migrate_identity_projection import status
from test_ghostnetwork_suite_snapshot import valid_profile


class PlayerLauncherHotPathTest(unittest.TestCase):
    setUp = selection.PlayerTargetSelectionTest.setUp
    seed = selection.PlayerTargetSelectionTest.seed
    prepare = selection.PlayerTargetSelectionTest.prepare
    setup_selection = selection.PlayerTargetSelectionTest.setup_selection
    mark = selection.PlayerTargetSelectionTest.mark

    def setup_launcher(self, heavy=False):
        self.setup_selection(heavy=heavy)
        self.assertEqual(self.mark().status_code, 200)
        self.operations = PlayerOperationStore(self.path)
        self.receipts = AppActionReceiptStore(self.path)
        self.stack.enter_context(patch.object(run, 'player_operation_store', self.operations))
        self.stack.enter_context(patch.object(run, 'app_action_receipt_store', self.receipts))
        self.inventory.install_app('attacker', {
            'id': 'testScanner', 'name': 'Test Scanner', 'map_actions': ['scan_ports'],
            'operation_types': ['port_scan'], 'type': 'recon', 'requires_off': [],
        }, purchase_key='scanner')
        self.payload = {'action': 'scan_ports', 'lat': 52.2, 'lng': 21, 'label': 'victim',
                        'target_mode': 'player', 'target_username': 'victim',
                        'target_id': 'player:victim', 'selected_app_id': 'testScanner',
                        '_client_action_key': 'launch-test', '_flow_id': 'launch-flow'}

    def test_heavy_launch_continuation_queue_and_replay_without_profile(self):
        self.setup_launcher(heavy=True)
        self.positions.upsert('victim', {'lat': 53, 'lng': 22})
        revision = self.users.get_profile_with_revision('attacker')['profile_revision']
        token = reset_hot_path_metrics()
        self.addCleanup(restore_hot_path_metrics, token)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')), \
             patch.object(run, 'load_profile_readonly', side_effect=AssertionError('readonly full profile')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            response = self.client.post('/hack-action', json=self.payload)
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertTrue(response.json.get('added_apps'), response.get_json())
            queued = self.client.get('/launch-queue')
            self.assertEqual(queued.status_code, 200, queued.get_json())
            self.assertEqual(len(queued.json), 1)
            self.assertEqual(self.client.get('/launch-queue').json, [])
            replay = self.client.post('/hack-action', json=self.payload)
            self.assertEqual(replay.status_code, 200, replay.get_json())
            self.assertTrue(replay.json['duplicate'])
            self.assertEqual(self.client.get('/launch-queue').json, [])
        self.assertEqual(get_hot_path_metrics().get('profile_bytes', 0), 0)
        self.assertEqual(self.users.get_profile_with_revision('attacker')['profile_revision'], revision)
        self.assertEqual(len(self.inventory.launch_risk_events('attacker')), 1)
        self.assertTrue(self.targets.get_active_target('attacker')['actions_allowed']['scan_ports'])

    def test_atomic_queue_risk_warning_and_concurrent_consume(self):
        self.setup_launcher()
        item = {'name': 'Test Scanner', 'receipt': 'atomic', 'app_id': 'testScanner'}
        risk = {'id': 'risk-test', 'dedupe_key': 'risk-test', 'event_type': 'scan'}
        with patch.object(self.messages, 'add_message', side_effect=RuntimeError('disk failure')):
            with self.assertRaises(RuntimeError):
                self.inventory.commit_launch('attacker', [item], [risk], self.messages)
        self.assertEqual(self.inventory.consume_launches('attacker'), [])
        self.assertEqual(self.inventory.launch_risk_events('attacker'), [])
        self.inventory.commit_launch('attacker', [item], [risk], self.messages)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.inventory.consume_launches('attacker'), range(2)))
        self.assertEqual(sum(len(result) for result in results), 1)
        self.inventory.commit_launch('attacker', [item], [risk], self.messages)
        self.assertEqual(self.inventory.consume_launches('attacker'), [])
        self.assertEqual(len(self.inventory.launch_risk_events('attacker')), 1)

    def test_explicit_migration_preserves_pending_queue_and_risk_without_replay(self):
        self.setup_launcher()
        profile = valid_profile('legacy')
        profile['launch_queue'] = [{'name': 'Old tool', 'receipt': 'legacy-test'}]
        profile['risk_events'] = [{'id': 'old-risk'}]
        self.users.save_profile(profile)
        with db_connect(self.path) as conn:
            for table in ('player_launcher_state', 'player_launch_entries', 'player_launch_risk_events'):
                conn.execute(f"DELETE FROM {table} WHERE username='legacy'")
        self.assertEqual(status(self.path)['launcher_missing'], 1)
        with self.assertRaises(ProfileRecoveryRequired):
            self.inventory.consume_launches('legacy')
        self.identity.backfill_page(limit=10)
        self.assertEqual(status(self.path)['launcher_missing'], 0)
        self.assertEqual(self.inventory.consume_launches('legacy')[0]['receipt'], 'legacy-test')
        self.assertEqual(self.inventory.launch_risk_events('legacy')[0]['id'], 'old-risk')
        self.identity.backfill_page(limit=10)
        self.assertEqual(self.inventory.consume_launches('legacy'), [])

    def test_unmarked_player_cannot_be_launched_by_username(self):
        self.setup_launcher()
        self.targets.clear_if_matches('attacker', self.targets.get_active_target('attacker'))
        response = self.client.post('/hack-action', json=self.payload)
        self.assertEqual(response.status_code, 409, response.get_json())
        response = self.client.post('/hack-action', json={**self.payload, 'target_mode': 'standard'})
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(self.inventory.consume_launches('attacker'), [])

    def test_queue_preserves_insertion_order(self):
        self.setup_launcher()
        self.inventory.commit_launch('attacker', [
            {'name': key, 'receipt': key} for key in ('z', 'a', 'm')
        ], [], self.messages)
        self.assertEqual([item['receipt'] for item in self.inventory.consume_launches('attacker')], ['z', 'a', 'm'])

    def test_preflight_and_legacy_request_without_intent_key(self):
        self.setup_launcher()
        with patch.object(run, 'PROVISIONAL_APP_LAUNCH_ENABLED', True):
            preflight = self.client.post('/hack-action', json={**self.payload, 'selected_app_id': ''})
        self.assertEqual(preflight.status_code, 200, preflight.get_json())
        self.assertTrue(preflight.json['tool_selection_required'])
        self.assertEqual(self.inventory.consume_launches('attacker'), [])
        payload = {**self.payload, '_client_action_key': '', '_flow_id': ''}
        first = self.client.post('/hack-action', json=payload)
        self.assertEqual(first.status_code, 200, first.get_json())
        first_queue = self.inventory.consume_launches('attacker')
        second = self.client.post('/hack-action', json=payload)
        self.assertEqual(second.status_code, 200, second.get_json())
        second_queue = self.inventory.consume_launches('attacker')
        self.assertEqual(len(first_queue), 1)
        self.assertEqual(len(second_queue), 1)
        self.assertNotEqual(first_queue[0]['receipt'], second_queue[0]['receipt'])
