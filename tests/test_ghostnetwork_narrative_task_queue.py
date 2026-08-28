import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from database import db_connect
from ghostnetwork import GhostNetworkRepository


class MutableClock:
    def __init__(self, value=None):
        self.value = value or datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class GhostNarrativeTaskQueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.clock = MutableClock()
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def task(self, event_id="event-1", medium="blacknet", audience_scope="public", **overrides):
        task = {
            "event_id": event_id,
            "source_scope": "ghostnetwork",
            "source_event_id": event_id,
            "processor": "ollama",
            "target_medium": medium,
            "audience_scope": audience_scope,
            "audience_clan": "",
            "audience_owner": "",
            "truth_class": "canonical",
            "facts": [{"fact_id": f"fact:{event_id}", "fact_type": "test"}],
            "allowed_actions": [],
            "canon_version": "test-canon-v1",
            "prompt_version": "unassigned",
            "output_schema_version": "unassigned",
            "model_policy_version": "unassigned",
            "task_variant": "test",
            "status": "ready",
        }
        task.update(overrides)
        return task

    def test_semantic_dedupe_is_one_task_per_event_audience_medium(self):
        first = self.repo.enqueue_narrative_task(self.task())
        second = self.repo.enqueue_narrative_task(self.task())
        version_changed = self.repo.enqueue_narrative_task(
            self.task(prompt_version="prompt-v2", output_schema_version="schema-v2")
        )
        clan = self.repo.enqueue_narrative_task(
            self.task(audience_scope="clan", audience_clan="virex")
        )
        cyberner = self.repo.enqueue_narrative_task(self.task(medium="cyberner"))

        self.assertEqual(first["outbox_id"], second["outbox_id"])
        self.assertEqual(first["outbox_id"], version_changed["outbox_id"])
        self.assertTrue(second["idempotent"])
        self.assertNotEqual(first["outbox_id"], clan["outbox_id"])
        self.assertNotEqual(first["outbox_id"], cyberner["outbox_id"])
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=20)), 3)
        self.assertEqual(
            len(self.repo.list_narrative_outbox(source_event_id="event-1", limit=20)),
            3,
        )

        receipt = self.repo.enqueue_narrative_task(
            self.task(
                event_id="",
                source_event_id="",
                source_receipt_id="receipt-1",
            )
        )
        by_receipt = self.repo.list_narrative_outbox(
            source_receipt_id="receipt-1",
            limit=20,
        )
        self.assertEqual([item["outbox_id"] for item in by_receipt], [receipt["outbox_id"]])

    def test_enqueue_rejects_noncanonical_identity_and_active_status(self):
        with self.assertRaises(ValueError):
            self.repo.enqueue_narrative_task(self.task(dedupe_key="caller-controlled"))
        with self.assertRaises(ValueError):
            self.repo.enqueue_narrative_task(self.task(outbox_id="caller-controlled"))
        with self.assertRaises(ValueError):
            self.repo.enqueue_narrative_task(self.task(status="claimed"))
        with self.assertRaises(ValueError):
            self.repo.enqueue_narrative_task(self.task(status="completed"))
        with self.assertRaises(ValueError):
            self.repo.enqueue_narrative_task(self.task(processor="filesystem"))
        ready = self.repo.enqueue_narrative_task(
            self.task(
                event_id="event-no-spoofed-lease",
                claimed_by="caller",
                claimed_at=self.repo.now(),
                lease_until=self.repo.now(),
                attempt_count=4,
            )
        )
        self.assertEqual(ready["claimed_by"], "")
        self.assertEqual(ready["lease_until"], "")
        self.assertEqual(ready["attempt_count"], 0)

    def test_concurrent_enqueue_creates_one_record(self):
        repositories = [
            GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
            for _ in range(8)
        ]

        def enqueue(repo):
            return repo.enqueue_narrative_task(self.task(event_id="event-concurrent"))

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(enqueue, repositories))

        self.assertEqual(len({item["outbox_id"] for item in results}), 1)
        rows = self.repo.list_narrative_outbox(limit=20)
        self.assertEqual(len(rows), 1)

    def test_two_workers_get_exactly_one_active_lease(self):
        self.repo.enqueue_narrative_task(self.task(event_id="event-claim"))
        worker_a = GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
        worker_b = GhostNetworkRepository(db_path=self.db_path, clock=self.clock)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda pair: pair[0].claim_next_narrative_task(pair[1], lease_seconds=30),
                ((worker_a, "worker-a"), (worker_b, "worker-b")),
            ))

        claimed = [item for item in results if item]
        self.assertEqual(len(claimed), 1)
        task = self.repo.get_narrative_outbox(claimed[0]["outbox_id"])
        self.assertEqual(task["status"], "claimed")
        self.assertIn(task["claimed_by"], {"worker-a", "worker-b"})
        self.assertEqual(task["attempt_count"], 1)

    def test_crash_expiry_reuses_task_and_rejects_stale_owner(self):
        original = self.repo.enqueue_narrative_task(self.task(event_id="event-crash"))
        claim_a = self.repo.claim_next_narrative_task("worker-a", lease_seconds=10)
        self.assertEqual(claim_a["outbox_id"], original["outbox_id"])
        old_lease = claim_a["lease_until"]

        self.clock.advance(11)
        claim_b = self.repo.claim_next_narrative_task("worker-b", lease_seconds=20)
        self.assertEqual(claim_b["outbox_id"], original["outbox_id"])
        self.assertEqual(claim_b["attempt_count"], 2)
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=20)), 1)

        stale_complete = self.repo.complete_narrative_task(
            original["outbox_id"], "worker-a", old_lease
        )
        self.assertIsNone(stale_complete)

        processing = self.repo.mark_narrative_task_processing(
            original["outbox_id"], "worker-b", claim_b["lease_until"]
        )
        self.assertEqual(processing["status"], "processing")
        completed = self.repo.complete_narrative_task(
            original["outbox_id"], "worker-b", claim_b["lease_until"]
        )
        self.assertEqual(completed["status"], "completed")
        self.assertIsNone(
            self.repo.complete_narrative_task(
                original["outbox_id"], "worker-b", claim_b["lease_until"]
            )
        )
        self.assertIsNone(self.repo.claim_next_narrative_task("worker-c"))

    def test_renew_is_cas_safe_and_non_owner_cannot_change_active_task(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="event-renew"))
        claim = self.repo.claim_next_narrative_task("worker-a", lease_seconds=30)

        self.assertIsNone(
            self.repo.renew_narrative_task_lease(
                item["outbox_id"], "worker-b", claim["lease_until"], lease_seconds=30
            )
        )
        renewed = self.repo.renew_narrative_task_lease(
            item["outbox_id"], "worker-a", claim["lease_until"], lease_seconds=30
        )
        self.assertGreater(renewed["lease_until"], claim["lease_until"])
        with self.assertRaises(ValueError):
            self.repo.update_narrative_outbox_status(item["outbox_id"], "completed")

    def test_retry_reaches_dead_letter_without_new_task(self):
        item = self.repo.enqueue_narrative_task(
            self.task(event_id="event-dead", max_attempts=2)
        )
        first = self.repo.claim_next_narrative_task("worker-a", lease_seconds=30)
        retried = self.repo.retry_narrative_task(
            item["outbox_id"], "worker-a", first["lease_until"], "temporary", backoff_seconds=0
        )
        self.assertEqual(retried["status"], "retry_wait")

        second = self.repo.claim_next_narrative_task("worker-b", lease_seconds=30)
        dead = self.repo.retry_narrative_task(
            item["outbox_id"], "worker-b", second["lease_until"], "still_broken", backoff_seconds=0
        )
        self.assertEqual(dead["status"], "dead_letter")
        self.assertEqual(dead["attempt_count"], 2)
        self.assertIsNone(self.repo.claim_next_narrative_task("worker-c"))
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=20)), 1)

    def test_parallel_recovery_is_single_and_exhausted_lease_dead_letters(self):
        item = self.repo.enqueue_narrative_task(
            self.task(event_id="event-recovery", max_attempts=2)
        )
        first = self.repo.claim_next_narrative_task("worker-a", lease_seconds=10)
        self.clock.advance(11)
        repositories = [
            GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
            for _ in range(2)
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            recovered = list(executor.map(
                lambda repo: repo.recover_expired_narrative_leases(limit=10),
                repositories,
            ))
        self.assertEqual(sum(len(batch) for batch in recovered), 1)
        ready = self.repo.get_narrative_outbox(item["outbox_id"])
        self.assertEqual(ready["status"], "ready")
        second = self.repo.claim_next_narrative_task("worker-b", lease_seconds=10)
        self.assertEqual(second["attempt_count"], 2)
        self.clock.advance(11)
        dead = self.repo.recover_expired_narrative_leases(limit=10)
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0]["status"], "dead_letter")
        self.assertEqual(dead[0]["last_error_code"], "lease_expired")
        self.assertIsNone(
            self.repo.complete_narrative_task(
                item["outbox_id"], "worker-a", first["lease_until"]
            )
        )

    def test_claim_respects_priority(self):
        low = self.repo.enqueue_narrative_task(
            self.task(event_id="event-priority-low", priority=1)
        )
        high = self.repo.enqueue_narrative_task(
            self.task(event_id="event-priority-high", priority=50)
        )
        claimed = self.repo.claim_next_narrative_task("worker-priority", lease_seconds=30)
        self.assertEqual(claimed["outbox_id"], high["outbox_id"])
        self.assertNotEqual(claimed["outbox_id"], low["outbox_id"])

    def test_bounded_list_cursor_continues_after_last_task(self):
        for index in range(5):
            self.repo.enqueue_narrative_task(self.task(event_id=f"event-page-{index}"))
            self.clock.advance(1)
        first = self.repo.list_narrative_outbox(limit=2)
        second = self.repo.list_narrative_outbox(limit=2, cursor=first[-1]["outbox_id"])
        third = self.repo.list_narrative_outbox(limit=2, cursor=second[-1]["outbox_id"])
        ids = [item["outbox_id"] for item in first + second + third]
        self.assertEqual(len(ids), 5)
        self.assertEqual(len(set(ids)), 5)

    def test_schema_migrates_sprint_129_rows_and_retires_pseudo_medium(self):
        legacy_path = os.path.join(self.tmp.name, "legacy.sqlite3")
        conn = sqlite3.connect(legacy_path)
        conn.execute(
            """
            CREATE TABLE ghost_narrative_outbox (
                outbox_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                audience_scope TEXT NOT NULL,
                audience_clan TEXT NOT NULL DEFAULT '',
                medium TEXT NOT NULL,
                truth_class TEXT NOT NULL,
                facts_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                processed_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        created = self.clock().isoformat()
        conn.executemany(
            """
            INSERT INTO ghost_narrative_outbox (
                outbox_id, event_id, audience_scope, audience_clan, medium,
                truth_class, facts_json, status, created_at, processed_at
            ) VALUES (?, ?, 'public', '', ?, 'canonical', '{}', ?, ?, '')
            """,
            (
                ("legacy-blacknet", "event-old-a", "blacknet", "failed", created),
                ("legacy-file", "event-old-b", "ollama_outbox", "ready", created),
            ),
        )
        conn.commit()
        conn.close()

        migrated = GhostNetworkRepository(db_path=legacy_path, clock=self.clock)
        blacknet = migrated.get_narrative_outbox("legacy-blacknet")
        diagnostic = migrated.get_narrative_outbox("legacy-file")

        self.assertEqual(blacknet["status"], "retry_wait")
        self.assertEqual(blacknet["facts"], [])
        self.assertEqual(blacknet["source_event_id"], "event-old-a")
        self.assertEqual(blacknet["target_medium"], "blacknet")
        self.assertEqual(blacknet["processor"], "ollama")
        self.assertEqual(diagnostic["target_medium"], "blacknet")
        self.assertEqual(diagnostic["status"], "completed")
        self.assertEqual(diagnostic["last_error_code"], "legacy_diagnostic_medium_retired")
        same = migrated.enqueue_narrative_task(
            self.task(event_id="event-old-a", medium="blacknet")
        )
        self.assertEqual(same["outbox_id"], "legacy-blacknet")
        self.assertTrue(same["idempotent"])

    def test_ready_query_uses_index_with_thousands_of_terminal_tasks(self):
        with self.repo.transaction():
            for index in range(2000):
                self.repo.enqueue_narrative_task(
                    self.task(event_id=f"event-terminal-{index}")
                )
            self.repo._transaction_conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'completed', completed_at = ?, processed_at = ?,
                    updated_at = ?, next_attempt_at = ''
                WHERE event_id LIKE 'event-terminal-%'
                """,
                (self.repo.now(), self.repo.now(), self.repo.now()),
            )
            ready = self.repo.enqueue_narrative_task(
                self.task(event_id="event-ready", priority=50)
            )

        with db_connect(self.db_path) as conn:
            plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT * FROM ghost_narrative_outbox
                WHERE processor = ?
                  AND status IN ('ready', 'retry_wait')
                  AND attempt_count < max_attempts
                  AND (next_attempt_at = '' OR next_attempt_at <= ?)
                ORDER BY priority DESC, next_attempt_at ASC, created_at ASC, outbox_id ASC
                LIMIT 1
                """,
                ("ollama", self.repo.now()),
            ).fetchall()
        details = " ".join(str(row["detail"]) for row in plan)
        self.assertIn("idx_ghost_narrative_task_ready", details)

        with db_connect(self.db_path) as conn:
            recovery_plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT outbox_id FROM ghost_narrative_outbox
                WHERE status IN ('claimed', 'processing')
                  AND lease_until != '' AND lease_until <= ?
                ORDER BY lease_until ASC, outbox_id ASC
                LIMIT 100
                """,
                (self.repo.now(),),
            ).fetchall()
            dedupe_plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT * FROM ghost_narrative_outbox
                WHERE dedupe_key = ? AND dedupe_key IS NOT NULL AND dedupe_key != ''
                LIMIT 1
                """,
                (ready["dedupe_key"],),
            ).fetchall()
        self.assertIn(
            "idx_ghost_narrative_task_lease",
            " ".join(str(row["detail"]) for row in recovery_plan),
        )
        self.assertIn(
            "idx_ghost_narrative_outbox_dedupe",
            " ".join(str(row["detail"]) for row in dedupe_plan),
        )

        claimed = self.repo.claim_next_narrative_task("worker-load", lease_seconds=30)
        self.assertEqual(claimed["outbox_id"], ready["outbox_id"])
        self.assertEqual(len(self.repo.list_narrative_outbox(status="completed", limit=3000)), 1000)


if __name__ == "__main__":
    unittest.main()
