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
    west,south,east,north=bounds;mid=(west+east)/2
    left=box(west,south,mid,north);right=box(mid,south,east,north)
    invalid=[];left_ids=set();right_ids=set();reason_counts={};selected_ids=set()
    types={};polygon_parts=0;interior_rings=0;hole_objects=0
    for obj in batch.objects:
        reasons=[];geometry=None
        if layer not in obj.layers:reasons.append('layer_mismatch')
        if not obj.geometry:reasons.append('missing_geometry')
        elif obj.geometry.crosses_antimeridian:reasons.append('antimeridian_geometry')
        else:
            geometry=shape(obj.geometry.geojson())
            types[obj.geometry.kind]=types.get(obj.geometry.kind,0)+1
            polygons=list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry] if geometry.geom_type=='Polygon' else []
            polygon_parts+=len(polygons)
            holes=sum(len(p.interiors) for p in polygons)
            interior_rings+=holes;hole_objects+=bool(holes)
            if geometry.is_empty:reasons.append('empty_geometry')
            elif not geometry.is_valid:reasons.append('invalid_geometry')
            else:
                if not geometry.intersects(area):reasons.append('geometry_outside_bbox')
                if not reasons:
                    selected_ids.add(obj.identity)
                    if geometry.intersects(left):left_ids.add(obj.identity)
                    if geometry.intersects(right):right_ids.add(obj.identity)
        if reasons:
            for reason in reasons:reason_counts[reason]=reason_counts.get(reason,0)+1
            tags=dict(obj.tags)
            invalid.append(dict(identity=obj.identity,reasons=reasons,layers=list(obj.layers),
                geometry_type=obj.geometry.kind if obj.geometry else None,
                bounds=list(geometry.bounds) if geometry is not None and not geometry.is_empty else None,
                envelope_intersects_bbox=bool(geometry.envelope.intersects(area)) if geometry is not None and not geometry.is_empty and geometry.is_valid else None,
                classification_tags={key:tags[key] for key in ('highway','waterway','natural','area','type') if key in tags}))
    # A bbox-index false positive can be removed locally, but this says nothing
    # about features absent from the response. Keep the raw test and certification separate.
    removable=[item for item in invalid if item['reasons']==['geometry_outside_bbox']
               and item['envelope_intersects_bbox']]
    blocking=len(invalid)-len(removable)
    result.update(status='response_checked_not_certified',objects=len(batch.objects),
        completeness=batch.completeness,reasons=list(batch.reasons),invalid_objects=len(invalid),
        invalid_reasons=reason_counts,invalid_details=invalid[:20],invalid_details_truncated=len(invalid)>20,
        missing=['source dataset consistency','separate area certification']+(['provider selection semantics'] if removable else [])+(['boundary selection investigation'] if blocking else []),
        neighbor_candidates=dict(left=len(left_ids),right=len(right_ids),crossing=len(left_ids & right_ids)),
        local_filter=dict(predicate='geometry.intersects(bbox), full geometry retained',
            selected_objects=len(selected_ids),excluded_envelope_false_positives=len(removable),
            blocking_objects=blocking,neighbor_union_matches=(left_ids|right_ids)==selected_ids,
            observed_geometry_pass=not blocking and batch.completeness=='complete',
            proves_provider_completeness=False,mutates_saved_response=False),
        boundary_selection_pass=not invalid and batch.completeness=='complete')
    result['topology']=dict(geometry_types=types,polygon_parts=polygon_parts,
        interior_rings=interior_rings,objects_with_holes=hole_objects,
        water_surface_with_holes_observed=layer=='inland_water' and hole_objects>0,
        note='Interior rings are observed geometry, not independent proof of real islands or coverage.')
    if layer in ('roads','waterways','inland_water'):
        from poi_infrastructure.world_region_candidate import prepare
        from poi_infrastructure.world_contract import ContractError
        try:
            candidate=prepare(batch,plan)
            result['candidate']=dict(status='prepared_not_certified',objects=len(candidate.batch.objects),
                                     excluded=len(candidate.excluded_ids),region_certified=False)
        except ContractError as exc:
            result['candidate']=dict(status='blocked',reason=str(exc),region_certified=False)
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
