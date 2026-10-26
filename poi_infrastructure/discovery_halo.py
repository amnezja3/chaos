"""One bounded ring around direct demand; never expand from generated demand."""
from contextlib import closing
import time

from .discovery_queue import DemandQueue
from .world_contract import ContractError


def cells(repo, limit=100, halo=False):
    with closing(repo.connect()) as c:
        migrated = 'origin' in {r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')}
        if halo and not migrated:
            raise ContractError('halo_schema_required')
        origin = "CASE WHEN origin='direct' THEN 0 ELSE 1 END" if migrated else '0'
        rows = c.execute('SELECT cell_x,cell_y,min('+origin+') tier FROM world_discovery_demand '
            'WHERE expires>?'+(" AND origin='direct'" if migrated and not halo else '')+
            ' GROUP BY cell_x,cell_y ORDER BY tier,max(last_seen) DESC LIMIT ?',
            (time.time(),limit)).fetchall()
        return [(tuple(r[:2]),r['tier']) for r in rows]


def expand(repo):
    queue = DemandQueue(repo)
    with closing(repo.connect()) as c:
        if 'origin' not in {r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')}:
            raise ContractError('halo_schema_required')
        seeds = c.execute("SELECT cell_x,cell_y,min(expires) expires FROM world_discovery_demand "
            "WHERE origin='direct' AND expires>? GROUP BY cell_x,cell_y ORDER BY max(last_seen) DESC LIMIT 100",
            (time.time(),)).fetchall()
        occupied = {(r[0],r[1]) for r in c.execute('SELECT DISTINCT cell_x,cell_y FROM world_discovery_demand')}
        if c.execute("SELECT count(*) FROM world_discovery_demand WHERE origin='halo'").fetchone()[0]>=480:
            return 0
    added = 0
    for seed in seeds:
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            x,y = seed['cell_x']+dx,seed['cell_y']+dy
            if not (-18000<=x<18000 and -9000<=y<9000):continue
            if (x,y) in occupied:continue
            occupied.add((x,y))
            if queue.record((x+.5)/100,(y+.5)/100,origin='halo',expires_at=seed['expires']):
                added += 1
                if added>=8:return added
    return added


def tasks_for(entries, cursor):
    """Rotate within tiers; pending direct work always precedes halo work."""
    result=[]
    for tier in (0,1):
        tasks=[(cell,profile) for cell,kind in entries if kind==tier
               for profile in ('roads','waterways','inland_water','coastline','poi')]
        if tasks:
            start=cursor%len(tasks)
            result.extend(tasks[start:]+tasks[:start])
    return result
