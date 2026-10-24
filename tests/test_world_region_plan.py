import unittest
from unittest.mock import patch
from dataclasses import replace
from poi_infrastructure.world_adapters import plan_maplark_region,plan_maplark
from poi_infrastructure.world_contract import ContractError
from tools.world_region_plan import evaluate


class RegionPlanTests(unittest.TestCase):
    def test_bbox_allowlist_and_radius_contract_unchanged(self):
        plan=plan_maplark_region((20.36,51.53,20.37,51.54))
        with patch.dict('os.environ',CHAOS_MAPLARK_API_KEY='fixture'):
            path,headers=plan.authenticated_wire()
            self.assertIn('bbox=',path);self.assertNotIn('fixture',path)
            bad=replace(plan,params=plan.params+(('zoom','3'),))
            with self.assertRaises(ContractError):bad.authenticated_wire()
        self.assertIn('location',dict(plan_maplark(52,21,300).params))
        with self.assertRaises(ContractError):plan_maplark_region((0,0,1,1))
        with self.assertRaises(ContractError):plan_maplark_region((20,51,20.01,51.01),profile='land_water')

    def test_offline_neighbor_observation_is_not_certificate(self):
        body=dict(type='FeatureCollection',features=[dict(type='Feature',id='way/1',
            properties=dict(tags={'highway':'residential'}),
            geometry=dict(type='LineString',coordinates=[[20.359,51.535],[20.371,51.535]]))])
        result=evaluate([20.36,51.53,20.37,51.54],'roads',body,{'X-Returned':'1','X-Has-More':'false'})
        self.assertTrue(result['boundary_selection_pass'])
        self.assertFalse(result['region_certified']);self.assertEqual(result['network_calls'],0)
        self.assertEqual(result['neighbor_candidates'],dict(left=1,right=1,crossing=1))
        partial=evaluate([20.36,51.53,20.37,51.54],'roads',body,{'X-Returned':'1','X-Has-More':'true'})
        self.assertFalse(partial['boundary_selection_pass'])
