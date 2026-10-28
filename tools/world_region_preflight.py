"""Read-only regional reader preflight at explicit scan coordinates. No HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
import os

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.maplark_region import read, FLAG, PROFILE
from poi_infrastructure.maplark_profile import PROFILE as EXACT_PROFILE
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import batch_key


class ReadOnlyRepository(Repository):
    def connect(self):
        conn=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.5)
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        return conn


def inspect(db,snapshot,lat,lon,radius=300):
    repo=ReadOnlyRepository(db)
    report=dict(status='not_ready',network_calls=0,production_writes=0,
                web_environment_verified=False,live_acceptance=False,
                query=dict(lat=lat,lon=lon,radius=radius))
    with closing(repo.connect()) as conn:
        row=conn.execute('SELECT fetched,fresh_until FROM world_snapshot WHERE id=?',(snapshot,)).fetchone()
    if row is None:return dict(report,reason='snapshot_missing')
    expiry=min(row['fresh_until'],row['fetched']+300)
    report['fresh_until']=expiry
    report['remaining_seconds']=round(expiry-time.time(),2)
    if time.time()<row['fetched'] or report['remaining_seconds']<60:
        return dict(report,reason='freshness_window_too_short')
    candidate=next((p for p in Registry(repo).eligible('normal_scan') if p['id']=='maplark'),None)
    if not candidate:return dict(report,reason='provider_not_eligible')
    plan=plan_maplark(lat,lon,radius,limit=1000)
    report['expected_key']=batch_key('maplark',EXACT_PROFILE,plan.profile,EXACT_PROFILE,
        {'params':plan.params,'revision':candidate['revision']})[:12]
    trace={}
    started=time.monotonic()
    # Only this diagnostic process; never claims to inspect the PM2 worker env.
    with patch.dict(os.environ,{FLAG:PROFILE,'CHAOS_POI_WORLD_REPOSITORY_ENABLED':'1'}):
        data=read(SimpleNamespace(repo=repo),candidate,report['query'],lambda:True,diagnostic=trace)
    report.update(diagnostic=trace,reader_seconds=round(time.monotonic()-started,4),
                  remaining_seconds=round(expiry-time.time(),2))
    if data is None:return dict(report,reason='regional_reader_miss')
    if trace.get('snapshot')!=snapshot:return dict(report,reason='different_snapshot_selected')
    if report['remaining_seconds']<60:return dict(report,reason='freshness_window_too_short')
    return dict(report,status='ready',reason='fresh_regional_read',objects=len(data['elements']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--lat',required=True,type=float)
    parser.add_argument('--lon',required=True,type=float)
    parser.add_argument('--radius',type=float,default=300)
    args=parser.parse_args()
    result=inspect(args.db,args.snapshot,args.lat,args.lon,args.radius)
    print(json.dumps(result))
    raise SystemExit(0 if result['status']=='ready' else 2)
