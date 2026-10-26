"""Exact-query cache, shared single-flight and bounded Overpass transport."""
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import random
import sqlite3
import time
from urllib.parse import urlsplit
import uuid

import overpy
import requests
from .repository import Repository
from . import logger

LOG = logger()


class POIError(RuntimeError):
    pass


class Cancelled(POIError):
    pass


class UpstreamUnavailable(POIError):
    """A transport outage, not a parsing/configuration/application error."""


@dataclass(frozen=True)
class Config:
    deadline: float = 110
    join_wait: float = 2
    connect_timeout: float = 3
    max_response: int = 4 * 1024 * 1024
    max_elements: int = 20000
    max_cache: int = 64 * 1024 * 1024
    max_entries: int = 2000
    diagnostic_errors: bool = False

    @classmethod
    def environment(cls):
        defaults = cls()
        bounds = {'deadline': (1, 110), 'join_wait': (0, 10), 'connect_timeout': (.1, 5),
                  'max_response': (1024, 16 * 1024 * 1024), 'max_elements': (1, 50000),
                  'max_cache': (1024 * 1024, 256 * 1024 * 1024), 'max_entries': (1, 5000)}
        values = {}
        for name, (low, high) in bounds.items():
            default = getattr(defaults, name)
            raw = os.environ.get('CHAOS_POI_' + name.upper(), str(default))
            value = float(raw) if name in ('deadline', 'join_wait', 'connect_timeout') else int(raw)
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError('Invalid POI setting: ' + name)
            values[name] = value
        return cls(**values)


def key_for(query):
    # Exact wire query is the authority, including filter order and geometry.
    return hashlib.sha256(('poi-ql-v1:out-center-v1\n' + query).encode()).hexdigest()


def group_for(endpoint):
    host = urlsplit(endpoint).hostname or ''
    return 'overpass-api.de' if host.endswith('.overpass-api.de') or host == 'overpass-api.de' else host


def validate(data, config):
    if not isinstance(data, dict) or not isinstance(data.get('elements'), list) or data.get('remark'):
        raise POIError('invalid_response')
    if len(data['elements']) > config.max_elements:
        raise POIError('response_limit')
    for e in data['elements']:
        if not isinstance(e, dict) or e.get('type') not in ('node', 'way', 'relation') or type(e.get('id')) is not int:
            raise POIError('invalid_element')
        if not isinstance(e.get('tags', {}), dict):
            raise POIError('invalid_tags')
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in e.get('tags', {}).items()):
            raise POIError('invalid_tags')
        # Do not discard ways/relations based on distance of their bbox center.
        point = e if e['type'] == 'node' else e.get('center')
        if point is not None:
            if not isinstance(point, dict):
                raise POIError('invalid_coordinates')
            for field, limit in [('lat', 90), ('lon', 180)]:
                value = point.get(field)
                if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > limit:
                    raise POIError('invalid_coordinates')
    try:
        overpy.Result.from_json(data)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise POIError('invalid_response') from exc
    return data


def retry_delay(value):
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return 0
    return max(0, seconds) if math.isfinite(seconds) else 86400


def _http_child(pipe, config, endpoint, query, timeout, deadline, secure=False):
    try:
        if secure == 'world-features':
            from .secure_transport import request
            result = request(config, endpoint, '', timeout, deadline, feature_plan=query)
        elif secure:
            from .secure_transport import request
            result = request(config, endpoint, query, timeout, deadline)
        else:
            result = Service(config=config).http(endpoint, query, timeout, deadline)
        pipe.send((True, result, False))
    except Exception as exc:
        pipe.send((False, str(exc) if isinstance(exc, POIError) else type(exc).__name__,
                   isinstance(exc, (requests.Timeout, requests.ConnectionError, UpstreamUnavailable))))
    finally:
        pipe.close()


def bounded_http(config, endpoint, query, timeout, deadline, secure=False):
    """Same killable spawn pattern as LLM executor; no abandoned HTTP threads."""
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_http_child, args=(child, config, endpoint, query, timeout, deadline, secure), daemon=True)
    try:
        process.start()
        child.close()
        if not parent.poll(max(0, deadline - time.monotonic())):
            raise UpstreamUnavailable('deadline')
        try:
            ok, result, unavailable = parent.recv()
        except EOFError as exc:
            raise POIError('http_process_failed') from exc
        if time.monotonic() >= deadline:
            raise POIError('deadline')
        if not ok:
            raise (UpstreamUnavailable if unavailable else POIError)(result)
        return result
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()


