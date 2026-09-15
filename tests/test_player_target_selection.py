import unittest
from unittest.mock import patch

import run
import test_intruder_kicker as kicker
from database import (PlayerTargetRuntimeStore, ProfileRecoveryRequired, db_connect,
                      get_hot_path_metrics, reset_hot_path_metrics, restore_hot_path_metrics)
from tools.migrate_identity_projection import status, dry_run


class PlayerTargetSelectionTest(unittest.TestCase):
    setUp = kicker.IntruderKickerTest.setUp
    seed = kicker.IntruderKickerTest.seed
    prepare = kicker.IntruderKickerTest.prepare

    def setup_selection(self, heavy=False, foreign=True):
        self.prepare(heavy=heavy)
        if foreign:
            record = self.users.get_profile_with_revision('victim')
            self.users.patch_profile_guarded('victim', {
                'clan': '', 'ghost_clan_code': '', 'security': {'firewall': True},
            }, source='test.selection', expected_revision=record['profile_revision'])
        self.positions.upsert('attacker', {'lat': 52.2, 'lng': 21.0001})
        self.targets = PlayerTargetRuntimeStore(self.path)
        self.stack.enter_context(patch.object(run, 'player_target_runtime_store', self.targets))

    def mark(self):
        return self.client.post('/api/map/player-targets/mark', json={'target_username': 'victim'})

    def test_heavy_selection_and_retry_use_canonical_position_and_progress(self):
        self.setup_selection(heavy=True)
        before = self.users.get_profile_with_revision('attacker')['profile_revision']
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')), \
             patch.object(self.users, 'list_profiles', side_effect=AssertionError('full scan')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            token = reset_hot_path_metrics()
            try:
                response = self.mark()
                self.assertEqual(response.status_code, 200, response.get_json())
                target = response.json['target']
                self.assertEqual(target['target_id'], 'player:victim')
                self.assertEqual(target['lat'], 52.2)
                self.assertEqual(target['position_version'], self.positions.get('victim')['version'])
                target['security']['firewall'] = False
                target['actions_allowed']['scan_ports'] = True
                self.targets.upsert_aimed('attacker', target)
                retry = self.mark()
                self.assertEqual(retry.status_code, 200, retry.get_json())
                self.assertFalse(retry.json['target']['security']['firewall'])
                self.assertTrue(retry.json['target']['actions_allowed']['scan_ports'])
                self.assertEqual(get_hot_path_metrics().get('profile_bytes', 0), 0)
            finally:
                restore_hot_path_metrics(token)
        self.assertEqual(self.users.get_profile_with_revision('attacker')['profile_revision'], before)

    def test_hidden_or_teleported_target_cannot_be_marked(self):
        self.setup_selection()
        self.positions.upsert('victim', {'lat': 53.0, 'lng': 22.0})
        response = self.mark()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json['reason'], 'target_not_visible')
        self.assertEqual(self.targets.get_active_target('attacker'), {})

    def test_visible_but_out_of_range(self):
        self.setup_selection()
        self.positions.upsert('attacker', {'lat': 53.0, 'lng': 22.0})
        response = self.mark()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json['reason'], 'target_out_of_range')
        self.assertEqual(self.targets.get_active_target('attacker'), {})

    def test_same_clan_and_self_rejected(self):
        self.setup_selection(foreign=False)
        self.assertEqual(self.mark().status_code, 403)
        response = self.client.post('/api/map/player-targets/mark', json={'target_username': 'attacker'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.targets.get_active_target('attacker'), {})

    def test_friend_cannot_be_marked_even_when_hostile_inside_territory(self):
        self.setup_selection()
        with patch.object(run.mail_store, 'list_accepted_contacts', return_value=[{'name': 'victim'}]):
            actors = run.build_visible_player_actors('attacker')
            self.assertFalse(actors[0]['actions']['mark_target']['enabled'])
            self.assertEqual(self.mark().status_code, 403)
        self.assertEqual(self.targets.get_active_target('attacker'), {})

    def test_migration_rejects_unbounded_security_without_copying_it(self):
        self.setup_selection()
        record = self.users.get_profile_with_revision('victim')
        self.users.patch_profile_guarded('victim', {'security': {str(i): True for i in range(129)}},
                                        source='test.security_limit', expected_revision=record['profile_revision'])
        report = dry_run(self.path, limit=10)
        self.assertEqual(report['skipped'][0]['errors'], ['player_security_projection_invalid'])
        self.assertEqual(self.identity.backfill_page(limit=10)['skipped'][0]['username'], 'victim')
        with self.assertRaises(ProfileRecoveryRequired):
            self.identity.get_player_security('victim')

    def test_guarded_security_update_refreshes_projection_without_descriptions(self):
        self.setup_selection()
        record = self.users.get_profile_with_revision('victim')
        self.users.patch_profile_guarded('victim', {
            'security': {'firewall': False, 'anonymity_score': 50,
                         'descriptions': {'firewall': 'display metadata'}},
        }, source='test.security_update', expected_revision=record['profile_revision'])
        self.assertEqual(self.identity.get_player_security('victim'), {'firewall': False, 'anonymity_score': 50})

    def test_missing_security_requires_explicit_backfill(self):
        self.setup_selection()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET desktop_boot_json=json_remove(desktop_boot_json, '$.player_security') WHERE username='victim'")
        self.assertEqual(status(self.path)['player_security_missing'], 1)
        with self.assertRaises(ProfileRecoveryRequired):
            self.identity.get_player_security('victim')
        self.assertEqual(self.mark().status_code, 409)
        self.assertEqual(self.targets.get_active_target('attacker'), {})
        before = self.users.get_profile_with_revision('victim')['profile_revision']
        self.identity.backfill_page(limit=10)
        self.assertEqual(status(self.path)['player_security_missing'], 0)
        self.assertEqual(self.identity.get_player_security('victim'), {'firewall': True})
        self.assertEqual(self.users.get_profile_with_revision('victim')['profile_revision'], before)
        self.assertEqual(self.mark().status_code, 200)


if __name__ == '__main__':
    unittest.main()
