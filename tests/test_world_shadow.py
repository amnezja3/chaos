from dataclasses import replace
import os
import sqlite3
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
