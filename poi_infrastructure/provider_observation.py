"""Dated manual provider balance observations, never ledger settlements."""
from contextlib import closing
import math
from pathlib import Path
import sqlite3
import time


def initialize(repo):
    with repo.transaction() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS world_provider_observation (
            account TEXT PRIMARY KEY, revision INTEGER NOT NULL,
            credit_limit INTEGER NOT NULL, used INTEGER NOT NULL,
            period_start REAL NOT NULL, period_end REAL NOT NULL,
            observed_at REAL NOT NULL, recorded_at REAL NOT NULL)''')


def save(repo,account,revision,credit_limit,used,period_start,period_end,observed_at):
    now=time.time()
    if (account not in ('maplark','geoapify') or type(revision) is not int or revision<0
        or any(type(v) is not int or not 0<=v<=10**9 for v in (credit_limit,used)) or credit_limit==0
        or any(type(v) not in (int,float) or not math.isfinite(v) for v in (period_start,period_end,observed_at))
        or not 0<period_start<=observed_at<=now+60 or not observed_at<period_end
        or period_end-period_start>370*86400):
        raise ValueError('invalid_provider_observation')
    with repo.transaction() as c:
        row=c.execute('SELECT revision FROM world_provider_observation WHERE account=?',(account,)).fetchone()
        if (row[0] if row else 0)!=revision: raise ValueError('observation_revision_conflict')
        c.execute('INSERT OR REPLACE INTO world_provider_observation VALUES (?,?,?,?,?,?,?,?)',
                  (account,revision+1,credit_limit,used,period_start,period_end,observed_at,now))
    return read(repo,account)


def read(repo,account):
    with closing(sqlite3.connect(Path(repo.path).resolve().as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='world_provider_observation'").fetchone(): return None
        row=c.execute('SELECT * FROM world_provider_observation WHERE account=?',(account,)).fetchone()
    if not row:return None
    return dict(row,source='manual_provider_panel',remaining=max(0,row['credit_limit']-row['used']),
                stale=time.time()-row['observed_at']>86400 or time.time()>=row['period_end'])
