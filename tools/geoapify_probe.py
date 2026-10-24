"""Explicit bounded VPS contract check. No gameplay activation or secret output."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    from poi_infrastructure.repository import Repository
    from poi_infrastructure.credit_budget import CreditBudget
    from poi_infrastructure.geoapify import inspect_places, PROFILES
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--provider',default='geoapify')
    parser.add_argument('--lat',type=float,default=52.2319)
    parser.add_argument('--lon',type=float,default=21.0067)
    parser.add_argument('--radius',type=float,default=300)
    parser.add_argument('--pages',type=int,choices=(1,2,3),default=1)
    parser.add_argument('--profile',choices=tuple(PROFILES),default='broad')
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare-budget',action='store_true')
    actions.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute and not args.prepare_budget:
        print(json.dumps(dict(status='plan',network_calls=0,max_network_calls=args.pages,
            reservation_per_page=5,deadline=35,secret_ref='CHAOS_GEOAPIFY_API_KEY',
            gameplay_changed=False,required_scope='small_probe',
            query=dict(profile=args.profile,categories=list(PROFILES[args.profile]),
                       latitude=args.lat,longitude=args.lon,radius=args.radius,limit=100,method='POST'))))
        return
    repo=Repository(args.db)
    try:
        if args.prepare_budget:
            from poi_infrastructure.providers import Registry
            from poi_infrastructure.routing import GEOAPIFY
            registry=Registry(repo);registry.initialize()
            candidate=next((p for p in registry.list() if p['id']==args.provider),None)
            if candidate is None:
                candidate=registry.save(args.provider,0,dict(name='Geoapify Places',url=GEOAPIFY,
                    operator_group='api.geoapify.com',priority=10),'operator:geoapify-prepare')
            elif candidate['url']!=GEOAPIFY:
                raise ValueError('provider_endpoint_mismatch')
            budget=CreditBudget(repo); budget.initialize()
            day=int(time.time()//86400)*86400
            # Repeated setup never resets the same UTC-day usage.
            budget.configure_window('geoapify','diagnostic:'+str(day),day,day+86400,20)
            result=dict(status='budget_prepared',network_calls=0,limit=20,ends=day+86400,
                        provider_enabled=candidate['enabled'],environment_changed=False,
                        approval_required='small_probe',provider_revision=candidate['revision'])
        else:
            result=inspect_places(repo,args.provider,args.lat,args.lon,args.radius,
                                  pages=args.pages,profile=args.profile)
        print(json.dumps(result))
    except Exception as exc:
        # Transport exceptions can include URLs/credentials. Only safe known codes.
        from poi_infrastructure.service import POIError
        from poi_infrastructure.world_contract import ContractError
        message=str(exc) if isinstance(exc,(POIError,ContractError)) else type(exc).__name__
        print(json.dumps(dict(ok=False,error=message)))
        sys.exit(1)


if __name__=='__main__':
    main()
