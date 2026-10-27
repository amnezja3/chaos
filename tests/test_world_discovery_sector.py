"""Sector collection must not reuse or consume legacy radius jobs."""
from contextlib import closing
from dataclasses import replace
import json
import unittest

import test_world_discovery_worker as fixtures
from poi_infrastructure.discovery_producer import prepare_jobs
from poi_infrastructure.discovery_runtime import load_permit


class SectorCollectionTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def test_full_poi_archive_uses_all_scanner_tags_without_certifying_radius(self):
        from poi_infrastructure.discovery_queue import DemandQueue
        from poi_infrastructure.world_contract import FILTERS
        from poi_infrastructure.world_region_candidate import prepare
        from poi_infrastructure.world_adapters import plan_maplark_region,normalize_maplark,MAPLARK_VERSION
        from poi_infrastructure.world_contract import Provenance
        import time
        DemandQueue(self.repo).record(21,52,['poi'])
        self.permit=replace(self.permit,acquisition='sector-bbox-v1',profiles=frozenset({'poi'}),budget_id='poi-test')
        for scope in self.permit.budget_scopes('poi'):
            self.ledger.configure_scope('maplark',scope,time.time()-1,self.permit.until,100)
        self.worker.permit=self.permit
        self.assertEqual(len(prepare_jobs(self.repo,self.permit,apply=True)['jobs']),1)
        result=self.worker.run_one()
        self.assertEqual(result['status'],'committed')
        self.assertEqual(result['coverage'],'UNKNOWN')
        params=dict(self.transport.call_args.args[2].params)
        self.assertEqual(params['tags'],'|'.join(FILTERS))
        plan=plan_maplark_region((21,52,21.01,52.01),profile='poi')
        raw=self.transport.return_value[2]
        batch=normalize_maplark(raw['body'],raw['response_headers'],Provenance('maplark',MAPLARK_VERSION,'test',time.time()),profile='poi')
        self.assertFalse(prepare(batch,plan).region_certified)

    def sector(self):
        self.permit = replace(self.permit, acquisition='sector-bbox-v1')
        self.worker.permit = self.permit
        return prepare_jobs(self.repo, self.permit, apply=True)['jobs'][0]

    def test_sector_has_separate_identity_and_does_not_claim_radius(self):
        key = self.sector()
        self.assertNotEqual(key, self.key)
        result = self.worker.run_one()
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(result['coverage'], 'UNKNOWN')
        params = dict(self.transport.call_args.args[2].params)
        self.assertEqual(tuple(map(float, params['bbox'].split(','))), (21,52,21.01,52.01))
        self.assertNotIn('radius', params)
        self.assertEqual(self.jobs.get(self.key)['state'], 'PENDING')
        self.assertEqual(self.jobs.get(self.key)['attempts'], 0)
        self.assertEqual(self.jobs.get(key)['state'], 'COMMITTED')
        with closing(self.repo.connect()) as c:
            payload = json.loads(c.execute('SELECT payload FROM world_snapshot').fetchone()[0])
        context = payload['observation_context']
        self.assertEqual(context['acquisition'], 'sector-bbox-v1')
        self.assertEqual(context['demand_bounds'], [21,52,21.01,52.01])
        self.assertEqual(context['request_params'], params)
        self.assertNotIn('coverage', payload)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)
        self.assertEqual(prepare_jobs(self.repo, self.permit, apply=True)['jobs'], [])
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.transport.assert_called_once()

    def test_legacy_permit_cannot_consume_sector_job(self):
        key = self.sector()
        self.worker.permit = replace(self.permit, acquisition='radius-300-v1')
        self.assertEqual(self.worker.run_one()['status'], 'committed')
        self.assertEqual(self.jobs.get(key)['state'], 'PENDING')
        self.assertEqual(self.jobs.get(key)['attempts'], 0)

    def test_partial_sector_is_observation_not_coverage_and_not_retried(self):
        self.sector()
        self.transport.return_value[2]['response_headers']['X-Has-More'] = 'true'
        result = self.worker.run_one()
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(result['response_completeness'], 'partial')
        self.assertEqual(result['coverage'], 'UNKNOWN')
        self.assertTrue(result['reasons'])
        with closing(self.repo.connect()) as c:
            payload = json.loads(c.execute('SELECT payload FROM world_snapshot').fetchone()[0])
            self.assertEqual(payload['completeness'], 'partial')
            self.assertNotIn('coverage', payload)
        self.assertEqual(self.worker.run_one()['status'], 'idle')
        self.transport.assert_called_once()

    def test_additive_migration_preserves_legacy_job_and_budget(self):
        self.worker.run_one()
        before = self.jobs.get(self.key)
        with self.repo.transaction() as c:
            c.execute('ALTER TABLE world_discovery_job DROP COLUMN acquisition')
        self.jobs.initialize()
        self.jobs.initialize()
        self.assertEqual(self.jobs.get(self.key), before)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)

    def test_release_check_detects_missing_collection_schema_without_migrating(self):
        from tools.world_release_check import inspect
        self.assertTrue(inspect(self.repo.path, require_collection=True)['collection_schema_ready'])
        with self.repo.transaction() as c:
            c.execute('ALTER TABLE world_discovery_job DROP COLUMN acquisition')
        result = inspect(self.repo.path, require_collection=True)
        self.assertFalse(result['ok'])
        self.assertFalse(result['collection_schema_ready'])
        with closing(self.repo.connect()) as c:
            self.assertNotIn('acquisition', {r[1] for r in c.execute('PRAGMA table_info(world_discovery_job)')})

    def test_permit_loader_legacy_new_and_invalid(self):
        from pathlib import Path
        path = Path(self.tmp.name) / 'permit.json'
        data = dict(cells=[[2100,5200]], profiles=['roads'], until=self.permit.until,
                    reservation=20, budget_id='test')
        path.write_text(json.dumps(data))
        self.assertEqual(load_permit(path).acquisition, 'radius-300-v1')
        data['acquisition'] = 'sector-bbox-v1'
        path.write_text(json.dumps(data))
        self.assertEqual(load_permit(path).acquisition, 'sector-bbox-v1')
        data['acquisition'] = 'whole-planet'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            load_permit(path)

    def test_plan_reports_sector_without_cost_or_claim(self):
        self.permit = replace(self.permit, acquisition='sector-bbox-v1')
        result = prepare_jobs(self.repo, self.permit)
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(result['jobs'][0]['acquisition'], 'sector-bbox-v1')
        self.assertEqual(self.jobs.get(self.key)['attempts'], 0)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0], 1)
        self.transport.assert_not_called()
