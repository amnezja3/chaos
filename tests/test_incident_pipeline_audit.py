"""Reproductions of current integration gaps, not desired gameplay contracts."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import run
import test_incident_initializer as fixtures
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from ghostnetwork.producers import BlackNetNarrativeProducer, narrative_intent_for_signal


class IncidentPipelineAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = IncidentStore(str(Path(self.tmp.name) / 'audit.sqlite3'))
        self.initializer = IncidentInitializer(self.store)
        self.now = datetime(2026, 7, 14, 10, 45, tzinfo=timezone.utc)

    def test_partial_actor_tick_drops_other_actor_from_merged_incident(self):
        alice = fixtures.operation('op-a', owner='alice')
        bob = fixtures.operation('op-b', owner='bob')
        self.initializer.sync_operations([alice, bob], now=self.now)
        self.assertEqual(set(self.store.list_active()[0]['operation_ids']), {'op-a', 'op-b'})
        self.initializer.sync_operations([alice], now=self.now)
        self.assertEqual(self.store.list_active()[0]['operation_ids'], ['op-a'])

    def test_timeout_removes_public_incident_without_presence_check(self):
        operation = fixtures.operation('op-a')
        self.initializer.sync_operations([operation], now=self.now)
        operation['status'] = 'timeout'
        self.initializer.sync_operations([operation], now=self.now)
        self.assertEqual(self.store.list_public(), [])

    def test_expired_incident_visible_in_map_store_but_absent_from_blacknet(self):
        operation = fixtures.operation('op-a')
        self.initializer.sync_operations([operation], now=self.now)
        self.assertEqual(len(self.store.list_public()), 1)
        later = datetime(2026, 7, 14, 14, 0, tzinfo=timezone.utc)
        with patch.object(run, 'incident_store', self.store):
            self.assertEqual(run.build_blacknet_incident_facts(later), [])
        self.assertEqual(len(self.store.list_public()), 1)

    def test_incident_to_blacknet_narrative_intent_and_no_radio_route(self):
        self.initializer.sync_operations([fixtures.operation('op-a')], now=self.now)
        with patch.object(run, 'incident_store', self.store):
            facts = run.build_blacknet_incident_facts(self.now)
        snapshot = run.build_blacknet_world_signals(
            {'version': 'audit', 'facts': facts}, now=self.now, limit=4)
        signal = snapshot['signals'][0]
        self.assertEqual(signal['cta_target'], 'incident')
        self.assertEqual(narrative_intent_for_signal(signal), 'intercepted_incident_alert')
        result = BlackNetNarrativeProducer(None).enqueue_signal(snapshot, signal, target_medium='radio')
        self.assertEqual(result['reason_code'], 'unsupported_target_medium')
