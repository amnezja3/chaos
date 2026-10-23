"""Allowlisted pilot using the existing registry, exact cache, leases and budget."""
import os
import time
import uuid

from .maplark_profile import ENDPOINT, PROFILE, export_maplark
from .providers import Registry
from .service import POIError, validate
from .world_acquisition import acquire_maplark
from .world_adapters import plan_maplark
from .world_contract import FILTERS, ContractError, batch_key


def pilot_user(user):
    return (os.environ.get('CHAOS_POI_MAPLARK_PILOT_ENABLED') == '1'
            and isinstance(user, str) and user in {
                v.strip() for v in os.environ.get('CHAOS_POI_MAPLARK_PILOT_USERS', '').split(',') if v.strip()})


def fetch_pilot(service, spatial, fresh_ttl, stale_ttl, live):
    if os.environ.get('CHAOS_POI_MAPLARK_PILOT_ENABLED') != '1':
        raise POIError('maplark_pilot_disabled')
    if not spatial or tuple(spatial['filters']) != FILTERS:
        raise POIError('maplark_filter_profile_mismatch')
    registry = Registry(service.repo)
    # Schema/configuration must have been prepared explicitly, not by a player.
    def eligible():
        return next((v for v in registry.eligible('normal_scan') if v['url'] == ENDPOINT
                     and registry.approved(v, 'storage')), None)
    candidate = eligible()
    if not candidate:
        raise POIError('maplark_not_approved')
    plan = plan_maplark(spatial['lat'], spatial['lon'], spatial['radius'], limit=1000)
    key = batch_key('maplark', PROFILE, plan.profile, PROFILE,
                    {'params': plan.params, 'revision': candidate['revision']})
    def active():
        current = eligible()
        return (os.environ.get('CHAOS_POI_MAPLARK_PILOT_ENABLED') == '1' and live()
                and current is not None and current['revision'] == candidate['revision'])
    def cached(ttl):
        if not active():
            raise POIError('scanner_inactive_or_provider_changed')
        data = service.repo.read(key, ttl)
        return validate(data, service.config) if data is not None else None
    data = cached(fresh_ttl)
    if data is not None:
        return data, 'fresh'
    owner = None
    wait_until = time.monotonic() + service.config.join_wait
    try:
        while owner is None:
            if not active():
                raise POIError('scanner_inactive_or_provider_changed')
            owner = service.repo.acquire(key, 42)
            if owner:
                break
            data = cached(fresh_ttl)
            if data is not None:
                return data, 'fresh'
            if time.monotonic() >= wait_until:
                raise POIError('join_timeout')
            time.sleep(.05)
        data = cached(fresh_ttl)
        if data is not None:
            return data, 'fresh'
        # No default variable-price consent or invented reservation bound.
        reservation = int(os.environ.get('CHAOS_MAPLARK_CREDIT_RESERVATION', '0'))
        started = time.monotonic()
        status = 'error'
        try:
            batch, billing = acquire_maplark(service.repo, plan, uuid.uuid4().hex, reservation,
                accept_variable_cost=os.environ.get('CHAOS_MAPLARK_ACCEPT_VARIABLE_COST') == '1',
                still_active=lambda: active() and service.repo.owns(key, owner))
            data = validate(export_maplark(batch), service.config)
            if not active() or not service.repo.write(key, owner, data, stale_ttl):
                raise POIError('cache_capacity_or_lease_lost')
            status = '200'
            return data, 'upstream'
        except (POIError, ContractError) as exc:
            status = str(exc)
            raise
        finally:
            registry.record_health(candidate['id'], candidate['revision'], 'maplark_scan', status,
                                   time.monotonic()-started)
    finally:
        if owner:
            service.repo.release(key, owner)
