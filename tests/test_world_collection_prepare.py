from contextlib import closing
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from tools.world_collection_prepare import prepare
from poi_infrastructure.discovery_runtime import cycle


class CollectionPreparationTests(unittest.TestCase):
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def setUp(self):
        fixtures.DiscoveryWorkerTests.setUp(self)
        self.provider['review_due_at']=time.time()+7200
        self.save_provider()
        self.output=Path(self.tmp.name)/'collection'

    def test_plan_needs_no_database_and_writes_nothing(self):
        result=prepare('missing',self.output)
        self.assertEqual(result['max_jobs'],3)
        self.assertEqual(result['network_calls'],0)
        self.assertFalse(self.output.exists())

    def test_prepare_three_jobs_then_restart_idle_preserves_ledger(self):
        result=prepare(self.repo.path,self.output,apply=True)
        self.assertTrue(Path(result['backup']).is_file())
        self.assertEqual(len(result['plan']['jobs']),3)
        with patch.dict('os.environ',CHAOS_POI_DISCOVERY_WORKER_ENABLED='1'):
            for _ in range(3):
                self.assertEqual(cycle(self.repo,result['permit'],execute=True,
                                      transport=self.transport)['status'],'committed')
            self.assertEqual(cycle(self.repo,result['permit'],execute=True,
                                   transport=self.transport)['status'],'idle')
        self.assertEqual(self.transport.call_count,3)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],9)
        self.assertEqual(prepare(self.repo.path,self.output,apply=True)['status'],'already_prepared')
        self.assertEqual(self.jobs.get(self.key)['attempts'],0)
        with closing(self.repo.connect()) as c:
            limits=[r[0] for r in c.execute('SELECT credit_limit FROM world_credit_scope WHERE scope LIKE ?',
                                           ('discovery:collection-sector-%',))]
        self.assertEqual(sorted(limits),[20,20,20,60])

    def test_new_directory_cannot_reset_existing_limits(self):
        prepare(self.repo.path,self.output,apply=True)
        with self.assertRaisesRegex(ValueError,'do_not_reset'):
            prepare(self.repo.path,self.output.with_name('other'),apply=True)
        self.assertFalse(self.output.with_name('other').exists())

    def test_runner_restart_sends_nothing_and_deferral_stops(self):
        from tools.world_collection_run import run
        from poi_infrastructure.upstream_priority import UpstreamPriority
        from contextlib import redirect_stdout
        import io
        result=prepare(self.repo.path,self.output,apply=True)
        with patch.dict('os.environ',CHAOS_POI_DISCOVERY_WORKER_ENABLED='1'),redirect_stdout(io.StringIO()):
            ticket=UpstreamPriority(self.repo).register()
            self.assertEqual(run(self.repo.path,result['permit'],transport=self.transport),2)
            self.transport.assert_not_called()
            UpstreamPriority(self.repo).cancel(ticket)
            with self.repo.transaction() as c:
                c.execute("UPDATE world_discovery_job SET available_at=0 WHERE state='DEFERRED'")
            self.assertEqual(run(self.repo.path,result['permit'],transport=self.transport),0)
            self.assertEqual(run(self.repo.path,result['permit'],transport=self.transport),0)
        self.assertEqual(self.transport.call_count,3)

    def test_missing_scope_stops_before_backup_or_permit(self):
        self.provider['scopes'].remove('background_refresh')
        self.save_provider()
        with self.assertRaisesRegex(ValueError,'collection_approval_required'):
            prepare(self.repo.path,self.output,apply=True)
        self.assertFalse(self.output.exists())
        self.transport.assert_not_called()
