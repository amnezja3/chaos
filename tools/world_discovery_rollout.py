"""Promote the tested MapLark provider to recurring budgets. Dry-run by default."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.maplark_profile import ENDPOINT, PROFILE
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError
from poi_infrastructure.world_contract import ContractError

REFERENCE = 'Sprint 161 MapLark production rollout'


def operate(db, action, *, apply=False, daily=800, rolling=24000):
    if action not in ('promote','status','disable'):
        raise ContractError('rollout_action_invalid')
    if type(daily) is not int or type(rolling) is not int or not 1 <= daily <= rolling <= 30000:
        raise ContractError('budget_policy_invalid')
    result = dict(status='plan', action=action, profile=PROFILE, network_calls=0,
                  daily_limit=daily, rolling_31_day_limit=rolling,
                  environment_changed=False, provider_price_cap=False)
    if not apply:
        return result
    if not Path(db).is_file():
        raise ContractError('existing_poi_database_required')
    repo=Repository(db); registry=Registry(repo); ledger=CreditBudget(repo)
    value=next((v for v in registry.list() if v['id']=='maplark' and v['url']==ENDPOINT),None)
    if not value:
        raise ContractError('tested_maplark_provider_required')
    if action=='promote':
        if value['technical_status']!='tested_ok':
            raise ContractError('tested_maplark_provider_required')
        ledger.initialize()
        c=repo.connect()
        try:
            if c.execute('SELECT 1 FROM world_credit_hold WHERE account=?',('maplark',)).fetchone():
                raise ContractError('budget_account_held')
        finally:
            c.close()
        # Keep history; this supersedes the pilot window for future reservations.
        # Idempotent reapplication does not reset counts or invalidate cache.
        needs_decision = (value['policy_status']!='approved_for_defined_use'
            or not {'normal_scan','storage'} <= set(value['scopes'])
            or (value.get('evidence') or {}).get('reference') != REFERENCE
            or value['review_due_at'] <= time.time())
        if needs_decision:
            value=registry.decision(value['id'],value['revision'],'approved_for_defined_use',
                ['normal_scan','storage'],dict(source_url='https://maplark.com/terms-of-service',
                reference=REFERENCE,notes='Operator-authorized scanner rollout. Exact cache only; '
                'no world ingest or background requests. Native MapLark radius/bounds profile. '
                'Recurring internal budget is separate from provider balance and variable billing.'),
                time.time()+365*86400,'operator:rollout-cli')
        ledger.configure_recurring('maplark',daily,rolling)
        if not value['enabled']:
            value=registry.enable(value['id'],value['revision'],True,'operator:rollout-cli')
    elif action=='disable' and value['enabled']:
        value=registry.enable(value['id'],value['revision'],False,'operator:rollout-cli')
    c=repo.connect()
    try:
        hold=c.execute('SELECT reason FROM world_credit_hold WHERE account=?',('maplark',)).fetchone()
        unsettled=c.execute("SELECT COUNT(*) FROM world_credit_operation WHERE account=? AND state!='settled'",('maplark',)).fetchone()[0]
    finally:
        c.close()
    return dict(result,status='configured' if action=='promote' else action,
        provider_enabled=value['enabled'],revision=value['revision'],review_due_at=value['review_due_at'],
        budget_windows=ledger.status('maplark'),account_hold=hold[0] if hold else None,
        unresolved_operations=unsettled)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('promote','status','disable'))
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--daily',type=int,default=800)
    parser.add_argument('--rolling',type=int,default=24000)
    args=parser.parse_args()
    try:
        print(json.dumps(operate(args.db,args.action,apply=args.apply,daily=args.daily,rolling=args.rolling)))
        return 0
    except (POIError,ContractError,OSError,ValueError) as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,(POIError,ContractError)) else 'rollout_failed')))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
