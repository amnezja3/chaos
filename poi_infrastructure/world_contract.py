"""Provider-neutral v1 contracts. No IO, coverage certification or activation.

Planar topology validation is NOT an around/coverage certificate. Dateline
crossings are retained as structural-only and cannot be certified locally.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re


SCHEMA_VERSION = 'chaos-world-v1'
GEOMETRY_VERSION = 'wgs84-geos-v1'
POI_PROFILE = 'poi-gameplay-v1'
FILTERS = ('shop', 'amenity', 'office', 'healthcare', 'atm=yes', 'man_made=surveillance')
LAYERS = frozenset(('poi', 'roads', 'waterways', 'inland_water', 'coastline', 'land_water'))
OSM_TYPES = ('node', 'way', 'relation')


class ContractError(ValueError):
    """Stable, non-sensitive error code; never include response text/secrets."""


def position(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ContractError('position_shape')
    if any(type(n) not in (int, float) or not math.isfinite(n) for n in value):
        raise ContractError('position_numeric')
    lon, lat = value
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ContractError('position_range')
    return (lon, lat)


@dataclass(frozen=True)
class Geometry:
    kind: str
    coordinates: tuple
    bounds: tuple
    vertices: int
    crosses_antimeridian: bool
    validation: str = 'structural_only'

    @classmethod
    def parse(cls, raw, max_vertices=20000):
        if not isinstance(raw, dict) or set(raw) - {'type', 'coordinates', 'bbox'}:
            raise ContractError('geometry_fields')
        if type(max_vertices) is not int or max_vertices < 1:
            raise ContractError('geometry_limit')
        kind = raw.get('type')
        if kind not in ('Point', 'LineString', 'Polygon', 'MultiPolygon'):
            raise ContractError('geometry_unsupported')
        points = []
        crossing = False

        def point(p):
            if len(points) >= max_vertices:
                raise ContractError('geometry_limit')
            result = position(p)
            points.append(result)
            return result

        def sequence(items, minimum):
            if not isinstance(items, (list, tuple)) or len(items) < minimum:
                raise ContractError('geometry_shape')
            if len(items) > max_vertices:
                raise ContractError('geometry_limit')
            return items

        def line(items, ring=False):
            nonlocal crossing
            result = tuple(point(p) for p in sequence(items, 4 if ring else 2))
            if len(set(result)) < (3 if ring else 2):
                raise ContractError('geometry_degenerate')
            if ring and result[0] != result[-1]:
                raise ContractError('geometry_open_ring')
            crossing |= any(abs(a[0] - b[0]) > 180 for a, b in zip(result, result[1:]))
            return result

        def polygon(items):
            return tuple(line(r, True) for r in sequence(items, 1))

        coords = raw.get('coordinates')
        if kind == 'Point':
            coords = point(coords)
        elif kind == 'LineString':
            coords = line(coords)
        elif kind == 'Polygon':
            coords = polygon(coords)
        else:
            coords = tuple(polygon(p) for p in sequence(coords, 1))
        bounds = (min(p[0] for p in points), min(p[1] for p in points),
                  max(p[0] for p in points), max(p[1] for p in points))
        # GEOS is planar; it must not interpret a dateline edge as a world-wide one.
        validation = 'structural_only'
        if not crossing:
            from shapely.geometry import shape
            from shapely.errors import GEOSException
            try:
                topology = shape({'type': kind, 'coordinates': coords})
                if topology.is_empty or not topology.is_valid:
                    raise ContractError('geometry_topology_invalid')
            except GEOSException as exc:
                raise ContractError('geometry_topology_invalid') from exc
            validation = 'planar_topology_valid'
        return cls(kind, coords, bounds, len(points), crossing, validation)

    def geojson(self):
        return json.loads(json.dumps({'type': self.kind, 'coordinates': self.coordinates}))


def layers_for(tags):
    layers = set()
    if any(k in tags for k in FILTERS[:4]) or tags.get('atm') == 'yes' or tags.get('man_made') == 'surveillance':
        layers.add('poi')
    if 'highway' in tags:
        layers.add('roads')
    if 'waterway' in tags:
        layers.add('waterways')
    if tags.get('natural') == 'water':
        layers.add('inland_water')
    if tags.get('natural') == 'coastline':
        layers.add('coastline')
    # land_water needs independent dataset/topology evidence, never inferred.
    return frozenset(layers)


@dataclass(frozen=True)
class Provenance:
    provider: str
    adapter_version: str
    snapshot: str
    fetched_at: float
    source_dataset_at: str | None = None
    license_ref: str | None = None

    def __post_init__(self):
        for value in (self.provider, self.adapter_version, self.snapshot):
            if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}', value):
                raise ContractError('provenance_identifier')
        if type(self.fetched_at) not in (int, float) or not math.isfinite(self.fetched_at) or self.fetched_at < 0:
            raise ContractError('provenance_time')


@dataclass(frozen=True)
class WorldObject:
    identity: str
    external_id: str
    osm_type: str | None
    osm_id: int | None
    tags: tuple
    layers: frozenset
    geometry: Geometry | None
    marker: tuple | None
    marker_method: str | None
    provenance: Provenance
    ordinal: int

    @classmethod
    def create(cls, *, external_id, tags, geometry, marker, marker_method, provenance,
               ordinal, osm_type=None, osm_id=None):
        if not isinstance(provenance, Provenance):
            raise ContractError('provenance_required')
        if not isinstance(external_id, str) or not external_id or len(external_id) > 2048:
            raise ContractError('identity_missing')
        if not isinstance(tags, dict) or len(tags) > 1024 or any(
                not isinstance(k, str) or not isinstance(v, str) or len(k) > 256 or len(v) > 8192
                for k, v in tags.items()):
            raise ContractError('tags_invalid')
        if type(ordinal) is not int or ordinal < 0:
            raise ContractError('ordinal_invalid')
        if osm_type is None and osm_id is None:
            digest = hashlib.sha256(external_id.encode()).hexdigest()
            identity = f'provider:{provenance.provider}:{digest}'
        elif osm_type in OSM_TYPES and type(osm_id) is int and osm_id > 0:
            identity = f'osm:{osm_type}:{osm_id}'
        else:
            raise ContractError('osm_identity_invalid')
        if geometry is not None and not isinstance(geometry, Geometry):
            raise ContractError('geometry_invalid')
        if marker_method not in (None, 'source_point', 'source_centroid', 'overpass_center', 'geometry_bounds_center'):
            raise ContractError('marker_method_invalid')
        if (marker is None) != (marker_method is None):
            raise ContractError('marker_method_missing')
        return cls(identity, external_id, osm_type, osm_id, tuple(sorted(tags.items())),
                   layers_for(tags), geometry, position(marker) if marker is not None else None,
                   marker_method, provenance, ordinal)

    def attribute(self, key, yes='yes', no='no'):
        value = dict(self.tags).get(key)
        return True if value == yes else False if value == no else None


@dataclass(frozen=True)
class ProviderBatch:
    objects: tuple
    profile: str
    completeness: str
    reasons: tuple
    selection: str
    order: str

    def __post_init__(self):
        if self.profile not in LAYERS | {POI_PROFILE}:
            raise ContractError('profile_unknown')
        if self.completeness not in ('complete', 'partial', 'unknown'):
            raise ContractError('completeness_invalid')
        if not isinstance(self.objects, tuple) or not all(isinstance(o, WorldObject) for o in self.objects):
            raise ContractError('objects_invalid')
        if len({o.identity for o in self.objects}) != len(self.objects):
            raise ContractError('duplicate_identity')

    def export_overpass(self):
        """Only the reference contract is exportable until provider parity is proven."""
        if (self.profile != POI_PROFILE or self.completeness != 'complete' or self.reasons
                or self.selection != 'overpass-around-v1' or self.order != 'overpass-source-order-v1'):
            raise ContractError('gameplay_contract_unproven')
        elements = []
        for obj in self.objects:
            if obj.osm_type not in OSM_TYPES or obj.marker is None:
                raise ContractError('gameplay_identity_or_marker_missing')
            if obj.marker_method not in ('source_point', 'overpass_center'):
                raise ContractError('gameplay_marker_unproven')
            row = dict(type=obj.osm_type, id=obj.osm_id, tags=dict(obj.tags))
            lon, lat = obj.marker
            if obj.osm_type == 'node':
                row.update(lat=lat, lon=lon)
            else:
                row['center'] = dict(lat=lat, lon=lon)
            elements.append(row)
        return {'elements': elements}


def batch_key(provider, adapter_version, profile, selection, query):
    """Separate provider/profile/semantics; never reuse legacy QL cache keys."""
    raw = json.dumps([SCHEMA_VERSION, provider, adapter_version, profile, selection, query],
                     sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class CoverageEvidence:
    """Evidence envelope, not a spatial index or a grant of provider rights."""
    layer: str
    bounds: tuple
    profile_version: str
    snapshot: str
    completeness: str
    selection: str
    geometry_proof: str
    observed_at: float
    fresh_until: float
    usable_until: float
    object_count: int | None

    def __post_init__(self):
        if self.layer not in LAYERS or self.completeness not in ('unknown', 'partial', 'complete'):
            raise ContractError('coverage_profile_invalid')
        if not isinstance(self.bounds, tuple) or len(self.bounds) != 4:
            raise ContractError('coverage_bounds_invalid')
        west, south = position(self.bounds[:2])
        east, north = position(self.bounds[2:])
        if west >= east or south >= north:
            raise ContractError('coverage_bounds_unsupported')
        times = (self.observed_at, self.fresh_until, self.usable_until)
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in times) or not 0 <= times[0] <= times[1] <= times[2]:
            raise ContractError('coverage_time_invalid')
        if self.object_count is not None and (type(self.object_count) is not int or self.object_count < 0):
            raise ContractError('coverage_count_invalid')
        for token in (self.profile_version, self.snapshot, self.selection, self.geometry_proof):
            if not isinstance(token, str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}', token):
                raise ContractError('coverage_evidence_missing')
        if self.completeness == 'complete' and (self.object_count is None or self.geometry_proof in ('unknown', 'structural_only')):
            raise ContractError('coverage_complete_unproven')

    def state(self, now):
        if type(now) not in (int, float) or not math.isfinite(now) or now < self.observed_at:
            raise ContractError('coverage_clock_invalid')
        if self.completeness != 'complete':
            return self.completeness.upper()
        if now < self.fresh_until:
            return 'COMPLETE_FRESH'
        if now < self.usable_until:
            return 'COMPLETE_STALE'
        return 'EXPIRED'
