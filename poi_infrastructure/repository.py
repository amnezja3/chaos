"""Short SQLite transactions; fencing applies to writes and lease release."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


class Repository:
    def __init__(self, path, max_bytes=64 * 1024 * 1024, max_entries=2000):
        self.path = str(path)
        self.max_bytes = max_bytes
        self.max_entries = max_entries

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=.5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout=500')
        conn.execute('PRAGMA wal_autocheckpoint=64')
        conn.execute('PRAGMA journal_size_limit=1048576')
        return conn

    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        c = self.connect()
        try:
            if (c.execute('PRAGMA user_version').fetchone()[0] == 1
                    and c.execute('PRAGMA journal_mode').fetchone()[0].lower() == 'wal'):
                return
        finally:
            c.close()
        with self.transaction() as c:
            version = c.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('poi_schema_version')
            c.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload BLOB NOT NULL, digest TEXT NOT NULL, fetched REAL NOT NULL, bytes INTEGER NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS cache_age ON cache(fetched)')
            c.execute('CREATE TABLE IF NOT EXISTS leases (key TEXT PRIMARY KEY, owner TEXT NOT NULL, until_at REAL NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS providers (name TEXT PRIMARY KEY, failures INTEGER NOT NULL, until_at REAL NOT NULL)')
            c.execute('PRAGMA user_version=1')
        c = self.connect()
        try:
            c.execute('PRAGMA journal_mode=WAL')
            # Physical main-file limit; WAL bounded operationally by short readers
            # and checkpoints. No VACUUM in request handling.
            page_size = c.execute('PRAGMA page_size').fetchone()[0]
            c.execute(f'PRAGMA max_page_count={max(256, self.max_bytes * 2 // page_size)}')
        finally:
            c.close()

    @contextmanager
    def transaction(self):
        wal = Path(self.path + '-wal')
        if wal.exists() and wal.stat().st_size > self.max_bytes + 8 * 1024 * 1024:
            raise sqlite3.OperationalError('poi_wal_capacity')
        c = self.connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            page_size = c.execute('PRAGMA page_size').fetchone()[0]
            c.execute(f'PRAGMA max_page_count={max(256, self.max_bytes * 2 // page_size)}')
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def read(self, key, ttl):
        c = self.connect()
        try:
            row = c.execute('SELECT * FROM cache WHERE key=?', (key,)).fetchone()
        finally:
            c.close()
        if row is None or not 0 <= time.time() - row['fetched'] <= ttl:
            return None
        raw = row['payload']
        if len(raw) > self.max_bytes or len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['digest']:
            return None
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            return None

    def acquire(self, key, seconds):
        now = time.time()
        owner = uuid.uuid4().hex
        with self.transaction() as c:
            c.execute('DELETE FROM leases WHERE key=? AND until_at<=?', (key, now))
            cur = c.execute('INSERT OR IGNORE INTO leases VALUES (?,?,?)', (key, owner, now + seconds))
            return owner if cur.rowcount else None

    def owns(self, key, owner):
        c = self.connect()
        try:
            return bool(c.execute('SELECT 1 FROM leases WHERE key=? AND owner=? AND until_at>?', (key, owner, time.time())).fetchone())
        finally:
            c.close()

    def release(self, key, owner):
        with self.transaction() as c:
            c.execute('DELETE FROM leases WHERE key=? AND owner=?', (key, owner))

    def write(self, key, owner, data, stale_ttl):
        raw = json.dumps(data, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > self.max_bytes:
            return False
        now = time.time()
        with self.transaction() as c:
            if not c.execute('SELECT 1 FROM leases WHERE key=? AND owner=? AND until_at>?', (key, owner, now)).fetchone():
                return False
            c.execute('DELETE FROM leases WHERE until_at<=?', (now,))
            # Bounded cache size bounds this maintenance transaction as well.
            evicted = c.execute('DELETE FROM cache WHERE fetched<? AND key NOT IN (SELECT key FROM leases)', (now - stale_ttl,)).rowcount
            total, count = c.execute('SELECT coalesce(sum(bytes),0),count(*) FROM cache WHERE key<>?', (key,)).fetchone()
            for row in c.execute('SELECT key,bytes FROM cache WHERE key<>? AND key NOT IN (SELECT key FROM leases) ORDER BY fetched', (key,)).fetchall():
                if total + len(raw) <= self.max_bytes and count < self.max_entries:
                    break
                c.execute('DELETE FROM cache WHERE key=?', (row['key'],))
                evicted += 1
                total -= row['bytes']
                count -= 1
            if total + len(raw) > self.max_bytes or count >= self.max_entries:
                return False
            c.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?)', (key, raw, hashlib.sha256(raw).hexdigest(), now, len(raw)))
            if evicted:
                from . import logger
                logger().info('poi_cache %s', json.dumps({'evictions': evicted}))
            return True

    def allowed(self, group):
        c = self.connect()
        try:
            row = c.execute('SELECT until_at FROM providers WHERE name=?', (group,)).fetchone()
            return row is None or row[0] <= time.time()
        finally:
            c.close()

    def outcome(self, group, success, retry_after=0):
        with self.transaction() as c:
            row = c.execute('SELECT failures FROM providers WHERE name=?', (group,)).fetchone()
            failures = 0 if success else (row[0] if row else 0) + 1
            cooldown = max(retry_after, min(120, 2 ** min(failures, 7)) if failures >= 3 else 0)
            c.execute('INSERT OR REPLACE INTO providers VALUES (?,?,?)', (group, failures, time.time() + cooldown))
