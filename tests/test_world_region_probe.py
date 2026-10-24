import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.service import POIError,UpstreamUnavailable
from tools.world_region_probe import capture,OPERATION,SCOPE


class RegionProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3')
        self.ledger=CreditBudget(self.repo);self.ledger.initialize()
        self.ledger.configure_recurring('maplark',800,24000)
        registry=Registry(self.repo);registry.initialize()
        p=registry.save('maplark',0,dict(name='MapLark',url='https://api.maplark.com/v3/osm_features',
            operator_group='api.maplark.com',priority=0),'test')
        p=registry.decision('maplark',p['revision'],'approved_for_defined_use',['storage'],
            dict(source_url='https://maplark.com/terms-of-service',reference='fixture',notes='fixture'),time.time()+86400,'test')
        # Fixture enables the provider without claiming a real technical test.
        with self.repo.transaction() as c:
            p['enabled']=True;p['technical_status']='tested_ok'
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        env=patch.dict('os.environ',CHAOS_MAPLARK_API_KEY='fixture-secret-xyz',CHAOS_POI_PRIORITY_ENABLED='1')
        env.start();self.addCleanup(env.stop)
        self.output=Path(self.tmp.name)/'capture'
        self.body=dict(type='FeatureCollection',features=[dict(type='Feature',id='way/1',
            properties=dict(tags={'highway':'residential'}),
            geometry=dict(type='LineString',coordinates=[[20.359,51.535],[20.371,51.535]]))])
        self.headers={'X-Returned':'1','X-Has-More':'false','X-Usage-Units-Charged':'3'}
        self.transport=Mock(return_value=(200,None,dict(body=self.body,response_headers=self.headers)))

    def call(self,**kwargs):
        return capture(self.repo.path,self.output,execute=True,approve=True,
                       accept_variable_cost=True,transport=self.transport,**kwargs)

    def test_plan_no_database_or_network(self):
        missing=Path(self.tmp.name)/'missing.sqlite3'
        result=capture(missing,transport=self.transport)
        self.assertEqual(result['network_calls'],0);self.assertFalse(missing.exists())
        self.transport.assert_not_called()

    def test_single_capture_shared_cost_no_registry_change_no_repeat(self):
        before=Registry(self.repo).list()
        result=self.call()
        self.assertEqual(result['billing']['reported_credits'],3)
        self.assertFalse(result['region_certified'])
        self.assertEqual(result['inspection']['neighbor_candidates']['crossing'],1)
        self.assertEqual(Registry(self.repo).list(),before)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        self.assertEqual(self.ledger.scope_status('maplark',SCOPE)['committed'],3)
        self.assertEqual(json.loads((self.output/'body.json').read_text()),self.body)
        with self.assertRaisesRegex(ContractError,'already_used'):self.call()
        self.transport.assert_called_once()

    def test_explicit_approval_and_budget_required(self):
        with self.assertRaisesRegex(ContractError,'approval_required'):
            capture(self.repo.path,self.output,execute=True,accept_variable_cost=True,transport=self.transport)
        self.ledger.reserve('maplark','exhaust',800)
        with self.assertRaisesRegex(ContractError,'budget_exhausted'):self.call()
        self.transport.assert_not_called()

    def test_unknown_cost_timeout_no_retry(self):
        self.transport.side_effect=UpstreamUnavailable('http_read_timeout')
        with self.assertRaises(UpstreamUnavailable):self.call()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],20)
        with self.assertRaisesRegex(ContractError,'already_used'):self.call()
        self.transport.assert_called_once()

    def test_partial_response_not_certified_but_charged(self):
        self.headers['X-Has-More']='true'
        with self.assertRaisesRegex(ContractError,'incomplete'):self.call()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        self.assertFalse((self.output/'body.json').exists())

    def test_existing_output_and_expired_policy_no_network(self):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):self.call()
        self.transport.assert_not_called()
        with self.repo.transaction() as c:
            p=Registry(self.repo)._load(c,'maplark');p['review_due_at']=0
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        with self.assertRaisesRegex(ContractError,'approved_maplark_storage_required'):self.call()

    def test_response_secret_never_saved(self):
        self.body['features'][0]['properties']['tags']['name']='fixture-secret-xyz'
        with self.assertRaisesRegex(ContractError,'sensitive_response_not_saved'):self.call()
        self.assertEqual(list(self.output.iterdir()),[])
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)

    def test_revision_change_after_transport_prevents_artifact(self):
        response=self.transport.return_value
        def change(*args,**kwargs):
            with self.repo.transaction() as c:
                p=Registry(self.repo)._load(c,'maplark');p['revision']+=1
                c.execute('UPDATE poi_provider_config SET config=?,revision=? WHERE id=?',(json.dumps(p),p['revision'],'maplark'))
            return response
        self.transport.side_effect=change
        with self.assertRaisesRegex(POIError,'scanner_inactive'):self.call()
        self.assertFalse((self.output/'body.json').exists())
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)

    def test_expired_scope_not_reopened(self):
        now=time.time()
        self.ledger.configure_scope('maplark',SCOPE,now-100,now-1,20)
        with self.assertRaisesRegex(ContractError,'window_expired'):self.call()
        self.transport.assert_not_called()
        self.assertLess(self.ledger.scope_status('maplark',SCOPE)['ends'],now)

    def test_waiting_player_has_priority_without_probe_charge(self):
        from poi_infrastructure.upstream_priority import UpstreamPriority
        gate=UpstreamPriority(self.repo);ticket=gate.register()
        try:
            with self.assertRaisesRegex(POIError,'upstream_busy'):self.call()
            self.transport.assert_not_called()
            self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)
        finally:gate.cancel(ticket)
