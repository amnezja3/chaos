import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import overpy
from poiFetchClass import POIFetcher
from poi_infrastructure.world_contract import (
    ContractError, CoverageEvidence, FILTERS, Geometry, Provenance, batch_key, layers_for)
from poi_infrastructure.world_adapters import (
    GEOAPIFY_VERSION, MAPLARK_VERSION, normalize_geoapify, normalize_maplark,
    normalize_overpass, plan_geoapify, plan_maplark)


def provenance(provider='maplark'):
    return Provenance(provider, MAPLARK_VERSION if provider == 'maplark' else GEOAPIFY_VERSION,
                      'synthetic-fixture', 1)


def feature(identity='node/1', tags=None, geometry=None):
    return {'type': 'Feature', 'id': identity, 'properties': {'tags': tags or {'shop': 'books'}},
            'geometry': geometry or {'type': 'Point', 'coordinates': [21, 52]}}


def collection(*features):
    return {'type': 'FeatureCollection', 'features': list(features)}


class WorldContractTests(unittest.TestCase):
    def test_empty_coverage_has_independent_profile_and_expiry(self):
        proof = CoverageEvidence('poi', (0, 0, 1, 1), 'poi-v1', 'fixture', 'complete',
                                 'exact-query', 'fixture-reference', 1, 10, 20, 0)
        self.assertEqual(proof.state(2), 'COMPLETE_FRESH')
        self.assertEqual(proof.state(10), 'COMPLETE_STALE')
        self.assertEqual(proof.state(20), 'EXPIRED')
        self.assertNotEqual(proof.layer, 'roads')
        with self.assertRaisesRegex(ContractError, 'coverage_complete_unproven'):
            CoverageEvidence('land_water', (0, 0, 1, 1), 'v1', 'fixture', 'complete',
                             'bbox', 'structural_only', 1, 10, 20, 0)

    def test_four_geometries_roundtrip_with_hole_and_island(self):
        ring = [[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]
        hole = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
        island = [[7, 0], [8, 0], [8, 1], [7, 0]]
        for kind, coords in [('Point', [21, 52]), ('LineString', [[0, 0], [1, 1]]),
                             ('Polygon', [ring, hole]), ('MultiPolygon', [[ring, hole], [island]])]:
            with self.subTest(kind=kind):
                raw = dict(type=kind, coordinates=coords)
                geometry = Geometry.parse(raw)
                self.assertEqual(geometry.geojson(), raw)
                self.assertEqual(geometry.validation, 'planar_topology_valid')
                self.assertEqual(Geometry.parse(json.loads(json.dumps(geometry.geojson()))), geometry)

    def test_invalid_coordinates_open_rings_and_resource_limits(self):
        invalid = [dict(type='Point', coordinates=[True, 1]),
                   dict(type='Point', coordinates=[float('nan'), 1]),
                   dict(type='Point', coordinates=[0, 91]),
                   dict(type='Point', coordinates=[1, 2, 3]),
                   dict(type='Polygon', coordinates=[[[0, 0], [1, 0], [0, 1], [1, 1]]]),
                   dict(type='LineString', coordinates=[[1, 1], [1, 1]]),
                   dict(type='MultiLineString', coordinates=[[[0, 0], [1, 1]]])]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                Geometry.parse(raw)
        with self.assertRaisesRegex(ContractError, 'geometry_limit'):
            Geometry.parse(dict(type='LineString', coordinates=[[0, 0], [1, 1]]), max_vertices=1)

    def test_antimeridian_is_explicit_not_certified(self):
        geo = Geometry.parse(dict(type='LineString', coordinates=[[179, 0], [-179, 0]]))
        self.assertTrue(geo.crosses_antimeridian)
        self.assertEqual(geo.validation, 'structural_only')

    def test_self_intersection_and_hole_outside_are_rejected(self):
        shell = [[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]
        outside = [[6, 6], [7, 6], [7, 7], [6, 6]]
        bowtie = [[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]
        for rings in ([shell, outside], [bowtie]):
            with self.assertRaisesRegex(ContractError, 'geometry_topology_invalid'):
                Geometry.parse(dict(type='Polygon', coordinates=rings))

    def test_coastline_never_implies_land_water(self):
        self.assertEqual(layers_for({'natural': 'coastline'}), {'coastline'})
        self.assertEqual(layers_for({'natural': 'water', 'waterway': 'river'}), {'inland_water', 'waterways'})
        self.assertEqual(layers_for({'highway': 'residential', 'shop': 'books'}), {'roads', 'poi'})

    def test_profile_provider_and_version_isolate_cache(self):
        key = batch_key('maplark', 'v3', 'poi', 'radius', {'lat': 52})
        for args in [('other', 'v3', 'poi', 'radius'), ('maplark', 'v2', 'poi', 'radius'),
                     ('maplark', 'v3', 'roads', 'radius'), ('maplark', 'v3', 'poi', 'bbox')]:
            self.assertNotEqual(key, batch_key(*args, {'lat': 52}))

    def test_maplark_original_tags_unknown_and_immutability(self):
        raw = collection(feature(tags={'amenity': 'bank', 'internet_access': 'wlan', 'addr:city': 'Warszawa'}))
        batch = normalize_maplark(raw, {'X-Returned': '1', 'X-Has-More': 'false'}, provenance())
        obj = batch.objects[0]
        self.assertIsNone(obj.attribute('atm'))
        self.assertEqual(obj.identity, 'osm:node:1')
        self.assertEqual(dict(obj.tags)['internet_access'], 'wlan')
        raw['features'][0]['properties']['tags']['atm'] = 'yes'
        raw['features'][0]['geometry']['coordinates'][0] = 0
        self.assertIsNone(obj.attribute('atm'))
        self.assertEqual(obj.marker, (21, 52))
        self.assertEqual(batch.completeness, 'complete')
        with self.assertRaisesRegex(ContractError, 'gameplay_contract_unproven'):
            batch.export_overpass()

    def test_maplark_header_and_pagination_fail_closed_even_empty(self):
        for headers in [{}, {'X-Returned': '0', 'X-Has-More': 'true'},
                        {'X-Returned': '1', 'X-Has-More': 'false'},
                        {'X-Returned': '0', 'X-Has-More': 'false', 'X-Next-Cursor': 'old-v2'}]:
            with self.subTest(headers=headers):
                self.assertEqual(normalize_maplark(collection(), headers, provenance()).completeness, 'partial')
        empty = normalize_maplark(collection(), {'X-Returned': '0', 'X-Has-More': 'false'}, provenance())
        self.assertEqual(empty.completeness, 'complete')
        with self.assertRaises(ContractError):
            empty.export_overpass()

    def test_maplark_does_not_use_polygon_centroid_as_overpass_center(self):
        f = feature('way/2', geometry=dict(type='Polygon', coordinates=[[[0, 0], [3, 0], [1, 2], [0, 0]]]))
        f['properties']['centroid'] = dict(type='Point', coordinates=[1.3, .7])
        batch = normalize_maplark(collection(f), {'X-Returned': '1', 'X-Has-More': 'false'}, provenance())
        self.assertIsNone(batch.objects[0].marker)
        self.assertEqual(batch.objects[0].geometry.kind, 'Polygon')

    def test_duplicate_identity_and_missing_tags_are_not_silently_dropped(self):
        with self.assertRaisesRegex(ContractError, 'duplicate_identity'):
            normalize_maplark(collection(feature(), feature()), {'X-Returned': '2', 'X-Has-More': 'false'}, provenance())
        f = feature(); f['properties'] = {}
        with self.assertRaisesRegex(ContractError, 'tags_invalid'):
            normalize_maplark(collection(f), {}, provenance())

    def test_geoapify_category_never_invents_osm_tag_or_id(self):
        f = feature()
        f['properties'] = {'place_id': 'some-place', 'categories': ['service.financial.atm']}
        batch = normalize_geoapify(collection(f), provenance('geoapify'))
        self.assertEqual(batch.completeness, 'unknown')
        self.assertEqual(batch.objects[0].tags, ())
        self.assertIsNone(batch.objects[0].osm_id)
        self.assertTrue(batch.objects[0].identity.startswith('provider:geoapify:'))
        with self.assertRaises(ContractError):
            batch.export_overpass()

    def test_geoapify_short_osm_types_are_canonicalized(self):
        for source, canonical in [('n', 'node'), ('w', 'way'), ('r', 'relation'), ('node', 'node')]:
            with self.subTest(source=source):
                f = feature()
                f['properties'] = {'place_id': 'x', 'datasource': {'raw': {
                    'osm_type': source, 'osm_id': 123, 'amenity': 'bank'}}}
                batch = normalize_geoapify(collection(f), provenance('geoapify'))
                self.assertEqual(batch.objects[0].osm_type, canonical)
                self.assertEqual(batch.objects[0].osm_id, 123)
                self.assertEqual(batch.completeness, 'unknown')

    def test_geoapify_invalid_identity_still_rejected(self):
        for kind, identity in [('x', 1), ('n', True), ('n', '123'), ('w', -1), ('r', None), (None, 1)]:
            with self.subTest(kind=kind, identity=identity):
                f = feature()
                f['properties'] = {'place_id': 'x', 'datasource': {'raw': {
                    'osm_type': kind, 'osm_id': identity}}}
                with self.assertRaisesRegex(ContractError, 'geoapify_osm_identity_unverified'):
                    normalize_geoapify(collection(f), provenance('geoapify'))

    def test_geoapify_full_page_requires_more_work(self):
        f = feature(); f['properties'] = {'place_id': 'x'}
        batch = normalize_geoapify(collection(f), provenance('geoapify'), page_limit=1)
        self.assertIn('more_pages_possible', batch.reasons)

    def test_request_plans_have_no_credentials_and_no_implicit_geography(self):
        plan = plan_maplark(52, 21, 300)
        self.assertEqual(dict(plan.params)['tags'], '|'.join(FILTERS))
        self.assertEqual(dict(plan.params)['clipGeometry'], 'false')
        self.assertNotIn('cursor', dict(plan.params))
        self.assertNotIn('zoom', dict(plan.params))
        self.assertNotIn('apiKey', plan.path)
        with self.assertRaises(ContractError):
            plan_maplark(52, 21, 300, profile='land_water')
        g = plan_geoapify(52, 21, 300, categories=('commercial',))
        self.assertEqual(g.auth_header, 'x-api-key')
        with self.assertRaises(ContractError):
            plan_geoapify(52, 21, 300, categories=('commercial&apiKey=oops',))

    def test_reference_export_preserves_real_fasade_results(self):
        # Same saved independent Overpass fixture, no provider calls.
        path = Path(__file__).parent / 'fixtures/poi/geometry_reference.json'
        for name, case in json.loads(path.read_text(encoding='utf-8'))['cases'].items():
            raw = case['response']
            batch = normalize_overpass(raw, Provenance('overpass', 'reference-v1', 'fixture', 1))
            fetcher = POIFetcher(tag_filters=list(FILTERS))
            with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(raw)):
                expected = fetcher._get_all(0, 0)
            with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(batch.export_overpass())):
                self.assertEqual(fetcher._get_all(0, 0), expected, name)

    def test_reference_bank_atm_and_duplicate_coordinate_semantics(self):
        raw = {'elements': [
            dict(type='node', id=1, lat=52, lon=21, tags={'amenity': 'bank', 'atm': 'yes'}),
            dict(type='node', id=2, lat=52, lon=21, tags={'amenity': 'atm'}),
            dict(type='way', id=3, center={'lat': 52.1, 'lon': 21.1}, tags={'man_made': 'surveillance'})]}
        batch = normalize_overpass(copy.deepcopy(raw), Provenance('overpass', 'v1', 'fixture', 1))
        self.assertTrue(batch.objects[0].attribute('atm'))
        self.assertEqual(batch.export_overpass(), raw)
        fetcher = POIFetcher(tag_filters=list(FILTERS))
        with patch.object(fetcher, '_fetch', return_value=overpy.Result.from_json(batch.export_overpass())):
            self.assertEqual([r['osm_id'] for r in fetcher._get_all(0, 0)], [1, 3])


if __name__ == '__main__':
    unittest.main()
