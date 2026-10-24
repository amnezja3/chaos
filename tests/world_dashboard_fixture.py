"""Synthetic evidence for local UI/tests only, never a provider certificate."""
import json
import time
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import SelectionProof, AREA_SELECTION
from poi_infrastructure.world_contract import Geometry,Provenance,ProviderBatch,WorldObject


def seed(repo):
    registry=Registry(repo);registry.initialize()
    world=CanonicalWorldRepository(repo);world.initialize_canonical()
    now=time.time()
    with repo.transaction() as c:
        p=dict(id='fixture',revision=1,name='Synthetic fixture',url='https://fixture.invalid/api/interpreter',
            operator_group='fixture.invalid',priority=100,technical_status='tested_ok',
            enabled=False,policy_status='approved_for_defined_use',scopes=['storage','world_storage'],
            review_due_at=now+86400,evidence=dict(reference='synthetic-only',source_url='https://example.org',notes='synthetic',checked_by='fixture',checked_at=now))
        # Publication is enabled only within this isolated fixture construction.
        p['enabled']=True
        c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',('fixture',1,json.dumps(p)))
    ids=[]
    for i,(layer,mode,empty) in enumerate((('roads','area',False),('roads','area',True),('inland_water',None,False),('poi','exact',False))):
        x=21+i*.03;y=52
        tags={'highway':'residential'} if layer=='roads' else {'natural':'water'} if layer=='inland_water' else {'shop':'books'}
        geometry=(dict(type='LineString',coordinates=[[x,y],[x+.01,y+.01]]) if layer=='roads' else
                  dict(type='Polygon',coordinates=[[[x,y],[x+.01,y],[x+.01,y+.01],[x,y+.01],[x,y]]]) if layer=='inland_water' else
                  dict(type='Point',coordinates=[x,y]))
        obj=WorldObject.create(external_id=str(i+1),tags=tags,geometry=Geometry.parse(geometry),
            marker=None,marker_method=None,ordinal=0,osm_type='way' if layer!='poi' else 'node',osm_id=i+1,
            provenance=Provenance('fixture','fixture-v1','synthetic',now-1,license_ref='synthetic-only'))
        selection=AREA_SELECTION if mode=='area' else 'maplark-radius-unverified'
        profile=layer if layer!='poi' else 'poi-gameplay-v1'
        batch=ProviderBatch(() if empty else (obj,),profile,'complete',(),selection,'source')
        key='fixture-'+str(i);owner=repo.acquire(key,120)
        proof=(SelectionProof(mode,layer,profile,selection,'fixture-v1',key,
                 (x-.002,y-.002,x+.012,y+.012) if mode=='area' else None,
                 'synthetic-certificate' if mode=='area' else None) if mode else None)
        ids.append(world.publish_batch(key,owner,batch,provider='fixture',revision=1,
            storage_reference='synthetic-only',fresh_until=now+300,usable_until=now+1800,
            coverage=proof,certified_selections=(('fixture','fixture-v1',layer,selection,'synthetic-certificate'),)))
        repo.release(key,owner)
    return ids
