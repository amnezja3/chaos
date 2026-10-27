"""Offline regional land/sea mask from pinned Natural Earth 1:10m land.

This generalized cartographic layer is NOT OSM coastline or gameplay geometry.
No HTTP, registry approval or coverage certificate is generated here.
"""
import hashlib
import json
from shapely.geometry import box, shape, mapping
from shapely.ops import unary_union

from .world_contract import ContractError
from .world_read import checked_bounds

VERSION='natural-earth-5.1.1-land-10m'
SOURCE='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.1/geojson/ne_10m_land.geojson'
SOURCE_SHA256='1ac90796408bc6ad6911d69448485d3c4dbf2190370080368a09976e1c9f7416'
LICENSE='https://www.naturalearthdata.com/about/terms-of-use/'


def extract(raw,bounds):
    bounds=checked_bounds(bounds)
    if bounds[2]-bounds[0]>.020001 or bounds[3]-bounds[1]>.020001:
        raise ContractError('land_water_bounds')
    if len(raw)>15*1024*1024 or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ContractError('natural_earth_source_mismatch')
    source=json.loads(raw)
    if source.get('type')!='FeatureCollection':raise ContractError('natural_earth_format')
    area=box(*bounds);parts=[]
    region=hashlib.sha256(json.dumps(list(bounds),separators=(',',':')).encode()).hexdigest()[:16]
    for f in source['features']:
        geom=shape(f['geometry'])
        if not geom.is_valid:raise ContractError('natural_earth_invalid_source')
        if geom.intersects(area):
            clipped=geom.intersection(area)
            if clipped.area>0:parts.append(clipped)
    land=unary_union(parts) if parts else area.difference(area)
    sea=area.difference(land)
    features=[]
    for role,geom in (('land',land),('sea',sea)):
        if geom.is_empty:continue
        if geom.geom_type not in ('Polygon','MultiPolygon') or not geom.is_valid:
            raise ContractError('natural_earth_region_topology')
        features.append(dict(type='Feature',id=VERSION+':'+region+':'+role,
            properties=dict(surface=role),geometry=mapping(geom)))
    return dict(type='FeatureCollection',features=features)
