import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from contextlib import closing

import test_world_discovery_worker as fixtures
from poi_infrastructure.discovery_runtime import cycle, load_permit
from poi_infrastructure.discovery_queue import DemandQueue


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        fixtures.DiscoveryWorkerTests.setUp(self)
        self.path=Path(self.tmp.name)/'permit.json'
        self.path.write_text(json.dumps(dict(cells=[[2100,5200]],profiles=['roads'],
            until=self.permit.until,reservation=20,budget_id='test')),encoding='utf8')
        env=patch.dict(os.environ,CHAOS_POI_DISCOVERY_WORKER_ENABLED='1')
        env.start();self.addCleanup(env.stop)

    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def test_disabled_without_permit_no_claim(self):
        with patch.dict(os.environ,CHAOS_POI_DISCOVERY_WORKER_ENABLED='0'):
            result=cycle(self.repo,'missing',execute=True,transport=self.transport)
        self.assertEqual(result['status'],'disabled')
        self.assertEqual(self.jobs.get(self.key)['attempts'],0)
        self.transport.assert_not_called()

    def test_plan_never_executes_or_claims(self):
        self.assertEqual(cycle(self.repo,self.path)['status'],'plan')
        self.assertEqual(self.jobs.get(self.key)['attempts'],0)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)

    def test_execute_restart_no_second_http(self):
        result=cycle(self.repo,self.path,execute=True,transport=self.transport)
        self.assertEqual(result['status'],'committed')
        self.assertEqual(cycle(self.repo,self.path,execute=True,transport=self.transport)['status'],'idle')
        self.transport.assert_called_once()

    def test_permit_removal_inflight_prevents_publication(self):
        response=self.transport.return_value
        def remove(*a,**kw):
            self.path.unlink()
            return response
        self.transport.side_effect=remove
        result=cycle(self.repo,self.path,execute=True,transport=self.transport)
        self.assertEqual(result['status'],'reconciliation_required')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)

    def test_out_of_scope_job_not_claimed_or_blocked(self):
        DemandQueue(self.repo).record(20,51,['roads'])
        with closing(self.repo.connect()) as c:
            demand=c.execute('SELECT key FROM world_discovery_demand WHERE cell_x=2000').fetchone()[0]
        other=self.jobs.enqueue(demand,'maplark',1,'roads')
        self.assertEqual(cycle(self.repo,self.path,execute=True,transport=self.transport)['status'],'committed')
        self.assertEqual(self.jobs.get(other)['state'],'PENDING')
        self.assertEqual(self.jobs.get(other)['attempts'],0)

    def test_expired_or_invalid_permit_never_sends(self):
        data=json.loads(self.path.read_text())
        for change in ({'until':time.time()-1},{'profiles':['land_water']},{'extra':'no'}):
            self.path.write_text(json.dumps(dict(data,**change)))
            with self.assertRaises(ValueError):
                cycle(self.repo,self.path,execute=True,transport=self.transport)
        self.transport.assert_not_called()

    def test_shutdown_before_cycle_no_claim(self):
        result=cycle(self.repo,self.path,execute=True,stopping=lambda:True,transport=self.transport)
        self.assertEqual(result['status'],'disabled')
        self.assertEqual(self.jobs.get(self.key)['attempts'],0)

    def test_worker_schema_preparation_is_idempotent_preserves_ledger(self):
        from tools.poi_world import initialize
        self.ledger.reserve('maplark','existing',20)
        self.ledger.settle('maplark','existing',3)
        for _ in range(2):
            result=initialize(self.repo.path,canonical=True,discovery=True,jobs=True)
            self.assertEqual(result['integrity'],'ok')
            self.assertEqual(result['foreign_keys'],'ok')
            self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
            self.assertEqual(self.jobs.get(self.key)['attempts'],0)

    def test_admin_queue_projection_is_passive_and_distinguishes_unresolved(self):
        from poi_infrastructure.world_operations import status
        before=status(self.repo)['jobs']
        self.assertEqual(before['total'],1)
        self.assertEqual(before['ready_by_time'],1)
        self.assertEqual(before['runtime'],'unknown')
        job=self.jobs.claim()
        self.jobs.transition(job['id'],job['owner'],'FETCHING',operation='fixture-op')
        self.jobs.transition(job['id'],job['owner'],'POLICY_BLOCKED')
        for _ in range(20):
            value=status(self.repo)['jobs']
            self.assertEqual(value['unresolved'],1)
            self.assertEqual(value['ready_by_time'],0)
            self.assertNotIn('owner',value['recent'][0])
            self.assertNotIn('operation',value['recent'][0])
        self.assertEqual(self.jobs.get(self.key)['state'],'POLICY_BLOCKED')
        self.transport.assert_not_called()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)
