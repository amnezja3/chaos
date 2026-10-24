"""Request-local presentation evidence; never stores player state in POI cache."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import os
import time

_capture = ContextVar('poi_presentation', default=None)


def enabled():
    return all(os.environ.get(key, '').strip() == '1' for key in
               ('CHAOS_POI_INFRASTRUCTURE_ENABLED', 'CHAOS_POI_MASA_UX_ENABLED'))


@contextmanager
def capture():
    evidence = {}
    token = _capture.set(evidence)
    try:
        yield evidence
    finally:
        _capture.reset(token)


def publish(source, policy=None, restored=False):
    from .scan_metrics import source as record_source
    record_source(source)
    evidence = _capture.get()
    if evidence is None or not enabled():
        return
    policy = policy or {}
    state = ('degraded' if source == 'stale' else
             'restored' if source == 'upstream' and restored else
             'ready' if source in ('fresh', 'world', 'upstream') else policy.get('state'))
    if state not in ('ready', 'degraded', 'restored', 'blocked', 'recovering'):
        return
    now = time.time()
    signal = {'type': 'masa', 'state': state,
              'server_now': datetime.fromtimestamp(now, timezone.utc).isoformat()}
    until = policy.get('blocked_until')
    if state == 'blocked' and isinstance(until, (int, float)) and now < until < 253402300799:
        signal.update(blocked_until=datetime.fromtimestamp(until, timezone.utc).isoformat(),
                      retry_after_seconds=round(until-now, 3))
    evidence.update(interference=signal, poi_data_mode=source)
    if state in ('blocked', 'recovering'):
        evidence['failure_reason'] = 'poi_upstream_unavailable'


def public_fields(evidence):
    if not enabled() or not evidence:
        return {}
    return dict(evidence)
