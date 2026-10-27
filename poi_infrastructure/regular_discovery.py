"""Demand-driven observation collection. No automatic provider approvals or quota resets."""
from contextlib import closing
import hashlib
import json
import os
import time
from pathlib import Path

from .credit_budget import CreditBudget
from .discovery_worker import DiscoveryPermit,DiscoveryWorker,PermitExpired
from .discovery_producer import prepare_jobs
from .providers import Registry
from .routing import Routing,adapter,reason
from .world import WorldRepository
from .discovery_jobs import DiscoveryJobs
from .discovery_halo import cells as demand_cells, expand as expand_halo, tasks_for

POLICY_VERSION='regular-world-v1'
DEFAULTS=dict(version=POLICY_VERSION,enabled=True,interval=60,max_regions=100,
              retention_seconds=604800,refresh_seconds=604800,
              maplark_background_daily=200,geoapify_background_daily=200,
              overpass_daily_requests=120)


def initialize(repo):
    from .worker_heartbeat import initialize as initialize_heartbeat
    initialize_heartbeat(repo)
    with repo.transaction() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS world_collection_runtime (
            id INTEGER PRIMARY KEY CHECK(id=1), next_cycle REAL NOT NULL,
            cursor INTEGER NOT NULL, report TEXT NOT NULL)''')
        c.execute("INSERT OR IGNORE INTO world_collection_runtime VALUES (1,0,0,'{}')")
        c.execute('''CREATE TABLE IF NOT EXISTS world_collection_seen (
            cell_x INTEGER NOT NULL,cell_y INTEGER NOT NULL,profile TEXT NOT NULL,
            fetched REAL NOT NULL,provider TEXT NOT NULL DEFAULT '',revision INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(cell_x,cell_y,profile))''')
        columns={r[1] for r in c.execute('PRAGMA table_info(world_collection_seen)')}
        if 'provider' not in columns:c.execute("ALTER TABLE world_collection_seen ADD COLUMN provider TEXT NOT NULL DEFAULT ''")
        if 'revision' not in columns:c.execute('ALTER TABLE world_collection_seen ADD COLUMN revision INTEGER NOT NULL DEFAULT 0')


def load(path):
    raw=Path(path).read_bytes()
    if len(raw)>8192:raise ValueError('collection_policy_size')
    policy=json.loads(raw)
    if set(policy)!=set(DEFAULTS)|{'review_until'} or any(type(policy[k]) is not type(v) or policy[k]!=v for k,v in DEFAULTS.items() if k!='enabled'):
        raise ValueError('collection_policy_contract')
    if type(policy['enabled']) is not bool or type(policy['review_until']) not in (float,int):
        raise ValueError('collection_policy_types')
    if not time.time()<policy['review_until']<=time.time()+31*86400:
        raise PermitExpired('collection_policy_review_expired')
    return policy,hashlib.sha256(raw).hexdigest()


def report(repo):
    from .worker_heartbeat import inspect as heartbeat_status
    with closing(repo.connect()) as c:
        heartbeat=heartbeat_status(c)
        row=c.execute('SELECT * FROM world_collection_runtime WHERE id=1').fetchone()
        states={r[0]:r[1] for r in c.execute('SELECT state,count(*) FROM world_discovery_job GROUP BY state')}
        estimates=c.execute("SELECT count(*),coalesce(sum(reserved),0) FROM world_credit_operation WHERE account='geoapify' AND state='estimated'").fetchone()
        snapshots=c.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone()
        accounts=[r[0] for r in c.execute('SELECT account FROM world_credit_policy')]
        receipts=c.execute('SELECT count(*) FROM world_discovery_refresh').fetchone()[0]
        uncertain={r[0]:dict(operations=r[1],reserved=r[2]) for r in c.execute("SELECT account,count(*),sum(reserved) FROM world_credit_operation WHERE state IN ('uncertain','reserved') GROUP BY account")}
    budgets={account:CreditBudget(repo).status(account) for account in accounts}
    warnings=[account+'_budget_low' for account,windows in budgets.items() if any(w['remaining']<.1*w['credit_limit'] for w in windows)]
    if heartbeat['status'] not in ('running','waiting'):warnings.append('collector_heartbeat_'+heartbeat['status'])
    last=json.loads(row['report'])
    if last.get('at',0)<time.time()-300:warnings.append('collector_cycle_stale')
    if last.get('status') in ('reconciliation_required','policy_blocked','deferred'):warnings.append('collector_attention_required')
    if receipts>=1800:warnings.append('refresh_history_capacity_near')
    return dict(status='read_only',network_calls=0,heartbeat=heartbeat,next_cycle=row['next_cycle'],last=last,jobs=states,
                snapshots=snapshots[0],snapshot_bytes=snapshots[1],budgets=budgets,warnings=warnings,
                budget_units={account:'credits' if account in ('maplark','geoapify') else 'request_attempts' for account in accounts},
                unresolved=uncertain,refresh_receipts=receipts,
                geoapify_estimated_operations=estimates[0],geoapify_reserved_estimate=estimates[1],
                note='Internal ledger, not provider balance. Old uncertain operations remain reserved.')


def cycle(repo,path,*,execute=False,enabled=lambda:False,transport=None):
    policy,digest=load(path)
    if not policy['enabled'] or (execute and not enabled()):return dict(status='disabled',network_calls=0)
    now=time.time()
    halo=os.getenv('CHAOS_POI_WORLD_HALO_ENABLED')=='1'
    entries=demand_cells(repo,policy['max_regions'],halo=halo)
    cells=[cell for cell,tier in entries]
    with closing(repo.connect()) as c:
        state=c.execute('SELECT * FROM world_collection_runtime WHERE id=1').fetchone()
    if not execute:return dict(status='plan',network_calls=0,regions=len(cells),max_regions=policy['max_regions'],
        refresh_seconds=604800,retention_seconds=604800,review_until=policy['review_until'],
        routes=Routing(repo).describe()['routes'])
    if now<state['next_cycle']:return dict(status='waiting',network_calls=0,next_cycle=state['next_cycle'])
    lease=repo.acquire('@regular-world-cycle',110)
    if not lease:return dict(status='busy',network_calls=0)
    def active():
        if not enabled() or not repo.owns('@regular-world-cycle',lease):return False
        try:return load(path)[1]==digest
        except (OSError,ValueError,TypeError):return False
    result=dict(status='idle',network_calls=0,regions=len(cells));started=time.monotonic()
    try:
        with repo.transaction() as c:
            current=c.execute('SELECT next_cycle FROM world_collection_runtime WHERE id=1').fetchone()[0]
            if time.time()<current:return dict(status='waiting',network_calls=0,next_cycle=current)
            c.execute('UPDATE world_collection_runtime SET next_cycle=? WHERE id=1',(now+policy['interval'],))
            c.execute('DELETE FROM world_collection_seen WHERE fetched<=?',(now-604800,))
            c.execute('''INSERT INTO world_collection_seen
                SELECT d.cell_x,d.cell_y,j.profile,max(j.updated),j.provider,j.revision FROM world_discovery_job j
                JOIN world_discovery_demand d ON d.key=j.demand_key
                WHERE j.state='COMMITTED' AND j.updated>?
                AND j.acquisition IN ('sector-bbox-v1','overpass-bbox-geom-v1','geoapify-commercial-v1')
                GROUP BY d.cell_x,d.cell_y,j.profile
                ON CONFLICT(cell_x,cell_y,profile) DO UPDATE SET fetched=excluded.fetched,
                provider=excluded.provider,revision=excluded.revision WHERE excluded.fetched>=fetched''',(now-604800,))
        WorldRepository(repo).prune_expired(50)
        DiscoveryJobs(repo).prune(50)
        providers={p['id']:p for p in Registry(repo).list()}
        halo_added=0
        if halo and active():
            halo_added=expand_halo(repo)
            entries=demand_cells(repo,policy['max_regions'],halo=True)
            cells=[cell for cell,tier in entries]
        tasks=tasks_for(entries,state['cursor'])
        cursor=state['cursor']%max(1,len(tasks));visited=0;skipped={}
        for offset in range(len(tasks)):
            if not active():return dict(status='policy_changed',network_calls=0)
            if time.monotonic()-started>10:break
            cell,profile=tasks[offset];visited+=1
            # Archive observation age suppresses duplicate collection across geometry providers.
            with closing(repo.connect()) as c:
                recent=c.execute('SELECT * FROM world_collection_seen WHERE cell_x=? AND cell_y=? AND profile=? AND fetched>?',
                                 (*cell,profile,now-604800)).fetchone()
            source=providers.get(recent['provider']) if recent else None
            if source and source['revision']==recent['revision'] and not reason(source,profile,'background'):continue
            chain=Routing(repo).get(profile,'background')['chain']
            for provider_id in chain:
                p=providers.get(provider_id)
                why=reason(p,profile,'background') if p else 'provider_missing'
                if why:
                    skipped[why]=skipped.get(why,0)+1;continue
                if not repo.allowed(p['operator_group']):
                    skipped['circuit_open']=skipped.get('circuit_open',0)+1;continue
                kind=adapter(p)
                acquisition={'overpass':'overpass-bbox-geom-v1','maplark':'sector-bbox-v1','geoapify':'geoapify-commercial-v1'}[kind]
                reserve={'overpass':1,'maplark':20,'geoapify':6}[kind]
                day=int(now//86400)*86400
                until=min(day+86400,policy['review_until'],p['review_due_at']-604801)
                if until<=time.time():
                    skipped['storage_review_required']=skipped.get('storage_review_required',0)+1;continue
                budget_id=f'regular-{provider_id}-{day}'
                permit=DiscoveryPermit(frozenset({cell}),frozenset({profile}),until,reserve,budget_id,
                    acquisition,604800,604800,provider_id if kind=='overpass' else '')
                cap=policy['overpass_daily_requests'] if kind=='overpass' else policy[kind+'_background_daily']
                ledger=CreditBudget(repo)
                if not ledger.status(provider_id):
                    skipped['budget_unconfigured']=skipped.get('budget_unconfigured',0)+1;continue
                for scope in permit.budget_scopes(profile):ledger.configure_scope(provider_id,scope,day,day+86400,cap)
                # Existing operations/windows are retained, including uncertain charges.
                prepare_jobs(repo,permit,apply=True)
                worker=DiscoveryWorker(repo,permit,enabled=active,transport=transport)
                outcome=worker.run_one()
                if outcome['status']=='committed':
                    with repo.transaction() as c:
                        c.execute('INSERT OR REPLACE INTO world_collection_seen VALUES (?,?,?,?,?,?)',(*cell,profile,time.time(),provider_id,p['revision']))
                result=dict(outcome,provider=provider_id,profile=profile,regions=len(cells),skipped=skipped,
                            demand_origin='halo' if dict(entries).get(cell)==1 else 'direct')
                if outcome.get('network_calls',0):break
                if outcome['status'] not in ('idle','deferred','policy_blocked','reconciliation_required'):break
            if result.get('network_calls',0):break
        result.update(halo_enabled=halo,halo_added_cells=halo_added)
        with repo.transaction() as c:
            c.execute('UPDATE world_collection_runtime SET cursor=?,report=? WHERE id=1',
                      ((cursor+max(1,visited))%max(1,len(tasks)),json.dumps(dict(result,at=time.time()))))
        return result
    finally:repo.release('@regular-world-cycle',lease)
