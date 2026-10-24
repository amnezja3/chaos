from contextlib import closing
from pathlib import Path
import tempfile
import time
import unittest

from poi_infrastructure.repository import Repository
from poi_infrastructure.credit_budget import CreditBudget
from tools.provider_routing import prepare


class RoutingMigrationTests(unittest.TestCase):
    def test_dry_run_and_apply_preserve_ledger_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'poi.sqlite3'
            repo=Repository(path);ledger=CreditBudget(repo);ledger.initialize()
            ledger.configure_window('maplark','pilot',time.time()-1,time.time()+3600,100)
            ledger.reserve('maplark','existing',20);ledger.settle('maplark','existing',3)
            self.assertEqual(prepare(path)['status'],'dry_run')
            with closing(repo.connect()) as c:
                self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='poi_routing'").fetchone())
            result=prepare(path,Path(directory)/'backup')
            self.assertEqual(ledger.status('maplark')[0]['committed'],3)
            backup=Repository(result['backup'])
            self.assertEqual(CreditBudget(backup).status('maplark')[0]['committed'],3)
            with closing(backup.connect()) as c:
                self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='poi_routing'").fetchone())
            with self.assertRaisesRegex(ValueError,'already_exists'):
                prepare(path,Path(directory)/'backup')
