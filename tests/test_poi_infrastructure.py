import copy
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.utils import formatdate

from poiFetchClass import POIFetcher
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import Config, Service, POIError, Cancelled, key_for, validate, group_for, retry_delay

FIXTURE = Path(__file__).parent / 'fixtures/poi/complete.json'


def abandoned_lease(path, ready):
    r=Repository(path)
    r.acquire(key_for('q'),.1)
    ready.set()
    os._exit(0)


def process_fetch(path, barrier, counter, results):
    def transport(*args):
        with counter.get_lock():
            counter.value += 1
        time.sleep(.3)
        return 200, None, {'elements': []}
    s = Service(path, Config(join_wait=3), transport)
    s.repo.initialize()
    barrier.wait()
    try:
        results.put(s.fetch('same', ['https://example.test'], 1, 300, 1800))
    except Exception as e:
        results.put(type(e).__name__ + ':' + str(e))


class POIInfrastructureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'poi.sqlite3'
        self.raw = json.loads(FIXTURE.read_text())
        self.transport = Mock(return_value=(200, None, self.raw))
        self.service = Service(self.path, transport=self.transport)
        self.endpoints = ['https://one.example', 'https://two.example']

    def fetch(self, service=None, query='q', options=None, endpoints=None):
        return (service or self.service).fetch(query, endpoints or self.endpoints, 1, 300, 1800, options)

    def age(self, seconds):
        with self.service.repo.transaction() as c:
            c.execute('UPDATE cache SET fetched=?', (time.time() - seconds,))

    def test_fresh_survives_new_service_and_results_are_private(self):
        self.fetch()
        other = Service(self.path, transport=Mock(side_effect=AssertionError('network')))
        data = self.fetch(other)
        data['elements'][0]['tags']['name'] = 'private'
        self.assertEqual(self.fetch(other)['elements'][0]['tags']['name'], 'Bookshop')
        self.assertEqual(self.transport.call_count, 1)

    def test_exact_wire_query_keys_preserve_nearby_centers(self):
        f = POIFetcher()
        self.assertNotEqual(key_for(f._build_query(52.00001, 21)), key_for(f._build_query(52.00002, 21)))
        self.assertNotEqual(key_for('one'), key_for('two'))

    def test_facade_preserves_geometry_order_dedup_limit_and_isolation(self):
        with patch.dict(os.environ, CHAOS_POI_INFRASTRUCTURE_ENABLED='1'):
            f = POIFetcher(tag_filters=['shop','amenity','office'])
            f._poi_service = self.service
            result = f.get_all(52,21)
            self.assertEqual([(r['osm_type'],r['osm_id']) for r in result], [('node',1),('way',3),('relation',4)])
            result[0]['tags']['name']='player-only'
            self.assertEqual(f.get_all(52,21,result_limit=1)[0]['tags']['name'],'Bookshop')
            self.assertEqual(self.transport.call_count,1)

    def test_empty_complete_result_cached(self):
        self.transport.return_value=(200,None,{'elements':[]})
        self.assertEqual(self.fetch(),{'elements':[]})
        self.assertEqual(self.fetch(),{'elements':[]})
        self.assertEqual(self.transport.call_count,1)

    def test_stale_after_http_and_parser_errors_without_refreshing_age(self):
        self.fetch()
        self.age(400)
        for response in [(502,None,None),(406,None,None),(200,None,{'remark':'runtime error','elements':[]}), (200,None,{'bad':[]})]:
            self.transport.return_value=response
            self.assertEqual(self.fetch(endpoints=self.endpoints[:1]),self.raw)
        with self.service.repo.transaction() as c:
            self.assertLess(c.execute('SELECT fetched FROM cache').fetchone()[0],time.time()-399)

    def test_stale_checked_at_delivery_and_cold_failure_not_empty(self):
        self.transport.return_value=(503,None,None)
        with self.assertRaises(POIError): self.fetch(endpoints=self.endpoints[:1])
        self.transport.return_value=(200,None,self.raw)
        self.fetch()
        self.age(1799)
        def failure(*args):
            self.age(1801)
            return 502,None,None
        self.transport.side_effect=failure
        with self.assertRaises(POIError): self.fetch(endpoints=self.endpoints[:1])

    def test_corrupt_cache_does_not_escape_or_return_partial(self):
        self.fetch()
        with self.service.repo.transaction() as c: c.execute("UPDATE cache SET digest='wrong'")
        self.transport.return_value=(200,None,{'elements':[]})
        self.assertEqual(self.fetch(),{'elements':[]})
        self.assertEqual(self.transport.call_count,2)

    def test_fencing_expired_owner_cannot_write_or_release_successor(self):
        r=self.service.repo
        r.initialize()
        first=r.acquire('q',10)
        with r.transaction() as c: c.execute('UPDATE leases SET until_at=0')
        second=r.acquire('q',10)
        self.assertNotEqual(first,second)
        self.assertFalse(r.write('q',first,{'elements':[]},1800))
        r.release('q',first)
        self.assertTrue(r.owns('q',second))
        self.assertTrue(r.write('q',second,{'elements':[]},1800))

    def test_retry_after_alias_circuit_and_permanent_error(self):
        self.assertEqual(group_for('https://lz4.overpass-api.de/api/interpreter'),'overpass-api.de')
        self.transport.return_value=(429,'120',None)
        with self.assertRaises(POIError): self.fetch()
        self.assertEqual(self.transport.call_count,1)
        self.assertFalse(self.service.repo.allowed('one.example'))
        self.assertEqual(retry_delay('120'),120)
        self.assertEqual(retry_delay('nonsense'),0)
        self.transport.reset_mock()
        self.transport.return_value=(403,None,None)
        with self.assertRaises(POIError): self.fetch(query='other',endpoints=['https://permanent.example']*5)
        self.assertEqual(self.transport.call_count,1)

    def test_cancellation_before_fresh_and_after_fetch(self):
        self.fetch()
        with self.assertRaises(Cancelled): self.fetch(options={'still_active':lambda:False})
        live=[True]
        def transport(*args):
            live[0]=False
            return 200,None,self.raw
        self.transport.side_effect=transport
        with self.assertRaises(Cancelled): self.fetch(query='new',options={'still_active':lambda:live[0]})
        self.transport.side_effect=None
        self.transport.reset_mock()
        self.fetch(query='new')
        self.transport.assert_not_called()  # Complete shared raw cache survives owner cancellation.

    def test_global_slot_busy_does_not_send_http(self):
        self.service.repo.initialize()
        self.service.repo.acquire('@upstream',10)
        with self.assertRaisesRegex(POIError,'upstream_busy'): self.fetch()
        self.transport.assert_not_called()

    def test_storage_failure_never_bypasses_coordination(self):
        with patch.object(self.service.repo,'initialize',side_effect=sqlite3.OperationalError('full')):
            with self.assertRaisesRegex(POIError,'storage_unavailable'): self.fetch()
        self.transport.assert_not_called()

    def test_limits_and_cleanup_protect_active_entries(self):
        r=Repository(self.path,max_bytes=10000,max_entries=1)
        r.initialize()
        a=r.acquire('a',10)
        self.assertTrue(r.write('a',a,{'elements':[]},1800))
        b=r.acquire('b',10)
        self.assertFalse(r.write('b',b,{'elements':[]},1800))
        r.release('a',a)
        self.assertTrue(r.write('b',b,{'elements':[]},1800))
        self.assertIsNone(r.read('a',1800))

    def test_multiprocess_singleflight(self):
        self.service.repo.initialize()
        ctx=multiprocessing.get_context('spawn')
        barrier,counter,results=ctx.Barrier(3),ctx.Value('i',0),ctx.Queue()
        processes=[ctx.Process(target=process_fetch,args=(str(self.path),barrier,counter,results)) for _ in range(3)]
        try:
            for p in processes:p.start()
            for p in processes:
                p.join(15)
                self.assertEqual(p.exitcode,0)
            self.assertEqual([results.get(timeout=1) for _ in processes],[{'elements':[]}]*3)
            self.assertEqual(counter.value,1)
        finally:
            for p in processes:
                if p.is_alive():p.terminate()
                p.join()
                p.close()
            results.close()
            results.join_thread()

    def test_sqlite_writer_contention_waits_within_join_budget(self):
        self.service.repo.initialize()
        ready = threading.Event()
        def hold_writer():
            conn = sqlite3.connect(self.path, isolation_level=None)
            try:
                conn.execute('BEGIN IMMEDIATE')
                ready.set()
                time.sleep(.8)  # Longer than SQLite's 500 ms busy timeout.
                conn.commit()
            finally:
                conn.close()
        thread = threading.Thread(target=hold_writer)
        thread.start()
        try:
            self.assertTrue(ready.wait(3))
            self.assertEqual(self.fetch(), self.raw)
            self.assertEqual(self.transport.call_count, 1)
        finally:
            thread.join(3)

    def test_existing_owner_can_be_joined_while_writer_is_locked(self):
        self.service.repo.initialize()
        owner = self.service.repo.acquire('q', 10)
        conn = sqlite3.connect(self.path, isolation_level=None)
        try:
            conn.execute('BEGIN IMMEDIATE')
            started = time.monotonic()
            self.assertIsNone(self.service.repo.acquire('q', 10))
            self.assertLess(time.monotonic() - started, .4)
            self.assertTrue(self.service.repo.owns('q', owner))
        finally:
            conn.rollback()
            conn.close()

    def test_ghostlab_extra_attempt_can_succeed(self):
        with patch.dict(os.environ,CHAOS_POI_INFRASTRUCTURE_ENABLED='1'):
            for extra in (0,1):
                path=Path(self.tmp.name)/f'extra-{extra}.sqlite3'
                transport=Mock(side_effect=[(502,None,None),(502,None,None),(200,None,{'elements':[]})])
                f=POIFetcher()
                f._poi_service=Service(path,transport=transport)
                if extra:
                    self.assertEqual(f.get_all(1,2,scan_options={'extra_retries':extra}),[])
                    self.assertEqual(transport.call_count,3)
                else:
                    with self.assertRaises(POIError):f.get_all(1,2)
                    self.assertEqual(transport.call_count,2)

    def test_dead_process_lease_recovered(self):
        self.service.repo.initialize()
        ctx=multiprocessing.get_context('spawn')
        ready=ctx.Event()
        p=ctx.Process(target=abandoned_lease,args=(str(self.path),ready))
        p.start()
        self.assertTrue(ready.wait(5))
        p.join(5)
        self.assertEqual(p.exitcode,0)
        p.close()
        time.sleep(.15)
        self.assertEqual(self.fetch(),self.raw)

    def test_retry_http_date_and_circuit_recovery(self):
        self.assertGreater(retry_delay(formatdate(time.time()+60,usegmt=True)),58)
        r=self.service.repo
        r.initialize()
        for _ in range(3):r.outcome('one.example',False)
        self.assertFalse(r.allowed('one.example'))
        with r.transaction() as c:c.execute('UPDATE providers SET until_at=0')
        self.assertEqual(self.fetch(),self.raw)
        with r.transaction() as c:
            self.assertEqual(c.execute('SELECT failures FROM providers WHERE name=?',('one.example',)).fetchone()[0],0)

    def test_cancelled_joiner_does_not_release_owner(self):
        r=self.service.repo
        r.initialize()
        owner=r.acquire(key_for('q'),10)
        live=Mock(side_effect=[True,True,False])
        with self.assertRaises(Cancelled):self.fetch(options={'still_active':live})
        self.assertTrue(r.owns(key_for('q'),owner))
        self.transport.assert_not_called()

    def test_limits_validation_and_sensitive_fields_not_logged(self):
        with self.assertRaises(POIError):validate(self.raw,Config(max_elements=1))
        bad=copy.deepcopy(self.raw)
        bad['elements'][0]['lat']=float('nan')
        with self.assertRaises(POIError):validate(bad,Config())
        with self.assertLogs('chaos.poi',level='INFO') as logs:self.fetch()
        text=' '.join(logs.output)
        self.assertNotIn('Bookshop',text)
        self.assertNotIn('52.0',text)
        self.assertIn('"source": "upstream"',text)

    def test_flag_off_keeps_existing_transport(self):
        response=Mock(status_code=200)
        response.json.return_value={'elements':[]}
        with patch.dict(os.environ,CHAOS_POI_INFRASTRUCTURE_ENABLED='0'), patch('poiFetchClass.requests.post',return_value=response) as post:
            self.assertEqual(POIFetcher().get_all(1,2),[])
            self.assertEqual(post.call_count,1)


class TransportTest(unittest.TestCase):
    def test_local_http_success_and_hard_deadline(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path=='/slow':time.sleep(3)
                self.send_response(200)
                self.end_headers()
                try:self.wfile.write(b'{"elements":[]}')
                except OSError:pass
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                s=Service(Path(tmp)/'cache.sqlite3',Config(deadline=2))
                url=f'http://127.0.0.1:{server.server_port}'
                self.assertEqual(s.fetch('q',[url],1,300,1800),{'elements':[]})
                before=time.monotonic()
                with self.assertRaises(POIError):s.fetch('slow',[url+'/slow'],10,300,1800)
                self.assertLess(time.monotonic()-before,3)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__=='__main__':unittest.main()
