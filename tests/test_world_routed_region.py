"""Live router compared with saved independent Overpass reference answers."""
import json
import multiprocessing
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_world_global_access as global_fixture
from poi_infrastructure.service import Service, Config, POIError
from poi_infrastructure.world_contract import FILTERS
from poi_infrastructure.routed_region import PROFILE

FIXTURES = Path(__file__).parent/'fixtures/poi'


def concurrent_scan(path, name, ready, start, calls, results):
    def transport(*args, **kwargs):
        with calls.get_lock():
            calls.value += 1
        time.sleep(.2)
        return 200,None,json.loads((FIXTURES/'geometry_wide_reference.json').read_text())
    case = json.loads((FIXTURES/'geometry_reference.json').read_text())['cases'][name]
    service = Service(path,config=Config(join_wait=10))
    ready.put(name)
    start.wait(20)
    try:
        with patch('poi_infrastructure.scan_router.bounded_http',side_effect=transport):
            answer = service.fetch(case['query'],[],25,300,1800,dict(_spatial=dict(
                lat=case['lat'],lon=case['lon'],radius=case['radius'],filters=list(FILTERS))))
        results.put((name,answer['elements']==case['response']['elements']))
    except Exception as exc:
        results.put((name,type(exc).__name__+':'+str(exc)))


