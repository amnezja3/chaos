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


def _http_child(pipe, config, endpoint, query, timeout, deadline):
    try:
        pipe.send((True, Service(config=config).http(endpoint, query, timeout, deadline), False))
    except Exception as exc:
        pipe.send((False, str(exc) if isinstance(exc, POIError) else type(exc).__name__,
                   isinstance(exc, (requests.Timeout, requests.ConnectionError, UpstreamUnavailable))))
    finally:
        pipe.close()


def bounded_http(config, endpoint, query, timeout, deadline):
    """Same killable spawn pattern as LLM executor; no abandoned HTTP threads."""
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_http_child, args=(child, config, endpoint, query, timeout, deadline), daemon=True)
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
        live = options.get('still_active', lambda: True)
        started = time.monotonic()
        deadline = started + self.config.deadline
        key = key_for(query)
        owner = slot = None
        source, error, attempts = 'error', '', 0
        joined, wait_seconds = False, 0.0
        request_id = uuid.uuid4().hex
        restored = False
        policy = {}
        policy_eligible = True

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
                raise POIError(error or 'upstream_unavailable')
            return data

        try:
            active()
            if self._initialized_pid != os.getpid():
                self.repo.initialize()
                self._initialized_pid = os.getpid()
            data = cached(fresh_ttl)
            if data is not None:
                source = 'fresh'
                return data
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
            for index, endpoint in enumerate(endpoints):
                active()
                if time.monotonic() >= deadline or not self.repo.owns(key, owner):
                    error = 'deadline_or_lease_lost'
                    break
                group = group_for(endpoint)
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
                try:
                    if not self.repo.allowed(group):
                        error = 'circuit_open'
                        continue
                    attempts += 1
                    status, retry, data = self.transport(endpoint, query, timeout, deadline)
                    LOG.info('poi_http %s', json.dumps(dict(provider=group, status=status)))
                    if status == 200:
                        data = validate(data, self.config)
                        if time.monotonic() >= deadline or not self.repo.owns('@upstream', slot):
                            raise POIError('deadline_or_slot_lost')
                        if not self.repo.write(key, owner, data, stale_ttl):
                            raise POIError('cache_capacity_or_lease_lost')
                        self.repo.outcome(group, True)
                        restored = bool(probe)
                        active()
                        source = 'upstream'
                        return data
                    error = 'http_' + str(status)
                    delay = retry_delay(retry)
                    permanent = status not in (429, 502, 503, 504)
                    policy_eligible = not permanent
                    if policy_eligible:
                        self.repo.outcome(group, False, delay or (30 if status == 429 else 0))
                except Cancelled:
                    raise
                except (requests.RequestException, POIError, ValueError) as exc:
                    error = str(exc) if isinstance(exc, POIError) else type(exc).__name__
                    LOG.info('poi_http %s', json.dumps(dict(provider=group, status='error', error=error)))
                    policy_eligible = isinstance(exc, (requests.Timeout, requests.ConnectionError, UpstreamUnavailable))
                    if policy_eligible:
                        self.repo.outcome(group, False)
                finally:
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
                policy = self.repo.presentation_policy(group_for(e) for e in endpoints) if policy_eligible else {}
            except (sqlite3.Error, OSError):
                policy = {}
            raise
        finally:
            from .presentation import publish
            publish(source, policy, restored)
            for lease_key, token in [('@upstream', slot), (key, owner)]:
                if token:
                    try:
                        self.repo.release(lease_key, token)
                    except (sqlite3.Error, OSError):
                        pass  # Expiration recovers ownership after storage failure.
            LOG.info('poi_fetch %s', json.dumps(dict(request_id=request_id, key=key[:12], source=source,
                     error=error, attempts=attempts, joined=joined, wait_seconds=round(wait_seconds,4),
                     seconds=round(time.monotonic()-started, 4))))
