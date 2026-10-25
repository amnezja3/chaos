"""Explicit regular observation policy setup. No HTTP or gameplay route changes."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing,adapter,reason
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.regular_discovery import DEFAULTS,load,cycle,report


def prepare(repo,path,apply=False):
    path=Path(path)
    policy=load(path)[0] if path.exists() else dict(DEFAULTS,review_until=time.time()+30*86400)
    providers={p['id']:p for p in Registry(repo).list()}
    for pid in ('maplark','geoapify'):
        p=providers.get(pid)
        if not p or adapter(p)!=pid or p['technical_status']!='tested_ok':
            raise ValueError(pid+'_validated_provider_required')
    result=dict(status='plan',network_calls=0,policy=policy,
        accounts={'maplark':{'daily':800,'rolling_31_days':24000},'geoapify':{'daily':2700,'rolling_31_days':83700}},
        overpass_eligible=[p['id'] for p in providers.values() if adapter(p)=='overpass' and not reason(p,'roads','background')],
        overpass_skipped=[dict(id=p['id'],reason=reason(p,'roads','background')) for p in providers.values()
                          if adapter(p)=='overpass' and reason(p,'roads','background')],
        overpass_approvals_changed=False,live_routes_changed=False)
    if not apply:return result
    # Save approval duration once. Repeated setup does not renew the review or clear costs.
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf8') as f:json.dump(policy,f,indent=2)
    registry=Registry(repo);actor='operator:regular-collection'
    for pid in ('maplark','geoapify'):
        p=next(p for p in registry.list() if p['id']==pid)
        required={'storage','world_storage','background_refresh'}
        review=policy['review_until']+7*86400+60
        if not required<=set(p['scopes']) or p['review_due_at']<review:
            source='https://www.geoapify.com/places-api/' if pid=='geoapify' else 'https://maplark.com/terms-of-service'
            p=registry.decision(pid,p['revision'],'approved_for_defined_use',sorted(set(p['scopes'])|required),
                dict(source_url=source,reference='Operator instruction 2026-10-25: regular world collection',
                     notes='Observation archive only. 7-day retention. Existing API plan; no new gameplay approval.'),
                max(review,p['review_due_at']),actor)
        if not p['enabled']:
            registry.enable(pid,p['revision'],True,actor)
    ledger=CreditBudget(repo)
    ledger.configure_recurring('maplark',800,24000)
    ledger.configure_recurring('geoapify',2700,83700)
    routing=Routing(repo)
    for profile in ('roads','waterways','inland_water','coastline','poi'):
        current=routing.get(profile,'background')
        candidates=[p for p in registry.list() if not reason(p,profile,'background')]
        candidates.sort(key=lambda p:({'overpass':0,'maplark':1,'geoapify':2}[adapter(p)],p.get('priority',100),p['id']))
        groups=set();chain=[]
        for p in candidates:
            if p['operator_group'] in groups:continue
            groups.add(p['operator_group']);chain.append(p['id'])
            if adapter(p)=='overpass':ledger.configure_recurring(p['id'],120,3720)
            if len(chain)==3:break
        if chain!=current['chain']:routing.save(profile,'background',current['revision'],chain,actor)
    return dict(result,status='configured',runtime_plan=cycle(repo,path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--policy',default='data/world-collection-policy.json')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--status',action='store_true')
    args=parser.parse_args()
    try:
        if not Path(args.db).is_file() or Path(args.db).name=='game.sqlite3':raise ValueError('poi_database_required')
        repo=Repository(args.db)
        print(json.dumps(report(repo) if args.status else prepare(repo,args.policy,args.apply)))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,network_calls=0)))
        return 1


if __name__=='__main__':raise SystemExit(main())
