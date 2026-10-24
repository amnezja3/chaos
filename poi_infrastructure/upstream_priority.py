"""Cross-process admission using the existing leases table, no new HTTP slots.

Waiting live callers precede background admission. In-flight requests keep their
slot until the existing bounded transport finishes. Tickets contain no user data.
"""
import time
import uuid


class UpstreamPriority:
    PREFIX='@live-wait:'

    def __init__(self,repo):
        self.repo=repo

    def register(self):
        ticket=uuid.uuid4().hex
        with self.repo.transaction() as c:
            now=time.time()
            c.execute("DELETE FROM leases WHERE key LIKE '@live-wait:%' AND until_at<=?",(now,))
            if c.execute("SELECT count(*) FROM leases WHERE key LIKE '@live-wait:%'").fetchone()[0]>=256:
                return None
            c.execute('INSERT INTO leases VALUES (?,?,?)',(self.PREFIX+ticket,ticket,now+10))
        return ticket

    def cancel(self,ticket):
        if ticket:self.repo.release(self.PREFIX+ticket,ticket)

    def acquire(self,*,lane,ticket=None,group='api.maplark.com'):
        if lane not in ('live','background'):raise ValueError('priority_lane')
        owner=uuid.uuid4().hex
        with self.repo.transaction() as c:
            now=time.time()
            first=c.execute("SELECT owner FROM leases WHERE key LIKE '@live-wait:%' AND until_at>? ORDER BY until_at,key LIMIT 1",(now,)).fetchone()
            if lane=='background' and first:return None
            if lane=='live' and (not ticket or not first or first['owner']!=ticket):return None
            if c.execute("SELECT 1 FROM leases WHERE key='@upstream' AND until_at>?",(now,)).fetchone():return None
            circuit=c.execute('SELECT failures,until_at FROM providers WHERE name=?',(group,)).fetchone()
            if circuit and circuit['until_at']>now:return None
            c.execute("DELETE FROM leases WHERE key='@upstream' AND until_at<=?",(now,))
            c.execute('INSERT INTO leases VALUES (?,?,?)',('@upstream',owner,now+42))
            if circuit and circuit['failures'] and 0<circuit['until_at']<=now:
                c.execute('INSERT OR REPLACE INTO leases VALUES (?,?,?)',('@probe:'+group,owner,now+42))
            if ticket:c.execute('DELETE FROM leases WHERE key=? AND owner=?',(self.PREFIX+ticket,ticket))
            return owner
