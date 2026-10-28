"""Explain saved Paris acceptance positions offline; no HTTP, DB or TTL renewal."""
import argparse
from collections import Counter
from pathlib import Path
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.world_discovery_inspect import read_json
from tools.world_paris_region_acceptance import candidate_positions,BOUNDS,COMPACT_BOUNDS
from poi_infrastructure.world_adapters import normalize_maplark,plan_maplark_region,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance,ContractError


def inspect(directory):
    root=Path(directory)
    body,digest=read_json(root/'body.json')
    headers,_=read_json(root/'headers.json')
    request,_=read_json(root/'request.json')
    bounds=next((b for b in (BOUNDS,COMPACT_BOUNDS)
                 if dict(plan_maplark_region(b,profile='poi',limit=1000).params)==request.get('params')),None)
    if bounds is None:raise ContractError('capture_query_mismatch')
    batch=normalize_maplark(body,headers,Provenance('maplark',MAPLARK_VERSION,digest,0),profile='poi',maximum=1000)
    positions,rejections=candidate_positions(batch,bounds)
    return dict(status='offline_positions',network_calls=0,production_writes=0,
                body_sha256=digest,objects=len(batch.objects),completeness=batch.completeness,
                geometry_types=dict(Counter(o.geometry.kind for o in batch.objects)),
                positions=positions,position_rejections=rejections,
                live_freshness_checked=False,acceptance_pass=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args=parser.parse_args()
    print(json.dumps(inspect(args.directory)))
