from contextlib import closing
from dataclasses import replace
import time
import unittest

import test_world_discovery_worker as fixtures
from poi_infrastructure.discovery_producer import prepare_jobs
from poi_infrastructure.discovery_queue import DemandQueue


class ProducerTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def add_demand(self):
        DemandQueue(self.repo).record(21.02, 52, ['roads', 'waterways', 'poi'])
        DemandQueue(self.repo).record(22, 53, ['roads'])
        self.permit = replace(self.permit, cells=frozenset({(2100,5200), (2102,5200)}))

    def test_plan_does_not_write_or_fetch_then_apply_deduplicates(self):
        self.add_demand()
        result = prepare_jobs(self.repo, self.permit)
        self.assertEqual(len(result['jobs']), 1)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0], 1)
        result = prepare_jobs(self.repo, self.permit, apply=True)
        self.assertEqual(len(result['jobs']), 1)
        self.assertEqual(prepare_jobs(self.repo, self.permit, apply=True)['jobs'], [])
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)
        self.transport.assert_not_called()

    def test_expired_demand_and_revoked_policy_produce_nothing(self):
        self.add_demand()
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_demand SET expires=?', (time.time()-1,))
        self.assertEqual(prepare_jobs(self.repo, self.permit, apply=True)['jobs'], [])
        self.provider['scopes'].remove('background_refresh')
        self.save_provider()
        self.assertEqual(prepare_jobs(self.repo, self.permit)['status'], 'policy_blocked')

    def test_missing_budgets_fail_before_enqueue(self):
        self.add_demand()
        with self.assertRaises(ValueError):
            prepare_jobs(self.repo, replace(self.permit, budget_id='missing'), apply=True)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0], 1)

    def test_small_batches_progress_without_resetting_existing_jobs(self):
        self.add_demand()
        DemandQueue(self.repo).record(21.03, 52, ['roads'])
        self.permit = replace(self.permit, cells=self.permit.cells | {(2103,5200)})
        self.assertEqual(len(prepare_jobs(self.repo, self.permit, apply=True, limit=1)['jobs']), 1)
        self.assertEqual(len(prepare_jobs(self.repo, self.permit, apply=True, limit=1)['jobs']), 1)
        self.assertEqual(prepare_jobs(self.repo, self.permit, apply=True, limit=1)['jobs'], [])
