"""Bounded one-job executor; no daemon, automatic enqueue, or production wiring.

Execution requires an explicit short-lived region/profile permit and a live
enable callback. Observations do not certify reusable geographic coverage.
"""
from dataclasses import dataclass
import math
import os
import time

from .discovery_jobs import DiscoveryJobs, ADMISSION_DEFERRALS, ACQUISITIONS
from .credit_budget import CreditBudget, _token
from .providers import Registry
from .service import POIError, bounded_http
from .world_acquisition import acquire_features
from .world_adapters import plan_maplark, plan_maplark_region, plan_geoapify
from .world_storage import CanonicalWorldRepository
from .world_shadow import reference
from .world_contract import ContractError


class PermitExpired(ValueError):
    """A bounded process should stop normally rather than restart an expired permit."""


@dataclass(frozen=True)
class DiscoveryPermit:
    cells: frozenset
    profiles: frozenset
    until: float
    reservation: int = 20
    budget_id: str = ''
    acquisition: str = 'radius-300-v1'
    retention_seconds: int = 1800
    refresh_seconds: int = 0
    provider_id: str = ''

    @property
    def account(self):
        if self.provider_id:return self.provider_id
        return 'geoapify' if self.acquisition == 'geoapify-commercial-v1' else 'maplark'

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
                status = ledger.scope_status(self.account, scope)
                if not status or not status['starts'] <= now < self.until <= status['ends']:
                    raise ValueError('discovery_budget_missing_or_expired')

    def validate(self):
        if type(self.until) in (int,float) and math.isfinite(self.until) and self.until<=time.time():
            raise PermitExpired('discovery_permit_expired')
        if (not isinstance(self.cells, frozenset) or not 1 <= len(self.cells) <= 10
                or any(not isinstance(c, tuple) or len(c) != 2
                       or any(type(v) is not int for v in c)
                       or not -18000 <= c[0] < 18000 or not -9000 <= c[1] < 9000
                       for c in self.cells)
                or not isinstance(self.profiles, frozenset) or not self.profiles
                or not self.profiles <= ({'poi'} if self.account=='geoapify' else
                                        {'roads', 'waterways', 'inland_water', 'coastline'})
                or type(self.until) not in (int, float) or not math.isfinite(self.until)
                or not 0 < self.until - time.time() <= 86400
                or type(self.reservation) is not int or not 1 <= self.reservation <= 20
                or not isinstance(self.acquisition, str) or self.acquisition not in ACQUISITIONS
                or type(self.retention_seconds) is not int or not 1800 <= self.retention_seconds <= 31*86400):
            raise ValueError('discovery_permit_invalid_or_expired')
        if self.provider_id:
            _token(self.provider_id)
            if self.acquisition!='overpass-bbox-geom-v1':raise ValueError('discovery_provider_acquisition')
        if (type(self.refresh_seconds) is not int or self.refresh_seconds not in (0,604800)
                or self.refresh_seconds and self.retention_seconds!=604800):
            raise ValueError('discovery_refresh_requires_maplark_seven_day_archive')


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
            if job['provider'] not in eligible:
                return None
        for item in Registry(self.repo).list():
            account = self.permit.account
            if self.permit.acquisition=='overpass-bbox-geom-v1':
                from .routing import adapter,reason
                if (item['id']==job['provider']==account and item['revision']==job['revision']
                        and adapter(item)=='overpass' and not reason(item,job.get('profile','roads'),'background')
                        and item.get('review_due_at',0)>=time.time()+self.permit.retention_seconds):return item
                continue
            endpoint = ('https://api.geoapify.com/v2/places' if account=='geoapify'
                        else 'https://api.maplark.com/v3/osm_features')
            if (item['id'] == job['provider'] == account
                    and item['revision'] == job['revision']
                    and item.get('enabled') and item.get('technical_status') == 'tested_ok'
                    and item.get('url') == endpoint
                    and item.get('operator_group') == 'api.'+account+'.com'
                    and Registry.approved(item, 'background_refresh')
                    and (self.permit.retention_seconds == 1800 or
                         item.get('review_due_at',0) >= time.time()+self.permit.retention_seconds)
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
        job = self.jobs.claim(120, cells=self.permit.cells, profiles=self.permit.profiles,
                              acquisition=self.permit.acquisition, allow_refresh=bool(self.permit.refresh_seconds),provider=self.permit.account)
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
            if job['acquisition']=='overpass-bbox-geom-v1':
                plan=None
            elif job['acquisition'] == 'geoapify-commercial-v1':
                plan = plan_geoapify((demand['cell_y']+.5)/100, (demand['cell_x']+.5)/100,
                                    300, categories=('commercial',), limit=100)
            elif job['acquisition'] == 'sector-bbox-v1':
                x, y = demand['cell_x'], demand['cell_y']
                plan = plan_maplark_region((x / 100, y / 100, (x + 1) / 100, (y + 1) / 100),
                                           profile=job['profile'], limit=1000)
            else:
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
            if plan is None:
                from .overpass_world import acquire
                x,y=demand['cell_x'],demand['cell_y']
                batch,billing=acquire(self.repo,self.candidate(job),(x/100,y/100,(x+1)/100,(y+1)/100),
                    job['profile'],'discovery:'+key,self.permit.budget_scopes(job['profile']),transport=send,active=active)
            else:
                batch, billing = acquire_features(self.repo, plan, 'discovery:' + key,
                self.permit.reservation, account=self.permit.account,
                accept_variable_cost=(self.permit.account=='geoapify' or
                                      os.environ.get('CHAOS_MAPLARK_ACCEPT_VARIABLE_COST') == '1'),
                transport=send, still_active=active, lane='background',
                allow_partial_observations=job['acquisition']=='sector-bbox-v1',
                budget_scopes=self.permit.budget_scopes(job['profile']),
                conservative_geoapify=self.permit.account=='geoapify' and self.permit.reservation==6)
            if not active() or not self.jobs.transition(key, owner, 'VALIDATING'):
                raise POIError('discovery_fence_lost')
            candidate = self.candidate(job)
            now = time.time()
            snapshot = world.publish_batch(key, publication_owner, batch, provider=self.permit.account,
                revision=job['revision'], storage_reference=reference(candidate),
                fresh_until=now + 300, usable_until=now + 1800,
                retain_until=now+self.permit.retention_seconds if self.permit.retention_seconds>1800 else None,
                observation_context=dict(acquisition=job['acquisition'],
                    demand_bounds=(demand['cell_x']/100, demand['cell_y']/100,
                                   (demand['cell_x']+1)/100, (demand['cell_y']+1)/100),
                    request_params=dict(plan.params) if plan else dict(geometry='full',profile=job['profile'],limit='1001',
                        bbox=','.join(map(str,(demand['cell_x']/100,demand['cell_y']/100,(demand['cell_x']+1)/100,(demand['cell_y']+1)/100))))))
            if not snapshot or not self.jobs.acknowledge(key, snapshot, owner):
                raise POIError('publication_ack_pending')
            return dict(status='committed', network_calls=calls, coverage='UNKNOWN',
                        snapshot=snapshot, billing=billing, acquisition=job['acquisition'],
                        response_completeness=batch.completeness, reasons=batch.reasons)
        except Exception as exc:
            current = self.jobs.get(key)
            reason=str(exc) if isinstance(exc,(POIError,ContractError)) else None
            if (calls==0 and reason in ADMISSION_DEFERRALS
                    and self.jobs.defer_admission(key,owner,reason)):
                return dict(status='deferred',network_calls=0,reason=reason,
                            retry_after_seconds=60,error_type=type(exc).__name__)
            if current and current['owner'] == owner:
                # Any possible HTTP is quarantined, never repeated automatically.
                target = 'DEFERRED' if current['state'] == 'LEASED' else 'POLICY_BLOCKED'
                self.jobs.transition(key, owner, target, delay=60 if target == 'DEFERRED' else 0)
            current = self.jobs.get(key)
            if calls and job['acquisition']=='overpass-bbox-geom-v1':
                self.jobs.schedule_overpass_retry(key)
            deferred = current and current['state'] in ('DEFERRED', 'RETRY_AFTER')
            return dict(status='deferred' if deferred else 'reconciliation_required',
                        network_calls=calls, error_type=type(exc).__name__)
        finally:
            if publication_owner:
                self.repo.release(key, publication_owner)
