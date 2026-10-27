"""Expiring collector liveness; separate from job success and provider health."""
from contextlib import closing
import time
import uuid


TABLE = 'world_worker_heartbeat'


def initialize(repo):
    with repo.transaction() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS world_worker_heartbeat (
            id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT NOT NULL,
            observed REAL NOT NULL, expires REAL NOT NULL, state TEXT NOT NULL)''')


def inspect(connection, now=None):
    now = time.time() if now is None else now
    prepared = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    result = dict(prepared=bool(prepared), status='unknown', reason='schema_missing',
                  observed_at=None, age_seconds=None, expires_at=None)
    if not prepared:
        return result
    row = connection.execute('SELECT observed,expires,state FROM world_worker_heartbeat WHERE id=1').fetchone()
    if row is None:
        return dict(result, reason='not_observed')
    observed, expires, state = row
    result.update(observed_at=observed, expires_at=expires,
                  age_seconds=round(max(0, now-observed), 1))
    if observed > now or expires <= now:
        return dict(result, reason='clock_skew' if observed > now else 'expired')
    if state not in ('running', 'waiting', 'stopped', 'error'):
        return dict(result, reason='invalid_state')
    return dict(result, status=state, reason='recent_heartbeat')


class Heartbeat:
    """Only an explicit worker execution writes; no implicit schema migration.

    The newest registered worker owns the record. An older process cannot renew
    or mark its successor stopped. This is liveness, not a scheduling lease.
    """
    def __init__(self, repo, interval=30):
        self.repo = repo
        self.owner = uuid.uuid4().hex
        self.ttl = max(120, interval + 110)

    def start(self):
        try:
            with closing(self.repo.connect()) as c:
                if not inspect(c)['prepared']:
                    return False
            now = time.time()
            with self.repo.transaction() as c:
                c.execute('INSERT OR REPLACE INTO world_worker_heartbeat VALUES (1,?,?,?,?)',
                          (self.owner, now, now+self.ttl, 'running'))
            return True
        except Exception:
            return False

    def pulse(self, state):
        if state not in ('running', 'waiting', 'stopped', 'error'):
            raise ValueError('heartbeat_state')
        try:
            now = time.time()
            with self.repo.transaction() as c:
                return c.execute('''UPDATE world_worker_heartbeat SET observed=?,expires=?,state=?
                    WHERE id=1 AND owner=?''', (now, now+self.ttl, state, self.owner)).rowcount == 1
        except Exception:
            # Telemetry failure must not interrupt collection or weaken its leases.
            return False
