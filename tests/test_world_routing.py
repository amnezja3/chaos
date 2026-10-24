import json
import os
import time
import unittest
from unittest.mock import patch, Mock

import test_world_maplark_pilot as fixtures
from poi_infrastructure.routing import Routing, GEOAPIFY
from poi_infrastructure.service import POIError, UpstreamUnavailable


class RoutingTests(unittest.TestCase):
    setUp=fixtures.PilotTests.setUp
    fetch=fixtures.PilotTests.fetch

    def route(self, chain):
        routing=Routing(self.service.repo);routing.initialize()
        old=routing.get('poi','live')
        routing.save('poi','live',old['revision'],chain,'test')
        return routing

    def overpass(self):
        p=self.registry.save('overpass',0,dict(name='Fixture',url='https://fixture.invalid/api/interpreter',
            operator_group='fixture.invalid',priority=0),'test')
        p=self.registry.decision(p['id'],p['revision'],'approved_for_defined_use',['normal_scan','storage'],
            dict(source_url='https://example.org/terms',reference='fixture',notes='fixture'),time.time()+3600,'test')
        p=self.registry.tested(p['id'],p['revision'],True,'test')
        return self.registry.enable(p['id'],p['revision'],True,'test')

    def test_default_matches_maplark_and_does_not_create_route_schema(self):
        r=Routing(self.service.repo).get('poi','live')
        self.assertEqual(r['chain'],['maplark'])
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(fixtures.normalized([fixtures.point()]),{})) as http:
            self.assertEqual(self.fetch()['elements'][0]['id'],1)
            self.fetch();http.assert_called_once()

    def test_reorder_restore_revision_conflict_and_permissions_unchanged(self):
        self.overpass();r=self.route(['overpass','maplark'])
        with self.assertRaisesRegex(POIError,'conflict'):
            r.save('poi','live',0,['maplark'],'test')
        self.assertEqual(r.restore('poi','live',1,'test')['chain'],['maplark'])
        self.assertTrue(all(p['enabled'] for p in self.registry.list()))
        for chain in (['maplark','maplark'],['missing'],['a']*4):
            with self.assertRaises(POIError):r.save('poi','live',2,chain,'test')

    def test_overpass_then_maplark_fallback_one_attempt_each(self):
        self.overpass();self.route(['overpass','maplark'])
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.scan_router.bounded_http',return_value=(502,None,None)) as over,patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(fixtures.normalized([fixtures.point()]),{})) as maplark:
            self.assertEqual(self.fetch()['elements'][0]['id'],1)
            over.assert_called_once();maplark.assert_called_once()
            self.assertGreater(maplark.call_args.kwargs['deadline'],time.monotonic())

    def test_all_fresh_local_before_first_network(self):
        self.overpass();r=self.route(['maplark'])
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(fixtures.normalized([fixtures.point()]),{})):
            self.fetch()
        r.save('poi','live',1,['overpass','maplark'],'test')
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.scan_router.bounded_http') as over,patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark') as maplark:
            self.assertEqual(self.fetch()['elements'][0]['id'],1)
            over.assert_not_called();maplark.assert_not_called()

    def test_geoapify_saved_but_not_allowed_to_replace_scanner(self):
        self.registry.save('geoapify',0,dict(name='Geoapify',url=GEOAPIFY,operator_group='api.geoapify.com',priority=0),'test')
        r=self.route(['geoapify','maplark'])
        self.assertEqual(r.describe()['routes'][0]['candidates'][0]['reason'],'geoapify_contract_unverified')
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(fixtures.normalized([]),{})) as m:
            self.assertEqual(self.fetch()['elements'],[]);m.assert_called_once()

    def test_revision_change_during_request_cannot_publish_or_fallback(self):
        self.overpass();r=self.route(['overpass','maplark'])
        def change(*args,**kwargs):
            r.save('poi','live',1,['maplark'],'other')
            return 200,None,{'elements':[]}
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.scan_router.bounded_http',side_effect=change),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark') as m:
            with self.assertRaisesRegex(POIError,'changed'):self.fetch()
            m.assert_not_called()

    def test_deadline_does_not_restart_for_fallback(self):
        self.overpass();self.route(['overpass','maplark'])
        from dataclasses import replace
        self.service.config=replace(self.service.config,deadline=.01)
        def slow(*a,**kw):
            time.sleep(.03)
            raise UpstreamUnavailable('http_read_timeout')
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.scan_router.bounded_http',side_effect=slow),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark') as m:
            with self.assertRaisesRegex(POIError,'deadline'):self.fetch()
            m.assert_not_called()

    def test_no_implicit_provider_when_route_empty(self):
        self.route([])
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch('poi_infrastructure.scan_router.bounded_http') as http:
            with self.assertRaisesRegex(POIError,'no_eligible'):self.fetch()
            http.assert_not_called()

    def test_routing_does_not_bypass_maplark_pilot_allowlist(self):
        self.route(['maplark'])
        self.options['_maplark_pilot']=False
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.maplark_pilot.acquire_maplark') as http:
            with self.assertRaisesRegex(POIError,'no_eligible'):self.fetch()
            http.assert_not_called()

    def test_stale_is_used_only_after_network_failure_and_not_after_expiry(self):
        from poi_infrastructure.world_contract import ContractError
        self.route(['maplark'])
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'):
            with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(fixtures.normalized([fixtures.point()]),{})):
                expected=self.fetch()
            with self.service.repo.transaction() as c:
                c.execute('UPDATE cache SET fetched=?',(time.time()-400,))
            with patch('poi_infrastructure.maplark_pilot.acquire_maplark',side_effect=ContractError('budget_exhausted')) as http:
                self.assertEqual(self.fetch(),expected)
                http.assert_called_once()
            with self.service.repo.transaction() as c:
                c.execute('UPDATE cache SET fetched=?',(time.time()-1900,))
            with patch('poi_infrastructure.maplark_pilot.acquire_maplark',side_effect=ContractError('budget_exhausted')):
                with self.assertRaisesRegex(ContractError,'exhausted'):self.fetch()

    def test_overpass_response_uses_cache_on_next_scan(self):
        self.overpass();self.route(['overpass'])
        response={'elements':[{'type':'node','id':1,'lat':52,'lon':21,'tags':{'amenity':'bank'}}]}
        with patch.dict(os.environ,CHAOS_POI_ROUTING_ENABLED='1'),patch(
                'poi_infrastructure.scan_router.bounded_http',return_value=(200,None,response)) as http:
            self.assertEqual(self.fetch(),response)
            self.assertEqual(self.fetch(),response)
            http.assert_called_once()
