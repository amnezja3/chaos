"""Offline decoders and request plans. No HTTP, secret values or registry activation.

MapLark v3 and Geoapify Places are candidates, NOT certified POIFetcher replacements.
Headers are part of the input contract: a JSON file alone cannot prove completeness.
"""
from dataclasses import dataclass
import os
import re
from urllib.parse import urlencode

from .world_contract import (ContractError, FILTERS, Geometry, POI_PROFILE,
                             ProviderBatch, WorldObject, position)

MAPLARK_VERSION = 'maplark-v3-offline-v1'
GEOAPIFY_VERSION = 'geoapify-places-v2-offline-v1'


@dataclass(frozen=True)
class RequestPlan:
    endpoint: str
    params: tuple
    auth_header: str
    secret_ref: str
    profile: str
    adapter_version: str

    @property
    def path(self):
        # Contains geography, never an API key. Do not include in operational logs.
        return self.endpoint.split('.com', 1)[1] + '?' + urlencode(self.params)

    def authenticated_wire(self):
        """Reconstruct the allowlisted plan before resolving a server-only secret."""
        try:
            params = dict(self.params)
            if len(params) != len(self.params):
                raise ValueError()
            if self.endpoint == 'https://api.maplark.com/v3/osm_features':
                if 'bbox' in params:
                    expected = plan_maplark_region(tuple(map(float,params['bbox'].split(','))),
                                                   profile=self.profile,limit=int(params['limit']))
                else:
                    lat, lon = map(float, params['location'].split(','))
                    expected = plan_maplark(lat, lon, float(params['radius']),
                                            profile=self.profile, limit=int(params['limit']))
            elif self.endpoint == 'https://api.geoapify.com/v2/places':
                shape, values = params['filter'].split(':', 1)
                lon, lat, radius = values.split(',')
                if shape != 'circle':
                    raise ValueError()
                expected = plan_geoapify(float(lat), float(lon), float(radius),
                    categories=tuple(params['categories'].split(',')), limit=int(params['limit']), offset=int(params['offset']))
            else:
                raise ValueError()
            # Numeric formatting may differ after parsing; compare parsed values
            # by constructing requests with stable formatting in the builders.
            if self != expected:
                raise ValueError()
        except (ValueError, TypeError, KeyError, IndexError):
            raise ContractError('request_plan_not_allowlisted') from None
        secret = os.environ.get(self.secret_ref, '')
        if not secret or len(secret) > 4096 or any(not 33 <= ord(c) <= 126 for c in secret):
            raise ContractError('provider_secret_missing_or_invalid')
        value = 'Bearer ' + secret if self.auth_header == 'Authorization' else secret
        return self.path, {self.auth_header: value}


def plan_maplark(lat, lon, radius, *, profile=POI_PROFILE, limit=20000):
    position((lon, lat))
    if type(radius) not in (int, float) or not 0 < radius <= 10000:
        raise ContractError('radius_invalid')
    if type(limit) is not int or not 1 <= limit <= 20000:
        raise ContractError('feature_limit')
    filters = {POI_PROFILE: '|'.join(FILTERS), 'roads': 'highway', 'waterways': 'waterway',
               'inland_water': 'natural=water', 'coastline': 'natural=coastline'}
    if profile not in filters:
        raise ContractError('profile_unsupported')
    # No zoom/simplification, clipping or cursor. Local caps are not provider quotas.
    return RequestPlan('https://api.maplark.com/v3/osm_features',
                       (('location', f'{float(lat)},{float(lon)}'), ('radius', str(float(radius))),
                        ('tags', filters[profile]), ('limit', str(limit)), ('clipGeometry', 'false')),
                       'Authorization', 'CHAOS_MAPLARK_API_KEY', profile, MAPLARK_VERSION)


