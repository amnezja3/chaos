import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import run
import test_player_target_selection as selection
from database import AppActionReceiptStore, PlayerOperationStore, db_connect


class PlayerHackCompletionTest(unittest.TestCase):
    setUp = selection.PlayerTargetSelectionTest.setUp
    seed = selection.PlayerTargetSelectionTest.seed
    prepare = selection.PlayerTargetSelectionTest.prepare
    setup_selection = selection.PlayerTargetSelectionTest.setup_selection
    mark = selection.PlayerTargetSelectionTest.mark

    def setup_complete(self, heavy=False):
        self.setup_selection(heavy=heavy)
        self.assertEqual(self.mark().status_code, 200)
        self.receipts = AppActionReceiptStore(self.path)
        self.operations = PlayerOperationStore(self.path)
        self.stack.enter_context(patch.object(run, 'app_action_receipt_store', self.receipts))
        self.stack.enter_context(patch.object(run, 'player_operation_store', self.operations))
        # Use the real server critical-key list, obtained from its resource.
        target = self.targets.get_active_target('attacker')
        template = json.loads((Path(run.__file__).parent / 'static/user_security.json').read_text(encoding='utf-8'))
        target['security'] = {key: False for key, value in template.items() if isinstance(value, bool)}
        target['actions_allowed'] = dict.fromkeys(('scan_ports', 'exploit', 'sniff', 'trace'), True)
        self.targets.upsert_aimed('attacker', target)
        self.inventory.install_app('attacker', {'id': 'completionTest', 'name': 'Completion Test',
                                              'requires_off': [], 'interferes_with': []}, purchase_key='completion-app')
        self.request = {'app_id': 'completionTest', 'launch_receipt': 'test-capture', 'expected_target': target}
        with db_connect(self.path) as conn:
            conn.execute('DELETE FROM player_hack_access')

    def test_capture_after_leaving_and_replay_after_expiry_without_profiles(self):
        self.setup_complete(heavy=True)
        self.positions.upsert('victim', {'lat': 53, 'lng': 22})
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            response = self.client.post('/gonna-win', json=self.request)
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertIn('player_hack_access', response.json)
            self.assertNotIn('hacked', response.json)
            deadline = response.json['player_hack_access']['hacked_until']
            self.assertEqual(response.json['captured_player']['target_username'], 'victim')
            self.assertEqual(response.json['captured_player']['player_hack_access_until'], deadline)
            self.assertIsNone(response.json['captured_target'])
            self.assertEqual(self.targets.get_active_target('attacker'), {})
            with patch('database.datetime', wraps=datetime) as clock:
                clock.utcnow.return_value = datetime.utcnow() + timedelta(hours=4)
                replay = self.client.post('/gonna-win', json=self.request)
            self.assertEqual(replay.status_code, 200, replay.get_json())
            self.assertTrue(replay.json['replayed'])
            self.assertFalse(replay.json['player_hack_access']['active'])
            self.assertEqual(replay.json['player_hack_access']['hacked_until'], deadline)

    def test_cooldown_explains_capture_refusal_without_renewing_access(self):
        self.setup_complete()
        self.access.grant_access('attacker', 'victim')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_hack_access SET hacked_until=? WHERE attacker_username='attacker'",
                         ((datetime.utcnow() - timedelta(minutes=1)).isoformat(timespec='seconds'),))
        before = self.access.get_cooldown('attacker', 'victim')
        target_before = self.targets.get('attacker')
        response = self.client.post('/gonna-win', json=self.request)
        self.assertEqual(response.status_code, 409, response.json)
        self.assertEqual(response.json['reason'], 'player_hack_cooldown')
        self.assertTrue(response.json['blocked'])
        self.assertIn('Cooldown PvP', response.json['message'])
        self.assertGreater(response.json['cooldown_seconds_left'], 0)
        self.assertEqual(response.json['cooldown_until'], before['cooldown_until'])
        self.assertIsNone(self.access.get_active_access('attacker', 'victim'))
        self.assertEqual(self.targets.get('attacker'), target_before)
        self.assertEqual(self.access.visible_cooldowns('attacker', ['victim']), {'victim': before['cooldown_until']})
        self.assertEqual(self.access.visible_cooldowns('other', ['victim']), {})
        self.assertEqual(self.access.visible_cooldowns('attacker', ['other']), {})

    def test_rollback_after_access_before_terminal_target(self):
        self.setup_complete()
        state = self.targets.get('attacker')
        with patch.object(self.targets, 'mark_captured', side_effect=RuntimeError('disk failure')):
            with self.assertRaises(RuntimeError):
                self.access.complete_capture('attacker', state['target'], state['version'], 'rollback',
                                             ['firewall'], self.targets, lambda access: {'success': True})
        self.assertIsNone(self.access.get_active_access('attacker', 'victim'))
        self.assertIsNone(self.access.get_capture_receipt('attacker', 'rollback'))
        self.assertEqual(self.targets.get('attacker')['version'], state['version'])

    def test_concurrent_completion_commits_once(self):
        self.setup_complete()
        state = self.targets.get('attacker')
        def complete(_):
            return self.access.complete_capture('attacker', state['target'], state['version'], 'concurrent',
                                                ['firewall'], self.targets, lambda access: {'deadline': access['hacked_until']})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(complete, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.targets.get('attacker')['version'], state['version'] + 1)

    def test_operation_only_does_not_grant_access(self):
        self.setup_complete()
        response = self.client.post('/gonna-win', json={**self.request, 'operation_only': True})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertTrue(response.json['operation_only'])
        self.assertIsNone(self.access.get_active_access('attacker', 'victim'))

    def test_failure_after_commit_replays_durable_capture(self):
        self.setup_complete()
        with patch.object(self.receipts, 'finish', side_effect=RuntimeError('response write failed')):
            response = self.client.post('/gonna-win', json=self.request)
        self.assertEqual(response.status_code, 500)
        access = self.access.get_active_access('attacker', 'victim')
        self.assertIsNotNone(access)
        replay = self.client.post('/gonna-win', json=self.request)
        self.assertEqual(replay.status_code, 200, replay.get_json())
        self.assertTrue(replay.json['replayed'])
        self.assertEqual(replay.json['player_hack_access']['hacked_until'], access['hacked_until'])

    def test_selection_change_cannot_capture_another_target(self):
        self.setup_complete()
        state = self.targets.get('attacker')
        self.targets.upsert_aimed('attacker', {**state['target'], 'target_id': 'player:other',
                                             'target_username': 'other', 'username': 'other'})
        with self.assertRaisesRegex(ValueError, 'target_selection_changed'):
            self.access.complete_capture('attacker', state['target'], state['version'], 'changed',
                                         ['firewall'], self.targets, lambda access: {})
        self.assertIsNone(self.access.get_active_access('attacker', 'victim'))
