import copy
import json
from pathlib import Path
import tempfile
import unittest
from shapely.geometry import box,shape
from tools.world_region_compare import compare,inspect_directories
from tools.world_region_probe import PARTS
from tools.world_region_plan import evaluate
from poi_infrastructure.world_contract import ContractError


class RegionCompareTests(unittest.TestCase):
    def samples(self):
        # Synthetic independent responses derived from a real geometry fixture.
        body=json.loads((Path(__file__).parent/'fixtures/poi/maplark_roads_bbox_20261024.json').read_text())
        result={}
        for part,bounds in PARTS.items():
            features=[copy.deepcopy(f) for f in body['features'] if shape(f['geometry']).envelope.intersects(box(*bounds))]
            result[part]=(dict(type='FeatureCollection',features=features),{'X-Returned':str(len(features)),'X-Has-More':'false'})
        return result

    def test_matching_samples_do_not_certify_dataset(self):
        result=compare(self.samples())
        self.assertTrue(result['sample_comparison_pass'])
        self.assertFalse(result['region_certified']);self.assertFalse(result['dataset_version_verified'])
        self.assertEqual(result['network_calls'],0)
        self.assertEqual(result['comparisons']['left']['local_objects'],33)
        self.assertEqual(result['comparisons']['right']['local_objects'],54)

    def test_missing_independent_object_fails(self):
        samples=self.samples();body,headers=samples['left']
        victim=next(f for f in body['features'] if shape(f['geometry']).intersects(box(*PARTS['left'])))
        body['features'].remove(victim);headers['X-Returned']=str(len(body['features']))
        result=compare(samples)
        self.assertFalse(result['sample_comparison_pass'])
        self.assertEqual(len(result['comparisons']['left']['missing_from_independent']),1)

    def test_clipped_full_line_is_detected(self):
        samples=self.samples();body,_=samples['right']
        for f in body['features']:
            geom=shape(f['geometry']);clipped=geom.intersection(box(*PARTS['right']))
            if not clipped.is_empty and clipped.geom_type=='LineString' and not geom.equals(clipped):
                f['geometry']=clipped.__geo_interface__;break
        else:self.fail('crossing line fixture missing')
        result=compare(samples)
        self.assertFalse(result['sample_comparison_pass'])
        self.assertTrue(result['comparisons']['right']['changed_full_geometry'])

    def test_partial_response_cannot_pass_matching_ids(self):
        samples=self.samples();samples['right'][1]['X-Has-More']='true'
        self.assertFalse(compare(samples)['sample_comparison_pass'])

    def test_reports_bind_query_and_revision_not_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths={}
            for part,(body,headers) in self.samples().items():
                path=Path(tmp)/part;path.mkdir();paths[part]=str(path)
                for name,value in {'body':body,'headers':headers,'report':dict(status='captured_not_certified',
                    params=evaluate(PARTS[part],'roads')['params'],provider_revision=9)}.items():
                    (path/(name+'.json')).write_text(json.dumps(value),encoding='utf8')
            self.assertTrue(inspect_directories(paths)['sample_comparison_pass'])
            report_path=Path(paths['right'])/'report.json';report=json.loads(report_path.read_text())
            report['provider_revision']=10;report_path.write_text(json.dumps(report))
            self.assertFalse(inspect_directories(paths)['sample_comparison_pass'])
            report['params']['bbox']='0,0,1,1';report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ContractError,'query_mismatch'):inspect_directories(paths)
