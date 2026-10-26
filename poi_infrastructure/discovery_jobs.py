"""Offline job lifecycle, not a network worker or permission to fetch.

Existing passive demand is unchanged. A caller must separately enforce provider
policy, live priority, shared transport slots and credit reservations before HTTP.
An interrupted possible HTTP is quarantined, never automatically repeated.
"""
import hashlib
import json
import math
import re
import time
import uuid

from .discovery_queue import DemandQueue
from .world_storage import FORMAT


STATES = ('PENDING','LEASED','FETCHING','VALIDATING','COMMITTED','DEFERRED',
          'RETRY_AFTER','POLICY_BLOCKED','FAILED_TERMINAL','CANCELLED')

ADMISSION_DEFERRALS=frozenset(('upstream_busy','circuit_open','world_capacity',
    'publication_busy','budget_exhausted','budget_scope_exhausted',
    'provider_secret_missing_or_invalid'))

ACQUISITIONS = frozenset(('radius-300-v1', 'sector-bbox-v1', 'geoapify-commercial-v1','overpass-bbox-geom-v1'))


def token(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',value):
        raise ValueError('job_token')
    return value


class DiscoveryJobs:
    def __init__(self,repo,max_jobs=2000,max_attempts=3):
        if type(max_jobs) is not int or not 1<=max_jobs<=2000:
            raise ValueError('job_capacity')
        if type(max_attempts) is not int or not 1<=max_attempts<=3:
            raise ValueError('job_attempts')
        self.repo=repo; self.max_jobs=max_jobs; self.max_attempts=max_attempts

    def initialize(self):
        DemandQueue(self.repo).initialize()
        with self.repo.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS world_discovery_job (
                id TEXT PRIMARY KEY, demand_key TEXT NOT NULL, provider TEXT NOT NULL,
                revision INTEGER NOT NULL, profile TEXT NOT NULL, state TEXT NOT NULL
                CHECK(state IN ('PENDING','LEASED','FETCHING','VALIDATING','COMMITTED',
                'DEFERRED','RETRY_AFTER','POLICY_BLOCKED','FAILED_TERMINAL','CANCELLED')),
                attempts INTEGER NOT NULL, owner TEXT, lease_until REAL NOT NULL,
                available_at REAL NOT NULL, expires REAL NOT NULL, updated REAL NOT NULL,
                operation TEXT, snapshot TEXT, reason TEXT NOT NULL)''')
            c.execute('CREATE INDEX IF NOT EXISTS world_job_ready ON world_discovery_job(state,available_at,updated)')
            columns = {row[1] for row in c.execute('PRAGMA table_info(world_discovery_job)')}
            if 'acquisition' not in columns:
                c.execute("ALTER TABLE world_discovery_job ADD COLUMN acquisition TEXT NOT NULL DEFAULT 'radius-300-v1'")
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS world_job_operation ON world_discovery_job(operation) WHERE operation IS NOT NULL')
            # One durable cursor, no per-player history or unbounded region table.
            c.execute('''CREATE TABLE IF NOT EXISTS world_discovery_cursor (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                cell_x INTEGER NOT NULL, cell_y INTEGER NOT NULL)''')
            # Survives job/snapshot pruning: an uncertain generation cannot be
            # forgotten and a completed generation cannot be immediately refetched.
            c.execute('''CREATE TABLE IF NOT EXISTS world_discovery_refresh (
                base_id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE,
                generation INTEGER NOT NULL, due REAL NOT NULL,
                settled INTEGER NOT NULL CHECK(settled IN (0,1)))''')
            c.execute('''INSERT OR IGNORE INTO world_discovery_refresh
                SELECT id,id,0,updated+604800,1 FROM world_discovery_job WHERE state='COMMITTED' ''')

    def enqueue(self,demand_key,provider,revision,profile, *, acquisition='radius-300-v1',
                refresh_seconds=0, plan_only=False):
        token(demand_key);token(provider);token(profile)
        if acquisition not in ACQUISITIONS:
            raise ValueError('job_acquisition')
        if type(revision) is not int or revision<1:
            raise ValueError('job_revision')
        if type(refresh_seconds) is not int or refresh_seconds not in (0,604800):
            raise ValueError('job_refresh_interval')
        now=time.time()
        identity = [demand_key,provider,revision,profile]
        if acquisition != 'radius-300-v1':
            identity.append(acquisition)
        key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        with self.repo.transaction() as c:
            demand=c.execute('SELECT expires FROM world_discovery_demand WHERE key=? AND expires>?',
                             (demand_key,now)).fetchone()
            if not demand:
                return None
            base_key=key
            generation=0
            unsent_cancel=False
            if refresh_seconds:
                receipt=c.execute('SELECT * FROM world_discovery_refresh WHERE base_id=?',(base_key,)).fetchone()
                old=c.execute('SELECT * FROM world_discovery_job WHERE id=?',
                              (receipt['job_id'] if receipt else key,)).fetchone()
                unsent_cancel=bool(old and old['state']=='CANCELLED' and old['operation'] is None
                    and not c.execute('SELECT 1 FROM world_credit_operation WHERE account=? AND operation=?',
                                      (provider,'discovery:'+old['id'])).fetchone())
                # Legacy pre-HTTP failures could exhaust attempts and be pruned,
                # leaving an unsettled receipt forever. Every HTTP in this path
                # requires a durable ledger reservation, never pruned here.
                # Recover only this orphan, with a NEW operation; any ledger row
                # (including uncertain or settled) keeps the old quarantine.
                if (not old and receipt and not receipt['settled'] and receipt['due']==0
                        and acquisition=='geoapify-commercial-v1'
                        and not c.execute('SELECT 1 FROM world_credit_operation WHERE account=? AND operation=?',
                                          (provider,'discovery:'+receipt['job_id'])).fetchone()):
                    unsent_cancel=True
                if unsent_cancel:
                    generation=(receipt['generation'] if receipt else 0)+1
                elif receipt:
                    if not receipt['settled'] or receipt['due']>now:
                        return None
                    generation=receipt['generation']+1
                elif old:
                    if old['state']!='COMMITTED' or old['updated']+refresh_seconds>now:
                        if not plan_only:
                            if c.execute('SELECT count(*) FROM world_discovery_refresh').fetchone()[0]>=self.max_jobs:
                                return None
                            c.execute('INSERT INTO world_discovery_refresh VALUES (?,?,?,?,?)',
                                      (base_key,key,0,old['updated']+refresh_seconds,int(old['state']=='COMMITTED')))
                        return None
                    generation=1
                if generation:
                    prior=receipt['job_id'] if receipt else base_key
                    charge=c.execute('SELECT state FROM world_credit_operation WHERE account=? AND operation=?',
                                     (provider,'discovery:'+prior)).fetchone()
                    if not unsent_cancel and (not charge or charge['state'] not in ('settled','estimated')):
                        return None
                    key=hashlib.sha256(f'{base_key}:refresh:{generation}'.encode()).hexdigest()
                if not receipt and c.execute('SELECT count(*) FROM world_discovery_refresh').fetchone()[0]>=self.max_jobs:
                    return None
            # Dedup never resets a completed/uncertain operation or extends its TTL.
            if c.execute('SELECT 1 FROM world_discovery_job WHERE id=?',(key,)).fetchone():
                return key
            if c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0]>=self.max_jobs:
                return None
            if plan_only:
                return key
            c.execute('''INSERT INTO world_discovery_job
                (id,demand_key,provider,revision,profile,state,attempts,owner,lease_until,
                 available_at,expires,updated,operation,snapshot,reason,acquisition)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (key,demand_key,provider,revision,profile,'PENDING',0,None,0,now,demand['expires'],now,None,None,'',acquisition))
            if refresh_seconds:
                c.execute('INSERT OR REPLACE INTO world_discovery_refresh VALUES (?,?,?,?,?)',
                          (base_key,key,generation,0,0))
        return key

    def _recover(self,c,now):
        rows=c.execute('''SELECT * FROM world_discovery_job WHERE state IN
            ('LEASED','FETCHING','VALIDATING') AND lease_until<=? LIMIT 100''',(now,)).fetchall()
        for row in rows:
            if row['state']!='LEASED':
                state,reason='POLICY_BLOCKED','outcome_unknown'
            elif row['expires']<=now:
                state,reason='CANCELLED','demand_expired'
            elif row['attempts']>=self.max_attempts:
                state,reason='FAILED_TERMINAL','attempt_limit'
            else:
                state,reason='PENDING','lease_expired_before_http'
            c.execute('UPDATE world_discovery_job SET state=?,reason=?,owner=NULL,lease_until=0,updated=? WHERE id=?',
                      (state,reason,now,row['id']))
        c.execute('''UPDATE world_discovery_job SET state='CANCELLED',reason='demand_expired',updated=?
            WHERE expires<=? AND state IN ('PENDING','DEFERRED','RETRY_AFTER')''',(now,now))

    def claim(self,seconds=60, *, cells=None, profiles=None, acquisition=None, allow_refresh=False,provider=None):
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 1<=seconds<=120:
            raise ValueError('job_lease')
        now=time.time();owner=uuid.uuid4().hex
        clauses=[]; params=[]
        if provider is not None:
            token(provider);clauses.append('j.provider=?');params.append(provider)
        if not allow_refresh:
            clauses.append('NOT EXISTS (SELECT 1 FROM world_discovery_refresh r WHERE r.job_id=j.id AND r.generation>0)')
        if acquisition is not None:
            if acquisition not in ACQUISITIONS:
                raise ValueError('job_acquisition')
            clauses.append('j.acquisition=?')
            params.append(acquisition)
        if cells is not None:
            if not cells or len(cells)>10: raise ValueError('job_claim_scope')
            clauses.append('('+' OR '.join('(d.cell_x=? AND d.cell_y=?)' for _ in cells)+')')
            for x,y in sorted(cells): params.extend((x,y))
        if profiles is not None:
            if not profiles or len(profiles)>6: raise ValueError('job_claim_scope')
            clauses.append('j.profile IN ('+','.join('?' for _ in profiles)+')')
            params.extend(sorted(profiles))
        scope=(' AND '+' AND '.join(clauses)) if clauses else ''
        with self.repo.transaction() as c:
            self._recover(c,now)
            cursor=c.execute('SELECT cell_x,cell_y FROM world_discovery_cursor WHERE singleton=1').fetchone()
            # Rotate sectors, then oldest job within the chosen sector. Eligibility
            # excludes expired/deleted demand; hits never buy a higher priority.
            x,y=(cursor['cell_x'],cursor['cell_y']) if cursor else (-18001,-9001)
            row=c.execute('''SELECT j.*,d.cell_x,d.cell_y FROM world_discovery_job j
                JOIN world_discovery_demand d ON d.key=j.demand_key
                WHERE j.state IN ('PENDING','DEFERRED','RETRY_AFTER')
                AND j.available_at<=? AND j.expires>? AND d.expires>? AND j.attempts<?
                '''+scope+''' ORDER BY CASE WHEN d.cell_x>? OR (d.cell_x=? AND d.cell_y>?)
                    THEN 0 ELSE 1 END,d.cell_x,d.cell_y,j.updated,j.id LIMIT 1''',
                (now,now,now,self.max_attempts,*params,x,x,y)).fetchone()
            if not row:
                return None
            c.execute("UPDATE world_discovery_job SET state='LEASED',owner=?,lease_until=?,attempts=attempts+1,updated=?,reason='' WHERE id=?",
                      (owner,min(now+seconds,row['expires']),now,row['id']))
            c.execute('INSERT OR REPLACE INTO world_discovery_cursor VALUES (1,?,?)',
                      (row['cell_x'],row['cell_y']))
            return dict(c.execute('SELECT * FROM world_discovery_job WHERE id=?',(row['id'],)).fetchone())

    def transition(self,key,owner,target,*,delay=0,operation=None):
        """No refund or HTTP here. Retry scheduling is only legal before HTTP."""
        token(key);token(owner)
        if target not in STATES or type(delay) not in (int,float) or not math.isfinite(delay) or not 0<=delay<=86400:
            raise ValueError('job_transition')
        if operation is not None:token(operation)
        now=time.time()
        with self.repo.transaction() as c:
            row=c.execute('SELECT * FROM world_discovery_job WHERE id=? AND owner=? AND lease_until>? AND expires>?',
                          (key,owner,now,now)).fetchone()
            if not row:return False
            allowed={'LEASED':{'FETCHING','DEFERRED','RETRY_AFTER','POLICY_BLOCKED','CANCELLED'},
                     'FETCHING':{'VALIDATING','POLICY_BLOCKED','FAILED_TERMINAL'},
                     'VALIDATING':{'POLICY_BLOCKED','FAILED_TERMINAL'}}
            if target not in allowed.get(row['state'],set()):raise ValueError('job_transition')
            if target=='FETCHING' and not operation:raise ValueError('job_operation_required')
            retained=target in ('FETCHING','VALIDATING')
            reason='outcome_unknown' if target=='POLICY_BLOCKED' and row['state']!='LEASED' else ''
            if target in ('DEFERRED','RETRY_AFTER') and row['attempts']>=self.max_attempts:
                target='FAILED_TERMINAL';reason='attempt_limit'
            c.execute('''UPDATE world_discovery_job SET state=?,owner=?,lease_until=?,available_at=?,
                updated=?,operation=?,reason=? WHERE id=?''',
                (target,owner if retained else None,row['lease_until'] if retained else 0,now+delay,now,
                 operation if target=='FETCHING' else row['operation'],reason,key))
            return True

    def defer_admission(self,key,owner,reason,delay=60):
        """Yield before any cost reservation/HTTP without consuming a fetch attempt.

        Keep demand expiry and existing failed-attempt count. A known operation,
        changed owner, expired lease or possible HTTP prohibits this path.
        """
        token(key);token(owner)
        if (reason not in ADMISSION_DEFERRALS or type(delay) not in (int,float)
                or not math.isfinite(delay) or not 1<=delay<=300):
            raise ValueError('job_admission_deferral')
        now=time.time()
        with self.repo.transaction() as c:
            row=c.execute('''SELECT * FROM world_discovery_job WHERE id=? AND owner=?
                AND state='LEASED' AND operation IS NULL AND lease_until>? AND expires>?''',
                (key,owner,now,now)).fetchone()
            if not row:return False
            if c.execute('SELECT 1 FROM world_credit_operation WHERE account=? AND operation=?',
                         (row['provider'],'discovery:'+key)).fetchone():return False
            c.execute('''UPDATE world_discovery_job SET state='DEFERRED',owner=NULL,
                lease_until=0,attempts=max(0,attempts-1),available_at=?,updated=?,reason=?
                WHERE id=?''',(now+delay,now,reason,key))
            return True

    def acknowledge(self,key,snapshot,owner=None):
        """Ack a published snapshot; recovery does not fetch or settle credits.

        Publication must use the job id as query_key. Unknown interrupted jobs
        can be reconciled only against a matching stored receipt, not a new HTTP.
        This is not a certification of geographic completeness or a budget ack.
        """
        token(key);token(snapshot)
        now=time.time()
        with self.repo.transaction() as c:
            self._recover(c,now)
            job=c.execute('SELECT * FROM world_discovery_job WHERE id=?',(key,)).fetchone()
            if not job:return False
            if job['state']=='COMMITTED':return job['snapshot']==snapshot
            active=(job['state']=='VALIDATING' and owner is not None and job['owner']==owner and job['lease_until']>now)
            recovery=(job['state']=='POLICY_BLOCKED' and job['reason']=='outcome_unknown' and owner is None)
            if not (active or recovery):return False
            row=c.execute('SELECT * FROM world_snapshot WHERE id=? AND query_key=? AND provider=? AND profile=?',
                          (snapshot,key,job['provider'],FORMAT)).fetchone()
            if not row or len(row['payload'])>8*1024*1024:return False
            if hashlib.sha256(row['payload']).hexdigest()!=row['digest']:return False
            try:
                payload=json.loads(row['payload'])
            except (ValueError,UnicodeError):
                return False
            if not isinstance(payload,dict):return False
            if payload.get('revision')!=job['revision'] or payload.get('profile')!=job['profile']:return False
            c.execute("UPDATE world_discovery_job SET state='COMMITTED',snapshot=?,owner=NULL,lease_until=0,reason='',updated=? WHERE id=?",
                      (snapshot,now,key))
            c.execute('UPDATE world_discovery_refresh SET settled=1,due=? WHERE job_id=?',
                      (now+604800,key))
            if not c.execute('SELECT 1 FROM world_discovery_refresh WHERE job_id=?',(key,)).fetchone():
                if c.execute('SELECT count(*) FROM world_discovery_refresh').fetchone()[0]<self.max_jobs:
                    c.execute('INSERT INTO world_discovery_refresh VALUES (?,?,?,?,?)',(key,key,0,now+604800,1))
            return True

    def prune(self,limit=100):
        """Never discard unresolved operations, even after demand expiration."""
        if type(limit) is not int or not 1<=limit<=100:raise ValueError('job_prune_limit')
        with self.repo.transaction() as c:
            return c.execute('''DELETE FROM world_discovery_job WHERE id IN
                (SELECT id FROM world_discovery_job WHERE expires<=? AND
                 state IN ('COMMITTED','CANCELLED','FAILED_TERMINAL')
                 AND NOT (state='CANCELLED' AND EXISTS (SELECT 1 FROM world_discovery_refresh r
                    WHERE r.job_id=world_discovery_job.id AND r.settled=0)) LIMIT ?)''',
                 (time.time(),limit)).rowcount

    def get(self,key):
        c=self.repo.connect()
        try:
            row=c.execute('SELECT * FROM world_discovery_job WHERE id=?',(key,)).fetchone()
            return dict(row) if row else None
        finally:c.close()

    def schedule_overpass_retry(self,key,delay=3600):
        """Read-only remote service: count the attempt, back off; never retry paid requests here."""
        with self.repo.transaction() as c:
            row=c.execute('SELECT * FROM world_discovery_job WHERE id=?',(key,)).fetchone()
            if not row or row['acquisition']!='overpass-bbox-geom-v1' or row['state']!='POLICY_BLOCKED':return False
            operation=c.execute('SELECT state FROM world_credit_operation WHERE account=? AND operation=?',
                                (row['provider'],'discovery:'+key)).fetchone()
            if not operation or operation['state']!='settled':return False
            c.execute("UPDATE world_discovery_job SET state='FAILED_TERMINAL',reason='overpass_backoff' WHERE id=?",(key,))
            c.execute('UPDATE world_discovery_refresh SET settled=1,due=? WHERE job_id=?',(time.time()+delay,key))
            return True
