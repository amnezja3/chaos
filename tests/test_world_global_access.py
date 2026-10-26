"""Real SQLite and router, mocked provider boundary; never calls a provider."""
import os
import time
import unittest
from unittest.mock import patch

import test_world_shadow as shadow_fixture
import test_world_routing as router_fixture
from poi_infrastructure.service import Service, Config, POIError
from poi_infrastructure.world_access import allowed


class GlobalWorldTests(unittest.TestCase):
    def setUp(self):
        shadow_fixture.WorldShadowTests.setUp(self)
        env = patch.dict(os.environ, CHAOS_POI_WORLD_ACCESS_MODE='global',
                         CHAOS_POI_ROUTING_ENABLED='1', CHAOS_POI_SCAN_NETWORK_PAUSED='0')
        env.start(); self.addCleanup(env.stop)
        self.options['_world_pilot_user'] = 'account-a'
        self.grant()

    fetch = shadow_fixture.WorldShadowTests.fetch
    grant = shadow_fixture.WorldShadowTests.grant
    evict_cache = shadow_fixture.WorldShadowTests.evict_cache
    route = router_fixture.RoutingTests.route
    overpass = router_fixture.RoutingTests.overpass

    def test_general_access_does_not_modify_pilot_or_accept_unknown_mode(self):
        self.assertTrue(allowed('account-b', self.options['_spatial']))
        for mode in ('pilot', 'off', '', 'globla'):
            with self.subTest(mode=mode), patch.dict(os.environ, CHAOS_POI_WORLD_ACCESS_MODE=mode):
                self.assertFalse(allowed('account-b', self.options['_spatial']))

    def test_maplark_second_account_and_independent_workers_read_world(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})) as http:
            expected = self.fetch()
            self.evict_cache()
            with self.service.repo.transaction() as c:
                before = [tuple(row) for row in c.execute('SELECT * FROM world_credit_operation')]
                times = [tuple(row) for row in c.execute('SELECT fetched,fresh_until,usable_until FROM world_snapshot')]
            self.options['_world_pilot_user'] = 'account-b'
            with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
                for _ in range(4):
                    independent = Service(path=self.service.repo.path, config=Config(join_wait=0))
                    self.assertEqual(independent.fetch('irrelevant legacy query', [], 8, 300, 1800, self.options), expected)
            http.assert_called_once()
            with self.service.repo.transaction() as c:
                self.assertEqual(before, [tuple(row) for row in c.execute('SELECT * FROM world_credit_operation')])
                self.assertEqual(times, [tuple(row) for row in c.execute('SELECT fetched,fresh_until,usable_until FROM world_snapshot')])

    def test_pause_without_local_data_does_not_call_network(self):
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'), patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark', side_effect=AssertionError('HTTP forbidden')):
            with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                self.fetch()

    def test_general_mode_still_respects_read_and_ingest_switches(self):
        with patch.dict(os.environ, CHAOS_POI_WORLD_INGEST_ENABLED='0'), patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        self.assertEqual(self.world.status()['snapshots'], 0)
        self.evict_cache()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        self.evict_cache()
        with patch.dict(os.environ, CHAOS_POI_WORLD_REPOSITORY_ENABLED='0', CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                self.fetch()
        self.assertEqual(self.world.status()['snapshots'], 1)

    def test_overpass_exact_world_preserves_markers_and_order_without_http(self):
        p = self.overpass()
        p = self.registry.decision(p['id'], p['revision'], 'approved_for_defined_use',
            ['normal_scan', 'storage', 'world_storage'],
            dict(source_url='https://example.org/terms', reference='fixture with spaces', notes='test'),
            time.time()+3600, 'test')
        self.registry.enable(p['id'], p['revision'], True, 'test')
        self.route(['overpass'])
        data = {'elements': [
            {'type': 'way', 'id': 8, 'center': {'lat': 52.01, 'lon': 21.01}, 'tags': {'shop': 'yes'}},
            {'type': 'node', 'id': 1, 'lat': 52, 'lon': 21, 'tags': {'amenity': 'bank'}}]}
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200, None, data)) as http:
            self.assertEqual(self.fetch(), data)
            self.assertEqual(self.world.status()['snapshots'], 1)
            self.evict_cache()
            with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
                self.assertEqual(self.fetch(), data)
            http.assert_called_once()

    def test_empty_maplark_result_is_reusable(self):
        from dataclasses import replace
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(replace(self.batch, objects=()), {})) as http:
            self.assertEqual(self.fetch(), {'elements': []})
            self.evict_cache()
            self.assertEqual(self.fetch(), {'elements': []})
            http.assert_called_once()

    def test_general_mode_does_not_bypass_provider_revocation(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        self.evict_cache()
        p = self.registry.list()[0]
        self.registry.enable(p['id'], p['revision'], False, 'test')
        with self.assertRaises(POIError):
            self.fetch()

    def test_world_age_does_not_refresh_and_expired_data_cannot_answer(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        self.evict_cache()
        base = time.time()
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'), patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark', side_effect=AssertionError('HTTP forbidden')):
            with patch('time.time', return_value=base+301):
                self.assertEqual(len(self.fetch()['elements']), 1)
            with patch('time.time', return_value=base+1801):
                with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                    self.fetch()

    def test_changed_query_is_not_answered_by_exact_snapshot(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        self.evict_cache()
        self.options['_spatial']['lon'] += .001
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                self.fetch()

    def test_general_retention_does_not_extend_scan_freshness(self):
        import json
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark', return_value=(self.batch, {})):
            self.fetch()
        with self.service.repo.transaction() as c:
            row = c.execute('SELECT payload,fresh_until,usable_until FROM world_snapshot').fetchone()
        raw = json.loads(row['payload'])
        self.assertGreater(raw['retain_until'], row['usable_until'])
        self.assertLessEqual(raw['retain_until'], self.registry.list()[0]['review_due_at'])
        self.assertLessEqual(row['fresh_until']-time.time(), 300)
        self.assertLessEqual(row['usable_until']-time.time(), 1800)

    def test_legacy_route_honors_network_pause_too(self):
        from unittest.mock import Mock
        transport = Mock(side_effect=AssertionError('HTTP forbidden'))
        legacy = Service(path=self.service.repo.path, config=Config(join_wait=0), transport=transport)
        with patch.dict(os.environ, CHAOS_POI_ROUTING_ENABLED='0',
                        CHAOS_POI_WORLD_INGEST_ENABLED='0', CHAOS_POI_WORLD_REPOSITORY_ENABLED='0',
                        CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                legacy.fetch('legacy-query', ['https://example.org/api/interpreter'], 8, 300, 1800)
        transport.assert_not_called()
