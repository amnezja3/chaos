from dataclasses import replace
from contextlib import closing
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_world_shadow as fixtures
from poi_infrastructure.maplark_region import select, read, FLAG, PROFILE
from poi_infrastructure.world_adapters import normalize_maplark, plan_maplark_region, MAPLARK_VERSION
from poi_infrastructure.world_contract import ContractError, Provenance, POI_PROFILE
from poi_infrastructure.maplark_profile import export_maplark

ROOT=Path(__file__).parent/'fixtures/poi/maplark_radius_1635'
BOUNDS=(20.36,51.53,20.37,51.54)
SPATIAL=dict(lat=51.53357,lon=20.365,radius=300)


def batch(name, profile='poi'):
    return normalize_maplark(json.loads((ROOT/name/'body.json').read_text()),
        json.loads((ROOT/name/'headers.json').read_text()),
        Provenance('maplark',MAPLARK_VERSION,'fixture',time.time(),license_ref='ODbL-1.0'),profile=profile)


class SelectionTests(unittest.TestCase):
    def test_dense_paris_fixture_is_readable_without_weakening_completeness(self):
        from tools.world_paris_positions import inspect
        root=Path(__file__).parent/'fixtures/poi/maplark_paris_1635'
        result=inspect(root)
        self.assertEqual(result['selection_profile'],PROFILE)
        self.assertEqual(result['objects'],826)
        self.assertEqual([p['objects'] for p in result['positions']],[479,465])
        self.assertEqual(result['position_rejections'],{})
        self.assertFalse(result['acceptance_pass'])

    def test_real_pair_including_building_with_center_outside(self):
        self.assertEqual(select(batch('parent'),BOUNDS,**SPATIAL),
                         export_maplark(batch('radius',POI_PROFILE)))

    def test_outside_partial_and_mixed_sources_rejected(self):
        parent=batch('parent')
        for bad,spatial in [(replace(parent,completeness='partial'),SPATIAL),
                            (parent,dict(SPATIAL,lon=20.36))]:
            with self.assertRaises(ContractError):select(bad,BOUNDS,**spatial)
        changed=replace(parent.objects[0],provenance=replace(parent.objects[0].provenance,snapshot='other'))
        with self.assertRaises(ContractError):
            select(replace(parent,objects=(changed,)+parent.objects[1:]),BOUNDS,**SPATIAL)

    def test_near_boundary_does_not_reject_whole_scan_and_empty_is_valid(self):
        parent=batch('parent')
        self.assertEqual(select(replace(parent,objects=()),BOUNDS,**SPATIAL),{'elements':[]})
        # An object inside the former five-metre uncertainty band is now selected.
        obj=next(o for o in parent.objects if o.geometry.kind=='Point')
        lon,lat=obj.geometry.coordinates
        result=select(replace(parent,objects=(obj,)),BOUNDS,lat,lon,1)
        self.assertEqual(len(result['elements']),1)

    def test_explicit_inclusive_distance_boundary(self):
        features=[dict(type='Feature',id='node/'+str(i),properties={'tags':{'shop':'yes'}},
                       geometry=dict(type='Point',coordinates=[0,d/111195]))
                  for i,d in enumerate((299,300,301),1)]
        parent=normalize_maplark(dict(type='FeatureCollection',features=features),
            {'X-Returned':'3','X-Has-More':'false'},
            Provenance('maplark',MAPLARK_VERSION,'boundary',time.time(),license_ref='ODbL-1.0'),profile='poi')
        result=select(parent,(-.005,-.005,.005,.005),0,0,300)
        self.assertEqual([o['id'] for o in result['elements']],[1,2])

    def test_polygon_hole_and_multipart_do_not_use_bounds_center(self):
        outer=[[20.361,51.531],[20.369,51.531],[20.369,51.539],[20.361,51.539],[20.361,51.531]]
        hole=[[20.363,51.533],[20.367,51.533],[20.367,51.537],[20.363,51.537],[20.363,51.533]]
        far=[[20.361,51.531],[20.362,51.531],[20.362,51.532],[20.361,51.532],[20.361,51.531]]
        near=[[20.3649,51.5349],[20.3651,51.5349],[20.3651,51.5351],[20.3649,51.5351],[20.3649,51.5349]]
        features=[dict(type='Feature',id='relation/1',properties={'tags':{'amenity':'park'}},
                       geometry=dict(type='Polygon',coordinates=[outer,hole])),
                  dict(type='Feature',id='relation/2',properties={'tags':{'amenity':'park'}},
                       geometry=dict(type='MultiPolygon',coordinates=[[far],[near]]))]
        parent=normalize_maplark(dict(type='FeatureCollection',features=features),
            {'X-Returned':'2','X-Has-More':'false'},
            Provenance('maplark',MAPLARK_VERSION,'geometry',time.time(),license_ref='ODbL-1.0'),profile='poi')
        result=select(parent,BOUNDS,51.535,20.365,50)
        self.assertEqual([o['id'] for o in result['elements']],[2])


