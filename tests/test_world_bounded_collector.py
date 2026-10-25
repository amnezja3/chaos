from contextlib import closing, redirect_stdout
import io
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_world_discovery_worker as fixtures
from tools.world_collection_prepare import prepare
from tools.world_collector_start import start
from tools.world_runtime_check import FLAGS, inspect
from poi_infrastructure.discovery_runtime import cycle, load_permit
from poi_infrastructure.discovery_worker import PermitExpired


class BoundedCollectorTests(unittest.TestCase):
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def setUp(self):
        fixtures.DiscoveryWorkerTests.setUp(self)
        self.provider['review_due_at']=time.time()+10*86400
        self.save_provider()
        self.output=Path(self.tmp.name)/'data/collection-daemon-2036-5153-v1'

    def test_new_permit_does_not_recreate_completed_sector_jobs(self):
        old=prepare(self.repo.path,Path(self.tmp.name)/'old',apply=True)
        with patch.dict(os.environ,CHAOS_POI_DISCOVERY_WORKER_ENABLED='1'):
            for _ in range(3):
                self.assertEqual(cycle(self.repo,old['permit'],execute=True,transport=self.transport)['status'],'committed')
            result=prepare(self.repo.path,self.output,apply=True,bounded=True)
            self.assertEqual(result['plan']['jobs'],[])
            before=self.jobs.get(self.key)
            for _ in range(3):
                self.assertEqual(cycle(self.repo,result['permit'],execute=True,transport=self.transport)['status'],'idle')
            self.assertEqual(before,self.jobs.get(self.key))
        self.assertEqual(self.transport.call_count,3)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],9)

    def test_new_work_gets_seven_days_and_restart_preserves_permit_and_budget(self):
        result=prepare(self.repo.path,self.output,apply=True,bounded=True)
        path=Path(result['permit']);original=path.read_bytes()
        with patch.dict(os.environ,CHAOS_POI_DISCOVERY_WORKER_ENABLED='1'):
            outcome=cycle(self.repo,path,execute=True,transport=self.transport)
        self.assertEqual(outcome['status'],'committed')
        with closing(self.repo.connect()) as c:
            row=c.execute('SELECT fetched,retain_until FROM world_snapshot s JOIN world_retention r ON r.snapshot_id=s.id').fetchone()
        self.assertAlmostEqual(row['retain_until']-row['fetched'],604800,delta=2)
        self.assertEqual(prepare(self.repo.path,self.output,apply=True,bounded=True)['status'],'already_prepared')
        self.assertEqual(original,path.read_bytes())
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        with self.assertRaises(ValueError):
            prepare(self.repo.path,self.output.with_name('new-directory'),apply=True,bounded=True)

    def test_expiry_is_normal_shutdown_without_renewal_or_network(self):
        from tools.world_discovery_worker import main
        result=prepare(self.repo.path,self.output,apply=True,bounded=True)
        path=Path(result['permit']);data=json.loads(path.read_text())
        with patch('time.time',return_value=data['until']+1):
            with self.assertRaises(PermitExpired):load_permit(path)
            with patch.dict(os.environ,CHAOS_POI_DISCOVERY_WORKER_ENABLED='1'), \
                    patch('sys.argv',['worker','--execute','--serve','--db',str(self.repo.path),'--permit',str(path)]), \
                    patch('tools.world_discovery_worker.signal.signal'),redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(),0)
            self.assertEqual(json.loads(out.getvalue())['status'],'permit_expired')
        self.assertEqual(json.loads(path.read_text())['until'],data['until'])
        self.transport.assert_not_called()

    def test_launcher_copies_only_requested_secret_and_does_not_log_it(self):
        prepare(self.repo.path,self.output,apply=True,bounded=True)
        root=Path(self.tmp.name)
        env=dict(FLAGS,status='online',pm_cwd=str(root),CHAOS_MAPLARK_API_KEY='private-fixture',UNRELATED_SECRET='no-copy')
        env['CHAOS_POI_ROUTING_ENABLED']='1'
        runner=Mock(side_effect=[SimpleNamespace(stdout=json.dumps([dict(name='chaos',pm2_env=env)])),SimpleNamespace()])
        with patch('tools.world_collector_start.__file__',str(root/'tools/start.py')), \
                patch('tools.world_collector_start.Repository',return_value=self.repo):
            result=start(runner=runner)
        self.assertNotIn('private-fixture',json.dumps(result))
        child=runner.call_args.kwargs['env']
        self.assertEqual(child['CHAOS_MAPLARK_API_KEY'],'private-fixture')
        self.assertNotIn('UNRELATED_SECRET',child)
        self.assertNotIn('private-fixture',str(runner.call_args.args))
        self.assertIn('bounded',runner.call_args.args[0])
        self.transport.assert_not_called()

    def test_runtime_online_requires_worker_flags_and_matching_cwd(self):
        root=Path(self.tmp.name)
        web=dict(name='chaos',pm2_env=dict(FLAGS,status='online',pm_cwd=str(root)))
        web['pm2_env']['CHAOS_POI_ROUTING_ENABLED']='1'
        worker=dict(name='chaos-world-discovery-worker',pm2_env=dict(status='online',pm_cwd=str(root),
            CHAOS_POI_DISCOVERY_WORKER_ENABLED='1',CHAOS_POI_PRIORITY_ENABLED='1',CHAOS_POI_ROUTING_ENABLED='1'))
        self.assertTrue(inspect([web,worker],root,routing='1',worker='online')['ok'])
        self.assertFalse(inspect([web],root,routing='1',worker='online')['ok'])
        self.assertFalse(inspect([web,worker],root,routing='1')['ok'])
        worker['pm2_env']['CHAOS_POI_PRIORITY_ENABLED']='0'
        self.assertFalse(inspect([web,worker],root,routing='1',worker='online')['ok'])

    def test_launcher_rejects_missing_secret_and_empty_background_route(self):
        from poi_infrastructure.routing import Routing
        prepare(self.repo.path,self.output,apply=True,bounded=True)
        root=Path(self.tmp.name)
        env=dict(FLAGS,status='online',pm_cwd=str(root))
        env['CHAOS_POI_ROUTING_ENABLED']='1'
        with patch('tools.world_collector_start.__file__',str(root/'tools/start.py')), \
                patch('tools.world_collector_start.Repository',return_value=self.repo):
            runner=Mock(return_value=SimpleNamespace(stdout=json.dumps([dict(name='chaos',pm2_env=env)])))
            with self.assertRaisesRegex(ValueError,'credential_unavailable'):start(runner=runner)
            self.assertEqual(runner.call_count,1)
            env['CHAOS_MAPLARK_API_KEY']='private-fixture'
            routing=Routing(self.repo);routing.initialize();routing.save('roads','background',0,[],'test')
            runner=Mock(return_value=SimpleNamespace(stdout=json.dumps([dict(name='chaos',pm2_env=env)])))
            with self.assertRaisesRegex(ValueError,'background_route_not_maplark'):start(runner=runner)
            self.assertEqual(runner.call_count,1)
        self.transport.assert_not_called()
