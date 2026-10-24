"""One budgeted MapLark acquisition using existing POI coordination/transport.

No automatic schema initialization, retries, gameplay export or cache writes.
Reservation is an internal allowance, NOT a provider-enforced price cap.
"""
import time
import os

from .credit_budget import CreditBudget
from .service import Config, POIError, UpstreamUnavailable, bounded_http, retry_delay
from .world_adapters import MAPLARK_VERSION, GEOAPIFY_VERSION, normalize_maplark, normalize_geoapify
from .world_contract import ContractError, Provenance


def acquire_maplark(repo, plan, operation, reservation, *,
                    accept_variable_cost=False, transport=None, still_active=lambda: True,
                    lane='live', budget_scopes=(), deadline=None):
    """Caller must configure ledger windows and authorize this provider first.

Returns a normalized, UNAPPROVED batch plus nonsecret billing metadata.
Same operation ID can never cause a second upstream request.
"""
    return acquire_features(repo, plan, operation, reservation, accept_variable_cost=accept_variable_cost,
        transport=transport, still_active=still_active, lane=lane, budget_scopes=budget_scopes,
        deadline=deadline, account='maplark')


def acquire_features(repo, plan, operation, reservation, *, account,
                     accept_variable_cost=False, transport=None, still_active=lambda:True,
                     lane='live', budget_scopes=(), deadline=None):
    if not accept_variable_cost:
        raise ContractError('variable_credit_cost_acceptance_required')
    expected = {'maplark': (MAPLARK_VERSION,'https://api.maplark.com/v3/osm_features'),
                'geoapify': (GEOAPIFY_VERSION,'https://api.geoapify.com/v2/places')}
    if account not in expected or (plan.adapter_version,plan.endpoint)!=expected[account]:
        raise ContractError('acquisition_provider_unsupported')
    plan.authenticated_wire()
    if not still_active():
        raise POIError('scanner_inactive')
    group = 'api.'+account+'.com'
    if not repo.allowed(group):
        raise POIError('circuit_open')
    if lane not in ('live','background'):
        raise ContractError('acquisition_lane')
    priority=os.environ.get('CHAOS_POI_PRIORITY_ENABLED')=='1'
    if lane=='background':
        # No production background caller is wired yet. This is an admission
        # primitive, never a replacement for provider/background scope checks.
        if not priority:raise ContractError('background_priority_required')
    if priority:
        from .upstream_priority import UpstreamPriority
        gate=UpstreamPriority(repo)
        ticket=gate.register() if lane=='live' else None
        slot=None
        try:
            until=time.monotonic()+2
            while still_active():
                if lane=='live' and ticket is None:break
                slot=gate.acquire(lane=lane,ticket=ticket,group=group)
                if slot or lane=='background' or time.monotonic()>=until:break
                time.sleep(.05)
        finally:
            gate.cancel(ticket)
    else:
        slot = repo.acquire('@upstream', 42, probe_group=group)
    if not slot:
        raise POIError('upstream_busy')
    ledger = CreditBudget(repo)
    reserved = sent = settled = False
    started = time.monotonic()
    deadline = min(started + 35, deadline) if deadline is not None else started + 35
    try:
        if deadline <= time.monotonic():
            raise POIError('deadline')
        reserved = ledger.reserve(account, operation, reservation, scopes=budget_scopes)
        if not reserved:
            raise ContractError('budget_operation_already_used')
        if not still_active() or not repo.owns('@upstream', slot):
            raise POIError('scanner_inactive_or_slot_lost')
        sent = True
        from .scan_metrics import transport_attempt
        transport_attempt()
        status, retry, envelope = (transport or bounded_http)(
            Config(deadline=35), plan.endpoint, plan, min(30, deadline-time.monotonic()), deadline,
            secure='world-features')
        headers = envelope.get('response_headers', {}) if isinstance(envelope, dict) else {}
        # Bill errors and malformed responses too. Never infer free requests
        # from HTTP status or a missing/invalid charge header.
        value = headers.get('X-Usage-Units-Charged') if account=='maplark' and isinstance(headers, dict) else None
        charged = int(value) if isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 12 else None
        ledger.settle(account, operation, charged)
        settled = True
        if status != 200:
            if status in (429, 500, 502, 503, 504):
                repo.outcome(group, False, retry_delay(retry) or (30 if status == 429 else 0))
            raise POIError('http_' + str(status))
        provenance = Provenance(account, plan.adapter_version, operation, time.time(), license_ref='ODbL-1.0')
        if account=='maplark':
            batch = normalize_maplark(envelope.get('body'), headers, provenance,
                                      profile=plan.profile, maximum=int(dict(plan.params)['limit']))
            if 'bbox' in dict(plan.params):
                from dataclasses import replace
                batch=replace(batch,selection='maplark-bbox-unverified')
        else:
            batch = normalize_geoapify(envelope.get('body'), provenance,
                                       page_limit=int(dict(plan.params)['limit']))
        if account=='maplark' and batch.completeness != 'complete':
            raise ContractError('provider_response_incomplete')
        if time.monotonic() >= deadline or not repo.owns('@upstream', slot):
            raise POIError('deadline_or_slot_lost')
        if not still_active():
            raise POIError('scanner_inactive')
        repo.outcome(group, True)
        return batch, dict(operation=operation, reported_credits=charged,
            reserved_credits=reservation, billing_state='settled' if charged is not None else 'uncertain',
            network_calls=1, gameplay_approved=False)
    except UpstreamUnavailable:
        repo.outcome(group, False)
        raise
    finally:
        try:
            if reserved and not settled:
                ledger.settle(account, operation, None if sent else 0)
        finally:
            try:
                repo.release('@probe:' + group, slot)
            finally:
                repo.release('@upstream', slot)
