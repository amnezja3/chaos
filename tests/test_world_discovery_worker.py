from contextlib import closing
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.discovery_jobs import DiscoveryJobs
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.discovery_worker import DiscoveryPermit, DiscoveryWorker
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.upstream_priority import UpstreamPriority
from poi_infrastructure.world_storage import CanonicalWorldRepository


class DiscoveryWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name) / 'poi.sqlite3')
        self.jobs = DiscoveryJobs(self.repo)
        self.jobs.initialize()
        Registry(self.repo).initialize()
        CanonicalWorldRepository(self.repo).initialize_canonical()
        self.ledger = CreditBudget(self.repo)
        self.ledger.initialize()
        self.ledger.configure_window('maplark', 'test', time.time()-1, time.time()+3600, 100)
        self.provider = dict(id='maplark', revision=1, enabled=True,
            url='https://api.maplark.com/v3/osm_features', operator_group='api.maplark.com',
            technical_status='tested_ok', policy_status='approved_for_defined_use',
            scopes=['storage', 'world_storage', 'background_refresh'],
            evidence={'reference': 'offline-test'}, review_due_at=time.time()+3600)
        self.save_provider()
        DemandQueue(self.repo).record(21, 52, ['roads'])
        with closing(self.repo.connect()) as c:
            demand = c.execute('SELECT key FROM world_discovery_demand').fetchone()[0]
        self.key = self.jobs.enqueue(demand, 'maplark', 1, 'roads')
        self.permit = DiscoveryPermit(frozenset({(2100, 5200)}), frozenset({'roads'}), time.time()+3600)
        self.transport = Mock(return_value=(200, None, dict(response_headers={
            'X-Usage-Units-Charged': '3', 'X-Returned': '0', 'X-Has-More': 'false'},
            body={'type': 'FeatureCollection', 'features': []})))
        self.enabled = True
        self.worker = DiscoveryWorker(self.repo, self.permit,
            enabled=lambda: self.enabled, transport=self.transport)
        env = patch.dict(os.environ, CHAOS_MAPLARK_API_KEY='fixture',
            CHAOS_POI_PRIORITY_ENABLED='1', CHAOS_MAPLARK_ACCEPT_VARIABLE_COST='1')
        env.start()
        self.addCleanup(env.stop)

    def save_provider(self):
        with self.repo.transaction() as c:
            c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',
                      ('maplark', self.provider['revision'], json.dumps(self.provider)))

    def test_disabled_is_noop(self):
        worker = DiscoveryWorker(self.repo, self.permit, transport=self.transport)
        self.assertEqual(worker.run_one()['status'], 'disabled')
        self.assertEqual(self.jobs.get(self.key)['state'], 'PENDING')
        self.transport.assert_not_called()

    def test_commit_once_no_coverage_no_neighbors(self):
        result = self.worker.run_one()
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(result['coverage'], 'UNKNOWN')
        self.assertEqual(result['network_calls'], 1)
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.transport.assert_called_once()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)
        with closing(self.repo.connect()) as c:
            payload = json.loads(c.execute('SELECT payload FROM world_snapshot').fetchone()[0])
            self.assertNotIn('coverage', payload)
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_demand').fetchone()[0], 1)

    def test_scope_or_revision_blocks_before_http(self):
        self.provider['scopes'].remove('background_refresh')
        self.save_provider()
        self.assertEqual(self.worker.run_one()['status'], 'policy_blocked')
        self.transport.assert_not_called()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)

    def test_outside_permit_never_fetches(self):
        self.worker.permit = DiscoveryPermit(frozenset({(0, 0)}), frozenset({'roads'}), time.time()+60)
        self.assertEqual(self.worker.run_one()['status'], 'policy_blocked')
        self.transport.assert_not_called()

    def test_live_waiter_defers_without_charge(self):
        UpstreamPriority(self.repo).register()
        self.assertEqual(self.worker.run_one()['status'], 'deferred')
        self.assertEqual(self.jobs.get(self.key)['state'], 'DEFERRED')
        self.transport.assert_not_called()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)

    def test_exhausted_budget_never_calls_transport(self):
        self.ledger.reserve('maplark', 'existing-use', 100)
        self.ledger.settle('maplark', 'existing-use', 100)
        self.assertEqual(self.worker.run_one()['status'], 'deferred')
        self.transport.assert_not_called()

    def test_priority_required_before_claim(self):
        with patch.dict(os.environ, CHAOS_POI_PRIORITY_ENABLED='0'):
            self.assertEqual(self.worker.run_one()['status'], 'priority_required')
        self.assertEqual(self.jobs.get(self.key)['state'], 'PENDING')
        self.transport.assert_not_called()

    def test_partial_response_is_not_published_or_retried(self):
        self.transport.return_value[2]['response_headers']['X-Has-More'] = 'true'
        self.assertEqual(self.worker.run_one()['status'], 'reconciliation_required')
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0], 0)
        self.transport.assert_called_once()

    def test_timeout_quarantines_and_retains_unknown_cost(self):
        self.transport.side_effect = TimeoutError('fixture')
        self.assertEqual(self.worker.run_one()['status'], 'reconciliation_required')
        self.assertEqual(self.jobs.get(self.key)['state'], 'POLICY_BLOCKED')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 20)
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.transport.assert_called_once()

    def test_revocation_after_http_prevents_publication_but_preserves_charge(self):
        response = self.transport.return_value
        def revoke(*args, **kwargs):
            self.provider['revision'] = 2
            self.save_provider()
            return response
        self.transport.side_effect = revoke
        self.assertEqual(self.worker.run_one()['status'], 'reconciliation_required')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0], 0)

    def test_stop_after_http_never_refunds_charge(self):
        response = self.transport.return_value
        def stop(*args, **kwargs):
            self.enabled = False
            return response
        self.transport.side_effect = stop
        self.assertEqual(self.worker.run_one()['status'], 'reconciliation_required')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)

    def test_crash_after_publication_ack_recovers_without_fetch(self):
        with patch.object(self.worker.jobs, 'acknowledge', side_effect=RuntimeError('crash')):
            self.assertEqual(self.worker.run_one()['status'], 'reconciliation_required')
        with closing(self.repo.connect()) as c:
            snapshot = c.execute('SELECT id FROM world_snapshot').fetchone()[0]
        self.assertTrue(DiscoveryJobs(self.repo).acknowledge(self.key, snapshot))
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.transport.assert_called_once()

    def test_invalid_permits_rejected_before_claim(self):
        for permit in (
                DiscoveryPermit(frozenset({(0, 0)}), frozenset({'land_water'}), time.time()+60),
                DiscoveryPermit(frozenset({(0, 0)}), frozenset({'roads'}), time.time()-1)):
            self.worker.permit = permit
            with self.assertRaises(ValueError): self.worker.run_one()
        self.assertEqual(self.jobs.get(self.key)['state'], 'PENDING')
        self.transport.assert_not_called()
