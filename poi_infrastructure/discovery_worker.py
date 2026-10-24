"""Bounded one-job executor; no daemon, automatic enqueue, or production wiring.

Execution requires an explicit short-lived region/profile permit and a live
enable callback. Observations do not certify reusable geographic coverage.
"""
from dataclasses import dataclass
import math
import os
import time

from .discovery_jobs import DiscoveryJobs
from .credit_budget import CreditBudget, _token
from .providers import Registry
from .service import POIError, bounded_http
from .world_acquisition import acquire_maplark
from .world_adapters import plan_maplark
from .world_storage import CanonicalWorldRepository
from .world_shadow import reference


@dataclass(frozen=True)
class DiscoveryPermit:
    cells: frozenset
    profiles: frozenset
    until: float
    reservation: int = 20
    budget_id: str = ''

    def budget_scopes(self, profile):
        _token(self.budget_id)
        if profile not in self.profiles:
            raise ValueError('discovery_profile_outside_permit')
        scopes = ('discovery:' + self.budget_id, 'discovery:' + self.budget_id + ':' + profile)
        for scope in scopes:
            _token(scope)
        return scopes

    def validate_budgets(self, repo):
        ledger = CreditBudget(repo)
        now = time.time()
        for profile in self.profiles:
            for scope in self.budget_scopes(profile):
                status = ledger.scope_status('maplark', scope)
                if not status or not status['starts'] <= now < self.until <= status['ends']:
                    raise ValueError('discovery_budget_missing_or_expired')

    def validate(self):
        if (not isinstance(self.cells, frozenset) or not 1 <= len(self.cells) <= 10
                or any(not isinstance(c, tuple) or len(c) != 2
                       or any(type(v) is not int for v in c)
                       or not -18000 <= c[0] < 18000 or not -9000 <= c[1] < 9000
                       for c in self.cells)
                or not isinstance(self.profiles, frozenset) or not self.profiles
                or not self.profiles <= {'roads', 'waterways', 'inland_water', 'coastline'}
                or type(self.until) not in (int, float) or not math.isfinite(self.until)
                or not 0 < self.until - time.time() <= 86400
                or type(self.reservation) is not int or not 1 <= self.reservation <= 20):
            raise ValueError('discovery_permit_invalid_or_expired')


