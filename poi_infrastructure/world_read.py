"""Local selection proofs. No provider calls, implicit unions or gameplay changes.

Exact response reuse and geographic bbox intersection are different contracts.
The latter is deliberately unavailable for MapLark radius POI and land/water.
Only trusted server-side adapter configuration may supply area certificates.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import time

from .world_contract import ContractError, ProviderBatch, SCHEMA_VERSION, position


READ_FORMAT = 'canonical-local-read-v1'
AREA_SELECTION = 'bbox-intersects-full-v1'
AREA_LAYERS = frozenset(('roads', 'waterways', 'inland_water', 'coastline'))


def checked_bounds(bounds):
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
        raise ContractError('local_bounds_invalid')
    west,south = position(bounds[:2])
    east,north = position(bounds[2:])
    if west >= east or south >= north or east-west > 180:
        raise ContractError('local_bounds_unsupported')
    return (west,south,east,north)


@dataclass(frozen=True)
class SelectionProof:
    mode: str
    layer: str
    profile: str
    selection: str
    adapter_version: str
    query_key: str
    bounds: tuple | None = None
    certificate: str | None = None
    schema: str = SCHEMA_VERSION
    dataset_version: str | None = None

    def __post_init__(self):
        if self.mode not in ('exact', 'area') or self.schema != SCHEMA_VERSION:
            raise ContractError('local_proof_version')
        if self.dataset_version is not None and (not isinstance(self.dataset_version,str)
                or not 1 <= len(self.dataset_version) <= 160):
            raise ContractError('local_dataset_version')
        for token in (self.layer,self.profile,self.selection,self.adapter_version,self.query_key):
            if not isinstance(token,str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}',token):
                raise ContractError('local_proof_identifier')
        if self.mode == 'exact':
            if self.bounds is not None or self.certificate is not None or self.layer != 'poi':
                raise ContractError('local_exact_profile')
        else:
            if (self.layer not in AREA_LAYERS or self.profile != self.layer
                    or self.selection != AREA_SELECTION or not isinstance(self.certificate,str)
                    or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}',self.certificate)):
                raise ContractError('local_area_unsupported')
            object.__setattr__(self,'bounds',checked_bounds(self.bounds))

    def validate_batch(self, batch, key, provider, certificates=()):
        if (batch.completeness != 'complete' or batch.reasons or key != self.query_key
                or batch.profile != self.profile or batch.selection != self.selection):
            raise ContractError('local_response_not_complete')
        if any(o.provenance.adapter_version != self.adapter_version for o in batch.objects):
            raise ContractError('local_adapter_mismatch')
        if any(o.provenance.source_dataset_at != self.dataset_version for o in batch.objects):
            raise ContractError('local_dataset_mismatch')
        if self.mode == 'area':
            # No certificate is inferred from successful HTTP or valid topology.
            required=(provider,self.adapter_version,self.layer,self.selection,self.certificate)
            if required not in certificates:
                raise ContractError('local_area_not_certified')
            if any(self.layer not in o.layers or not o.geometry or o.geometry.crosses_antimeridian
                   or o.geometry.validation != 'planar_topology_valid' for o in batch.objects):
                raise ContractError('local_area_geometry_incomplete')
            from shapely.geometry import box, shape
            area=box(*self.bounds)
            if any(not shape(o.geometry.geojson()).intersects(area) for o in batch.objects):
                raise ContractError('local_area_selection_mismatch')

    def document(self):
        return asdict(self)


@dataclass(frozen=True)
class LocalRead:
    state: str
    reason: str
    batch: ProviderBatch | None = None
    snapshot: str | None = None


class WorldReadPlanner:
    """Bounded one-snapshot local planner, called explicitly below acquisition.

    Caller supplies the retained storage decision reference and current provider
    revision. In this first conservative version a revision change is a miss.
    Stale selection is explicit; this class never performs retries or requests.
    """
    def __init__(self, world):
        self.world=world

    def read(self, *, provider, revision, storage_reference, profile, selection,
             adapter_version, layer='poi', query_key=None, bounds=None,
             allow_stale=False, still_active=lambda: True, max_objects=1000,
             max_seconds=2.0, dataset_version=None):
        from .world_storage import FORMAT, decode_object
        if type(max_objects) is not int or not 1 <= max_objects <= 10000:
            raise ContractError('local_read_limit')
        if type(max_seconds) not in (int,float) or not 0 < max_seconds <= 10:
            raise ContractError('local_read_deadline')
        deadline=time.monotonic()+max_seconds
        bytes_read=0
        if (query_key is None) == (bounds is None):
            raise ContractError('local_query_ambiguous')
        area=checked_bounds(bounds) if bounds is not None else None
        if not still_active():
            return LocalRead('CANCELLED','scanner_inactive')
        c=self.world.repo.connect()
        try:
            # Metadata lookup only; at most 64 candidates, never unbounded payloads.
            rows=c.execute('''SELECT s.id,s.query_key,s.fetched,s.fresh_until,s.usable_until,c.bounds
                FROM world_coverage c JOIN world_snapshot s ON s.id=c.snapshot_id
                WHERE c.profile=? AND s.profile=? AND s.provider=? AND s.usable_until>?
                AND (? IS NULL OR s.query_key=?)
                ORDER BY s.fetched DESC LIMIT 64''',
                (READ_FORMAT,FORMAT,provider,time.time(),query_key,query_key)).fetchall()
        finally:
            c.close()
        for row in rows:
            if time.monotonic()>=deadline:
                return LocalRead('MISS','local_read_deadline')
            if not still_active():
                return LocalRead('CANCELLED','scanner_inactive')
            try:
                proof=SelectionProof(**json.loads(row['bounds']))
                if proof.dataset_version != dataset_version:
                    continue
                if (proof.layer,proof.profile,proof.selection,proof.adapter_version) != (layer,profile,selection,adapter_version):
                    continue
                if area is None:
                    if proof.mode != 'exact' or proof.query_key != query_key:
                        continue
                else:
                    if proof.mode != 'area':
                        continue
                    w,s,e,n=proof.bounds
                    if not (w <= area[0] <= area[2] <= e and s <= area[1] <= area[3] <= n):
                        continue
                expiry=row['usable_until' if allow_stale else 'fresh_until']
                if not row['fetched'] <= time.time() < expiry:
                    continue
                c=self.world.repo.connect()
                try:
                    stored=c.execute('SELECT payload,digest FROM world_snapshot WHERE id=?',(row['id'],)).fetchone()
                finally:
                    c.close()
                if stored is None or len(stored['payload'])>8*1024*1024 or hashlib.sha256(stored['payload']).hexdigest()!=stored['digest']:
                    continue
                bytes_read+=len(stored['payload'])
                if bytes_read>8*1024*1024:
                    return LocalRead('MISS','local_read_byte_limit')
                raw=json.loads(stored['payload'])
                if (raw.get('schema') != SCHEMA_VERSION or raw.get('format') != FORMAT
                        or raw.get('revision') != revision or raw.get('storage_reference') != storage_reference
                        or raw.get('coverage') != json.loads(row['bounds'])
                        or raw.get('completeness') != 'complete' or raw.get('reasons')
                        or raw.get('profile') != profile or raw.get('selection') != selection
                        or raw.get('fresh_until') != row['fresh_until'] or raw.get('usable_until') != row['usable_until']):
                    continue
                objects=tuple(decode_object(o) for o in raw['objects'])
                if any(o.provenance.provider != provider or o.provenance.adapter_version != adapter_version
                       or o.provenance.source_dataset_at != dataset_version for o in objects):
                    continue
                if area is not None:
                    from shapely.geometry import box, shape
                    region=box(*area)
                    if any(not o.geometry or o.geometry.crosses_antimeridian for o in objects):
                        continue
                    objects=tuple(o for o in objects if shape(o.geometry.geojson()).intersects(region))
                if len(objects)>max_objects:
                    return LocalRead('MISS','local_result_limit')
                batch=ProviderBatch(objects,profile,'complete',(),selection,raw['order'])
                # Permission/revision/expiry/cancellation rechecked after parsing.
                c=self.world.repo.connect()
                try:
                    current=c.execute('SELECT revision,config FROM poi_provider_config WHERE id=?',(provider,)).fetchone()
                    exists=c.execute('SELECT 1 FROM world_coverage WHERE snapshot_id=? AND profile=?',
                                     (row['id'],READ_FORMAT)).fetchone()
                finally:
                    c.close()
                if current is None or current['revision']!=revision or not exists:
                    continue
                policy=json.loads(current['config'])
                if (policy.get('policy_status')!='approved_for_defined_use' or 'storage' not in policy.get('scopes',[])
                        or policy.get('review_due_at',0)<=time.time()):
                    continue
                # enabled controls network acquisition, not a retained storage right.
                if not still_active():
                    return LocalRead('CANCELLED','scanner_inactive')
                if time.monotonic()>=deadline:
                    return LocalRead('MISS','local_read_deadline')
                finished_at=time.time()
                if finished_at>=expiry:
                    continue
                return LocalRead('COMPLETE_FRESH' if finished_at<row['fresh_until'] else 'COMPLETE_STALE',
                                 'single_snapshot',batch,row['id'])
            except (ValueError,TypeError,KeyError):
                continue
        return LocalRead('MISS','no_compatible_coverage')
