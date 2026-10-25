from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
import unittest

import test_world_discovery_worker as fixtures
from poi_infrastructure.routing import Routing
from tools.world_activation_readiness import inspect


class ActivationReadinessTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def dump(self):
        with closing(self.repo.connect()) as c:
            return '\n'.join(c.iterdump())

    def test_report_preserves_database_and_saved_empty_route(self):
        routing = Routing(self.repo)
        routing.initialize()
        routing.save('roads', 'background', 0, [], 'fixture')
        before = self.dump()
        result = inspect(self.repo.path)
        self.assertEqual(before, self.dump())
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(result['production_writes'], 0)
        route = next(r for r in result['routes'] if (r['layer'], r['lane']) == ('roads', 'background'))
        self.assertEqual(route['chain'], [])
        maplark, geo = result['collection']
        self.assertIn('review_shorter_than_requested_retention', maplark['blockers'])
        self.assertIn('provider_missing', geo['blockers'])
        self.assertFalse(maplark['execution_authorized'])

    def test_uncertain_expired_cost_is_not_available_credit(self):
        now = time.time()
        self.ledger.configure_window('geoapify', 'expired', now - 100, now - 10, 20)
        self.ledger.reserve('geoapify', 'old', 5, now=now - 50)
        self.ledger.settle('geoapify', 'old')
        before = self.dump()
        result = inspect(self.repo.path)
        self.assertEqual(before, self.dump())
        geo = result['collection'][1]
        self.assertIn('previous_period_unresolved_requires_explicit_carry_forward', geo['blockers'])
        budget = next(b for b in result['budgets'] if b['account'] == 'geoapify')
        self.assertEqual(budget['lifetime_operations']['uncertain_reserved'], 5)

    def test_all_missing_scopes_reported_without_exposing_evidence(self):
        self.provider.update(scopes=['small_probe'], evidence=None, enabled=False)
        self.save_provider()
        row = inspect(self.repo.path)['collection'][0]
        for scope in ('storage', 'world_storage', 'background_refresh'):
            self.assertIn('scope_required:' + scope, row['blockers'])
        self.assertIn('storage_reference_required', row['blockers'])
        self.assertNotIn('evidence', row)

    def test_missing_or_wrong_database_is_not_initialized(self):
        path = Path(self.tmp.name) / 'missing.sqlite3'
        with self.assertRaises(ValueError):
            inspect(path)
        self.assertFalse(path.exists())
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE users(id)')
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            inspect(path)
        self.assertEqual(before, path.read_bytes())

    def test_review_and_budget_do_not_claim_permission_to_execute(self):
        self.provider['review_due_at'] = time.time() + 8 * 86400
        self.save_provider()
        row = inspect(self.repo.path)['collection'][0]
        self.assertEqual(row['blockers'], [])
        self.assertFalse(row['execution_authorized'])
        self.assertIn('bounded_permit', row['still_required'])
