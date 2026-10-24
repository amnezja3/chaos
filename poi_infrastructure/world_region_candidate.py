"""Unapproved single-response roads candidate; never creates an area certificate."""
from dataclasses import dataclass,replace
from shapely.geometry import box,shape
from .world_adapters import MAPLARK_VERSION,plan_maplark_region
from .world_contract import ContractError,ProviderBatch

SELECTION='maplark-bbox-local-filter-v1'


@dataclass(frozen=True)
class RegionalCandidate:
    batch: ProviderBatch
    bounds: tuple
    excluded_ids: tuple
    raw_objects: int
    region_certified: bool = False


def prepare(batch,plan):
    """Keep full geometry and provenance; remove only bbox-envelope false positives.

    Complete here describes the source response, never provider area coverage.
    This helper never approves publication or gameplay. An explicitly accepted
    CLI pilot may consume its output under a separate isolated adapter contract.
    """
    try:
        params=dict(plan.params)
        bounds=tuple(map(float,params['bbox'].split(',')))
        expected=plan_maplark_region(bounds,profile='roads',limit=int(params['limit']))
    except (KeyError,TypeError,ValueError):
        raise ContractError('regional_plan_invalid') from None
    if plan!=expected or batch.profile!='roads':raise ContractError('regional_profile_unqualified')
    if batch.completeness!='complete' or batch.reasons:raise ContractError('regional_response_incomplete')
    if batch.selection not in ('maplark-bbox-unverified','maplark-radius-unverified'):
        raise ContractError('regional_input_selection')
    if len({(o.provenance.snapshot,o.provenance.source_dataset_at) for o in batch.objects})>1:
        raise ContractError('regional_mixed_source')
    area=box(*bounds);kept=[];excluded=[]
    for obj in batch.objects:
        if obj.provenance.provider!='maplark' or obj.provenance.adapter_version!=MAPLARK_VERSION:
            raise ContractError('regional_provider_mismatch')
        if 'roads' not in obj.layers or not obj.geometry or obj.geometry.crosses_antimeridian:
            raise ContractError('regional_geometry_or_layer')
        geom=shape(obj.geometry.geojson())
        if geom.is_empty or not geom.is_valid:raise ContractError('regional_invalid_geometry')
        if geom.intersects(area):kept.append(obj)
        elif geom.envelope.intersects(area):excluded.append(obj.identity)
        else:raise ContractError('regional_unrelated_geometry')
    return RegionalCandidate(replace(batch,objects=tuple(kept),selection=SELECTION),bounds,
                             tuple(excluded),len(batch.objects))
