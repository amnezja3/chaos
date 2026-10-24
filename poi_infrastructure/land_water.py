"""Bounded, offline regional land/sea products. No coastline closing or HTTP.

Callers supply an explicitly approved, versioned regional extract. Topology
validation is not source/license certification. Normal provider adapters never
create these objects from their tags. The ordinary world store is reused.
"""
import hashlib
import json
from shapely.geometry import shape,box
from shapely.ops import unary_union
from .world_contract import ContractError,Geometry,LandWaterOrigin,ProviderBatch,WorldObject
from .world_read import AREA_SELECTION,checked_bounds

ADAPTER='land-sea-regional-product-v1'


def validate_partition(objects,bounds,dataset_version):
    bounds=checked_bounds(bounds)
    if not dataset_version or not objects or len(objects)>1000:
        raise ContractError('land_water_product_incomplete')
    area=box(*bounds);groups={'land':[],'sea':[]};lineage=set();vertices=0
    for obj in objects:
        origin=obj.land_water_origin
        if (not origin or origin.dataset_version!=dataset_version or tuple(origin.bounds)!=tuple(bounds)
                or obj.provenance.source_dataset_at!=dataset_version or obj.layers!=frozenset(('land_water',))
                or not obj.geometry or obj.geometry.kind not in ('Polygon','MultiPolygon')
                or obj.geometry.crosses_antimeridian or obj.geometry.validation!='planar_topology_valid'):
            raise ContractError('land_water_lineage_mismatch')
        lineage.add((origin.product_digest,origin.dependencies,origin.algorithm,
                     obj.provenance.provider,obj.provenance.adapter_version,obj.provenance.snapshot))
        vertices+=obj.geometry.vertices
        if vertices>100000:raise ContractError('land_water_vertex_limit')
        geometry=shape(obj.geometry.geojson())
        if not geometry.intersects(area):raise ContractError('land_water_outside_region')
        groups[origin.role].append(geometry.intersection(area))
    if len(lineage)!=1:raise ContractError('land_water_mixed_product')
    land=unary_union(groups['land']);sea=unary_union(groups['sea'])
    # Same-role overlap is valid for split source products; opposite roles are not.
    if land.intersection(sea).area>0:raise ContractError('land_water_conflicting_roles')
    if not land.union(sea).equals(area):raise ContractError('land_water_uncovered_region')


def prepare_product(body,*,bounds,provenance,dependencies):
    """Validate complete land/sea partition in an already bounded GeoJSON extract.

Features use properties.surface=land|sea and unique string IDs. No tags from
normal OSM responses can grant this contract. Raw source hashes are dependencies.
No automatic area proof or production permission is granted by this function.
"""
    if provenance.adapter_version!=ADAPTER or not provenance.source_dataset_at or not provenance.license_ref:
        raise ContractError('land_water_source_version_required')
    if not isinstance(body,dict) or body.get('type')!='FeatureCollection':raise ContractError('land_water_format')
    features=body.get('features')
    if not isinstance(features,list) or not 1<=len(features)<=1000:raise ContractError('land_water_feature_limit')
    encoded=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(encoded)>4*1024*1024:raise ContractError('land_water_byte_limit')
    digest=hashlib.sha256(encoded).hexdigest();objects=[]
    for ordinal,feature in enumerate(features):
        if not isinstance(feature,dict) or feature.get('type')!='Feature':raise ContractError('land_water_feature')
        props=feature.get('properties')
        if not isinstance(props,dict):raise ContractError('land_water_feature')
        origin=LandWaterOrigin(provenance.source_dataset_at,digest,props.get('surface'),tuple(bounds),tuple(dependencies))
        obj=WorldObject.create(external_id=feature.get('id'),tags={},
            geometry=Geometry.parse(feature.get('geometry')),marker=None,marker_method=None,
            provenance=provenance,ordinal=ordinal,land_water_origin=origin)
        objects.append(obj)
    batch=ProviderBatch(tuple(objects),'land_water','complete',(),AREA_SELECTION,'source-product-order')
    validate_partition(batch.objects,bounds,provenance.source_dataset_at)
    return batch
