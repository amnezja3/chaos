import os
import tempfile
import unittest
from datetime import datetime, timezone

from database import db_connect
from ghostnetwork.repository import GhostNetworkRepository
from scripts.audit_narrative_publication_lifecycle import build_report


class NarrativePublicationLifecycleAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "lifecycle-audit.sqlite3")
        self.now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_and_legacy_history_are_safe(self):
        self.assertTrue(build_report(self.repo, now=self.now)["ok"])
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ghost_narrative_medium_records (
                    medium_record_id, publication_receipt_id, candidate_id, task_id,
                    target_medium, audience_scope, source_scope, truth_class,
                    title, body, fact_refs_json, cta_payload_json, created_at, published_at
                ) VALUES ('legacy', 'receipt', 'candidate', 'task', 'blacknet',
                    'public', 'ghostnetwork', 'canonical', 'title', 'body', '[]',
                    '{}', ?, ?)
                """,
                (self.now.isoformat(), self.now.isoformat()),
            )
        report = build_report(self.repo, now=self.now)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["warnings"], ["historical_legacy_records_present"])

    def test_duplicate_active_heads_fail_closed(self):
        with db_connect(self.db_path) as conn:
            for suffix in ("one", "two"):
                conn.execute(
                    """
                    INSERT INTO ghost_narrative_medium_records (
                        medium_record_id, publication_receipt_id, candidate_id, task_id,
                        target_medium, audience_scope, source_scope, truth_class,
                        title, body, fact_refs_json, cta_payload_json,
                        narrative_thread_id, event_family, significance, active_state,
                        valid_from, valid_until, semantic_contract_version,
                        lifecycle_contract_version, created_at, published_at
                    ) VALUES (?, ?, ?, ?, 'blacknet', 'public', 'ghostnetwork',
                        'canonical', 'title', 'body', '[]', '{}', 'ghost-part:one',
                        'part_activated', 'high', 'active', ?, ?,
                        'chaos-llm-semantic-input-v1',
                        'ghostnetwork-publication-lifecycle-v1', ?, ?)
                    """,
                    (
                        f"medium-{suffix}", f"receipt-{suffix}",
                        f"candidate-{suffix}", f"task-{suffix}",
                        self.now.isoformat(), "2026-09-05T12:00:00+00:00",
                        self.now.isoformat(), self.now.isoformat(),
                    ),
                )
        report = build_report(self.repo, now=self.now)
        self.assertFalse(report["ok"])
        self.assertIn("duplicate_active_thread_heads", report["errors"])


if __name__ == "__main__":
    unittest.main()
