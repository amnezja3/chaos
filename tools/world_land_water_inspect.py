"""Inspect a bounded supplied land/sea product offline. No DB, HTTP or approval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.land_water import ADAPTER,prepare_product
from poi_infrastructure.world_contract import Provenance,ContractError


def inspect(body_path,manifest_path):
    with open(body_path,'rb') as f:raw=f.read(4*1024*1024+1)
    with open(manifest_path,'rb') as f:manifest_raw=f.read(8193)
    if len(raw)>4*1024*1024 or len(manifest_raw)>8192:raise ContractError('regional_file_limit')
    manifest=json.loads(manifest_raw)
    fields={'bounds','provider','snapshot','fetched_at','dataset_version','license_ref','dependencies','body_sha256'}
    if not isinstance(manifest,dict) or set(manifest)!=fields:raise ContractError('product_manifest_fields')
    if hashlib.sha256(raw).hexdigest()!=manifest['body_sha256']:raise ContractError('product_digest_mismatch')
    batch=prepare_product(json.loads(raw),bounds=manifest['bounds'],dependencies=manifest['dependencies'],
        provenance=Provenance(manifest['provider'],ADAPTER,manifest['snapshot'],manifest['fetched_at'],
                              manifest['dataset_version'],manifest['license_ref']))
    return dict(status='topology_checked_not_approved',network_calls=0,production_writes=0,
        region_certified=False,objects=len(batch.objects),vertices=sum(o.geometry.vertices for o in batch.objects),
        roles={role:sum(o.land_water_origin.role==role for o in batch.objects) for role in ('land','sea')},
        dataset_version=manifest['dataset_version'],dependencies=manifest['dependencies'],
        note='Input source/version/license are supplied metadata, not independently verified by this inspector.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--body',required=True);p.add_argument('--manifest',required=True)
    a=p.parse_args()
    try:print(json.dumps(inspect(a.body,a.manifest)));return 0
    except Exception as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,ContractError) else type(exc).__name__)));return 1


if __name__=='__main__':raise SystemExit(main())
