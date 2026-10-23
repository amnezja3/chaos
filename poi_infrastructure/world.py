"""Durable immutable OSM snapshots. Exact evidence is never spatial coverage.

Stored alongside the 158 coordinator so lease fencing and publication share
one SQLite transaction. No player data or mutated marker objects belong here.
"""
import hashlib
import json
import math
import time

from .service import Config, POIError, validate


class WorldRepository:
    VERSION = 1

    def __init__(self, repository, max_bytes=128 * 1024 * 1024, max_snapshots=5000):
        self.repo = repository
        self.max_bytes = max_bytes
        self.max_snapshots = max_snapshots

    def initialize(self):
        self.repo.initialize()
        with self.repo.transaction() as c:
            c.execute('CREATE TABLE IF NOT EXISTS world_schema (version INTEGER NOT NULL)')
            row = c.execute('SELECT version FROM world_schema').fetchone()
            if row and row[0] not in (self.VERSION, 2):
                raise POIError('world_schema_version')
            c.execute('''CREATE TABLE IF NOT EXISTS world_snapshot (
                id TEXT PRIMARY KEY, query_key TEXT NOT NULL, provider TEXT NOT NULL,
                fetched REAL NOT NULL, profile TEXT NOT NULL,
                payload BLOB NOT NULL, digest TEXT NOT NULL, bytes INTEGER NOT NULL,
                fresh_until REAL NOT NULL, usable_until REAL NOT NULL)''')
            c.execute('CREATE INDEX IF NOT EXISTS world_query ON world_snapshot(query_key, fetched DESC)')
            c.execute('''CREATE TABLE IF NOT EXISTS world_member (
                snapshot_id TEXT NOT NULL REFERENCES world_snapshot(id) ON DELETE CASCADE,
                osm_type TEXT NOT NULL, osm_id INTEGER NOT NULL, ordinal INTEGER NOT NULL,
                element BLOB NOT NULL, PRIMARY KEY(snapshot_id, osm_type, osm_id))''')
            # No center-only response is allowed in this table. Spatial evidence
            # will require its own verified profile before publication.
            c.execute('''CREATE TABLE IF NOT EXISTS world_coverage (
                cell TEXT NOT NULL, profile TEXT NOT NULL, snapshot_id TEXT NOT NULL
                REFERENCES world_snapshot(id) ON DELETE CASCADE,
                bounds TEXT NOT NULL, PRIMARY KEY(cell, profile))''')
            if not row:
                c.execute('INSERT INTO world_schema VALUES (?)', (self.VERSION,))

    def publish_exact(self, key, owner, data, provider, fresh_ttl, usable_ttl,
                      config=None, fetched=None):
        return self._publish(key, owner, data, provider, fresh_ttl, usable_ttl,
                             config, fetched, 'exact-center-v1')

    def publish_geometry(self, key, owner, data, provider, fresh_ttl, usable_ttl,
                         lat, lon, radius, filters, config=None, fetched=None):
        """Full-closure storage used only by explicitly enabled wide fetch."""
        from .geometry import CoveredGeometry
        coverage = CoveredGeometry(data, lat, lon, radius, filters)
        # Check dependencies even for objects outside a particular scan. This
        # rejects incomplete closure before recording any area evidence.
        for element in coverage.snapshot.elements.values():
            coverage.snapshot._lines(element)
        bounds = dict(lat=lat, lon=lon, radius=radius, filters=list(filters))
        return self._publish(key, owner, data, provider, fresh_ttl, usable_ttl,
                             config, fetched, coverage.PROFILE, bounds)

    def _publish(self, key, owner, data, provider, fresh_ttl, usable_ttl,
                 config, fetched, profile, bounds=None):
        """Publish only under the still-valid 158 query lease; all or nothing."""
        config = config or Config()
        validate(data, config)
        now = time.time()
        fetched = now if fetched is None else fetched
        if (not all(math.isfinite(v) for v in (fetched, fresh_ttl, usable_ttl))
                or not 0 <= fresh_ttl <= usable_ttl or fetched > now):
            raise POIError('world_invalid_time')
        raw = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > min(config.max_response, self.max_bytes):
            raise POIError('world_capacity')
        identities = [(e['type'], e['id']) for e in data['elements']]
        if len(identities) != len(set(identities)):
            raise POIError('world_duplicate_identity')
        digest = hashlib.sha256(raw).hexdigest()
        snapshot = hashlib.sha256(f'{key}:{fetched}:{digest}:{profile}:{json.dumps(bounds,sort_keys=True)}'.encode()).hexdigest()
        with self.repo.transaction() as c:
            if not c.execute('SELECT 1 FROM leases WHERE key=? AND owner=? AND until_at>?',
                             (key, owner, time.time())).fetchone():
                return False
            total, count = c.execute('SELECT coalesce(sum(bytes),0),count(*) FROM world_snapshot').fetchone()
            if c.execute('SELECT 1 FROM world_snapshot WHERE id=?', (snapshot,)).fetchone():
                return True
            # Capacity is explicit; no implicit loss of the growing world.
            if total + len(raw) > self.max_bytes or count >= self.max_snapshots:
                raise POIError('world_capacity')
            c.execute('INSERT INTO world_snapshot VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (snapshot, key, provider, fetched, profile, raw,
                       digest, len(raw), fetched + fresh_ttl, fetched + usable_ttl))
            c.executemany('INSERT INTO world_member(snapshot_id,osm_type,osm_id,ordinal,element) VALUES (?,?,?,?,?)',
                          [(snapshot, e['type'], e['id'], i,
                            json.dumps(e, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
                           for i, e in enumerate(data['elements'])])
            if bounds is not None:
                c.execute('INSERT OR REPLACE INTO world_coverage VALUES (?,?,?,?)',
                          (key, profile, snapshot, json.dumps(bounds, sort_keys=True, allow_nan=False)))
        return True

    def read_exact(self, key, allow_stale=False, config=None):
        c = self.repo.connect()
        try:
            row = c.execute("SELECT * FROM world_snapshot WHERE query_key=? AND profile='exact-center-v1' ORDER BY fetched DESC LIMIT 1",
                            (key,)).fetchone()
        finally:
            c.close()
        if not row:
            return None
        now = time.time()
        if not row['fetched'] <= now <= row['usable_until' if allow_stale else 'fresh_until']:
            return None
        raw = row['payload']
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['digest']:
            return None
        try:
            data = validate(json.loads(raw), config or Config())
        except (ValueError, UnicodeError, POIError):
            return None
        return data

    def read_geometry(self, lat, lon, radius, filters, allow_stale=False, config=None):
        """Experimental read; unsupported or incomplete geometry is a miss."""
        from .geometry import CoveredGeometry, UncertifiedGeometry
        c = self.repo.connect()
        try:
            rows = c.execute('''SELECT s.id, s.fresh_until, s.usable_until, c.bounds FROM world_coverage c
                JOIN world_snapshot s ON s.id=c.snapshot_id WHERE c.profile=?
                AND s.profile=c.profile AND s.fetched<=? AND s.usable_until>=?
                ORDER BY s.fetched DESC''', (CoveredGeometry.PROFILE,time.time(),time.time())).fetchall()
        finally:
            c.close()
        for row in rows:
            expires = row['usable_until' if allow_stale else 'fresh_until']
            if time.time() > expires:
                continue
            try:
                bounds = json.loads(row['bounds'])
                # Reject non-covering candidates before loading large payloads.
                CoveredGeometry({'elements':[]}, **bounds).select(lat,lon,radius,filters)
            except (UncertifiedGeometry,ValueError,TypeError,KeyError):
                continue
            c = self.repo.connect()
            try:
                row = c.execute('SELECT * FROM world_snapshot WHERE id=?',(row['id'],)).fetchone()
            finally:
                c.close()
            if row is None:
                continue
            raw = row['payload']
            if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['digest']:
                continue
            try:
                covered = CoveredGeometry(json.loads(raw), **bounds)
                result = covered.select(lat,lon,radius,filters)
                validate(result, config or Config())
            except (UncertifiedGeometry, ValueError, TypeError, KeyError, POIError):
                continue
            if time.time() <= expires:
                return result
        return None

    def prune_expired(self, limit=100):
        """Bounded cleanup; membership and coverage are removed atomically by FK."""
        if type(limit) is not int or not 1 <= limit <= 500:
            raise POIError('world_cleanup_limit')
        with self.repo.transaction() as c:
            rows=c.execute('SELECT id FROM world_snapshot WHERE usable_until<? ORDER BY usable_until LIMIT ?',
                           (time.time(),limit)).fetchall()
            c.executemany('DELETE FROM world_snapshot WHERE id=?',[(r[0],) for r in rows])
        return len(rows)

    def status(self):
        c = self.repo.connect()
        try:
            count, size = c.execute('SELECT count(*),coalesce(sum(bytes),0) FROM world_snapshot').fetchone()
            return dict(snapshots=count, payload_bytes=size,
                        members=c.execute('SELECT count(*) FROM world_member').fetchone()[0],
                        certified_cells=0,
                        experimental_coverage=c.execute('SELECT count(*) FROM world_coverage').fetchone()[0])
        finally:
            c.close()
