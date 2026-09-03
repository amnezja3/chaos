import json
import os
import tempfile
import unittest

from ghostnetwork.cycles import GhostCycleService
from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.ollama_client import OllamaGenerationResult
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.repository import GhostNetworkRepository
from scripts.audit_narrative_generation import build_report


class FakeClient:
    def __init__(self, content):
        self.content = content

    def verify(self):
        return {"ok": True, "errors": []}

    def generate(self, _package, policy):
        return OllamaGenerationResult(
            model=policy.model_name,
            model_digest=policy.model_digest,
            runtime_version="0.15.4",
            content=self.content,
            done=True,
            done_reason="stop",
            total_duration_ns=10,
            load_duration_ns=1,
            prompt_eval_count=20,
            eval_count=10,
            raw_response_hash="response-hash",
        )


class NarrativeGenerationAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "generation.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.event = self.repo.append_event(
            "ghost.part_activated",
            cycle_id=cycle["cycle_id"],
            audience_scope="public",
            payload={"status": "active"},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _task(self, _suffix):
        fact = attach_semantic_content(
            {
                "fact_id": f"ghost_fact:{self.event['event_id']}:part_activated:public",
                "fact_type": "part_activated",
            },
            {"statement": "Element GhostNetwork został aktywowany."},
        )
        task = assign_ollama_task_policy({
            "event_id": self.event["event_id"],
            "source_scope": "ghostnetwork",
            "source_event_id": self.event["event_id"],
            "processor": "ollama",
            "target_medium": "blacknet",
            "audience_scope": "public",
            "truth_class": "canonical",
            "truth_class_policy": "canonical",
            "facts": [fact],
            "allowed_actions": [],
            "fixed_action": {
                "cta_action": "show_ghostnetwork_part",
                "cta_payload": {"public_entity_id": "ghost-node:test"},
            },
            "task_variant": "part_activated",
            "narrative_intent": "ghost_part_activation",
            "validation": {
                "event_family": "part_activated",
                "significance": "high",
            },
            "priority": 1000,
            "status": "ready",
        })
        return self.repo.enqueue_narrative_task(task)

    def _run(self, item, content):
        worker = OllamaNarrativeWorker(
            repository=self.repo,
            client=FakeClient(content),
            config=OllamaWorkerConfig(
                enabled=True,
                poll_seconds=0.1,
                poll_jitter_seconds=0,
                lease_seconds=60,
                heartbeat_seconds=30,
            ),
            worker_id="generation-audit-test",
        )
        result = worker.process_once(target_medium="blacknet")
        self.assertEqual(result["task_id"], item["outbox_id"])

    def test_strict_chain_passes_for_accepted_v3_candidate(self):
        item = self._task("accepted")
        self._run(item, json.dumps({
            "title": "Przebudzenie w sieci",
            "body": "Ukryty element GhostNetwork został aktywowany.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }, ensure_ascii=False))

        report = build_report(self.repo, task_id=item["outbox_id"])

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["sample_count"], 1)
        sample = report["samples"][0]
        self.assertTrue(sample["ok"], sample)
        self.assertEqual(sample["candidate"]["validation_status"], "accepted")
        self.assertEqual(sample["attempt"]["request_hash"], sample["package"]["request_hash"])
        self.assertEqual(
            sample["model_input"]["semantic_facts"][0]["statement"],
            "Element GhostNetwork został aktywowany.",
        )

    def test_strict_chain_fails_and_exposes_quarantine_reason(self):
        item = self._task("quarantined")
        self._run(item, json.dumps({
            "title": "Identyfikator",
            "body": "Aktywowano event_deadbeef123456.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }))

        report = build_report(self.repo, task_id=item["outbox_id"])

        self.assertFalse(report["ok"])
        sample = report["samples"][0]
        self.assertIn("candidate_not_accepted:quarantined", sample["errors"])
        self.assertIn("internal_identifier_leak", sample["candidate"]["validation_errors"])

    def test_strict_chain_fails_for_ready_task_without_attempt(self):
        item = self._task("ready")

        report = build_report(self.repo, task_id=item["outbox_id"])

        self.assertFalse(report["ok"])
        self.assertIn("attempt_missing", report["samples"][0]["errors"])
        self.assertIn("candidate_missing", report["samples"][0]["errors"])

    def test_event_gate_cannot_pass_without_complete_producer_fanout(self):
        report = build_report(self.repo, event_id=self.event["event_id"])

        self.assertFalse(report["ok"])
        self.assertIn("generation_v3_tasks_missing", report["errors"])
        self.assertIn("expected_generation_tasks_missing", report["errors"])
        self.assertEqual(report["expected_task_count"], 2)
        self.assertEqual(
            {item["target_medium"] for item in report["missing_task_identities"]},
            {"blacknet", "googleplex_news"},
        )


if __name__ == "__main__":
    unittest.main()
