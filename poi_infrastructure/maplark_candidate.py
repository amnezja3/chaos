"""Offline compatibility candidate. Not registered as a gameplay provider.

Full GeoJSON ways can reproduce node/way around and bbox-center semantics.
Relations require original member topology, which this input does not provide.
Selection cannot prove that a provider supplied every matching OSM object.
"""
from .geometry import GeometrySnapshot, UncertifiedGeometry
from .world_adapters import MAPLARK_VERSION
from .world_contract import ContractError, FILTERS, POI_PROFILE


def preview_maplark(batch, lat, lon, radius):
    """Return diagnostic out-center data; never grant batch export approval."""
    if (batch.profile != POI_PROFILE or batch.completeness != 'complete' or
            batch.reasons or batch.selection != 'maplark-radius-unverified'):
        raise ContractError('candidate_response_incomplete_or_wrong_profile')
    elements = []
    # Untagged local vertices are implementation details, never exported identities.
    vertex_id = -1
    for obj in batch.objects:
        if (obj.provenance.provider != 'maplark' or
                obj.provenance.adapter_version != MAPLARK_VERSION):
            raise ContractError('adapter_provenance_mismatch')
        geometry = obj.geometry
        if not geometry or geometry.validation != 'planar_topology_valid':
            raise ContractError('candidate_geometry_unverified')
        element = dict(type=obj.osm_type, id=obj.osm_id, tags=dict(obj.tags))
        if obj.osm_type == 'node' and geometry.kind == 'Point':
            element.update(lon=geometry.coordinates[0], lat=geometry.coordinates[1])
        elif obj.osm_type == 'way':
            if geometry.kind == 'LineString':
                points = geometry.coordinates
            elif geometry.kind == 'Polygon' and len(geometry.coordinates) == 1:
                points = geometry.coordinates[0]
            else:
                raise ContractError('candidate_way_topology_unverified')
            element['nodes'] = []
            for longitude, latitude in points:
                elements.append(dict(type='node', id=vertex_id, lon=longitude, lat=latitude))
                element['nodes'].append(vertex_id)
                vertex_id -= 1
        else:
            # Never silently discard a relation and label a partial scan complete.
            raise ContractError('candidate_member_topology_required')
        elements.append(element)
    try:
        result = GeometrySnapshot(elements).select(lat, lon, radius, FILTERS)
    except UncertifiedGeometry as exc:
        raise ContractError('candidate_' + str(exc)) from None
    for element in result['elements']:
        element.pop('nodes', None)
    return {'status': 'offline_candidate', 'gameplay_approved': False,
            'coverage_approved': False, 'network_calls': 0,
            'unresolved': ['provider_selection_completeness', 'relation_member_topology'],
            'response': result}
