import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError
from poi_infrastructure.world_contract import ContractError
from tools.world_discovery_probe import capture


class ProbeTests(unittest.TestCase):
    def test_dry_run_needs_no_database_or_secret_and_never_calls(self):
        transport = Mock(side_effect=AssertionError('network'))
        result = capture('nonexistent', transport=transport)
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(result['max_network_calls'], 1)
        transport.assert_not_called()

    def test_acceptance_and_key_required_before_network(self):
        with self.assertRaisesRegex(ContractError, 'acceptance_required'):
            capture('missing', execute=True)
        with patch.dict(os.environ, {'CHAOS_MAPLARK_API_KEY': ''}), \
                self.assertRaisesRegex(ContractError, 'secret_missing'):
            capture('missing', execute=True, accept_variable_credit_cost=True)

    def test_one_capture_shared_rate_and_no_world_store(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CHAOS_MAPLARK_API_KEY': 'synthetic-only'}):
            path = Path(tmp) / 'poi.sqlite3'
            repo = Repository(path); repo.initialize()
            transport = Mock(return_value=(200, None, {
                'response_headers': {'X-Returned': '0', 'X-Has-More': 'false'},
                'body': {'type': 'FeatureCollection', 'features': []}}))
            result = capture(path, Path(tmp)/'one', execute=True,
                             accept_variable_credit_cost=True, transport=transport)
            self.assertEqual(result['status'], 'captured_not_approved')
            self.assertFalse(result['inspection']['gameplay_approved'])
            transport.assert_called_once()
            self.assertTrue((Path(tmp)/'one/body.json').is_file())
            self.assertIsNotNone(repo.acquire('@upstream', 1))
            with self.assertRaisesRegex(POIError, 'controlled_scan_rate_limited'):
                capture(path, Path(tmp)/'two', execute=True,
                        accept_variable_credit_cost=True, transport=transport)
            self.assertEqual(transport.call_count, 1)
            c = repo.connect()
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cache').fetchone()[0], 0)
            c.close()
