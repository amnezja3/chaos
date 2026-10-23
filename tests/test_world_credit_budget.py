from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_contract import ContractError


def reserve_in_process(args):
    path, i = args
    try:
        return CreditBudget(Repository(path)).reserve('a', f'op-{i}', 3, now=1)
    except ContractError as exc:
        if str(exc) != 'budget_exhausted':
            raise
        return False


class CreditBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'poi.sqlite3'
        self.ledger = CreditBudget(Repository(self.path))
        self.ledger.initialize()
        self.ledger.configure_window('a', 'day-1', 0, 100, 10)
        self.ledger.configure_window('a', 'month-1', 0, 1000, 15)

    def test_parallel_reservations_share_all_limits(self):
        with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as pool:
            self.assertEqual(sum(pool.map(reserve_in_process, [(str(self.path), i) for i in range(12)])), 3)
        self.assertEqual(self.ledger.status('a', now=1)[0]['committed'], 9)

    def test_restart_idempotency_uncertain_and_reconciliation(self):
        self.assertTrue(self.ledger.reserve('a', 'one', 8, now=1))
        self.ledger.settle('a', 'one')
        ledger = CreditBudget(Repository(self.path)); ledger.initialize()
        self.assertFalse(ledger.reserve('a', 'one', 8, now=2))
        with self.assertRaisesRegex(ContractError, 'budget_exhausted'):
            ledger.reserve('a', 'two', 3, now=2)
        ledger.settle('a', 'one', 2)
        ledger.settle('a', 'one', 2)
        self.assertTrue(ledger.reserve('a', 'two', 3, now=2))
        self.assertEqual(ledger.status('a', now=2)[0]['committed'], 5)

    def test_new_day_cannot_hide_pending_old_day_cost(self):
        self.ledger.reserve('a', 'one', 8, now=99)
        self.ledger.configure_window('a', 'day-2', 100, 200, 10)
        with self.assertRaisesRegex(ContractError, 'budget_previous_period_unresolved'):
            self.ledger.reserve('a', 'two', 1, now=101)
        self.ledger.settle('a', 'one', 8)
        with self.assertRaisesRegex(ContractError, 'budget_exhausted'):
            self.ledger.reserve('a', 'two', 8, now=101)  # monthly limit still 15
        self.assertTrue(self.ledger.reserve('a', 'two', 7, now=101))

    def test_remote_overcharge_is_recorded_and_holds_account(self):
        self.ledger.reserve('a', 'one', 2, now=1)
        self.ledger.settle('a', 'one', 5)
        self.assertEqual(self.ledger.status('a', now=1)[0]['committed'], 5)
        with self.assertRaisesRegex(ContractError, 'budget_account_held'):
            self.ledger.reserve('a', 'two', 1, now=1)

    def test_reduced_limit_and_conflicts(self):
        self.ledger.reserve('a', 'one', 8, now=1)
        self.ledger.configure_window('a', 'day-1', 0, 100, 5)
        with self.assertRaisesRegex(ContractError, 'budget_exhausted'):
            self.ledger.reserve('a', 'two', 1, now=1)
        with self.assertRaisesRegex(ContractError, 'budget_operation_conflict'):
            self.ledger.reserve('a', 'one', 7, now=1)
        with self.assertRaisesRegex(ContractError, 'budget_window_immutable'):
            self.ledger.configure_window('a', 'day-1', 1, 200, 10)
        self.ledger.settle('a', 'one', 0)  # proven not sent
        with self.assertRaisesRegex(ContractError, 'budget_settlement_conflict'):
            self.ledger.settle('a', 'one', 1)

    def test_missing_budget_or_price_fails_closed(self):
        with self.assertRaisesRegex(ContractError, 'budget_unconfigured'):
            self.ledger.reserve('b', 'one', 1, now=1)
        for amount in (0, -1, True, 1.2, None):
            with self.subTest(amount=amount), self.assertRaises(ContractError):
                self.ledger.reserve('a', 'one', amount, now=1)


if __name__ == '__main__':
    unittest.main()
