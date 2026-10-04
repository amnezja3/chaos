import unittest
from unittest.mock import patch
from contextlib import ExitStack
from datetime import datetime

import run
from tests.test_player_hack_read_paths import PlayerHackReadPathsTest


class ScanMarkerCategoriesTest(unittest.TestCase):
    setUp = PlayerHackReadPathsTest.setUp

    def scan(self, tags, marked=(), hour=12):
        poi = dict(lat=52.0, lon=21.0, name='Test', osm_id=123, tags=tags)
        with ExitStack() as stack:
            clock = stack.enter_context(patch.object(run, 'datetime', wraps=datetime))
            clock.now.return_value = datetime(2026, 10, 4, hour, 0)
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
                self.assertTrue(any(m['source_type'] == 'atm' for m in markers))
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

    def test_shop_clients_and_cameras_survive_every_hour_and_attached_atm(self):
        for hour in (0, 7, 8, 20, 21, 23):
            for tags in ({'shop': 'clothes'}, {'shop': 'convenience', 'atm': 'yes'}):
                with self.subTest(hour=hour, tags=tags):
                    markers = self.scan(tags, hour=hour)
                    clients = [m for m in markers if m['name'] == 'Klient']
                    self.assertGreaterEqual(len(clients), 3)
                    self.assertLessEqual(len(clients), 8)
                    self.assertTrue(all(m['target_type'] == 'person' for m in clients))
                    cameras = [m for m in markers if m['name'] == 'Kamera sklepu']
                    self.assertGreaterEqual(len(cameras), 2)
                    self.assertLessEqual(len(cameras), 4)
                    if tags.get('atm'):
                        self.assertTrue(any(m['name'] == 'Kamera bankomatu' for m in markers))
                        camera_ids = [m['camera_id'] for m in markers if m['source_type'] == 'camera']
                        self.assertEqual(len(camera_ids), len(set(camera_ids)))

    def test_all_scene_types_match_their_creator_actions(self):
        from creator_policy import RECIPES, supports_target_type
        cases = [({'shop': 'books'}, 'Klient', ['trace_device', 'mic_sniff']),
                 ({'amenity': 'restaurant'}, 'Gość restauracji', ['trace_device', 'mic_sniff']),
                 ({'amenity': 'atm'}, 'Test', ['atm_logs', 'install_sniffer']),
                 ({'amenity': 'atm'}, 'Kamera bankomatu', ['camera_stream', 'camera_shutdown']),
                 ({'amenity': 'parking'}, 'Auto: 🚘 Tesla', ['car_hack', 'trace_gps']),
                 ({'shop': 'books'}, 'Test', ['scan_ports', 'exploit', 'sniff', 'trace']),
                 ({'amenity': 'bicycle_parking'}, 'Stacja rowerowa', ['scan_ports', 'exploit', 'sniff', 'trace']),
                 ({'amenity': 'parcel_locker'}, 'Kuriero-bot', ['scan_ports', 'exploit', 'sniff', 'trace']),
                 ({'amenity': 'car_wash'}, 'Test', ['scan_ports', 'exploit', 'sniff', 'trace']),
                 ({'amenity': 'parking'}, 'Test', ['scan_ports', 'exploit', 'sniff', 'trace'])]
        for tags, name, actions in cases:
            with self.subTest(tags=tags, name=name):
                marker = next(m for m in self.scan(tags) if m['name'] == name)
                for action in actions:
                    self.assertTrue(supports_target_type(RECIPES[action], marker['target_type']), (action, marker))

    def test_marked_shop_keeps_its_scene(self):
        markers = self.scan({'shop': 'clothes'}, [{'lat': 52., 'lng': 21.}], hour=23)
        self.assertTrue(any(m['name'] == 'Klient' for m in markers))
        self.assertTrue(any(m['name'] == 'Kamera sklepu' for m in markers))
        self.assertFalse(any(not m['generated'] for m in markers))

    def test_legacy_markers_and_editions_keep_correct_target_support(self):
        from creator_policy import supports_target_type
        for source, name, expected in [('shop_clothes', 'Klient', 'person'),
                ('atm', 'Osoba przy bankomacie', 'person'),
                ('restaurant', 'Gość restauracji', 'person'),
                ('parking', 'Auto: 🚘 Tesla', 'vehicle')]:
            self.assertEqual(run.infer_target_type_from_target(dict(source_type=source, name=name, generated=True)), expected)
        self.assertTrue(supports_target_type({'action': 'scan_ports', 'target_types': ['poi']}, 'venue'))
        self.assertTrue(supports_target_type({'action': 'install_sniffer', 'target_types': ['poi']}, 'atm'))
        self.assertFalse(supports_target_type({'action': 'atm_logs', 'target_types': ['atm']}, 'venue'))
        self.assertFalse(supports_target_type({'action': 'car_hack', 'target_types': ['vehicle']}, 'venue'))
        self.assertFalse(supports_target_type({'action': 'scan_ports', 'target_types': ['poi']}, 'person'))


if __name__ == '__main__':
    unittest.main()
