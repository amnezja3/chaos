"""One manual MapLark v3 reference capture. Dry-run by default; no gameplay activation.

--execute requires explicit acceptance of variable credit billing on a Free
account. This is NOT the budget-controlled gameplay adapter or a provider PASS.
No automatic retry, cursor, splitting, estimate or secondary provider request.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import Config, POIError, UpstreamUnavailable, bounded_http, retry_delay
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import ContractError
from tools.world_discovery_inspect import inspect


def capture(db, output=None, *, execute=False, accept_variable_credit_cost=False, transport=None):
    plan = plan_maplark(52.2319, 21.0067, 300, limit=1000)
    result = dict(status='plan', provider='maplark', endpoint=plan.endpoint,
                  params=dict(plan.params), deadline=35, max_network_calls=1, network_calls=0,
                  credit_cost='variable_not_hard_capped_by_client', account_plan_required='Free',
                  secret_ref=plan.secret_ref, gameplay_changed=False, world_ingest=False,
                  artifact='new private diagnostic directory; no request headers saved')
    if not execute:
        return result
    if not accept_variable_credit_cost:
        raise ContractError('variable_credit_cost_acceptance_required')
    plan.authenticated_wire()  # fail before DB mutation/network if the key is missing
    if not Path(db).is_file():
        raise ContractError('existing_poi_database_required')
    if output is None:
        raise ContractError('new_output_directory_required')
    destination = Path(output)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    repo = Repository(db)
    group = 'api.maplark.com'
    if not repo.allowed(group):
        raise POIError('circuit_open')
    if not repo.acquire('@controlled-scan-rate:' + group, 900):
        raise POIError('controlled_scan_rate_limited')
    slot = repo.acquire('@upstream', 42, probe_group=group)
    if not slot:
        raise POIError('upstream_busy')
    started = time.monotonic()
    try:
        result['network_calls'] = 1
        status, retry, envelope = (transport or bounded_http)(
            Config(deadline=35), plan.endpoint, plan, 30, started+35, secure='world-features')
        result.update(status='http_error', http_status=status)
        headers = envelope['response_headers']
        result['reported_credits'] = headers.get('X-Usage-Units-Charged', 'unknown')
        # Preserve only whitelisted response metadata; no provider error body.
        body = envelope['body']
        if status == 200:
            try:
                result['inspection'] = inspect('maplark', body, headers)
                result['status'] = 'captured_not_approved'
            except ContractError as exc:
                result.update(status='captured_contract_error', contract_error=str(exc))
        if status in (429, 500, 502, 503, 504):
            repo.outcome(group, False, retry_delay(retry) or (30 if status == 429 else 0))
        # Do not mark technical approval or reset a gameplay health assessment.
        for name, value in (('body.json', body), ('headers.json', headers)):
            if value is None:
                continue
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
            if os.environ[plan.secret_ref] in raw:
                raise ContractError('sensitive_response_not_saved')
            with os.fdopen(os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as f:
                f.write(raw)
        return dict(result, seconds=round(time.monotonic()-started, 3))
    except UpstreamUnavailable:
        repo.outcome(group, False)
        raise
    finally:
        try:
            repo.release('@probe:' + group, slot)
        finally:
            repo.release('@upstream', slot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT / 'data/poi_cache.sqlite3'))
    parser.add_argument('--output', help='New private directory for body and response metadata')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--accept-variable-credit-cost', action='store_true',
                        help='Operator approval for one variable-cost call on confirmed Free account')
    args = parser.parse_args()
    try:
        result = capture(args.db, args.output, execute=args.execute,
                         accept_variable_credit_cost=args.accept_variable_credit_cost)
    except (POIError, ContractError, OSError, ValueError) as exc:
        result = {'ok': False, 'error': str(exc) if isinstance(exc, (POIError, ContractError)) else 'diagnostic_failed',
                  'gameplay_changed': False}
        print(json.dumps(result)); return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] in ('plan', 'captured_not_approved') else 1


if __name__ == '__main__':
    raise SystemExit(main())
