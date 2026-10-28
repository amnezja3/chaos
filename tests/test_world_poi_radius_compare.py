import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_world_region_probe as fixtures
from tools.world_region_probe import capture,BOUNDS,POI_RADIUS_CENTER
from tools.world_poi_radius_compare import compare
from poi_infrastructure.world_adapters import plan_maplark_region,plan_maplark
from poi_infrastructure.world_contract import ContractError


class RadiusCaptureTests(unittest.TestCase):
    setUp=fixtures.RegionProbeTests.setUp

    def test_radius_once_preserves_parent_and_registry(self):
        self.body['features']=[];self.headers['X-Returned']='0'
        kwargs=dict(execute=True,approve=True,accept_variable_cost=True,transport=self.transport,profile='poi',poi_radius=True)
        result=capture(self.repo.path,self.output,**kwargs)
        self.assertEqual(result['params'],dict(plan_maplark(*POI_RADIUS_CENTER,300,limit=1000).params))
        self.assertEqual(result['billing']['reported_credits'],3)
        self.assertFalse(result['world_ingest'])
        with self.assertRaisesRegex(ContractError,'already_used'):capture(self.repo.path,self.output,**kwargs)
        self.transport.assert_called_once()

    def test_invalid_radius_combination_before_network(self):
        with self.assertRaises(ContractError):capture(self.repo.path,poi_radius=True)
        self.transport.assert_not_called()


class CompareTests(unittest.TestCase):
    def test_vps_pair_preserves_geometry_selection_and_game_markers(self):
        root=Path(__file__).parent/'fixtures/poi/maplark_radius_1635'
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=compare(root/'parent',root/'radius')
        self.assertEqual(result['parent_sha256']['body'],'45e89d529d63fda01e4dc5e87e1dcca200624f7e1a21cce50b7be57762bb972c')
        self.assertEqual(result['radius_sha256']['body'],'6a339164b5b85a1597ca99045c2cac14f4d7a843a66fe2afe1ffb5499a8eb376')
        self.assertEqual((result['parent_objects'],result['radius_objects']),(23,18))
        self.assertTrue(result['observed_sample_pass'])
        self.assertTrue(result['hypotheses']['geometry_distance']['gameplay_rows_match'])
        center=result['hypotheses']['bounds_center_distance']
        self.assertFalse(center['gameplay_rows_match'])
        self.assertEqual(center['additional_in_radius'],['osm:way:1028355440'])
        self.assertFalse(result['regional_scan_approved'])

    def test_independent_sample_and_changes_not_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            feature=dict(type='Feature',id='node/1',properties={'tags':{'shop':'yes'}},geometry={'type':'Point','coordinates':[20.365,51.535]})
            for name,plan in [('parent',plan_maplark_region(BOUNDS,profile='poi')),('radius',plan_maplark(*POI_RADIUS_CENTER,300,limit=1000))]:
                target=root/name;target.mkdir()
                (target/'body.json').write_text(json.dumps(dict(type='FeatureCollection',features=[feature])))
                (target/'headers.json').write_text(json.dumps({'X-Returned':'1','X-Has-More':'false'}))
                (target/'report.json').write_text(json.dumps(dict(status='captured_not_certified',params=dict(plan.params),fetched_at=100,provider_revision=9)))
            with patch('socket.create_connection',side_effect=AssertionError('network')):
                result=compare(root/'parent',root/'radius')
            self.assertTrue(result['hypotheses']['geometry_distance']['identities_match'])
            self.assertFalse(result['regional_scan_approved'])
            self.assertEqual(result['changed_geometry'],[])
            feature['properties']['tags']['shop']='clothes'
            (root/'radius/body.json').write_text(json.dumps(dict(type='FeatureCollection',features=[feature])))
            self.assertEqual(compare(root/'parent',root/'radius')['changed_tags'],['osm:node:1'])
            self.assertFalse(compare(root/'parent',root/'radius')['observed_sample_pass'])
            feature['properties']['tags']['shop']='yes'
            (root/'radius/body.json').write_text(json.dumps(dict(type='FeatureCollection',features=[feature])))
            report_path=root/'radius/report.json'
            report=json.loads(report_path.read_text());report['provider_revision']=10
            report_path.write_text(json.dumps(report))
            result=compare(root/'parent',root/'radius')
            self.assertTrue(result['hypotheses']['geometry_distance']['gameplay_rows_match'])
            self.assertFalse(result['observed_sample_pass'])
            with self.assertRaises(ContractError):compare(root/'radius')
