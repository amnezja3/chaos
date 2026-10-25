"""Prepare one bounded three-layer sector acceptance; never performs HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.discovery_worker import DiscoveryPermit
from poi_infrastructure.discovery_runtime import load_permit, cycle

IDENTITY='collection-sector-2036-5153-v1'
PROFILES=('inland_water','roads','waterways')


def prepare(db, output, *, apply=False, bounded=False, cells=None, identity=None, refresh=False):
    custom = cells is not None or identity is not None
    if custom and (not bounded or not cells or not identity):
        raise ValueError('bounded_region_scope_required')
    cells = frozenset(tuple(c) for c in cells) if custom else frozenset({(2036,5153)})
    identity = identity or ('collection-daemon-2036-5153-v1' if bounded else IDENTITY)
    if refresh and not bounded: raise ValueError('bounded_refresh_required')
    hours = 24 if bounded else 1
    retention = 604800 if bounded else 1800
    preview=DiscoveryPermit(cells,frozenset(PROFILES),time.time()+86399,20,identity,
                            'sector-bbox-v1',retention,604800 if refresh else 0)
    preview.validate()
    for profile in PROFILES: preview.budget_scopes(profile)
    plan=dict(status='plan',network_calls=0,cells=sorted(cells),profiles=list(PROFILES),
              acquisition='sector-bbox-v1',max_jobs=3*len(cells),refresh_seconds=preview.refresh_seconds,reservation_per_job=20,
              shared_credit_limit=60,hours=hours,retention_seconds=retention,
              environment_changed=False,registry_changed=False,provider_price_cap=False)
    if not apply:
        return plan
    db,output=Path(db).resolve(),Path(output).resolve()
    if not db.is_file() or db.name=='game.sqlite3':
        raise ValueError('existing_poi_database_required')
    repo=Repository(db)
    permit_path=output/'permit.json'
    if output.exists():
        permit=load_permit(permit_path)
        if (permit.budget_id!=identity or permit.acquisition!='sector-bbox-v1'
                or permit.cells!=cells or permit.profiles!=frozenset(PROFILES)
                or permit.reservation!=20 or permit.retention_seconds!=retention
                or permit.refresh_seconds!=preview.refresh_seconds):
            raise ValueError('existing_permit_differs')
        return dict(plan,status='already_prepared',plan=cycle(repo,permit_path),permit=str(permit_path))
    now=time.time();until=now+hours*3600
    provider=next((p for p in Registry(repo).list() if p['id']=='maplark'),None)
    if (not provider or not provider.get('enabled')
            or provider.get('url')!='https://api.maplark.com/v3/osm_features'
            or provider.get('operator_group')!='api.maplark.com'
            or provider.get('review_due_at',0)<until+(retention if bounded else 0)
            or not all(Registry.approved(provider,s) for s in ('storage','world_storage','background_refresh'))):
        raise ValueError('collection_approval_required')
    scopes=['discovery:'+identity]+['discovery:'+identity+':'+p for p in PROFILES]
    with closing(repo.connect()) as c:
        if c.execute('SELECT 1 FROM world_credit_scope WHERE account=? AND scope=?',('maplark',scopes[0])).fetchone():
            raise ValueError('collection_already_exists_do_not_reset')
        if 'acquisition' not in {r[1] for r in c.execute('PRAGMA table_info(world_discovery_job)')}:
            raise ValueError('collection_migration_required')
        c.execute('SELECT snapshot_id FROM world_retention LIMIT 1').fetchall()
    output.mkdir(parents=True,exist_ok=False)
    backup=output/'poi_cache.sqlite3'
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
        if (target.execute('PRAGMA integrity_check').fetchone()[0]!='ok'
                or target.execute('PRAGMA foreign_key_check').fetchall()):
            raise ValueError('backup_integrity')
    data=dict(cells=sorted(cells),profiles=list(PROFILES),until=until,reservation=20,
              budget_id=identity,acquisition='sector-bbox-v1',retention_seconds=retention,
              refresh_seconds=preview.refresh_seconds)
    with permit_path.open('x',encoding='utf8') as f:
        json.dump(data,f,indent=2)
    with repo.transaction() as c:
        current=Registry(repo)._load(c,'maplark')
        if current['revision']!=provider['revision']:
            raise ValueError('provider_revision_conflict')
        for index,scope in enumerate(scopes):
            c.execute('INSERT INTO world_credit_scope VALUES (?,?,?,?,?)',
                      ('maplark',scope,now,until,60 if index==0 else 20))
    # Explicit operator acceptance sector, previously tested; no neighboring cells.
    if not custom:
        DemandQueue(repo).record(20.365,51.535,PROFILES)
    return dict(plan,status='prepared',permit=str(permit_path),backup=str(backup),
                plan=cycle(repo,permit_path))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--output')
    p.add_argument('--bounded',action='store_true',help='24h permit, seven-day archive, same sector and budget cap')
    p.add_argument('--apply',action='store_true')
    p.add_argument('--cell',nargs=2,type=int,action='append',help='Explicit approved cell; repeat up to ten. Does not create demand.')
    args=p.parse_args()
    try:
        output=args.output or ('data/collection-regions-v1' if args.cell else
                              'data/collection-daemon-2036-5153-v1' if args.bounded else 'data/'+IDENTITY)
        print(json.dumps(prepare(args.db,output,apply=args.apply,bounded=args.bounded,
            cells=args.cell,identity='collection-regions-v1' if args.cell else None,refresh=bool(args.cell))))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__)))
        return 1


if __name__=='__main__':raise SystemExit(main())
