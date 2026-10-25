"""Next water evidence probe stays bounded; all HTTP is mocked."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import time
import unittest
from unittest.mock import patch

import test_world_region_probe
from test_world_region_water import water_body,HEADERS
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.service import UpstreamUnavailable
from tools.world_region_probe import capture,BOUNDS
from tools.world_region_plan import evaluate,main


REGION=(20.361,51.531,20.369,51.539)
SCOPE='region-probe:water-topology-v1'


class WaterTopologyProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_world_region_probe.RegionProbeTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.fixture.transport.return_value=(200,None,dict(body=water_body(),response_headers=HEADERS))

    def call(self,bounds=REGION):
        return capture(self.fixture.repo.path,self.fixture.output,profile='inland_water',
            water_bounds=bounds,execute=True,approve=True,accept_variable_cost=True,
            transport=self.fixture.transport)

    def test_plan_is_offline_and_repeat_identity_is_stable(self):
        missing=Path(self.fixture.tmp.name)/'missing.sqlite3'
        a=capture(missing,profile='inland_water',water_bounds=REGION)
        b=capture(missing,profile='inland_water',water_bounds=list(REGION))
        self.assertEqual(a['operation'],b['operation'])
        self.assertEqual((a['network_calls'],a['max_network_calls'],a['shared_probe_limit']),(0,1,40))
        self.assertFalse(missing.exists());self.fixture.transport.assert_not_called()

    def test_missing_cli_priority_fails_before_scope_or_output_and_can_resume(self):
        with patch.dict('os.environ',CHAOS_POI_PRIORITY_ENABLED='0'):
            with self.assertRaisesRegex(ContractError,'background_priority_required'):self.call()
        self.assertFalse(self.fixture.output.exists())
        self.assertIsNone(self.fixture.ledger.scope_status('maplark',SCOPE))
        self.assertEqual(self.fixture.ledger.status('maplark')[0]['committed'],0)
        self.fixture.transport.assert_not_called()
        # Once configuration is corrected, the same operation remains unused.
        self.assertEqual(self.call()['network_calls'],1)

    def test_bounds_profile_and_existing_region_rejected_before_network(self):
        for kwargs in (dict(water_bounds=REGION,profile='roads'),
                       dict(water_bounds=REGION,profile='waterways'),
                       dict(water_bounds=BOUNDS,profile='inland_water'),
                       dict(water_bounds=(20.36,51.53,20.375,51.54),profile='inland_water'),
                       dict(water_bounds=(20,51,19,52),profile='inland_water'),
                       dict(water_bounds=(20,51,float('nan'),52),profile='inland_water')):
            with self.subTest(kwargs=kwargs),self.assertRaises(ContractError):
                capture(self.fixture.repo.path,execute=True,**kwargs)
        self.fixture.transport.assert_not_called()

    def test_single_capture_reports_holes_and_multipart_without_approval(self):
        report=self.call()
        self.assertTrue(report['inspection']['topology']['water_surface_with_holes_observed'])
        self.assertTrue(report['inspection']['topology']['water_multipolygon_observed'])
        self.assertFalse(report['world_ingest']);self.assertFalse(report['region_certified'])
        self.assertEqual(report['billing']['reported_credits'],3)
        with self.assertRaisesRegex(ContractError,'already_used'):self.call()
        self.fixture.transport.assert_called_once()

    def test_timeout_stays_reserved_and_second_region_shares_allowance(self):
        self.fixture.transport.side_effect=UpstreamUnavailable('http_read_timeout')
        with self.assertRaises(UpstreamUnavailable):self.call()
        with self.assertRaisesRegex(ContractError,'already_used'):self.call()
        self.fixture.output=Path(self.fixture.tmp.name)/'second'
        with self.assertRaises(UpstreamUnavailable):self.call((20.362,51.531,20.369,51.539))
        self.assertEqual(self.fixture.ledger.scope_status('maplark',SCOPE)['committed'],40)
        self.fixture.output=Path(self.fixture.tmp.name)/'third'
        with self.assertRaises(Exception):self.call((20.363,51.531,20.369,51.539))
        self.assertEqual(self.fixture.transport.call_count,2)

    def test_expired_diagnostic_window_is_not_reopened(self):
        self.fixture.ledger.configure_scope('maplark',SCOPE,time.time()-100,time.time()-1,40)
        with self.assertRaisesRegex(ContractError,'window_expired'):self.call()
        self.fixture.transport.assert_not_called()

    def test_outside_hole_and_multipart_do_not_pass_selected_water_evidence(self):
        report=evaluate((20.39,51.53,20.40,51.54),'inland_water',water_body(),HEADERS)
        self.assertGreater(report['topology']['interior_rings'],0)
        self.assertFalse(report['topology']['water_surface_with_holes_observed'])
        self.assertFalse(report['topology']['water_multipolygon_observed'])
        self.assertEqual(report['topology']['selected_hole_ids'],[])
        self.assertEqual(report['candidate']['status'],'blocked')

    def test_offline_cli_requires_observed_topology_and_preserves_capture(self):
        body=Path(self.fixture.tmp.name)/'body.json';headers=body.with_name('headers.json')
        headers.write_text(json.dumps(HEADERS),encoding='utf8')
        for kind,expected in (('Polygon',2),('MultiPolygon',0)):
            body.write_text(json.dumps(water_body(kind)),encoding='utf8')
            before=body.read_bytes();output=io.StringIO()
            args=['world_region_plan','--layer','inland_water','--body',str(body),
                  '--headers',str(headers),'--require-water-holes','--require-water-multipart']
            with patch('sys.argv',args),redirect_stdout(output),patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
                self.assertEqual(main(),expected)
            report=json.loads(output.getvalue())
            self.assertEqual(report['requested_topology_pass'],expected==0)
            self.assertFalse(report['region_certified'])
            self.assertEqual(body.read_bytes(),before)

    def test_topology_requirement_cannot_be_used_with_plan_only(self):
        with patch('sys.argv',['world_region_plan','--layer','inland_water','--require-water-holes']),self.assertRaises(SystemExit) as caught:
            main()
        self.assertEqual(caught.exception.code,2)


if __name__=='__main__':unittest.main()
