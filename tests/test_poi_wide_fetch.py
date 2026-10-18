import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from poiFetchClass import POIFetcher
from poi_infrastructure.geometry import fill_plan
from poi_infrastructure.providers import Registry
from poi_infrastructure.service import Service, Config, Cancelled, POIError
from poi_infrastructure.world import WorldRepository

FIXTURE=Path(__file__).parent/'fixtures/poi'
FILTERS=['shop','amenity','office','healthcare','atm=yes','man_made=surveillance']
FLAGS={f'CHAOS_POI_{k}_ENABLED':'1' for k in ('PROVIDER_REGISTRY','WORLD_INGEST','WORLD_REPOSITORY','WIDE_FETCH')}


def parallel_scan(path,name,ready,start,calls,results):
    def transport(*args):
        with calls.get_lock(): calls.value+=1
        time.sleep(.2)
        return 200,None,json.loads((FIXTURE/'geometry_wide_reference.json').read_text())
    service=Service(path,config=Config(join_wait=10),transport=transport)
    case=json.loads((FIXTURE/'geometry_reference.json').read_text())['cases'][name]
    ready.put(name)
    start.wait(15)
    try:
        value=service.fetch(case['query'],['unused']*2,8,300,1800,
            dict(_spatial=dict(lat=case['lat'],lon=case['lon'],radius=case['radius'],filters=FILTERS)))
        results.put((name,value['elements']==case['response']['elements']))
    except Exception as exc: results.put((name,str(exc)))


class WideFetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.transport=Mock(return_value=(200,None,json.loads((FIXTURE/'geometry_wide_reference.json').read_text())))
        self.service=Service(Path(self.tmp.name)/'poi.sqlite3',transport=self.transport)
        self.registry=Registry(self.service.repo)
        self.registry.initialize()
        v=self.registry.save('fixture',0,dict(name='Fixture',url='https://example.org/api/interpreter',operator_group='fixture',priority=0),'admin')
        v=self.registry.decision('fixture',v['revision'],'approved_for_defined_use',['normal_scan','wide_fetch','storage'],
            dict(source_url='https://example.org/terms',reference='isolated fixture',notes='test only'),time.time()+86400,'admin')
        v=self.registry.tested('fixture',v['revision'],True,'test')
        self.value=self.registry.enable('fixture',v['revision'],True,'admin')
        self.env=patch.dict(os.environ,FLAGS)
        self.env.start();self.addCleanup(self.env.stop)
        self.reference=json.loads((FIXTURE/'geometry_reference.json').read_text())['cases']

    def scan(self,name='origin',live=lambda:True,endpoints=2):
        c=self.reference[name]
        return self.service.fetch(c['query'],['unused']*endpoints,8,300,1800,
            dict(still_active=live,_spatial=dict(lat=c['lat'],lon=c['lon'],radius=c['radius'],filters=FILTERS)))

    def test_one_fill_serves_nearby_after_restart_with_provider_disabled(self):
        self.assertEqual(fill_plan(0,0,300,FILTERS)[1],(FIXTURE/'geometry_wide.ql').read_text())
        self.assertEqual(self.scan()['elements'],self.reference['origin']['response']['elements'])
        self.assertEqual(self.transport.call_count,1)
        self.assertIn('out body;',self.transport.call_args.args[1])
        self.registry.enable('fixture',self.value['revision'],False,'admin')
        self.service=Service(self.service.repo.path,transport=self.transport)
        for name in ('nearby','edge','small','larger'):
            self.assertEqual(self.scan(name)['elements'],self.reference[name]['response']['elements'])
        self.assertEqual(self.transport.call_count,1)

    def test_bad_geometry_uses_remaining_exact_attempt_same_deadline(self):
        self.transport.side_effect=[(200,None,dict(elements=[dict(type='way',id=1,nodes=[999],tags={'shop':'books'})])),
                                    (200,None,self.reference['origin']['response'])]
        self.assertEqual(self.scan(),self.reference['origin']['response'])
        first,second=self.transport.call_args_list
        self.assertIn('out body;',first.args[1]);self.assertIn('out center;',second.args[1])
        self.assertEqual(first.args[3],second.args[3])
        self.assertEqual(WorldRepository(self.service.repo).status()['experimental_coverage'],0)

    def test_no_extra_attempt_after_exhaustion(self):
        self.transport.return_value=(200,None,dict(elements=[],remark='partial'))
        with self.assertRaises(POIError):self.scan(endpoints=1)
        self.assertEqual(self.transport.call_count,1)

    def test_cancellation_does_not_deliver_gameplay_and_releases_leases(self):
        live=[True]
        def respond(*args):
            live[0]=False
            return 200,None,json.loads((FIXTURE/'geometry_wide_reference.json').read_text())
        self.transport.side_effect=respond
        with self.assertRaises(Cancelled):self.scan(live=lambda:live[0])
        c=self.service.repo.connect()
        try:self.assertEqual(c.execute('SELECT count(*) FROM leases').fetchone()[0],0)
        finally:c.close()

    def test_scope_and_dependencies_prevent_wide(self):
        with patch.dict(os.environ,{'CHAOS_POI_WORLD_INGEST_ENABLED':'0'}):
            with self.assertRaisesRegex(POIError,'dependencies'):self.scan()
        self.transport.assert_not_called()
        v=self.registry.decision('fixture',self.value['revision'],'approved_for_defined_use',['normal_scan'],
            dict(source_url='https://example.org/terms',reference='no storage',notes='fixture restriction'),time.time()+86400,'admin')
        self.registry.enable('fixture',v['revision'],True,'admin')
        self.transport.return_value=(200,None,self.reference['origin']['response'])
        self.scan()
        self.assertIn('out center;',self.transport.call_args.args[1])

    def test_four_processes_share_one_fill(self):
        ctx=multiprocessing.get_context('spawn')
        ready,results,start,calls=ctx.Queue(),ctx.Queue(),ctx.Event(),ctx.Value('i',0)
        processes=[ctx.Process(target=parallel_scan,args=(self.service.repo.path,n,ready,start,calls,results))
                   for n in ('origin','nearby','small','larger')]
        try:
            for p in processes:p.start()
            for _ in processes:ready.get(timeout=20)
            start.set()
            output=[results.get(timeout=20) for _ in processes]
            self.assertTrue(all(value is True for _,value in output),output)
            self.assertEqual(calls.value,1)
            for p in processes:
                p.join(10);self.assertEqual(p.exitcode,0)
        finally:
            for p in processes:
                if p.is_alive():p.terminate()
                p.join();p.close()
            for q in (ready,results):q.close();q.join_thread()


if __name__=='__main__':unittest.main()
