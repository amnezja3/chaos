"""Bounded, passive admin projections; never fetches, migrates or reads secrets."""
import os
import time

from .discovery_queue import DemandQueue
from .credit_budget import CreditBudget
from .world_storage import FORMAT


def status(repo):
    c=repo.connect()
    try:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result=dict(network_calls=0,world_prepared=False,snapshots=0,canonical_snapshots=0,
                    payload_bytes=0,fresh=0,stale=0,expired=0,
                    ingest_enabled=os.environ.get('CHAOS_POI_WORLD_INGEST_ENABLED')=='1',
                    read_enabled=os.environ.get('CHAOS_POI_WORLD_REPOSITORY_ENABLED')=='1',
                    discovery_mode=os.environ.get('CHAOS_POI_DISCOVERY_MODE','off'),
                    background_fetch_enabled=False)
        if {'world_snapshot','world_schema'}<=tables:
            result['world_prepared']=c.execute('SELECT version FROM world_schema').fetchone()[0]==2
            row=c.execute('''SELECT count(*) n,coalesce(sum(bytes),0) bytes,
                coalesce(sum(profile=?),0) canonical FROM world_snapshot''',(FORMAT,)).fetchone()
            result.update(snapshots=row['n'],canonical_snapshots=row['canonical'],payload_bytes=row['bytes'])
            now=time.time()
            row=c.execute('''SELECT coalesce(sum(fresh_until>?),0) fresh,
                coalesce(sum(fresh_until<=? AND usable_until>?),0) stale,
                coalesce(sum(usable_until<=?),0) expired FROM world_snapshot''',(now,now,now,now)).fetchone()
            result.update(dict(row))
        has_ledger={'world_credit_operation','world_credit_window'}<=tables
    finally:
        c.close()
    result['demand']=DemandQueue(repo).summary()
    result['budget_windows']=CreditBudget(repo).status('maplark') if has_ledger else []
    return result
