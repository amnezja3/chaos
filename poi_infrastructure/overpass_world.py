"""Bounded full-geometry observations; no coastline-to-ocean inference."""
import time
import re
from shapely.geometry import Polygon
from shapely.ops import linemerge

from .world_contract import ContractError, Geometry, ProviderBatch, Provenance, WorldObject, position
from .world_read import checked_bounds
from .providers import endpoint_host
from .service import Config, POIError, bounded_http, retry_delay
from .upstream_priority import UpstreamPriority
from .credit_budget import CreditBudget

VERSION='overpass-bbox-geom-v1'
FILTERS={'roads':'[highway]','waterways':'[waterway]',
         'inland_water':'[natural=water]','coastline':'[natural=coastline]'}


def query(bounds,profile):
    w,s,e,n=checked_bounds(bounds)
    if e-w>.020001 or n-s>.020001 or profile not in FILTERS:
        raise ContractError('overpass_region_profile')
    return f'[out:json][timeout:25][maxsize:33554432];nwr({s},{w},{n},{e}){FILTERS[profile]};out body geom 1001;'


def normalize(raw,provenance,profile):
    if not isinstance(raw,dict) or not isinstance(raw.get('elements'),list) or len(raw['elements'])>1001:
        raise ContractError('overpass_world_response')
    reasons=set();objects=[];remaining=100000;identities=set()
    if raw.get('remark'):reasons.add('provider_remark')
    if len(raw['elements'])>=1001:reasons.add('response_limit')
    def coordinates(items):
        nonlocal remaining
        if not isinstance(items,list) or not 2<=len(items)<=20000:
            raise ContractError('incomplete_geometry')
        remaining-=len(items)
        if remaining<0:raise ContractError('geometry_limit')
        return [position((p.get('lon'),p.get('lat'))) if isinstance(p,dict)
                else position(None) for p in items]
    def rings(lines):
        if not lines:return []
        merged=linemerge(lines)
        parts=[merged] if merged.geom_type=='LineString' else list(merged.geoms)
        if any(not p.is_ring for p in parts):raise ContractError('unclosed_relation')
        return [list(p.coords) for p in parts]
    for ordinal,element in enumerate(raw['elements']):
        if not isinstance(element,dict):raise ContractError('overpass_element')
        kind=element.get('type');osm_id=element.get('id');tags=element.get('tags',{})
        if kind not in ('node','way','relation') or type(osm_id) is not int or osm_id<=0:
            raise ContractError('overpass_identity')
        if (kind,osm_id) in identities:raise ContractError('overpass_duplicate')
        identities.add((kind,osm_id));geometry=None
        try:
            if kind=='node':
                raw_geometry=dict(type='Point',coordinates=position((element.get('lon'),element.get('lat'))))
            elif kind=='way':
                coords=coordinates(element.get('geometry'))
                area=tags.get('area')=='yes' or tags.get('natural')=='water'
                raw_geometry=dict(type='Polygon' if area else 'LineString',coordinates=[coords] if area else coords)
            else:
                members=element.get('members')
                if tags.get('type')!='multipolygon' or not isinstance(members,list) or not 1<=len(members)<=1000:
                    raise ContractError('unsupported_relation_geometry')
                outer=[];inner=[]
                for member in members:
                    if not isinstance(member,dict) or member.get('type')!='way' or member.get('role') not in ('outer','inner'):
                        raise ContractError('incomplete_relation_members')
                    (outer if member['role']=='outer' else inner).append(coordinates(member.get('geometry')))
                shells=rings(outer);holes=rings(inner)
                if not shells:raise ContractError('missing_outer')
                polygons=[[shell] for shell in shells]
                for hole in holes:
                    owners=[i for i,shell in enumerate(shells) if Polygon(shell).contains(Polygon(hole))]
                    if len(owners)!=1:raise ContractError('ambiguous_hole')
                    polygons[owners[0]].append(hole)
                raw_geometry=dict(type='Polygon' if len(polygons)==1 else 'MultiPolygon',
                                  coordinates=polygons[0] if len(polygons)==1 else polygons)
            geometry=Geometry.parse(raw_geometry)
        except (ContractError,ValueError,TypeError,AttributeError):
            if remaining<0:raise ContractError('geometry_limit')
            reasons.add('incomplete_or_unsupported_geometry')
        marker=geometry.coordinates if geometry and geometry.kind=='Point' else None
        objects.append(WorldObject.create(external_id=f'{kind}/{osm_id}',osm_type=kind,osm_id=osm_id,
            tags=tags,geometry=geometry,marker=marker,marker_method='source_point' if marker else None,
            provenance=provenance,ordinal=ordinal))
    return ProviderBatch(tuple(objects),profile,'partial' if reasons else 'complete',tuple(sorted(reasons)),
                         'overpass-bbox-observations','provider-order-unverified')


def acquire(repo,provider,bounds,profile,operation,scopes,*,transport=None,active=lambda:True,deadline=None):
    endpoint_host(provider['url']);group=provider['operator_group']
    q=query(bounds,profile)
    if not active():raise POIError('scanner_inactive')
    if not repo.allowed(group):raise POIError('circuit_open')
    slot=UpstreamPriority(repo).acquire(lane='background',group=group)
    if not slot:raise POIError('upstream_busy')
    ledger=CreditBudget(repo);reserved=False;sent=False;outcome_recorded=False
    try:
        reserved=ledger.reserve(provider['id'],operation,1,scopes=scopes)
        if not reserved:raise ContractError('budget_operation_already_used')
        if not active():raise POIError('scanner_inactive')
        deadline=min(deadline or float('inf'),time.monotonic()+35)
        if deadline<=time.monotonic():raise POIError('deadline')
        sent=True
        status,retry,body=(transport or bounded_http)(Config(deadline=35,max_response=4*1024*1024),
            provider['url'],q,min(30,deadline-time.monotonic()),deadline,secure=True)
        if status!=200:
            repo.outcome(group,False,max(3600,retry_delay(retry)))
            outcome_recorded=True
            raise POIError('http_'+str(status))
        if not active() or not repo.owns('@upstream',slot):raise POIError('scanner_inactive_or_slot_lost')
        dataset=body.get('osm3s',{}).get('timestamp_osm_base') if isinstance(body,dict) and isinstance(body.get('osm3s',{}),dict) else None
        if not isinstance(dataset,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',dataset):dataset=None
        batch=normalize(body,Provenance(provider['id'],VERSION,operation,time.time(),source_dataset_at=dataset,license_ref='ODbL-1.0'),profile)
        if time.monotonic()>=deadline:raise POIError('deadline')
        repo.outcome(group,True)
        return batch,dict(operation=operation,reported_credits=0,reserved_credits=0,
                          request_units=1,billing_state='settled',network_calls=1,gameplay_approved=False)
    except Exception:
        if sent and not outcome_recorded:repo.outcome(group,False,3600)
        raise
    finally:
        try:
            # This account counts attempts, not paid provider credits, including timeouts.
            if reserved:ledger.settle(provider['id'],operation,1 if sent else 0)
        finally:
            repo.release('@probe:'+group,slot);repo.release('@upstream',slot)
