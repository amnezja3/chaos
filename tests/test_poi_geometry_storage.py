import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from poi_infrastructure.repository import Repository
from poi_infrastructure.world import WorldRepository
from poi_infrastructure.geometry import UncertifiedGeometry
from test_poi_geometry import source_elements, FIXTURE, FILTERS


class GeometryStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name)/'poi.sqlite3')
        self.world = WorldRepository(self.repo)
        self.world.initialize()
        self.key = 'synthetic-full-closure'
        self.owner = self.repo.acquire(self.key,30)

    def publish(self, elements=None, fetched=None):
        wide = json.loads((FIXTURE/'geometry_wide_reference.json').read_text())
        return self.world.publish_geometry(self.key,self.owner,
            wide if elements is None else dict(elements=elements),
            'synthetic',300,1800,0,0,1500,FILTERS,fetched=fetched)

    def test_persisted_nearby_reads_and_restore_match_overpass(self):
        self.assertTrue(self.publish())
        path = Path(self.tmp.name)/'restored.sqlite3'
        source = self.repo.connect()
        dest = sqlite3.connect(path)
        source.backup(dest)
        dest.close(); source.close()
        world = WorldRepository(Repository(path))
        world.initialize()
        for name, case in json.loads((FIXTURE/'geometry_reference.json').read_text())['cases'].items():
            local = world.read_geometry(case['lat'],case['lon'],case['radius'],FILTERS)
            if name == 'empty':
                self.assertIsNone(local)  # Unknown terrain is not a certified empty result.
            else:
                self.assertEqual(local['elements'],case['response']['elements'])
        self.assertIsNone(world.read_exact(self.key))
        self.assertEqual(world.status()['certified_cells'],0)

    def test_empty_complete_and_missing_member_are_different(self):
        self.publish([])
        self.assertEqual(self.world.read_geometry(0,0,300,FILTERS),{'elements':[]})
        with self.assertRaises(UncertifiedGeometry):
            self.publish([e for e in source_elements() if e['id']!=11])
        self.assertEqual(self.world.status()['snapshots'],1)

    def test_fencing_expiry_and_corruption(self):
        self.publish(fetched=time.time()-400)
        self.assertIsNone(self.world.read_geometry(0,0,300,FILTERS))
        self.assertIsNotNone(self.world.read_geometry(0,0,300,FILTERS,True))
        with self.repo.transaction() as c:
            c.execute('UPDATE leases SET until_at=0')
        self.assertFalse(self.publish())
        with self.repo.transaction() as c:
            c.execute("UPDATE world_snapshot SET digest='bad'")
        self.assertIsNone(self.world.read_geometry(0,0,300,FILTERS,True))

    def test_expired_cleanup_cascades_and_preserves_usable_snapshot(self):
        self.publish(fetched=time.time()-2000)
        self.publish()
        self.assertEqual(self.world.prune_expired(1),1)
        self.assertEqual(self.world.status()['snapshots'],1)
        self.assertIsNotNone(self.world.read_geometry(0,0,300,FILTERS))
        c=self.repo.connect()
        try:self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        finally:c.close()


if __name__ == '__main__':
    unittest.main()
