"""Bounded Places acquisition for contract inspection, never a full CHAOS scan.

Offset pagination only establishes traversal of this category query. It does not
prove coverage of CHAOS tags, OSM identity or complete geographic geometry.
"""
import time
import uuid
from collections import Counter

from .providers import Registry
from .routing import GEOAPIFY
from .service import POIError
from .world_acquisition import acquire_features
from .world_adapters import plan_geoapify

CATEGORIES = ('commercial','catering','accommodation','education','healthcare',
              'service','entertainment','parking','public_transport')
PROFILES = {'broad': CATEGORIES, 'commercial': ('commercial',),
            'catering': ('catering',)}


def inspect_places(repo, provider_id, lat, lon, radius, *, pages=1, transport=None, profile='broad'):
    if profile not in PROFILES:
        raise POIError('geoapify_probe_profile_invalid')
    categories = PROFILES[profile]
    if type(pages) is not int or not 1<=pages<=3:
        raise POIError('geoapify_page_limit')
    plan_geoapify(lat,lon,radius,categories=categories,limit=100).authenticated_wire()
    registry=Registry(repo)
    candidate=next((p for p in registry.list() if p['id']==provider_id),None)
    if (not candidate or candidate['url']!=GEOAPIFY or not candidate.get('probe_allowed')
            or candidate['policy_status']!='approved_for_defined_use'
            or candidate['review_due_at']<=time.time() or 'small_probe' not in candidate['scopes']):
        raise POIError('provider_probe_not_approved')
    def active():
        return any(p['id']==provider_id and p['revision']==candidate['revision']
                   and p.get('probe_allowed') and p['review_due_at']>time.time() for p in registry.list())
    if not repo.acquire('@geoapify-diagnostic-rate',900):
        raise POIError('probe_rate_limited')
    deadline=time.monotonic()+35
    objects={}; bills=[]; page_end=False; repeated=False
    for page in range(pages):
        if time.monotonic()>=deadline or not active():
            raise POIError('deadline_or_provider_changed')
        plan=plan_geoapify(lat,lon,radius,categories=categories,limit=100,offset=page*100)
        batch,bill=acquire_features(repo,plan,uuid.uuid4().hex,5,account='geoapify',
            accept_variable_cost=True,transport=transport,still_active=active,deadline=deadline)
        bills.append(bill)
        before=len(objects)
        for obj in batch.objects:
            objects[obj.identity]=obj
        if len(batch.objects)<100:
            page_end=True
            break
        if len(objects)==before:
            repeated=True
            break
    tag_matches = Counter()
    for obj in objects.values():
        tags = dict(obj.tags)
        matches = [key for key in ('shop','amenity','office','healthcare') if tags.get(key)]
        if tags.get('atm') == 'yes': matches.append('atm=yes')
        if tags.get('man_made') == 'surveillance': matches.append('man_made=surveillance')
        tag_matches.update(matches or ['no_chaos_tag_match'])
    return dict(status='captured_not_approved', provider=provider_id, network_calls=len(bills),
        query=dict(profile=profile,categories=list(categories),latitude=lat,longitude=lon,
                   radius=radius,limit=100,method='POST'),
        raw_tag_matches=dict(tag_matches),
        geometry_types=dict(Counter(o.geometry.kind if o.geometry else 'missing' for o in objects.values())),
        objects=len(objects), pages=len(bills), page_end_observed=page_end,
        repeated_page=repeated, truncated=not page_end,
        osm_identified=sum(o.osm_id is not None for o in objects.values()),
        tag_keys=sorted({key for o in objects.values() for key,value in o.tags}),
        gameplay_approved=False, world_ingest=False, billing=bills,
        reasons=['category_mapping_unverified','spatial_selection_unverified',
                 'full_geometry_unverified'],
        note='Missing charge reports remain reserved; configured budget is not provider balance.')
