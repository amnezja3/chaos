"""Synthetic topology and bounded HTTP fixtures; no live water qualification."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_world_read
import test_world_region_probe
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_adapters import MAPLARK_VERSION,normalize_maplark,plan_maplark_region
from poi_infrastructure.world_contract import Provenance,ContractError
from poi_infrastructure.world_read import WorldReadPlanner
from poi_infrastructure.world_region_candidate import prepare
from poi_infrastructure.world_storage import CanonicalWorldRepository
from tools.world_region_plan import evaluate
from tools.world_region_probe import capture,BOUNDS


SHELL=[[20.36,51.53],[20.37,51.53],[20.37,51.54],[20.36,51.54],[20.36,51.53]]
HOLE=[[20.362,51.532],[20.362,51.534],[20.364,51.534],[20.364,51.532],[20.362,51.532]]
SECOND=[[20.38,51.53],[20.381,51.53],[20.381,51.531],[20.38,51.531],[20.38,51.53]]


def water_body(kind='MultiPolygon'):
    geometry=dict(type=kind,coordinates=[[SHELL,HOLE],[SECOND]] if kind=='MultiPolygon' else [SHELL,HOLE])
    return dict(type='FeatureCollection',features=[dict(type='Feature',id='relation/123',
        properties=dict(tags={'natural':'water','type':'multipolygon'}),geometry=geometry)])


HEADERS={'X-Returned':'1','X-Has-More':'false','X-Usage-Units-Charged':'3'}


def normalized(body,profile='inland_water'):
    return normalize_maplark(body,HEADERS,Provenance('maplark',MAPLARK_VERSION,'synthetic-water',1),
                             profile=profile,maximum=1000)


class WaterGeometryTests(unittest.TestCase):
    def test_candidate_retains_multipart_holes_and_outside_parts(self):
        batch=normalized(water_body())
        candidate=prepare(batch,plan_maplark_region(BOUNDS,profile='inland_water'))
        self.assertEqual(candidate.batch.objects,batch.objects)
        self.assertEqual(candidate.batch.objects[0].geometry.geojson()['coordinates'],water_body()['features'][0]['geometry']['coordinates'])
        self.assertFalse(candidate.region_certified)

    def test_inspection_reports_holes_without_certifying_islands(self):
        report=evaluate(BOUNDS,'inland_water',water_body(),HEADERS)
        self.assertEqual(report['topology']['polygon_parts'],2)
        self.assertEqual(report['topology']['interior_rings'],1)
        self.assertTrue(report['topology']['water_surface_with_holes_observed'])
        self.assertEqual(report['candidate']['status'],'prepared_not_certified')
        self.assertFalse(report['region_certified'])

    def test_surface_point_cannot_be_qualified_as_lake(self):
        body=water_body();body['features'][0]['geometry']=dict(type='Point',coordinates=[20.365,51.535])
        with self.assertRaisesRegex(ContractError,'water_surface_required'):
            prepare(normalized(body),plan_maplark_region(BOUNDS,profile='inland_water'))
        report=evaluate(BOUNDS,'inland_water',body,HEADERS)
        self.assertEqual(report['candidate']['status'],'blocked')
        self.assertFalse(report['topology']['water_surface_with_holes_observed'])

    def test_crossing_waterway_keeps_both_outside_endpoints(self):
        body=water_body()
        body['features'][0].update(id='way/5',properties=dict(tags={'waterway':'stream'}),
            geometry=dict(type='LineString',coordinates=[[20.35,51.535],[20.38,51.535]]))
        batch=normalized(body,'waterways')
        candidate=prepare(batch,plan_maplark_region(BOUNDS,profile='waterways'))
        self.assertEqual(candidate.batch.objects,batch.objects)
        self.assertEqual(evaluate(BOUNDS,'waterways',body,HEADERS)['neighbor_candidates'],dict(left=1,right=1,crossing=1))

    def test_hole_selects_no_water_and_restore_preserves_other_parts(self):
        fixture=test_world_read.LocalWorldReadTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        obj=normalized(water_body()).objects[0]
        obj=replace(obj,provenance=Provenance('fixture','adapter-v1','water-fixture',fixture.now,license_ref='synthetic'))
        batch,proof=fixture.area([obj],bounds=BOUNDS,layer='inland_water')
        fixture.publish(batch,proof)  # Synthetic certificate only, never MapLark approval.
        restored=Path(fixture.tmp.name)/'restored.sqlite3'
        with closing(fixture.repo.connect()) as src,closing(sqlite3.connect(restored)) as dst:
            src.backup(dst)
            self.assertEqual(dst.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(restored)))
        with patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
            hole=fixture.read_area((20.3625,51.5325,20.3635,51.5335),'inland_water')
            self.assertEqual(hole.state,'COMPLETE_FRESH');self.assertEqual(hole.batch.objects,())
            water=fixture.read_area((20.365,51.535,20.369,51.539),'inland_water')
            self.assertEqual(water.batch.objects[0].geometry,obj.geometry)
            # An outside polygon part is stored, but grants no coverage beyond the proof.
            self.assertEqual(fixture.read_area((20.38,51.53,20.381,51.531),'inland_water').state,'MISS')
            self.assertEqual(fixture.read_area(BOUNDS,'waterways').state,'MISS')

    def test_partial_or_coastline_cannot_inherit_water_candidate(self):
        batch=normalized(water_body())
        with self.assertRaisesRegex(ContractError,'incomplete'):
            prepare(replace(batch,completeness='partial'),plan_maplark_region(BOUNDS,profile='inland_water'))
        with self.assertRaisesRegex(ContractError,'profile_unqualified'):
            prepare(replace(batch,profile='coastline'),plan_maplark_region(BOUNDS,profile='coastline'))


class WaterProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_world_region_probe.RegionProbeTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def call(self,profile):
        return capture(self.fixture.repo.path,Path(self.fixture.tmp.name)/profile,profile=profile,
                       execute=True,approve=True,accept_variable_cost=True,transport=self.fixture.transport)

    def test_profiles_share_budget_but_not_operation_and_never_ingest(self):
        water=water_body()
        stream=dict(type='FeatureCollection',features=[dict(type='Feature',id='way/1',
            properties=dict(tags={'waterway':'stream'}),geometry=dict(type='LineString',coordinates=[[20.35,51.535],[20.38,51.535]]))])
        self.fixture.transport.side_effect=[(200,None,dict(body=b,response_headers=HEADERS)) for b in (stream,water)]
        reports=[self.call(profile) for profile in ('waterways','inland_water')]
        self.assertNotEqual(reports[0]['operation'],reports[1]['operation'])
        self.assertEqual([r['params']['tags'] for r in reports],['waterway','natural=water'])
        self.assertTrue(all(not r['world_ingest'] and not r['region_certified'] for r in reports))
        scope=self.fixture.ledger.scope_status('maplark','region-probe:water-2036-5153-bbox-v1')
        self.assertEqual((scope['credit_limit'],scope['committed']),(40,6))
        with self.assertRaisesRegex(ContractError,'already_used'):self.call('waterways')
        self.assertEqual(self.fixture.transport.call_count,2)

    def test_no_implicit_water_pilot_neighbors_or_coastline_network(self):
        for kwargs in (dict(profile='waterways',_pilot=True),dict(profile='inland_water',part='left'),dict(profile='coastline')):
            with self.assertRaises(ContractError):capture(self.fixture.repo.path,execute=True,**kwargs)
        self.fixture.transport.assert_not_called()

    def test_empty_probe_is_not_island_evidence(self):
        self.fixture.transport.return_value=(200,None,dict(body=dict(type='FeatureCollection',features=[]),
            response_headers={'X-Returned':'0','X-Has-More':'false','X-Usage-Units-Charged':'1'}))
        result=self.call('inland_water')
        self.assertFalse(result['inspection']['topology']['water_surface_with_holes_observed'])
        self.assertFalse(result['region_certified'])


if __name__=='__main__':unittest.main()
