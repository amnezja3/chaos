from contextlib import closing, redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.repository import Repository
from poi_infrastructure.worker_heartbeat import Heartbeat, initialize, inspect
from tools.world_discovery_worker import main


class HeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name)/'poi.sqlite3')
        self.repo.initialize()

    def read(self, now):
        with closing(self.repo.connect()) as c:
            return inspect(c, now)

    def test_missing_schema_stays_unknown_without_implicit_migration(self):
        self.assertEqual(self.read(100)['reason'], 'schema_missing')
        self.assertFalse(Heartbeat(self.repo).start())
        self.assertEqual(self.read(100)['reason'], 'schema_missing')
        initialize(self.repo)
        self.assertEqual(self.read(100)['reason'], 'not_observed')

    def test_expiry_and_clock_skew_never_claim_running(self):
        initialize(self.repo)
        beat = Heartbeat(self.repo)
        with patch('time.time', return_value=100):
            self.assertTrue(beat.start())
        self.assertEqual(self.read(101)['status'], 'running')
        self.assertEqual(self.read(99)['reason'], 'clock_skew')
        self.assertEqual(self.read(240)['reason'], 'expired')
        with patch('time.time', return_value=200):
            self.assertTrue(beat.pulse('waiting'))
        self.assertEqual(self.read(201)['status'], 'waiting')
        with patch('time.time', return_value=202):
            beat.pulse('stopped')
        self.assertEqual(self.read(203)['status'], 'stopped')
        self.assertNotIn(beat.owner, json.dumps(self.read(203)))

    def test_old_process_cannot_renew_or_stop_replacement(self):
        initialize(self.repo)
        old, new = Heartbeat(self.repo), Heartbeat(self.repo)
        with patch('time.time', return_value=100):
            old.start()
            new.start()
        with patch('time.time', return_value=150):
            self.assertFalse(old.pulse('stopped'))
            self.assertFalse(old.pulse('running'))
        self.assertEqual(self.read(151)['observed_at'], 100)
        self.assertEqual(self.read(240)['status'], 'unknown')

    def test_telemetry_failure_is_optional(self):
        initialize(self.repo)
        beat = Heartbeat(self.repo)
        beat.start()
        with patch.object(self.repo, 'transaction', side_effect=OSError('private')):
            self.assertFalse(beat.pulse('running'))

    def run_worker(self, *args):
        with patch.dict(os.environ, {'CHAOS_POI_DISCOVERY_WORKER_ENABLED': '1'}, clear=True), \
                patch('sys.argv', ['worker', '--db', self.repo.path, *args]), \
                patch('tools.world_discovery_worker.signal.signal'), \
                redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            code = main()
        return code, out.getvalue()

    def test_plan_never_registers_worker_and_execution_records_stop(self):
        initialize(self.repo)
        with patch('tools.world_discovery_worker.cycle', return_value={'status':'plan','network_calls':0}):
            self.assertEqual(self.run_worker()[0], 0)
        self.assertEqual(self.read(100)['reason'], 'not_observed')
        with patch('tools.world_discovery_worker.cycle', return_value={'status':'idle','network_calls':0}):
            self.assertEqual(self.run_worker('--execute')[0], 0)
        self.assertEqual(self.read(100)['reason'], 'not_observed')
        stop = Mock()
        stop.is_set.side_effect = [False, True]
        with patch('time.time', return_value=100), \
                patch('tools.world_discovery_worker.threading.Event', return_value=stop), \
                patch('tools.world_discovery_worker.cycle', return_value={'status':'idle','network_calls':0}):
            self.assertEqual(self.run_worker('--execute','--serve')[0], 0)
        self.assertEqual(self.read(101)['status'], 'stopped')

    def test_failure_records_error_without_exception_message(self):
        initialize(self.repo)
        with patch('time.time', return_value=100), \
                patch('tools.world_discovery_worker.cycle', side_effect=ValueError('secret-url')):
            code, output = self.run_worker('--execute','--serve')
        self.assertEqual(code, 1)
        self.assertNotIn('secret-url', output)
        self.assertEqual(self.read(101)['status'], 'error')

    def test_read_only_monitor_can_inspect_and_does_not_renew(self):
        initialize(self.repo)
        with patch('time.time', return_value=100):
            Heartbeat(self.repo).start()
        from tools.world_collection_monitor import ReadOnlyRepository
        with closing(ReadOnlyRepository(self.repo.path).connect()) as c:
            self.assertEqual(inspect(c, 120)['age_seconds'], 20)
            self.assertEqual(inspect(c, 240)['status'], 'unknown')
        self.assertEqual(self.read(240)['observed_at'], 100)

    def test_release_gate_requires_migration_and_reports_heartbeat_separately(self):
        from tools.poi_world import initialize as prepare
        from tools.world_release_check import inspect as release
        from poi_infrastructure.regular_discovery import report
        prepare(self.repo.path, canonical=True, discovery=True, jobs=True, metrics=True)
        self.assertTrue(release(self.repo.path, require_heartbeat=True)['ok'])
        with patch('time.time', return_value=100):
            Heartbeat(self.repo).start()
            monitor = report(self.repo)
        self.assertEqual(monitor['heartbeat']['status'], 'running')
        self.assertEqual(monitor['last'], {})
        self.assertEqual(monitor['network_calls'], 0)
        with self.repo.transaction() as c:
            c.execute('DROP TABLE world_worker_heartbeat')
        self.assertFalse(release(self.repo.path, require_heartbeat=True)['ok'])
        self.assertTrue(release(self.repo.path)['ok'])
        self.assertEqual(report(self.repo)['heartbeat']['reason'], 'schema_missing')
