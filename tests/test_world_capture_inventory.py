import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.world_capture_inventory import inventory,inspect_file


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def write(self,name,body):
        path=self.root/name;path.write_text(json.dumps(body),encoding='utf-8');return path

    def test_geometry_evidence_and_digest_tampering(self):
        polygon=[[[0,0],[2,0],[2,2],[0,2],[0,0]],[[.5,.5],[1,.5],[1,1],[.5,1],[.5,.5]]]
        path=self.write('water.json',dict(type='FeatureCollection',features=[dict(type='Feature',properties={'natural':'water'},geometry=dict(type='MultiPolygon',coordinates=[polygon]))]))
        self.write('water.metadata.json',dict(synthetic=False,fixture_sha256_lf=hashlib.sha256(path.read_bytes()).hexdigest()))
        result=inspect_file(path)
        self.assertEqual(result['evidence'],'recorded_response')
        self.assertEqual(result['valid_geometry_types'],{'MultiPolygon':1})
        self.assertEqual(result['interior_rings'],1)
        self.assertFalse(result['certification'])
        path.write_bytes(path.read_bytes()+b' ')
        self.assertEqual(inspect_file(path)['evidence'],'unverified_metadata')

    def test_no_raw_properties_headers_or_network(self):
        self.write('headers.json',{'Authorization':'secret-example'})
        self.write('body.json',dict(type='FeatureCollection',features=[dict(properties={'email':'private-example'},geometry=None)]))
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=inventory([self.root])
        encoded=json.dumps(result)
        self.assertNotIn('secret-example',encoded);self.assertNotIn('private-example',encoded)
        self.assertEqual(result['network_calls'],0)
        self.assertEqual(next(i for i in result['items'] if i['file']=='body.json')['invalid_geometries'],1)

    def test_bounded_and_malformed_files(self):
        (self.root/'bad.json').write_text('{')
        self.write('other.json',{})
        with patch('tools.world_capture_inventory.MAX_FILES',1):
            result=inventory([self.root])
        self.assertTrue(result['truncated']);self.assertEqual(len(result['items']),1)
        with patch('tools.world_capture_inventory.MAX_BYTES',1):
            result=inventory([self.root/'other.json'])
        self.assertEqual(result['items'][0]['status'],'unreadable_or_invalid')

    def test_synthetic_is_not_real_and_duplicate_roots_are_deduplicated(self):
        path=self.write('synthetic.json',dict(type='FeatureCollection',features=[]))
        result=inventory([self.root,path])
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['evidence'],'synthetic_filename_only')

    def test_missing_root_is_reported_and_verified_hash_does_not_invent_origin(self):
        path=self.write('sample.json',{})
        self.write('sample.metadata.json',dict(fixture_sha256_lf=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.assertEqual(inspect_file(path)['evidence'],'verified_fixture_origin_unspecified')
        self.assertEqual(inventory([self.root/'missing'])['missing_roots'],['missing'])
