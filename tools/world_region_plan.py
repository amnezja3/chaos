"""Offline regional test plan and saved-response check. Never executes HTTP."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.world_adapters import plan_maplark_region,normalize_maplark,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance
from tools.world_discovery_inspect import read_json


def evaluate(bounds,layer,body=None,headers=None):
    plan=plan_maplark_region(tuple(bounds),profile=layer)
    result=dict(status='plan',network_calls=0,params=dict(plan.params),profile=layer,
        region_certified=False,world_ingest=False,gameplay_changed=False,
        source='https://maplark.com/products/osm-features-api',
        missing=['VPS bbox response and boundary fixtures','source dataset consistency','separate area certification'])
    if body is None:return result
    from shapely.geometry import box,shape
    batch=normalize_maplark(body,headers,Provenance('maplark',MAPLARK_VERSION,'offline-region-check',0),profile=layer,maximum=1000)
    area=box(*bounds)
    invalid=[o.identity for o in batch.objects if not o.geometry or o.geometry.crosses_antimeridian
             or layer not in o.layers or not shape(o.geometry.geojson()).intersects(area)]
    west,south,east,north=bounds;mid=(west+east)/2
    left=box(west,south,mid,north);right=box(mid,south,east,north)
    left_ids={o.identity for o in batch.objects if shape(o.geometry.geojson()).intersects(left)}
    right_ids={o.identity for o in batch.objects if shape(o.geometry.geojson()).intersects(right)}
    result.update(status='response_checked_not_certified',objects=len(batch.objects),
        completeness=batch.completeness,reasons=list(batch.reasons),invalid_objects=len(invalid),
        neighbor_candidates=dict(left=len(left_ids),right=len(right_ids),crossing=len(left_ids & right_ids)),
        boundary_selection_pass=not invalid and batch.completeness=='complete')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bbox',nargs=4,type=float,default=[20.36,51.53,20.37,51.54])
    p.add_argument('--layer',choices=['roads','waterways','inland_water','coastline'],default='roads')
    p.add_argument('--body');p.add_argument('--headers')
    a=p.parse_args()
    if bool(a.body)!=bool(a.headers):p.error('--body and --headers must be supplied together')
    body=read_json(a.body)[0] if a.body else None
    headers=read_json(a.headers)[0] if a.headers else None
    print(json.dumps(evaluate(a.bbox,a.layer,body,headers)))


if __name__=='__main__':main()
