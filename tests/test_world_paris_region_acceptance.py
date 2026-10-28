import json
from pathlib import Path
from contextlib import closing
import unittest
from unittest.mock import patch
import test_world_region_probe as fixtures
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_contract import ContractError
from tools.world_paris_region_acceptance import run,OPERATION,DIAGNOSTIC_OPERATION


class ParisAcceptanceTests(unittest.TestCase):
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
