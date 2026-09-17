import unittest
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch
from datetime import timedelta
import test_ghostnetwork_narrative_task_queue as fixtures
import test_narrative_publications as publication_fixtures
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.publication import NarrativePublicationService
from ghostnetwork.task_freshness import instant


class NarrativeFreshnessTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GhostNarrativeTaskQueueTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.repo = self.fixture.repo
        self.clock = self.fixture.clock

    def task(self, name, **kwargs):
        return self.repo.enqueue_narrative_task(self.fixture.task(name, **kwargs))

    def test_expired_high_priority_task_is_not_claimed(self):
        stale = self.task('old', priority=99, created_at=(self.clock() - timedelta(days=7)).isoformat())
        fresh = self.task('new', priority=1)
        self.assertEqual(self.repo.claim_next_narrative_task('worker')['outbox_id'], fresh['outbox_id'])
        self.assertEqual(self.repo.get_narrative_outbox(stale['outbox_id'])['last_error_code'], 'task_expired')

    def test_urgent_task_precedes_normal_and_editorial(self):
        self.task('promo', source_scope='googleplex_editorial', priority=999)
        self.task('normal', priority=99)
        urgent = self.task('urgent', narrative_intent='ghost_conflict_escalation', priority=1)
        self.assertEqual(self.repo.claim_next_narrative_task('worker')['outbox_id'], urgent['outbox_id'])

    def test_replay_and_retry_do_not_extend_expiry(self):
        task = self.task('one')
        self.clock.advance(60)
        self.assertEqual(self.task('one')['expires_at'], task['expires_at'])
        claimed = self.repo.claim_next_narrative_task('worker')
        self.repo.retry_narrative_task(claimed['outbox_id'], 'worker', claimed['lease_until'], 'model_timeout')
        self.assertEqual(self.repo.get_narrative_outbox(task['outbox_id'])['expires_at'], task['expires_at'])

    def test_legacy_expiry_is_based_on_original_creation(self):
        task = self.task('legacy', created_at=(self.clock() - timedelta(days=7)).isoformat())
        with self.repo._conn() as conn:
            conn.execute("UPDATE ghost_narrative_outbox SET expires_at='' WHERE outbox_id=?", (task['outbox_id'],))
        self.repo.maintain_narrative_freshness()
        self.assertEqual(self.repo.get_narrative_outbox(task['outbox_id'])['status'], 'dead_letter')

    def test_source_deadline_is_not_extended_to_queue_ttl(self):
        end = self.clock() + timedelta(minutes=3)
        task = self.task('short', validation={'source_expires_at': end.isoformat()})
        self.assertEqual(instant(task['expires_at']), end)
        self.clock.advance(181)
        self.assertFalse(self.repo.narrative_task_is_current(task['outbox_id']))

    def test_newest_source_replaces_waiting_versions(self):
        old = self.task('v1', source_scope='blacknet_world', selected_source_ref='same')
        new = self.task('v2', source_scope='blacknet_world', selected_source_ref='same')
        self.assertEqual(self.repo.get_narrative_outbox(old['outbox_id'])['status'], 'dead_letter')
        self.assertEqual(self.repo.claim_next_narrative_task('worker')['outbox_id'], new['outbox_id'])

    def test_new_version_invalidates_inflight_generation(self):
        old = self.task('inflight', source_scope='blacknet_world', selected_source_ref='same')
        claimed = self.repo.claim_next_narrative_task('worker')
        self.task('new-head', source_scope='blacknet_world', selected_source_ref='same')
        self.assertFalse(self.repo.narrative_task_is_current(old['outbox_id']))
        self.assertIsNone(self.repo.complete_narrative_task(old['outbox_id'], 'worker', claimed['lease_until']))

    def worker_task(self, name, **kwargs):
        task = self.fixture.task(name, source_scope='blacknet_world',
            task_variant='blacknet_signal_narration', narrative_intent='intercepted_world_signal', **kwargs)
        return self.repo.enqueue_narrative_task(assign_ollama_task_policy(task))

    def test_expiration_during_model_call_discards_result(self):
        task = self.worker_task('slow', expires_at=(self.clock() + timedelta(seconds=2)).isoformat())
        clock = self.clock
        class SlowClient(publication_fixtures.AcceptedClient):
            def generate(self, package, policy):
                clock.advance(3)
                return super().generate(package, policy)
        worker = OllamaNarrativeWorker(repository=self.repo, client=SlowClient(),
            config=OllamaWorkerConfig(enabled=True), worker_id='slow-worker')
        self.assertEqual(worker.process_once()['result'], 'expired')
        self.assertIsNone(self.repo.get_narrative_candidate_for_task(task['outbox_id']))

    def test_expiration_between_generation_and_publication_is_rejected(self):
        task = self.worker_task('late-publication', expires_at=(self.clock() + timedelta(seconds=2)).isoformat())
        worker = OllamaNarrativeWorker(repository=self.repo, client=publication_fixtures.AcceptedClient(),
            config=OllamaWorkerConfig(enabled=True), worker_id='fast-worker')
        self.assertEqual(worker.process_once()['result'], 'completed')
        self.clock.advance(3)
        NarrativePublicationService(self.repo).process_once()
        self.assertEqual(self.repo.list_narrative_medium_records('blacknet'), [])

    def test_closed_conflict_cannot_reach_model(self):
        with self.repo._conn() as conn:
            conn.execute('CREATE TABLE territory_conflicts(conflict_key TEXT PRIMARY KEY,status TEXT,conflict_version INTEGER)')
            conn.execute("INSERT INTO territory_conflicts VALUES ('Abacus','resolved',2)")
        task = self.task('abacus', source_scope='blacknet_world', narrative_intent='intercepted_conflict_warning',
            validation={'conflict_context': [{'key': 'Abacus', 'version': 1}]})
        self.assertIsNone(self.repo.claim_next_narrative_task('worker'))
        self.assertEqual(self.repo.get_narrative_outbox(task['outbox_id'])['status'], 'dead_letter')

    def test_readonly_audit_reports_queue_without_claiming_tasks(self):
        from tools.audit_narrative_freshness import main
        task = self.task('audit')
        output = io.StringIO()
        with patch('sys.argv', ['audit', '--db', self.fixture.db_path]), redirect_stdout(output):
            main()
        report = json.loads(output.getvalue())
        self.assertTrue(report['read_only'])
        self.assertTrue(report['expiry_schema'])
        self.assertEqual(report['next_tasks'][0]['outbox_id'], task['outbox_id'])
        self.assertEqual(self.repo.get_narrative_outbox(task['outbox_id'])['status'], 'ready')
