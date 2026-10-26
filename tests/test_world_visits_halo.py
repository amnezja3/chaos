from contextlib import closing
import os
import ast
import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch,Mock

from poi_infrastructure.repository import Repository
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.discovery_halo import expand,cells,tasks_for
from poi_infrastructure.world_visits import record_visit


def concurrent_visit(path):
    DemandQueue(Repository(path)).record(21.001,52.001,min_interval=60)


class VisitsHaloTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'poi.sqlite3'
        self.repo=Repository(self.path);self.queue=DemandQueue(self.repo);self.queue.initialize()
        env=patch.dict(os.environ,CHAOS_POI_CACHE_PATH=str(self.path),CHAOS_POI_DISCOVERY_MODE='passive',CHAOS_POI_WORLD_VISITS_ENABLED='1')
        env.start();self.addCleanup(env.stop)

    def test_visits_coalesce_and_refresh_after_interval(self):
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            self.assertEqual(record_visit(dict(lng=21.001,lat=52.001)),6)
            self.assertEqual(record_visit(dict(lng=21.002,lat=52.002)),0)
            self.assertEqual(self.queue.summary()['cells'][0]['hits'],6)
            with patch('poi_infrastructure.discovery_queue.time.time',return_value=time.time()+61):
                self.assertEqual(record_visit(dict(lng=21.002,lat=52.002)),6)

    def test_four_workers_only_record_one_visit_per_sector_interval(self):
        ctx=multiprocessing.get_context('spawn')
        processes=[ctx.Process(target=concurrent_visit,args=(str(self.path),)) for _ in range(4)]
        for process in processes:process.start()
        for process in processes:
            process.join(20)
            self.assertEqual(process.exitcode,0)
        self.assertEqual(self.queue.summary()['cells'][0]['hits'],6)

    def test_position_hook_uses_committed_position_and_skips_failed_writes(self):
        source=Path('run.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='normalize_profile_position_update')
        store=Mock()
        scope={'player_position_store':store}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'run.py','exec'),scope)
        store.upsert.return_value={'position':{'lat':52.001,'lng':21.001}}
        scope[node.name]({'lat':40,'lng':30},username='test')
        self.assertEqual(self.queue.summary()['cells'][0]['cell_x'],2100)
        store.upsert.side_effect=ValueError('movement denied')
        with self.assertRaisesRegex(ValueError,'movement denied'):
            scope[node.name]({'lat':40,'lng':30},username='test')
        self.assertEqual(self.queue.summary()['pending'],6)

    def test_flags_missing_database_invalid_position_do_not_create_data(self):
        with patch.dict(os.environ,CHAOS_POI_WORLD_VISITS_ENABLED='0'):
            self.assertEqual(record_visit(dict(lng=21,lat=52)),0)
        self.assertEqual(record_visit(dict(lng=float('nan'),lat=52)),0)
        missing=Path(self.tmp.name)/'missing.sqlite3'
        with patch.dict(os.environ,CHAOS_POI_CACHE_PATH=str(missing)):
            self.assertEqual(record_visit(dict(lng=21,lat=52)),0)
        self.assertFalse(missing.exists())
        self.assertEqual(self.queue.summary()['pending'],0)

    def test_one_ring_no_recursion_or_renewal(self):
        self.queue.record(21.001,52.001)
        self.assertEqual(expand(self.repo),4)
        with closing(self.repo.connect()) as c:
            before=[tuple(r) for r in c.execute('SELECT * FROM world_discovery_demand ORDER BY key')]
        self.assertEqual(expand(self.repo),0)
        with closing(self.repo.connect()) as c:
            self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM world_discovery_demand ORDER BY key')])
            direct_expiry=c.execute("SELECT min(expires) FROM world_discovery_demand WHERE origin='direct'").fetchone()[0]
            self.assertLessEqual(c.execute("SELECT max(expires) FROM world_discovery_demand WHERE origin='halo'").fetchone()[0],direct_expiry)
        self.assertEqual(len(cells(self.repo)),1)
        self.assertEqual(len(cells(self.repo,halo=True)),5)

    def test_visit_promotes_halo_and_priority_survives_rotation(self):
        self.queue.record(21.001,52.001);expand(self.repo)
        self.assertEqual(record_visit(dict(lng=21.015,lat=52.005)),6)
        entries=cells(self.repo,halo=True)
        self.assertEqual(sum(tier==0 for cell,tier in entries),2)
        direct={cell for cell,tier in entries if tier==0}
        for cursor in (0,7,19,100):
            tasks=tasks_for(entries,cursor)
            self.assertTrue(all(cell in direct for cell,profile in tasks[:10]))
            self.assertTrue(all(cell not in direct for cell,profile in tasks[10:]))

    def test_expansion_batch_and_queue_cap(self):
        for n in range(25):self.queue.record(20+n*.1,50)
        self.assertEqual(expand(self.repo),8)
        for _ in range(15):expand(self.repo)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM world_discovery_demand WHERE origin='halo'").fetchone()[0],480)
            self.assertEqual(c.execute("SELECT count(*) FROM world_discovery_demand WHERE origin='direct'").fetchone()[0],150)

    def test_edges_do_not_wrap_or_exceed_coordinates(self):
        self.queue.record(180,90)
        self.assertEqual(expand(self.repo),2)
        self.assertTrue(all(-18000<=cell[0]<18000 and -9000<=cell[1]<9000 for cell,tier in cells(self.repo,halo=True)))

    def test_legacy_schema_direct_compatible_explicit_halo_migration(self):
        with self.repo.transaction() as c:c.execute('ALTER TABLE world_discovery_demand DROP COLUMN origin')
        self.assertEqual(record_visit(dict(lng=21,lat=52)),6)
        with self.assertRaisesRegex(ValueError,'halo_schema_required'):expand(self.repo)
        self.queue.initialize()
        self.assertEqual(expand(self.repo),4)
