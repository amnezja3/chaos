import json
import os
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import db_connect
from ghostnetwork.ollama_client import OllamaClientError, OllamaGenerationResult
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    registered_ollama_policies,
)
from ghostnetwork.ollama_worker import (
    OLLAMA_RUNTIME_CONTRACT_VERSION,
    OllamaNarrativeWorker,
    OllamaWorkerConfig,
    is_database_contention,
    verify_ollama_runtime_policy,
)
from ghostnetwork.cycles import GhostCycleService
from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.llm.registry import (
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
)
from ghostnetwork.repository import (
    GhostNetworkRepository,
    narrative_task_retry_backoff_seconds,
)


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class FakeClient:
    def __init__(self, contents=None, error=None):
        self.contents = list(contents or [])
        self.error = error
        self.calls = 0
        self.verify_result = {"ok": True, "errors": []}

    def verify(self):
        return self.verify_result

    def generate(self, _package, policy):
        self.calls += 1
        if self.error:
            raise self.error
        content = self.contents.pop(0)
        return OllamaGenerationResult(
            model=policy.model_name,
            model_digest=policy.model_digest,
            runtime_version="0.15.4",
            content=content,
            done=True,
            done_reason="stop",
            total_duration_ns=10,
            load_duration_ns=1,
            prompt_eval_count=20,
            eval_count=10,
            raw_response_hash="response-hash",
        )


class OllamaWorkerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "worker.sqlite3")
        self.clock = MutableClock()
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
        self.config = OllamaWorkerConfig(
            enabled=True,
            poll_seconds=0.1,
            poll_jitter_seconds=0,
            lease_seconds=60,
            heartbeat_seconds=30,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def task(self, event_id="event-1", **overrides):
        fact = attach_semantic_content(
            {"fact_id": f"fact:{event_id}", "fact_type": "test"},
            {"statement": "Czesc GhostNetwork zostala aktywowana."},
        )
        task = assign_ollama_task_policy({
            "event_id": event_id,
            "source_scope": "ghostnetwork",
            "source_event_id": event_id,
            "processor": "ollama",
            "target_medium": "blacknet",
            "audience_scope": "public",
            "audience_clan": "",
            "audience_owner": "",
            "truth_class": "canonical",
            "truth_class_policy": "canonical_facts_only",
            "facts": [fact],
            "allowed_actions": [],
            "canon_version": "test-v1",
            "task_variant": "part_activated",
            "narrative_intent": "ghost_part_activation",
            "narrative_thread_id": "ghost-part:public:test",
            "validation": {
                "event_family": "part_activated",
                "significance": "high",
            },
            "status": "ready",
        })
        task.update(overrides)
        return task

    def accepted(self, event_id="event-1"):
        return json.dumps({
            "title": "PRZECHWYT // AKTYWNY ELEMENT",
            "body": "...element sieci jest aktywny. Sygnal zanika.",
            "tone": "info",
            "fact_refs": ["f01"],
            "cta_ref": None,
        })

    def worker(self, client, worker_id="worker-a"):
        return OllamaNarrativeWorker(
            repository=self.repo,
            client=client,
            config=self.config,
            worker_id=worker_id,
        )

    def test_unassigned_task_is_reported_but_never_claimed(self):
        self.repo.enqueue_narrative_task(self.task(
            event_id="unassigned",
            prompt_version="unassigned",
            output_schema_version="unassigned",
            model_policy_version="unassigned",
        ))
        counts = self.repo.narrative_task_queue_counts(registered_ollama_policies())
        result = self.worker(FakeClient([])).process_once()

        self.assertEqual(result["result"], "idle")
        self.assertEqual(counts["eligible_ready"], 0)
        self.assertEqual(counts["ineligible_ready"], 1)
        self.assertEqual(counts["ready_by_prompt_version"], {"unassigned": 1})
        self.assertEqual(self.repo.list_narrative_outbox(limit=10)[0]["status"], "ready")

    def test_legacy_ghostnetwork_v1_task_is_claimed_during_v2_cutover(self):
        legacy = self.task(
            event_id="legacy-v1",
            prompt_version="ghostnetwork-event-prompt-v1",
        )
        item = self.repo.enqueue_narrative_task(legacy)
        client = FakeClient([self.accepted("legacy-v1")])

        result = self.worker(client).process_once()

        self.assertEqual(result["result"], "completed", result)
        self.assertEqual(client.calls, 1)
        self.assertEqual(
            self.repo.get_narrative_outbox(item["outbox_id"])["status"], "completed"
        )

    def test_thousands_of_historical_unassigned_tasks_do_not_block_eligible_claim(self):
        with self.repo.transaction():
            for index in range(1200):
                self.repo.enqueue_narrative_task(self.task(
                    event_id=f"historical-{index}",
                    prompt_version="unassigned",
                    output_schema_version="unassigned",
                    model_policy_version="unassigned",
                ))
            eligible = self.repo.enqueue_narrative_task(self.task(
                event_id="eligible-after-history", priority=100
            ))

        claimed = self.repo.claim_next_narrative_task(
            "bounded-worker", lease_seconds=60,
            eligible_policies=registered_ollama_policies(),
        )
        self.assertEqual(claimed["outbox_id"], eligible["outbox_id"])
        self.assertEqual(claimed["attempt_count"], 1)
        policy = registered_ollama_policies()[0]
        with db_connect(self.db_path) as conn:
            plan = conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT outbox_id FROM ghost_narrative_outbox
                INDEXED BY idx_ghost_narrative_registered_ready
                WHERE processor = 'ollama'
                  AND status IN ('ready', 'retry_wait')
                  AND attempt_count < max_attempts
                  AND (next_attempt_at = '' OR next_attempt_at <= ?)
                  AND prompt_version != 'unassigned'
                  AND output_schema_version != 'unassigned'
                  AND model_policy_version != 'unassigned'
                  AND source_scope = ? AND task_variant = ? AND target_medium = ?
                  AND prompt_version = ? AND output_schema_version = ?
                  AND model_policy_version = ?
                ORDER BY priority DESC, next_attempt_at, created_at, outbox_id
                LIMIT 1
                """,
                (self.repo.now(),) + policy.eligibility_tuple(),
            ).fetchall()
        details = " ".join(str(row["detail"]) for row in plan)
        self.assertIn("idx_ghost_narrative_registered_ready", details)

    def test_valid_generation_is_durable_before_outbox_completion(self):
        item = self.repo.enqueue_narrative_task(self.task())
        client = FakeClient([self.accepted()])
        result = self.worker(client).process_once()

        self.assertEqual(result["result"], "completed")
        self.assertEqual(client.calls, 1)
        self.assertEqual(self.repo.get_narrative_outbox(item["outbox_id"])["status"], "completed")
        candidates = self.repo.list_narrative_candidates(limit=10)
        attempts = self.repo.list_narrative_attempts(task_id=item["outbox_id"], limit=10)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["validation_status"], "accepted")
        self.assertEqual(attempts[0]["status"], "completed")
        self.assertGreater(attempts[0]["input_bytes"], 0)
        self.assertEqual(attempts[0]["fact_count"], 1)
        self.assertEqual(result["input_bytes"], attempts[0]["input_bytes"])
        self.assertEqual(result["fact_count"], attempts[0]["fact_count"])

    def test_two_workers_produce_exactly_one_model_call_and_candidate(self):
        self.repo.enqueue_narrative_task(self.task(event_id="two-workers"))
        client_a = FakeClient([self.accepted("two-workers")])
        client_b = FakeClient([self.accepted("two-workers")])
        worker_a = OllamaNarrativeWorker(
            repository=GhostNetworkRepository(db_path=self.db_path, clock=self.clock),
            client=client_a, config=self.config, worker_id="worker-a",
        )
        worker_b = OllamaNarrativeWorker(
            repository=GhostNetworkRepository(db_path=self.db_path, clock=self.clock),
            client=client_b, config=self.config, worker_id="worker-b",
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda worker: worker.process_once(), (worker_a, worker_b)))

        self.assertEqual(client_a.calls + client_b.calls, 1)
        self.assertEqual(sum(item["result"] == "completed" for item in results), 1)
        self.assertEqual(len(self.repo.list_narrative_candidates(limit=10)), 1)

    def test_invalid_json_retries_once_then_records_rejected_candidate(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="bad-json"))
        client = FakeClient(["not-json", "still-not-json"])
        worker = self.worker(client)

        first = worker.process_once()
        self.assertEqual(first["result"], "retry_wait")
        self.clock.advance(6)
        second = worker.process_once()
        self.assertEqual(second["result"], "completed")
        candidate = self.repo.get_narrative_candidate_for_task(item["outbox_id"])
        self.assertEqual(candidate["validation_status"], "rejected")
        self.assertEqual(client.calls, 2)

    def test_rejected_discovery_uses_support_fallback_before_completion(self):
        fact = attach_semantic_content(
            {"fact_id": "fact:support-drop", "fact_type": "part_discovered"},
            {
                "statement": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
                "entities": [
                    {"role": "miejsce", "kind": "target", "label": "Zara"},
                ],
            },
        )
        task = assign_ollama_task_policy({
            **self.task(event_id="support-drop"),
            "task_variant": "part_discovered",
            "narrative_intent": "ghost_part_discovery",
            "facts": [fact],
            "validation": {
                "event_family": "part_discovered", "significance": "high",
            },
        })
        item = self.repo.enqueue_narrative_task(task)
        client = FakeClient([json.dumps({
            "title": "PRZECHWYT // ELEMENT",
            "body": "...ujawniono ukryty element sieci.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        })])

        result = self.worker(client).process_once()

        candidate = self.repo.get_narrative_candidate_for_task(item["outbox_id"])
        attempt = self.repo.list_narrative_attempts(
            task_id=item["outbox_id"], limit=1
        )[0]
        self.assertEqual(result["narrative_support_mode"], "full")
        self.assertEqual(candidate["validation_status"], "accepted")
        self.assertIn("Zara", candidate["body"])
        self.assertEqual(attempt["result"], "accepted_support_full")

    def test_retryable_transport_error_preserves_task(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="timeout"))
        client = FakeClient(error=OllamaClientError("ollama_timeout", retryable=True))
        result = self.worker(client).process_once()

        self.assertEqual(result["result"], "retry_wait")
        current = self.repo.get_narrative_outbox(item["outbox_id"])
        self.assertEqual(current["status"], "retry_wait")
        self.assertEqual(current["last_error_code"], "ollama_timeout")

    def test_runtime_policy_exposes_canonical_retry_schedule(self):
        result = verify_ollama_runtime_policy(self.config)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["contract_version"], OLLAMA_RUNTIME_CONTRACT_VERSION)
        self.assertEqual(result["task_retry_backoff_seconds"], [5, 10, 20, 40, 80])
        self.assertEqual(
            [narrative_task_retry_backoff_seconds(index) for index in range(1, 7)],
            [5, 10, 20, 40, 80, 160],
        )

    def test_database_contention_is_returned_as_retryable_runtime_result(self):
        worker = self.worker(FakeClient([]))
        worker._reconcile_persisted_events = lambda: {"ok": True}
        worker._ensure_preflight = lambda: {"ok": True}

        def contended(*_args, **_kwargs):
            raise sqlite3.OperationalError("database is locked")

        self.repo.claim_next_narrative_task = contended
        first = worker.process_once()
        second = worker.process_once()

        self.assertEqual(first["result"], "database_contention")
        self.assertEqual(first["error_code"], "sqlite_busy")
        self.assertTrue(first["retryable"])
        self.assertGreaterEqual(first["retry_after_seconds"], 0.25)
        self.assertLessEqual(first["retry_after_seconds"], 2.0)
        self.assertEqual(second["result"], "database_contention")
        self.assertEqual(worker._runtime_metrics["database_contention_total"], 2)
        self.assertEqual(worker._runtime_metrics["database_contention_consecutive"], 2)
        self.assertTrue(is_database_contention(sqlite3.OperationalError("database is busy")))
        self.assertFalse(is_database_contention(sqlite3.OperationalError("no such table")))

    def test_non_contention_database_error_remains_fail_fast(self):
        worker = self.worker(FakeClient([]))
        worker._reconcile_persisted_events = lambda: {"ok": True}
        worker._ensure_preflight = lambda: {"ok": True}

        def broken(*_args, **_kwargs):
            raise sqlite3.OperationalError("no such table")

        self.repo.claim_next_narrative_task = broken
        with self.assertRaises(sqlite3.OperationalError):
            worker.process_once()

    def test_retry_backoff_reaches_dead_letter_at_max_attempts(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="retry-exhausted"))
        worker = self.worker(FakeClient(error=OllamaClientError(
            "ollama_timeout", retryable=True,
        )))

        expected_delays = [5, 10, 20, 40]
        for attempt, expected_delay in enumerate(expected_delays, start=1):
            result = worker.process_once()
            current = self.repo.get_narrative_outbox(item["outbox_id"])
            self.assertEqual(result["result"], "retry_wait")
            self.assertEqual(current["attempt_count"], attempt)
            expected_at = self.clock.value + timedelta(seconds=expected_delay)
            self.assertEqual(datetime.fromisoformat(current["next_attempt_at"]), expected_at)
            self.clock.advance(expected_delay + 1)

        result = worker.process_once()
        current = self.repo.get_narrative_outbox(item["outbox_id"])
        self.assertEqual(result["result"], "dead_letter")
        self.assertEqual(current["status"], "dead_letter")
        self.assertEqual(current["attempt_count"], 5)
        self.assertEqual(current["next_attempt_at"], "")
        self.assertEqual(len(self.repo.list_narrative_attempts(
            task_id=item["outbox_id"], limit=10,
        )), 5)

    def test_heartbeat_renews_lease_during_slow_generation(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="slow-generation"))

        class SlowClient(FakeClient):
            def generate(client_self, package, policy):
                time.sleep(0.08)
                self.clock.advance(3)
                time.sleep(0.06)
                return super(SlowClient, client_self).generate(package, policy)

        config = OllamaWorkerConfig(
            enabled=True,
            poll_seconds=0.1,
            poll_jitter_seconds=0,
            lease_seconds=2,
            heartbeat_seconds=0.05,
        )
        worker = OllamaNarrativeWorker(
            repository=self.repo,
            client=SlowClient([self.accepted("slow-generation")]),
            config=config,
            worker_id="heartbeat-worker",
        )

        result = worker.process_once()
        attempt = self.repo.list_narrative_attempts(task_id=item["outbox_id"], limit=1)[0]

        self.assertEqual(result["result"], "completed", result)
        self.assertEqual(attempt["status"], "completed")

    def test_controlled_run_once_can_claim_one_selected_medium(self):
        blacknet = self.repo.enqueue_narrative_task(self.task(event_id="medium-blacknet"))
        cyberner_task = assign_ollama_task_policy({
            "event_id": "medium-cyberner",
            "source_scope": "googleplex_app",
            "source_event_id": "medium-cyberner",
            "source_app_id": "agi2108Console",
            "processor": "ollama",
            "target_medium": "cyberner",
            "audience_scope": "owner",
            "audience_owner": "alice",
            "truth_class": "interpretation",
            "truth_class_policy": "owner_requested_interpretation",
            "facts": [{"fact_id": "fact:medium-cyberner", "fact_type": "test"}],
            "allowed_actions": [],
            "canon_version": "test-v1",
            "task_variant": "owner-analysis",
            "status": "ready",
        })
        cyberner = self.repo.enqueue_narrative_task(cyberner_task)
        client = FakeClient([self.accepted("medium-cyberner")])

        result = self.worker(client).process_once(target_medium="cyberner")

        self.assertEqual(result["result"], "completed")
        self.assertEqual(result["task_id"], cyberner["outbox_id"])
        self.assertEqual(self.repo.get_narrative_outbox(blacknet["outbox_id"])["status"], "ready")


    def test_failed_runtime_preflight_does_not_claim_task(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="preflight"))
        client = FakeClient([self.accepted("preflight")])
        client.verify_result = {"ok": False, "errors": ["ollama_model_digest_mismatch"]}
        result = self.worker(client).process_once()

        self.assertEqual(result["result"], "preflight_failed")
        self.assertEqual(client.calls, 0)
        current = self.repo.get_narrative_outbox(item["outbox_id"])
        self.assertEqual(current["status"], "ready")
        self.assertEqual(current["attempt_count"], 0)

    def test_event_reconciliation_runs_even_when_ollama_preflight_fails(self):
        self.clock.value = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        event = next(
            item for item in self.repo.list_events(cycle["cycle_id"], limit=1000)
            if item["event_type"] == "ghost.cycle_activated"
        )
        client = FakeClient([])
        client.verify_result = {"ok": False, "errors": ["ollama_unavailable"]}

        result = self.worker(client).process_once()
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event["event_id"], limit=10,
        )

        self.assertEqual(result["result"], "preflight_failed")
        self.assertEqual(
            {task["target_medium"] for task in tasks},
            {"blacknet", "googleplex_news"},
        )
        packages = {
            task["target_medium"]: (
                task,
                json.loads(build_ollama_task_package(task)["messages"][1]["content"]),
            )
            for task in tasks
        }
        self.assertEqual(
            packages["blacknet"][0]["prompt_version"],
            GHOSTNETWORK_EVENT_PROMPT_VERSION,
        )
        self.assertEqual(
            packages["googleplex_news"][0]["prompt_version"],
            GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
        )
        self.assertEqual(
            packages["googleplex_news"][1]["output_limits"]["title_chars"], 36,
        )
        for _task, model_input in packages.values():
            self.assertEqual(model_input["narrative_intent"], "ghost_cycle_state")
            self.assertEqual(model_input["event_family"], "cycle_activated")
            self.assertEqual(model_input["significance"], "high")
            self.assertEqual(model_input["tone_hint"], "warning")
            self.assertNotIn("source", model_input)
            self.assertNotIn("versions", model_input)
            self.assertNotIn("truth", model_input)
            self.assertEqual(model_input["audience"], {"scope": "public"})
            self.assertNotIn(event["event_id"], json.dumps(model_input))
            self.assertNotIn(event["cycle_id"], json.dumps(model_input))
            self.assertTrue(all(
                row["fact_ref"].startswith("f")
                for row in model_input["semantic_facts"]
            ))
        self.assertEqual(client.calls, 0)

    def test_crash_after_candidate_does_not_call_model_again(self):
        item = self.repo.enqueue_narrative_task(self.task(event_id="candidate-crash"))
        first_claim = self.repo.claim_next_narrative_task(
            "crashed-worker", lease_seconds=10, eligible_policies=registered_ollama_policies()
        )
        processing = self.repo.mark_narrative_task_processing(
            item["outbox_id"], "crashed-worker", first_claim["lease_until"]
        )
        attempt = self.repo.begin_narrative_attempt(
            processing, "crashed-worker", processing["lease_until"], "llama3.1:8b", "digest"
        )
        validation = {
            "status": "accepted",
            "errors": [],
            "output": json.loads(self.accepted("candidate-crash")),
        }
        candidate = self.repo.record_narrative_candidate(
            processing,
            attempt["attempt_id"],
            "crashed-worker",
            processing["lease_until"],
            validation,
            self.accepted("candidate-crash"),
            {"model": "llama3.1:8b", "model_digest": "digest", "runtime_version": "0.15.4"},
        )
        self.assertIsNotNone(candidate)

        self.clock.advance(11)
        next_client = FakeClient([])
        result = self.worker(next_client, worker_id="recovery-worker").process_once()
        self.assertEqual(result["result"], "candidate_recovered")
        self.assertEqual(next_client.calls, 0)
        self.assertEqual(self.repo.get_narrative_outbox(item["outbox_id"])["status"], "completed")
        recovered_attempt = self.repo.list_narrative_attempts(
            task_id=item["outbox_id"], limit=1,
        )[0]
        self.assertEqual(recovered_attempt["status"], "completed")
        self.assertEqual(recovered_attempt["result"], "candidate_recovered")

    def test_worker_modules_have_no_profile_or_web_app_dependency_and_do_not_log_prompts(self):
        root = os.path.dirname(os.path.dirname(__file__))
        paths = [
            os.path.join(root, "ghostnetwork", "ollama_worker.py"),
            os.path.join(root, "ghostnetwork", "ollama_client.py"),
            os.path.join(root, "ghostnetwork", "ollama_policy.py"),
            os.path.join(root, "scripts", "ollama_narrative_worker.py"),
        ]
        source = "\n".join(Path(path).read_text(encoding="utf-8") for path in paths)
        for forbidden in (
            "import run", "from run import", "load_profile", "get_profile(",
            "list_profiles(", "profile_json", "logging.", "print(package",
            "print(prompt", "print(generation.content",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
