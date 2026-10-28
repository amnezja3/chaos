"""Opt-in CHAOS regional selection, not a claim of native API radius parity.

One complete bbox response, full geometry, deterministic local distance.
No unions, HTTP, cache writes, budget changes or renewal of source timestamps.
"""
from dataclasses import replace
import hashlib
import json
import math
import os
import time

from shapely.geometry import Point, shape
from shapely.ops import transform

from .world_adapters import MAPLARK_VERSION, plan_maplark_region
from .world_contract import ContractError, POI_PROFILE, ProviderBatch, SCHEMA_VERSION
from .world_region_candidate import prepare
from .world_storage import FORMAT, decode_object
from .world_shadow import reference
from .providers import Registry
from .maplark_profile import export_maplark

PROFILE = 'chaos-maplark-region-geometry-v2'
FLAG = 'CHAOS_POI_MAPLARK_REGIONAL_PROFILE'


def select(batch, bounds, lat, lon, radius):
    """CHAOS v2: full-geometry distance <= radius in the local planar metric.

    Coordinates project to metres with x=(lon-origin_lon)*111195*cos(lat)
    and y=(lat-origin_lat)*111195. Holes and all polygon parts are retained.
    This defines CHAOS selection, not the provider's undocumented radius rule.
    """
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (lat, lon, radius))
            or abs(lat) > 60 or not -180 < lon < 180 or not 1 <= radius <= 500):
        raise ContractError('regional_query_unsupported')
    plan = plan_maplark_region(bounds, profile='poi', limit=1000)
    candidate = prepare(batch, plan)
    scale = 111195 * math.cos(math.radians(lat))
    def project(x, y, z=None):
        return ((x-lon)*scale, (y-lat)*111195)
    w, s, e, n = bounds
    # Preserve the coverage guard. It does not exclude objects near the circle.
    margin = max(5.0, radius * .01)
    if min((lon-w)*scale, (e-lon)*scale, (lat-s)*111195, (n-lat)*111195) <= radius+margin:
        raise ContractError('regional_circle_not_contained')
    selected = []
    origin = Point(0, 0)
    for obj in candidate.batch.objects:
        geo = obj.geometry
        if geo.kind not in ('Point', 'LineString', 'Polygon', 'MultiPolygon'):
            raise ContractError('regional_geometry_unsupported')
        # Keep projection local even when the source retains a whole long way.
        gw, gs, ge, gn = geo.bounds
        if max(abs(gw-lon), abs(ge-lon), abs(gs-lat), abs(gn-lat)) > .1:
            raise ContractError('regional_geometry_extent')
        distance = transform(project, shape(geo.geojson())).distance(origin)
        if distance <= radius:
            selected.append(obj)
    # Selection is separate from the existing marker/ID/tag export contract.
    return export_maplark(replace(batch, objects=tuple(selected), profile=POI_PROFILE,
                                 selection='maplark-radius-unverified'))


def read(service, candidate, spatial, active, allow_stale=False, *, diagnostic=None):
    trace = diagnostic if diagnostic is not None else {}
    trace.update(reason='no_compatible_snapshot', examined=0, rejected={})
    def reject(reason):
        trace['rejected'][reason] = trace['rejected'].get(reason, 0)+1
    if (os.environ.get(FLAG) != PROFILE
            or os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED') != '1'
            or reference(candidate) is None or not active()):
        trace['reason'] = 'profile_access_or_approval_disabled'
        return None
    deadline = time.monotonic()+2
    total = 0
    conn = service.repo.connect()
    try:
        rows = conn.execute('''SELECT id,length(payload) AS size FROM world_snapshot
            WHERE provider=? AND profile=? AND usable_until>?
            ORDER BY fetched DESC LIMIT 64''', (candidate['id'], FORMAT, time.time())).fetchall()
        for item in rows:
            if time.monotonic() >= deadline or not active():
                trace['reason'] = 'deadline_or_inactive'
                return None
            total += item['size']
            if total > 8*1024*1024:
                trace['reason'] = 'byte_limit'
                return None
            trace['examined'] += 1
            row = conn.execute('SELECT * FROM world_snapshot WHERE id=?', (item['id'],)).fetchone()
            if row is None:
                continue
            expiry = min(row['usable_until' if allow_stale else 'fresh_until'],
                         row['fetched']+(1800 if allow_stale else 300))
            if not row['fetched'] <= time.time() < expiry:
                reject('not_fresh' if not allow_stale else 'expired')
                continue
            try:
                if hashlib.sha256(row['payload']).hexdigest() != row['digest']:
                    reject('digest_mismatch')
                    continue
                raw = json.loads(row['payload'])
                if (raw.get('format') != FORMAT or raw.get('schema') != SCHEMA_VERSION
                        or raw.get('revision') != candidate['revision']
                        or raw.get('storage_reference') != reference(candidate)
                        or raw.get('profile') != 'poi' or raw.get('completeness') != 'complete'
                        or raw.get('reasons') or raw.get('fresh_until') != row['fresh_until']
                        or raw.get('usable_until') != row['usable_until']):
                    reject('metadata_mismatch')
                    continue
                context = raw.get('observation_context', {})
                if context.get('acquisition') != 'sector-bbox-v1':
                    reject('not_regional_bbox')
                    continue
                bounds = context['demand_bounds']
                if context['request_params'] != dict(plan_maplark_region(bounds, profile='poi', limit=1000).params):
                    reject('request_profile_mismatch')
                    continue
                if len(raw['objects']) > 1000:
                    reject('object_limit')
                    continue
                objects = tuple(decode_object(o) for o in raw['objects'])
                if any(o.provenance.adapter_version != MAPLARK_VERSION for o in objects):
                    reject('adapter_mismatch')
                    continue
                batch = ProviderBatch(objects, 'poi', 'complete', (), raw['selection'], raw['order'])
                data = select(batch, bounds, spatial['lat'], spatial['lon'], spatial['radius'])
                current = next((p for p in Registry(service.repo).list() if p['id']==candidate['id']), None)
                if (current is None or current['revision'] != candidate['revision']
                        or reference(current) != reference(candidate) or not active()
                        or time.monotonic() >= deadline or time.time() >= expiry):
                    trace['reason'] = 'post_selection_fence_or_deadline'
                    return None
                if not conn.execute('SELECT 1 FROM world_snapshot WHERE id=?', (row['id'],)).fetchone():
                    continue
                trace['reason'] = 'selected'
                return data
            except ContractError as exc:
                reject(str(exc))
                continue
            except (ValueError, TypeError, KeyError):
                reject('invalid_snapshot')
                continue
    finally:
        conn.close()
    return None
