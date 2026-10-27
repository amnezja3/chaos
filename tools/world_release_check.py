"""Read-only VPS acceptance on a consistent temporary copy. No provider calls."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_dashboard import coverage, budget_projection
from poi_infrastructure.world_operations import job_summary
from poi_infrastructure.scan_metrics import summary
from poi_infrastructure.providers import Registry


def inspect(db,require_metrics=False,require_collection=False,require_visits=False,require_heartbeat=False):
    source=Path(db).resolve()
    if not source.is_file(): raise ValueError('existing_poi_database_required')
    with tempfile.TemporaryDirectory(prefix='chaos-world-release-') as directory:
        target=Path(directory)/'poi.sqlite3'
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
            tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'cache','leases','providers'}<=tables or 'users' in tables:
                raise ValueError('not_a_poi_database')
            with closing(sqlite3.connect(target)) as dest: src.backup(dest)
        repo=Repository(target)
        with closing(repo.connect()) as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
            fk=len(c.execute('PRAGMA foreign_key_check').fetchall())
            version=c.execute('SELECT version FROM world_schema').fetchone()[0] if 'world_schema' in tables else None
            jobs=job_summary(c,tables,time.time())
            job_columns={r[1] for r in c.execute('PRAGMA table_info(world_discovery_job)')}
            collection_ready='acquisition' in job_columns and 'world_retention' in tables
            required={'world_provider_observation','world_scan_metric'}
            metrics_ready=required<=tables
            visits_ready='origin' in {r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')}
            heartbeat_ready='world_worker_heartbeat' in tables
            totals=c.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone() if 'world_snapshot' in tables else (0,0)
            processes_expected='4 web + bounded worker; this report does not inspect PM2'
        ok=(integrity=='ok' and fk==0 and version==2 and jobs['prepared']
            and (metrics_ready or not require_metrics) and (collection_ready or not require_collection)
            and (visits_ready or not require_visits) and (heartbeat_ready or not require_heartbeat))
        world_sources=[dict(provider=p['id'],revision=p['revision'],
                            world_storage_allowed=Registry.approved(p,'world_storage'))
                       for p in Registry(repo).eligible('normal_scan')] if 'poi_provider_config' in tables else []
        return dict(ok=ok,status='checked' if ok else 'requirements_not_met',network_calls=0,
            production_writes=0,source_access='SQLite mode=ro; inspection on temporary backup',
            integrity=integrity,foreign_keys='ok' if fk==0 else 'failed',world_schema=version,
            metrics_schema_ready=metrics_ready,snapshots=totals[0],logical_bytes=totals[1],
            collection_schema_ready=collection_ready,
            visits_schema_ready=visits_ready,
            heartbeat_schema_ready=heartbeat_ready,
            live_scan_sources=world_sources,
            jobs=jobs,coverage=coverage(repo,show_empty=True),budgets=budget_projection(repo),
            metrics=summary(repo),runtime=processes_expected,
            limitation='Not a live provider certification, load benchmark or network trace')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--require-metrics',action='store_true')
    p.add_argument('--require-collection',action='store_true')
    p.add_argument('--require-visits',action='store_true')
    p.add_argument('--require-heartbeat',action='store_true')
    args=p.parse_args()
    result=inspect(args.db,args.require_metrics,args.require_collection,args.require_visits,args.require_heartbeat)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
