from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_contract import ContractError


def reserve(args):
    path, i = args
    try:
        return CreditBudget(Repository(path)).reserve('maplark',f'op-{i}',3,now=100)
    except ContractError as exc:
        if str(exc) != 'budget_exhausted': raise
        return False


class RecurringBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'poi.db'
        self.b=CreditBudget(Repository(self.path)); self.b.initialize()

    def test_pilot_usage_preserved_and_old_ceiling_superseded(self):
        self.b.configure_window('maplark','pilot',0,86400,10)
        self.b.reserve('maplark','old',9,now=1); self.b.settle('maplark','old',9)
        self.b.configure_recurring('maplark',20,30)
        self.assertTrue(self.b.reserve('maplark','new',10,now=2))
        self.assertEqual(self.b.status('maplark',now=3)[0]['committed'],19)
        self.b.configure_recurring('maplark',20,30)
        with self.assertRaisesRegex(ContractError,'exhausted'):
            self.b.reserve('maplark','no-reset',2,now=4)

    def test_midnight_resets_day_not_rolling(self):
        self.b.configure_recurring('maplark',10,15)
        self.b.reserve('maplark','yesterday',9,now=86399); self.b.settle('maplark','yesterday',9)
        windows=self.b.status('maplark',now=86401)
        self.assertEqual([w['committed'] for w in windows],[0,9])
        with self.assertRaisesRegex(ContractError,'exhausted'):
            self.b.reserve('maplark','blocked-rolling',7,now=86401)
        self.assertTrue(self.b.reserve('maplark','allowed',6,now=86401))

    def test_unresolved_survives_31_days_and_settlement_releases(self):
        self.b.configure_recurring('maplark',10,10)
        self.b.reserve('maplark','unknown',9,now=1); self.b.settle('maplark','unknown')
        now=32*86400
        self.assertEqual([w['committed'] for w in self.b.status('maplark',now=now)],[9,9])
        with self.assertRaisesRegex(ContractError,'exhausted'):
            self.b.reserve('maplark','blocked',2,now=now)
        self.b.settle('maplark','unknown',3)
        self.assertEqual([w['committed'] for w in self.b.status('maplark',now=now)],[0,0])

    def test_four_processes_share_recurring_budget(self):
        self.b.configure_recurring('maplark',10,20)
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
            self.assertEqual(sum(pool.map(reserve,[(str(self.path),i) for i in range(12)])),3)
        self.assertEqual(self.b.status('maplark',now=100)[0]['committed'],9)

    def test_old_schema_can_continue_pilot_during_rolling_upgrade(self):
        self.b.configure_window('maplark','pilot',0,1000,10)
        with self.b.repo.transaction() as c: c.execute('DROP TABLE world_credit_policy')
        self.assertTrue(self.b.reserve('maplark','old-worker',3,now=1))
        self.assertEqual(self.b.status('maplark',now=2)[0]['committed'],3)
