"""Canonical observations in the existing world snapshot/member store.

Explicit offline schema migration only. No network, gameplay routing, coverage
certification or automatic provider storage permission is introduced here.
Spatial inspection is not an answer to a complete gameplay scan.
"""
from dataclasses import asdict
import hashlib
import json
import math
import time

from .world import WorldRepository
from .world_contract import (Geometry, Provenance, ProviderBatch, WorldObject,
                             ContractError, LAYERS, SCHEMA_VERSION, position)
from .service import POIError


LAYER_BITS = {name: 1 << i for i, name in enumerate(sorted(LAYERS))}
FORMAT = 'canonical-observations-v1'


def encode_object(obj):
    raw=dict(identity=obj.identity, external_id=obj.external_id,
                osm_type=obj.osm_type, osm_id=obj.osm_id, tags=dict(obj.tags),
                geometry=obj.geometry.geojson() if obj.geometry else None,
                marker=obj.marker, marker_method=obj.marker_method,
                provenance=asdict(obj.provenance), ordinal=obj.ordinal)
    if obj.land_water_origin is not None:raw['land_water_origin']=asdict(obj.land_water_origin)
    return raw


def decode_object(raw):
    value = dict(raw)
    identity = value.pop('identity')
    value['provenance'] = Provenance(**value['provenance'])
    value['geometry'] = Geometry.parse(value['geometry']) if value['geometry'] else None
    if value.get('land_water_origin') is not None:
        from .world_contract import LandWaterOrigin
        origin=dict(value['land_water_origin'])
        origin['bounds']=tuple(origin['bounds']);origin['dependencies']=tuple(origin['dependencies'])
        value['land_water_origin']=LandWaterOrigin(**origin)
    obj = WorldObject.create(**value)
    if obj.identity != identity:
        raise ContractError('stored_identity_mismatch')
    return obj


