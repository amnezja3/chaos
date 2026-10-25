"""Recorded lake with two holes; certificates/time in storage tests are synthetic."""
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from shapely.geometry import Polygon,box,shape
import test_world_read
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_adapters import MAPLARK_VERSION,normalize_maplark,plan_maplark_region
from poi_infrastructure.world_contract import Provenance,ContractError
from poi_infrastructure.world_region_candidate import prepare
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import WorldReadPlanner
from tools.world_region_plan import evaluate


BOUNDS=(16.79,52.26,16.8,52.27)


class WaterHolesReferenceTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).parent/'fixtures/poi/maplark_inland_water_holes_20261025'
        raw=base.with_suffix('.json').read_bytes()
        self.meta=json.loads(base.with_suffix('.metadata.json').read_text(encoding='utf8'))
        self.assertEqual(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),self.meta['fixture_sha256_lf'])
        self.body=json.loads(raw)
        batch=normalize_maplark(self.body,self.meta['headers'],Provenance('maplark',MAPLARK_VERSION,
            'recorded-lake-holes',self.meta['fetched_at'],license_ref='ODbL-1.0'),profile='inland_water',maximum=1000)
        self.candidate=prepare(batch,plan_maplark_region(BOUNDS,profile='inland_water'))
        self.obj=self.candidate.batch.objects[0]
        self.geometry=shape(self.obj.geometry.geojson())

    def storage(self):
        fixture=test_world_read.LocalWorldReadTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        # Keep all real geometry. Only test provenance, clock and certificate change.
        obj=replace(self.obj,provenance=Provenance('fixture','adapter-v1','lake-holes',
                    fixture.now,license_ref='ODbL-1.0'))
        batch,proof=fixture.area([obj],bounds=BOUNDS,layer='inland_water')
        return fixture,batch,proof

    @staticmethod
    def inside_bounds(geometry):
        point=geometry.representative_point()
        size=1e-5
        for _ in range(20):
            bounds=(point.x-size,point.y-size,point.x+size,point.y+size)
            if geometry.contains(box(*bounds)):return bounds
            size/=2
        raise AssertionError('No strictly interior test box')

    def test_recorded_counts_identity_and_topology(self):
        self.assertEqual(self.obj.identity,'osm:relation:3654250')
        self.assertEqual(self.obj.geometry.kind,'Polygon')
        self.assertEqual([len(r) for r in self.body['features'][0]['geometry']['coordinates']],[608,40,46])
        self.assertEqual(self.obj.geometry.geojson(),self.body['features'][0]['geometry'])
        self.assertEqual(self.candidate.excluded_ids,())
        report=evaluate(BOUNDS,'inland_water',self.body,self.meta['headers'])
        self.assertTrue(report['topology']['water_surface_with_holes_observed'])
        self.assertFalse(report['topology']['water_multipolygon_observed'])
        self.assertEqual(report['topology']['interior_rings'],2)
        self.assertFalse(report['region_certified'])
        self.assertEqual(report['neighbor_candidates'],dict(left=1,right=1,crossing=1))

    def test_both_rings_survive_reopen_backup_restore_and_neighbor_selection(self):
        fixture,batch,proof=self.storage();fixture.publish(batch,proof)
        restored=Path(fixture.tmp.name)/'restored.sqlite3'
        with closing(fixture.repo.connect()) as source,closing(sqlite3.connect(restored)) as dest:
            source.backup(dest)
            self.assertEqual(dest.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(dest.execute('PRAGMA foreign_key_check').fetchall(),[])
        with patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
            for db in (fixture.repo.path,restored):
                fixture.planner=WorldReadPlanner(CanonicalWorldRepository(Repository(db)))
                for bounds in (BOUNDS,(16.79,52.26,16.795,52.27),(16.795,52.26,16.8,52.27)):
                    result=fixture.read_area(bounds,'inland_water')
                    self.assertEqual(result.state,'COMPLETE_FRESH')
                    self.assertEqual(result.batch.objects,batch.objects)
                    self.assertEqual(result.batch.objects[0].geometry,self.obj.geometry)

    def test_island_is_empty_water_but_outside_hole_has_no_coverage(self):
        fixture,batch,proof=self.storage();fixture.publish(batch,proof)
        area=box(*BOUNDS)
        holes=[Polygon(ring) for ring in self.geometry.interiors]
        outside=[h for h in holes if not h.intersects(area)]
        inside=[h.intersection(area) for h in holes if h.intersects(area)]
        self.assertEqual((len(outside),len(inside)),(1,1))
        with patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
            island=fixture.read_area(self.inside_bounds(inside[0]),'inland_water')
            self.assertEqual(island.state,'COMPLETE_FRESH')
            self.assertEqual(island.batch.objects,())
            self.assertEqual(fixture.read_area(self.inside_bounds(outside[0]),'inland_water').state,'MISS')
            water=fixture.read_area(self.inside_bounds(self.geometry.intersection(area)),'inland_water')
            self.assertEqual(water.batch.objects,batch.objects)
            self.assertEqual(fixture.read_area(BOUNDS,'land_water').state,'MISS')

    def test_real_holes_do_not_supply_a_provider_area_certificate(self):
        fixture,batch,proof=self.storage()
        with self.assertRaisesRegex(ContractError,'not_certified'):
            fixture.publish(batch,proof,certified=False)
        fixture.world.publish_batch('query',fixture.owner,batch,provider='fixture',revision=1,
            storage_reference='fixture-storage-v1',fresh_until=fixture.fresh,usable_until=fixture.usable)
        self.assertEqual(fixture.read_area(BOUNDS,'inland_water').state,'MISS')


if __name__=='__main__':unittest.main()
