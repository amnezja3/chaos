import tempfile
from pathlib import Path
import unittest
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.world_contract import ContractError
from tools.world_discovery_pilot import operate as pilot
from tools.world_discovery_rollout import operate


class RolloutTests(unittest.TestCase):
    def test_dry_run_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'absent.db'
            self.assertEqual(operate(path,'promote')['status'],'plan')
            self.assertFalse(path.exists())

    def test_promote_preserves_pilot_usage_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'poi.db'; repo=Repository(path); repo.initialize()
            pilot(path,'prepare',apply=True)
            with self.assertRaisesRegex(ContractError,'tested_maplark'):
                operate(path,'promote',apply=True)
            registry=Registry(repo); value=registry.list()[0]
            registry.tested('maplark',value['revision'],True,'fixture')
            ledger=CreditBudget(repo)
            ledger.reserve('maplark','already-paid',20); ledger.settle('maplark','already-paid',9)
            first=operate(path,'promote',apply=True)
            second=operate(path,'promote',apply=True)
            self.assertEqual(first['revision'],second['revision'])
            self.assertTrue(second['provider_enabled'])
            self.assertEqual([w['committed'] for w in second['budget_windows']],[9,9])
            self.assertEqual([w['credit_limit'] for w in second['budget_windows']],[800,24000])
            self.assertFalse(operate(path,'disable',apply=True)['provider_enabled'])
            ledger.reserve('maplark','overcharged',1); ledger.settle('maplark','overcharged',2)
            with self.assertRaisesRegex(ContractError,'account_held'):
                operate(path,'promote',apply=True)
            self.assertFalse(registry.list()[0]['enabled'])