def pack(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


class CanonicalWorldRepository(WorldRepository):
    def initialize_canonical(self):
        """Explicit additive v2 migration; preserve every legacy member/value."""
        super().initialize()
        with self.repo.transaction() as c:
            version = c.execute('SELECT version FROM world_schema').fetchone()[0]
            if version == 2:
                return False
            c.execute('''CREATE TABLE world_member_v2 (
                snapshot_id TEXT NOT NULL REFERENCES world_snapshot(id) ON DELETE CASCADE,
                osm_type TEXT, osm_id INTEGER, ordinal INTEGER NOT NULL,
                element BLOB NOT NULL, identity TEXT, layer_mask INTEGER NOT NULL DEFAULT 0,
                west REAL, south REAL, east REAL, north REAL,
                spatial_valid INTEGER NOT NULL DEFAULT 0, element_digest TEXT,
                PRIMARY KEY(snapshot_id, osm_type, osm_id),
                UNIQUE(snapshot_id, identity))''')
            c.execute('''INSERT INTO world_member_v2(snapshot_id,osm_type,osm_id,ordinal,element)
                         SELECT snapshot_id,osm_type,osm_id,ordinal,element FROM world_member''')
            c.execute('DROP TABLE world_member')
            c.execute('ALTER TABLE world_member_v2 RENAME TO world_member')
            # Portable bounds index; R*Tree is not silently assumed available.
            c.execute('CREATE INDEX world_member_bounds ON world_member(snapshot_id,spatial_valid,west,east)')
            c.execute('UPDATE world_schema SET version=2')
        return True

    def publish_batch(self, key, owner, batch, *, provider, revision,
                      storage_reference, fresh_until, usable_until, coverage=None,
                      certified_selections=()):
        """Store immutable observations under lease and registry revision fencing.

        storage_reference must refer to a separately approved durable-storage
        decision supplied by trusted server code. It is not inferred from the
        existing exact-cache scope. The optional scanner caller additionally
        requires the explicit world_storage registry scope and an ingest flag.
        """
        if not isinstance(batch, ProviderBatch) or not batch.objects and batch.completeness == 'unknown':
            raise POIError('world_batch_invalid')
        if (type(revision) is not int or revision < 1 or not isinstance(storage_reference, str)
                or not 1 <= len(storage_reference) <= 300):
            raise POIError('world_storage_decision_required')
        now = time.time()
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (fresh_until, usable_until))
                or not now <= fresh_until <= usable_until):
            raise POIError('world_invalid_time')
        if len(batch.objects) > 10000 or sum(o.geometry.vertices if o.geometry else 0 for o in batch.objects) > 200000:
            raise POIError('world_capacity')
        objects = []
        for obj in batch.objects:
            # Revalidate even manually constructed dataclasses before persistence.
            raw = encode_object(obj)
            checked = decode_object(raw)
            if (checked != obj or obj.provenance.provider != provider
                    or obj.provenance.fetched_at > now or not obj.provenance.license_ref):
                raise POIError('world_provenance_invalid')
            objects.append(raw)
        if len({o.ordinal for o in batch.objects}) != len(objects):
            raise POIError('world_duplicate_ordinal')
        if coverage is not None:
            from .world_read import SelectionProof
            if not isinstance(coverage,SelectionProof):
                raise POIError('world_coverage_invalid')
            coverage.validate_batch(batch,key,provider,certified_selections)
        envelope = dict(format=FORMAT, schema=SCHEMA_VERSION, profile=batch.profile,
                        completeness=batch.completeness, reasons=batch.reasons,
                        selection=batch.selection, order=batch.order, objects=objects,
                        revision=revision, storage_reference=storage_reference,
                        fresh_until=fresh_until, usable_until=usable_until)
        if coverage is not None:
            envelope['coverage']=coverage.document()
        payload = pack(envelope)
        member_payloads = [pack(o) for o in objects]
        # Account for both stored copies; never silently raise the old world budget.
        size = len(payload) + sum(map(len, member_payloads))
        if size > min(self.max_bytes, 8 * 1024 * 1024):
            raise POIError('world_capacity')
        digest = hashlib.sha256(payload).hexdigest()
        snapshot = hashlib.sha256(pack([key, provider, digest])).hexdigest()
        members = []
        for obj, raw in zip(batch.objects, member_payloads):
            geo = obj.geometry
            bounds = geo.bounds if geo else (None,) * 4
            spatial = bool(geo and not geo.crosses_antimeridian and geo.validation == 'planar_topology_valid')
            members.append((snapshot,obj.osm_type,obj.osm_id,obj.ordinal,raw,obj.identity,
                            sum(LAYER_BITS[layer] for layer in obj.layers),*bounds,int(spatial),
                            hashlib.sha256(raw).hexdigest()))
        with self.repo.transaction() as c:
            if c.execute('SELECT version FROM world_schema').fetchone()[0] != 2:
                raise POIError('world_migration_required')
            if not c.execute('SELECT 1 FROM leases WHERE key=? AND owner=? AND until_at>?',
                             (key, owner, time.time())).fetchone():
                return None
            row = c.execute('SELECT revision,config FROM poi_provider_config WHERE id=?', (provider,)).fetchone()
            if row is None or row['revision'] != revision:
                raise POIError('world_provider_revision')
            config = json.loads(row['config'])
            if (not config.get('enabled') or config.get('policy_status') != 'approved_for_defined_use'
                    or 'storage' not in config.get('scopes', []) or config.get('review_due_at', 0) <= time.time()):
                raise POIError('world_provider_storage_denied')
            if c.execute('SELECT 1 FROM world_snapshot WHERE id=?', (snapshot,)).fetchone():
                return snapshot
            total, count = c.execute('SELECT coalesce(sum(bytes),0),count(*) FROM world_snapshot').fetchone()
            if total + size > self.max_bytes or count >= self.max_snapshots:
                raise POIError('world_capacity')
            c.execute('INSERT INTO world_snapshot VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (snapshot, key, provider, now, FORMAT, payload, digest, size, fresh_until, usable_until))
            c.executemany('''INSERT INTO world_member
                    (snapshot_id,osm_type,osm_id,ordinal,element,identity,layer_mask,west,south,east,north,spatial_valid,element_digest)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', members)
            if coverage is not None:
                from .world_read import READ_FORMAT
                c.execute('INSERT INTO world_coverage(cell,profile,snapshot_id,bounds) VALUES (?,?,?,?)',
                          (snapshot,READ_FORMAT,snapshot,pack(coverage.document()).decode()))
            if not c.execute('SELECT 1 FROM leases WHERE key=? AND owner=? AND until_at>?',
                             (key,owner,time.time())).fetchone():
                raise POIError('world_lease_expired_during_publication')
        return snapshot

    def read_batch(self, snapshot, allow_stale=False):
        """Explicit snapshot read, never newest-by-fetch conflict resolution."""
        c = self.repo.connect()
        try:
            row = c.execute('SELECT * FROM world_snapshot WHERE id=? AND profile=?', (snapshot, FORMAT)).fetchone()
        finally:
            c.close()
        if row is None or not row['fetched'] <= time.time() < row['usable_until' if allow_stale else 'fresh_until']:
            return None
        if hashlib.sha256(row['payload']).hexdigest() != row['digest']:
            return None
        try:
            raw = json.loads(row['payload'])
            if raw['format'] != FORMAT or raw['schema'] != SCHEMA_VERSION:
                return None
            return ProviderBatch(tuple(decode_object(o) for o in raw['objects']), raw['profile'],
                                 raw['completeness'], tuple(raw['reasons']), raw['selection'], raw['order'])
        except (ValueError, TypeError, KeyError):
            return None

    def inspect_region(self, snapshot, layer, bounds, limit=500):
        """Bounded exact intersection of stored observations, NOT coverage proof.

        Retains conflicting versions in separate snapshots; no union, no around,
        no clipping or implicit ocean reconstruction. Dateline is unsupported.
        """
        from shapely.geometry import shape, box
        if layer not in LAYER_BITS or type(limit) is not int or not 1 <= limit <= 1000:
            raise POIError('world_query_limit')
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
            raise POIError('world_query_bounds')
        west, south = position(bounds[:2])
        east, north = position(bounds[2:])
        if west >= east or south >= north or east - west > 180:
            raise POIError('world_query_bounds')
        c = self.repo.connect()
        try:
            c.execute('BEGIN')
            parent = c.execute('SELECT profile,usable_until FROM world_snapshot WHERE id=?', (snapshot,)).fetchone()
            if parent is None or parent['profile'] != FORMAT or parent['usable_until'] <= time.time():
                return dict(objects=(), coverage='UNKNOWN', truncated=False, unsupported=False)
            unsupported = bool(c.execute('''SELECT 1 FROM world_member WHERE snapshot_id=?
                AND (layer_mask & ?) != 0 AND spatial_valid=0 LIMIT 1''',
                (snapshot, LAYER_BITS[layer])).fetchone())
            rows = c.execute('''SELECT element,element_digest FROM world_member WHERE snapshot_id=?
                AND spatial_valid=1 AND (layer_mask & ?) != 0
                AND west<=? AND east>=? AND south<=? AND north>=? ORDER BY ordinal LIMIT ?''',
                (snapshot,LAYER_BITS[layer],east,west,north,south,limit+1))
            result = []
            vertices = 0
            bytes_read = 0
            truncated = False
            area = box(west,south,east,north)
            for index, row in enumerate(rows):
                if index >= limit:
                    truncated = True
                    break
                bytes_read += len(row['element'])
                if bytes_read > 4 * 1024 * 1024:
                    truncated = True
                    break
                if hashlib.sha256(row['element']).hexdigest() != row['element_digest']:
                    raise POIError('world_member_corrupt')
                obj = decode_object(json.loads(row['element']))
                vertices += obj.geometry.vertices
                if vertices > 100000:
                    truncated = True
                    break
                if shape(obj.geometry.geojson()).intersects(area):
                    result.append(obj)
            return dict(objects=tuple(result), coverage='UNKNOWN', truncated=truncated, unsupported=unsupported)
        finally:
            c.close()