class DiscoveryWorker:
    def __init__(self, repo, permit, *, enabled=lambda: False, transport=None):
        self.repo = repo
        self.permit = permit
        self.enabled = enabled
        self.transport = transport or bounded_http
        self.jobs = DiscoveryJobs(repo)

    def candidate(self, job):
        if os.environ.get('CHAOS_POI_ROUTING_ENABLED')=='1' and job.get('profile'):
            from .routing import Routing, reason
            chain=Routing(self.repo).get(job['profile'],'background')['chain']
            providers={p['id']:p for p in Registry(self.repo).list()}
            eligible=[p for p in chain if p in providers and not reason(providers[p],job['profile'],'background')]
            if not eligible or eligible[0]!=job['provider']:
                return None
        for item in Registry(self.repo).list():
            if (item['id'] == job['provider'] == 'maplark'
                    and item['revision'] == job['revision']
                    and item.get('enabled') and item.get('technical_status') == 'tested_ok'
                    and item.get('url') == 'https://api.maplark.com/v3/osm_features'
                    and item.get('operator_group') == 'api.maplark.com'
                    and Registry.approved(item, 'background_refresh')
                    and Registry.approved(item, 'storage') and reference(item)):
                return item
        return None

    def run_one(self):
        # Disabled execution does not even claim work or resolve credentials.
        if not self.enabled():
            return dict(status='disabled', network_calls=0)
        self.permit.validate()
        self.permit.validate_budgets(self.repo)
        if os.environ.get('CHAOS_POI_PRIORITY_ENABLED') != '1':
            return dict(status='priority_required', network_calls=0)
        job = self.jobs.claim(120, cells=self.permit.cells, profiles=self.permit.profiles)
        if job is None:
            return dict(status='idle', network_calls=0)
        key, owner = job['id'], job['owner']
        calls = 0
        publication_owner = None

        def active():
            if not self.enabled() or time.time() >= self.permit.until:
                return False
            current = self.jobs.get(key)
            if (not current or current['owner'] != owner
                    or current['state'] not in ('LEASED', 'FETCHING', 'VALIDATING')
                    or min(current['lease_until'], current['expires']) <= time.time()):
                return False
            conn = self.repo.connect()
            try:
                demand = conn.execute('SELECT * FROM world_discovery_demand WHERE key=? AND expires>?',
                                      (job['demand_key'], time.time())).fetchone()
            finally:
                conn.close()
            return bool(demand and (demand['cell_x'], demand['cell_y']) in self.permit.cells
                        and demand['layer'] == job['profile'] in self.permit.profiles
                        and self.candidate(job))

        def send(*args, **kwargs):
            nonlocal calls
            if not active() or not self.jobs.transition(key, owner, 'FETCHING', operation='discovery:' + key):
                raise POIError('discovery_fence_lost')
            calls += 1
            return self.transport(*args, **kwargs)

        try:
            if not active():
                self.jobs.transition(key, owner, 'POLICY_BLOCKED')
                return dict(status='policy_blocked', network_calls=0)
            conn = self.repo.connect()
            try:
                demand = conn.execute('SELECT cell_x,cell_y FROM world_discovery_demand WHERE key=?',
                                      (job['demand_key'],)).fetchone()
            finally:
                conn.close()
            plan = plan_maplark((demand['cell_y'] + .5) / 100,
                                (demand['cell_x'] + .5) / 100, 300,
                                profile=job['profile'], limit=1000)
            # The existing store enforces its global limits atomically at commit.
            # Reserve room for a maximum-size publication before spending credits.
            conn = self.repo.connect()
            try:
                count, size = conn.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone()
            finally:
                conn.close()
            world = CanonicalWorldRepository(self.repo)
            if count >= world.max_snapshots or size + 8 * 1024 * 1024 > world.max_bytes:
                raise POIError('world_capacity')
            publication_owner = self.repo.acquire(key, 120)
            if not publication_owner:
                raise POIError('publication_busy')
            batch, billing = acquire_maplark(self.repo, plan, 'discovery:' + key,
                self.permit.reservation,
                accept_variable_cost=os.environ.get('CHAOS_MAPLARK_ACCEPT_VARIABLE_COST') == '1',
                transport=send, still_active=active, lane='background',
                budget_scopes=self.permit.budget_scopes(job['profile']))
            if not active() or not self.jobs.transition(key, owner, 'VALIDATING'):
                raise POIError('discovery_fence_lost')
            candidate = self.candidate(job)
            now = time.time()
            snapshot = world.publish_batch(key, publication_owner, batch, provider='maplark',
                revision=job['revision'], storage_reference=reference(candidate),
                fresh_until=now + 300, usable_until=now + 1800)
            if not snapshot or not self.jobs.acknowledge(key, snapshot, owner):
                raise POIError('publication_ack_pending')
            return dict(status='committed', network_calls=calls, coverage='UNKNOWN',
                        snapshot=snapshot, billing=billing)
        except Exception as exc:
            current = self.jobs.get(key)
            if current and current['owner'] == owner:
                # Any possible HTTP is quarantined, never repeated automatically.
                target = 'DEFERRED' if current['state'] == 'LEASED' else 'POLICY_BLOCKED'
                self.jobs.transition(key, owner, target, delay=60 if target == 'DEFERRED' else 0)
            current = self.jobs.get(key)
            deferred = current and current['state'] in ('DEFERRED', 'RETRY_AFTER')
            return dict(status='deferred' if deferred else 'reconciliation_required',
                        network_calls=calls, error_type=type(exc).__name__)
        finally:
            if publication_owner:
                self.repo.release(key, publication_owner)
