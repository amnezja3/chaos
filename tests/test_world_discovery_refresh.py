from contextlib import closing
from dataclasses import replace
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from poi_infrastructure.discovery_producer import prepare_jobs
from poi_infrastructure.discovery_queue import DemandQueue
from tools.world_collection_prepare import prepare


class RefreshTests(unittest.TestCase):
    setUp=fixtures.DiscoveryWorkerTests.setUp
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def enable_refresh(self):
        self.provider['review_due_at']=time.time()+10*86400
        self.save_provider()
        self.permit=replace(self.permit,retention_seconds=604800,refresh_seconds=604800)

    def test_completed_generation_waits_then_refreshes_once_without_reset(self):
        self.assertEqual(self.worker.run_one()['status'],'committed')
        self.enable_refresh()
        before=self.jobs.get(self.key)
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_refresh SET due=?',(time.time()-1,))
        plan=prepare_jobs(self.repo,self.permit)
        self.assertEqual(len(plan['jobs']),1)
        new=prepare_jobs(self.repo,self.permit,apply=True)['jobs']
        self.assertEqual(len(new),1)
        self.assertNotEqual(new[0],self.key)
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        self.assertEqual(self.jobs.get(self.key),before)
        # A rollback to a legacy permit cannot execute the refresh generation.
        self.assertEqual(self.worker.run_one()['status'],'idle')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        self.transport.assert_called_once()
        from poi_infrastructure.discovery_worker import DiscoveryWorker
        outcome=DiscoveryWorker(self.repo,self.permit,enabled=lambda:True,transport=self.transport).run_one()
        self.assertEqual(outcome['status'],'committed')
        self.assertEqual(self.transport.call_count,2)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],6)
        with closing(self.repo.connect()) as c:
            receipt=c.execute('SELECT * FROM world_discovery_refresh').fetchone()
        self.assertEqual(receipt['generation'],1)
        self.assertEqual(receipt['settled'],1)
        self.assertGreater(receipt['due'],time.time()+604790)

    def test_competing_enqueues_get_one_generation_and_keep_old_receipt(self):
        self.worker.run_one()
        self.enable_refresh()
        prepare_jobs(self.repo,self.permit,apply=True)
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_refresh SET due=0')
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:prepare_jobs(self.repo,self.permit,apply=True),range(2)))
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0],2)
            self.assertEqual(c.execute('SELECT generation FROM world_discovery_refresh').fetchone()[0],1)
        self.assertEqual(sum(len(r['jobs']) for r in results),1)

    def test_uncertain_or_pending_generation_is_never_recreated(self):
        self.enable_refresh()
        for state in ('PENDING','POLICY_BLOCKED','FAILED_TERMINAL'):
            with self.repo.transaction() as c:
                c.execute('DELETE FROM world_discovery_refresh')
                c.execute('UPDATE world_discovery_job SET state=?,updated=?',(state,time.time()-700000))
            self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        self.transport.assert_not_called()

    def test_committed_geometry_with_uncertain_charge_cannot_refresh(self):
        self.worker.run_one()
        self.enable_refresh()
        prepare_jobs(self.repo,self.permit,apply=True)
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_refresh SET due=0')
            c.execute("UPDATE world_credit_operation SET state='uncertain',charged=NULL")
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        self.transport.assert_called_once()

    def test_receipt_survives_pruning_and_missing_demand_prevents_refresh(self):
        self.worker.run_one()
        self.enable_refresh()
        prepare_jobs(self.repo,self.permit,apply=True)
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_job SET expires=0')
        self.assertEqual(self.jobs.prune(),1)
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        with self.repo.transaction() as c:
            c.execute('UPDATE world_discovery_refresh SET due=0')
            c.execute('UPDATE world_discovery_demand SET expires=0')
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['jobs'],[])
        DemandQueue(self.repo).record(21,52,['roads'])
        self.assertEqual(len(prepare_jobs(self.repo,self.permit,apply=True)['jobs']),1)

    def test_plan_is_read_only_and_bad_intervals_are_rejected(self):
        self.enable_refresh()
        prepare_jobs(self.repo,self.permit)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_refresh').fetchone()[0],0)
        for value in (True,60,604800.0):
            with self.assertRaises(ValueError):replace(self.permit,refresh_seconds=value).validate()

    def test_expired_unsent_generation_can_serve_new_demand_without_reusing_operation(self):
        self.enable_refresh()
        prepare_jobs(self.repo,self.permit,apply=True)
        with self.repo.transaction() as c:
            c.execute("UPDATE world_discovery_job SET state='CANCELLED',expires=0 WHERE id=?",(self.key,))
        self.assertEqual(self.jobs.prune(),0)
        DemandQueue(self.repo).record(21,52,['roads'])
        new=prepare_jobs(self.repo,self.permit,apply=True)['jobs']
        self.assertEqual(len(new),1)
        self.assertNotEqual(new[0],self.key)
        self.assertEqual(self.jobs.get(self.key)['state'],'CANCELLED')
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)
        self.transport.assert_not_called()

    def test_region_admission_does_not_manufacture_demand_or_expand_budget(self):
        self.enable_refresh()
        output=Path(self.tmp.name)/'regions'
        result=prepare(self.repo.path,output,apply=True,bounded=True,
                       cells=[(2102,5200),(2103,5200)],identity='approved-regions-v1',refresh=True)
        self.assertEqual(result['plan']['jobs'],[])
        self.assertEqual(result['shared_credit_limit'],60)
        self.assertEqual(result['max_jobs'],6)
        self.assertEqual(prepare(self.repo.path,output,apply=True,bounded=True,
            cells=[(2102,5200),(2103,5200)],identity='approved-regions-v1',refresh=True)['status'],'already_prepared')
        self.transport.assert_not_called()

    def test_geoapify_pruned_unsent_failure_gets_new_generation(self):
        DemandQueue(self.repo).record(21,52,['poi'])
        with closing(self.repo.connect()) as c:
            demand=c.execute("SELECT key FROM world_discovery_demand WHERE layer='poi'").fetchone()[0]
        args=(demand,'geoapify',1,'poi')
        options=dict(acquisition='geoapify-commercial-v1',refresh_seconds=604800)
        key=self.jobs.enqueue(*args,**options)
        with self.repo.transaction() as c:
            c.execute("UPDATE world_discovery_job SET state='FAILED_TERMINAL',expires=0 WHERE id=?",(key,))
        self.assertEqual(self.jobs.prune(),1)
        planned=self.jobs.enqueue(*args,**options,plan_only=True)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT job_id FROM world_discovery_refresh WHERE job_id=?',(key,)).fetchone()[0],key)
        new=self.jobs.enqueue(*args,**options)
        self.assertEqual(new,planned);self.assertNotEqual(new,key)
        self.assertEqual(self.jobs.enqueue(*args,**options),None)
        self.transport.assert_not_called()

    def test_geoapify_orphan_with_uncertain_reservation_stays_blocked(self):
        DemandQueue(self.repo).record(21,52,['poi'])
        with closing(self.repo.connect()) as c:
            demand=c.execute("SELECT key FROM world_discovery_demand WHERE layer='poi'").fetchone()[0]
        args=(demand,'geoapify',1,'poi')
        options=dict(acquisition='geoapify-commercial-v1',refresh_seconds=604800)
        key=self.jobs.enqueue(*args,**options)
        self.ledger.configure_recurring('geoapify',2700,83700)
        self.ledger.reserve('geoapify','discovery:'+key,6)
        with self.repo.transaction() as c:
            c.execute("UPDATE world_credit_operation SET state='uncertain' WHERE account='geoapify'")
            c.execute("UPDATE world_discovery_job SET state='FAILED_TERMINAL',expires=0 WHERE id=?",(key,))
        self.jobs.prune()
        self.assertIsNone(self.jobs.enqueue(*args,**options))
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],6)
        self.transport.assert_not_called()


if __name__=='__main__':unittest.main()
