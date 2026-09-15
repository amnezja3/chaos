import unittest
from unittest.mock import patch
import run
import test_intruder_kicker as kicker
from test_ghostnetwork_suite_snapshot import valid_profile
from database import ProfileRecoveryRequired, db_connect, reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics


class MapActorHotPathTest(unittest.TestCase):
    setUp = kicker.IntruderKickerTest.setUp
    seed = kicker.IntruderKickerTest.seed
    prepare = kicker.IntruderKickerTest.prepare

    def check_snapshot(self, big_viewer, big_actor):
        self.prepare()
        for name, big, clan in [('attacker', big_viewer, 'virex'), ('victim', big_actor, '')]:
            record = self.users.get_profile_with_revision(name)
            self.users.patch_profile_guarded(name, {
                'clan': clan, 'ghost_clan_code': clan,
                'avatar': '/static/images/custom-test-avatar.png',
                'hot_path_padding': 'x' * (35 * 1024 * 1024 if big else 0),
            }, source='test.map_fixture', expected_revision=record['profile_revision'])
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')), \
             patch.object(self.users, 'list_profiles', side_effect=AssertionError('all profiles')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            token = reset_hot_path_metrics()
            try:
                response = self.client.get('/api/map/player-actors')
                self.assertEqual(response.status_code, 200, response.get_json())
                actor = response.json['player_actors'][0]
                self.assertEqual(actor['username'], 'victim')
                self.assertTrue(actor['attackable'])
                self.assertEqual(actor['position_version'], 1)
                self.assertEqual(actor['avatar'], '/static/images/custom-test-avatar.png')
                self.assertEqual(get_hot_path_metrics().get('profile_bytes', 0), 0)
            finally:
                restore_hot_path_metrics(token)

    def test_small(self):
        self.check_snapshot(False, False)

    def test_heavy_viewer(self):
        self.check_snapshot(True, False)

    def test_heavy_actor(self):
        self.check_snapshot(False, True)

    def test_heavy_both(self):
        self.check_snapshot(True, True)

    def test_candidate_projection_excludes_unrelated_outside_actors(self):
        self.prepare()
        vertices = [[point['lat'], point['lng']] for point in self.area['vertices']]
        self.assertEqual(len(self.identity.map_actor_candidates('attacker', polygons=[vertices])), 1)
        self.positions.upsert('victim', {'lat': 53, 'lng': 22})
        self.assertEqual(self.identity.map_actor_candidates('attacker', polygons=[self.area['vertices']]), [])
        self.assertEqual(len(self.identity.map_actor_candidates('attacker', contact_names=['victim'])), 1)
        self.assertEqual(len(self.identity.map_actor_candidates('attacker', clan_code='virex')), 1)
        with self.assertRaises(ProfileRecoveryRequired):
            self.identity.map_actor_candidates('attacker', polygons=[self.area['vertices']] * 129)

    def test_missing_avatar_projection_requires_explicit_backfill(self):
        self.prepare()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET desktop_boot_json=json_remove(desktop_boot_json, '$.avatar') WHERE username='victim'")
        with self.assertRaises(ProfileRecoveryRequired):
            self.identity.map_actor_candidates('attacker', contact_names=['victim'])
        before = self.users.get_profile_with_revision('victim')['profile_revision']
        self.identity.backfill_page(limit=10)
        self.assertEqual(len(self.identity.map_actor_candidates('attacker', contact_names=['victim'])), 1)
        self.assertEqual(self.users.get_profile_with_revision('victim')['profile_revision'], before)
