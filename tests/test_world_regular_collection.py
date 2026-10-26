from contextlib import closing
import json
from pathlib import Path
import time
import os
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from poi_infrastructure.regular_discovery import initialize,DEFAULTS,cycle,load
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.routing import Routing
from tools.world_regular_setup import prepare


class RegularCollectionTests(unittest.TestCase):
    setUp=fixtures.DiscoveryWorkerTests.setUp
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def configure(self):
        initialize(self.repo)
        self.provider['review_due_at']=time.time()+40*86400;self.save_provider()
        Routing(self.repo).initialize()
        self.path=Path(self.tmp.name)/'policy.json'
        self.path.write_text(json.dumps(dict(DEFAULTS,review_until=time.time()+30*86400)))
        self.ledger.configure_recurring('maplark',800,24000)

    def test_regular_cycle_archives_once_throttles_and_preserves_restart(self):
        self.configure()
        result=cycle(self.repo,self.path,execute=True,enabled=lambda:True,transport=self.transport)
        self.assertEqual(result['status'],'committed')
        self.assertEqual(result['provider'],'maplark')
        self.assertEqual(cycle(self.repo,self.path,execute=True,enabled=lambda:True)['status'],'waiting')
        with self.repo.transaction() as c:c.execute('UPDATE world_collection_runtime SET next_cycle=0')
        self.assertEqual(cycle(self.repo,self.path,execute=True,enabled=lambda:True)['status'],'idle')
        self.transport.assert_called_once()

    def test_no_demand_plan_and_disabled_never_fetch(self):
        self.configure()
        with self.repo.transaction() as c:c.execute('DELETE FROM world_discovery_demand')
        self.assertEqual(cycle(self.repo,self.path)['regions'],0)
        self.assertEqual(cycle(self.repo,self.path,execute=True)['status'],'disabled')
        self.assertEqual(cycle(self.repo,self.path,execute=True,enabled=lambda:True)['status'],'idle')
        self.transport.assert_not_called()

    def test_policy_revocation_in_flight_blocks_publication(self):
        self.configure();response=self.transport.return_value
        def revoke(*args,**kwargs):
            self.path.unlink();return response
        self.transport.side_effect=revoke
        result=cycle(self.repo,self.path,execute=True,enabled=lambda:True,transport=self.transport)
        self.assertEqual(result['status'],'reconciliation_required')
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)

    def test_daily_setup_preserves_geoapify_uncertain_operations(self):
        self.configure()
        geo=dict(self.provider,id='geoapify',url='https://api.geoapify.com/v2/places',operator_group='api.geoapify.com',
                 scopes=['small_probe','storage','world_storage'],enabled=False)
        with self.repo.transaction() as c:c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('geoapify',1,json.dumps(geo)))
        self.ledger.configure_window('geoapify','old',time.time()-1,time.time()+100,20)
        self.ledger.reserve('geoapify','old-uncertain',5);self.ledger.settle('geoapify','old-uncertain',None)
        prepare(self.repo,self.path,apply=True)
        until=load(self.path)[0]['review_until']
        prepare(self.repo,self.path,apply=True)
        self.assertEqual(load(self.path)[0]['review_until'],until)
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],5)
        self.assertEqual(self.ledger.status('geoapify')[0]['credit_limit'],2700)
        self.assertEqual(Routing(self.repo).get('poi','background')['chain'],['geoapify'])
        self.transport.assert_not_called()

    def test_overpass_outage_falls_back_next_cycle_without_extra_requests(self):
        self.configure()
        over=dict(self.provider,id='overpass-test',url='https://overpass.example.org/api/interpreter',operator_group='overpass.example.org',priority=0)
        with self.repo.transaction() as c:c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('overpass-test',1,json.dumps(over)))
        self.ledger.configure_recurring('overpass-test',120,3720)
        response=self.transport.return_value
        self.transport.side_effect=[(502,None,None),response]
        first=cycle(self.repo,self.path,execute=True,enabled=lambda:True,transport=self.transport)
        self.assertEqual(first['provider'],'overpass-test');self.assertEqual(first['network_calls'],1)
        with self.repo.transaction() as c:c.execute('UPDATE world_collection_runtime SET next_cycle=0')
        second=cycle(self.repo,self.path,execute=True,enabled=lambda:True,transport=self.transport)
        self.assertEqual(second['provider'],'maplark');self.assertEqual(second['status'],'committed')
        self.assertEqual(self.transport.call_count,2)

    def test_geoapify_conservative_cost_is_not_claimed_as_provider_report(self):
        from test_world_geoapify import response
        self.configure()
        geo=dict(self.provider,id='geoapify',url='https://api.geoapify.com/v2/places',operator_group='api.geoapify.com')
        with self.repo.transaction() as c:
            c.execute('DELETE FROM world_discovery_demand')
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)',('geoapify',1,json.dumps(geo)))
        DemandQueue(self.repo).record(21,52,['poi'])
        self.ledger.configure_recurring('geoapify',2700,83700)
        self.transport.return_value=response(2)
        with patch.dict(os.environ,CHAOS_GEOAPIFY_API_KEY='synthetic'):
            result=cycle(self.repo,self.path,execute=True,enabled=lambda:True,transport=self.transport)
        self.assertEqual(result['status'],'committed')
        self.assertEqual(result['billing']['billing_state'],'estimated_upper_bound')
        self.assertIsNone(result['billing']['reported_credits'])
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],6)
        with closing(self.repo.connect()) as c:
            row=c.execute("SELECT state,charged FROM world_credit_operation WHERE account='geoapify'").fetchone()
        self.assertEqual(tuple(row),('estimated',None))
        tomorrow=(int(time.time()//86400)+1)*86400+1
        self.assertEqual(self.ledger.status('geoapify',now=tomorrow)[0]['committed'],0)
        self.assertEqual(self.ledger.status('geoapify',now=tomorrow)[1]['committed'],6)

    def test_monitor_uses_read_only_database_and_does_not_fetch(self):
        from tools.world_collection_monitor import ReadOnlyRepository
        from poi_infrastructure.regular_discovery import report
        self.configure()
        result=report(ReadOnlyRepository(self.repo.path))
        self.assertEqual(result['network_calls'],0)
        with closing(ReadOnlyRepository(self.repo.path).connect()) as c:
            with self.assertRaises(Exception):c.execute('DELETE FROM world_discovery_job')
        self.transport.assert_not_called()

    def test_regular_launcher_uses_both_credentials_without_echoing_them(self):
        from tools.world_collector_start import start
        from tools.world_runtime_check import FLAGS
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.configure()
        root=Path(self.tmp.name);target=root/'data/world-collection-policy.json'
        target.parent.mkdir();target.write_bytes(self.path.read_bytes())
        env=dict(FLAGS,status='online',pm_cwd=str(root),CHAOS_POI_ROUTING_ENABLED='1',
                 CHAOS_MAPLARK_API_KEY='map-fixture',CHAOS_GEOAPIFY_API_KEY='geo-fixture',OTHER_SECRET='not-copied')
        runner=Mock(side_effect=[SimpleNamespace(stdout=json.dumps([dict(name='chaos',pm2_env=env)])),SimpleNamespace(),
            SimpleNamespace(stdout=json.dumps([dict(name='chaos-world-discovery-worker',pm2_env=env)]))])
        with patch('tools.world_collector_start.__file__',str(root/'tools/start.py')),patch('tools.world_collector_start.Repository',return_value=self.repo):
            result=start(runner=runner,regular=True)
        invocation=runner.call_args_list[1]
        self.assertIn('regular',invocation.args[0])
        self.assertEqual(invocation.kwargs['env']['CHAOS_GEOAPIFY_API_KEY'],'geo-fixture')
        self.assertNotIn('OTHER_SECRET',invocation.kwargs['env'])
        self.assertTrue(result['credentials_verified'])
        self.assertNotIn('geo-fixture',json.dumps(result))
        self.transport.assert_not_called()

    def test_launcher_rejects_missing_or_old_worker_key_without_exposing_it(self):
        from tools.world_collector_start import verify_credentials
        expected={'CHAOS_GEOAPIFY_API_KEY':'new-private-fixture'}
        for env in ({},{'CHAOS_GEOAPIFY_API_KEY':'old-private-fixture'}):
            with self.assertRaisesRegex(ValueError,'^worker_credentials_not_applied$'):
                verify_credentials([dict(name='chaos-world-discovery-worker',pm2_env=env)],expected)

    def test_ecosystem_explicitly_forwards_keys_and_omits_absent_values(self):
        import subprocess
        root=Path(__file__).resolve().parents[1]
        script="const e=require('./ecosystem.discovery.config.js').apps[0].env_regular; console.log(JSON.stringify([e.CHAOS_MAPLARK_API_KEY,e.CHAOS_GEOAPIFY_API_KEY]));"
        env=dict(os.environ,CHAOS_MAPLARK_API_KEY='map-fixture',CHAOS_GEOAPIFY_API_KEY='geo-fixture')
        result=subprocess.run(['node','-e',script],cwd=root,env=env,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout),['map-fixture','geo-fixture'])
        env.pop('CHAOS_MAPLARK_API_KEY');env.pop('CHAOS_GEOAPIFY_API_KEY')
        result=subprocess.run(['node','-e',script],cwd=root,env=env,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout),[None,None])

    def test_review_expiry_does_not_renew_or_fetch(self):
        from poi_infrastructure.discovery_worker import PermitExpired
        self.configure();original=self.path.read_bytes()
        with patch('time.time',return_value=time.time()+31*86400):
            with self.assertRaises(PermitExpired):cycle(self.repo,self.path,execute=True,enabled=lambda:True)
        self.assertEqual(original,self.path.read_bytes());self.transport.assert_not_called()
