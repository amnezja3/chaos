from pathlib import Path
import json
import tempfile
import unittest
from contextlib import closing

from tools.world_runtime_check import inspect,FLAGS
from tools.poi_world import initialize
from tools.world_release_check import inspect as storage_inspect
from poi_infrastructure.repository import Repository


class AcceptanceTests(unittest.TestCase):
    def processes(self,stage):
        env=dict(FLAGS,status='online',pm_cwd=str(Path.cwd()),CHAOS_POI_ROUTING_ENABLED='1')
        env.update(CHAOS_POI_WORLD_ACCESS_MODE='pilot' if stage=='rollback' else 'global',
            CHAOS_POI_WORLD_INGEST_ENABLED='0' if stage=='rollback' else '1',
            CHAOS_POI_WORLD_REPOSITORY_ENABLED='1' if stage in ('read','visits') else '0',
            CHAOS_POI_WORLD_VISITS_ENABLED='1' if stage=='visits' else '0',
            CHAOS_POI_WORLD_REGIONAL_READ_ENABLED='0',CHAOS_POI_WIDE_FETCH_ENABLED='0',
            CHAOS_POI_SCAN_NETWORK_PAUSED='0')
        worker=dict(status='online',pm_cwd=str(Path.cwd()),CHAOS_POI_ROUTING_ENABLED='1',
            CHAOS_POI_DISCOVERY_WORKER_ENABLED='1',CHAOS_POI_PRIORITY_ENABLED='1')
        return [dict(name='chaos',pm2_env=env),dict(name='chaos-world-discovery-worker',pm2_env=worker)]

    def test_stages_are_distinct_and_fail_closed(self):
        for stage in ('ingest','read','visits','rollback'):
            processes=self.processes(stage)
            self.assertTrue(inspect(processes,Path.cwd(),routing='1',worker='online',world_stage=stage)['ok'])
            processes[0]['pm2_env']['CHAOS_POI_SCAN_NETWORK_PAUSED']='1'
            self.assertFalse(inspect(processes,Path.cwd(),routing='1',worker='online',world_stage=stage)['ok'])
        self.assertFalse(inspect(self.processes('ingest'),Path.cwd(),routing='1',worker='online',world_stage='read')['ok'])

    def test_unknown_flag_and_secret_are_never_echoed(self):
        processes=self.processes('read')
        processes[0]['pm2_env']['CHAOS_POI_WORLD_ACCESS_MODE']='secret-invalid'
        processes[0]['pm2_env']['API_KEY']='secret-value'
        result=inspect(processes,Path.cwd(),routing='1',worker='online',world_stage='read')
        self.assertFalse(result['ok'])
        self.assertNotIn('secret-',json.dumps(result))

    def test_visits_schema_gate_is_read_only_and_additive(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'poi.sqlite3'
            initialize(db,canonical=True,discovery=True,jobs=True,metrics=True)
            repo=Repository(db)
            self.assertTrue(storage_inspect(db,True,True,True)['ok'])
            with repo.transaction() as c:c.execute('ALTER TABLE world_discovery_demand DROP COLUMN origin')
            with closing(repo.connect()) as c:before=list(c.iterdump())
            result=storage_inspect(db,True,True,True)
            self.assertFalse(result['ok']);self.assertFalse(result['visits_schema_ready'])
            self.assertEqual(result['production_writes'],0)
            with closing(repo.connect()) as c:self.assertEqual(before,list(c.iterdump()))
            initialize(db,canonical=True,discovery=True,jobs=True,metrics=True)
            self.assertTrue(storage_inspect(db,True,True,True)['ok'])
