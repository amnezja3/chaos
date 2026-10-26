"""Reuse the independently exercised Overpass closure selector in live routing.

One provider/revision/snapshot only. Never certify center-only or GeoJSON data.
No migrations, grants, implicit activation, or provider calls in this module.
"""
import json
import os
import time

from .geometry import CoveredGeometry, fill_plan
from .providers import Registry
from .service import key_for
from .world import WorldRepository
from .world_contract import FILTERS
from .world_shadow import reference

PROFILE = 'routed-overpass-closure-v1'


def metadata(candidate):
    return dict(provider=candidate['id'], revision=candidate['revision'],
                storage_reference=reference(candidate))


def allowed(candidate):
    return (os.environ.get('CHAOS_POI_WORLD_REGIONAL_READ_ENABLED') == '1'
            and reference(candidate) is not None
            and all(Registry.approved(candidate, s) for s in ('normal_scan', 'storage')))


def plan(candidate, spatial):
    if (not spatial or tuple(spatial.get('filters', ())) != FILTERS or not allowed(candidate)
            or os.environ.get('CHAOS_POI_WIDE_FETCH_ENABLED') != '1'
            or os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED') != '1'
            or os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED') != '1'
            or not Registry.approved(candidate, 'wide_fetch')):
        return None
    bounds, query = fill_plan(**spatial)
    key = 'routed-fill:' + key_for(json.dumps([PROFILE, metadata(candidate), bounds], sort_keys=True))
    return key, bounds, query


def read(service, candidate, spatial, active, stale=False):
    if (not spatial or tuple(spatial.get('filters', ())) != FILTERS or not allowed(candidate)
            or os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED') != '1'):
        return None
    return WorldRepository(service.repo).read_geometry(**spatial, allow_stale=stale,
        config=service.config, provider=candidate['id'], profile=PROFILE,
        metadata=metadata(candidate), still_active=active)


def store(service, candidate, key, owner, bounds, data, fresh_ttl, stale_ttl):
    if not allowed(candidate) or os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED') != '1':
        return False
    covered = CoveredGeometry(data, **bounds)
    for element in covered.snapshot.elements.values():
        covered.snapshot._lines(element)
    expected = metadata(candidate)

    def guard(connection):
        row = connection.execute('SELECT config FROM poi_provider_config WHERE id=?',
                                 (candidate['id'],)).fetchone()
        current = json.loads(row[0]) if row else None
        return bool(current and current.get('enabled') and metadata(current) == expected
                    and allowed(current) and Registry.approved(current, 'wide_fetch'))

    now = time.time()
    retain = min(now+7*86400, candidate['review_due_at'])
    return WorldRepository(service.repo)._publish(key, owner, data, candidate['id'],
        min(fresh_ttl, 300), min(stale_ttl, 1800), service.config, now,
        PROFILE, dict(bounds, _source=expected), publication_guard=guard,
        retain_until=retain if retain >= now+min(stale_ttl,1800) else None)
