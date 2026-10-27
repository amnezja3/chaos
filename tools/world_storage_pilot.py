"""Inspect one exact world result, optionally evict only its disposable cache.

No HTTP, provider decision, schema mutation or ledger reset. Explicit prune
removes only expired snapshots of the selected exact query.
"""
import argparse
import json
import re
from contextlib import closing
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.maplark_profile import PROFILE, ENDPOINT
from poi_infrastructure.world_adapters import plan_maplark, MAPLARK_VERSION
from poi_infrastructure.world_contract import batch_key, POI_PROFILE, ContractError
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import WorldReadPlanner
from poi_infrastructure.world_shadow import reference


def inspect(db,lat=None,lon=None,*,key_prefix=None,evict=False,prune=False,apply=False):
    if evict and prune:raise ValueError('one_action_required')
    if key_prefix is not None:
        if lat is not None or lon is not None:raise ValueError('choose_key_or_coordinates')
        if not isinstance(key_prefix,str) or not re.fullmatch('[0-9a-f]{12,64}',key_prefix):
            raise ValueError('key_prefix_requires_12_to_64_hex_characters')
    elif lat is None or lon is None:raise ValueError('coordinates_or_key_required')
    if not Path(db).is_file():raise ValueError('existing_poi_database_required')
    repo=Repository(db)
    provider=next((p for p in Registry(repo).eligible('normal_scan') if p['id']=='maplark' and p['url']==ENDPOINT),None)
    if not provider or not reference(provider):raise ValueError('world_storage_approval_required')
    if key_prefix is None:
        plan=plan_maplark(lat,lon,300,limit=1000)
        key=batch_key('maplark',PROFILE,plan.profile,PROFILE,{'params':plan.params,'revision':provider['revision']})
    else:
        with closing(repo.connect()) as c:
            rows=c.execute("SELECT DISTINCT query_key FROM world_snapshot WHERE provider='maplark' AND query_key LIKE ? LIMIT 2",
                           (key_prefix+'%',)).fetchall()
        if len(rows)!=1:raise ValueError('world_key_missing_or_ambiguous')
        key=rows[0][0]
    result=WorldReadPlanner(CanonicalWorldRepository(repo)).read(provider='maplark',revision=provider['revision'],
        storage_reference=reference(provider),profile=POI_PROFILE,selection='maplark-radius-unverified',
        adapter_version=MAPLARK_VERSION,query_key=key)
    removed=0
    pruned=0
    if prune and apply:
        with repo.transaction() as c:
            current=c.execute("SELECT revision FROM poi_provider_config WHERE id='maplark'").fetchone()
            if not current or current[0]!=provider['revision']:raise ValueError('provider_revision_changed')
            rows=c.execute('SELECT id FROM world_snapshot WHERE query_key=? AND usable_until<? LIMIT 100',
                           (key,time.time())).fetchall()
            c.executemany('DELETE FROM world_snapshot WHERE id=?',[(r[0],) for r in rows])
            pruned=len(rows)
    if evict and apply:
        if result.batch is None:raise ValueError('fresh_world_result_required')
        with repo.transaction() as c:
            now=time.time()
            current=c.execute("SELECT revision FROM poi_provider_config WHERE id='maplark'").fetchone()
            if not current or current[0]!=provider['revision']:raise ValueError('provider_revision_changed')
            if not c.execute('SELECT 1 FROM world_snapshot WHERE id=? AND fresh_until>?',(result.snapshot,now)).fetchone():
                raise ValueError('fresh_world_result_required')
            if c.execute('SELECT 1 FROM leases WHERE key=? AND until_at>?',(key,now)).fetchone():
                raise ValueError('scan_in_flight')
            removed=c.execute('DELETE FROM cache WHERE key=?',(key,)).rowcount
    return dict(status='cache_evicted' if evict and apply else 'expired_pruned' if prune and apply else 'read_only',network_calls=0,
        key=key[:12],revision=provider['revision'],world_state=result.state,reason=result.reason,
        objects=len(result.batch.objects) if result.batch is not None else None,
        removed_cache_entries=removed,pruned_snapshots=pruned,ledger_unchanged=True,world_unchanged=not pruned)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--lat',type=float)
    parser.add_argument('--lon',type=float)
    parser.add_argument('--key-prefix',help='Exact MapLark scan key from its log, 12–64 hex characters')
    parser.add_argument('--evict-cache',action='store_true')
    parser.add_argument('--prune-expired',action='store_true')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:
        print(json.dumps(inspect(args.db,args.lat,args.lon,key_prefix=args.key_prefix,evict=args.evict_cache,prune=args.prune_expired,apply=args.apply)))
    except (ValueError,ContractError) as exc:
        print(json.dumps(dict(ok=False,error=str(exc),network_calls=0)))
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
