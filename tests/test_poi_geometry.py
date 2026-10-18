import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import overpy
from poiFetchClass import POIFetcher
from poi_infrastructure.geometry import GeometrySnapshot, CoveredGeometry, UncertifiedGeometry, EARTH_RADIUS

FIXTURE = Path(__file__).parent / 'fixtures' / 'poi'
FILTERS = ['shop', 'amenity', 'office', 'healthcare', 'atm=yes', 'man_made=surveillance']


def source_elements():
    result = []
    for item in ET.parse(FIXTURE / 'geometry_source.osm').getroot():
        e = dict(type=item.tag, id=int(item.attrib['id']))
        tags = {t.attrib['k']:t.attrib['v'] for t in item.findall('tag')}
        if tags:
            e['tags'] = tags
        if item.tag == 'node':
            e.update(lat=float(item.attrib['lat']), lon=float(item.attrib['lon']))
        elif item.tag == 'way':
            e['nodes'] = [int(n.attrib['ref']) for n in item.findall('nd')]
        else:
            e['members'] = [dict(type=m.attrib['type'], ref=int(m.attrib['ref']), role=m.attrib['role']) for m in item.findall('member')]
        result.append(e)
    return result


class GeometryParityTests(unittest.TestCase):
    def test_actual_wide_response_against_independent_exact_answers(self):
        wide = json.loads((FIXTURE/'geometry_wide_reference.json').read_text())
        reference = json.loads((FIXTURE/'geometry_reference.json').read_text())
        self.assertNotIn('remark',wide)
        self.assertEqual(wide['generator'],reference['cases']['origin']['response']['generator'])
        self.assertEqual(wide['osm3s'],reference['cases']['origin']['response']['osm3s'])
        self.assertEqual(len(wide['elements']),19)
        source = {(e['type'],e['id']):e for e in source_elements()}
        for element in wide['elements']:
            self.assertEqual(element,source[element['type'],element['id']])
        covered = CoveredGeometry(wide,0,0,1500,FILTERS)
        for name,case in reference['cases'].items():
            if name == 'empty':
                with self.assertRaisesRegex(UncertifiedGeometry,'outside_coverage'):
                    covered.select(case['lat'],case['lon'],case['radius'],FILTERS)
                continue
            with self.subTest(name=name):
                result = covered.select(case['lat'],case['lon'],case['radius'],FILTERS)
                self.assertEqual(result['elements'],case['response']['elements'])
                for limit in (0,2,60):
                    fetcher = POIFetcher(tag_filters=FILTERS)
                    with patch.object(fetcher,'_fetch',return_value=overpy.Result.from_json(case['response'])):
                        expected = fetcher.get_all(case['lat'],case['lon'],limit)
                    with patch.object(fetcher,'_fetch',return_value=overpy.Result.from_json(result)):
                        self.assertEqual(fetcher.get_all(case['lat'],case['lon'],limit),expected)

    def test_independent_reference_source_and_wire_queries(self):
        reference = json.loads((FIXTURE / 'geometry_reference.json').read_text())
        # Binary fixture hash preserves the exact imported bytes, including CRLF.
        self.assertEqual(hashlib.sha256((FIXTURE / 'geometry_source.osm').read_bytes()).hexdigest(), reference['source_sha256'])
        self.assertEqual(len(reference['cases']), 6)
        for case in reference['cases'].values():
            fetcher = POIFetcher(radius=case['radius'], tag_filters=FILTERS)
            self.assertEqual(fetcher._build_query(case['lat'], case['lon']), case['query'])
            self.assertEqual(case['response']['generator'], 'Overpass API 0.7.62.3 00a720d2')

    def test_six_reference_results_and_gameplay_output(self):
        reference = json.loads((FIXTURE / 'geometry_reference.json').read_text())
        snapshot = GeometrySnapshot(source_elements())
        for name, case in reference['cases'].items():
            with self.subTest(name=name):
                local = snapshot.select(case['lat'], case['lon'], case['radius'], FILTERS)
                self.assertEqual(local['elements'], case['response']['elements'])
                # Compare real facade ordering, categories, coordinate dedup and
                # limits, not a reimplementation of gameplay formatting.
                for limit in (0, 2, 60):
                    fetcher = POIFetcher(tag_filters=FILTERS)
                    with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(case['response'])):
                        expected = fetcher.get_all(case['lat'],case['lon'],limit)
                    with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(local)):
                        self.assertEqual(fetcher.get_all(case['lat'],case['lon'],limit), expected)

    def test_missing_geometry_invalidates_whole_selection(self):
        elements = [e for e in source_elements() if e['id'] != 11]
        with self.assertRaisesRegex(UncertifiedGeometry, 'missing_member'):
            GeometrySnapshot(elements).select(0,0,300,FILTERS)

    def test_full_circle_and_filter_coverage_required(self):
        coverage = CoveredGeometry(dict(elements=source_elements()),0,0,1500,FILTERS)
        reference = json.loads((FIXTURE / 'geometry_reference.json').read_text())
        for name in ('origin','nearby','edge','small','larger'):
            c = reference['cases'][name]
            self.assertEqual(coverage.select(c['lat'],c['lon'],c['radius'],FILTERS)['elements'],c['response']['elements'])
        for lat, lon, radius in [(0,.012,300),(1,1,300),(0,0,1500)]:
            with self.assertRaisesRegex(UncertifiedGeometry,'outside_coverage'):
                coverage.select(lat,lon,radius,FILTERS)
        with self.assertRaisesRegex(UncertifiedGeometry,'filter_profile'):
            coverage.select(0,0,300,['shop'])

    def test_boundary_and_unverified_regions_defer(self):
        import math
        node = dict(type='node', id=1, lat=0, lon=math.degrees(300/EARTH_RADIUS), tags={'shop':'books'})
        with self.assertRaisesRegex(UncertifiedGeometry, 'boundary_uncertain'):
            GeometrySnapshot([node]).select(0,0,300,FILTERS)
        for lat, lon in [(85,0),(0,179.9)]:
            with self.assertRaises(UncertifiedGeometry):
                GeometrySnapshot([]).select(lat,lon,300,FILTERS)

    def test_duplicate_and_nested_center_rejected_and_private_copy(self):
        elements = source_elements()
        with self.assertRaisesRegex(UncertifiedGeometry, 'duplicate'):
            GeometrySnapshot(elements+[copy.deepcopy(elements[0])])
        snapshot = GeometrySnapshot(elements)
        first = snapshot.select(0,0,300,FILTERS)
        first['elements'][0]['tags']['shop'] = 'changed'
        self.assertEqual(snapshot.select(0,0,300,FILTERS)['elements'][0]['tags']['shop'], 'books')
        for e in elements:
            if e['type']=='relation' and e['id']==200:
                e['members'].append(dict(type='relation', ref=201, role=''))
        with self.assertRaisesRegex(UncertifiedGeometry, 'nested_center'):
            GeometrySnapshot(elements).select(0,0,300,FILTERS)


if __name__ == '__main__':
    unittest.main()
