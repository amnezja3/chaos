"""Bounded anonymous demand queue. Passive collection never performs HTTP.

Cells are presentation/dedup keys, NOT a proof of geographic coverage.
No user identifiers, exact positions, routes, or recursively generated neighbors.
"""
import hashlib
import math
import time

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

    def record(self,lon,lat,layers=LAYERS):
        lon,lat=position((lon,lat))
        layers=frozenset(layers)
        if not layers or not layers<=LAYERS:
            raise ContractError('demand_layers')
        # Clamp the endpoint to the last valid half-open cell.
        x=min(17999,math.floor(lon*100)); y=min(8999,math.floor(lat*100))
        now=time.time()
        written=0
        with self.repo.transaction() as c:
            # Bound maintenance as well as queue size; no eviction of live demand.
            c.execute('DELETE FROM world_discovery_demand WHERE key IN (SELECT key FROM world_discovery_demand WHERE expires<=? LIMIT 100)',(now,))
            count=c.execute('SELECT count(*) FROM world_discovery_demand').fetchone()[0]
            for layer in sorted(layers):
                key=hashlib.sha256(f'{SCHEMA_VERSION}:{layer}:{x}:{y}'.encode()).hexdigest()
                row=c.execute('SELECT 1 FROM world_discovery_demand WHERE key=?',(key,)).fetchone()
                if row:
                    c.execute('''UPDATE world_discovery_demand SET hits=min(hits+1,1000000),
                        last_seen=?,expires=? WHERE key=?''',(now,now+self.ttl,key))
                elif count<self.max_entries:
                    c.execute('INSERT INTO world_discovery_demand VALUES (?,?,?,?,?,?,?,?,?,?)',
                              (key,x,y,layer,SCHEMA_VERSION,1,now,now,now+self.ttl,'PENDING'))
                    count+=1
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
