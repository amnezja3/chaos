import json
from pathlib import Path
from contextlib import closing
import unittest
from unittest.mock import patch
import test_world_region_probe as fixtures
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_contract import ContractError
from tools.world_paris_region_acceptance import run,OPERATION,DIAGNOSTIC_OPERATION,COMPACT_OPERATION,COMPACT_BOUNDS


class ParisAcceptanceTests(unittest.TestCase):
    def test_verified_publication_requires_reader_preflight_and_forbids_retry(self):
        result=run(self.repo.path,self.backup,execute=True,accept=True,
                   transport=self.transport,verified_v5=True)
        self.assertTrue(result['acceptance_ready'])
        self.assertEqual(len(result['preflight']),2)
        self.assertTrue(all(c['status']=='ready' and c['expected_key'] for c in result['preflight']))
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'retry.sqlite3',execute=True,accept=True,
                transport=self.transport,verified_v5=True)
        self.transport.assert_called_once()

    def test_verified_reader_miss_does_not_approve_or_retry(self):
        with patch('tools.world_region_preflight.inspect',return_value={'status':'not_ready','reason':'regional_reader_miss'}):
            result=run(self.repo.path,self.backup,execute=True,accept=True,
                       transport=self.transport,verified_v5=True)
        self.assertEqual(result['status'],'published')
        self.assertFalse(result['acceptance_ready'])
        self.assertEqual(result['billing']['reported_credits'],3)
        self.transport.assert_called_once()

    def test_read_diagnostic_does_not_mutate_or_fetch(self):
        from tools.world_paris_read_diagnostic import inspect
        result=run(self.repo.path,self.backup,execute=True,accept=True,
                   transport=self.transport,live_v4=True)
        with closing(self.repo.connect()) as c:before='\n'.join(c.iterdump())
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            diagnostic=inspect(self.repo.path,result['snapshot'],['000000000000'])
            key=diagnostic['positions'][0]['expected_key']
            matched=inspect(self.repo.path,result['snapshot'],[key])
            missing=inspect(self.repo.path,'absent',[])
        self.assertTrue(diagnostic['digest_ok'])
        self.assertTrue(diagnostic['storage_reference_matches'])
        self.assertFalse(diagnostic['positions'][0]['matches_supplied_scan'])
        self.assertTrue(matched['positions'][0]['matches_supplied_scan'])
        self.assertEqual(diagnostic['positions'][0]['objects'],1)
        self.assertFalse(diagnostic['live_acceptance'])
        self.assertEqual(missing['status'],'snapshot_missing')
        with closing(self.repo.connect()) as c:self.assertEqual(before,'\n'.join(c.iterdump()))
        self.transport.assert_called_once()

    def test_live_refresh_preserves_previous_operation_and_rejects_retry(self):
        from tools.world_paris_region_acceptance import LIVE_OPERATION
        from poi_infrastructure.credit_budget import CreditBudget
        import time
        run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport,compact_v3=True)
        with closing(self.repo.connect()) as c:
            before=tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(COMPACT_OPERATION,)).fetchone())
        ledger=CreditBudget(self.repo)
        now=time.time()
        ledger.configure_scope('maplark','unrelated-background-limit',now-100,now-1,20)
        scope_before=ledger.scope_status('maplark','unrelated-background-limit')
        result=run(self.repo.path,self.output.parent/'live.sqlite3',execute=True,accept=True,
                   transport=self.transport,live_v4=True)
        self.assertEqual(result['operation'],LIVE_OPERATION)
        self.assertEqual(result['bounds'],COMPACT_BOUNDS)
        self.assertTrue(result['acceptance_ready'])
        self.assertEqual(result['selection_profile'],'chaos-maplark-region-geometry-v2')
        self.assertEqual(scope_before,ledger.scope_status('maplark','unrelated-background-limit'))
        with closing(self.repo.connect()) as c:
            self.assertEqual(before,tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(COMPACT_OPERATION,)).fetchone()))
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'retry-live.sqlite3',execute=True,accept=True,
                transport=self.transport,live_v4=True)
        with self.assertRaisesRegex(ContractError,'mode_conflict'):
            run('missing',live_v4=True,compact_v3=True)
        self.assertEqual(self.transport.call_count,2)

    def setUp(self):
        fixtures.RegionProbeTests.setUp(self)
        CanonicalWorldRepository(self.repo).initialize_canonical()
        p=Registry(self.repo).list()[0]
        p['scopes']=['normal_scan','storage','world_storage','background_refresh']
        with self.repo.transaction() as c:
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        self.body['features']=[dict(type='Feature',id='node/1',properties={'tags':{'shop':'yes'}},
                                  geometry=dict(type='Point',coordinates=[2.338,48.861]))]
        self.backup=self.output.parent/'backup.sqlite3'

    def test_plan_without_database_and_consent_before_network(self):
        self.assertEqual(run('missing')['network_calls'],0)
        with self.assertRaises(ContractError):run(self.repo.path,self.backup,execute=True)
        self.transport.assert_not_called()

    def test_compact_plan_and_conflicting_modes_do_not_call_network(self):
        result=run('missing',compact_v3=True)
        self.assertEqual(result['bounds'],COMPACT_BOUNDS)
        self.assertEqual(result['operation'],COMPACT_OPERATION)
        self.assertEqual(result['max_network_calls'],1)
        with self.assertRaises(ContractError):run('missing',compact_v3=True,diagnostic_v2=True)
        self.transport.assert_not_called()

    def test_offline_positions_explain_partial_capture_without_network(self):
        from tools.world_paris_positions import inspect
        from poi_infrastructure.world_adapters import plan_maplark_region
        self.output.mkdir()
        self.headers['X-Has-More']='true'
        for name,value in [('body.json',self.body),('headers.json',self.headers),
                           ('request.json',dict(params=dict(plan_maplark_region(COMPACT_BOUNDS,profile='poi',limit=1000).params)))]:
            (self.output/name).write_text(json.dumps(value))
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=inspect(self.output)
        self.assertEqual(result['position_rejections'],{'regional_response_incomplete':25})
        self.assertFalse(result['acceptance_pass'])
        self.assertFalse(result['live_freshness_checked'])
        self.transport.assert_not_called()

    def test_compact_publication_preserves_v2_charge_and_records_correct_extent(self):
        self.headers['X-Has-More']='true'
        run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport,diagnostic_v2=True)
        with closing(self.repo.connect()) as c:
            before=tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(DIAGNOSTIC_OPERATION,)).fetchone())
        self.headers['X-Has-More']='false'
        result=run(self.repo.path,self.output.parent/'compact.sqlite3',execute=True,accept=True,
                   transport=self.transport,compact_v3=True)
        self.assertTrue(result['acceptance_ready'])
        request=json.loads((Path(result['diagnostics'])/'request.json').read_text())
        self.assertEqual(request['params']['bbox'],'2.3335,48.858,2.3425,48.864')
        self.assertEqual(request['params']['limit'],'1000')
        with closing(self.repo.connect()) as c:
            after=tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(DIAGNOSTIC_OPERATION,)).fetchone())
            raw=json.loads(c.execute('SELECT payload FROM world_snapshot WHERE id=?',(result['snapshot'],)).fetchone()[0])
        self.assertEqual(before,after)
        self.assertEqual(raw['observation_context']['demand_bounds'],list(COMPACT_BOUNDS))
        self.assertEqual(raw['observation_context']['request_params'],request['params'])
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'retry.sqlite3',execute=True,accept=True,
                transport=self.transport,compact_v3=True)
        self.assertEqual(self.transport.call_count,2)

    def test_one_request_publishes_native_bbox_and_positions_without_policy_changes(self):
        before=Registry(self.repo).list()
        result=run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport)
        self.assertEqual(result['status'],'published')
        self.assertTrue(result['acceptance_ready'])
        self.assertEqual(result['billing']['reported_credits'],3)
        self.assertEqual(Registry(self.repo).list(),before)
        self.assertTrue(self.backup.exists())
        self.assertEqual(CanonicalWorldRepository(self.repo).status()['snapshots'],1)
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'second.sqlite3',execute=True,accept=True,transport=self.transport)
        self.transport.assert_called_once()

    def test_v2_preserves_previous_charge_and_incomplete_artifacts(self):
        self.headers['X-Has-More']='true'
        run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport)
        with closing(self.repo.connect()) as c:
            before=tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(OPERATION,)).fetchone())
        self.headers['Authorization']='must-not-save'
        self.body['features'][0]['properties']['tags']['name']='fixture-secret-xyz'
        backup=self.output.parent/'v2.sqlite3'
        result=run(self.repo.path,backup,execute=True,accept=True,transport=self.transport,diagnostic_v2=True)
        self.assertEqual(result['operation'],DIAGNOSTIC_OPERATION)
        self.assertEqual(result['status'],'response_incomplete')
        directory=Path(result['diagnostics'])
        self.assertEqual(json.loads((directory/'headers.json').read_text())['X-Has-More'],'true')
        self.assertEqual(json.loads((directory/'report.json').read_text())['billing']['reported_credits'],3)
        artifacts=''.join(p.read_text() for p in directory.iterdir())
        self.assertNotIn('fixture-secret-xyz',artifacts)
        self.assertNotIn('must-not-save',artifacts)
        with closing(self.repo.connect()) as c:
            after=tuple(c.execute('SELECT * FROM world_credit_operation WHERE operation=?',(OPERATION,)).fetchone())
        self.assertEqual(before,after)
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'v3.sqlite3',execute=True,accept=True,transport=self.transport,diagnostic_v2=True)
        self.assertEqual(self.transport.call_count,2)

    def test_v2_keeps_response_even_when_normalizer_raises(self):
        self.body['features'][0]['id']='not-an-osm-id'
        with self.assertRaises(ContractError):
            run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport,diagnostic_v2=True)
        directory=Path(str(self.backup)+'.diagnostics')
        self.assertTrue((directory/'body.json').exists())
        self.assertEqual(json.loads((directory/'http.json').read_text())['status'],200)
        self.assertTrue((directory/'failure.json').exists())
        self.transport.assert_called_once()

    def test_missing_scope_stops_before_cost(self):
        with self.repo.transaction() as c:
            p=Registry(self.repo).list()[0];p['scopes']=['storage']
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        with self.assertRaisesRegex(ContractError,'approval_required'):
            run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport)
        self.transport.assert_not_called()

    def test_partial_response_reports_reason_and_cost_without_publication_or_retry(self):
        self.headers['X-Has-More']='true'
        result=run(self.repo.path,self.backup,execute=True,accept=True,transport=self.transport)
        self.assertEqual(result['status'],'response_incomplete')
        self.assertIn('truncated',result['reasons'])
        self.assertEqual(result['billing']['reported_credits'],3)
        self.assertFalse(result['world_published'])
        self.assertFalse(result['acceptance_ready'])
        self.assertEqual(CanonicalWorldRepository(self.repo).status()['snapshots'],0)
        with self.assertRaisesRegex(ContractError,'already_used'):
            run(self.repo.path,self.output.parent/'second.sqlite3',execute=True,accept=True,transport=self.transport)
        self.transport.assert_called_once()
