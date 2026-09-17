import copy
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

import run
import test_incident_initializer as fixtures
import test_narrative_publications as narrative_fixtures
from database import PlayerOperationStore, GameStateDeltaBus, db_connect, init_db
from response_network.incident_store import IncidentStore
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_publications import IncidentPublicationRelay
from response_network.response_dispatcher import ResponseDispatcher
from response_network.npc_capsule_store import NPCCapsuleStore
from ghostnetwork.publication import NarrativePublicationService


class IncidentLifecyclePublicationsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'game.sqlite3')
        init_db(self.path)
        self.store = IncidentStore(self.path)
        self.initializer = IncidentInitializer(self.store)
        self.now = datetime(2026, 7, 14, 10, 45, tzinfo=timezone.utc)

    def incident(self):
        op = fixtures.operation('op-a')
        self.initializer.sync_operations([op], now=self.now)
        return op, self.store.get(op['operation_risk_meter']['incident_id'])

    def test_offline_long_running_operation_and_independent_cooling_deadline(self):
        op = fixtures.operation('op-long')
        op['expires_at'] = (self.now + timedelta(hours=4)).isoformat()
        self.initializer.sync_operations([op], now=self.now)
        incident_id = op['operation_risk_meter']['incident_id']
        self.initializer.tick_lifecycle(now=self.now + timedelta(hours=3))
        self.assertNotEqual(self.store.get(incident_id)['status'], 'cooling')
        end = self.now + timedelta(hours=4)
        self.initializer.tick_lifecycle(now=end)
        cooling = self.store.get(incident_id)
        self.assertEqual(cooling['status'], 'cooling')
        self.assertEqual(datetime.fromisoformat(cooling['expires_at']), end + timedelta(minutes=30))
        self.initializer.tick_lifecycle(now=end + timedelta(minutes=29))
        self.assertEqual(self.store.get(incident_id)['expires_at'], cooling['expires_at'])
        self.initializer.tick_lifecycle(now=end + timedelta(minutes=30))
        self.assertEqual(self.store.get(incident_id)['status'], 'resolved')

    def test_new_operation_reactivates_cooling_without_reset_by_logout(self):
        op, incident = self.incident()
        op['status'] = 'timeout'
        self.initializer.sync_operations([op], now=self.now)
        fresh = fixtures.operation('op-new')
        self.initializer.sync_operations([fresh], now=self.now + timedelta(minutes=1))
        self.assertEqual(fresh['operation_risk_meter']['incident_id'], incident['incident_id'])
        self.assertNotEqual(self.store.get(incident['incident_id'])['status'], 'cooling')

    def test_canonical_other_actor_terminal_state_is_reloaded(self):
        ops = PlayerOperationStore(self.path)
        alice, bob = fixtures.operation('alice'), fixtures.operation('bob', owner='bob')
        self.initializer.sync_operations([alice, bob], now=self.now)
        bob['status'] = 'cancelled'
        ops.upsert_operations('bob', [bob])
        self.initializer.sync_operations([alice], now=self.now)
        incident = self.store.get(alice['operation_risk_meter']['incident_id'])
        self.assertEqual(incident['operation_ids'], ['alice'])

    def test_incident_and_publication_head_commit_or_rollback_together(self):
        with db_connect(self.path) as conn:
            conn.execute("CREATE TRIGGER fail_publication BEFORE INSERT ON response_incident_publications BEGIN SELECT RAISE(ABORT, 'outbox unavailable'); END")
        with self.assertRaisesRegex(Exception, 'outbox unavailable'):
            self.incident()
        self.assertEqual(self.store.list_active(), [])
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM response_incident_audit').fetchone()[0], 0)

    def test_zero_heat_does_not_end_an_active_operation(self):
        op, incident = self.incident()
        op['operation_risk_meter']['active_contribution'] = 0
        self.initializer.sync_operations([op], now=self.now)
        current = self.store.get(incident['incident_id'])
        self.assertEqual(current['status'], 'active')
        self.assertEqual(current['heat'], 0)
        self.assertEqual(current['operation_ids'], ['op-a'])

    def test_stale_incoming_runtime_cannot_restore_cancelled_operation(self):
        op, incident = self.incident()
        ops = PlayerOperationStore(self.path)
        ops.upsert_operations('neo', [op])
        with db_connect(self.path) as conn:
            op['_runtime_version'] = conn.execute('SELECT version FROM player_operations WHERE operation_id=?', ('op-a',)).fetchone()[0]
        cancelled = copy.deepcopy(op)
        cancelled['status'] = 'cancelled'
        ops.upsert_operations('neo', [cancelled])
        self.initializer.sync_operations([op], now=self.now)
        self.assertEqual(self.store.get(incident['incident_id'])['status'], 'cooling')
        self.assertEqual(op['status'], 'cancelled')

    def test_failed_publisher_recovers_after_restart_and_does_not_duplicate(self):
        _, incident = self.incident()
        relay = IncidentPublicationRelay(self.store)
        failed = relay.drain(Mock(side_effect=RuntimeError('offline')), self.now)
        self.assertEqual(failed['failed'], 1)
        delivered = []
        def publish(head, cursor):
            delivered.append((head['incident_id'], head['version']))
            return '', True
        self.assertEqual(relay.drain(publish, self.now)['delivered'], 0)
        restarted = IncidentPublicationRelay(IncidentStore(self.path))
        self.assertEqual(restarted.drain(publish, self.now + timedelta(seconds=61))['delivered'], 1)
        self.assertEqual(restarted.drain(publish, self.now + timedelta(seconds=62))['delivered'], 0)
        self.assertEqual(delivered, [(incident['incident_id'], incident['version'])])

    def test_new_head_during_paged_delivery_is_replayed_for_all_viewers(self):
        _, incident = self.incident()
        relay = IncidentPublicationRelay(self.store)
        def first_page(head, cursor):
            self.store.upsert({**head, 'heat': 99}, now=self.now)
            return 'viewer64', False
        relay.drain(first_page, self.now)
        relay.drain(lambda head, cursor: ('viewer99', True), self.now)
        seen = []
        relay.drain(lambda head, cursor: (seen.append((head['version'], cursor)) or '', True), self.now)
        self.assertEqual(seen, [(incident['version'] + 1, '')])

    def test_public_map_and_blacknet_agree_at_cooling_expiry(self):
        op, _ = self.incident()
        op['status'] = 'timeout'
        self.initializer.sync_operations([op], now=self.now)
        with patch.object(run, 'incident_store', self.store):
            before = self.now + timedelta(minutes=29)
            after = self.now + timedelta(minutes=30)
            self.assertTrue(self.store.list_public(now=before))
            self.assertTrue(run.build_blacknet_incident_facts(before))
            self.assertEqual(self.store.list_public(now=after), [])
            self.assertEqual(run.build_blacknet_incident_facts(after), [])

    def test_delivery_fans_out_bounded_public_deltas_and_replays_without_duplicates(self):
        _, incident = self.incident()
        with db_connect(self.path) as conn:
            conn.executemany("INSERT INTO user_identity_projection(username,source_profile_revision,source_profile_checksum,projection_version,updated_at) VALUES (?,1,'test',1,'2026-07-14')",
                             [(f'viewer{i:03}',) for i in range(70)])
        bus = GameStateDeltaBus(self.path)
        dispatcher = ResponseDispatcher(NPCCapsuleStore(self.path))
        producer = Mock()
        producer.enqueue_signal.return_value = {'ok': True}
        fixed_now = self.now
        class FixedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls.fromtimestamp(fixed_now.timestamp(), tz=tz)
        with patch.object(run, 'incident_store', self.store), patch.object(run, 'delta_bus', bus), \
             patch.object(run, 'response_dispatcher', dispatcher), \
             patch.object(run, 'BlackNetNarrativeProducer', return_value=producer), \
             patch.object(run, 'get_ghostnetwork_service'), \
             patch.object(run, 'datetime', FixedClock):
            cursor, done = run.deliver_incident_publication(incident, '')
            self.assertFalse(done)
            self.assertEqual(cursor, 'viewer063')
            self.assertEqual(bus.get_changes_since('viewer069', 0)['changes'], [])
            run.deliver_incident_publication(incident, cursor)
            first = bus.get_changes_since('viewer069', 0)['changes']
            self.assertTrue(first)
            run.deliver_incident_publication(incident, cursor)
            self.assertEqual(bus.get_changes_since('viewer069', 0)['changes'], first)
            public = first[0]['payload']
            self.assertNotIn('suspect_refs', public)
            self.assertNotIn('operation_ids', public)
            self.assertEqual({call.kwargs['target_medium'] for call in producer.enqueue_signal.call_args_list}, {'blacknet'})

    def test_late_dispatch_cannot_restore_npc_after_resolution(self):
        _, incident = self.incident()
        dispatcher = ResponseDispatcher(NPCCapsuleStore(self.path))
        dispatcher.dispatch_incident(incident, now=self.now)
        resolved = self.store.upsert({**incident, 'status': 'resolved'}, now=self.now)
        dispatcher.cancel_incident(incident['incident_id'], now=self.now, incident_version=resolved['version'])
        dispatcher.dispatch_incident(incident, now=self.now)
        self.assertEqual(dispatcher.capsule_store.list_by_incident(incident['incident_id']), [])

    def test_blacknet_candidate_uses_existing_publication_pipeline(self):
        fixture = narrative_fixtures.NarrativePublicationTest()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        candidate = fixture.accepted_candidate('incident-blacknet', source_scope='blacknet_world',
            task_variant='blacknet_signal_narration', target_medium='blacknet',
            narrative_intent='intercepted_incident_alert')
        self.assertEqual(candidate['validation_status'], 'accepted')
        result = NarrativePublicationService(fixture.repo).process_once()
        self.assertEqual(result['result'], 'published', result)
        self.assertEqual(len(fixture.repo.list_narrative_medium_records('blacknet', active_only=True)), 1)

    def test_delayed_blacknet_cannot_publish_after_incident_closes(self):
        fixture = narrative_fixtures.NarrativePublicationTest()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        store = IncidentStore(fixture.repo.db_path)
        incident = store.upsert({'incident_id': 'blacknet-incident', 'status': 'active',
            'level': 2, 'heat': 65, 'center': {'lat': 52.1, 'lng': 21.2}})
        fixture.accepted_candidate('delayed-incident-blacknet', source_scope='blacknet_world',
            task_variant='blacknet_signal_narration', target_medium='blacknet',
            narrative_intent='intercepted_incident_alert',
            validation={'incident_context': {'id': incident['incident_id'],
                        'publication_version': incident['publication_version']}})
        store.upsert({**incident, 'status': 'resolved'})
        result = NarrativePublicationService(fixture.repo).process_once()
        self.assertEqual(result['result'], 'rejected', result)
        self.assertEqual(result['reason'], 'lifecycle_state_superseded')
        self.assertEqual(fixture.repo.list_narrative_medium_records('blacknet'), [])

    def test_concurrent_actors_merge_without_losing_contributions(self):
        a, b = fixtures.operation('parallel-a'), fixtures.operation('parallel-b', owner='bob')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.initializer.sync_operations, [op], self.now) for op in (a, b)]
            for future in futures:
                future.result()
        incidents = self.store.list_active()
        self.assertEqual(len(incidents), 1)
        self.assertEqual(set(incidents[0]['operation_ids']), {'parallel-a', 'parallel-b'})

    def test_lifecycle_uses_bounded_queries_not_world_lists_or_profiles(self):
        self.incident()
        with patch.object(self.store, 'list_active', side_effect=AssertionError('world scan')), \
             patch.object(self.store, 'list_public', side_effect=AssertionError('world scan')), \
             patch.object(run.user_store, 'get_profile', side_effect=AssertionError('profile read')), \
             patch.object(run.user_store, 'list_profiles', side_effect=AssertionError('profile scan')):
            self.initializer.sync_operations([fixtures.operation('second')], now=self.now)
            self.initializer.tick_lifecycle(now=self.now + timedelta(hours=3), limit=1)
