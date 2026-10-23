import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import overpy
from poiFetchClass import POIFetcher
from poi_infrastructure.maplark_candidate import preview_maplark
from poi_infrastructure.world_adapters import MAPLARK_VERSION, normalize_maplark
from poi_infrastructure.world_contract import ContractError, FILTERS, Provenance

FIXTURES = Path(__file__).parent / 'fixtures/poi'


def batch(features, headers=None):
    return normalize_maplark({'type': 'FeatureCollection', 'features': features},
        headers or {'X-Returned': str(len(features)), 'X-Has-More': 'false'},
        Provenance('maplark', MAPLARK_VERSION, 'synthetic', 1))


def feature(kind, identity, geometry, tags):
    return dict(type='Feature', id=f'{kind}/{identity}', geometry=geometry,
                properties={'tags': tags, 'centroid': [99, 77]})


def facade(raw, lat=0, lon=0):
    fetcher = POIFetcher(tag_filters=list(FILTERS))
    with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(raw)):
        return fetcher._get_all(lat, lon)


class MaplarkCandidateTests(unittest.TestCase):
    def test_nodes_ways_against_six_independent_overpass_answers(self):
        # Convert saved OSM source geometry, NOT expected output, to synthetic
        # MapLark shape. Relations deliberately excluded on BOTH sides.
        wide = json.loads((FIXTURES / 'geometry_wide_reference.json').read_text())
        source = {(e['type'], e['id']): e for e in wide['elements']}
        features = []
        for e in wide['elements']:
            if not e.get('tags') or e['type'] == 'relation':
                continue
            if e['type'] == 'node':
                geometry = dict(type='Point', coordinates=[e['lon'], e['lat']])
            else:
                points = [[source['node', n]['lon'], source['node', n]['lat']] for n in e['nodes']]
                closed = points[0] == points[-1]
                geometry = dict(type='Polygon' if closed else 'LineString',
                                coordinates=[points] if closed else points)
            features.append(feature(e['type'], e['id'], geometry, e['tags']))
        candidate = batch(list(reversed(features)))
        reference = json.loads((FIXTURES / 'geometry_reference.json').read_text())
        for name, case in reference['cases'].items():
            with self.subTest(name=name):
                result = preview_maplark(candidate, case['lat'], case['lon'], case['radius'])
                expected = {'elements': [e for e in case['response']['elements'] if e['type'] != 'relation']}
                # GeoJSON has coordinates, not OSM vertex IDs. Compare fields
                # consumed by gameplay, then run the untouched full reference
                # through the real facade as an independent second check.
                projected = copy.deepcopy(expected)
                for element in projected['elements']:
                    element.pop('nodes', None)
                self.assertEqual(result['response'], projected)
                self.assertEqual(facade(result['response']), facade(expected))
                self.assertFalse(result['gameplay_approved'])
        with self.assertRaises(ContractError):
            candidate.export_overpass()

    def test_order_limit_and_original_tags_survive(self):
        features = [feature('node', i, dict(type='Point', coordinates=[i * .00001, 0]),
                    {'amenity': 'bank', 'atm': 'yes', 'internet_access': 'wlan', 'addr:city': 'Test'})
                    for i in range(1, 66)]
        left = preview_maplark(batch(features), 0, 0, 300)['response']
        right = preview_maplark(batch(list(reversed(features))), 0, 0, 300)['response']
        self.assertEqual(left, right)
        self.assertEqual([e['osm_id'] for e in facade(right)], list(range(1, 61)))
        self.assertEqual(right['elements'][0]['tags'], features[0]['properties']['tags'])

    def test_partial_and_unsupported_objects_reject_whole_preview(self):
        point = feature('node', 1, dict(type='Point', coordinates=[0, 0]), {'shop': 'books'})
        relation = feature('relation', 2, dict(type='Point', coordinates=[0, 0]), {'office': 'company'})
        with self.assertRaisesRegex(ContractError, 'member_topology'):
            preview_maplark(batch([point, relation]), 0, 0, 300)
        with self.assertRaisesRegex(ContractError, 'incomplete'):
            preview_maplark(batch([point], {'X-Returned': '1', 'X-Has-More': 'true'}), 0, 0, 300)
        ring = [[0, 0], [.001, 0], [.001, .001], [0, 0]]
        multi = feature('way', 2, dict(type='MultiPolygon', coordinates=[[ring]]), {'shop': 'books'})
        with self.assertRaisesRegex(ContractError, 'way_topology'):
            preview_maplark(batch([point, multi]), 0, 0, 300)

    def test_uncertain_boundary_is_not_empty_success(self):
        point = feature('node', 1, dict(type='Point', coordinates=[.0027, 0]), {'shop': 'books'})
        with self.assertRaisesRegex(ContractError, 'boundary_uncertain'):
            preview_maplark(batch([point]), 0, 0, 300)

    def test_polygon_containment_is_not_around_boundary(self):
        ring = [[-.01, -.01], [.01, -.01], [.01, .01], [-.01, .01], [-.01, -.01]]
        polygon = feature('way', 1, dict(type='Polygon', coordinates=[ring]), {'amenity': 'school'})
        self.assertEqual(preview_maplark(batch([polygon]), 0, 0, 300)['response']['elements'], [])
