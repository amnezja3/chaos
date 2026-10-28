"""Hourly aggregate scanner outcomes, without coordinates, users or query keys."""
from contextvars import ContextVar
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import time

_current=ContextVar('world_scan_metrics',default=None)
BUCKETS=(.1,.5,1,3,10,30,120)


def initialize(repo):
    with repo.transaction() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS world_scan_metric (
            hour INTEGER NOT NULL, source TEXT NOT NULL, outcome TEXT NOT NULL,
            latency_bucket INTEGER NOT NULL, samples INTEGER NOT NULL,
            transport_attempts INTEGER NOT NULL, elapsed_ms INTEGER NOT NULL,
            PRIMARY KEY(hour,source,outcome,latency_bucket))''')


def begin():
    return _current.set(dict(sources=set(),attempts=0,started=time.monotonic()))


def source(value):
    current=_current.get()
    if current is not None and value in ('world','fresh','stale','upstream'):
        current['sources'].add(value)


def transport_attempt():
    current=_current.get()
    if current is not None: current['attempts']+=1


def record(repo, sources, attempts, outcome, seconds, now=None):
    if outcome not in ('success','empty','api_error'): raise ValueError('metric_outcome')
    if type(attempts) is not int or attempts<0 or attempts>100: raise ValueError('metric_attempts')
    import math
    if not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<0:
        raise ValueError('metric_seconds')
    kind=('network' if attempts or 'upstream' in sources else
          'mixed' if 'world' in sources and {'fresh','stale'} & set(sources) else
          'world' if 'world' in sources else 'cache' if {'fresh','stale'} & set(sources) else 'unknown')
    hour=int((time.time() if now is None else now)//3600)*3600
    bucket=next((i for i,b in enumerate(BUCKETS) if seconds<=b),len(BUCKETS))
    # Retry only transient SQLite contention after transaction() has rolled
    # back and closed its connection. Keep optional telemetry bounded: three
    # attempts with the existing 500 ms busy timeout, no global timeout change.
    for attempt in range(3):
        try:
            with repo.transaction() as c:
                c.execute('DELETE FROM world_scan_metric WHERE hour<?',(hour-7*86400,))
                c.execute('''INSERT INTO world_scan_metric VALUES (?,?,?,?,1,?,?)
                    ON CONFLICT(hour,source,outcome,latency_bucket) DO UPDATE SET
                    samples=samples+1,transport_attempts=transport_attempts+excluded.transport_attempts,
                    elapsed_ms=elapsed_ms+excluded.elapsed_ms''',
                    (hour,kind,outcome,bucket,attempts,round(seconds*1000)))
            return
        except sqlite3.OperationalError as exc:
            code=getattr(exc,'sqlite_errorcode',None)
            busy=(code is not None and (code & 255) in (5,6))  # SQLITE_BUSY / SQLITE_LOCKED
            # Python 3.10 does not expose sqlite_errorcode.
            if code is None:busy=str(exc) in ('database is locked','database table is locked')
            if not busy or attempt==2:raise
            time.sleep(.025*(attempt+1))


def finish(token,outcome):
    value=_current.get();_current.reset(token)
    if os.environ.get('CHAOS_POI_METRICS_ENABLED')!='1': return
    from .repository import Repository
    try:
        repo=Repository(os.environ.get('CHAOS_POI_CACHE_PATH','data/poi_cache.sqlite3'))
        if not Path(repo.path).is_file(): return
        record(repo,value['sources'],value['attempts'],outcome,time.monotonic()-value['started'])
    except (sqlite3.Error,OSError):
        # Optional telemetry must not turn a completed gameplay scan into failure.
        from . import logger
        logger().warning('poi_metrics_write_skipped')


def summary(repo,now=None):
    end=time.time() if now is None else now
    start=int(end//3600)*3600-23*3600
    result=dict(prepared=False,window_start=start,window_end=end,attempts=0,successful=0,
                empty_successes=0,errors=0,sources={},transport_attempts=0,
                world_local_scan_ratio=None,network_scan_ratio=None,
                latency_p50_upper_seconds=None,latency_p95_upper_seconds=None,
                definition='POIFetcher.get_all outcomes; empty counts as success; excludes background/probes; current plus 23 UTC hours')
    if not Path(repo.path).is_file(): return result
    with closing(sqlite3.connect(Path(repo.path).resolve().as_uri()+'?mode=ro',uri=True)) as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='world_scan_metric'").fetchone(): return result
        result['prepared']=True
        rows=c.execute('SELECT source,outcome,latency_bucket,samples,transport_attempts FROM world_scan_metric WHERE hour>=? AND hour<=?',(start,end)).fetchall()
    buckets={};world=network=0
    for src,outcome,bucket,n,requests in rows:
        result['attempts']+=n;result['transport_attempts']+=requests
        buckets[bucket]=buckets.get(bucket,0)+n
        if outcome=='api_error': result['errors']+=n;continue
        result['successful']+=n
        result['empty_successes']+=n if outcome=='empty' else 0
        result['sources'][src]=result['sources'].get(src,0)+n
        world+=n if src=='world' else 0;network+=n if src=='network' else 0
    if result['successful']:
        result['world_local_scan_ratio']=world/result['successful']
        result['network_scan_ratio']=network/result['successful']
    for percentile in (50,95):
        acc=0
        for bucket,n in sorted(buckets.items()):
            acc+=n
            if acc>=result['attempts']*percentile/100:
                result[f'latency_p{percentile}_upper_seconds']=BUCKETS[bucket] if bucket<len(BUCKETS) else None
                break
    return result
