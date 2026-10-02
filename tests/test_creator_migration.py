import copy
import tempfile
import unittest
from pathlib import Path

from creator_migration import plan, apply
from creator_store import CreatorStore


class CreatorMigrationTest(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store=CreatorStore(str(Path(folder.name)/'game.sqlite'))
        self.app=dict(id='xmapper',name='XMapper',creator_username='author',
            project_file='XMapper.sh',generated=True,published=True,price=2225,
            levels=[{'options':[{'effect':{'firewall':False},'price':123}]}])

    def test_exact_snapshot_idempotency_and_source_conflict(self):
        original=copy.deepcopy(self.app)
        entries=plan([self.app],['author'])
        self.assertEqual(self.store.catalog(),[])
        self.assertEqual(apply(self.store,entries)[0]['status'],'migrated')
        self.assertEqual(self.store.catalog(),[original])
        self.assertEqual(apply(self.store,entries)[0]['status'],'already_migrated')
        changed=plan([dict(self.app,price=1)],['author'])
        with self.assertRaises(ValueError):apply(self.store,changed)
        self.assertEqual(self.store.catalog(),[original])

    def test_explicit_owners_ambiguity_and_ghostlab_exclusion(self):
        with self.assertRaises(ValueError):plan([self.app],[])
        self.assertEqual(plan([self.app],['other']),[])
        self.assertEqual(plan([dict(self.app,ghostlab_generated=True)],['author']),[])
        entries=plan([self.app,dict(self.app,id='duplicate')],['author'])
        self.assertTrue(all(item['status']=='review' for item in entries))
        apply(self.store,entries)
        self.assertEqual(self.store.catalog(),[])

    def test_migration_never_restores_a_withdrawn_offer(self):
        entries=plan([self.app],['author'])
        apply(self.store,entries)
        self.store.withdraw('author','XMapper.sh')
        apply(self.store,entries)
        self.assertFalse(self.store.catalog()[0]['published'])


if __name__=='__main__':unittest.main()
