import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.world_runtime_check import inspect as inspect_runtime,FLAGS
from tools.world_land_water_inspect import inspect as inspect_product
from test_world_land_water import product,BOUNDS,DEPS


class ReleasePackageTests(unittest.TestCase):
    def test_routing_profile_changes_only_expected_routing_flag(self):
        env=dict(FLAGS,status='online',pm_cwd=str(Path.cwd()))
        processes=[dict(name='chaos',pm2_env=env)]
        self.assertFalse(inspect_runtime(processes,Path.cwd(),routing='1')['ok'])
        env['CHAOS_POI_ROUTING_ENABLED']='1'
        self.assertTrue(inspect_runtime(processes,Path.cwd(),routing='1')['ok'])
        self.assertFalse(inspect_runtime(processes,Path.cwd())['ok'])
        env['CHAOS_ADULT_POLICY_ENABLED']='1'
        self.assertFalse(inspect_runtime(processes,Path.cwd(),routing='1')['ok'])

    def test_runtime_baseline_filters_secrets_and_does_not_echo_invalid_values(self):
        env=dict(FLAGS,status='online',pm_cwd=str(Path.cwd()),SECRET_KEY='do-not-echo')
        processes=[dict(name='chaos',pm2_env=env),dict(name='unrelated',pm2_env={'secret':'private'})]
        result=inspect_runtime(processes,Path.cwd())
        self.assertTrue(result['ok']);self.assertNotIn('do-not-echo',json.dumps(result))
        env['CHAOS_ADULT_POLICY_ENABLED']='private-invalid'
        result=inspect_runtime(processes,Path.cwd())
        self.assertFalse(result['ok']);self.assertNotIn('private-invalid',json.dumps(result))

    def test_active_worker_or_missing_flag_or_wrong_cwd_requires_review(self):
        env=dict(FLAGS,status='online',pm_cwd=str(Path.cwd()))
        web=dict(name='chaos',pm2_env=env)
        self.assertFalse(inspect_runtime([web,dict(name='chaos-world-discovery-worker',pm2_env={'status':'online'})],Path.cwd())['ok'])
        self.assertFalse(inspect_runtime([web],Path.cwd()/'other')['ok'])
        env.pop('CHAOS_POI_ROUTING_ENABLED')
        self.assertFalse(inspect_runtime([web],Path.cwd())['ok'])

    def test_offline_product_inspector_checks_digest_and_preserves_files(self):
        with tempfile.TemporaryDirectory() as folder:
            body=Path(folder)/'body.json';manifest=Path(folder)/'manifest.json'
            raw=json.dumps(product()).encode();body.write_bytes(raw)
            meta=dict(bounds=BOUNDS,provider='fixture',snapshot='sample',fetched_at=1,
                dataset_version='v1',license_ref='synthetic',dependencies=DEPS,body_sha256=hashlib.sha256(raw).hexdigest())
            manifest.write_text(json.dumps(meta))
            with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
                result=inspect_product(body,manifest)
            self.assertEqual(result['roles'],{'land':1,'sea':1})
            self.assertFalse(result['region_certified']);self.assertEqual(body.read_bytes(),raw)
            body.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'digest_mismatch'):inspect_product(body,manifest)
