import os
import time
import unittest
from unittest.mock import patch, Mock

import test_world_maplark_pilot as fixtures
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.geoapify import inspect_places
from poi_infrastructure.routing import GEOAPIFY
from poi_infrastructure.service import POIError, UpstreamUnavailable


def response(count, start=0):
    return 200,None,{'response_headers':{},'body':{'type':'FeatureCollection','features':[
        {'type':'Feature','geometry':{'type':'Point','coordinates':[21,52]},
         'properties':{'place_id':'place'+str(i),'datasource':{'raw':{
             'osm_type':'n','osm_id':i+1,'amenity':'bank'}}}} for i in range(start,start+count)]}}


class GeoapifyTests(unittest.TestCase):
    def setUp(self):
        fixtures.PilotTests.setUp(self)
        p=self.registry.save('geoapify',0,dict(name='Geoapify',url=GEOAPIFY,operator_group='api.geoapify.com',priority=0),'test')
        self.registry.decision(p['id'],p['revision'],'approved_for_defined_use',['small_probe'],
            dict(source_url='https://geoapify.com/terms',reference='fixture',notes='fixture'),time.time()+3600,'test')
        self.ledger=CreditBudget(self.service.repo)
        self.ledger.configure_window('geoapify','probe',time.time()-1,time.time()+3600,20)
        env=patch.dict(os.environ,CHAOS_GEOAPIFY_API_KEY='synthetic-secret');env.start();self.addCleanup(env.stop)

    def test_pagination_shared_deadline_cost_and_no_gameplay_approval(self):
        http=Mock(side_effect=[response(100),response(2,100)])
        result=inspect_places(self.service.repo,'geoapify',52,21,300,pages=3,transport=http)
        self.assertEqual(result['objects'],102)
        self.assertTrue(result['page_end_observed']);self.assertFalse(result['gameplay_approved'])
        self.assertEqual(http.call_count,2)
        self.assertEqual(http.call_args_list[0].args[4],http.call_args_list[1].args[4])
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],10)
        self.assertTrue(all(b['billing_state']=='uncertain' for b in result['billing']))
        self.assertNotIn('synthetic-secret',str(result))

    def test_page_cap_and_duplicate_page_stop(self):
        http=Mock(side_effect=[response(100),response(100)])
        result=inspect_places(self.service.repo,'geoapify',52,21,300,pages=3,transport=http)
        self.assertTrue(result['repeated_page']);self.assertTrue(result['truncated'])
        self.assertEqual(http.call_count,2)

    def test_timeout_keeps_reservation_no_retry(self):
        http=Mock(side_effect=UpstreamUnavailable('http_read_timeout'))
        with self.assertRaises(UpstreamUnavailable):inspect_places(self.service.repo,'geoapify',52,21,300,transport=http)
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],5)
        http.assert_called_once()
        with self.assertRaisesRegex(POIError,'rate_limited'):
            inspect_places(self.service.repo,'geoapify',52,21,300,transport=http)

    def test_missing_approval_never_sends(self):
        with self.service.repo.transaction() as c:
            c.execute("DELETE FROM poi_provider_config WHERE id='geoapify'")
        http=Mock()
        with self.assertRaisesRegex(POIError,'approved'):
            inspect_places(self.service.repo,'geoapify',52,21,300,transport=http)
        http.assert_not_called()

    def test_budget_exhaustion_stops_before_http(self):
        from poi_infrastructure.world_contract import ContractError
        self.ledger.reserve('geoapify','other',20)
        http=Mock()
        with self.assertRaisesRegex(ContractError,'exhausted'):
            inspect_places(self.service.repo,'geoapify',52,21,300,transport=http)
        http.assert_not_called()
