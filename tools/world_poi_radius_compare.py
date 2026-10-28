"""Compare independent saved radius vs bbox POI. Hypotheses only, no certification."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Point,shape
from shapely.ops import transform
from tools.world_discovery_inspect import read_json
from tools.world_region_probe import BOUNDS,POI_RADIUS_CENTER
from poi_infrastructure.world_adapters import normalize_maplark,plan_maplark,plan_maplark_region,MAPLARK_VERSION
from poi_infrastructure.world_contract import Provenance,ContractError


def load(directory,plan):
    directory=Path(directory)
    body,bhash=read_json(directory/'body.json');headers,hhash=read_json(directory/'headers.json')
    report,_=read_json(directory/'report.json')
    if report.get('params')!=dict(plan.params) or report.get('status')!='captured_not_certified':
        raise ContractError('capture_query_mismatch')
    if not isinstance(report.get('fetched_at'),(int,float)) or not isinstance(report.get('provider_revision'),int):
        raise ContractError('capture_metadata_missing')
    batch=normalize_maplark(body,headers,Provenance('maplark',MAPLARK_VERSION,bhash,report['fetched_at']),profile=plan.profile,maximum=1000)
    if batch.completeness!='complete' or batch.reasons:raise ContractError('capture_incomplete')
    objects={obj.identity:obj for obj in batch.objects}
    if len(objects)!=len(batch.objects):raise ContractError('duplicate_identity')
    return objects,report,dict(body=bhash,headers=hhash)


def compare(parent,radius=None):
    objects,report,hashes=load(parent,plan_maplark_region(BOUNDS,profile='poi'))
    # Deliberately a diagnostic approximation, not a production selection rule.
    # Flag objects within two metres; no precision/Overpass parity claim.
    lat,lon=POI_RADIUS_CENTER
    def project(x,y,z=None):return ((x-lon)*111195*math.cos(math.radians(lat)),(y-lat)*111195)
    origin=Point(0,0);predicates={'geometry_distance':set(),'bounds_center_distance':set()};boundary=[]
    for key,obj in objects.items():
        if not obj.geometry:raise ContractError('geometry_required')
        geom=shape(obj.geometry.geojson());west,south,east,north=geom.bounds
        distances=(transform(project,geom).distance(origin),Point(*project((west+east)/2,(south+north)/2)).distance(origin))
        for name,distance in zip(predicates,distances):
            if distance<=300:predicates[name].add(key)
            if abs(distance-300)<=2:boundary.append(dict(identity=key,hypothesis=name,distance_m=round(distance,3)))
    result=dict(status='hypotheses_not_certified',network_calls=0,production_writes=0,
        regional_scan_approved=False,parent_objects=len(objects),parent_sha256=hashes,
        hypotheses={k:dict(count=len(v),identities=sorted(v)) for k,v in predicates.items()},near_boundary=boundary,
        limitation='Approximate local metric; one empirical sample cannot certify source completeness, radius semantics or dataset consistency.')
    if radius is None:return result
    actual,other,otherhashes=load(radius,plan_maplark(lat,lon,300,limit=1000))
    result.update(radius_objects=len(actual),radius_sha256=otherhashes,
        capture_gap_seconds=abs(report['fetched_at']-other['fetched_at']),
        provider_revisions_match=report['provider_revision']==other['provider_revision'],
        radius_ids_absent_from_parent=sorted(actual.keys()-objects.keys()))
    shared=actual.keys()&objects.keys()
    result['changed_geometry']=sorted(k for k in shared if objects[k].geometry!=actual[k].geometry)
    result['changed_tags']=sorted(k for k in shared if dict(objects[k].tags)!=dict(actual[k].tags))
    for name,selected in predicates.items():
        result['hypotheses'][name].update(missing_from_radius=sorted(selected-actual.keys()),
            additional_in_radius=sorted(actual.keys()-selected),identities_match=selected==actual.keys())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',required=True);p.add_argument('--radius')
    a=p.parse_args()
    try:result=compare(a.parent,a.radius)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,network_calls=0)));return 1
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
