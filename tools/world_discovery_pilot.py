"""Prepare, probe or enable the bounded MapLark pilot. Dry-run by default."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.maplark_profile import ENDPOINT, PROFILE, export_maplark
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import ContractError


def operate(db, action, *, apply=False, budget=100, reservation=20, accept_variable_cost=False):
    if type(budget) is not int or type(reservation) is not int or not 1 <= reservation <= budget <= 30000:
        raise ContractError('pilot_budget_invalid')
    if action not in ('prepare','probe','enable','disable','status'):
        raise ContractError('pilot_action_invalid')
    result=dict(action=action,status='plan',profile=PROFILE,network_calls=0,
        budget=budget,reservation=reservation,window_hours=24,
        note='Internal reservation is not a provider price cap; environment remains unchanged')
    if not apply:
        return result
    if not Path(db).is_file():
        raise ContractError('existing_poi_database_required')
    repo=Repository(db); registry=Registry(repo); ledger=CreditBudget(repo)
    if action=='prepare':
        registry.initialize(); ledger.initialize()
        if any(v['id']=='maplark' for v in registry.list()):
            raise ContractError('pilot_already_prepared_no_budget_reset')
        now=time.time()
        ledger.configure_window('maplark','pilot-161',now,now+86400,budget)
        value=registry.save('maplark',0,dict(name='MapLark pilot',url=ENDPOINT,
            operator_group='api.maplark.com',priority=0),'operator:pilot-cli')
        value=registry.decision('maplark',value['revision'],'approved_for_defined_use',
            ['normal_scan','storage'],dict(source_url='https://maplark.com/terms-of-service',
            reference='Sprint 161 operator-controlled pilot',
            notes='24h pilot; exact response cache only, no world ingest or background fetching. '
                  'MapLark native selection and geometry bounds; no Overpass parity claim.'),
            now+86400,'operator:pilot-cli')
        return dict(result,status='prepared_disabled',enabled=value['enabled'])
    values=registry.list()
    value=next((v for v in values if v['id']=='maplark' and v['url']==ENDPOINT),None)
    if not value:
        raise ContractError('pilot_not_prepared')
    if action=='status':
        return dict(result,status='read_only',provider=value,budget_windows=ledger.status('maplark'))
    if action=='probe':
        if value['policy_status']!='approved_for_defined_use' or value['review_due_at']<=time.time():
            raise ContractError('pilot_decision_expired')
        plan=plan_maplark(52.2319,21.0067,300,limit=1000)
        batch,billing=acquire_maplark(repo,plan,uuid.uuid4().hex,reservation,
            accept_variable_cost=accept_variable_cost)
        raw=export_maplark(batch)
        # This records transport/profile test only. Game acceptance is separate.
        registry.tested('maplark',value['revision'],True,'operator:pilot-cli')
        return dict(result,status='profile_probe_pass',network_calls=1,
            objects=len(raw['elements']),billing=billing,live_scanner_pass=False)
    value=registry.enable('maplark',value['revision'],action=='enable','operator:pilot-cli')
    return dict(result,status=action,enabled=value['enabled'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','probe','enable','disable','status'))
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--budget',type=int,default=100)
    parser.add_argument('--reservation',type=int,default=20)
    parser.add_argument('--accept-variable-credit-cost',action='store_true')
    args=parser.parse_args()
    try:
        result=operate(args.db,args.action,apply=args.apply,budget=args.budget,
            reservation=args.reservation,accept_variable_cost=args.accept_variable_credit_cost)
        print(json.dumps(result,ensure_ascii=False)); return 0
    except (POIError,ContractError,OSError,ValueError) as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,(POIError,ContractError)) else 'pilot_failed')))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
