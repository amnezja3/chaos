import os
import tempfile
import unittest
from datetime import datetime, timezone

from database import db_connect
from ghostnetwork.ollama_worker import active_ollama_worker_policies
from ghostnetwork.repository import GhostNetworkRepository
from scripts.audit_narrative_runtime import build_report


class NarrativeRuntimeAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "runtime.sqlite3")
        self.now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        self.policy = active_ollama_worker_policies()[0]

    def tearDown(self):
        self.tmp.cleanup()

    def task(self, event_id):
        source, variant, medium, prompt, schema, model = self.policy.eligibility_tuple()
        return {
            "event_id": event_id,
            "source_scope": source,
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
        }

    def test_healthy_ready_and_scheduled_retry_queue_passes(self):
        self.repo.enqueue_narrative_task(self.task("ready"))
        retry_task = self.task("retry")
        retry_task["priority"] = 100
        retried = self.repo.enqueue_narrative_task(retry_task)
        claim = self.repo.claim_next_narrative_task(
            "runtime-audit", eligible_policies=(self.policy,), now=self.now,
        )
        self.assertEqual(claim["outbox_id"], retried["outbox_id"])
        self.repo.retry_narrative_task(
            claim["outbox_id"], "runtime-audit", claim["lease_until"],
            "ollama_timeout", now=self.now,
        )

        report = build_report(self.repo, now=self.now)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["health"]["retry_schedule_violations"], 0)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["profiles_loaded"])

    def test_invalid_retry_schedule_fails_closed(self):
        item = self.repo.enqueue_narrative_task(self.task("bad-retry"))
        claim = self.repo.claim_next_narrative_task(
            "runtime-audit", eligible_policies=(self.policy,), now=self.now,
        )
        self.repo.retry_narrative_task(
            claim["outbox_id"], "runtime-audit", claim["lease_until"],
            "ollama_timeout", now=self.now,
        )
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE ghost_narrative_outbox SET next_attempt_at = ? WHERE outbox_id = ?",
                ("2026-09-03T12:10:00+00:00", item["outbox_id"]),
            )

        report = build_report(self.repo, now=self.now)

        self.assertFalse(report["ok"])
        self.assertIn("retry_schedule_violation", report["errors"])

    def test_active_task_without_lease_and_exhausted_ready_are_reported(self):
        active = self.repo.enqueue_narrative_task(self.task("active-invalid"))
        exhausted = self.repo.enqueue_narrative_task(self.task("exhausted-invalid"))
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE ghost_narrative_outbox SET status = 'processing' WHERE outbox_id = ?",
                (active["outbox_id"],),
            )
            conn.execute(
                "UPDATE ghost_narrative_outbox SET attempt_count = max_attempts WHERE outbox_id = ?",
                (exhausted["outbox_id"],),
            )

        report = build_report(self.repo, now=self.now)

        self.assertFalse(report["ok"])
        self.assertIn("active_tasks_without_lease", report["errors"])
        self.assertIn("exhausted_tasks_not_dead_lettered", report["errors"])


if __name__ == "__main__":
    unittest.main()
