from pathlib import Path
from contextlib import closing
import tempfile
import time
import unittest
from unittest.mock import patch

from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError, UpstreamUnavailable
from tools.poi_controlled_scan import scan


class ControlledScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'poi.sqlite3'
        self.repo = Repository(self.path)
        self.registry = Registry(self.repo)
        self.registry.initialize()
        p = self.registry.save('fixture', 0, dict(name='Fixture',
            url='https://example.org/api/interpreter', operator_group='example.org', priority=1), 'test')
        p = self.registry.decision(p['id'], p['revision'], 'approved_for_defined_use',
            ['small_probe'], dict(source_url='https://example.org/terms', reference='fixture',
                                 notes='diagnostic only'), time.time()+86400, 'test')
        self.registry.tested(p['id'], p['revision'], True, 'test')

    def test_dry_run_and_single_request_preserve_registry_and_no_poi_storage(self):
        before = self.registry.list()
        with patch('tools.poi_controlled_scan.bounded_http', return_value=(200, None,
                {'elements': [{'type':'node', 'id':1, 'lat':52.2319, 'lon':21.0067}]})) as http:
            self.assertEqual(scan(self.path, 'fixture')['status'], 'dry_run')
            http.assert_not_called()
            result = scan(self.path, 'fixture', True)
            self.assertEqual(result['elements'], 1)
            self.assertEqual(http.call_args.args[3], 25)
            self.assertIn('around:300,52.2319,21.0067', http.call_args.args[2])
            self.assertIn('[timeout:25]', http.call_args.args[2])
            self.assertTrue(http.call_args.kwargs['secure'])
            with self.assertRaisesRegex(POIError, 'rate_limited'):
                scan(self.path, 'fixture', True)
            http.assert_called_once()
        self.assertEqual(self.registry.list(), before)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM cache').fetchone()[0], 0)
        self.assertIsNotNone(self.repo.acquire('@upstream', 1))

    def test_timeout_records_failure_and_releases_slot(self):
        with patch('tools.poi_controlled_scan.bounded_http', side_effect=UpstreamUnavailable('http_read_timeout')):
            with self.assertRaisesRegex(POIError, 'http_read_timeout'):
                scan(self.path, 'fixture', True)
        self.assertEqual(self.registry.health()[0]['status'], 'http_read_timeout')
        self.assertIsNotNone(self.repo.acquire('@upstream', 1))

    def test_simple_query_and_error_detail_do_not_retry(self):
        detail = {'body_excerpt':'upstream unavailable'}
        with patch('tools.poi_controlled_scan.bounded_http', return_value=(502, None, detail)) as http:
            result = scan(self.path, 'fixture', True, 'simple')
            self.assertEqual(result['diagnostic'],detail)
            self.assertEqual(result['query_kind'],'simple')
            self.assertTrue(http.call_args.args[0].diagnostic_errors)
            self.assertIn('node(around:300,52.2319,21.0067)["amenity"]',http.call_args.args[2])
            self.assertNotIn('nwr',http.call_args.args[2])
            http.assert_called_once()

    def test_partial_response_never_passes(self):
        with patch('tools.poi_controlled_scan.bounded_http', return_value=(200, None,
                {'elements': [], 'remark':'runtime error'})):
            with self.assertRaisesRegex(POIError, 'invalid_response'):
                scan(self.path, 'fixture', True)
        self.assertEqual(self.registry.health()[0]['status'], 'invalid_response')


if __name__ == '__main__':
    unittest.main()
