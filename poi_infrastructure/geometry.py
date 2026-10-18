"""Conservative around/center selector behind the opt-in Sprint 160 flags.

Inputs contain full node coordinates and way/member references, not out-center
responses. Ambiguous boundaries and unsupported geometry fail the whole query.
No caller may infer area completeness from this selector alone.
"""
import copy
import math
import re


class UncertifiedGeometry(ValueError):
    pass


EARTH_RADIUS = 20_000_000 / math.pi
BOUNDARY_MARGIN = 1.0  # metres; defer numerically ambiguous cases to exact Overpass


def _vector(point):
    lat, lon = map(math.radians, point)
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _norm(v):
    return math.sqrt(_dot(v, v))


def _angle(a, b):
    return math.atan2(_norm(_cross(a, b)), _dot(a, b))


def distance(a, b):
    return EARTH_RADIUS * _angle(_vector(a), _vector(b))


def segment_distance(point, start, end):
    p, a, b = map(_vector, (point, start, end))
    arc = _angle(a, b)
    best = min(_angle(p, a), _angle(p, b))
    if arc < 1e-12:
        return best * EARTH_RADIUS
    if arc > math.radians(5):
        raise UncertifiedGeometry('long_segment')
    normal = _cross(a, b)
    length = _norm(normal)
    normal = tuple(x/length for x in normal)
    projection = tuple(x-_dot(p, normal)*n for x, n in zip(p, normal))
    length = _norm(projection)
    if length > 1e-12:
        q = tuple(x/length for x in projection)
        if abs(_angle(a, q)+_angle(q, b)-arc) < 1e-10:
            best = min(best, _angle(p, q))
    return best * EARTH_RADIUS


def _point(element):
    values = (element.get('lat'), element.get('lon'))
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise UncertifiedGeometry('missing_coordinates')
    if abs(values[0]) > 80 or abs(values[1]) >= 179:
        raise UncertifiedGeometry('polar_or_dateline')
    return values


class GeometrySnapshot:
    def __init__(self, elements):
        self.elements = {}
        for element in copy.deepcopy(elements):
            identity = element.get('type'), element.get('id')
            if identity[0] not in ('node', 'way', 'relation') or type(identity[1]) is not int:
                raise UncertifiedGeometry('invalid_identity')
            if identity in self.elements:
                raise UncertifiedGeometry('duplicate_identity')
            tags = element.get('tags', {})
            if not isinstance(tags, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in tags.items()):
                raise UncertifiedGeometry('invalid_tags')
            self.elements[identity] = element

    def _member(self, kind, ref):
        try:
            return self.elements[kind, ref]
        except (KeyError, TypeError):
            raise UncertifiedGeometry('missing_member') from None

    def _lines(self, element):
        kind = element['type']
        if kind == 'node':
            return [[_point(element)]]
        if kind == 'way':
            nodes = element.get('nodes')
            if not isinstance(nodes, list) or not nodes:
                raise UncertifiedGeometry('missing_way_nodes')
            return [[_point(self._member('node', ref)) for ref in nodes]]
        members = element.get('members')
        if not isinstance(members, list):
            raise UncertifiedGeometry('missing_members')
        lines = []
        for member in members:
            if member.get('type') == 'relation':
                # Around tests direct node/way members, not recursive relations.
                # Center reconstruction for selected mixed nested relations is
                # not certified, so those selections are rejected below.
                continue
            if member.get('type') not in ('node', 'way'):
                raise UncertifiedGeometry('invalid_member')
            lines.extend(self._lines(self._member(member['type'], member.get('ref'))))
        return lines

    def select(self, lat, lon, radius, filters):
        point = _point(dict(lat=lat, lon=lon))
        if type(radius) not in (int, float) or not math.isfinite(radius) or not 0 < radius <= 1000:
            raise UncertifiedGeometry('unsupported_radius')
        selected = []
        for identity in sorted(self.elements, key=lambda k: (('node','way','relation').index(k[0]), k[1])):
            element = self.elements[identity]
            tags = element.get('tags', {})
            if not any((tags.get(t.split('=', 1)[0]) == t.split('=', 1)[1]) if '=' in t
                       else bool(tags.get(t)) for t in filters):
                continue
            lines = self._lines(element)
            distances = [distance(point, p) for line in lines for p in line]
            distances.extend(segment_distance(point, a, b) for line in lines for a, b in zip(line, line[1:]))
            nearest = min(distances, default=math.inf)
            if abs(nearest-radius) <= BOUNDARY_MARGIN:
                raise UncertifiedGeometry('boundary_uncertain')
            if nearest > radius:
                continue
            if element['type'] == 'relation' and any(m['type']=='relation' for m in element['members']):
                raise UncertifiedGeometry('nested_center')
            result = copy.deepcopy(element)
            result.pop('version', None)
            if element['type'] != 'node':
                points = [p for line in lines for p in line]
                result['center'] = dict(lat=round((min(p[0] for p in points)+max(p[0] for p in points))/2, 7),
                                        lon=round((min(p[1] for p in points)+max(p[1] for p in points))/2, 7))
            selected.append(result)
        return dict(elements=selected)


