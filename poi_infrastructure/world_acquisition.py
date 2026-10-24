"""One budgeted MapLark acquisition using existing POI coordination/transport.

No automatic schema initialization, retries, gameplay export or cache writes.
Reservation is an internal allowance, NOT a provider-enforced price cap.
"""
import time
import os

from .credit_budget import CreditBudget
from .service import Config, POIError, UpstreamUnavailable, bounded_http, retry_delay
from .world_adapters import MAPLARK_VERSION, normalize_maplark
from .world_contract import ContractError, Provenance


def acquire_maplark(repo, plan, operation, reservation, *,
                    accept_variable_cost=False, transport=None, still_active=lambda: True,
                    lane='live'):
    """Caller must configure ledger windows and authorize this provider first.

Returns a normalized, UNAPPROVED batch plus nonsecret billing metadata.
Same operation ID can never cause a second upstream request.
"""
    if not accept_variable_cost:
        raise ContractError('variable_credit_cost_acceptance_required')
    if plan.adapter_version != MAPLARK_VERSION or plan.endpoint != 'https://api.maplark.com/v3/osm_features':
        raise ContractError('acquisition_provider_unsupported')
    plan.authenticated_wire()
    if not still_active():
        raise POIError('scanner_inactive')
    group = 'api.maplark.com'
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
    try:
        reserved = ledger.reserve('maplark', operation, reservation)
        if not reserved:
            raise ContractError('budget_operation_already_used')
        if not still_active() or not repo.owns('@upstream', slot):
            raise POIError('scanner_inactive_or_slot_lost')
        sent = True
        status, retry, envelope = (transport or bounded_http)(
            Config(deadline=35), plan.endpoint, plan, 30, started + 35,
            secure='world-features')
        headers = envelope.get('response_headers', {}) if isinstance(envelope, dict) else {}
        # Bill errors and malformed responses too. Never infer free requests
        # from HTTP status or a missing/invalid charge header.
        value = headers.get('X-Usage-Units-Charged') if isinstance(headers, dict) else None
        charged = int(value) if isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 12 else None
        ledger.settle('maplark', operation, charged)
        settled = True
        if status != 200:
            if status in (429, 500, 502, 503, 504):
                repo.outcome(group, False, retry_delay(retry) or (30 if status == 429 else 0))
            raise POIError('http_' + str(status))
        provenance = Provenance('maplark', MAPLARK_VERSION, operation, time.time(), license_ref='ODbL-1.0')
        batch = normalize_maplark(envelope.get('body'), headers, provenance,
                                  profile=plan.profile, maximum=int(dict(plan.params)['limit']))
        if batch.completeness != 'complete':
            raise ContractError('provider_response_incomplete')
        if time.monotonic() >= started + 35 or not repo.owns('@upstream', slot):
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
                ledger.settle('maplark', operation, None if sent else 0)
        finally:
            try:
                repo.release('@probe:' + group, slot)
            finally:
                repo.release('@upstream', slot)
