from contextlib import closing
import json
import multiprocessing
import sqlite3
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from poi_infrastructure.repository import Repository
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.discovery_jobs import DiscoveryJobs
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_contract import ProviderBatch


def claim_process(path,output):
    job=DiscoveryJobs(Repository(path)).claim()
    output.put(job['owner'] if job else None)


class DiscoveryJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3')
        self.jobs=DiscoveryJobs(self.repo);self.jobs.initialize()
        self.demand=DemandQueue(self.repo);self.demand.record(21,52,['poi'])
        with closing(self.repo.connect()) as c:
            self.demand_key=c.execute('SELECT key FROM world_discovery_demand').fetchone()[0]
        self.key=self.jobs.enqueue(self.demand_key,'fixture',1,'poi')

    def receipt(self,key=None,revision=1):
        key=key or self.key
        Registry(self.repo).initialize()
        world=CanonicalWorldRepository(self.repo);world.initialize_canonical()
        with self.repo.transaction() as c:
            c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',('fixture',revision,
                json.dumps(dict(enabled=True,policy_status='approved_for_defined_use',scopes=['storage'],review_due_at=time.time()+3600))))
        owner=self.repo.acquire(key,60)
        return world.publish_batch(key,owner,ProviderBatch((),'poi','complete',(),'fixture','source'),
            provider='fixture',revision=revision,storage_reference='fixture-only',
            fresh_until=time.time()+300,usable_until=time.time()+1800)

    def fetching(self):
        row=self.jobs.claim()
        self.assertTrue(self.jobs.transition(self.key,row['owner'],'FETCHING',operation='credit-operation-1'))
        return row['owner']

    def test_dedup_revision_capacity_and_no_synthetic_neighbors(self):
        self.assertEqual(self.jobs.enqueue(self.demand_key,'fixture',1,'poi'),self.key)
        limited=DiscoveryJobs(self.repo,max_jobs=1)
        self.assertIsNone(limited.enqueue(self.demand_key,'fixture',2,'poi'))
        self.assertIsNone(self.jobs.enqueue('unknown-demand','fixture',1,'poi'))
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_demand').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0],1)

    def test_four_processes_only_one_owner(self):
        ctx=multiprocessing.get_context('spawn');output=ctx.Queue()
        workers=[ctx.Process(target=claim_process,args=(self.repo.path,output)) for _ in range(4)]
        for worker in workers:worker.start()
        for worker in workers:
            worker.join(20);self.assertEqual(worker.exitcode,0)
        self.assertEqual(sum(output.get(timeout=2) is not None for _ in workers),1)
        output.close();output.join_thread()

    def test_region_rotation_survives_restart_and_ignores_popularity(self):
        self.demand.record(22,52,['poi','roads','waterways'])
        self.demand.record(21,52,['roads','waterways'])
        for _ in range(10):self.demand.record(21,52,['poi'])
        with closing(self.repo.connect()) as c:
            demands=c.execute('SELECT key,cell_x FROM world_discovery_demand').fetchall()
        regions={d['key']:d['cell_x'] for d in demands}
        for d in demands:self.jobs.enqueue(d['key'],'fixture',1,'poi')
        claimed=[]
        for _ in range(6):
            job=DiscoveryJobs(self.repo).claim()
            claimed.append(regions[job['demand_key']])
            self.jobs.transition(job['id'],job['owner'],'CANCELLED')
        self.assertEqual(claimed,[2100,2200,2100,2200,2100,2200])
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_cursor').fetchone()[0],1)

    def test_deleted_demand_cannot_start_job(self):
        with self.repo.transaction() as c:
            c.execute('DELETE FROM world_discovery_demand')
        self.assertIsNone(self.jobs.claim())

    def test_deferred_sector_does_not_block_eligible_sector(self):
        first=self.jobs.claim()
        self.jobs.transition(first['id'],first['owner'],'DEFERRED',delay=300)
        self.demand.record(22,52,['poi'])
        with closing(self.repo.connect()) as c:
            key=c.execute('SELECT key FROM world_discovery_demand WHERE cell_x=2200').fetchone()[0]
        second=self.jobs.enqueue(key,'fixture',1,'poi')
        self.assertEqual(self.jobs.claim()['id'],second)

    def test_restart_before_http_reclaims_with_new_fence(self):
        first=self.jobs.claim(1)
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=time.time()+2):
            second=DiscoveryJobs(self.repo).claim()
            self.assertNotEqual(first['owner'],second['owner'])
            self.assertFalse(self.jobs.transition(self.key,first['owner'],'FETCHING',operation='old'))
            self.assertTrue(self.jobs.transition(self.key,second['owner'],'FETCHING',operation='new'))

    def test_expired_http_is_quarantined_and_not_pruned_or_retried(self):
        owner=self.fetching()
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=time.time()+86401):
            self.assertIsNone(DiscoveryJobs(self.repo).claim())
            self.assertEqual(self.jobs.get(self.key)['reason'],'outcome_unknown')
            self.assertEqual(self.jobs.prune(),0)
            self.assertFalse(self.jobs.transition(self.key,owner,'VALIDATING'))

    def test_crash_after_publication_reconciles_without_second_fetch(self):
        owner=self.fetching();self.jobs.transition(self.key,owner,'VALIDATING')
        snapshot=self.receipt()
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=time.time()+121):
            restored=DiscoveryJobs(self.repo)
            self.assertIsNone(restored.claim())
            self.assertFalse(restored.acknowledge(self.key,snapshot,owner))
            self.assertTrue(restored.acknowledge(self.key,snapshot))
            self.assertTrue(restored.acknowledge(self.key,snapshot))
            self.assertIsNone(restored.claim())
        self.assertEqual(self.jobs.get(self.key)['operation'],'credit-operation-1')

    def test_ack_checks_snapshot_job_and_revision(self):
        owner=self.fetching();self.jobs.transition(self.key,owner,'VALIDATING')
        wrong=self.receipt('another-job')
        self.assertFalse(self.jobs.acknowledge(self.key,wrong,owner))
        wrong_revision=self.receipt(revision=2)
        self.assertFalse(self.jobs.acknowledge(self.key,wrong_revision,owner))
        with self.repo.transaction() as c:c.execute('DELETE FROM leases WHERE key=?',(self.key,))
        correct=self.receipt()
        self.assertTrue(self.jobs.acknowledge(self.key,correct,owner))
        self.assertFalse(self.jobs.acknowledge(self.key,wrong,owner))

    def test_delay_and_attempt_limit(self):
        now=time.time()
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=now):
            row=self.jobs.claim();self.jobs.transition(self.key,row['owner'],'RETRY_AFTER',delay=30)
            self.assertIsNone(self.jobs.claim())
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=now+31):
            row=self.jobs.claim();self.jobs.transition(self.key,row['owner'],'DEFERRED')
            row=self.jobs.claim();self.jobs.transition(self.key,row['owner'],'DEFERRED')
            self.assertEqual(self.jobs.get(self.key)['state'],'FAILED_TERMINAL')
            self.assertIsNone(self.jobs.claim())

    def test_http_cannot_return_to_retry_and_requires_operation(self):
        row=self.jobs.claim()
        with self.assertRaisesRegex(ValueError,'operation_required'):
            self.jobs.transition(self.key,row['owner'],'FETCHING')
        self.jobs.transition(self.key,row['owner'],'FETCHING',operation='charged')
        with self.assertRaisesRegex(ValueError,'transition'):
            self.jobs.transition(self.key,row['owner'],'RETRY_AFTER',delay=20)

    def test_cost_operation_cannot_be_reused_by_another_job(self):
        self.fetching()
        second=self.jobs.enqueue(self.demand_key,'fixture',2,'poi')
        owner=self.jobs.claim()['owner']
        with self.assertRaises(sqlite3.IntegrityError):
            self.jobs.transition(second,owner,'FETCHING',operation='credit-operation-1')
        self.assertEqual(self.jobs.get(second)['state'],'LEASED')

    def test_passive_collection_does_not_enqueue_jobs_or_network(self):
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            self.demand.record(22,53)
            self.jobs.initialize()
            with closing(self.repo.connect()) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0],1)

    def test_expired_pending_cancelled_and_terminal_pruned(self):
        with patch('poi_infrastructure.discovery_jobs.time.time',return_value=time.time()+86401):
            self.assertIsNone(self.jobs.claim())
            self.assertEqual(self.jobs.get(self.key)['state'],'CANCELLED')
            self.assertEqual(self.jobs.prune(),1)