class ReaderTests(unittest.TestCase):
    setUp=fixtures.WorldShadowTests.setUp
    grant=fixtures.WorldShadowTests.grant

    def publish(self):
        candidate=self.grant()
        owner=self.service.repo.acquire('region-fixture',60)
        now=time.time()
        self.world.publish_batch('region-fixture',owner,batch('parent'),provider='maplark',
            revision=candidate['revision'],storage_reference=candidate['evidence']['reference'],
            fresh_until=now+300,usable_until=now+1800,
            observation_context=dict(acquisition='sector-bbox-v1',demand_bounds=BOUNDS,
                request_params=dict(plan_maplark_region(BOUNDS,profile='poi',limit=1000).params)))
        return candidate

    def test_reader_opt_in_no_network_and_no_writes(self):
        candidate=self.publish()
        self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True))
        with patch.dict(os.environ,{FLAG:'chaos-maplark-region-geometry-v1'}):
            self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True))
        with closing(self.service.repo.connect()) as c:
            before=[tuple(r) for r in c.execute('SELECT * FROM world_snapshot')]
        with patch.dict(os.environ,{FLAG:PROFILE}),patch('socket.create_connection',side_effect=AssertionError('network')):
            result=read(self.service,candidate,SPATIAL,lambda:True)
            self.assertEqual(result,export_maplark(batch('radius',POI_PROFILE)))
            self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:False))
            self.assertIsNone(read(self.service,dict(candidate,revision=999),SPATIAL,lambda:True))
        with closing(self.service.repo.connect()) as c:
            self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM world_snapshot')])

    def test_corrupt_falls_through(self):
        candidate=self.publish()
        with self.service.repo.transaction() as c:
            c.execute("UPDATE world_snapshot SET digest='broken'")
        with patch.dict(os.environ,{FLAG:PROFILE}):
            self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True))

    def test_diagnostic_distinguishes_position_expiry_and_metadata(self):
        candidate=self.publish()
        with patch.dict(os.environ,{FLAG:PROFILE}):
            trace={}
            self.assertIsNone(read(self.service,candidate,dict(SPATIAL,lon=20.36),lambda:True,diagnostic=trace))
            self.assertEqual(trace['rejected']['regional_circle_not_contained'],1)
            self.assertNotIn('lat',trace)
            trace={}
            self.assertIsNone(read(self.service,dict(candidate,revision=999),SPATIAL,lambda:True,diagnostic=trace))
            self.assertEqual(trace['rejected']['metadata_mismatch'],1)
            trace={}
            self.assertIsNotNone(read(self.service,candidate,SPATIAL,lambda:True,diagnostic=trace))
            self.assertEqual(trace['reason'],'selected')
            with patch('time.time',return_value=time.time()+301):
                trace={}
                self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True,diagnostic=trace))
                self.assertEqual(trace['rejected']['not_fresh'],1)

    def test_active_scanner_reads_region_before_upstream(self):
        from poi_infrastructure.maplark_pilot import fetch_pilot
        from poi_infrastructure.world_contract import FILTERS
        self.publish()
        spatial=dict(SPATIAL,filters=FILTERS)
        with patch.dict(os.environ,{FLAG:PROFILE,'CHAOS_POI_WORLD_ACCESS_MODE':'global'}), \
                patch('poi_infrastructure.maplark_pilot.acquire_maplark',side_effect=AssertionError('upstream')):
            data,source=fetch_pilot(self.service,spatial,300,1800,lambda:True,world_user='second-user')
        self.assertEqual(source,'world')
        self.assertEqual(len(data['elements']),18)

    def test_age_does_not_renew_on_read(self):
        candidate=self.publish()
        now=time.time()
        with patch.dict(os.environ,{FLAG:PROFILE}),patch('time.time',return_value=now+301):
            self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True))
            self.assertIsNotNone(read(self.service,candidate,SPATIAL,lambda:True,allow_stale=True))
        with patch.dict(os.environ,{FLAG:PROFILE}),patch('time.time',return_value=now+1801):
            self.assertIsNone(read(self.service,candidate,SPATIAL,lambda:True,allow_stale=True))


if __name__=='__main__':unittest.main()
