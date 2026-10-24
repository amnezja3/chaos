"""Allowlisted PM2 metadata only; no secrets, mutations or worker-memory claims."""
import json
from pathlib import Path
import subprocess

FLAGS={'CHAOS_POI_INFRASTRUCTURE_ENABLED':'1','CHAOS_POI_MAPLARK_ENABLED':'1',
       'CHAOS_POI_WORLD_INGEST_ENABLED':'0','CHAOS_POI_WORLD_REPOSITORY_ENABLED':'0',
       'CHAOS_POI_DISCOVERY_MODE':'passive','CHAOS_POI_ROUTING_ENABLED':'0',
       'CHAOS_ADULT_POLICY_ENABLED':'0'}


def inspect(processes,expected_cwd):
    if not isinstance(processes,list):raise ValueError('pm2_list_required')
    selected=[]
    for item in processes:
        if item.get('name') not in ('chaos','chaos-world-discovery-worker'):continue
        env=item.get('pm2_env',{})
        values={}
        for key in FLAGS:
            value=env.get(key)
            allowed=('off','passive','bounded_prefetch') if key.endswith('_MODE') else ('0','1')
            values[key]=str(value) if str(value) in allowed else 'unknown'
        state=env.get('status')
        selected.append(dict(name=item['name'],status=state if state in ('online','stopped','errored','launching') else 'unknown',
            cwd_matches=str(Path(env.get('pm_cwd','')).resolve())==str(Path(expected_cwd).resolve()),flags=values))
    web=[p for p in selected if p['name']=='chaos']
    workers=[p for p in selected if p['name']=='chaos-world-discovery-worker']
    ready=(len(web)==1 and web[0]['status']=='online' and web[0]['cwd_matches']
           and web[0]['flags']==FLAGS and all(p['status']=='stopped' for p in workers))
    return dict(status='baseline_matches' if ready else 'review_required',ok=ready,
                processes=selected,network_calls=0,production_writes=0,
                scope='PM2 metadata only; not live worker environment or network tracing')


def main():
    try:
        response=subprocess.run(['pm2','jlist'],capture_output=True,text=True,timeout=15,check=True)
        result=inspect(json.loads(response.stdout),Path(__file__).resolve().parents[1])
        print(json.dumps(result));return 0 if result['ok'] else 2
    except Exception as exc:
        # Raw PM2 output/env and subprocess error strings may contain secrets.
        print(json.dumps(dict(ok=False,status='runtime_unavailable',error_type=type(exc).__name__)));return 1


if __name__=='__main__':raise SystemExit(main())
