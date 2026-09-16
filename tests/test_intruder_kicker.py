import unittest
from unittest.mock import patch
import run
from database import PlayerPositionStore, TerritoryStore, GameStateDeltaBus
import test_player_hack_read_paths as read_paths
import test_first_respawn_territory_edge as respawn


class IntruderKickerTest(unittest.TestCase):
    seed = read_paths.PlayerHackReadPathsTest.seed

    def setUp(self):
        read_paths.PlayerHackReadPathsTest.setUp(self)
        self.positions = PlayerPositionStore(self.path)
        self.territories = TerritoryStore(self.path)
        self.deltas = GameStateDeltaBus(self.path)
        for name, store in [('player_position_store', self.positions), ('territory_store', self.territories), ('delta_bus', self.deltas)]:
            self.stack.enter_context(patch.object(run, name, store))

    def prepare(self, heavy=False):
        self.seed(heavy, heavy)
        self.inventory.install_app('attacker', {'id': 'intruderKicker', 'name': 'Intruder Kicker'}, purchase_key='kicker')
        self.positions.upsert('victim', {'lat': 52.2, 'lng': 21.0})
        self.area = respawn.FirstRespawnTerritoryEdgeTest.area(1, 'attacker')
        self.territories.replace_player_areas('attacker', [self.area])

    def use(self):
        return self.client.post('/api/player-hack/tool/use', json={'tool_id': 'intruderKicker', 'victim_username': 'victim'})

    def test_heavy_success_replay_and_private_durable_position(self):
        self.prepare(heavy=True)
        before = self.positions.get('victim')
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('heavy revision')):
            response = self.use()
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertTrue(response.json['kicked'])
            replay = self.use()
            self.assertEqual(replay.status_code, 409)
            self.assertEqual(replay.json['reason'], 'tool_already_used')
            self.assertTrue(next(tool for tool in replay.json['access']['tools'] if tool['id'] == 'intruderKicker')['used'])
        after = self.positions.get('victim')
        self.assertEqual(after['version'], before['version'] + 1)
        self.assertFalse(run.territory_point_in_polygon_or_boundary(after, self.area['vertices']))
        events = self.deltas.get_changes_since('victim')['changes']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['type'], 'map.player_forced_position')
        self.assertEqual(events[0]['payload']['position_version'], after['version'])
        owner_events = self.deltas.get_changes_since('attacker')['changes']
        self.assertEqual(owner_events[0]['type'], 'map.player_actor_removed')
        self.assertNotIn('lat', owner_events[0]['payload'])
        self.assertNotIn('position', response.json)

    def test_outside_or_uninstalled_does_not_move(self):
        self.prepare()
        self.positions.upsert('victim', {'lat': 53.0, 'lng': 21.0})
        before = self.positions.get('victim')
        self.assertEqual(self.use().status_code, 409)
        self.assertEqual(self.positions.get('victim'), before)
        self.inventory.uninstall_app('attacker', 'intruderKicker')
        self.assertEqual(self.use().status_code, 403)

    def test_delta_failure_rolls_back_position_and_receipt(self):
        self.prepare()
        before = self.positions.get('victim')
        with patch.object(self.deltas, 'record_change', side_effect=RuntimeError('disk failure')):
            with self.assertRaises(RuntimeError):
                run.execute_intruder_kicker('attacker', 'victim')
        self.assertEqual(self.positions.get('victim'), before)
        access = self.access.get_active_access('attacker', 'victim')
        self.assertIsNone(self.access.get_tool_usage(access, 'attacker', 'victim', 'intruderKicker'))
        self.assertEqual(self.use().status_code, 200)

    def test_concurrent_use_moves_once(self):
        from concurrent.futures import ThreadPoolExecutor
        self.prepare()
        before = self.positions.get('victim')['version']
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run.execute_intruder_kicker('attacker', 'victim'), range(2)))
        self.assertEqual(sum(bool(result[0].get('duplicate')) for result in results), 1)
        self.assertEqual(self.positions.get('victim')['version'], before + 1)

    def test_actor_refresh_uses_canonical_position_after_kick(self):
        self.prepare()
        record = self.users.get_profile_with_revision('victim')
        self.users.patch_profile_guarded('victim', {'clan': '', 'ghost_clan_code': ''},
                                        source='test.map_fixture', expected_revision=record['profile_revision'])
        stale = {'username': 'victim', 'nick': 'Victim', 'clan': 'foreign',
                 'current_position': {'lat': 52.2, 'lng': 21.0}}
        with patch.object(self.users, 'get_profile', return_value={'username': 'attacker', 'clan': 'owner'}), \
             patch.object(self.users, 'list_profiles', return_value=[stale]), \
             patch.object(run.mail_store, 'list_accepted_contacts', return_value=[]), \
             patch.object(run.mail_store, 'list_pending_contact_names', return_value=[]), \
             patch.object(run, 'get_profile_clan', side_effect=lambda profile: profile.get('clan')), \
             patch.object(run, 'build_territory_engagement_visibility_context', return_value={}), \
             patch.object(run, 'project_territory_actor_visibility', side_effect=lambda *a, **kw: {'visible': False, 'combat_relation': 'hostile'}):
            before = self.client.get('/api/map/player-actors')
            self.assertEqual(before.status_code, 200, before.get_json())
            self.assertEqual(len(before.json['player_actors']), 1)
            self.assertEqual(self.use().status_code, 200)
            after = self.client.get('/api/map/player-actors')
            self.assertEqual(after.json['player_actors'], [])
