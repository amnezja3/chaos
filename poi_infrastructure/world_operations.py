"""Bounded, passive admin projections; never fetches, migrates or reads secrets."""
import os
import time

from .discovery_queue import DemandQueue
from .credit_budget import CreditBudget
from .world_storage import FORMAT


def job_summary(connection, tables, now):
    """Recorded queue state only; never infer a running process or recover leases."""
    result=dict(prepared='world_discovery_job' in tables, total=0, states={},
                ready_by_time=0, expired_waiting=0, expired_leases=0,
                unresolved=0, oldest_wait_seconds=None, recent=[], runtime='unknown')
    if not result['prepared']: return result
    for row in connection.execute('SELECT state,count(*) n FROM world_discovery_job GROUP BY state'):
        result['states'][row['state']]=row['n']; result['total']+=row['n']
    row=connection.execute('''SELECT
        coalesce(sum(state IN ('PENDING','DEFERRED','RETRY_AFTER') AND expires>? AND available_at<=?),0) ready,
        coalesce(sum(state IN ('PENDING','DEFERRED','RETRY_AFTER') AND expires<=?),0) expired,
        coalesce(sum(state IN ('LEASED','FETCHING','VALIDATING') AND lease_until<=?),0) lost,
        coalesce(sum(state='POLICY_BLOCKED' AND reason='outcome_unknown'),0) unresolved,
        min(CASE WHEN state IN ('PENDING','DEFERRED','RETRY_AFTER') AND expires>?
            THEN updated END) oldest FROM world_discovery_job''',(now,now,now,now,now)).fetchone()
    result.update(ready_by_time=row['ready'],expired_waiting=row['expired'],
                  expired_leases=row['lost'],unresolved=row['unresolved'],
                  oldest_wait_seconds=max(0,round(now-row['oldest'],1)) if row['oldest'] is not None else None)
    # No owner tokens, request/operation IDs, player identities or paths.
    result['recent']=[dict(r) for r in connection.execute('''SELECT provider,profile,state,
        attempts,updated,expires,reason FROM world_discovery_job ORDER BY updated DESC,id LIMIT 20''')]
    return result


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
        result['jobs']=job_summary(c,tables,time.time())
    finally:
        c.close()
    result['demand']=DemandQueue(repo).summary()
    result['budget_windows']=CreditBudget(repo).status('maplark') if has_ledger else []
    return result
