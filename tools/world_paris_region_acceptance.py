"""One paid MapLark bbox, existing world store, offline candidate positions."""
import argparse
from contextlib import closing
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark_region
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.maplark_region import select, PROFILE
from poi_infrastructure.service import bounded_http
from tools.world_region_pilot import backup_database

BOUNDS=(2.333,48.856,2.343,48.866)
OPERATION='region:paris-poi-1635-acceptance-v1'
DIAGNOSTIC_OPERATION='region:paris-poi-1635-diagnostic-v2'
COMPACT_BOUNDS=(2.3335,48.858,2.3425,48.864)
COMPACT_OPERATION='region:paris-poi-1635-compact-v3'


def candidate_positions(batch,bounds):
    positions=[]
    rejected=Counter()
    for dy in (0,-.0002,.0002,-.0004,.0004):
        for dx in (0,-.0002,.0002,-.0004,.0004):
            lat,lon=round(48.861+dy,7),round(2.338+dx,7)
            try:data=select(batch,bounds,lat,lon,300)
            except ContractError as exc:
                rejected[str(exc)]+=1
                continue
            positions.append(dict(lat=lat,lon=lon,radius=300,objects=len(data['elements'])))
            if len(positions)==2:return positions,dict(rejected)
    return positions,dict(rejected)


def run(db,backup=None,*,execute=False,accept=False,transport=None,diagnostic_v2=False,compact_v3=False):
    if diagnostic_v2 and compact_v3:raise ContractError('acceptance_mode_conflict')
    operation=COMPACT_OPERATION if compact_v3 else DIAGNOSTIC_OPERATION if diagnostic_v2 else OPERATION
    bounds=COMPACT_BOUNDS if compact_v3 else BOUNDS
    plan=plan_maplark_region(bounds,profile='poi',limit=1000)
    result=dict(status='plan',bounds=bounds,network_calls=0,max_network_calls=1,
                reservation=20,provider_price_cap=False,registry_changed=False,
                environment_changed=False,operation=operation,selection_profile=PROFILE)
    if not execute:return result
    if not accept:raise ContractError('variable_cost_acceptance_required')
    plan.authenticated_wire()
    if not backup or not Path(db).is_file():raise ContractError('existing_database_and_new_backup_required')
    repo=Repository(db)
    def provider():
        return next((p for p in Registry(repo).list() if p['id']=='maplark'),None)
    p=provider()
    if (not p or not p['enabled'] or p['url']!=plan.endpoint or p['technical_status']!='tested_ok'
            or not all(Registry.approved(p,s) for s in ('normal_scan','storage','world_storage','background_refresh'))):
        raise ContractError('maplark_approval_required')
    def active():
        current=provider()
        return bool(current and current==p)
    ledger=CreditBudget(repo)
    windows=ledger.status('maplark')
    if not windows or any(w['remaining']<20 for w in windows):raise ContractError('budget_exhausted')
    with closing(repo.connect()) as c:
        if c.execute('SELECT 1 FROM world_credit_operation WHERE account=? AND operation=?',
                     ('maplark',operation)).fetchone():raise ContractError('operation_already_used_no_retry')
        count,size=c.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone()
    world=CanonicalWorldRepository(repo)
    if count>=world.max_snapshots or size+8*1024*1024>world.max_bytes:
        raise ContractError('world_capacity_before_request')
    backup_database(db,backup)
    destination=Path(str(backup)+'.diagnostics') if diagnostic_v2 or compact_v3 else None
    if destination:destination.mkdir(mode=0o700,exist_ok=False)
    def save(name,value):
        if destination is None:return
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False)
        secret=os.environ.get(plan.secret_ref,'')
        if secret:raw=raw.replace(secret,'[REDACTED]')
        if len(raw.encode('utf8'))>8*1024*1024:
            raw=json.dumps(dict(status='artifact_too_large'))
        with os.fdopen(os.open(destination/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf8') as f:
            f.write(raw)
    if destination:
        result['diagnostics']=str(destination)
        save('request.json',dict(params=dict(plan.params),provider_revision=p['revision'],operation=operation))
    def send(*args,**kwargs):
        status,retry,envelope=(transport or bounded_http)(*args,**kwargs)
        # Save BEFORE normalization can reject the reply. No request headers.
        save('http.json',dict(status=status))
        if isinstance(envelope,dict):
            headers=envelope.get('response_headers',{})
            allowed={'x-returned','x-has-more','x-next-cursor','x-usage-units-charged','content-type'}
            save('headers.json',{k:v for k,v in headers.items() if k.lower() in allowed} if isinstance(headers,dict) else {})
            save('body.json',envelope.get('body'))
        return status,retry,envelope
    def finish(report):
        save('report.json',report)
        return report
    if ledger.scope_status('maplark',operation) is None:
        now=time.time();ledger.configure_scope('maplark',operation,now,now+3600,20)
    owner=repo.acquire(operation,120)
    if not owner:raise ContractError('region_busy')
    try:
        batch,billing=acquire_maplark(repo,plan,operation,20,accept_variable_cost=True,
            transport=send,still_active=active,lane='background',budget_scopes=(operation,),
            allow_partial_observations=True)
        if not active():raise ContractError('provider_changed')
        # Inspect an incomplete reply but never publish it as regional coverage.
        # The transport already settled billing; preserve its diagnostic result.
        if batch.completeness!='complete' or batch.reasons:
            return finish(dict(result,status='response_incomplete',network_calls=1,billing=billing,
                        completeness=batch.completeness,reasons=batch.reasons,
                        objects=len(batch.objects),world_published=False,
                        acceptance_ready=False,automatic_retry=False))
        now=time.time()
        snapshot=world.publish_batch(operation,owner,batch,
            provider='maplark',revision=p['revision'],storage_reference=p['evidence']['reference'],
            fresh_until=now+300,usable_until=now+1800,
            observation_context=dict(acquisition='sector-bbox-v1',demand_bounds=bounds,
                                     request_params=dict(plan.params)))
        if not snapshot:raise ContractError('publication_lease_lost')
        positions,rejections=candidate_positions(batch,bounds)
        return finish(dict(result,status='published',network_calls=1,snapshot=snapshot,billing=billing,
                    fresh_until=now+300,positions=positions,position_rejections=rejections,
                    acceptance_ready=len(positions)==2,automatic_retry=False))
    except Exception as exc:
        save('failure.json',dict(error_type=type(exc).__name__,automatic_retry=False))
        raise
    finally:repo.release(operation,owner)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--backup');parser.add_argument('--execute',action='store_true')
    parser.add_argument('--accept-variable-credit-cost',action='store_true')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--diagnostic-v2',action='store_true',help='Separately approved single request; preserve response artifacts')
    mode.add_argument('--compact-v3',action='store_true',help='Approved smaller Paris bbox; one request with diagnostics')
    args=parser.parse_args()
    try:
        result=run(args.db,args.backup,execute=args.execute,accept=args.accept_variable_credit_cost,
                   diagnostic_v2=args.diagnostic_v2,compact_v3=args.compact_v3)
        print(json.dumps(result));return 2 if result['status']=='response_incomplete' else 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error=str(exc) if isinstance(exc,ContractError)
                              else type(exc).__name__,automatic_retry=False)));return 1


if __name__=='__main__':raise SystemExit(main())
