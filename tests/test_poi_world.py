import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError, key_for
from poi_infrastructure.world import WorldRepository


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name) / 'poi.sqlite3')
        self.world = WorldRepository(self.repo)
        self.world.initialize()
        self.key = key_for('exact original query')
        self.owner = self.repo.acquire(self.key, 30)
        self.data = json.loads((Path(__file__).parent / 'fixtures/poi/complete.json').read_text())

    def write(self, data=None, **kwargs):
        return self.world.publish_exact(self.key, self.owner, self.data if data is None else data,
                                        'fixture', 300, 1800, **kwargs)

    def test_restart_immutable_and_no_fake_spatial_coverage(self):
        self.assertTrue(self.write())
        world = WorldRepository(Repository(self.repo.path))
        world.initialize()
        result = world.read_exact(self.key)
        result['elements'][0]['tags']['name'] = 'player modification'
        self.assertEqual(world.read_exact(self.key), self.data)
        self.assertIsNone(world.read_exact(key_for('nearby query')))
        self.assertEqual(world.status()['certified_cells'], 0)
        self.assertEqual(world.status()['members'], len(self.data['elements']))

    def test_empty_is_durable_but_partial_is_not(self):
        self.assertTrue(self.write({'elements': []}))
        self.assertEqual(self.world.read_exact(self.key), {'elements': []})
        for data in ({'elements': [], 'remark': 'runtime error'}, {'html':'error'},
                     {'elements':[{'type':'node','id':1,'lat':float('nan'),'lon':0}]}):
            with self.assertRaises((POIError, ValueError)):
                self.write(data)
        self.assertEqual(self.world.status()['snapshots'], 1)

    def test_fencing_and_no_partial_publish(self):
        with self.repo.transaction() as c:
            c.execute('UPDATE leases SET until_at=0')
        successor = self.repo.acquire(self.key,30)
        self.assertFalse(self.write())
        self.assertEqual(self.world.status()['snapshots'],0)
        self.assertTrue(self.repo.owns(self.key,successor))
        self.owner = successor
        duplicate = copy.deepcopy(self.data)
        duplicate['elements'].append(copy.deepcopy(duplicate['elements'][0]))
        with self.assertRaisesRegex(POIError,'duplicate_identity'):
            self.write(duplicate)
        self.assertEqual(self.world.status()['snapshots'],0)

    def test_age_not_extended_corruption_not_used(self):
        self.write(fetched=time.time()-400)
        self.assertIsNone(self.world.read_exact(self.key))
        self.assertEqual(self.world.read_exact(self.key,True),self.data)
        with self.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET digest=?',('corrupt',))
        self.assertIsNone(self.world.read_exact(self.key,True))

    def test_versions_do_not_delete_old_members(self):
        self.write(fetched=time.time()-10)
        self.write({'elements':[]})
        self.assertEqual(self.world.read_exact(self.key),{'elements':[]})
        self.assertEqual(self.world.status()['members'],len(self.data['elements']))
        self.assertEqual(self.world.status()['snapshots'],2)

    def test_capacity_refuses_without_destroying_previous_snapshot(self):
        self.write()
        self.world.max_snapshots = 1
        with self.assertRaisesRegex(POIError,'capacity'):
            self.write({'elements':[]})
        self.assertEqual(self.world.read_exact(self.key),self.data)

    def test_sqlite_backup_restore_preserves_snapshots(self):
        import sqlite3
        self.write()
        target = Path(self.tmp.name) / 'restored.sqlite3'
        source = self.repo.connect()
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            source.close(); dest.close()
        restored = WorldRepository(Repository(target))
        restored.initialize()
        self.assertEqual(restored.read_exact(self.key),self.data)


if __name__ == '__main__':
    unittest.main()
