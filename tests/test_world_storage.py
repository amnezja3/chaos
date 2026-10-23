import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.world import WorldRepository
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_contract import Geometry, Provenance, ProviderBatch, WorldObject
from poi_infrastructure.service import POIError


class CanonicalStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'poi.sqlite3'
        self.repo = Repository(self.path)
        self.legacy = WorldRepository(self.repo)
        self.legacy.initialize()
        Registry(self.repo).initialize()
        self.owner = self.repo.acquire('fixture', 60)
        self.data = {'elements': [{'type':'node','id':1,'lat':2,'lon':3,'tags':{'shop':'books'}}]}
        self.legacy.publish_exact('fixture',self.owner,self.data,'fixture',300,1800)
        with self.repo.transaction() as c:
            config = dict(enabled=True, policy_status='approved_for_defined_use', scopes=['storage'],review_due_at=time.time()+3600)
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)', ('fixture',1,json.dumps(config)))
        self.world = CanonicalWorldRepository(self.repo)
        self.assertTrue(self.world.initialize_canonical())
        self.fresh = time.time()+300
        self.usable = time.time()+1800

    def obj(self, ident=1, kind='Point', coords=None, tags=None, osm=True):
        coords = [2,2] if coords is None else coords
        return WorldObject.create(external_id=str(ident), tags=tags or {'shop':'books'},
            geometry=Geometry.parse(dict(type=kind,coordinates=coords)), marker=None, marker_method=None,
            provenance=Provenance('fixture','fixture-v1','snapshot',time.time()-10,license_ref='fixture-license'),
            ordinal=ident, osm_type='node' if osm else None, osm_id=ident if osm else None)

    def batch(self, *objects, completeness='complete'):
        return ProviderBatch(tuple(objects),'poi',completeness,(), 'fixture-intersection-v1','source')

    def publish(self, batch=None, **kwargs):
        return self.world.publish_batch('fixture',self.owner,self.batch(self.obj()) if batch is None else batch,
            provider='fixture',revision=kwargs.get('revision',1),storage_reference='offline-fixture-only',
            fresh_until=self.fresh,usable_until=self.usable)

    def test_migration_idempotent_and_legacy_reads_and_writes_survive(self):
        self.assertFalse(self.world.initialize_canonical())
        self.assertEqual(self.legacy.read_exact('fixture'),self.data)
        self.assertTrue(self.legacy.publish_exact('fixture',self.owner,{'elements':[]},'fixture',300,1800))
        self.assertEqual(self.legacy.read_exact('fixture'),{'elements':[]})
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())

    def test_four_geometries_provider_identity_backup_restore(self):
        shell=[[0,0],[10,0],[10,10],[0,10],[0,0]]
        hole=[[2,2],[2,4],[4,4],[4,2],[2,2]]
        island=[[20,0],[22,0],[22,2],[20,2],[20,0]]
        objects=[self.obj(), self.obj(2,'LineString',[[-1,3],[11,3]],{'highway':'road'}),
                 self.obj(3,'Polygon',[shell,hole],{'natural':'water'}),
                 self.obj(4,'MultiPolygon',[[shell,hole],[island]],{'natural':'water'},osm=False)]
        batch=self.batch(*objects)
        snapshot=self.publish(batch)
        self.assertEqual(self.publish(batch),snapshot)
        self.assertEqual(self.world.read_batch(snapshot),batch)
        target=Path(self.tmp.name)/'restored.sqlite3'
        with closing(self.repo.connect()) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
        restored=CanonicalWorldRepository(Repository(target))
        self.assertFalse(restored.initialize_canonical())
        self.assertEqual(restored.read_batch(snapshot),batch)

    def test_intersection_not_centroid_and_hole_not_water(self):
        shell=[[0,0],[10,0],[10,10],[0,10],[0,0]]
        hole=[[2,2],[2,4],[4,4],[4,2],[2,2]]
        snapshot=self.publish(self.batch(self.obj(1,'LineString',[[-1,3],[11,3]],{'highway':'road'}),
                                        self.obj(2,'Polygon',[shell,hole],{'natural':'water'})))
        road=self.world.inspect_region(snapshot,'roads',(2.5,2.5,3.5,3.5))
        self.assertEqual(len(road['objects']),1)
        self.assertEqual(road['coverage'],'UNKNOWN')
        self.assertEqual(self.world.inspect_region(snapshot,'inland_water',(2.5,2.5,3.5,3.5))['objects'],())
        self.assertEqual(len(self.world.inspect_region(snapshot,'inland_water',(0.5,0.5,1.5,1.5))['objects']),1)

    def test_dateline_retained_but_excluded_and_flagged(self):
        batch=self.batch(self.obj(1,'LineString',[[179,0],[-179,0]],{'natural':'coastline'}))
        snapshot=self.publish(batch)
        self.assertEqual(self.world.read_batch(snapshot),batch)
        result=self.world.inspect_region(snapshot,'coastline',(0,-1,1,1))
        self.assertTrue(result['unsupported'])
        self.assertEqual(result['objects'],())
        self.assertEqual(self.world.inspect_region(snapshot,'land_water',(0,-1,1,1))['coverage'],'UNKNOWN')

    def test_partial_empty_and_missing_never_claim_coverage(self):
        for batch in (self.batch(),self.batch(self.obj(),completeness='partial')):
            snapshot=self.publish(batch)
            self.assertEqual(self.world.read_batch(snapshot),batch)
            self.assertEqual(self.world.inspect_region(snapshot,'poi',(0,0,4,4))['coverage'],'UNKNOWN')
        self.assertEqual(self.world.inspect_region('missing','poi',(0,0,4,4))['coverage'],'UNKNOWN')

    def test_expired_lease_and_revision_cannot_publish(self):
        count=self.world.status()['snapshots']
        with self.assertRaisesRegex(POIError,'revision'):
            self.publish(revision=2)
        with self.repo.transaction() as c:
            c.execute('UPDATE leases SET until_at=0')
        self.assertIsNone(self.publish())
        self.assertEqual(self.world.status()['snapshots'],count)

    def test_crash_rolls_back_snapshot_and_members(self):
        count=self.world.status()['snapshots']
        with self.repo.transaction() as c:
            c.execute("CREATE TRIGGER simulated_failure BEFORE INSERT ON world_member BEGIN SELECT RAISE(ABORT,'fixture_crash'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.publish()
        self.assertEqual(self.world.status()['snapshots'],count)

    def test_lease_expiring_during_publication_rolls_back(self):
        count=self.world.status()['snapshots']
        with self.repo.transaction() as c:
            c.execute("CREATE TRIGGER expire_lease AFTER INSERT ON world_member BEGIN UPDATE leases SET until_at=0; END")
        with self.assertRaisesRegex(POIError,'lease_expired_during'):
            self.publish()
        self.assertEqual(self.world.status()['snapshots'],count)

    def test_conflicting_observations_preserved_not_merged(self):
        first=self.batch(self.obj(tags={'shop':'books'}))
        second=self.batch(self.obj(tags={'shop':'clothes'}))
        a=self.publish(first)
        b=self.publish(second)
        self.assertNotEqual(a,b)
        self.assertEqual(self.world.read_batch(a),first)
        self.assertEqual(self.world.read_batch(b),second)

    def test_capacity_and_candidate_limit_are_explicit(self):
        snapshot=self.publish(self.batch(self.obj(1),self.obj(2)))
        result=self.world.inspect_region(snapshot,'poi',(0,0,4,4),limit=1)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['objects']),1)
        self.world.max_bytes=1
        with self.assertRaisesRegex(POIError,'capacity'):
            self.publish()
        self.assertIsNotNone(self.world.read_batch(snapshot))

    def test_corrupt_payload_not_returned_and_cleanup_cascades(self):
        snapshot=self.publish()
        with self.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET digest=? WHERE id=?',('bad',snapshot))
        self.assertIsNone(self.world.read_batch(snapshot))
        with self.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET usable_until=0 WHERE id=?',(snapshot,))
        self.assertEqual(self.world.prune_expired(),1)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_member WHERE snapshot_id=?',(snapshot,)).fetchone()[0],0)

    def test_cli_dry_run_does_not_modify_source(self):
        before=self.path.read_bytes()
        result=subprocess.run([sys.executable,'tools/poi_world.py','--db',str(self.path),'--canonical'],
                              text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout)['status'],'dry_run')
        self.assertEqual(self.path.read_bytes(),before)

    def test_cli_backup_contains_pre_migration_version_and_ledger(self):
        path=Path(self.tmp.name)/'v1.sqlite3'
        repo=Repository(path)
        WorldRepository(repo).initialize()
        Registry(repo).initialize()
        with repo.transaction() as c:
            c.execute('CREATE TABLE fixture_billing (spent INTEGER)')
            c.execute('INSERT INTO fixture_billing VALUES (21)')
        backup=Path(self.tmp.name)/'backup.sqlite3'
        result=subprocess.run([sys.executable,'tools/poi_world.py','--db',str(path),'--canonical',
                               '--apply','--backup',str(backup)],text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout)['world_schema'],2)
        for candidate, version in ((backup,1),(path,2)):
            with closing(sqlite3.connect(candidate)) as c:
                self.assertEqual(c.execute('SELECT version FROM world_schema').fetchone()[0],version)
                self.assertEqual(c.execute('SELECT spent FROM fixture_billing').fetchone()[0],21)

    def test_migration_failure_rolls_back_original_table(self):
        path=Path(self.tmp.name)/'v1.sqlite3'
        repo=Repository(path)
        legacy=WorldRepository(repo)
        legacy.initialize()
        owner=repo.acquire('key',30)
        legacy.publish_exact('key',owner,self.data,'fixture',300,1800)
        with repo.transaction() as c:
            c.execute("CREATE TRIGGER fail_version BEFORE UPDATE ON world_schema BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            CanonicalWorldRepository(repo).initialize_canonical()
        self.assertEqual(legacy.read_exact('key'),self.data)
        with closing(repo.connect()) as c:
            self.assertEqual(c.execute('SELECT version FROM world_schema').fetchone()[0],1)
            self.assertNotIn('identity',[r[1] for r in c.execute('PRAGMA table_info(world_member)')])

    def test_corrupt_member_is_not_silently_used(self):
        snapshot=self.publish()
        with self.repo.transaction() as c:
            c.execute('UPDATE world_member SET element_digest=? WHERE snapshot_id=?',('bad',snapshot))
        with self.assertRaisesRegex(POIError,'world_member_corrupt'):
            self.world.inspect_region(snapshot,'poi',(0,0,4,4))

    def test_provider_revocation_and_expiration_deny_publish(self):
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=?', (json.dumps(dict(enabled=False)),))
        with self.assertRaisesRegex(POIError,'storage_denied'):
            self.publish()

    def test_apply_refuses_player_database_even_under_different_name(self):
        path=Path(self.tmp.name)/'renamed.sqlite3'
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE users(id INTEGER)')
        result=subprocess.run([sys.executable,'tools/poi_world.py','--db',str(path),'--canonical',
                               '--apply','--backup',str(Path(self.tmp.name)/'bad-backup.sqlite3')],
                              text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        with closing(sqlite3.connect(path)) as c:
            self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('users',)])


if __name__=='__main__':
    unittest.main()