def plan_maplark_region(bounds, *, profile='roads',limit=1000):
    """Small experimental bbox contract; not a certified area or live scanner."""
    from .world_read import checked_bounds
    west,south,east,north=checked_bounds(bounds)
    if east-west>.020001 or north-south>.020001:
        raise ContractError('region_probe_bounds_limit')
    filters={'poi':'|'.join(FILTERS),'roads':'highway','waterways':'waterway','inland_water':'natural=water','coastline':'natural=coastline'}
    if profile not in filters: raise ContractError('region_profile_unsupported')
    if type(limit) is not int or not 1<=limit<=1000:raise ContractError('feature_limit')
    return RequestPlan('https://api.maplark.com/v3/osm_features',
        (('bbox',','.join(str(float(v)) for v in (west,south,east,north))),
         ('tags',filters[profile]),('limit',str(limit)),('clipGeometry','false')),
        'Authorization','CHAOS_MAPLARK_API_KEY',profile,MAPLARK_VERSION)


def plan_geoapify(lat, lon, radius, *, categories, limit=100, offset=0):
    position((lon, lat))
    if type(radius) not in (int, float) or not 0 < radius <= 10000:
        raise ContractError('radius_invalid')
    if (not isinstance(categories, tuple) or not 1 <= len(categories) <= 100 or
            any(not isinstance(c, str) or not re.fullmatch(r'[a-z][a-z0-9_.]{0,100}', c) for c in categories)):
        raise ContractError('categories_invalid')
    if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or not 0 <= offset <= 20000:
        raise ContractError('pagination_invalid')
    return RequestPlan('https://api.geoapify.com/v2/places',
                       (('categories', ','.join(categories)), ('filter', f'circle:{float(lon)},{float(lat)},{float(radius)}'),
                        ('limit', str(limit)), ('offset', str(offset))),
                       'x-api-key', 'CHAOS_GEOAPIFY_API_KEY', 'poi', GEOAPIFY_VERSION)


def _features(raw, maximum):
    if (not isinstance(raw, dict) or raw.get('type') != 'FeatureCollection'
            or not isinstance(raw.get('features'), list)):
        raise ContractError('feature_collection_invalid')
    features = raw['features']
    if type(maximum) is not int or not 1 <= maximum <= 20000 or len(features) > maximum:
        raise ContractError('feature_limit')
    for f in features:
        if not isinstance(f, dict) or f.get('type') != 'Feature' or not isinstance(f.get('properties'), dict):
            raise ContractError('feature_invalid')
    return features


def normalize_maplark(raw, headers, provenance, *, profile=POI_PROFILE, maximum=20000):
    if provenance.provider != 'maplark' or provenance.adapter_version != MAPLARK_VERSION:
        raise ContractError('adapter_provenance_mismatch')
    features = _features(raw, maximum)
    if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                            for k, v in headers.items()):
        raise ContractError('headers_invalid')
    headers = {k.lower(): v.strip() for k, v in headers.items()}
    reasons = []
    if headers.get('x-has-more') == 'true':
        reasons.append('truncated')
    elif headers.get('x-has-more') != 'false':
        reasons.append('completeness_header_missing_or_invalid')
    try:
        count = int(headers['x-returned'])
    except (KeyError, ValueError):
        count = None
    if count != len(features):
        reasons.append('returned_count_unverified')
    if headers.get('x-next-cursor'):
        reasons.append('unexpected_v3_cursor')
    if raw.get('remark') or raw.get('error') or raw.get('truncated'):
        reasons.append('response_partial')
    objects = []
    remaining_vertices = 100000
    for ordinal, f in enumerate(features):
        match = re.fullmatch(r'(node|way|relation)/([1-9][0-9]*)', str(f.get('id', '')))
        if not match:
            raise ContractError('maplark_osm_identity_invalid')
        geometry = Geometry.parse(f.get('geometry'), max_vertices=min(20000, remaining_vertices))
        remaining_vertices -= geometry.vertices
        kind, osm_id = match.group(1), int(match.group(2))
        if kind == 'node' and geometry.kind != 'Point':
            raise ContractError('node_geometry_invalid')
        marker = geometry.coordinates if geometry.kind == 'Point' else None
        method = 'source_point' if marker is not None else None
        # Do not export provider centroid as historical Overpass bbox center.
        objects.append(WorldObject.create(external_id=f['id'], osm_type=kind, osm_id=osm_id,
            tags=f['properties'].get('tags'), geometry=geometry, marker=marker,
            marker_method=method, provenance=provenance, ordinal=ordinal))
    # Complete means the provider response, not parity with Overpass or reusable area.
    return ProviderBatch(tuple(objects), profile, 'partial' if reasons else 'complete',
                         tuple(reasons), 'maplark-radius-unverified', 'provider-order-unverified')