class Service:
    def __init__(self, path=None, config=None, transport=None):
        self.config = config or Config.environment()
        self.repo = Repository(path or os.environ.get('CHAOS_POI_CACHE_PATH') or Path(__file__).resolve().parents[1] / 'data/poi_cache.sqlite3', self.config.max_cache, self.config.max_entries)
        self.transport = transport or (lambda *args: bounded_http(self.config, *args))
        self._initialized_pid = None

    def http(self, endpoint, query, timeout, deadline):
        if os.environ.get('CHAOS_POI_PROVIDER_REGISTRY_ENABLED', '').strip() == '1':
            from .secure_transport import request
            return request(self.config, endpoint, query, timeout, deadline)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise POIError('deadline')
        with requests.post(endpoint, data={'data': query}, headers={'User-Agent': 'CHAOS/POI-v1 (+https://chaos.re; year2108@chaos.re)', 'Accept': 'application/json'},
                           timeout=(min(self.config.connect_timeout, remaining), min(timeout, remaining)), stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                return response.status_code, response.headers.get('Retry-After'), None
            raw = bytearray()
            for chunk in response.iter_content(chunk_size=1024):
                if time.monotonic() >= deadline:
                    raise POIError('deadline')
                raw.extend(chunk)
                if len(raw) > self.config.max_response:
                    raise POIError('response_limit')
            try:
                return 200, None, json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise POIError('invalid_json') from exc

    def fetch(self, query, endpoints, timeout, fresh_ttl, stale_ttl, options=None):
        options = options or {}
        if os.environ.get('CHAOS_POI_ROUTING_ENABLED') == '1' and options.get('_spatial'):
            from .scan_router import fetch_routed
            return fetch_routed(self,query,timeout,fresh_ttl,stale_ttl,options)
        if options.get('_maplark_pilot') is True:
            from .maplark_pilot import fetch_pilot
            from .presentation import publish
            try:
                data, pilot_source = fetch_pilot(self, options.get('_spatial'), fresh_ttl, stale_ttl,
                                   options.get('still_active', lambda: True),
                                   world_user=options.get('_world_pilot_user'))
                publish(pilot_source, {}, False)
                LOG.info('poi_maplark %s', json.dumps(dict(source=pilot_source, result='success')))
                return data
            except Exception as exc:
                publish('error', {}, False)
                LOG.info('poi_maplark %s', json.dumps(dict(result='error', error_type=type(exc).__name__)))
                raise
        live = options.get('still_active', lambda: True)
        started = time.monotonic()
        deadline = started + self.config.deadline
        key = key_for(query)
        owner = slot = None
        fill_owner = fill_key = fill_bounds = fill_query = None
        spatial = options.get('_spatial')
        wide_attempted = False
        source, error, attempts = 'error', '', 0
        joined, wait_seconds = False, 0.0
        request_id = uuid.uuid4().hex
        restored = False
        policy = {}
        policy_eligible = True
        registry = None
        candidates = {}
        world = None

        def local_world(stale=False):
            if not world or os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED','').strip()!='1':
                return None
            data = world.read_exact(key, allow_stale=stale, config=self.config)
            if data is None and spatial:
                data = world.read_geometry(**spatial, allow_stale=stale, config=self.config)
            active()
            return data

        def active():
            if not live():
                raise Cancelled('scanner_inactive')

        def cached(ttl):
            data = self.repo.read(key, ttl)
            if data is not None:
                try:
                    result = validate(data, self.config)
                except POIError:
                    return None
                active()
                return result

        def fallback():
            active()
            data = cached(stale_ttl)
            if data is None:
                data = local_world(True)
            if data is None:
                raise POIError(error or 'upstream_unavailable')
            active()
            return data

        try:
            active()
            if os.environ.get('CHAOS_POI_WIDE_FETCH_ENABLED','').strip()=='1' and any(
                    os.environ.get(f,'').strip()!='1' for f in ('CHAOS_POI_WORLD_INGEST_ENABLED',
                    'CHAOS_POI_WORLD_REPOSITORY_ENABLED','CHAOS_POI_PROVIDER_REGISTRY_ENABLED')):
                raise POIError('wide_fetch_dependencies')
            if self._initialized_pid != os.getpid():
                self.repo.initialize()
                self._initialized_pid = os.getpid()
            if os.environ.get('CHAOS_POI_PROVIDER_REGISTRY_ENABLED', '').strip() == '1':
                from .providers import Registry
                registry = Registry(self.repo)
                registry.initialize()
                candidates = {v['url']: v for v in registry.eligible('normal_scan')
                              if v['url'] not in ('https://api.maplark.com/v3/osm_features',
                                                  'https://api.geoapify.com/v2/places')}
                # Keep the caller's attempt budget, but not its old static URLs.
                urls = list(candidates)
                endpoints = [urls[i % len(urls)] for i in range(len(endpoints))] if urls else []
            if any(os.environ.get(flag, '').strip() == '1' for flag in
                   ('CHAOS_POI_WORLD_INGEST_ENABLED','CHAOS_POI_WORLD_REPOSITORY_ENABLED')):
                from .world import WorldRepository
                world = WorldRepository(self.repo)
                try:
                    world.initialize()
                    world.prune_expired(limit=20)
                except (sqlite3.Error,OSError,POIError):
                    if os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED','').strip()=='1':
                        raise
                    world = None
                    LOG.warning('poi_world shadow_initialize_failed')
            data = cached(fresh_ttl)
            if data is not None:
                source = 'fresh'
                return data
            if world and os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED', '').strip() == '1':
                data = local_world()
                if data is not None:
                    active()
                    source = 'world'
                    return data
            from .world_access import network_paused
            if network_paused():
                error = 'scan_network_paused'
                source = 'stale'
                return fallback()
            if registry and not endpoints:
                policy_eligible = False
                error = 'provider_configuration_unavailable'
                source = 'stale'
                return fallback()
            wait_until = min(deadline, started + self.config.join_wait)
            while owner is None:
                active()
                owner = self.repo.acquire(key, self.config.deadline + 5)
                if owner:
                    break
                joined = True
                wait_seconds = time.monotonic() - started
                data = cached(fresh_ttl)
                if data is not None:
                    source = 'fresh'
                    return data
                if time.monotonic() >= wait_until:
                    error = 'join_timeout'
                    source = 'stale'
                    return fallback()
                time.sleep(.05)
            # A previous owner may have filled the cache before our acquisition.
            data = cached(fresh_ttl)
            if data is not None:
                active()
                source = 'fresh'
                return data
            if (spatial and world and registry and os.environ.get('CHAOS_POI_WIDE_FETCH_ENABLED','').strip()=='1'
                    and any(registry.approved(c,'wide_fetch') and registry.approved(c,'storage') for c in candidates.values())):
                from .geometry import fill_plan, UncertifiedGeometry
                try:
                    fill_bounds,fill_query = fill_plan(**spatial)
                    fill_key = 'world-fill:'+key_for(fill_query)
                except UncertifiedGeometry:
                    fill_query = None
                if fill_query:
                    while fill_owner is None:
                        active()
                        data = local_world()
                        if data is not None:
                            source = 'world'
                            return data
                        fill_owner = self.repo.acquire(fill_key,self.config.deadline+5)
                        if fill_owner:
                            break
                        if time.monotonic() >= wait_until:
                            error,source = 'join_timeout','stale'
                            return fallback()
                        time.sleep(.05)
                    data = local_world()
                    if data is not None:
                        source = 'world'
                        return data
            for index, endpoint in enumerate(endpoints):
                active()
                if time.monotonic() >= deadline or not self.repo.owns(key, owner):
                    error = 'deadline_or_lease_lost'
                    break
                candidate = candidates.get(endpoint)
                group = candidate['operator_group'] if candidate else group_for(endpoint)
                if not self.repo.allowed(group):
                    error = 'circuit_open'
                    continue
                # One global network slot also serializes half-open probes.
                slot = self.repo.acquire('@upstream', self.config.deadline + 5, probe_group=group)
                if slot is None:
                    error = 'upstream_busy'
                    break
                delay = 0
                permanent = False
                probe = slot if self.repo.owns('@probe:' + group, slot) else None
                transport_started = None
                transport_status = 'not_sent'
                operation = 'normal_scan'
                try:
                    if registry:
                        # Re-read before every new network call: disable and edits
                        # propagate across all workers without a process restart.
                        current = next((v for v in registry.eligible('normal_scan') if v['id']==candidate['id']),None)
                        if not current or current['revision'] != candidate['revision']:
                            policy_eligible = False
                            error = 'provider_configuration_changed'
                            continue
                    if not self.repo.allowed(group):
                        error = 'circuit_open'
                        continue
                    attempts += 1
                    transport_started = time.monotonic()
                    use_wide = bool(fill_owner and not wide_attempted and candidate
                                    and registry.approved(current,'wide_fetch') and registry.approved(current,'storage')
                                    and self.repo.owns(fill_key,fill_owner))
                    if use_wide:
                        wide_attempted = True
                        operation = 'wide_fetch'
                    from .scan_metrics import transport_attempt
                    transport_attempt()
                    status, retry, data = self.transport(endpoint, fill_query if use_wide else query, timeout, deadline)
                    transport_status = str(status)
                    LOG.info('poi_http %s', json.dumps(dict(provider=group, status=status)))
                    if status == 200:
                        data = validate(data, self.config)
                        if time.monotonic() >= deadline or not self.repo.owns('@upstream', slot):
                            raise POIError('deadline_or_slot_lost')
                        if use_wide:
                            from .geometry import CoveredGeometry
                            # Incomplete/unsupported geometry consumes this attempt;
                            # the remaining exact attempts retain the same deadline.
                            selected = CoveredGeometry(data,**fill_bounds).select(**spatial)
                            if not world.publish_geometry(fill_key,fill_owner,data,candidate['id'],
                                    fresh_ttl,stale_ttl,**fill_bounds,config=self.config):
                                raise POIError('fill_lease_lost')
                            data = validate(selected,self.config)
                        if not self.repo.write(key, owner, data, stale_ttl):
                            raise POIError('cache_capacity_or_lease_lost')
                        self.repo.outcome(group, True)
                        if (not use_wide and world and os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED','').strip()=='1'
                                and candidate and registry.approved(candidate,'storage')):
                            try:
                                world.publish_exact(key,owner,data,candidate['id'],fresh_ttl,stale_ttl,self.config)
                            except (sqlite3.Error,OSError,POIError,ValueError):
                                LOG.warning('poi_world shadow_write_failed')
                        restored = bool(probe)
                        active()
                        source = 'upstream'
                        return data
                    error = 'http_' + str(status)
                    delay = retry_delay(retry)
                    permanent = status not in (429, 500, 502, 503, 504)
                    policy_eligible = not permanent
                    if policy_eligible:
                        self.repo.outcome(group, False, delay or (30 if status == 429 else 0))
                except Cancelled:
                    raise
                except (requests.RequestException, POIError, ValueError) as exc:
                    error = str(exc) if isinstance(exc, POIError) else type(exc).__name__
                    transport_status = error
                    LOG.info('poi_http %s', json.dumps(dict(provider=group, status='error', error=error)))
                    policy_eligible = isinstance(exc, (requests.Timeout, requests.ConnectionError, UpstreamUnavailable))
                    if policy_eligible:
                        self.repo.outcome(group, False)
                finally:
                    if registry and transport_started is not None:
                        try:
                            registry.record_health(candidate['id'],candidate['revision'],operation,
                                transport_status,time.monotonic()-transport_started)
                        except (sqlite3.Error,OSError):
                            LOG.warning('poi_health write_failed')
                    if probe:
                        self.repo.release('@probe:' + group, probe)
                    self.repo.release('@upstream', slot)
                    slot = None
                if permanent:
                    break
                if index + 1 < len(endpoints):
                    delay = max(delay, min(4, .25 * 2 ** index) + random.uniform(0, .1))
                    if time.monotonic() + delay >= deadline:
                        break
                    end = time.monotonic() + delay
                    while time.monotonic() < end:
                        active()
                        time.sleep(min(.05, end - time.monotonic()))
            source = 'stale'
            return fallback()
        except Cancelled:
            source, error = 'cancelled', 'scanner_inactive'
            raise
        except (sqlite3.Error, OSError) as exc:
            source, error = 'error', 'storage_unavailable'
            # Never bypass shared coordination with an unbudgeted HTTP request.
            raise POIError(error) from exc
        except POIError as exc:
            source, error = 'error', str(exc)
            # Only the shared policy proves a block. A timeout, malformed JSON,
            # application exception or exhausted budget alone does not.
            try:
                policy = self.repo.presentation_policy(
                    candidates[e]['operator_group'] if e in candidates else group_for(e)
                    for e in endpoints) if policy_eligible else {}
            except (sqlite3.Error, OSError):
                policy = {}
            raise
        finally:
            from .presentation import publish
            publish(source, policy, restored)
            for lease_key, token in [('@upstream', slot), (key, owner), (fill_key,fill_owner)]:
                if token:
                    try:
                        self.repo.release(lease_key, token)
                    except (sqlite3.Error, OSError):
                        pass  # Expiration recovers ownership after storage failure.
            LOG.info('poi_fetch %s', json.dumps(dict(request_id=request_id, key=key[:12], source=source,
                     error=error, attempts=attempts, joined=joined, wait_seconds=round(wait_seconds,4),
                     seconds=round(time.monotonic()-started, 4))))
