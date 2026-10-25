from dataclasses import replace
import json
import time
import unittest
from unittest.mock import Mock,patch

import test_world_discovery_worker as fixtures
from poi_infrastructure.overpass_world import normalize,query,VERSION
from poi_infrastructure.world_contract import Provenance
from poi_infrastructure.discovery_producer import prepare_jobs
from poi_infrastructure.discovery_worker import DiscoveryWorker
from poi_infrastructure.routing import Routing,capability


def points(coords):return [dict(lon=x,lat=y) for x,y in coords]
def ring(x,y,size):return [(x,y),(x+size,y),(x+size,y+size),(x,y+size),(x,y)]


class OverpassGeometryTests(unittest.TestCase):
    def batch(self,elements):
        return normalize(dict(elements=elements),Provenance('overpass-test',VERSION,'test',time.time(),license_ref='ODbL-1.0'),'inland_water')

    def test_relation_parts_and_holes_retained(self):
        members=[dict(type='way',role='outer',geometry=points(ring(20,51,.01))),
                 dict(type='way',role='inner',geometry=points(ring(20.002,51.002,.002))),
                 dict(type='way',role='outer',geometry=points(ring(21,52,.01)))]
        batch=self.batch([dict(type='relation',id=1,tags={'type':'multipolygon','natural':'water'},members=members)])
        geometry=batch.objects[0].geometry
        self.assertEqual(geometry.kind,'MultiPolygon')
        self.assertEqual(len(geometry.coordinates),2)
        self.assertEqual(sum(len(p)-1 for p in geometry.coordinates),1)
        self.assertEqual(batch.completeness,'complete')

    def test_split_outer_joins_but_missing_member_is_explicit_partial(self):
        coords=ring(20,51,.01)
        members=[dict(type='way',role='outer',geometry=points(coords[:3])),
                 dict(type='way',role='outer',geometry=points(coords[2:]))]
        element=dict(type='relation',id=2,tags={'type':'multipolygon','natural':'water'},members=members)
        self.assertEqual(self.batch([element]).objects[0].geometry.kind,'Polygon')
        members.pop()
        batch=self.batch([element])
        self.assertIsNone(batch.objects[0].geometry)
        self.assertEqual(batch.completeness,'partial')

    def test_query_has_full_geometry_and_fixed_resource_caps(self):
        wire=query((20,51,20.01,51.01),'roads')
        self.assertIn('out body geom 1001',wire)
        self.assertIn('[timeout:25]',wire)
        self.assertNotIn('out center',wire)
        with self.assertRaises(ValueError):query((20,51,21,52),'roads')


class OverpassWorkerTests(unittest.TestCase):
    setUp=fixtures.DiscoveryWorkerTests.setUp
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def configure(self):
        provider=dict(self.provider,id='overpass-test',url='https://overpass.example.org/api/interpreter',
                      operator_group='overpass.example.org',review_due_at=time.time()+40*86400)
        with self.repo.transaction() as c:
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',(provider['id'],1,json.dumps(provider)))
        permit=replace(self.permit,provider_id='overpass-test',acquisition=VERSION,
                       retention_seconds=604800,refresh_seconds=604800,reservation=1)
        self.ledger.configure_recurring('overpass-test',120,3720)
        for scope in permit.budget_scopes('roads'):
            self.ledger.configure_scope('overpass-test',scope,time.time()-1,permit.until,120)
        prepare_jobs(self.repo,permit,apply=True)
        self.transport.return_value=(200,None,dict(elements=[dict(type='way',id=5,tags={'highway':'service'},geometry=points([(21,52),(21.01,52.01)]))]))
        return DiscoveryWorker(self.repo,permit,enabled=lambda:True,transport=self.transport)

    def test_geometry_is_archived_request_quota_separate_from_paid_account(self):
        worker=self.configure()
        self.assertIsNone(capability(dict(url='https://overpass.example.org/api/interpreter'),'roads','background'))
        outcome=worker.run_one()
        self.assertEqual(outcome['status'],'committed')
        self.assertEqual(outcome['billing']['reported_credits'],0)
        self.assertEqual(self.ledger.status('overpass-test')[0]['committed'],1)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)
        self.assertTrue(self.transport.call_args.kwargs['secure'])

    def test_timeout_backoff_preserves_paid_ledger_and_can_recover_later(self):
        worker=self.configure()
        from poi_infrastructure.service import UpstreamUnavailable
        self.transport.side_effect=UpstreamUnavailable('http_read_timeout')
        outcome=worker.run_one()
        self.assertEqual(outcome['network_calls'],1)
        self.assertEqual(self.ledger.status('overpass-test')[0]['committed'],1)
        self.assertFalse(self.repo.allowed('overpass.example.org'))
        self.assertEqual(prepare_jobs(self.repo,worker.permit,apply=True)['jobs'],[])
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_refresh SET due=0')
        self.assertEqual(len(prepare_jobs(self.repo,worker.permit,apply=True)['jobs']),1)
        self.transport.assert_called_once()

    def test_background_enable_does_not_authorize_gameplay(self):
        from poi_infrastructure.providers import Registry
        from poi_infrastructure.routing import reason
        self.configure()
        registry=Registry(self.repo)
        provider=registry.enable('overpass-test',1,True,'test')
        self.assertIsNone(reason(provider,'roads','background'))
        self.assertEqual(reason(provider,'poi','live'),'approval_required')
