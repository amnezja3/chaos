"""Read-only retained inventory, not lifetime growth or a coverage certificate."""
from contextlib import closing
from pathlib import Path
import sqlite3
import time

from .world_storage import FORMAT


def summary(repo):
    result=dict(prepared=False, complete=False, unique_objects=None,
                first_seen_retained_24h=None, wal_bytes=None, database_bytes=None,
                queue_p95_wait_seconds=None, network_calls=0,
                scope='retained_canonical_inventory_not_lifetime_growth')
    path=Path(repo.path).resolve()
    if not path.is_file(): return result
    for key,file in (('database_bytes',path),('wal_bytes',Path(str(path)+'-wal'))):
        try: result[key]=file.stat().st_size
        except FileNotFoundError: result[key]=0
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as c:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'world_member','world_snapshot','world_schema'}<=tables: return result
        if c.execute('SELECT version FROM world_schema').fetchone()[0]!=2:return result
        result['prepared']=True
        deadline=time.monotonic()+2
        c.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        try:
            c.execute('BEGIN')
            now=time.time()
            row=c.execute('''SELECT count(*),coalesce(sum(first_seen>=?),0) FROM (
                SELECT m.identity,min(s.fetched) first_seen FROM world_member m
                JOIN world_snapshot s ON s.id=m.snapshot_id
                WHERE s.profile=? AND m.identity IS NOT NULL GROUP BY m.identity)''',
                (now-86400,FORMAT)).fetchone()
            result.update(unique_objects=row[0],first_seen_retained_24h=row[1])
            if 'world_discovery_job' in tables:
                pending="state IN ('PENDING','DEFERRED','RETRY_AFTER') AND expires>?"
                count=c.execute('SELECT count(*) FROM world_discovery_job WHERE '+pending,(now,)).fetchone()[0]
                if count:
                    import math
                    # Nearest-rank p95 of current waiting age, not completed latency.
                    row=c.execute('SELECT updated FROM world_discovery_job WHERE '+pending+
                        ' ORDER BY updated DESC LIMIT 1 OFFSET ?', (now,math.ceil(.95*count)-1)).fetchone()
                    result['queue_p95_wait_seconds']=round(max(0,now-row[0]),1)
            result['complete']=True
        except sqlite3.OperationalError as exc:
            if 'interrupt' not in str(exc).lower():raise
            result.update(unique_objects=None,first_seen_retained_24h=None,queue_p95_wait_seconds=None)
    return result
