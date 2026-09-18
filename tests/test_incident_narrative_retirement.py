import unittest
import json
import test_narrative_publications as fixtures
from ghostnetwork.publication import NarrativePublicationService
from response_network.incident_store import IncidentStore
from response_network.incident_navigation import safe_incident_entry_point
from ghostnetwork.producers import BlackNetNarrativeProducer


class IncidentNarrativeRetirementTest(unittest.TestCase):
    def test_published_incident_outlives_task_deadline_but_not_source(self):
        incident = self.store.upsert({'incident_id': 'long-running', 'status': 'escalated',
            'level': 4, 'center': {'lat': 52, 'lng': 21}}, now=self.fixture.clock())
        candidate = self.candidate('long-running-report', {'incident_context': {
            'id': incident['incident_id'], 'publication_version': incident['publication_version'],
            'narrative_version': incident['narrative_version']}})
        self.assertEqual(NarrativePublicationService(self.repo).process_once()['result'], 'published')
        self.fixture.clock.advance(1801)
        self.repo.maintain_narrative_freshness()
        self.repo.retire_stale_incident_narratives()
        self.assertEqual(self.repo.get_narrative_outbox(candidate['task_id'])['status'], 'completed')
        self.assertEqual(len(self.repo.list_narrative_medium_records('blacknet', active_only=True)), 1)
        self.store.upsert({**incident, 'status': 'resolved'}, now=self.fixture.clock())
        self.repo.retire_stale_incident_narratives()
        self.assertEqual(self.repo.list_narrative_medium_records('blacknet', active_only=True), [])

    def test_map_drift_during_generation_preserves_news_and_blacknet(self):
        for medium in ('googleplex_news', 'blacknet'):
            with self.subTest(medium=medium):
                incident = self.store.upsert({'incident_id': 'drift-' + medium,
                    'status': 'escalated', 'level': 4, 'search_radius_m': 200,
                    'center': {'lat': 52, 'lng': 21},
                    'operation_refs': [{'position': {'lat': 52, 'lng': 21}},
                                       {'position': {'lat': 52.001, 'lng': 21}}]},
                    now=self.fixture.clock())
                store, clock = self.store, self.fixture.clock
                class DriftingClient(fixtures.AcceptedClient):
                    def generate(self, package, policy):
                        store.upsert({**incident, 'center': {'lat': 52.0005, 'lng': 21}}, now=clock())
                        return super().generate(package, policy)
                candidate = self.fixture.accepted_candidate('drift-task-' + medium,
                    source_scope='blacknet_world', target_medium=medium,
                    task_variant='googleplex_world_dispatch' if medium == 'googleplex_news' else 'blacknet_signal_narration',
                    narrative_intent='intercepted_incident_alert', client=DriftingClient(),
                    validation={'incident_context': {'id': incident['incident_id'],
                        'publication_version': incident['publication_version'],
                        'narrative_version': incident['narrative_version']}})
                self.assertTrue(self.repo.narrative_task_is_current(candidate['task_id']))
                with self.repo._conn() as conn:
                    conn.execute("UPDATE ghost_narrative_inbox_candidates SET cta_action='focus_map_target', cta_payload_json=? WHERE candidate_id=?",
                        (json.dumps({'target_id': incident['incident_id'], 'lat': 0, 'lng': 0}), candidate['candidate_id']))
                self.assertEqual(self.repo.retire_stale_incident_narratives(), 0)
                self.assertEqual(NarrativePublicationService(self.repo).process_once()['result'], 'published')
                published = self.repo.list_narrative_medium_records(medium, active_only=True)[0]
                expected = safe_incident_entry_point({**incident, 'center': {'lat': 52.0005, 'lng': 21}})
                self.assertEqual(published['cta_payload']['lat'], expected['lat'])
                self.assertEqual(published['cta_payload']['lng'], expected['lng'])
                self.repo.invalidate_incident_publications(incident['incident_id'], incident['publication_version'] + 1)
                self.assertEqual(len(self.repo.list_narrative_medium_records(medium, active_only=True)), 1)
                store.upsert({**incident, 'level': 3}, now=clock())
                self.assertFalse(self.repo.narrative_task_is_current(candidate['task_id']))
                self.assertEqual(self.repo.retire_stale_incident_narratives(), 1)
                self.assertEqual(self.repo.list_narrative_medium_records(medium, active_only=True), [])

    def test_map_drift_does_not_enqueue_replacement_task(self):
        producer = BlackNetNarrativeProducer(self.repo)
        signal = {'id': 'drift-signal', 'fact_id': 'bnf:incidents:incident_hotspot_reaction:drift',
            'signal_type': 'incident_hotspot', 'category': 'incident',
            'title': 'INCYDENT / L4', 'label': 'POZIOM REAKCJI', 'value': 'L4',
            'stat': 'ACTIVE / ESCALATING', 'importance': 75,
            'cta_action': 'focus_map_target', 'cta_target_id': 'drift-source',
            'metadata': {'lat': 52, 'lng': 21, 'incident_id': 'drift-source',
                'incident_publication_version': 1, 'incident_narrative_version': 1}}
        for medium in ('blacknet', 'googleplex_news'):
            first = producer.enqueue_signal({}, signal, target_medium=medium)
            moved = {**signal, 'metadata': {**signal['metadata'], 'lat': 52.0001,
                'incident_publication_version': 2}}
            replay = producer.enqueue_signal({}, moved, target_medium=medium)
            self.assertEqual(first['status'], 'created')
            self.assertEqual(replay['status'], 'deduplicated')
            self.assertEqual(first['task']['outbox_id'], replay['task']['outbox_id'])

    def test_reportable_changes_increment_narrative_version(self):
        base = {'incident_id': 'semantic', 'status': 'active', 'level': 2,
            'center': {'lat': 52, 'lng': 21}, 'search_radius_m': 200,
            'operation_refs': [{'position': {'lat': 52, 'lng': 21}}]}
        for change in ({'status': 'cooling'}, {'level': 3}, {'search_radius_m': 240},
                       {'operation_refs': [{'position': {'lat': 53, 'lng': 21}}]}):
            original = self.store.upsert(base, now=self.fixture.clock())
            changed = self.store.upsert({**original, **change}, now=self.fixture.clock())
            self.assertGreater(changed['narrative_version'], original['narrative_version'])

    def test_existing_source_without_narrative_version_remains_publishable(self):
        incident = self.store.upsert({'incident_id': 'pre-deploy', 'status': 'active',
            'level': 2, 'center': {'lat': 52, 'lng': 21}}, now=self.fixture.clock())
        with self.repo._conn() as conn:
            conn.execute("UPDATE response_incidents SET incident_json=json_remove(incident_json,'$.narrative_version') WHERE incident_id=?",
                (incident['incident_id'],))
        candidate = self.candidate('post-deploy-task', {'incident_context': {
            'id': incident['incident_id'], 'publication_version': incident['publication_version'],
            'narrative_version': incident['publication_version']}})
        self.assertEqual(self.repo.retire_stale_incident_narratives(), 0)
        self.assertEqual(NarrativePublicationService(self.repo).process_once()['result'], 'published')
        self.repo.invalidate_incident_publications(incident['incident_id'], incident['publication_version'])
        self.assertEqual(len(self.repo.list_narrative_medium_records('blacknet', active_only=True)), 1)

    def setUp(self):
        self.fixture = fixtures.NarrativePublicationTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.repo = self.fixture.repo
        self.store = IncidentStore(self.repo.db_path)

    def candidate(self, name, validation=None):
        legacy = validation is None
        if legacy:
            incident = self.store.upsert({'incident_id': name, 'status': 'active', 'level': 2, 'center': {'lat': 52, 'lng': 21}})
            validation = {'incident_context': {'id': name, 'publication_version': incident['publication_version']}}
        result = self.fixture.accepted_candidate(name, source_scope='blacknet_world',
            task_variant='blacknet_signal_narration', target_medium='blacknet',
            narrative_intent='intercepted_incident_alert', validation=validation)
        if legacy:
            with self.repo._conn() as conn:
                conn.execute("UPDATE ghost_narrative_outbox SET validation_json='{}' WHERE outbox_id=?", (result['task_id'],))
        return result

    def test_legacy_incident_without_canonical_context_cannot_publish(self):
        self.candidate('legacy-before-context')
        result = NarrativePublicationService(self.repo).process_once()
        self.assertEqual(result['result'], 'rejected')
        self.assertEqual(self.repo.list_narrative_medium_records('blacknet'), [])

    def test_retirement_unblocks_googleplex_slot_without_deleting_history(self):
        candidate = self.candidate('legacy-slot')
        with self.repo._conn() as conn:
            conn.execute("UPDATE ghost_narrative_outbox SET target_medium='googleplex_news', presentation_slot='gp-home-world-grid' WHERE outbox_id=?", (candidate['task_id'],))
        self.assertFalse(self.repo.has_open_narrative_slot_assignment('googleplex_news', 'gp-home-world-grid'))
        task = self.repo.get_narrative_outbox(candidate['task_id'])
        self.assertEqual(task['status'], 'dead_letter')
        self.assertIsNotNone(self.repo.get_narrative_candidate(candidate['candidate_id']))

    def test_expired_source_hides_published_record_but_live_source_survives(self):
        incident = self.store.upsert({'incident_id': 'live', 'status': 'active',
            'level': 2, 'center': {'lat': 52, 'lng': 21}}, now=self.fixture.clock())
        candidate = self.candidate('current', {'incident_context': {
            'id': 'live', 'publication_version': incident['publication_version']}})
        self.assertEqual(self.repo.retire_stale_incident_narratives(), 0)
        self.assertEqual(NarrativePublicationService(self.repo).process_once()['result'], 'published')
        self.store.upsert({**incident, 'status': 'resolved'}, now=self.fixture.clock())
        self.assertEqual(self.repo.retire_stale_incident_narratives(), 1)
        self.assertEqual(self.repo.list_narrative_medium_records('blacknet', active_only=True), [])
        self.assertEqual(len(self.repo.list_narrative_medium_records('blacknet')), 1)
        self.assertEqual(self.repo.retire_stale_incident_narratives(), 0)