class RoutedRegionTests(unittest.TestCase):
    grant = global_fixture.GlobalWorldTests.grant
    overpass = global_fixture.GlobalWorldTests.overpass
    route = global_fixture.GlobalWorldTests.route
    evict_cache = global_fixture.GlobalWorldTests.evict_cache

    def setUp(self):
        global_fixture.GlobalWorldTests.setUp(self)
        env = patch.dict(os.environ, CHAOS_POI_WORLD_REGIONAL_READ_ENABLED='1',
                         CHAOS_POI_WIDE_FETCH_ENABLED='1')
        env.start(); self.addCleanup(env.stop)
        p = self.overpass()
        p = self.registry.decision(p['id'], p['revision'], 'approved_for_defined_use',
            ['normal_scan', 'storage', 'world_storage', 'wide_fetch'],
            dict(source_url='https://example.org/terms', reference='test only', notes='fixture'),
            time.time()+3600, 'test')
        self.provider = self.registry.enable(p['id'], p['revision'], True, 'test')
        from poi_infrastructure.credit_budget import CreditBudget
        CreditBudget(self.service.repo).initialize()
        CreditBudget(self.service.repo).configure_recurring('overpass',120,3720)
        self.route(['overpass'])
        self.raw = json.loads((FIXTURES/'geometry_wide_reference.json').read_text())
        self.cases = json.loads((FIXTURES/'geometry_reference.json').read_text())['cases']

    def scan(self, name='origin'):
        c = self.cases[name]
        return self.service.fetch(c['query'], [], 25, 300, 1800,
            dict(_world_pilot_user='other-account', _spatial=dict(
                lat=c['lat'], lon=c['lon'], radius=c['radius'], filters=list(FILTERS))))

    def test_regional_network_attempt_uses_shared_budget_but_neighbor_does_not(self):
        from poi_infrastructure.credit_budget import CreditBudget
        ledger=CreditBudget(self.service.repo)
        with patch('poi_infrastructure.scan_router.bounded_http',return_value=(200,None,self.raw)) as http:
            self.scan()
            self.scan('nearby')
        self.assertEqual(http.call_count,1)
        self.assertTrue(all(w['committed']==1 for w in ledger.status('overpass')))

    def test_regional_budget_exhaustion_never_calls_upstream(self):
        from poi_infrastructure.credit_budget import CreditBudget
        ledger=CreditBudget(self.service.repo)
        ledger.reserve('overpass','already-used',120);ledger.settle('overpass','already-used',120)
        from poi_infrastructure.world_contract import ContractError
        with patch('poi_infrastructure.scan_router.bounded_http') as http:
            with self.assertRaises((POIError,ContractError)):self.scan()
        http.assert_not_called()

    def test_neighbor_reads_match_reference_after_restart_without_http(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)) as http:
            self.assertEqual(self.scan()['elements'], self.cases['origin']['response']['elements'])
            self.assertIn('out body;', http.call_args.args[2])
            self.evict_cache()
            self.service = Service(self.service.repo.path, config=Config(join_wait=0))
            with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
                for name in ('nearby', 'small', 'larger', 'edge'):
                    with self.subTest(name=name):
                        self.assertEqual(self.scan(name)['elements'], self.cases[name]['response']['elements'])
                with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                    self.scan('empty')  # reference lies outside the original fill
            http.assert_called_once()

    def test_empty_complete_fill_serves_neighbor_without_http(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,{'elements':[]})) as http:
            self.assertEqual(self.scan(), {'elements':[]})
            self.evict_cache()
            with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
                self.assertEqual(self.scan('nearby'), {'elements':[]})
            http.assert_called_once()

    def test_regional_flag_off_does_not_initiate_wide_request(self):
        with patch.dict(os.environ, CHAOS_POI_WORLD_REGIONAL_READ_ENABLED='0'), patch(
                'poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.cases['origin']['response'])) as http:
            self.scan()
            self.assertIn('out center;', http.call_args.args[2])

    def test_region_is_not_reused_after_revision_change(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)):
            self.scan()
        p = self.provider
        fields = {k:p[k] for k in ('name','url','operator_group','priority')}
        fields['name'] = 'changed'
        self.registry.save(p['id'],p['revision'],fields,'test')
        self.evict_cache()
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError, 'scan_network_paused'):
                self.scan('nearby')

    def test_incomplete_closure_does_not_publish_region(self):
        broken = {'elements':[{'type':'way','id':1,'nodes':[999], 'tags':{'shop':'yes'}}]}
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,broken)) as http:
            with self.assertRaisesRegex(POIError,'provider_response_incomplete'):
                self.scan()
            http.assert_called_once()
        self.assertEqual(self.world.status()['snapshots'],0)

    def test_optional_region_store_failure_keeps_successful_scan(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)), patch(
                'poi_infrastructure.routed_region.store', side_effect=OSError('fixture disk full')):
            self.assertEqual(self.scan()['elements'],self.cases['origin']['response']['elements'])

    def test_stale_then_expired_region_with_network_paused(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)):
            self.scan()
        self.evict_cache()
        now = time.time()
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with patch('time.time', return_value=now+301):
                self.assertEqual(self.scan('nearby')['elements'],self.cases['nearby']['response']['elements'])
            with patch('time.time', return_value=now+1801):
                with self.assertRaisesRegex(POIError,'scan_network_paused'):
                    self.scan('nearby')

    def test_corrupted_region_is_a_miss(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)):
            self.scan()
        self.evict_cache()
        with self.service.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET digest=? WHERE profile=?', ('invalid',PROFILE))
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError,'scan_network_paused'):
                self.scan('nearby')

    def test_provider_changed_during_fetch_never_publishes(self):
        def respond(*a, **kw):
            self.registry.enable(self.provider['id'], self.provider['revision'], False, 'test')
            return 200,None,self.raw
        with patch('poi_infrastructure.scan_router.bounded_http',side_effect=respond):
            with self.assertRaisesRegex(POIError,'routing_changed_or_cancelled'):
                self.scan()
        self.assertEqual(self.world.status()['snapshots'],0)

    def test_coverage_metadata_corruption_is_not_accepted(self):
        with patch('poi_infrastructure.scan_router.bounded_http', return_value=(200,None,self.raw)):
            self.scan()
        self.evict_cache()
        with self.service.repo.transaction() as c:
            row = c.execute('SELECT cell,bounds FROM world_coverage WHERE profile=?',(PROFILE,)).fetchone()
            bounds=json.loads(row['bounds']);bounds['radius']=1900
            c.execute('UPDATE world_coverage SET bounds=? WHERE cell=? AND profile=?',
                      (json.dumps(bounds),row['cell'],PROFILE))
        with patch.dict(os.environ, CHAOS_POI_SCAN_NETWORK_PAUSED='1'):
            with self.assertRaisesRegex(POIError,'scan_network_paused'):
                self.scan('nearby')

    def test_demand_is_recorded_once_per_scan_including_overpass_world_hit(self):
        from poi_infrastructure.discovery_queue import DemandQueue
        DemandQueue(self.service.repo).initialize()
        with patch.dict(os.environ,CHAOS_POI_DISCOVERY_MODE='passive'), patch(
                'poi_infrastructure.scan_router.bounded_http',return_value=(200,None,self.raw)) as http:
            self.scan(); self.scan('nearby')
            http.assert_called_once()
        with self.service.repo.transaction() as c:
            rows = c.execute('SELECT hits FROM world_discovery_demand').fetchall()
        self.assertEqual(len(rows),6)
        self.assertTrue(all(r['hits']==2 for r in rows))

    def test_four_processes_share_one_regional_fill(self):
        ctx=multiprocessing.get_context('spawn')
        ready,results,start,calls=ctx.Queue(),ctx.Queue(),ctx.Event(),ctx.Value('i',0)
        workers=[ctx.Process(target=concurrent_scan,args=(self.service.repo.path,n,ready,start,calls,results))
                 for n in ('origin','nearby','small','larger')]
        try:
            for worker in workers:worker.start()
            for _ in workers:ready.get(timeout=30)
            start.set()
            answers=[results.get(timeout=30) for _ in workers]
            self.assertTrue(all(value is True for _,value in answers),answers)
            self.assertEqual(calls.value,1)
            for worker in workers:
                worker.join(10);self.assertEqual(worker.exitcode,0)
        finally:
            for worker in workers:
                if worker.is_alive():worker.terminate()
                worker.join();worker.close()
            for q in (ready,results):q.close();q.join_thread()
