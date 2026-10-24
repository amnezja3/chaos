"""Real VPS water geometry, synthetic storage certificates. No provider approval."""
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from shapely.geometry import box,shape

import test_world_read
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_adapters import MAPLARK_VERSION,normalize_maplark,plan_maplark_region
from poi_infrastructure.world_contract import Provenance,ContractError
from poi_infrastructure.world_region_candidate import prepare
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import WorldReadPlanner
from tools.world_region_plan import evaluate
from tools.world_region_probe import BOUNDS,PARTS


class WaterReferenceTests(unittest.TestCase):
    def load(self,profile):
        base=Path(__file__).parent/'fixtures/poi'/('maplark_'+profile+'_bbox_20261024')
        raw=base.with_suffix('.json').read_bytes()
        meta=json.loads(base.with_suffix('.metadata.json').read_text(encoding='utf8'))
        self.assertEqual(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),meta['fixture_sha256_lf'])
        body=json.loads(raw)
        batch=normalize_maplark(body,meta['headers'],Provenance('maplark',MAPLARK_VERSION,
            'recorded-water',meta['fetched_at'],license_ref='ODbL-1.0'),profile=profile,maximum=1000)
        return body,meta,batch

    def storage(self,profile,filtered=True):
        body,meta,raw=self.load(profile)
        batch=prepare(raw,plan_maplark_region(BOUNDS,profile=profile)).batch if filtered else raw
        fixture=test_world_read.LocalWorldReadTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        # Test-only provider/time/certificate, not freshening real production data.
        objects=tuple(replace(o,provenance=Provenance('fixture','adapter-v1','water-reference',
                          fixture.now,license_ref='ODbL-1.0')) for o in batch.objects)
        stored,proof=fixture.area(objects,bounds=BOUNDS,layer=profile)
        return fixture,stored,proof

    def test_captures_match_reported_topology_and_counts(self):
        for profile,counts in (('waterways',(2,1,1,0)),('inland_water',(4,4,3,1))):
            with self.subTest(profile=profile):
                body,meta,batch=self.load(profile)
                result=evaluate(BOUNDS,profile,body,meta['headers'])
                self.assertEqual((result['objects'],result['candidate']['objects'],
                    result['neighbor_candidates']['left'],result['neighbor_candidates']['right']),counts)
                self.assertEqual(result['topology']['interior_rings'],0)
                self.assertFalse(result['topology']['water_surface_with_holes_observed'])
                self.assertFalse(result['region_certified'])

    def test_real_envelope_false_positive_removed_without_clipping_crossing_line(self):
        _,_,batch=self.load('waterways')
        candidate=prepare(batch,plan_maplark_region(BOUNDS,profile='waterways'))
        self.assertEqual(candidate.excluded_ids,('osm:way:1158230038',))
        selected=candidate.batch.objects[0]
        self.assertEqual(selected.identity,'osm:way:287683438')
        self.assertEqual(selected,batch.objects[0])
        geometry=shape(selected.geometry.geojson());area=box(*BOUNDS)
        self.assertTrue(geometry.intersects(area))
        self.assertFalse(area.covers(geometry))
        self.assertFalse(area.covers(shape(dict(type='Point',coordinates=geometry.coords[0]))))
        self.assertFalse(area.covers(shape(dict(type='Point',coordinates=geometry.coords[-1]))))

    def test_restore_and_neighbor_reads_keep_exact_water_geometries(self):
        for profile,expected in (('waterways',(1,0)),('inland_water',(3,1))):
            with self.subTest(profile=profile):
                fixture,batch,proof=self.storage(profile)
                fixture.publish(batch,proof)
                restored=Path(fixture.tmp.name)/'restore.sqlite3'
                with closing(fixture.repo.connect()) as source,closing(sqlite3.connect(restored)) as dest:
                    source.backup(dest)
                    self.assertEqual(dest.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                    self.assertEqual(dest.execute('PRAGMA foreign_key_check').fetchall(),[])
                fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(restored)))
                with patch('socket.create_connection',side_effect=AssertionError('no HTTP')):
                    left=fixture.read_area(PARTS['left'],profile);right=fixture.read_area(PARTS['right'],profile)
                self.assertEqual((left.state,right.state),('COMPLETE_FRESH','COMPLETE_FRESH'))
                self.assertEqual((len(left.batch.objects),len(right.batch.objects)),expected)
                selected={o.identity:o for r in (left,right) for o in r.batch.objects}
                self.assertEqual(selected,{o.identity:o for o in batch.objects})
                self.assertEqual(fixture.read_area((20.35,51.53,20.37,51.54),profile).state,'MISS')
                other='inland_water' if profile=='waterways' else 'waterways'
                self.assertEqual(fixture.read_area(BOUNDS,other).state,'MISS')

    def test_no_real_water_area_proof_inferred_from_candidate(self):
        for profile in ('waterways','inland_water'):
            fixture,batch,proof=self.storage(profile)
            with self.assertRaisesRegex(ContractError,'not_certified'):
                fixture.publish(batch,proof,certified=False)
            fixture.world.publish_batch('query',fixture.owner,batch,provider='fixture',revision=1,
                storage_reference='fixture-storage-v1',fresh_until=fixture.fresh,usable_until=fixture.usable)
            self.assertEqual(fixture.read_area(BOUNDS,profile).state,'MISS')

    def test_unfiltered_false_positive_blocks_publication(self):
        fixture,batch,proof=self.storage('waterways',filtered=False)
        with self.assertRaisesRegex(ContractError,'selection_mismatch'):fixture.publish(batch,proof)
        with closing(fixture.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
