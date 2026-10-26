"""Optional world integration; failures never erase a successful provider scan.

No schema creation, HTTP, new billing, extra radius, or implicit storage grant.
General mode retains observations for up to seven days without extending scan TTL.
"""
import json
import os
import time

from .providers import Registry
from .service import LOG, validate
from .world_adapters import MAPLARK_VERSION
from .world_contract import POI_PROFILE
from .maplark_profile import export_maplark
from .world_storage import CanonicalWorldRepository
from .world_read import SelectionProof, WorldReadPlanner

OVERPASS_EXACT_VERSION = 'overpass-exact-scan-v1'


def reference(candidate):
    if not Registry.approved(candidate,'world_storage'):
        return None
    value=(candidate.get('evidence') or {}).get('reference')
    return value if isinstance(value,str) and 1 <= len(value) <= 300 else None


def failed(operation, exc):
    LOG.info('poi_world_optional %s',json.dumps(dict(operation=operation,status='skipped',error_type=type(exc).__name__)))


def demand(service,spatial):
    if os.environ.get('CHAOS_POI_DISCOVERY_MODE','off')!='passive':
        return
    try:
        from .discovery_queue import DemandQueue
        DemandQueue(service.repo).record(spatial['lon'],spatial['lat'])
    except Exception as exc:
        failed('demand',exc)


def store(service, candidate, key, owner, batch, fresh_ttl, stale_ttl, *, adapter_version=MAPLARK_VERSION):
    if os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED')!='1':
        return
    ref=reference(candidate)
    if ref is None:
        return
    try:
        proof=SelectionProof('exact','poi',batch.profile,batch.selection,adapter_version,key)
        now=time.time()
        retention = {}
        if os.environ.get('CHAOS_POI_WORLD_ACCESS_MODE') == 'global':
            until = min(now+7*86400, candidate['review_due_at'])
            if until >= now+stale_ttl:
                retention['retain_until'] = until
        snapshot=CanonicalWorldRepository(service.repo).publish_batch(key,owner,batch,
            provider=candidate['id'],revision=candidate['revision'],storage_reference=ref,
            fresh_until=now+fresh_ttl,usable_until=now+stale_ttl,coverage=proof,**retention)
        LOG.info('poi_world_optional %s',json.dumps(dict(operation='store',status='stored' if snapshot else 'lease_lost')))
    except Exception as exc:
        failed('store',exc)


def read(service, candidate, key, active, allow_stale=False, *, overpass=False):
    if os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED')!='1':
        return None
    ref=reference(candidate)
    if ref is None:
        return None
    try:
        result=WorldReadPlanner(CanonicalWorldRepository(service.repo)).read(
            provider=candidate['id'],revision=candidate['revision'],storage_reference=ref,
            profile=POI_PROFILE,
            selection='overpass-around-v1' if overpass else 'maplark-radius-unverified',
            adapter_version=OVERPASS_EXACT_VERSION if overpass else MAPLARK_VERSION,
            query_key=key,allow_stale=allow_stale,still_active=active)
        if result.batch is not None and active():
            return validate(result.batch.export_overpass() if overpass else export_maplark(result.batch),service.config)
    except Exception as exc:
        failed('read',exc)
    return None


def store_overpass(service, candidate, key, owner, data, fresh_ttl, stale_ttl):
    if os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED') != '1' or reference(candidate) is None:
        return
    try:
        from .world_adapters import normalize_overpass
        from .world_contract import Provenance
        batch = normalize_overpass(data, Provenance(candidate['id'], OVERPASS_EXACT_VERSION,
            key, time.time(), license_ref='ODbL-1.0'))
        # The stored contract must round-trip before publishing a selection proof.
        batch.export_overpass()
        store(service, candidate, key, owner, batch, min(fresh_ttl, 300), min(stale_ttl, 1800),
              adapter_version=OVERPASS_EXACT_VERSION)
    except Exception as exc:
        failed('store_overpass', exc)
