"""MapLark-native POI selection with CHAOS's existing marker/gameplay contract.

The API owns radius selection. Geometry bounds supply way/relation markers;
this is explicitly not a claim of Overpass member-topology equivalence.
"""
from .world_contract import ContractError, POI_PROFILE, OSM_TYPES
from .world_adapters import MAPLARK_VERSION

PROFILE = 'maplark-radius-bounds-v1'
ENDPOINT = 'https://api.maplark.com/v3/osm_features'


def export_maplark(batch):
    if (batch.profile != POI_PROFILE or batch.completeness != 'complete' or batch.reasons
            or batch.selection != 'maplark-radius-unverified'):
        raise ContractError('maplark_response_incomplete')
    elements = []
    for obj in sorted(batch.objects, key=lambda o: (OSM_TYPES.index(o.osm_type), o.osm_id)):
        if obj.provenance.provider != 'maplark' or obj.provenance.adapter_version != MAPLARK_VERSION:
            raise ContractError('adapter_provenance_mismatch')
        geo = obj.geometry
        if not geo or geo.validation != 'planar_topology_valid' or geo.crosses_antimeridian:
            raise ContractError('maplark_geometry_unsupported')
        if 'poi' not in obj.layers:
            continue
        row = dict(type=obj.osm_type, id=obj.osm_id, tags=dict(obj.tags))
        if obj.osm_type == 'node':
            if geo.kind != 'Point':
                raise ContractError('node_geometry_invalid')
            row.update(lon=geo.coordinates[0], lat=geo.coordinates[1])
        else:
            west, south, east, north = geo.bounds
            row['center'] = dict(lon=round((west+east)/2, 7), lat=round((south+north)/2, 7))
        elements.append(row)
    return {'elements': elements}
