"""Start only the bounded collector, reusing the web process's MapLark credential in memory."""
import json
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


def start(*, runner=subprocess.run):
    root=Path(__file__).resolve().parents[1]
    result=runner(['pm2','jlist'],capture_output=True,text=True,check=True,timeout=15)
    processes=json.loads(result.stdout)
    if not inspect(processes,root,routing='1')['ok']:
        raise ValueError('web_routing_or_worker_baseline_mismatch')
    path=root/'data/collection-daemon-2036-5153-v1/permit.json'
    permit=load_permit(path)
    if (permit.budget_id!='collection-daemon-2036-5153-v1'
            or permit.cells!=frozenset({(2036,5153)})
            or permit.profiles!=frozenset({'roads','waterways','inland_water'})
            or permit.retention_seconds!=604800 or permit.reservation!=20
            or permit.acquisition!='sector-bbox-v1'):
        raise ValueError('bounded_permit_mismatch')
    # Planning resolves neither credentials nor requests; scopes/budgets are checked again at execution.
    repo=Repository(root/'data/poi_cache.sqlite3')
    plan=cycle(repo,path)
    if plan['status']!='plan':raise ValueError('collection_policy_blocked')
    providers={p['id']:p for p in Registry(repo).list()}
    for layer in permit.profiles:
        chain=Routing(repo).get(layer,'background')['chain']
        eligible=[pid for pid in chain if pid in providers and not reason(providers[pid],layer,'background')]
        if not eligible or eligible[0]!='maplark':raise ValueError('background_route_not_maplark')
    web=next(p for p in processes if p['name']=='chaos')
    key=web.get('pm2_env',{}).get('CHAOS_MAPLARK_API_KEY','')
    if not isinstance(key,str) or not key or len(key)>4096 or any(not 33<=ord(c)<=126 for c in key):
        raise ValueError('web_maplark_credential_unavailable')
    child_env=dict(os.environ,CHAOS_MAPLARK_API_KEY=key)
    runner(['pm2','startOrReload','ecosystem.discovery.config.js','--only',
            'chaos-world-discovery-worker','--env','bounded','--update-env'],
           cwd=root,env=child_env,capture_output=True,text=True,check=True,timeout=60)
    return dict(status='start_requested',network_calls=0,secret_copied='web_to_worker_environment',
                secret_printed=False,permit_until=permit.until,automatic_renewal=False)


def main():
    try:
        print(json.dumps(start()));return 0
    except Exception as exc:
        # Never print subprocess output, arguments containing env, or raw PM2 data.
        safe={'web_routing_or_worker_baseline_mismatch','bounded_permit_mismatch',
              'collection_policy_blocked','web_maplark_credential_unavailable','background_route_not_maplark'}
        code=str(exc) if type(exc) is ValueError and str(exc) in safe else 'local_start_failed'
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,error=code,network_calls=0)))
        return 1


if __name__=='__main__':raise SystemExit(main())