def normalize_geoapify(raw, provenance, *, page_limit=100):
    if provenance.provider != 'geoapify' or provenance.adapter_version != GEOAPIFY_VERSION:
        raise ContractError('adapter_provenance_mismatch')
    features = _features(raw, page_limit)
    objects = []
    remaining_vertices = 100000
    for ordinal, f in enumerate(features):
        props = f['properties']
        external_id = props.get('place_id')
        if not isinstance(external_id, str) or not external_id:
            raise ContractError('geoapify_place_id_missing')
        geometry = Geometry.parse(f.get('geometry'), max_vertices=min(20000, remaining_vertices))
        remaining_vertices -= geometry.vertices
        raw_osm = props.get('datasource', {}).get('raw', {}) if isinstance(props.get('datasource'), dict) else {}
        if not isinstance(raw_osm, dict):
            raise ContractError('geoapify_raw_invalid')
        # Preserve only original string tags; never invent OSM tags from categories.
        tags = {k: v for k, v in raw_osm.items() if isinstance(v, str) and k not in ('osm_id', 'osm_type')}
        osm_type, osm_id = raw_osm.get('osm_type'), raw_osm.get('osm_id')
        # Geoapify uses n/w/r in datasource.raw; keep canonical world types.
        if isinstance(osm_type, str):
            osm_type = {'n': 'node', 'w': 'way', 'r': 'relation'}.get(osm_type, osm_type)
        if osm_type is None and osm_id is None:
            pass
        elif osm_type not in ('node', 'way', 'relation') or type(osm_id) is not int or osm_id <= 0:
            raise ContractError('geoapify_osm_identity_unverified')
        marker = geometry.coordinates if geometry.kind == 'Point' else None
        objects.append(WorldObject.create(external_id=external_id, osm_type=osm_type, osm_id=osm_id,
            tags=tags, geometry=geometry, marker=marker, marker_method='source_point' if marker else None,
            provenance=provenance, ordinal=ordinal))
    reasons = ['category_mapping_unverified', 'spatial_selection_unverified']
    if len(features) == page_limit:
        reasons.append('more_pages_possible')
    # A short page is not proof that all CHAOS categories were queried or indexed.
    return ProviderBatch(tuple(objects), 'poi', 'unknown', tuple(reasons),
                         'geoapify-places-unverified', 'provider-order-unverified')


def normalize_overpass(raw, provenance):
    from .service import Config, validate
    validate(raw, Config())
    objects = []
    for ordinal, e in enumerate(raw['elements']):
        kind = e['type']
        p = e if kind == 'node' else e.get('center')
        marker = (p['lon'], p['lat']) if p is not None else None
        geometry = Geometry.parse({'type': 'Point', 'coordinates': marker}) if kind == 'node' and marker else None
        objects.append(WorldObject.create(external_id=f"{kind}/{e['id']}", osm_type=kind,
            osm_id=e['id'], tags=e.get('tags', {}), geometry=geometry, marker=marker,
            marker_method=('source_point' if kind == 'node' else 'overpass_center') if marker else None,
            provenance=provenance, ordinal=ordinal))
    return ProviderBatch(tuple(objects), POI_PROFILE, 'complete', (),
                         'overpass-around-v1', 'overpass-source-order-v1')
