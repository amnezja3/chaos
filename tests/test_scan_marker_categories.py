import unittest
from unittest.mock import patch
from contextlib import ExitStack

import run
from tests.test_player_hack_read_paths import PlayerHackReadPathsTest


class ScanMarkerCategoriesTest(unittest.TestCase):
    setUp = PlayerHackReadPathsTest.setUp

    def scan(self, tags, marked=()):
        poi = dict(lat=52.0, lon=21.0, name='Test', osm_id=123, tags=tags)
        with ExitStack() as stack:
            for obj, method, result in [
                (run.player_position_store, 'get_position', {'lat': 52., 'lng': 21.}),
                (run.capability_projection_store, 'get_capabilities', {'action_range': 5000}),
                (run.identity_projection_store, 'get_identity', None),
                (run.player_marked_target_store, 'list_targets', list(marked)),
                (run.player_scan_snapshot_store, 'record', {'scan_id': 'scan-test'}),
                (run.fetcher, 'get_all', [poi]),
                (run, 'foreign_territory_action_block', None),
            ]:
                stack.enter_context(patch.object(obj, method, return_value=result))
            stack.enter_context(patch.object(run, 'sync_session_profile', side_effect=AssertionError('heavy profile')))
            response = self.client.post('/map-action', json={'action': 'scan', 'lat': 52., 'lng': 21.})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['markers']

    def test_standalone_and_attached_atm_have_camera_and_people(self):
        for tags in ({'amenity': 'atm'}, {'amenity': 'bank', 'atm': 'yes'}):
            with self.subTest(tags=tags):
                markers = self.scan(tags)
                self.assertEqual(markers[0]['source_type'], 'atm')
                camera = next(m for m in markers if m['source_type'] == 'camera')
                self.assertEqual(camera['target_type'], 'camera')
                self.assertTrue(camera['camera_id'])
                self.assertEqual(camera['scan_id'], 'scan-test')
                self.assertTrue(any(m['target_type'] == 'person' for m in markers))

    def test_marked_atm_still_generates_camera_without_duplicate_parent(self):
        markers = self.scan({'amenity': 'atm'}, [{'lat': 52., 'lng': 21.}])
        self.assertFalse(any(m['source_type'] == 'atm' for m in markers))
        self.assertTrue(any(m['source_type'] == 'camera' for m in markers))

    def test_parking_produces_vehicles_not_vehicle_parents(self):
        markers = self.scan({'amenity': 'parking'})
        self.assertEqual(markers[0]['source_type'], 'parking')
        self.assertNotEqual(markers[0]['target_type'], 'vehicle')
        self.assertEqual(len([m for m in markers if m['target_type'] == 'vehicle']), 4)

    def test_wash_and_bicycle_parking_are_not_cars(self):
        for category in ('car_wash', 'bicycle_parking'):
            self.assertTrue(all(m['target_type'] != 'vehicle' for m in self.scan({'amenity': category})))

    def test_generic_shop_keeps_cameras_and_surveillance_is_recognized(self):
        self.assertGreaterEqual(len([m for m in self.scan({'shop': 'convenience'}) if m['source_type'] == 'camera']), 2)
        camera = self.scan({'man_made': 'surveillance'})[0]
        self.assertEqual(camera['target_type'], 'camera')
        self.assertTrue(camera['camera_id'])


if __name__ == '__main__':
    unittest.main()
