from contextlib import closing
import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

from poi_infrastructure.repository import Repository
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.upstream_priority import UpstreamPriority
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.world_acquisition import acquire_maplark
from poi_infrastructure.world_adapters import plan_maplark


def contender(path,lane,index,ready,go):
    repo=Repository(path);gate=UpstreamPriority(repo)
    ticket=gate.register() if lane=='live' else None
    ready.put(lane)
    if not go.wait(20):raise RuntimeError('start_timeout')
    deadline=time.monotonic()+8
    slot=None
    try:
        while time.monotonic()<deadline:
            slot=gate.acquire(lane=lane,ticket=ticket)
            if slot:break
            time.sleep(.02)
        if not slot:raise RuntimeError('slot_timeout')
        ledger=CreditBudget(repo)
        charged=0
        try:
            if ledger.reserve('maplark','process-'+str(index),10):
                # Simulated completed HTTP; no public API is contacted.
                charged=10;ledger.settle('maplark','process-'+str(index),10)
        except ContractError as exc:
            if str(exc)!='budget_exhausted':raise
        with repo.transaction() as c:
            c.execute('INSERT INTO test_admission(lane,charged) VALUES (?,?)',(lane,charged))
    finally:
        if slot:repo.release('@upstream',slot)
        gate.cancel(ticket)


class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3');self.repo.initialize()
        self.gate=UpstreamPriority(self.repo)

    def test_waiting_live_precedes_background_and_fifo(self):
        first=self.gate.register();second=self.gate.register()
        self.assertIsNone(self.gate.acquire(lane='background'))
        self.assertIsNone(self.gate.acquire(lane='live',ticket=second))
        slot=self.gate.acquire(lane='live',ticket=first)
        self.assertIsNotNone(slot)
        self.gate.cancel(first)
        self.assertTrue(self.repo.owns('@upstream',slot))
        self.assertIsNone(self.gate.acquire(lane='background'))
        self.repo.release('@upstream',slot)
        slot=self.gate.acquire(lane='live',ticket=second)
        self.assertIsNotNone(slot)
        self.repo.release('@upstream',slot)
        self.assertIsNotNone(self.gate.acquire(lane='background'))

    def test_in_flight_background_is_not_preempted(self):
        slot=self.gate.acquire(lane='background');ticket=self.gate.register()
        self.assertIsNone(self.gate.acquire(lane='live',ticket=ticket))
        self.assertTrue(self.repo.owns('@upstream',slot))
        self.repo.release('@upstream','wrong-owner')
        self.assertTrue(self.repo.owns('@upstream',slot))
        self.repo.release('@upstream',slot)
        self.assertIsNotNone(self.gate.acquire(lane='live',ticket=ticket))

    def test_dead_waiter_expires_and_circuit_is_shared(self):
        ticket=self.gate.register()
        with patch('poi_infrastructure.upstream_priority.time.time',return_value=time.time()+11):
            self.assertIsNone(self.gate.acquire(lane='live',ticket=ticket))
            slot=self.gate.acquire(lane='background')
            self.assertIsNotNone(slot)
        self.repo.release('@upstream',slot)
        self.repo.outcome('api.maplark.com',False,30)
        self.assertIsNone(self.gate.acquire(lane='background'))

    def test_four_live_processes_and_background_share_slot_and_budget(self):
        ledger=CreditBudget(self.repo);ledger.initialize()
        ledger.configure_window('maplark','fixture',time.time()-1,time.time()+3600,30)
        with self.repo.transaction() as c:
            c.execute('CREATE TABLE test_admission(id INTEGER PRIMARY KEY,lane TEXT,charged INTEGER)')
        holding=self.repo.acquire('@upstream',42)
        ctx=multiprocessing.get_context('spawn');ready=ctx.Queue();go=ctx.Event()
        workers=[ctx.Process(target=contender,args=(self.repo.path,'live' if i<4 else 'background',i,ready,go)) for i in range(5)]
        for worker in workers:worker.start()
        for _ in workers:ready.get(timeout=20)
        self.repo.release('@upstream',holding);go.set()
        for worker in workers:
            worker.join(20);self.assertEqual(worker.exitcode,0)
        ready.close();ready.join_thread()
        with closing(self.repo.connect()) as c:
            rows=c.execute('SELECT lane,charged FROM test_admission ORDER BY id').fetchall()
        self.assertEqual([r['lane'] for r in rows],['live']*4+['background'])
        self.assertEqual(sum(r['charged'] for r in rows),30)
        self.assertEqual(ledger.status('maplark')[0]['committed'],30)

    def test_real_acquisition_uses_gate_and_same_idempotent_ledger(self):
        ledger=CreditBudget(self.repo);ledger.initialize()
        ledger.configure_window('maplark','fixture',time.time()-1,time.time()+3600,100)
        transport=Mock(return_value=(200,None,dict(response_headers={
            'X-Usage-Units-Charged':'9','X-Returned':'0','X-Has-More':'false'},
            body={'type':'FeatureCollection','features':[]})))
        with patch.dict('os.environ',CHAOS_MAPLARK_API_KEY='fixture',CHAOS_POI_PRIORITY_ENABLED='1'):
            acquire_maplark(self.repo,plan_maplark(52,21,300),'same-operation',20,
                accept_variable_cost=True,transport=transport)
            with self.assertRaisesRegex(ContractError,'already_used'):
                acquire_maplark(self.repo,plan_maplark(52,21,300),'same-operation',20,
                    accept_variable_cost=True,transport=transport)
        transport.assert_called_once()
        self.assertEqual(ledger.status('maplark')[0]['committed'],9)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM leases').fetchone()[0],0)

    def test_background_without_priority_never_calls_transport(self):
        transport=Mock()
        with patch.dict('os.environ',CHAOS_MAPLARK_API_KEY='fixture',CHAOS_POI_PRIORITY_ENABLED='0'):
            with self.assertRaisesRegex(ContractError,'background_priority_required'):
                acquire_maplark(self.repo,plan_maplark(52,21,300),'bg',20,lane='background',
                    accept_variable_cost=True,transport=transport)
        transport.assert_not_called()
