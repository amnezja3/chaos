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
            c.execute('CREATE UNIQUE INDEX IF NOT EXISTS world_job_operation ON world_discovery_job(operation) WHERE operation IS NOT NULL')
            # One durable cursor, no per-player history or unbounded region table.
            c.execute('''CREATE TABLE IF NOT EXISTS world_discovery_cursor (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                cell_x INTEGER NOT NULL, cell_y INTEGER NOT NULL)''')

    def enqueue(self,demand_key,provider,revision,profile):
        token(demand_key);token(provider);token(profile)
        if type(revision) is not int or revision<1:
            raise ValueError('job_revision')
        now=time.time()
        key=hashlib.sha256(json.dumps([demand_key,provider,revision,profile]).encode()).hexdigest()
        with self.repo.transaction() as c:
            demand=c.execute('SELECT expires FROM world_discovery_demand WHERE key=? AND expires>?',
                             (demand_key,now)).fetchone()
            if not demand:
                return None
            # Dedup never resets a completed/uncertain operation or extends its TTL.
            if c.execute('SELECT 1 FROM world_discovery_job WHERE id=?',(key,)).fetchone():
                return key
            if c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0]>=self.max_jobs:
                return None
            c.execute('INSERT INTO world_discovery_job VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (key,demand_key,provider,revision,profile,'PENDING',0,None,0,now,demand['expires'],now,None,None,''))
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

    def claim(self,seconds=60):
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 1<=seconds<=120:
            raise ValueError('job_lease')
        now=time.time();owner=uuid.uuid4().hex
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
                ORDER BY CASE WHEN d.cell_x>? OR (d.cell_x=? AND d.cell_y>?)
                    THEN 0 ELSE 1 END,d.cell_x,d.cell_y,j.updated,j.id LIMIT 1''',
                (now,now,now,self.max_attempts,x,x,y)).fetchone()
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
            return True

    def prune(self,limit=100):
        """Never discard unresolved operations, even after demand expiration."""
        if type(limit) is not int or not 1<=limit<=100:raise ValueError('job_prune_limit')
        with self.repo.transaction() as c:
            return c.execute('''DELETE FROM world_discovery_job WHERE id IN
                (SELECT id FROM world_discovery_job WHERE expires<=? AND
                 state IN ('COMMITTED','CANCELLED','FAILED_TERMINAL') LIMIT ?)''',
                 (time.time(),limit)).rowcount

    def get(self,key):
        c=self.repo.connect()
        try:
            row=c.execute('SELECT * FROM world_discovery_job WHERE id=?',(key,)).fetchone()
            return dict(row) if row else None
        finally:c.close()
