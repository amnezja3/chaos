"""Allowlisted pilot using the existing registry, exact cache, leases and budget."""
import os
import time
import uuid
import json

from .maplark_profile import ENDPOINT, PROFILE, export_maplark
from .providers import Registry
from .service import POIError, UpstreamUnavailable, validate, LOG
from .world_acquisition import acquire_maplark
from .world_adapters import plan_maplark
from .world_contract import FILTERS, ContractError, batch_key


def enabled():
    return (os.environ.get('CHAOS_POI_MAPLARK_ENABLED') == '1' or
            os.environ.get('CHAOS_POI_MAPLARK_PILOT_ENABLED') == '1')


def pilot_user(user):
    if not isinstance(user, str) or not user:
        return False
    if os.environ.get('CHAOS_POI_MAPLARK_ENABLED') == '1':
        return True
    return (os.environ.get('CHAOS_POI_MAPLARK_PILOT_ENABLED') == '1'
            and isinstance(user, str) and user in {
                v.strip() for v in os.environ.get('CHAOS_POI_MAPLARK_PILOT_USERS', '').split(',') if v.strip()})


def fetch_pilot(service, spatial, fresh_ttl, stale_ttl, live):
    if not enabled():
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
    from . import world_shadow
    world_shadow.demand(service,spatial)
    plan = plan_maplark(spatial['lat'], spatial['lon'], spatial['radius'], limit=1000)
    key = batch_key('maplark', PROFILE, plan.profile, PROFILE,
                    {'params': plan.params, 'revision': candidate['revision']})
    def active():
        current = eligible()
        return (enabled() and live()
                and current is not None and current['revision'] == candidate['revision'])
    def cached(ttl):
        if not active():
            raise POIError('scanner_inactive_or_provider_changed')
        data = service.repo.read(key, ttl)
        return validate(data, service.config) if data is not None else None
    def result(data, source):
        LOG.info('poi_maplark_cache %s', json.dumps(dict(
            source=source,key=key[:12],revision=candidate['revision'],
            fresh_ttl=fresh_ttl,stale_ttl=stale_ttl,pid=os.getpid(),at=round(time.time(),3))))
        return data, source
    data = cached(fresh_ttl)
    if data is not None:
        return result(data, 'fresh')
    data = world_shadow.read(service,candidate,key,active)
    if data is not None:
        return result(data,'world')
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
                return result(data, 'fresh')
            if time.monotonic() >= wait_until:
                raise POIError('join_timeout')
            time.sleep(.05)
        data = cached(fresh_ttl)
        if data is not None:
            return result(data, 'fresh')
        data = world_shadow.read(service,candidate,key,active)
        if data is not None:
            return result(data,'world')
        if os.environ.get('CHAOS_POI_MAPLARK_ENABLED') == '1':
            from .credit_budget import CreditBudget
            windows = CreditBudget(service.repo).status('maplark')
            if {w['period'] for w in windows} != {'utc_day','rolling_31_days'}:
                raise POIError('maplark_rollout_budget_not_configured')
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
            world_shadow.store(service,candidate,key,owner,batch,fresh_ttl,stale_ttl)
            if not active():
                raise POIError('scanner_inactive_or_provider_changed')
            status = '200'
            return result(data, 'upstream')
        except (POIError, ContractError) as exc:
            status = str(exc)
            raise
        finally:
            registry.record_health(candidate['id'], candidate['revision'], 'maplark_scan', status,
                                   time.monotonic()-started)
    except (POIError, ContractError) as exc:
        # Exact, time-bounded stale data remains usable on temporary upstream
        # failure/budget exhaustion. Never bypass disabled/revised providers.
        if (isinstance(exc, UpstreamUnavailable) or str(exc) in (
                'budget_exhausted','budget_account_held','budget_previous_period_unresolved',
                'circuit_open','upstream_busy','join_timeout','http_429','http_500',
                'http_502','http_503','http_504')):
            stale = cached(stale_ttl)
            if stale is not None:
                return result(stale, 'stale')
            stale = world_shadow.read(service,candidate,key,active,allow_stale=True)
            if stale is not None:
                return result(stale,'stale')
        raise
    finally:
        if owner:
            service.repo.release(key, owner)
