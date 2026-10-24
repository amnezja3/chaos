"""Real VPS geometry, synthetic storage permission; NOT provider area certification."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from shapely.geometry import box,shape
from poi_infrastructure.world_adapters import normalize_maplark,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance,ContractError
from poi_infrastructure.world_read import AREA_SELECTION,WorldReadPlanner
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.repository import Repository
from tools.world_region_plan import evaluate
import test_world_read


class RegionalReferenceTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).parent/'fixtures/poi/maplark_roads_bbox_20261024'
        raw=base.with_suffix('.json').read_bytes()
        self.meta=json.loads(base.with_suffix('.metadata.json').read_text())
        self.assertEqual(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),self.meta['fixture_sha256_lf'])
        self.body=json.loads(raw);self.bounds=tuple(self.meta['bbox'])
        self.batch=normalize_maplark(self.body,self.meta['headers'],
            Provenance('maplark',MAPLARK_VERSION,'saved-reference',0),profile='roads',maximum=1000)

    def storage_fixture(self):
        fixture=test_world_read.LocalWorldReadTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        objects=tuple(replace(obj,provenance=Provenance('fixture','adapter-v1','saved-reference',fixture.now,license_ref='ODbL-1.0'))
                      for obj in self.batch.objects)
        return fixture,objects

    def test_saved_response_and_neighbor_counts(self):
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            result=evaluate(self.bounds,'roads',self.body,self.meta['headers'])
        self.assertEqual(result['objects'],76)
        self.assertEqual(result['invalid_details'][0]['identity'],'osm:way:201343570')
        self.assertEqual(result['local_filter']['selected_objects'],75)
        self.assertEqual(result['local_filter']['blocking_objects'],0)
        self.assertTrue(result['local_filter']['neighbor_union_matches'])
        self.assertEqual(result['neighbor_candidates'],dict(left=33,right=54,crossing=12))
        self.assertFalse(result['region_certified'])

    def test_raw_observation_survives_storage_without_area_read(self):
        fixture,objects=self.storage_fixture()
        batch=replace(self.batch,objects=objects,selection='maplark-bbox-unverified')
        fixture.world.publish_batch('query',fixture.owner,batch,provider='fixture',revision=1,
            storage_reference='fixture-storage-v1',fresh_until=fixture.fresh,usable_until=fixture.usable)
        fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(fixture.repo.path)))
        self.assertEqual(fixture.read_area(self.bounds).state,'MISS')

    def test_neighbor_reads_after_restart_preserve_full_geometry(self):
        fixture,objects=self.storage_fixture()
        selected=tuple(o for o in objects if shape(o.geometry.geojson()).intersects(box(*self.bounds)))
        batch,proof=fixture.area(selected,bounds=self.bounds)
        # Synthetic fixture certificate tests the engine only, never MapLark approval.
        fixture.publish(batch,proof)
        fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(fixture.repo.path)))
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            left=fixture.read_area((20.36,51.53,20.365,51.54))
            right=fixture.read_area((20.365,51.53,20.37,51.54))
        self.assertEqual((left.state,right.state),('COMPLETE_FRESH','COMPLETE_FRESH'))
        l={o.identity:o for o in left.batch.objects};r={o.identity:o for o in right.batch.objects}
        self.assertEqual((len(l),len(r),len(l.keys()&r.keys())),(33,54,12))
        originals={o.identity:o for o in selected}
        self.assertEqual(l.keys()|r.keys(),originals.keys())
        for obj in (*l.values(),*r.values()):self.assertEqual(obj.geometry,originals[obj.identity].geometry)
        self.assertEqual(fixture.read_area((20.35,51.53,20.37,51.54)).state,'MISS')

    def test_raw_excess_cannot_bypass_area_validation(self):
        fixture,objects=self.storage_fixture()
        batch,proof=fixture.area(objects,bounds=self.bounds)
        with self.assertRaisesRegex(ContractError,'selection_mismatch'):fixture.publish(batch,proof)
        selected=tuple(o for o in objects if shape(o.geometry.geojson()).intersects(box(*self.bounds)))
        batch,proof=fixture.area(selected,bounds=self.bounds)
        with self.assertRaisesRegex(ContractError,'not_certified'):fixture.publish(batch,proof,certified=False)
