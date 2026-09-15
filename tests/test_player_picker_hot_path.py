import unittest
from unittest.mock import patch
import run
import test_player_target_selection as selection
from database import PlayerMarkedTargetStore, db_connect


class PlayerPickerHotPathTest(unittest.TestCase):
    setUp = selection.PlayerTargetSelectionTest.setUp
    seed = selection.PlayerTargetSelectionTest.seed
    prepare = selection.PlayerTargetSelectionTest.prepare
    setup_selection = selection.PlayerTargetSelectionTest.setup_selection
    mark = selection.PlayerTargetSelectionTest.mark

    def test_heavy_tracked_target_uses_current_distance_without_allowing_reselection(self):
        self.setup_selection(heavy=True)
        self.assertEqual(self.mark().status_code, 200)
        self.positions.upsert('victim', {'lat': 53, 'lng': 22})
        self.stack.enter_context(patch.object(run, 'player_marked_target_store', PlayerMarkedTargetStore(self.path)))
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full read')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            response = self.client.get('/api/victim-picker/candidates')
            self.assertEqual(response.status_code, 200, response.get_json())
            actor = next(item for item in response.json['candidates'] if item['target_id'] == 'player:victim')
            self.assertEqual(actor['lat'], 53)
            self.assertGreater(actor['distance_m'], 1000)
            self.assertTrue(actor['is_active_target'])
            self.assertFalse(actor['can_aim'])
            self.assertEqual(self.client.post('/api/victim-picker/aim', json={'target_id': 'player:victim'}).status_code, 409)
        self.assertEqual(self.targets.get_active_target('attacker')['target_id'], 'player:victim')

    def test_alternate_map_selection_cannot_bypass_visibility(self):
        self.setup_selection()
        self.positions.upsert('victim', {'lat': 53, 'lng': 22})
        response = self.client.post('/api/map/aim-target', json={
            'target_mode': 'player', 'target_username': 'victim', 'lat': 52.2, 'lng': 21,
            'label': 'victim', 'security': {'firewall': False},
        })
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(self.targets.get_active_target('attacker'), {})
