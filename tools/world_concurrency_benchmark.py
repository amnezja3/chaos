"""Bounded offline workload: four acquisition processes plus one background process.

Temporary SQLite only, synthetic empty responses and fixed simulated costs.
Measures coordination, not HTTP performance, geometry storage or user-facing SLO.
"""
import argparse
from collections import Counter
from contextlib import closing
import json
import math
import multiprocessing
import os
import queue
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.service import POIError


def worker(path,lane,indices,barrier,live_done,output):
    # Override any inherited real key. The only transport is the local function below.
    os.environ['CHAOS_MAPLARK_API_KEY']='synthetic-benchmark-key'
    os.environ['CHAOS_POI_PRIORITY_ENABLED']='1'
    repo=Repository(path)
    samples=[]
    def transport(*args,**kwargs):
        with repo.transaction() as c:
            c.execute('UPDATE benchmark_activity SET active=active+1,calls=calls+1')
            c.execute('UPDATE benchmark_activity SET peak=max(peak,active)')
        try:
            time.sleep(.02)
            return 200,None,dict(body=dict(type='FeatureCollection',features=[]),response_headers={
                'X-Returned':'0','X-Has-More':'false','X-Usage-Units-Charged':'3'})
        finally:
            with repo.transaction() as c:c.execute('UPDATE benchmark_activity SET active=active-1')
    try:
        barrier.wait(timeout=30)
        for index in indices:
            # First background attempt competes with live; the rest follow live.
            # These are distinct operations, not automatic retries of a failed HTTP.
            if lane=='background' and index>0 and not live_done.wait(60):
                raise RuntimeError('live_completion_timeout')
            started=time.monotonic()
            try:
                acquire_maplark(repo,plan_maplark(52,21,300),lane+'-'+str(index),20,
                    accept_variable_cost=True,transport=transport,lane=lane)
                status='success'
            except (ContractError,POIError) as exc:
                status=str(exc) if str(exc) in ('budget_exhausted','upstream_busy') else type(exc).__name__
            samples.append(dict(lane=lane,status=status,seconds=time.monotonic()-started))
        output.put(dict(ok=True,samples=samples))
    except Exception as exc:
        output.put(dict(ok=False,error_type=type(exc).__name__))


def percentile(values,fraction):
    return round(sorted(values)[max(0,math.ceil(len(values)*fraction)-1)],6) if values else None


def run(scans=100,background=10,credit_limit=100):
    if (type(scans) is not int or not 4<=scans<=100 or type(background) is not int
            or not 2<=background<=10 or type(credit_limit) is not int or not 20<=credit_limit<=1000):
        raise ValueError('benchmark_limits')
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='chaos-world-concurrency-') as directory:
        repo=Repository(Path(directory)/'poi.sqlite3');repo.initialize()
        ledger=CreditBudget(repo);ledger.initialize()
        ledger.configure_window('maplark','synthetic',time.time()-1,time.time()+600,credit_limit)
        with repo.transaction() as c:
            c.execute('CREATE TABLE benchmark_activity(active INTEGER,peak INTEGER,calls INTEGER)')
            c.execute('INSERT INTO benchmark_activity VALUES (0,0,0)')
        ctx=multiprocessing.get_context('spawn')
        barrier=ctx.Barrier(5);done=ctx.Event();output=ctx.Queue()
        processes=[ctx.Process(target=worker,args=(repo.path,'live',list(range(i,scans,4)),barrier,done,output)) for i in range(4)]
        processes.append(ctx.Process(target=worker,args=(repo.path,'background',list(range(background)),barrier,done,output)))
        messages=[]
        try:
            for process in processes:process.start()
            deadline=time.monotonic()+90
            while any(p.is_alive() for p in processes):
                if all(p.exitcode is not None for p in processes[:4]):done.set()
                if time.monotonic()>deadline:raise RuntimeError('benchmark_timeout')
                # Drain IPC while workers are running; joining before drain can deadlock.
                try:messages.append(output.get(timeout=.1))
                except queue.Empty:pass
            for process in processes:process.join()
            while len(messages)<5:messages.append(output.get(timeout=2))
            if any(p.exitcode!=0 for p in processes) or not all(m['ok'] for m in messages):
                raise RuntimeError('benchmark_child_failed')
        finally:
            for process in processes:
                if process.is_alive():process.terminate()
                if process.pid is not None:process.join(5)
            output.close();output.join_thread()
        samples=[s for m in messages for s in m['samples']]
        with closing(repo.connect()) as c:
            activity=dict(c.execute('SELECT * FROM benchmark_activity').fetchone())
            remaining_leases=c.execute('SELECT count(*) FROM leases').fetchone()[0]
            operations=c.execute('SELECT count(*) FROM world_credit_operation').fetchone()[0]
            integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
        committed=ledger.status('maplark')[0]['committed']
        success=sum(s['status']=='success' for s in samples)
        checks=dict(all_attempts_recorded=len(samples)==scans+background,
            outcomes_expected=all(s['status'] in ('success','budget_exhausted','upstream_busy') for s in samples),
            single_transport_slot=activity['peak']==1 and activity['active']==0,
            ledger_matches=committed==success*3 and success==activity['calls']==operations,
            within_budget=committed<=credit_limit,no_remaining_leases=remaining_leases==0,integrity=integrity=='ok')
        lanes={}
        for lane in ('live','background'):
            group=[s for s in samples if s['lane']==lane]
            lanes[lane]=dict(attempts=len(group),outcomes=dict(Counter(s['status'] for s in group)),
                latency_p50_seconds=percentile([s['seconds'] for s in group],.5),
                latency_p95_seconds=percentile([s['seconds'] for s in group],.95))
        return dict(status='pass' if all(checks.values()) else 'failed',synthetic=True,
            network_calls=0,production_writes=0,processes=dict(live=4,background=1),
            lanes=lanes,checks=checks,simulated_transport_calls=activity['calls'],
            simulated_credits=committed,credit_limit=credit_limit,reservation=20,
            max_inflight=activity['peak'],elapsed_seconds=round(time.monotonic()-started,4),
            note='100 scheduled acquisitions are not 100 concurrent players. Fixed 20 ms empty transport, 3 simulated credits. Background first competes, then drains after live. Not a web load test, priority proof, storage benchmark or production SLO.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scans',type=int,default=100)
    parser.add_argument('--background',type=int,default=10)
    parser.add_argument('--credit-limit',type=int,default=100)
    args=parser.parse_args()
    result=run(args.scans,args.background,args.credit_limit)
    print(json.dumps(result));return 0 if result['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())
