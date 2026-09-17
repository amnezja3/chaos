import unittest
import json
import test_narrative_publications as fixtures
from ghostnetwork.publication import NarrativePublicationService
from response_network.incident_store import IncidentStore


class IncidentNarrativeRetirementTest(unittest.TestCase):
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
