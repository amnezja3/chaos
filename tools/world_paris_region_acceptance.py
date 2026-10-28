"""One paid MapLark bbox, existing world store, offline candidate positions."""
import argparse
from contextlib import closing
import json
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
from poi_infrastructure.maplark_region import select
from tools.world_region_pilot import backup_database

BOUNDS=(2.333,48.856,2.343,48.866)
OPERATION='region:paris-poi-1635-acceptance-v1'


def run(db,backup=None,*,execute=False,accept=False,transport=None):
    plan=plan_maplark_region(BOUNDS,profile='poi',limit=1000)
    result=dict(status='plan',bounds=BOUNDS,network_calls=0,max_network_calls=1,
                reservation=20,provider_price_cap=False,registry_changed=False,
                environment_changed=False)
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
                     ('maplark',OPERATION)).fetchone():raise ContractError('operation_already_used_no_retry')
        count,size=c.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone()
    world=CanonicalWorldRepository(repo)
    if count>=world.max_snapshots or size+8*1024*1024>world.max_bytes:
        raise ContractError('world_capacity_before_request')
    backup_database(db,backup)
    if ledger.scope_status('maplark',OPERATION) is None:
        now=time.time();ledger.configure_scope('maplark',OPERATION,now,now+3600,20)
    owner=repo.acquire(OPERATION,120)
    if not owner:raise ContractError('region_busy')
    try:
        batch,billing=acquire_maplark(repo,plan,OPERATION,20,accept_variable_cost=True,
            transport=transport,still_active=active,lane='background',budget_scopes=(OPERATION,),
            allow_partial_observations=True)
        if not active():raise ContractError('provider_changed')
        # Inspect an incomplete reply but never publish it as regional coverage.
        # The transport already settled billing; preserve its diagnostic result.
        if batch.completeness!='complete' or batch.reasons:
            return dict(result,status='response_incomplete',network_calls=1,billing=billing,
                        completeness=batch.completeness,reasons=batch.reasons,
                        objects=len(batch.objects),world_published=False,
                        acceptance_ready=False,automatic_retry=False)
        now=time.time()
        snapshot=world.publish_batch(OPERATION,owner,batch,
            provider='maplark',revision=p['revision'],storage_reference=p['evidence']['reference'],
            fresh_until=now+300,usable_until=now+1800,
            observation_context=dict(acquisition='sector-bbox-v1',demand_bounds=BOUNDS,
                                     request_params=dict(plan.params)))
        if not snapshot:raise ContractError('publication_lease_lost')
        positions=[]
        for dy in (0,-.0002,.0002,-.0004,.0004):
            for dx in (0,-.0002,.0002,-.0004,.0004):
                lat,lon=round(48.861+dy,7),round(2.338+dx,7)
                try:data=select(batch,BOUNDS,lat,lon,300)
                except ContractError:continue
                positions.append(dict(lat=lat,lon=lon,radius=300,objects=len(data['elements'])))
                if len(positions)==2:break
            if len(positions)==2:break
        return dict(result,status='published',network_calls=1,snapshot=snapshot,billing=billing,
                    fresh_until=now+300,positions=positions,
                    acceptance_ready=len(positions)==2,automatic_retry=False)
    finally:repo.release(OPERATION,owner)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--backup');parser.add_argument('--execute',action='store_true')
    parser.add_argument('--accept-variable-credit-cost',action='store_true')
    args=parser.parse_args()
    try:
        result=run(args.db,args.backup,execute=args.execute,accept=args.accept_variable_credit_cost)
        print(json.dumps(result));return 2 if result['status']=='response_incomplete' else 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error=str(exc) if isinstance(exc,ContractError)
                              else type(exc).__name__,automatic_retry=False)));return 1


if __name__=='__main__':raise SystemExit(main())
