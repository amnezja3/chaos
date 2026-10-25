"""Explicit bounded process driver. No automatic permissions or budget creation."""
import json
import os

from .discovery_worker import DiscoveryPermit, DiscoveryWorker
from .discovery_producer import prepare_jobs


def load_permit(path):
    with open(path, 'rb') as f:
        raw=f.read(8193)
    if len(raw)>8192: raise ValueError('permit_size')
    data=json.loads(raw)
    required={'cells','profiles','until','reservation','budget_id'}
    if not isinstance(data,dict) or not required <= set(data) or set(data)-required-{'acquisition','retention_seconds'}:
        raise ValueError('permit_fields')
    if not isinstance(data['cells'],list) or not isinstance(data['profiles'],list):
        raise ValueError('permit_fields')
    permit=DiscoveryPermit(frozenset(tuple(c) for c in data['cells']),
        frozenset(data['profiles']),data['until'],data['reservation'],data['budget_id'],
        data.get('acquisition','radius-300-v1'),data.get('retention_seconds',1800))
    permit.validate()
    for profile in permit.profiles: permit.budget_scopes(profile)
    return permit


def cycle(repo, path, *, execute=False, stopping=lambda: False, transport=None):
    # Flag OFF is a no-op even if permit/database/secret do not exist.
    if execute and (os.environ.get('CHAOS_POI_DISCOVERY_WORKER_ENABLED')!='1' or stopping()):
        return dict(status='disabled',network_calls=0)
    permit=load_permit(path)
    permit.validate_budgets(repo)
    if not execute:
        return prepare_jobs(repo,permit,apply=False)
    def active():
        if stopping() or os.environ.get('CHAOS_POI_DISCOVERY_WORKER_ENABLED')!='1': return False
        try:
            return load_permit(path)==permit
        except (OSError,ValueError,TypeError):
            return False
    if not active(): return dict(status='permit_changed',network_calls=0)
    # File removal/expiry/replacement stops admission and publication in flight.
    # Per-job leases plus the shared upstream slot coordinate competing processes.
    if os.environ.get('CHAOS_POI_PRIORITY_ENABLED')!='1':
        return dict(status='priority_required',network_calls=0)
    prepare_jobs(repo,permit,apply=True)
    return DiscoveryWorker(repo,permit,enabled=active,transport=transport).run_one()
