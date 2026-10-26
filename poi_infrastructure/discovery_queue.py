"""Bounded anonymous demand queue. Passive collection never performs HTTP.

Cells are presentation/dedup keys, NOT a proof of geographic coverage.
No user identifiers, exact positions, routes, or recursively generated neighbors.
"""
import hashlib
import math
import time
from contextlib import closing

from .world_contract import LAYERS, SCHEMA_VERSION, position, ContractError


class DemandQueue:
    def __init__(self,repo,max_entries=2000,ttl=86400):
        if type(max_entries) is not int or not 1<=max_entries<=10000 or not 60<=ttl<=86400:
            raise ContractError('demand_limits')
        self.repo=repo
        self.max_entries=max_entries
        self.ttl=ttl

    def initialize(self):
        self.repo.initialize()
        with self.repo.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS world_discovery_demand (
                key TEXT PRIMARY KEY, cell_x INTEGER NOT NULL, cell_y INTEGER NOT NULL,
                layer TEXT NOT NULL, contract TEXT NOT NULL,
                hits INTEGER NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
                expires REAL NOT NULL, state TEXT NOT NULL CHECK(state='PENDING'))''')
            c.execute('CREATE INDEX IF NOT EXISTS world_demand_expiry ON world_discovery_demand(expires)')
            columns = {r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')}
            if 'origin' not in columns:
                c.execute("ALTER TABLE world_discovery_demand ADD COLUMN origin TEXT NOT NULL DEFAULT 'direct'")

    def record(self,lon,lat,layers=LAYERS, *, min_interval=0, origin='direct', expires_at=None):
        lon,lat=position((lon,lat))
        layers=frozenset(layers)
        if not layers or not layers<=LAYERS:
            raise ContractError('demand_layers')
        # Clamp the endpoint to the last valid half-open cell.
        x=min(17999,math.floor(lon*100)); y=min(8999,math.floor(lat*100))
        now=time.time()
        if origin not in ('direct','halo') or type(min_interval) is not int or not 0<=min_interval<=3600:
            raise ContractError('demand_origin_or_interval')
        if expires_at is not None and (type(expires_at) not in (int,float) or not math.isfinite(expires_at)):
            raise ContractError('demand_expiry')
        expires = now+self.ttl if expires_at is None else min(now+self.ttl,expires_at)
        if not math.isfinite(expires) or expires<=now: return 0
        with closing(self.repo.connect()) as c:
            has_origin = 'origin' in {r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')}
            if origin=='halo' and not has_origin:
                raise ContractError('halo_schema_required')
            if min_interval:
                recent = c.execute('SELECT layer,last_seen,expires'+(',origin' if has_origin else '')+
                    ' FROM world_discovery_demand WHERE cell_x=? AND cell_y=?',(x,y)).fetchall()
                if all(any(r['layer']==layer and r['expires']>now and r['last_seen']>now-min_interval
                           and (not has_origin or r['origin']=='direct' or origin=='halo') for r in recent) for layer in layers):
                    return 0
        written=0
        with self.repo.transaction() as c:
            # Bound maintenance as well as queue size; no eviction of live demand.
            c.execute('DELETE FROM world_discovery_demand WHERE key IN (SELECT key FROM world_discovery_demand WHERE expires<=? LIMIT 100)',(now,))
            count=c.execute('SELECT count(*) FROM world_discovery_demand').fetchone()[0]
            halo_count = c.execute("SELECT count(*) FROM world_discovery_demand WHERE origin='halo'").fetchone()[0] if has_origin else 0
            for layer in sorted(layers):
                key=hashlib.sha256(f'{SCHEMA_VERSION}:{layer}:{x}:{y}'.encode()).hexdigest()
                row=c.execute('SELECT last_seen,expires'+(',origin' if has_origin else '')+' FROM world_discovery_demand WHERE key=?',(key,)).fetchone()
                if row:
                    if origin=='halo': continue  # Never renew or demote direct demand.
                    if min_interval and row['last_seen']>now-min_interval and row['expires']>now and (not has_origin or row['origin']=='direct'):
                        continue
                    c.execute('''UPDATE world_discovery_demand SET hits=min(hits+1,1000000),
                        last_seen=?,expires=?'''+(",origin='direct'" if has_origin else '')+' WHERE key=?',(now,expires,key))
                elif count<self.max_entries:
                    if origin=='halo' and halo_count>=min(480,self.max_entries//4):continue
                    c.execute('INSERT INTO world_discovery_demand (key,cell_x,cell_y,layer,contract,hits,first_seen,last_seen,expires,state'+
                        (',origin' if has_origin else '')+') VALUES (?,?,?,?,?,?,?,?,?,?'+(',?' if has_origin else '')+')',
                        (key,x,y,layer,SCHEMA_VERSION,1,now,now,expires,'PENDING')+((origin,) if has_origin else ()))
                    count+=1
                    if origin=='halo':halo_count+=1
                else:
                    continue
                written+=1
        return written

    def summary(self):
        c=self.repo.connect()
        try:
            exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='world_discovery_demand'").fetchone()
            if not exists:
                return dict(prepared=False,pending=0,layers={},cells=[])
            now=time.time()
            rows=c.execute('SELECT layer,count(*) n FROM world_discovery_demand WHERE expires>? GROUP BY layer',(now,)).fetchall()
            # No timestamps, per-account data or individual scan coordinates in UI.
            cells=c.execute('''SELECT cell_x,cell_y,count(*) layers,sum(hits) hits
                FROM world_discovery_demand WHERE expires>? GROUP BY cell_x,cell_y
                ORDER BY max(last_seen) DESC LIMIT 100''',(now,)).fetchall()
            return dict(prepared=True,pending=sum(r['n'] for r in rows),
                        layers={r['layer']:r['n'] for r in rows},cells=[dict(r) for r in cells])
        finally:
            c.close()

    def prune(self,limit=100):
        if type(limit) is not int or not 1<=limit<=500:
            raise ContractError('demand_prune_limit')
        with self.repo.transaction() as c:
            return c.execute('''DELETE FROM world_discovery_demand WHERE key IN
                (SELECT key FROM world_discovery_demand WHERE expires<=? LIMIT ?)''',(time.time(),limit)).rowcount
