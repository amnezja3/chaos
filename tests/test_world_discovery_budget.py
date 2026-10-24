from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import tempfile
import time
import unittest

from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_contract import ContractError


class ScopedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name) / 'budget.sqlite3')
        self.budget = CreditBudget(self.repo)
        self.budget.initialize()
        self.budget.configure_recurring('maplark', 800, 24000)
        self.start, self.end = time.time()-1, time.time()+3600
        self.scopes = ('discovery:pilot', 'discovery:pilot:roads')
        for scope, cap in zip(self.scopes, (40, 20)):
            self.budget.configure_scope('maplark', scope, self.start, self.end, cap)

    def test_concurrent_last_layer_reservation_is_atomic(self):
        def reserve(i):
            try:
                return self.budget.reserve('maplark', 'request:'+str(i), 20, scopes=self.scopes)
            except ContractError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(reserve, range(4)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.budget.status('maplark')[0]['committed'], 20)
        self.assertEqual(self.budget.scope_status('maplark', self.scopes[0])['committed'], 20)

    def test_uncertain_and_settlement_share_single_ledger_after_restart(self):
        self.budget.reserve('maplark', 'one', 20, scopes=self.scopes)
        self.budget.settle('maplark', 'one', None)
        budget = CreditBudget(self.repo)
        with self.assertRaises(ContractError):
            budget.reserve('maplark', 'two', 20, scopes=self.scopes)
        budget.settle('maplark', 'one', 3)
        self.assertEqual(budget.scope_status('maplark', self.scopes[1])['committed'], 3)
        self.assertEqual(budget.status('maplark')[0]['committed'], 3)
        self.assertFalse(budget.reserve('maplark', 'one', 20, scopes=self.scopes))

    def test_global_cap_still_blocks_and_rolls_back_allocations(self):
        self.budget.reserve('maplark', 'live', 800)
        with self.assertRaises(ContractError):
            self.budget.reserve('maplark', 'background', 20, scopes=self.scopes)
        self.assertEqual(self.budget.scope_status('maplark', self.scopes[0])['committed'], 0)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_credit_allocation').fetchone()[0], 0)

    def test_pilot_total_applies_across_layers(self):
        water = 'discovery:pilot:waterways'
        self.budget.configure_scope('maplark', water, self.start, self.end, 40)
        self.budget.reserve('maplark', 'roads', 20, scopes=self.scopes)
        self.budget.reserve('maplark', 'water', 20, scopes=(self.scopes[0], water))
        with self.assertRaisesRegex(ContractError, 'scope_exhausted'):
            self.budget.reserve('maplark', 'water2', 1, scopes=(self.scopes[0], water))

    def test_immutable_expired_missing_and_overrun(self):
        with self.assertRaisesRegex(ContractError, 'immutable'):
            self.budget.configure_scope('maplark', self.scopes[0], self.start, self.end+1, 40)
        for scopes, now in ((('missing',), time.time()), (self.scopes, self.end)):
            with self.assertRaises(ContractError):
                self.budget.reserve('maplark', 'missing', 20, scopes=scopes, now=now)
        self.budget.reserve('maplark', 'overrun', 20, scopes=self.scopes)
        self.budget.settle('maplark', 'overrun', 25)
        self.assertEqual(self.budget.scope_status('maplark', self.scopes[1])['committed'], 25)
        with self.assertRaisesRegex(ContractError, 'held'):
            self.budget.reserve('maplark', 'live', 1)

    def test_live_reserve_supports_pre_scope_schema(self):
        with self.repo.transaction() as c:
            c.execute('DROP TABLE world_credit_allocation')
            c.execute('DROP TABLE world_credit_scope')
        self.assertTrue(self.budget.reserve('maplark', 'live', 20))
        self.budget.settle('maplark', 'live', 3)
        self.assertEqual(self.budget.status('maplark')[0]['committed'], 3)
