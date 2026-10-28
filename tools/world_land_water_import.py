"""Import the pinned regional Natural Earth fixture, offline and archive-only."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.land_water import prepare_product,ADAPTER
from poi_infrastructure.natural_earth_region import VERSION,SOURCE,SOURCE_SHA256,LICENSE
from poi_infrastructure.world_contract import Provenance
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import WorldReadPlanner,SelectionProof,AREA_SELECTION
from tools.world_region_pilot import backup_database

ROOT=Path(__file__).resolve().parents[1]/'tests/fixtures/world/natural_earth_5_1_1'
CERTIFICATE='natural-earth-5-1-1-generalized-regional-v1'


def run(db,*,apply=False,backup=None):
    raw=(ROOT/'body.json').read_bytes();manifest=json.loads((ROOT/'manifest.json').read_bytes())
    digest=hashlib.sha256(raw).hexdigest()
    if (digest!=manifest['body_sha256'] or manifest['dataset_version']!=VERSION
            or manifest['dependencies']!=[SOURCE_SHA256] or manifest['license_ref']!=LICENSE):
        raise ValueError('pinned_product_mismatch')
    batch=prepare_product(json.loads(raw),bounds=manifest['bounds'],dependencies=manifest['dependencies'],
        provenance=Provenance('natural-earth',ADAPTER,digest,manifest['fetched_at'],VERSION,LICENSE))
    result=dict(status='plan',network_calls=0,gameplay_changed=False,objects=len(batch.objects),
        dataset_version=VERSION,bounds=manifest['bounds'],scale='1:10000000',
        usage='generalized_land_sea_archive_only',retention_days=7)
    if not apply:return result
    if not backup or not Path(db).is_file():raise ValueError('existing_database_and_new_backup_required')
    repo=Repository(db);registry=Registry(repo)
    p=next((p for p in registry.list() if p['id']=='natural-earth'),None)
    if p and (p['url']!=SOURCE or not p['enabled'] or not Registry.approved(p,'world_storage')):
        raise ValueError('existing_source_not_approved')
    key='land-sea:'+digest
    with closing(repo.connect()) as c:
        previous=c.execute('SELECT id FROM world_snapshot WHERE query_key=?',(key,)).fetchone()
    if previous:return dict(result,status='already_imported',snapshot=previous[0],production_writes=0)
    backup_database(db,backup)
    if p is None:
        p=registry.save('natural-earth',0,dict(name='Natural Earth 5.1.1 (offline)',url=SOURCE,
            operator_group='raw.githubusercontent.com',priority=100),'operator:land-sea-import')
        p=registry.decision(p['id'],p['revision'],'approved_for_defined_use',['storage','world_storage'],
            dict(source_url=LICENSE,reference=CERTIFICATE,notes='Pinned local regional product. Public-domain source; generalized archive, no network or gameplay.'),
            time.time()+8*86400,'operator:land-sea-import')
        p=registry.tested(p['id'],p['revision'],True,'offline:validated-product')
        p=registry.enable(p['id'],p['revision'],True,'operator:land-sea-import')
    if p['review_due_at']<time.time()+7*86400:raise ValueError('storage_review_required')
    world=CanonicalWorldRepository(repo)
    owner=repo.acquire(key,120)
    if not owner:raise ValueError('import_busy')
    try:
        now=time.time()
        proof=SelectionProof('area','land_water','land_water',AREA_SELECTION,ADAPTER,key,
            tuple(manifest['bounds']),CERTIFICATE,dataset_version=VERSION)
        snapshot=world.publish_batch(key,owner,batch,provider=p['id'],revision=p['revision'],
            storage_reference=p['evidence']['reference'],fresh_until=now+300,usable_until=now+1800,
            retain_until=now+7*86400,coverage=proof,
            certified_selections=((p['id'],ADAPTER,'land_water',AREA_SELECTION,CERTIFICATE),))
        if not snapshot:raise ValueError('import_lease_lost')
        read=WorldReadPlanner(world).read(provider=p['id'],revision=p['revision'],
            storage_reference=p['evidence']['reference'],profile='land_water',layer='land_water',
            selection=AREA_SELECTION,adapter_version=ADAPTER,bounds=manifest['bounds'],
            dataset_version=VERSION,dependency_digests=(SOURCE_SHA256,))
        if read.batch!=batch:raise ValueError('local_roundtrip_failed')
        return dict(result,status='imported_verified',snapshot=snapshot,local_state=read.state)
    finally:repo.release(key,owner)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3');p.add_argument('--apply',action='store_true')
    p.add_argument('--backup');a=p.parse_args()
    print(json.dumps(run(a.db,apply=a.apply,backup=a.backup)))
