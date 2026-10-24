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
        self.assertFalse(partial['local_filter']['observed_geometry_pass'])

    def test_outside_geometry_distinguished_from_envelope_selection(self):
        # L-shaped road goes around the query, while its envelope overlaps it.
        body=dict(type='FeatureCollection',features=[dict(type='Feature',id='way/7',
            properties=dict(tags={'highway':'residential','name':'not needed in report'}),
            geometry=dict(type='LineString',coordinates=[[20.359,51.55],[20.359,51.529],[20.38,51.529]]))])
        result=evaluate([20.36,51.53,20.37,51.54],'roads',body,{'X-Returned':'1','X-Has-More':'false'})
        detail=result['invalid_details'][0]
        self.assertEqual(detail['identity'],'osm:way:7')
        self.assertEqual(detail['reasons'],['geometry_outside_bbox'])
        self.assertTrue(detail['envelope_intersects_bbox'])
        self.assertNotIn('name',detail['classification_tags'])
        self.assertFalse(result['boundary_selection_pass'])
        self.assertTrue(result['local_filter']['observed_geometry_pass'])
        self.assertEqual(result['local_filter']['excluded_envelope_false_positives'],1)
        self.assertEqual(result['local_filter']['selected_objects'],0)
        self.assertFalse(result['local_filter']['proves_provider_completeness'])

    def test_layer_mismatch_and_boundary_touch_are_separate(self):
        features=[dict(type='Feature',id='way/'+str(i),properties=dict(tags=tags),
            geometry=dict(type='LineString',coordinates=[[20.36,51.53],[20.36,51.54]]))
            for i,tags in ((1,{'highway':'residential'}),(2,{'waterway':'stream'}))]
        result=evaluate([20.36,51.53,20.37,51.54],'roads',dict(type='FeatureCollection',features=features),
                        {'X-Returned':'2','X-Has-More':'false'})
        self.assertEqual(result['invalid_objects'],1)
        self.assertEqual(result['invalid_details'][0]['reasons'],['layer_mismatch'])
        self.assertEqual(result['invalid_reasons'],{'layer_mismatch':1})
        self.assertFalse(result['local_filter']['observed_geometry_pass'])
        self.assertEqual(result['local_filter']['selected_objects'],1)

    def test_filtered_neighbors_preserve_full_geometry_and_input(self):
        import copy
        body=dict(type='FeatureCollection',features=[
            dict(type='Feature',id='way/1',properties=dict(tags={'highway':'residential'}),
                 geometry=dict(type='LineString',coordinates=[[20.359,51.535],[20.371,51.535]])),
            dict(type='Feature',id='way/2',properties=dict(tags={'highway':'unclassified'}),
                 geometry=dict(type='LineString',coordinates=[[20.359,51.55],[20.359,51.529],[20.38,51.529]]))])
        before=copy.deepcopy(body)
        result=evaluate([20.36,51.53,20.37,51.54],'roads',body,{'X-Returned':'2','X-Has-More':'false'})
        self.assertEqual(body,before)
        self.assertTrue(result['local_filter']['observed_geometry_pass'])
        self.assertEqual(result['local_filter']['selected_objects'],1)
        self.assertTrue(result['local_filter']['neighbor_union_matches'])
        self.assertEqual(result['neighbor_candidates'],dict(left=1,right=1,crossing=1))
        self.assertFalse(result['region_certified'])

    def test_disjoint_envelope_is_not_silently_accepted(self):
        body=dict(type='FeatureCollection',features=[dict(type='Feature',id='way/3',
            properties=dict(tags={'highway':'residential'}),
            geometry=dict(type='LineString',coordinates=[[21,52],[21.01,52.01]]))])
        result=evaluate([20.36,51.53,20.37,51.54],'roads',body,{'X-Returned':'1','X-Has-More':'false'})
        self.assertEqual(result['local_filter']['blocking_objects'],1)
        self.assertFalse(result['local_filter']['observed_geometry_pass'])
