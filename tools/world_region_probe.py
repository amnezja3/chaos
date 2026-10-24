"""One explicit roads bbox capture; shares live budgets, never ingests or enables discovery."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError, bounded_http
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark_region
from poi_infrastructure.world_contract import ContractError
from tools.world_region_plan import evaluate

BOUNDS=(20.36,51.53,20.37,51.54)
OPERATION='region:roads-2036-5153-bbox-v1'
SCOPE='region-probe:roads-2036-5153-bbox-v1'
PARTS={'parent':BOUNDS,'left':(20.36,51.53,20.365,51.54),'right':(20.365,51.53,20.37,51.54)}


def capture(db,output=None,*,execute=False,approve=False,accept_variable_cost=False,transport=None,part='parent'):
    if part not in PARTS:raise ContractError('region_part_invalid')
    bounds=PARTS[part]
    operation=OPERATION if part=='parent' else 'region:roads-2036-5153-neighbor-v1:'+part
    scope_id=SCOPE if part=='parent' else 'region-probe:roads-2036-5153-neighbors-v1'
    scope_limit=20 if part=='parent' else 40
    plan=plan_maplark_region(bounds)
    result=dict(status='plan',profile='roads',part=part,params=dict(plan.params),operation=operation,
        network_calls=0,max_network_calls=1,reservation=20,deadline=35,
        shared_probe_limit=scope_limit,
        provider_price_cap=False,gameplay_changed=False,world_ingest=False,
        region_certified=False,registry_changed=False)
    if not execute:return result
    if not approve:raise ContractError('explicit_bbox_probe_approval_required')
    if not accept_variable_cost:raise ContractError('variable_credit_cost_acceptance_required')
    plan.authenticated_wire()
    if not Path(db).is_file():raise ContractError('existing_poi_database_required')
    if not output:raise ContractError('new_output_directory_required')
    repo=Repository(db);registry=Registry(repo)
    def provider():
        return next((p for p in registry.list() if p['id']=='maplark'),None)
    candidate=provider()
    if (not candidate or not candidate['enabled'] or candidate['url']!=plan.endpoint
            or not Registry.approved(candidate,'storage')):
        raise ContractError('approved_maplark_storage_required')
    revision=candidate['revision']
    def active():
        current=provider()
        return bool(current and current['revision']==revision and current['enabled']
                    and Registry.approved(current,'storage'))
    ledger=CreditBudget(repo)
    # Reuse the live account limits; do not create/reset a budget or policy.
    windows=ledger.status('maplark')
    if not windows or any(w['remaining']<20 for w in windows):
        raise ContractError('budget_exhausted_or_unconfigured')
    with closing(repo.connect()) as c:
        used=c.execute('SELECT 1 FROM world_credit_operation WHERE account=? AND operation=?',
                       ('maplark',operation)).fetchone()
    if used:raise ContractError('budget_operation_already_used')
    scope=ledger.scope_status('maplark',scope_id)
    if scope is None:
        now=time.time();ledger.configure_scope('maplark',scope_id,now,now+3600,scope_limit)
    elif scope['ends']<=time.time():
        raise ContractError('bbox_probe_window_expired_do_not_reset')
    # Exclusive private output; never overwrite a previous capture.
    destination=Path(output)
    destination.mkdir(mode=0o700,parents=False,exist_ok=False)
    captured={}
    def send(*args,**kwargs):
        status,retry,envelope=(transport or bounded_http)(*args,**kwargs)
        if status==200 and isinstance(envelope,dict):captured.update(envelope)
        return status,retry,envelope
    _,billing=acquire_maplark(repo,plan,operation,20,accept_variable_cost=True,
        transport=send,still_active=active,budget_scopes=(scope_id,),lane='background')
    # Persist only successful JSON and allowlisted response metadata, never request auth.
    allowed={'X-Returned','X-Has-More','X-Next-Cursor','X-Usage-Units-Charged'}
    headers={k:v for k,v in captured.get('response_headers',{}).items() if k in allowed}
    body=captured['body']
    inspection=evaluate(bounds,'roads',body,headers)
    result.update(status='captured_not_certified',network_calls=1,billing=billing,
                  approval='operator_cli_single_bbox_probe',provider_revision=revision,
                  inspection=inspection,output=str(destination))
    values={'body.json':body,'headers.json':headers,'report.json':result}
    encoded={name:json.dumps(value,ensure_ascii=False,allow_nan=False) for name,value in values.items()}
    if any(os.environ[plan.secret_ref] in raw for raw in encoded.values()):
        raise ContractError('sensitive_response_not_saved')
    for name,raw in encoded.items():
        with os.fdopen(os.open(destination/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf8') as f:
            f.write(raw)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--output')
    p.add_argument('--part',choices=tuple(PARTS),default='parent')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--approve-bbox-probe',action='store_true')
    p.add_argument('--accept-variable-credit-cost',action='store_true')
    a=p.parse_args()
    try:
        result=capture(a.db,a.output,execute=a.execute,approve=a.approve_bbox_probe,
                       accept_variable_cost=a.accept_variable_credit_cost,part=a.part)
    except Exception as exc:
        # Do not print arbitrary transport exceptions, URLs or credentials.
        result=dict(ok=False,error=str(exc) if isinstance(exc,(POIError,ContractError)) else type(exc).__name__,
                    part=a.part,retry_automatically=False)
        print(json.dumps(result));return 1
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
