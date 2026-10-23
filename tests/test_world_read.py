from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import SelectionProof, WorldReadPlanner, AREA_SELECTION
from poi_infrastructure.world_contract import (WorldObject,Geometry,Provenance,ProviderBatch,ContractError)


class LocalWorldReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3')
        Registry(self.repo).initialize()
        self.world=CanonicalWorldRepository(self.repo)
        self.world.initialize_canonical()
        self.owner=self.repo.acquire('query',120)
        self.now=time.time()
        self.fresh=self.now+300
        self.usable=self.now+1800
        self.policy=dict(enabled=True,policy_status='approved_for_defined_use',scopes=['storage'],review_due_at=self.now+3600)
        with self.repo.transaction() as c:
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('fixture',1,json.dumps(self.policy)))
        self.planner=WorldReadPlanner(self.world)

    def object(self, ident=1, geometry=None, tags=None):
        return WorldObject.create(external_id=str(ident),tags=tags or {'shop':'books'},
            geometry=Geometry.parse(geometry or dict(type='Point',coordinates=[2,2])),
            marker=[2,2],marker_method='source_point',ordinal=ident,osm_type='node',osm_id=ident,
            provenance=Provenance('fixture','adapter-v1','source-v1',self.now,license_ref='fixture-only'))

    def exact(self, objects=None, completeness='complete'):
        batch=ProviderBatch((self.object(),) if objects is None else tuple(objects),'poi-gameplay-v1',
                            completeness,(),'maplark-radius-unverified','source')
        proof=SelectionProof('exact','poi',batch.profile,batch.selection,'adapter-v1','query')
        return batch,proof

    def area(self, objects=None, bounds=(0,0,10,10), layer='roads'):
        objects=objects if objects is not None else [self.object(geometry=dict(type='LineString',coordinates=[[-5,5],[15,5]]),tags={'highway':'road'})]
        batch=ProviderBatch(tuple(objects),layer,'complete',(),AREA_SELECTION,'source')
        proof=SelectionProof('area',layer,layer,AREA_SELECTION,'adapter-v1','query',bounds,'fixture-contract')
        return batch,proof

    def publish(self,batch,proof,certified=True):
        certificates=(('fixture','adapter-v1',proof.layer,proof.selection,'fixture-contract'),) if certified else ()
        return self.world.publish_batch('query',self.owner,batch,provider='fixture',revision=1,
            storage_reference='fixture-storage-v1',fresh_until=self.fresh,usable_until=self.usable,
            coverage=proof,certified_selections=certificates)

    def read(self,**kwargs):
        options=dict(provider='fixture',revision=1,storage_reference='fixture-storage-v1',profile='poi-gameplay-v1',
            selection='maplark-radius-unverified',adapter_version='adapter-v1',query_key='query')
        options.update(kwargs)
        return self.planner.read(**options)

    def read_area(self,bounds,layer='roads',**kwargs):
        return self.read(query_key=None,bounds=bounds,layer=layer,profile=layer,selection=AREA_SELECTION,**kwargs)

    def test_exact_survives_restart_and_disabled_network_without_http(self):
        batch,proof=self.exact()
        self.publish(batch,proof)
        self.policy['enabled']=False
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=?',(json.dumps(self.policy),))
        self.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(self.repo.path)))
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            result=self.read()
        self.assertEqual(result.state,'COMPLETE_FRESH')
        self.assertEqual(result.batch,batch)
        self.assertEqual(self.read(query_key='nearby').state,'MISS')

    def test_maplark_response_never_becomes_area_coverage(self):
        batch,proof=self.exact()
        self.publish(batch,proof)
        self.assertEqual(self.read_area((1,1,3,3)).state,'MISS')
        with self.assertRaises(ContractError):
            replace(proof,mode='area',bounds=(0,0,10,10),certificate='anything')

    def test_area_requires_separate_certificate_and_complete_geometry(self):
        batch,proof=self.area()
        with self.assertRaisesRegex(ContractError,'not_certified'):
            self.publish(batch,proof,certified=False)
        missing=replace(batch,objects=(replace(batch.objects[0],geometry=None),))
        with self.assertRaisesRegex(ContractError,'geometry_incomplete'):
            self.publish(missing,proof)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_coverage').fetchone()[0],0)

    def test_neighbor_region_long_line_and_layer_isolation(self):
        batch,proof=self.area()
        self.publish(batch,proof)
        for bounds in ((1,4,2,6),(8,4,9,6)):
            result=self.read_area(bounds)
            self.assertEqual(result.state,'COMPLETE_FRESH')
            self.assertEqual(result.batch.objects,batch.objects)
        self.assertEqual(self.read_area((1,4,2,6),'waterways').state,'MISS')
        self.assertEqual(self.read_area((9,4,11,6)).state,'MISS')

    def test_lake_hole_is_proven_empty_not_unknown(self):
        shell=[[0,0],[10,0],[10,10],[0,10],[0,0]]
        hole=[[2,2],[2,4],[4,4],[4,2],[2,2]]
        lake=self.object(geometry=dict(type='Polygon',coordinates=[shell,hole]),tags={'natural':'water'})
        batch,proof=self.area([lake],layer='inland_water')
        self.publish(batch,proof)
        result=self.read_area((2.5,2.5,3.5,3.5),'inland_water')
        self.assertEqual(result.state,'COMPLETE_FRESH')
        self.assertEqual(result.batch.objects,())

    def test_empty_complete_is_distinct_from_missing_or_partial(self):
        self.assertEqual(self.read().state,'MISS')
        batch,proof=self.exact([],completeness='partial')
        with self.assertRaisesRegex(ContractError,'not_complete'):
            self.publish(batch,proof)
        batch,proof=self.exact([])
        self.publish(batch,proof)
        self.assertEqual(self.read().batch.objects,())
        self.assertEqual(self.read().state,'COMPLETE_FRESH')

    def test_fresh_stale_expired_with_explicit_stale_opt_in(self):
        self.publish(*self.exact())
        with patch('poi_infrastructure.world_read.time.time',return_value=self.fresh+1):
            self.assertEqual(self.read().state,'MISS')
            self.assertEqual(self.read(allow_stale=True).state,'COMPLETE_STALE')
        with patch('poi_infrastructure.world_read.time.time',return_value=self.usable+1):
            self.assertEqual(self.read(allow_stale=True).state,'MISS')

    def test_revision_mapping_storage_and_order_contract_are_not_mixed(self):
        self.publish(*self.exact())
        for options in (dict(revision=2),dict(adapter_version='v2'),dict(profile='other'),
                        dict(selection='other'),dict(storage_reference='not-approved')):
            self.assertEqual(self.read(**options).state,'MISS')
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET revision=2')
        self.assertEqual(self.read().state,'MISS')

    def test_revoked_or_expired_storage_is_not_usable(self):
        self.publish(*self.exact())
        self.policy['scopes']=[]
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=?',(json.dumps(self.policy),))
        self.assertEqual(self.read().state,'MISS')

    def test_no_union_across_two_incomplete_regions(self):
        for bounds in ((0,0,4,10),(6,0,10,10)):
            self.publish(*self.area(bounds=bounds))
        self.assertEqual(self.read_area((1,1,9,9)).state,'MISS')

    def test_forged_coverage_metadata_does_not_expand_snapshot(self):
        snapshot=self.publish(*self.area(bounds=(0,0,4,10)))
        with self.repo.transaction() as c:
            row=c.execute('SELECT bounds FROM world_coverage WHERE snapshot_id=?',(snapshot,)).fetchone()
            forged=json.loads(row[0]); forged['bounds']=[0,0,10,10]
            c.execute('UPDATE world_coverage SET bounds=?',(json.dumps(forged),))
        self.assertEqual(self.read_area((1,1,9,9)).state,'MISS')

    def test_cancellation_and_limit_do_not_return_partial_success(self):
        self.publish(*self.exact([self.object(1),self.object(2)]))
        self.assertEqual(self.read(still_active=lambda:False).state,'CANCELLED')
        calls=[]
        def active():
            calls.append(1)
            return len(calls)<3
        self.assertEqual(self.read(still_active=active).state,'CANCELLED')
        self.assertEqual(self.read(max_objects=1).reason,'local_result_limit')

    def test_expiry_during_read_and_deadline_are_misses(self):
        self.publish(*self.exact())
        clock=[time.time()]*3+[self.usable+1]*10
        with patch('poi_infrastructure.world_read.time.time',side_effect=clock):
            self.assertEqual(self.read().state,'MISS')
        with patch('poi_infrastructure.world_read.time.monotonic',side_effect=[0,3]):
            self.assertEqual(self.read().reason,'local_read_deadline')

    def test_coastline_is_not_ocean_and_dateline_has_no_proof(self):
        with self.assertRaises(ContractError):
            self.area([],layer='land_water')
        line=self.object(geometry=dict(type='LineString',coordinates=[[179,0],[-179,0]]),tags={'natural':'coastline'})
        with self.assertRaisesRegex(ContractError,'geometry_incomplete'):
            self.publish(*self.area([line],layer='coastline'))

    def test_later_fetch_of_older_dataset_does_not_replace_pinned_version(self):
        current=self.object()
        current=replace(current,provenance=replace(current.provenance,source_dataset_at='2026-10-23'))
        batch,proof=self.exact([current])
        self.publish(batch,replace(proof,dataset_version='2026-10-23'))
        old=replace(current,tags=(('shop','clothes'),),
                    provenance=replace(current.provenance,source_dataset_at='2026-10-20'))
        old_batch,old_proof=self.exact([old])
        self.publish(old_batch,replace(old_proof,dataset_version='2026-10-20'))
        self.assertEqual(self.read(dataset_version='2026-10-23').batch,batch)
        self.assertEqual(self.read().state,'MISS')
        with self.assertRaisesRegex(ContractError,'dataset_mismatch'):
            self.publish(old_batch,proof)

    def test_exact_maplark_roundtrip_preserves_real_scanner_categories_and_limit(self):
        import overpy
        from poiFetchClass import POIFetcher
        from poi_infrastructure.maplark_profile import export_maplark
        from poi_infrastructure.world_adapters import normalize_maplark, MAPLARK_VERSION
        from poi_infrastructure.world_contract import FILTERS, POI_PROFILE
        features=[]
        for ident in range(1,75):
            tags={'shop':'books','name':f'fixture {ident}'}
            if ident==1: tags={'amenity':'bank','atm':'yes','internet_access':'wlan'}
            if ident==2: tags={'amenity':'atm'}
            if ident==3: tags={'man_made':'surveillance'}
            features.append(dict(type='Feature',id=f'node/{ident}',properties={'tags':tags},
                geometry=dict(type='Point',coordinates=[21+ident*.0001,52])))
        batch=normalize_maplark(dict(type='FeatureCollection',features=features),
            {'X-Returned':'74','X-Has-More':'false'},
            Provenance('maplark',MAPLARK_VERSION,'fixture',self.now,license_ref='fixture-only'))
        with self.repo.transaction() as c:
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('maplark',1,json.dumps(self.policy)))
        proof=SelectionProof('exact','poi',POI_PROFILE,batch.selection,MAPLARK_VERSION,'query')
        self.world.publish_batch('query',self.owner,batch,provider='maplark',revision=1,
            storage_reference='fixture-only',fresh_until=self.fresh,usable_until=self.usable,coverage=proof)
        result=self.read(provider='maplark',adapter_version=MAPLARK_VERSION,storage_reference='fixture-only')
        self.assertEqual(result.state,'COMPLETE_FRESH')
        fetcher=POIFetcher(tag_filters=list(FILTERS))
        with patch.object(fetcher,'_fetch',return_value=overpy.Result.from_json(export_maplark(batch))):
            expected=fetcher._get_all(52,21)
        with patch.object(fetcher,'_fetch',return_value=overpy.Result.from_json(export_maplark(result.batch))):
            actual=fetcher._get_all(52,21)
        self.assertEqual(actual,expected)
        self.assertEqual(len(actual),60)


if __name__=='__main__':
    unittest.main()