class CoveredGeometry:
    """A single immutable fill; never merge partial snapshots into coverage.

    Construction is an internal contract: the caller must have executed the
    corresponding full-closure query successfully. The query has independent
    synthetic Overpass evidence; unverified geometry still defers to exact.
    """
    PROFILE = 'around-body-closure-experimental-v1'

    def __init__(self, data, lat, lon, radius, filters):
        _point(dict(lat=lat, lon=lon))
        if type(radius) not in (int, float) or not math.isfinite(radius) or not 0 < radius <= 2000:
            raise UncertifiedGeometry('invalid_fill_radius')
        if not isinstance(data, dict) or data.get('remark') or not isinstance(data.get('elements'), list):
            raise UncertifiedGeometry('incomplete_fill')
        if not filters or any(not isinstance(t, str) or not t for t in filters):
            raise UncertifiedGeometry('invalid_filters')
        self.snapshot = GeometrySnapshot(data['elements'])
        self.lat, self.lon, self.radius = lat, lon, radius
        self.filters = tuple(filters)

    def select(self, lat, lon, radius, filters):
        if tuple(filters) != self.filters:
            raise UncertifiedGeometry('filter_profile_mismatch')
        _point(dict(lat=lat, lon=lon))
        if type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0:
            raise UncertifiedGeometry('unsupported_radius')
        if distance((lat,lon),(self.lat,self.lon)) + radius + BOUNDARY_MARGIN >= self.radius:
            raise UncertifiedGeometry('outside_coverage')
        return self.snapshot.select(lat, lon, radius, filters)


def fill_plan(lat, lon, radius, filters):
    """Fixed 0.002-degree cells share a bounded 1500 m fill, never player range."""
    _point(dict(lat=lat, lon=lon))
    if type(radius) not in (int,float) or not math.isfinite(radius) or not 0 < radius <= 1000:
        raise UncertifiedGeometry('unsupported_radius')
    if not filters or any(not isinstance(t,str) or not re.fullmatch(r'[a-zA-Z0-9_:]+(?:=[a-zA-Z0-9_:]+)?',t) for t in filters):
        raise UncertifiedGeometry('unsupported_filters')
    a, b = round(round(lat/.002)*.002,6), round(round(lon/.002)*.002,6)
    # Match the independently exercised wire format; scanner radius is unchanged.
    keys = [t for t in filters if '=' not in t]
    clauses = [f'  nwr(around:1500,{a:g},{b:g})[~"^({"|".join(keys)})$"~"."];'] if keys else []
    for tag in filters:
        if '=' in tag:
            k,v=tag.split('=',1)
            clauses.append(f'  nwr(around:1500,{a:g},{b:g})["{k}"="{v}"];')
    query = '[out:json][timeout:15];\n(\n'+'\n'.join(clauses)+'\n);\n(._; >>;);\nout body;\n'
    return dict(lat=a,lon=b,radius=1500,filters=list(filters)),query
