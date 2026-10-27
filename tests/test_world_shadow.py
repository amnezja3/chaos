from dataclasses import replace
import os
import sqlite3
import time
from unittest.mock import patch
import unittest

import test_world_maplark_pilot as fixtures
from poi_infrastructure.service import POIError
from poi_infrastructure.world_storage import CanonicalWorldRepository


class WorldShadowTests(unittest.TestCase):
    def setUp(self):
        fixtures.PilotTests.setUp(self)
        self.world=CanonicalWorldRepository(self.service.repo)
        self.world.initialize_canonical()
        env=patch.dict(os.environ,CHAOS_POI_WORLD_INGEST_ENABLED='1',CHAOS_POI_WORLD_REPOSITORY_ENABLED='1')
        env.start();self.addCleanup(env.stop)
        scope=patch.dict(os.environ,CHAOS_POI_WORLD_PILOT_USER='tester',
            CHAOS_POI_WORLD_PILOT_CENTER='52,21',CHAOS_POI_WORLD_PILOT_UNTIL=str(time.time()+3600))
        scope.start();self.addCleanup(scope.stop)
        self.options['_world_pilot_user']='tester'
        batch=fixtures.normalized([fixtures.point()])
        self.batch=replace(batch,objects=tuple(replace(o,provenance=replace(o.provenance,license_ref='fixture-only')) for o in batch.objects))

    fetch=fixtures.PilotTests.fetch

    def grant(self):
        v=self.registry.list()[0]
        v=self.registry.decision(v['id'],v['revision'],'approved_for_defined_use',
            ['normal_scan','storage','world_storage'],{k:v['evidence'][k] for k in ('source_url','reference','notes')},
            v['review_due_at'],'fixture')
        return self.registry.enable(v['id'],v['revision'],True,'fixture')

    def evict_cache(self):
        with self.service.repo.transaction() as c:
            c.execute('DELETE FROM cache')

    def test_existing_cache_permission_does_not_authorize_world_store(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream:
            self.fetch();self.evict_cache();self.fetch()
            self.assertEqual(upstream.call_count,2)
        self.assertEqual(self.world.status()['snapshots'],0)

    def test_world_hit_after_exact_cache_eviction_needs_no_upstream(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream:
            first=self.fetch();self.evict_cache();second=self.fetch()
            self.assertEqual(first,second)
            upstream.assert_called_once()
        self.assertEqual(self.world.status()['snapshots'],1)

    def test_optional_write_failure_does_not_fail_scan_or_duplicate_bill(self):
        self.grant()
        for failure in (sqlite3.OperationalError('disk full'),RuntimeError('fixture')):
            self.evict_cache()
            with (patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream,
                  patch.object(CanonicalWorldRepository,'publish_batch',side_effect=failure)):
                self.assertEqual(len(self.fetch()['elements']),1)
                upstream.assert_called_once()

    def test_missing_schema_or_read_failure_falls_through_to_existing_scanner(self):
        self.grant()
        from poi_infrastructure.world_read import WorldReadPlanner
        with (patch.object(WorldReadPlanner,'read',side_effect=sqlite3.OperationalError('fixture')),
              patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream):
            self.assertEqual(len(self.fetch()['elements']),1)
            upstream.assert_called_once()

    def test_rollback_flags_preserve_data_and_return_to_cache_then_upstream(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream:
            self.fetch()
            with patch.dict(os.environ,CHAOS_POI_WORLD_INGEST_ENABLED='0',CHAOS_POI_WORLD_REPOSITORY_ENABLED='0'):
                self.fetch();upstream.assert_called_once()
                self.evict_cache();self.fetch()
                self.assertEqual(upstream.call_count,2)
        self.assertEqual(self.world.status()['snapshots'],1)

    def test_provider_disable_cannot_be_bypassed_by_world(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            self.fetch()
        self.evict_cache()
        v=self.registry.list()[0]
        self.registry.enable(v['id'],v['revision'],False,'fixture')
        with self.assertRaisesRegex(POIError,'not_approved'):
            self.fetch()

    def test_scope_exclusion_uses_normal_scanner_without_world(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            self.fetch()
        self.evict_cache()
        self.options['_world_pilot_user']='someone-else'
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})) as upstream:
            self.assertEqual(len(self.fetch()['elements']),1)
            upstream.assert_called_once()
        self.assertEqual(self.world.status()['snapshots'],1)

    def test_pilot_tool_selective_eviction_and_busy_protection(self):
        from tools.world_storage_pilot import inspect
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            self.fetch()
        repo=self.service.repo
        with repo.transaction() as c:
            key=c.execute('SELECT key FROM cache').fetchone()[0]
            ledger_before=[tuple(r) for r in c.execute('SELECT * FROM world_credit_operation')]
        result=inspect(repo.path,52,21,evict=True)
        self.assertEqual(result['removed_cache_entries'],0)
        lease=repo.acquire(key,60)
        with self.assertRaisesRegex(ValueError,'scan_in_flight'):
            inspect(repo.path,52,21,evict=True,apply=True)
        repo.release(key,lease)
        result=inspect(repo.path,52,21,evict=True,apply=True)
        self.assertEqual(result['removed_cache_entries'],1)
        self.assertEqual(self.world.status()['snapshots'],1)
        with repo.transaction() as c:
            self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM world_credit_operation')],ledger_before)
        with self.assertRaisesRegex(ValueError,'fresh_world_result_required'):
            inspect(repo.path,53,22,evict=True,apply=True)
        self.assertEqual(inspect(repo.path,52,21,prune=True,apply=True)['pruned_snapshots'],0)
        with repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET usable_until=?',(time.time()-1,))
        self.assertEqual(inspect(repo.path,53,22,prune=True,apply=True)['pruned_snapshots'],0)
        self.assertEqual(inspect(repo.path,52,21,prune=True,apply=True)['pruned_snapshots'],1)

    def test_log_key_inspection_and_eviction_preserve_other_cache(self):
        from tools.world_storage_pilot import inspect
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            self.fetch()
        repo=self.service.repo
        with repo.transaction() as c:
            key=c.execute('SELECT key FROM cache').fetchone()[0]
            c.execute("INSERT INTO cache SELECT 'unrelated',payload,digest,fetched,bytes FROM cache WHERE key=?",(key,))
        self.assertEqual(inspect(repo.path,key_prefix=key[:12])['world_state'],'COMPLETE_FRESH')
        result=inspect(repo.path,key_prefix=key[:12],evict=True,apply=True)
        self.assertEqual(result['removed_cache_entries'],1)
        with repo.transaction() as c:
            self.assertEqual(c.execute('SELECT key FROM cache').fetchone()[0],'unrelated')
        for bad in ('%', 'abc', 'z'*12):
            with self.assertRaisesRegex(ValueError,'key_prefix_requires'):
                inspect(repo.path,key_prefix=bad)
        with self.assertRaisesRegex(ValueError,'choose_key_or_coordinates'):
            inspect(repo.path,52,21,key_prefix=key[:12])
        with self.assertRaisesRegex(ValueError,'world_key_missing_or_ambiguous'):
            inspect(repo.path,key_prefix='f'*64)
        with repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET fresh_until=?',(time.time()-1,))
        with self.assertRaisesRegex(ValueError,'fresh_world_result_required'):
            inspect(repo.path,key_prefix=key[:12],evict=True,apply=True)

    def test_local_world_survives_busy_network_and_exhausted_shared_budget(self):
        self.grant()
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(self.batch,{})):
            expected=self.fetch()
        self.evict_cache()
        from poi_infrastructure.credit_budget import CreditBudget
        from poi_infrastructure.upstream_priority import UpstreamPriority
        ledger=CreditBudget(self.service.repo)
        self.assertTrue(ledger.reserve('maplark','other-in-flight',100))
        gate=UpstreamPriority(self.service.repo)
        slot=gate.acquire(lane='background');ticket=gate.register()
        self.assertIsNotNone(slot)
        try:
            with (patch.dict(os.environ,CHAOS_POI_PRIORITY_ENABLED='1'),
                  patch('poi_infrastructure.maplark_pilot.acquire_maplark',side_effect=AssertionError('network forbidden'))):
                self.assertEqual(self.fetch(),expected)
            self.assertTrue(self.service.repo.owns('@upstream',slot))
            self.assertEqual(ledger.status('maplark')[0]['committed'],100)
        finally:
            self.service.repo.release('@upstream',slot);gate.cancel(ticket)
