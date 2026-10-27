"""Allowlisted PM2 metadata only; no secrets, mutations or worker-memory claims."""
import json
import argparse
from pathlib import Path
import subprocess

FLAGS={'CHAOS_POI_INFRASTRUCTURE_ENABLED':'1','CHAOS_POI_MAPLARK_ENABLED':'1',
       'CHAOS_POI_WORLD_INGEST_ENABLED':'0','CHAOS_POI_WORLD_REPOSITORY_ENABLED':'0',
       'CHAOS_POI_DISCOVERY_MODE':'passive','CHAOS_POI_ROUTING_ENABLED':'0',
       'CHAOS_ADULT_POLICY_ENABLED':'0'}


def inspect(processes,expected_cwd, *, routing='0',worker='stopped',world_stage=None,halo=None):
    if routing not in ('0','1'):raise ValueError('runtime_routing_expectation')
    if worker not in ('stopped','online'):raise ValueError('runtime_worker_expectation')
    if halo not in (None,'0','1'):raise ValueError('runtime_halo_expectation')
    expected=dict(FLAGS, CHAOS_POI_ROUTING_ENABLED=routing)
    if world_stage is not None:
        if world_stage not in ('ingest','read','visits','regional','rollback'):raise ValueError('runtime_world_stage')
        expected.update(CHAOS_POI_WORLD_ACCESS_MODE='pilot' if world_stage=='rollback' else 'global',
            CHAOS_POI_WORLD_INGEST_ENABLED='0' if world_stage=='rollback' else '1',
            CHAOS_POI_WORLD_REPOSITORY_ENABLED='1' if world_stage in ('read','visits','regional') else '0',
            CHAOS_POI_WORLD_VISITS_ENABLED='1' if world_stage in ('visits','regional') else '0',
            CHAOS_POI_WORLD_REGIONAL_READ_ENABLED='1' if world_stage=='regional' else '0',
            CHAOS_POI_WIDE_FETCH_ENABLED='1' if world_stage=='regional' else '0',
            CHAOS_POI_SCAN_NETWORK_PAUSED='0')
    if not isinstance(processes,list):raise ValueError('pm2_list_required')
    selected=[]
    for item in processes:
        if item.get('name') not in ('chaos','chaos-world-discovery-worker'):continue
        env=item.get('pm2_env',{})
        values={}
        for key in expected:
            value=env.get(key)
            allowed=(('off','pilot','global') if key=='CHAOS_POI_WORLD_ACCESS_MODE' else
                     ('off','passive','bounded_prefetch') if key.endswith('_MODE') else ('0','1'))
            values[key]=str(value) if str(value) in allowed else 'unknown'
        state=env.get('status')
        selected.append(dict(name=item['name'],status=state if state in ('online','stopped','errored','launching') else 'unknown',
            cwd_matches=str(Path(env.get('pm_cwd','')).resolve())==str(Path(expected_cwd).resolve()),flags=values))
        if item['name']=='chaos-world-discovery-worker':
            halo_value=str(env.get('CHAOS_POI_WORLD_HALO_ENABLED'))
            selected[-1]['halo']=halo_value if halo_value in ('0','1') else 'unknown'
            selected[-1]['controls']={key:str(env.get(key)) if str(env.get(key)) in ('0','1') else 'unknown'
                for key in ('CHAOS_POI_DISCOVERY_WORKER_ENABLED','CHAOS_POI_PRIORITY_ENABLED')}
    web=[p for p in selected if p['name']=='chaos']
    workers=[p for p in selected if p['name']=='chaos-world-discovery-worker']
    worker_ready=(all(p['status']=='stopped' for p in workers) if worker=='stopped' else
        len(workers)==1 and workers[0]['status']=='online' and workers[0]['cwd_matches']
        and workers[0]['flags']['CHAOS_POI_ROUTING_ENABLED']=='1'
        and all(v=='1' for v in workers[0]['controls'].values()))
    if halo is not None:
        worker_ready=worker_ready and len(workers)==1 and workers[0]['halo']==halo
    ready=(len(web)==1 and web[0]['status']=='online' and web[0]['cwd_matches']
           and web[0]['flags']==expected and worker_ready)
    return dict(status='baseline_matches' if ready else 'review_required',ok=ready,
                processes=selected,network_calls=0,production_writes=0,
                scope='PM2 metadata only; not live worker environment or network tracing')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routing', choices=('0','1'), default='0')
    parser.add_argument('--worker', choices=('stopped','online'), default='stopped')
    parser.add_argument('--world-stage',choices=('ingest','read','visits','regional','rollback'))
    parser.add_argument('--halo',choices=('0','1'))
    args=parser.parse_args()
    try:
        response=subprocess.run(['pm2','jlist'],capture_output=True,text=True,timeout=15,check=True)
        result=inspect(json.loads(response.stdout),Path(__file__).resolve().parents[1], routing=args.routing,worker=args.worker,world_stage=args.world_stage,halo=args.halo)
        print(json.dumps(result));return 0 if result['ok'] else 2
    except Exception as exc:
        # Raw PM2 output/env and subprocess error strings may contain secrets.
        print(json.dumps(dict(ok=False,status='runtime_unavailable',error_type=type(exc).__name__)));return 1


if __name__=='__main__':raise SystemExit(main())
