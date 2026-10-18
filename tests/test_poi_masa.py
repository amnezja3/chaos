import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.presentation import capture, public_fields
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import Config, Service, POIError, Cancelled


FLAGS = {'CHAOS_POI_INFRASTRUCTURE_ENABLED': '1', 'CHAOS_POI_MASA_UX_ENABLED': '1'}


def concurrent_scan(path, barrier, counter, results, release, blocked):
    os.environ.update(FLAGS)
    def transport(*args):
        with counter.get_lock():
            counter.value += 1
        if not release.wait(10):
            raise AssertionError('probe not released')
        return 200, None, {'elements': []}
    service = Service(path, Config(join_wait=3), transport)
    barrier.wait(timeout=15)
    for index in range(5 if blocked else 1):
        with capture() as evidence:
            try:
                service.fetch(f'q-{os.getpid()}-{index}', ['https://one.example'], 1, 300, 1800)
            except POIError:
                pass
        results.put(evidence)


class MasaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        flags = patch.dict(os.environ, FLAGS)
        flags.start()
        self.addCleanup(flags.stop)
        self.path = Path(self.tmp.name) / 'poi.sqlite3'
        self.transport = Mock(return_value=(200, None, {'elements': []}))
        self.service = Service(self.path, transport=self.transport)
        self.service.repo.initialize()

    def scan(self, query='q', endpoints=None, options=None):
        with capture() as evidence:
            try:
                self.service.fetch(query, endpoints or ['https://one.example'], 1, 300, 1800, options)
            except POIError:
                pass
        return evidence

    def test_ready_degraded_restored_and_complete_empty(self):
        self.assertEqual(self.scan()['interference']['state'], 'ready')
        with self.service.repo.transaction() as conn:
            conn.execute('UPDATE cache SET fetched=?', (time.time()-400,))
        self.transport.return_value = (503, '30', None)
        result = self.scan()
        self.assertEqual(result['interference']['state'], 'degraded')
        self.assertNotIn('failure_reason', result)
        with self.service.repo.transaction() as conn:
            conn.execute('UPDATE providers SET until_at=?', (time.time()-1,))
        self.transport.return_value = (200, None, {'elements': []})
        self.assertEqual(self.scan()['interference']['state'], 'restored')
        self.assertEqual(self.scan()['interference']['state'], 'ready')

    def test_blocked_is_shared_policy_not_one_failed_attempt(self):
        self.transport.return_value = (502, None, None)
        self.assertEqual(self.scan(), {})  # Below existing breaker threshold.
        self.transport.return_value = (429, '60', None)
        result = self.scan()
        self.assertEqual(result['interference']['state'], 'blocked')
        self.assertGreater(result['interference']['retry_after_seconds'], 0)
        self.transport.reset_mock()
        for i in range(10):
            self.assertEqual(self.scan(str(i))['interference']['state'], 'blocked')
        self.transport.assert_not_called()
        with self.service.repo.transaction() as c:
            c.execute('UPDATE providers SET until_at=1e100')
        unknown = self.scan('huge-retry-after')['interference']
        self.assertEqual(unknown['state'], 'blocked')
        self.assertNotIn('blocked_until', unknown)

    def test_other_provider_can_succeed(self):
        self.service.repo.outcome('one.example', False, 60)
        result = self.scan(endpoints=['https://one.example', 'https://two.example'])
        self.assertEqual(result['interference']['state'], 'ready')
        self.assertEqual(self.transport.call_count, 1)

    def test_failed_probe_renews_authoritative_deadline(self):
        self.service.repo.outcome('one.example', False, 60)
        with self.service.repo.transaction() as c:
            c.execute('UPDATE providers SET until_at=?', (time.time()-1,))
        self.transport.return_value = (502, '30', None)
        result = self.scan()
        self.assertEqual(result['interference']['state'], 'blocked')
        self.assertGreater(result['interference']['retry_after_seconds'], 28)
        self.assertEqual(self.transport.call_count, 1)
        self.scan('different')
        self.assertEqual(self.transport.call_count, 1)

    def test_other_errors_cancellation_flags_and_request_isolation(self):
        self.transport.return_value = (200, None, {'remark': 'broken', 'elements': []})
        for _ in range(4):
            self.assertEqual(self.scan(), {})
        self.assertTrue(self.service.repo.allowed('one.example'))
        self.assertEqual(self.scan(options={'still_active': lambda: False}), {})
        with patch.object(self.service.repo, 'read', side_effect=OSError('disk')):
            self.assertEqual(self.scan(), {})
        self.transport.return_value = (200, None, {'elements': []})
        with patch.dict(os.environ, CHAOS_POI_MASA_UX_ENABLED='0'):
            self.assertEqual(self.scan(), {})
            self.assertEqual(public_fields({'interference': {}}), {})
        with capture() as outer:
            self.assertEqual(self.scan()['interference']['state'], 'ready')
            self.assertEqual(outer, {})
        with patch.dict(os.environ, CHAOS_POI_INFRASTRUCTURE_ENABLED='0'):
            self.assertEqual(self.scan(), {})

    def parallel(self, blocked):
        self.service.repo.outcome('one.example', False, 60)
        if not blocked:
            with self.service.repo.transaction() as c:
                c.execute('UPDATE providers SET until_at=?', (time.time()-1,))
        ctx = multiprocessing.get_context('spawn')
        barrier, counter, results, release = ctx.Barrier(4), ctx.Value('i', 0), ctx.Queue(), ctx.Event()
        processes = [ctx.Process(target=concurrent_scan,
                     args=(str(self.path), barrier, counter, results, release, blocked)) for _ in range(4)]
        try:
            for p in processes: p.start()
            if blocked:
                messages = [results.get(timeout=20) for _ in range(20)]
                self.assertEqual(counter.value, 0)
                self.assertTrue(all(m['interference']['state']=='blocked' for m in messages))
            else:
                messages = [results.get(timeout=20) for _ in range(3)]
                self.assertTrue(all(m['interference']['state']=='recovering' for m in messages), messages)
                self.assertEqual(counter.value, 1)
                release.set()
                self.assertEqual(results.get(timeout=20)['interference']['state'], 'restored')
            for p in processes:
                p.join(15)
                self.assertEqual(p.exitcode, 0)
        finally:
            release.set()
            for p in processes:
                if p.is_alive(): p.terminate()
                p.join()
                p.close()
            results.close()
            results.join_thread()

    def test_twenty_requests_four_workers_blocked_zero_http(self):
        self.parallel(True)

    def test_four_workers_half_open_only_one_probe(self):
        self.parallel(False)


if __name__ == '__main__':
    unittest.main()
