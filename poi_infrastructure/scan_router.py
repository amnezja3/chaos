"""Bounded live route: all fresh local sources, then one attempt per provider.

No implicit cross-provider fallback, no reset of the scan deadline. Routes and
provider revisions are fenced throughout the operation. Partial data never wins.
"""
import json
import os
import time

from .routing import Routing, adapter, reason
from .providers import Registry
from .service import POIError, UpstreamUnavailable, bounded_http, key_for, validate, retry_delay, LOG

RETRYABLE = frozenset(('circuit_open','upstream_busy','join_timeout','budget_exhausted',
    'budget_account_held','budget_previous_period_unresolved','http_429','http_500',
    'http_502','http_503','http_504','provider_response_incomplete','invalid_response'))


def _overpass(service, candidate, query, timeout, fresh_ttl, stale_ttl, phase, active, deadline):
    # Namespace by source/revision: changing a chain cannot reuse an unrelated result.
    key = key_for(json.dumps([candidate['id'],candidate['revision'],query]))
    def local(ttl):
        if not active():
            raise POIError('routing_changed_or_cancelled')
        data = service.repo.read(key,ttl)
        return validate(data,service.config) if data is not None else None
    data = local(stale_ttl if phase=='stale' else fresh_ttl)
    if data is not None or phase != 'network':
        return data, 'stale' if phase=='stale' else 'fresh'
    group = candidate['operator_group']
    if not service.repo.allowed(group):
        raise POIError('circuit_open')
    owner = service.repo.acquire(key, min(115,max(1,deadline-time.monotonic()+5)))
    if not owner:
        raise POIError('join_timeout')
    slot = None
    try:
        data = local(fresh_ttl)
        if data is not None:
            return data,'fresh'
        if time.monotonic() >= deadline:
            raise POIError('deadline')
        if os.environ.get('CHAOS_POI_PRIORITY_ENABLED')=='1':
            from .upstream_priority import UpstreamPriority
            gate=UpstreamPriority(service.repo); ticket=gate.register()
            try:
                slot=gate.acquire(lane='live',ticket=ticket,group=group) if ticket else None
            finally:
                gate.cancel(ticket)
        else:
            slot=service.repo.acquire('@upstream',42,probe_group=group)
        if not slot:
            raise POIError('upstream_busy')
        if not active():
            raise POIError('routing_changed_or_cancelled')
        stop=min(deadline,time.monotonic()+35)
        from .scan_metrics import transport_attempt
        transport_attempt()
        status,retry,data=bounded_http(service.config,candidate['url'],query,min(timeout,30),stop,secure=True)
        if status!=200:
            if status in (429,500,502,503,504):
                service.repo.outcome(group,False,retry_delay(retry))
            raise POIError('http_'+str(status))
        data=validate(data,service.config)
        if time.monotonic()>=deadline or not active() or not service.repo.owns('@upstream',slot):
            raise POIError('routing_changed_or_cancelled')
        if not service.repo.write(key,owner,data,stale_ttl):
            raise POIError('cache_capacity_or_lease_lost')
        service.repo.outcome(group,True)
        return data,'upstream'
    except UpstreamUnavailable:
        service.repo.outcome(group,False)
        raise
    finally:
        if slot:
            service.repo.release('@probe:'+group,slot)
            service.repo.release('@upstream',slot)
        service.repo.release(key,owner)


def fetch_routed(service, query, timeout, fresh_ttl, stale_ttl, options):
    from .world_contract import ContractError
    from .maplark_pilot import fetch_pilot
    from .presentation import publish
    route_store=Routing(service.repo)
    route=route_store.get('poi','live')
    registry=Registry(service.repo)
    providers={p['id']:p for p in registry.list()}
    deadline=time.monotonic()+service.config.deadline
    live=options.get('still_active',lambda:True)
    observations=[]
    last=POIError('routing_no_eligible_provider')
    chosen=[]
    for provider_id in route['chain']:
        candidate=providers.get(provider_id)
        why=reason(candidate,'poi','live') if candidate else 'provider_missing'
        if (not why and adapter(candidate)=='maplark' and os.environ.get('CHAOS_POI_MAPLARK_ENABLED')!='1'
                and options.get('_maplark_pilot') is not True):
            why='maplark_pilot_user_not_allowed'
        if why:
            observations.append(dict(provider=provider_id,result='skipped',reason=why))
        else:
            chosen.append(candidate)

    def active(candidate):
        if os.environ.get('CHAOS_POI_ROUTING_ENABLED')!='1' or not live() or route_store.get('poi','live') != route:
            return False
        current=next((p for p in registry.list() if p['id']==candidate['id']),None)
        return bool(current and current['revision']==candidate['revision'] and not reason(current,'poi','live'))

    try:
        for phase in ('fresh','world','network','stale'):
            for candidate in chosen:
                if time.monotonic() >= deadline:
                    raise POIError('deadline')
                if not active(candidate):
                    raise POIError('routing_changed_or_cancelled')
                try:
                    started=time.monotonic()
                    guard=lambda:active(candidate)
                    if adapter(candidate)=='maplark':
                        data,source=fetch_pilot(service,options['_spatial'],fresh_ttl,stale_ttl,guard,
                            options.get('_world_pilot_user'),provider_id=candidate['id'],phase=phase,deadline=deadline)
                    else:
                        data,source=_overpass(service,candidate,query,timeout,fresh_ttl,stale_ttl,phase,guard,deadline)
                    if data is not None:
                        if not active(candidate):
                            raise POIError('routing_changed_or_cancelled')
                        publish(source,{},False)
                        observations.append(dict(provider=candidate['id'],result='success',source=source))
                        registry.record_health(candidate['id'],candidate['revision'],'route_'+phase,
                            'success:'+source,time.monotonic()-started)
                        return data
                except (POIError,ContractError) as exc:
                    last=exc
                    observations.append(dict(provider=candidate['id'],result='failed',reason=str(exc)))
                    registry.record_health(candidate['id'],candidate['revision'],'route_'+phase,
                        str(exc),time.monotonic()-started)
                    if not isinstance(exc,UpstreamUnavailable) and str(exc) not in RETRYABLE:
                        raise
        raise last
    except Exception:
        publish('error',{},False)
        raise
    finally:
        LOG.info('poi_route %s',json.dumps(dict(revision=route['revision'],observations=observations)))
