"""Start only the bounded collector, reusing the web process's MapLark credential in memory."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.world_runtime_check import inspect
from poi_infrastructure.discovery_runtime import load_permit, cycle
from poi_infrastructure.repository import Repository
from poi_infrastructure.routing import Routing, reason
from poi_infrastructure.providers import Registry


def verify_credentials(processes, expected):
    worker=next((p for p in processes if p.get('name')=='chaos-world-discovery-worker'),None)
    env=worker.get('pm2_env',{}) if worker else {}
    if any(env.get(name)!=value for name,value in expected.items()):
        raise ValueError('worker_credentials_not_applied')


def start(*, runner=subprocess.run, regions=False, regular=False,prompt_secrets=False):
    root=Path(__file__).resolve().parents[1]
    result=runner(['pm2','jlist'],capture_output=True,text=True,check=True,timeout=15)
    processes=json.loads(result.stdout)
    if not inspect(processes,root,routing='1')['ok']:
        raise ValueError('web_routing_or_worker_baseline_mismatch')
    identity='collection-regions-v1' if regions else 'collection-daemon-2036-5153-v1'
    path=root/'data'/identity/'permit.json'
    permit=None
    if not regular:permit=load_permit(path)
    if not regular and (permit.budget_id!=identity
            or (not regions and permit.cells!=frozenset({(2036,5153)}))
            or permit.refresh_seconds!=(604800 if regions else 0)
            or permit.profiles!=frozenset({'roads','waterways','inland_water'})
            or permit.retention_seconds!=604800 or permit.reservation!=20
            or permit.acquisition!='sector-bbox-v1'):
        raise ValueError('bounded_permit_mismatch')
    # Planning resolves neither credentials nor requests; scopes/budgets are checked again at execution.
    repo=Repository(root/'data/poi_cache.sqlite3')
    if regular:
        from poi_infrastructure.regular_discovery import cycle as regular_cycle,load
        path=root/'data/world-collection-policy.json'
        policy=load(path)[0]
        if not policy['enabled']:raise ValueError('collection_policy_blocked')
        plan=regular_cycle(repo,path)
    else:plan=cycle(repo,path)
    if plan['status']!='plan':raise ValueError('collection_policy_blocked')
    providers={p['id']:p for p in Registry(repo).list()}
    for layer in (() if regular else permit.profiles):
        chain=Routing(repo).get(layer,'background')['chain']
        eligible=[pid for pid in chain if pid in providers and not reason(providers[pid],layer,'background')]
        if not eligible or eligible[0]!='maplark':raise ValueError('background_route_not_maplark')
    web=next(p for p in processes if p['name']=='chaos')
    key=web.get('pm2_env',{}).get('CHAOS_MAPLARK_API_KEY','')
    if not isinstance(key,str) or not key or len(key)>4096 or any(not 33<=ord(c)<=126 for c in key):
        raise ValueError('web_maplark_credential_unavailable')
    child_env=dict(os.environ,CHAOS_MAPLARK_API_KEY=key)
    if regular:
        secret='CHAOS_GEOAPIFY_API_KEY'
        value=web.get('pm2_env',{}).get(secret) or os.environ.get(secret,'')
        if not value and prompt_secrets:
            from getpass import getpass
            value=getpass('Klucz API Geoapify (nie jest zapisywany w repo): ')
        if not isinstance(value,str) or not value or len(value)>4096 or any(not 33<=ord(c)<=126 for c in value):
            raise ValueError('geoapify_credential_unavailable')
        child_env[secret]=value
    runner(['pm2','startOrReload','ecosystem.discovery.config.js','--only',
            'chaos-world-discovery-worker','--env','regular' if regular else 'regions' if regions else 'bounded','--update-env'],
           cwd=root,env=child_env,capture_output=True,text=True,check=True,timeout=60)
    if regular:
        applied=runner(['pm2','jlist'],capture_output=True,text=True,check=True,timeout=15)
        verify_credentials(json.loads(applied.stdout),
            {name:child_env[name] for name in ('CHAOS_MAPLARK_API_KEY','CHAOS_GEOAPIFY_API_KEY')})
    return dict(status='start_requested',network_calls=0,secret_copied='web_to_worker_environment',
                secret_printed=False,credentials_verified=regular,
                permit_until=policy['review_until'] if regular else permit.until,automatic_renewal=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--regions',action='store_true')
    modes.add_argument('--regular',action='store_true')
    parser.add_argument('--prompt-secrets',action='store_true')
    args=parser.parse_args()
    try:
        print(json.dumps(start(regions=args.regions,regular=args.regular,prompt_secrets=args.prompt_secrets)));return 0
    except Exception as exc:
        # Never print subprocess output, arguments containing env, or raw PM2 data.
        safe={'web_routing_or_worker_baseline_mismatch','bounded_permit_mismatch',
              'collection_policy_blocked','web_maplark_credential_unavailable','background_route_not_maplark','geoapify_credential_unavailable','worker_credentials_not_applied'}
        code=str(exc) if type(exc) is ValueError and str(exc) in safe else 'local_start_failed'
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,error=code,network_calls=0)))
        return 1


if __name__=='__main__':raise SystemExit(main())
