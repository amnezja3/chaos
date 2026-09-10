import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork.errors import RepositoryIntegrityError
from ghostnetwork.ollama_worker import active_ollama_worker_policies
from ghostnetwork.repository import GhostNetworkRepository


class NarrativeBacklogRetirementTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 10, 16, 30, tzinfo=timezone.utc)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repository = GhostNetworkRepository(
            db_path=os.path.join(self.tmpdir.name, "backlog.sqlite3"),
            clock=lambda: self.now,
        )
        self.policy = active_ollama_worker_policies()[0]

    def _enqueue(self, event_id):
        scope, variant, medium, prompt, schema, model = self.policy.eligibility_tuple()
        return self.repository.enqueue_narrative_task({
            "event_id": event_id,
            "source_scope": scope,
            "source_event_id": event_id,
            "processor": "ollama",
            "target_medium": medium,
            "audience_scope": "public",
            "truth_class": "canonical",
            "facts": [{"fact_id": f"fact:{event_id}"}],
            "allowed_actions": [],
            "task_variant": variant,
            "prompt_version": prompt,
            "output_schema_version": schema,
            "model_policy_version": model,
        })

    def test_plan_and_apply_preserve_protected_and_new_tasks(self):
        old = self._enqueue("old-event")
        protected = self._enqueue("protected-signal")
        linked = self._enqueue("linked-old-event")
        with self.repository._conn() as conn:
            conn.execute(
                """
                INSERT INTO ghost_narrative_task_sources(
                    outbox_id, source_event_id, linked_at
                ) VALUES (?, ?, ?)
                """,
                (linked["outbox_id"], "protected-signal", self.now.isoformat()),
            )
        cutoff = self.now + timedelta(minutes=1)
        self.now += timedelta(minutes=2)
        fresh = self._enqueue("fresh-event")

        plan = self.repository.plan_historical_narrative_backlog_retirement(
            active_ollama_worker_policies(),
            before=cutoff,
            protected_source_event_ids=["protected-signal"],
        )
        self.assertEqual([task["outbox_id"] for task in plan], [old["outbox_id"]])

        retired = self.repository.retire_historical_narrative_backlog(
            active_ollama_worker_policies(),
            before=cutoff,
            protected_source_event_ids=["protected-signal"],
            expected_count=1,
            now=self.now,
        )
        self.assertEqual(retired[0]["status"], "dead_letter")
        self.assertEqual(
            retired[0]["last_error_code"], "historical_backlog_operator_cutoff"
        )
        self.assertEqual(
            self.repository.get_narrative_outbox(protected["outbox_id"])["status"],
            "ready",
        )
        self.assertEqual(
            self.repository.get_narrative_outbox(linked["outbox_id"])["status"],
            "ready",
        )
        self.assertEqual(
            self.repository.get_narrative_outbox(fresh["outbox_id"])["status"],
            "ready",
        )

    def test_apply_fails_closed_when_expected_count_changes(self):
        self._enqueue("old-event")
        with self.assertRaises(RepositoryIntegrityError):
            self.repository.retire_historical_narrative_backlog(
                active_ollama_worker_policies(),
                before=self.now + timedelta(minutes=1),
                expected_count=2,
                now=self.now,
            )

    def test_generated_candidate_excludes_task_from_retirement(self):
        task = self._enqueue("candidate-event")
        with self.repository._conn() as conn:
            conn.execute(
                """
                INSERT INTO ghost_narrative_inbox_candidates(
                    candidate_id, task_id, attempt_id, source_scope,
                    source_event_id, source_receipt_id, output_schema_version,
                    prompt_version, model_policy_version, model_name, model_digest,
                    ollama_runtime_version, target_medium, audience_scope,
                    audience_clan, audience_owner, truth_class, title, body, tone,
                    fact_refs_json, cta_ref, cta_action, cta_payload_json,
                    bounded_raw_output, output_hash, validation_status,
                    validation_errors_json, quarantine_reason, created_at,
                    validated_at, updated_at
                ) VALUES (?, ?, '', '', '', '', '', '', '', '', '', '', '', '',
                          '', '', '', '', '', '', '[]', '', '', '{}', '', '',
                          'quarantined', '[]', '', ?, ?, ?)
                """,
                ("candidate-test", task["outbox_id"], self.now.isoformat(),
                 self.now.isoformat(), self.now.isoformat()),
            )
        plan = self.repository.plan_historical_narrative_backlog_retirement(
            active_ollama_worker_policies(), before=self.now + timedelta(minutes=1)
        )
        self.assertEqual(plan, [])


if __name__ == "__main__":
    unittest.main()
