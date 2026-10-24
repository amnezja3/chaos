from contextlib import closing
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_dashboard import coverage,budget_projection
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure import scan_metrics
from world_dashboard_fixture import seed


def metric_writer(path):
    repo=Repository(path)
    for _ in range(10):scan_metrics.record(repo,{'world'},0,'success',.1)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name)/'poi.sqlite3');self.ids=seed(self.repo)

    def test_area_exact_observations_empty_and_layer_are_separate(self):
        d=coverage(self.repo)
        self.assertEqual(d['hidden_empty'],1)
        self.assertEqual(len(d['items']),3)
        self.assertEqual([i['state'] for i in d['items']].count('COMPLETE_FRESH'),1)
        self.assertEqual([i['state'] for i in d['items']].count('UNKNOWN'),2)
        self.assertEqual(len(coverage(self.repo,'roads',True)['items']),2)
        self.assertEqual(coverage(self.repo,'inland_water')['items'][0]['state'],'UNKNOWN')
        empty=next(i for i in coverage(self.repo,'roads',True)['items'] if i['empty'])
        self.assertEqual(empty['state'],'COMPLETE_FRESH')
        self.assertTrue(empty['local_read_allowed'])

    def test_expiry_and_revocation_do_not_turn_into_usable_green(self):
        with patch('poi_infrastructure.world_dashboard.time.time',return_value=time.time()+301):
            row=coverage(self.repo,'roads')['items'][0]
            self.assertEqual(row['state'],'COMPLETE_STALE');self.assertFalse(row['local_read_allowed'])
        with self.repo.transaction() as c:
            p=json.loads(c.execute("SELECT config FROM poi_provider_config WHERE id='fixture'").fetchone()[0]);p['scopes']=[]
            c.execute("UPDATE poi_provider_config SET config=? WHERE id='fixture'",(json.dumps(p),))
        row=coverage(self.repo,'roads')['items'][0]
        self.assertFalse(row['policy_allowed']);self.assertFalse(row['local_read_allowed'])

    def test_passive_refresh_preserves_db_and_no_network(self):
        with closing(self.repo.connect()) as c: before='\n'.join(c.iterdump())
        with patch('socket.create_connection',side_effect=AssertionError('HTTP forbidden')):
            for _ in range(20): self.assertEqual(coverage(self.repo)['network_calls'],0)
        with closing(self.repo.connect()) as c: self.assertEqual('\n'.join(c.iterdump()),before)

    def test_missing_database_not_created_and_bad_filter_rejected(self):
        p=Path(self.tmp.name)/'missing.sqlite3'
        self.assertEqual(coverage(Repository(p))['items'],[]);self.assertFalse(p.exists())
        with self.assertRaises(ValueError): coverage(self.repo,'invalid')

    def test_corrupt_snapshot_not_shown_as_complete(self):
        with self.repo.transaction() as c: c.execute('UPDATE world_snapshot SET digest=? WHERE id=?',('bad',self.ids[0]))
        self.assertFalse(any(i['id']==self.ids[0] for i in coverage(self.repo)['items']))

    def test_internal_thresholds_keep_provider_balance_unknown(self):
        ledger=CreditBudget(self.repo);ledger.initialize()
        ledger.configure_window('maplark','test',time.time()-1,time.time()+3600,100)
        for amount,threshold in ((70,70),(15,85),(10,95)):
            ledger.reserve('maplark',str(amount),amount);ledger.settle('maplark',str(amount),amount)
            a=budget_projection(self.repo)[0]
            self.assertEqual(a['windows'][0]['warning_threshold'],threshold)
            self.assertIsNone(a['provider_balance'])

    def test_metric_denominators_sources_error_and_empty(self):
        scan_metrics.initialize(self.repo)
        self.assertIsNone(scan_metrics.summary(self.repo)['world_local_scan_ratio'])
        for sources,attempts,outcome in (({'world'},0,'success'),({'fresh'},0,'empty'),({'world','fresh'},0,'success'),({'stale'},1,'success'),(set(),2,'api_error')):
            scan_metrics.record(self.repo,sources,attempts,outcome,.2)
        result=scan_metrics.summary(self.repo)
        self.assertEqual((result['attempts'],result['successful'],result['errors']),(5,4,1))
        self.assertEqual(result['sources'],dict(world=1,cache=1,mixed=1,network=1))
        self.assertEqual(result['transport_attempts'],3)
        self.assertEqual(result['world_local_scan_ratio'],.25)
        self.assertEqual(result['empty_successes'],1)
        self.assertEqual(result['latency_p95_upper_seconds'],.5)

    def test_metric_context_isolated_from_probe_and_survives_missing_schema(self):
        scan_metrics.transport_attempt();scan_metrics.source('upstream')
        with patch.dict('os.environ',CHAOS_POI_METRICS_ENABLED='1',CHAOS_POI_CACHE_PATH=self.repo.path):
            token=scan_metrics.begin();scan_metrics.source('world');scan_metrics.finish(token,'success')
        self.assertFalse(scan_metrics.summary(self.repo)['prepared'])

    def test_manual_account_observation_never_settles_uncertain_cost(self):
        from poi_infrastructure.provider_observation import initialize,save,read
        initialize(self.repo)
        ledger=CreditBudget(self.repo);ledger.initialize()
        ledger.configure_window('geoapify','test',time.time()-1,time.time()+3600,20)
        ledger.reserve('geoapify','uncertain',5);ledger.settle('geoapify','uncertain',None)
        now=time.time()
        save(self.repo,'geoapify',0,3000,7,now-3600,now+3600,now)
        self.assertEqual(read(self.repo,'geoapify')['remaining'],2993)
        with self.assertRaisesRegex(ValueError,'conflict'):
            save(self.repo,'geoapify',0,3000,7,now-3600,now+3600,now)
        with closing(self.repo.connect()) as c:
            row=c.execute("SELECT state,charged FROM world_credit_operation WHERE account='geoapify'").fetchone()
        self.assertEqual(tuple(row),('uncertain',None))
        with patch('poi_infrastructure.provider_observation.time.time',return_value=now+4000):
            self.assertTrue(read(self.repo,'geoapify')['stale'])

    def test_metric_context_records_source_even_when_masa_disabled(self):
        scan_metrics.initialize(self.repo)
        from poi_infrastructure.presentation import publish
        with patch.dict('os.environ',CHAOS_POI_METRICS_ENABLED='1',CHAOS_POI_MASA_UX_ENABLED='0',CHAOS_POI_CACHE_PATH=self.repo.path):
            token=scan_metrics.begin();publish('world');scan_metrics.finish(token,'empty')
        value=scan_metrics.summary(self.repo)
        self.assertEqual(value['world_local_scan_ratio'],1)
        self.assertEqual(value['empty_successes'],1)

    def test_aggregate_retention_has_no_identifiers(self):
        scan_metrics.initialize(self.repo)
        now=time.time()
        scan_metrics.record(self.repo,{'world'},0,'success',1,now-9*86400)
        scan_metrics.record(self.repo,{'fresh'},0,'success',1,now)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT sum(samples) FROM world_scan_metric').fetchone()[0],1)
            columns={r[1] for r in c.execute('PRAGMA table_info(world_scan_metric)')}
        self.assertEqual(columns,{'hour','source','outcome','latency_bucket','samples','transport_attempts','elapsed_ms'})

    def test_release_report_uses_copy_preserves_production_and_requires_migration(self):
        from tools.world_release_check import inspect
        from poi_infrastructure.discovery_jobs import DiscoveryJobs
        from tools.poi_world import initialize
        DiscoveryJobs(self.repo).initialize()
        with closing(self.repo.connect()) as c: before='\n'.join(c.iterdump())
        self.assertFalse(inspect(self.repo.path,True)['ok'])
        with closing(self.repo.connect()) as c:self.assertEqual('\n'.join(c.iterdump()),before)
        initialize(self.repo.path,canonical=True,discovery=True,jobs=True,metrics=True)
        result=inspect(self.repo.path,True)
        self.assertTrue(result['ok']);self.assertEqual(result['production_writes'],0)

    def test_four_process_metric_updates_do_not_lose_counts(self):
        import multiprocessing
        scan_metrics.initialize(self.repo)
        ctx=multiprocessing.get_context('spawn')
        children=[ctx.Process(target=metric_writer,args=(self.repo.path,)) for _ in range(4)]
        try:
            for child in children:child.start()
            for child in children:
                child.join(20);self.assertEqual(child.exitcode,0)
        finally:
            for child in children:
                if child.is_alive():child.terminate();child.join()
        self.assertEqual(scan_metrics.summary(self.repo)['successful'],40)
