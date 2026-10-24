from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import unittest
from shapely.geometry import box,mapping
import test_world_read
from poi_infrastructure.land_water import prepare_product,validate_partition,ADAPTER
from poi_infrastructure.world_contract import Provenance,ContractError,layers_for
from poi_infrastructure.world_read import SelectionProof,AREA_SELECTION,WorldReadPlanner
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.repository import Repository

BOUNDS=(20.,51.,20.01,51.01)
DEPS=('a'*64,'b'*64)


def product():
    area=box(*BOUNDS);island=box(20.003,51.003,20.007,51.007)
    return dict(type='FeatureCollection',features=[dict(type='Feature',id=role,
        properties={'surface':role},geometry=mapping(geom)) for role,geom in
        (('land',island),('sea',area.difference(island)))])


class LandWaterTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_world_read.LocalWorldReadTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.provenance=Provenance('fixture',ADAPTER,'regional-product',self.fixture.now,
                                   source_dataset_at='source-v1',license_ref='synthetic-test')

    def batch(self,body=None):
        return prepare_product(product() if body is None else body,bounds=BOUNDS,
                               provenance=self.provenance,dependencies=DEPS)

    def publish(self,batch=None):
        proof=SelectionProof('area','land_water','land_water',AREA_SELECTION,ADAPTER,'query',
                             BOUNDS,'synthetic-product',dataset_version='source-v1')
        return self.fixture.world.publish_batch('query',self.fixture.owner,batch or self.batch(),
            provider='fixture',revision=1,storage_reference='fixture-storage-v1',
            fresh_until=self.fixture.fresh,usable_until=self.fixture.usable,coverage=proof,
            certified_selections=(('fixture',ADAPTER,'land_water',AREA_SELECTION,'synthetic-product'),))

    def read(self,bounds,**kwargs):
        options=dict(provider='fixture',revision=1,storage_reference='fixture-storage-v1',profile='land_water',
            layer='land_water',selection=AREA_SELECTION,adapter_version=ADAPTER,bounds=bounds,
            dataset_version='source-v1',dependency_digests=DEPS)
        options.update(kwargs)
        return self.fixture.planner.read(**options)

    def test_island_and_sea_hole_roundtrip_after_restore(self):
        batch=self.batch();self.publish(batch)
        restored=Path(self.fixture.tmp.name)/'restore.sqlite3'
        with closing(self.fixture.repo.connect()) as src,closing(sqlite3.connect(restored)) as dest:
            src.backup(dest)
        self.fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(restored)))
        land=self.read((20.004,51.004,20.006,51.006))
        sea=self.read((20.001,51.001,20.002,51.002))
        self.assertEqual((land.state,sea.state),('COMPLETE_FRESH','COMPLETE_FRESH'))
        self.assertEqual([o.land_water_origin.role for o in land.batch.objects],['land'])
        self.assertEqual([o.land_water_origin.role for o in sea.batch.objects],['sea'])
        self.assertEqual(self.read(BOUNDS).batch,batch)

    def test_missing_changed_dependency_or_dataset_is_miss(self):
        self.publish()
        for changes in ({'dependency_digests':None},{'dependency_digests':('c'*64,)},{'dataset_version':'source-v2'}):
            self.assertEqual(self.read(BOUNDS,**changes).state,'MISS')
        self.assertEqual(self.read((19.999,51.,20.01,51.01)).state,'MISS')

    def test_gap_and_conflicting_roles_rejected(self):
        gap=product();gap['features']=gap['features'][:1]
        with self.assertRaisesRegex(ContractError,'uncovered'):self.batch(gap)
        overlap=product();overlap['features'][1]['geometry']=mapping(box(*BOUNDS))
        with self.assertRaisesRegex(ContractError,'conflicting_roles'):self.batch(overlap)

    def test_same_role_overlap_allowed_without_double_classification(self):
        body=product();duplicate=dict(body['features'][0],id='overlapping-land')
        body['features'].append(duplicate)
        self.assertEqual(len(self.batch(body).objects),3)

    def test_coastline_line_and_unknown_surface_do_not_become_sea(self):
        body=product();body['features'][0]['geometry']={'type':'LineString','coordinates':[[20,51],[20.01,51.01]]}
        with self.assertRaisesRegex(ContractError,'object_invalid'):self.batch(body)
        body=product();body['features'][0]['properties']['surface']='ocean-inferred'
        with self.assertRaisesRegex(ContractError,'origin_invalid'):self.batch(body)
        self.assertNotIn('land_water',layers_for({'natural':'coastline'}))
        self.assertNotIn('land_water',layers_for({'natural':'water'}))

    def test_version_limits_and_mixed_lineage_fail_closed(self):
        with self.assertRaisesRegex(ContractError,'version_required'):
            prepare_product(product(),bounds=BOUNDS,provenance=replace(self.provenance,source_dataset_at=None),dependencies=DEPS)
        with self.assertRaisesRegex(ContractError,'bounds'):
            prepare_product(product(),bounds=(0,0,10,10),provenance=self.provenance,dependencies=DEPS)
        batch=self.batch();obj=batch.objects[0]
        altered=replace(obj,land_water_origin=replace(obj.land_water_origin,dependencies=('c'*64,)))
        with self.assertRaisesRegex(ContractError,'mixed_product'):
            validate_partition((altered,*batch.objects[1:]),BOUNDS,'source-v1')

    def test_plain_observation_has_no_area_permission(self):
        f=self.fixture;batch=self.batch()
        f.world.publish_batch('query',f.owner,batch,provider='fixture',revision=1,
            storage_reference='fixture-storage-v1',fresh_until=f.fresh,usable_until=f.usable)
        self.assertEqual(self.read(BOUNDS).state,'MISS')

    def test_empty_and_duplicate_products_rejected(self):
        with self.assertRaisesRegex(ContractError,'feature_limit'):self.batch({'type':'FeatureCollection','features':[]})
        body=product();body['features'].append(body['features'][0])
        with self.assertRaisesRegex(ContractError,'duplicate_identity'):self.batch(body)

    def test_dashboard_does_not_claim_current_source_dependencies(self):
        from poi_infrastructure.world_dashboard import coverage
        self.publish()
        policy=dict(self.fixture.policy,scopes=['storage','world_storage'],
                    evidence={'reference':'fixture-storage-v1'})
        with self.fixture.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(policy),'fixture'))
        result=coverage(self.fixture.repo,layer='land_water')
        self.assertEqual(len(result['items']),1)
        self.assertTrue(result['items'][0]['policy_allowed'])
        self.assertFalse(result['items'][0]['local_read_allowed'])
        self.assertEqual(result['items'][0]['reason'],'source_dependencies_not_checked')
