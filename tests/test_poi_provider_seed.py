import tempfile
from pathlib import Path
import unittest
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from tools.poi_provider_seed import seed, CANDIDATES
from poiFetchClass import POIFetcher


class SeedTests(unittest.TestCase):
    def test_dry_run_disabled_candidates_and_preserving_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'poi.sqlite3'
            registry=Registry(Repository(path));registry.initialize()
            self.assertEqual([v[2] for v in CANDIDATES],POIFetcher().endpoints)
            self.assertEqual(len(seed(path)['added']),4)
            self.assertEqual(registry.list(),[])
            self.assertEqual(len(seed(path,True)['added']),4)
            rows=registry.list()
            self.assertTrue(all(not r['enabled'] and not r['scopes'] and r['policy_status']=='unknown' for r in rows))
            v=rows[0]
            registry.save(v['id'],v['revision'],dict(name='Custom name',url=v['url'],operator_group=v['operator_group'],priority=99),'admin')
            before=registry.list()
            self.assertEqual(seed(path,True)['added'],[])
            self.assertEqual(registry.list(),before)

    def test_refuse_unrelated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unknown.sqlite3'
            path.touch()
            with self.assertRaises(ValueError):seed(path,True)


if __name__=='__main__':unittest.main()
