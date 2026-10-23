from contextlib import closing
import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_operations import status
from poi_infrastructure.credit_budget import CreditBudget


def record_process(path):
    queue=DemandQueue(Repository(path))
    for _ in range(5):
        queue.record(21.001,52.001,['poi'])


class DemandQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3');self.repo.initialize()
        self.queue=DemandQueue(self.repo)
        self.queue.initialize()

    def test_dedup_layers_expiry_and_no_player_data(self):
        self.assertEqual(self.queue.record(21.001,52.001),6)
        self.assertEqual(self.queue.record(21.002,52.002),6)
        result=self.queue.summary()
        self.assertEqual(result['pending'],6)
        self.assertEqual(len(result['cells']),1)
        self.assertEqual(result['cells'][0]['hits'],12)
        with closing(self.repo.connect()) as c:
            names=[r[1] for r in c.execute('PRAGMA table_info(world_discovery_demand)')]
            self.assertFalse({'user_id','login','session','latitude','longitude'}&set(names))
        with patch('poi_infrastructure.discovery_queue.time.time',return_value=time.time()+86401):
            self.assertEqual(self.queue.summary()['pending'],0)
            self.assertEqual(self.queue.prune(),6)

    def test_capacity_never_grows_from_neighbors(self):
        queue=DemandQueue(self.repo,max_entries=2)
        self.assertEqual(queue.record(21,52,['poi']),1)
        self.assertEqual(queue.record(22,52,['poi']),1)
        self.assertEqual(queue.record(23,52,['poi']),0)
        self.assertEqual(queue.record(21,52,['poi']),1)
        self.assertEqual(queue.summary()['pending'],2)

    def test_four_processes_coalesce_demand(self):
        ctx=multiprocessing.get_context('spawn')
        workers=[ctx.Process(target=record_process,args=(self.repo.path,)) for _ in range(4)]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(20)
            self.assertEqual(worker.exitcode,0)
        self.assertEqual(self.queue.summary()['pending'],1)
        self.assertEqual(self.queue.summary()['cells'][0]['hits'],20)

    def test_read_only_summary_does_not_create_world_or_change_ledger(self):
        ledger=CreditBudget(self.repo);ledger.initialize()
        ledger.configure_recurring('maplark',800,24000)
        self.queue.record(21,52)
        with closing(self.repo.connect()) as c:
            before=c.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall()
            ledger_tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'world_credit_%'")]
            ledger_before={name:c.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall() for name in ledger_tables}
        with patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
            first=status(self.repo);second=status(self.repo)
        self.assertFalse(first['world_prepared'])
        self.assertFalse(first['background_fetch_enabled'])
        self.assertEqual(first['demand'],second['demand'])
        self.assertEqual(first['budget_windows'][0]['committed'],0)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall(),before)
            self.assertEqual({name:c.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall() for name in ledger_tables},ledger_before)

    def test_empty_unprepared_projection_and_boundary_cells(self):
        repo=Repository(Path(self.tmp.name)/'empty.sqlite3');repo.initialize()
        self.assertFalse(DemandQueue(repo).summary()['prepared'])
        self.queue.record(180,90,['poi'])
        cell=self.queue.summary()['cells'][0]
        self.assertEqual((cell['cell_x'],cell['cell_y']),(17999,8999))
