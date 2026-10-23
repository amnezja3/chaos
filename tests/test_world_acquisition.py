import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError, UpstreamUnavailable
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import ContractError


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name) / 'poi.sqlite3')
        self.ledger = CreditBudget(self.repo)
        self.ledger.initialize()
        self.ledger.configure_window('maplark', 'pilot', time.time()-60, time.time()+3600, 100)
        self.plan = plan_maplark(52, 21, 300, limit=1000)
        env = patch.dict('os.environ', {'CHAOS_MAPLARK_API_KEY': 'test-secret'})
        env.start(); self.addCleanup(env.stop)

    def response(self, cost='9', status=200, body=None):
        return status, None, {'response_headers': {
            'X-Usage-Units-Charged': cost, 'X-Returned': '0', 'X-Has-More': 'false'},
            'body': body if body is not None else {'type': 'FeatureCollection', 'features': []}}

    def call(self, transport, operation='op1', **kwargs):
        return acquire_maplark(self.repo, self.plan, operation, 20,
            accept_variable_cost=True, transport=transport, **kwargs)

    def test_one_send_settles_actual_and_never_approves_gameplay(self):
        transport = Mock(return_value=self.response())
        batch, bill = self.call(transport)
        self.assertEqual(bill['reported_credits'], 9)
        self.assertFalse(bill['gameplay_approved'])
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 9)
        with self.assertRaises(ContractError):
            batch.export_overpass()
        with self.assertRaisesRegex(ContractError, 'already_used'):
            self.call(transport)
        transport.assert_called_once()

    def test_http_error_still_charged_no_retry(self):
        transport = Mock(return_value=self.response(status=500))
        with self.assertRaisesRegex(POIError, 'http_500'):
            self.call(transport)
        transport.assert_called_once()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 9)

    def test_bad_body_still_charged(self):
        with self.assertRaises(ContractError):
            self.call(Mock(return_value=self.response(body={'broken': True})))
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 9)

    def test_timeout_keeps_reservation_and_releases_slot(self):
        with self.assertRaises(UpstreamUnavailable):
            self.call(Mock(side_effect=UpstreamUnavailable('deadline')))
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 20)
        slot = self.repo.acquire('@upstream', 42)
        self.assertIsNotNone(slot)
        self.repo.release('@upstream', slot)

    def test_unknown_charge_never_becomes_zero(self):
        _, bill = self.call(Mock(return_value=self.response(cost='unknown')))
        self.assertEqual(bill['billing_state'], 'uncertain')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 20)

    def test_overcharge_stops_next_call(self):
        self.call(Mock(return_value=self.response(cost='21')))
        transport = Mock()
        with self.assertRaisesRegex(ContractError, 'account_held'):
            self.call(transport, operation='op2')
        transport.assert_not_called()

    def test_busy_or_budget_exhausted_never_send(self):
        transport = Mock()
        slot = self.repo.acquire('@upstream', 42)
        with self.assertRaisesRegex(POIError, 'upstream_busy'):
            self.call(transport)
        self.repo.release('@upstream', slot)
        self.ledger.reserve('maplark', 'other', 100)
        with self.assertRaisesRegex(ContractError, 'budget_exhausted'):
            self.call(transport)
        transport.assert_not_called()

    def test_cancel_before_send_releases_reservation(self):
        transport = Mock()
        with self.assertRaisesRegex(POIError, 'scanner_inactive'):
            self.call(transport, still_active=Mock(side_effect=[True, False]))
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)
        transport.assert_not_called()
