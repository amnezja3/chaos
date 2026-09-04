import json
import os
import tempfile
import unittest

from database import db_connect
from ghostnetwork.cycles import GhostCycleService
from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.ollama_client import OllamaGenerationResult
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.publication import NarrativePublicationService
from ghostnetwork.repository import GhostNetworkRepository
from scripts.audit_narrative_e2e import build_report


class AcceptedClient:
    def __init__(self):
        self.sequence = 0

    def verify(self):
        return {"ok": True, "errors": []}

    def generate(self, package, policy):
        self.sequence += 1
        return OllamaGenerationResult(
            model=policy.model_name,
            model_digest=policy.model_digest,
            runtime_version="test",
            content=json.dumps({
                "title": "PRZECHWYT // AKTYWNY ELEMENT",
                "body": (
                    "...element GhostNetwork jest aktywny. "
                    f"Sygnał {self.sequence} zanika."
                ),
                "tone": "warning",
                "fact_refs": [next(iter(package["fact_refs"]))],
                "cta_ref": None,
            }, ensure_ascii=False),
            done=True,
            done_reason="stop",
            total_duration_ns=10,
            load_duration_ns=1,
            prompt_eval_count=20,
            eval_count=10,
            raw_response_hash="response-hash",
        )


class NarrativeE2EAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "narrative-e2e.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.event = self.repo.append_event(
            "ghost.part_activated",
            cycle_id=cycle["cycle_id"],
            audience_scope="public",
            payload={"status": "active"},
        )
        fact = attach_semantic_content({
            "fact_id": f"ghost_fact:{self.event['event_id']}:part_activated:public",
            "fact_type": "part_activated",
        }, {
            "statement": "Element GhostNetwork został aktywowany.",
        })
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
            "narrative_thread_id": "ghost-part:ghost-node:test",
            "world_state_version": str(self.event["state_version"]),
            "validation": {
                "event_family": "part_activated",
                "significance": "high",
            },
            "priority": 80,
            "status": "ready",
        })
        self.task = self.repo.enqueue_narrative_task(task)
        worker = OllamaNarrativeWorker(
            repository=self.repo,
            client=AcceptedClient(),
            config=OllamaWorkerConfig(
                enabled=True,
                poll_seconds=0.1,
                poll_jitter_seconds=0,
                lease_seconds=60,
                heartbeat_seconds=30,
            ),
            worker_id="e2e-audit-ollama",
        )
        processed = []
        for _ in range(20):
            result = worker.process_once(target_medium="blacknet")
            processed.append(result)
            if result.get("task_id") == self.task["outbox_id"]:
                break
        self.assertEqual(processed[-1].get("task_id"), self.task["outbox_id"], processed)
        self.assertEqual(processed[-1]["result"], "completed")

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self):
        publisher = NarrativePublicationService(
            repository=self.repo,
            worker_id="e2e-audit-publisher",
        )
        processed = []
        for _ in range(20):
            result = publisher.process_once()
            processed.append(result)
            if (result.get("record") or {}).get("task_id") == self.task["outbox_id"]:
                break
        self.assertEqual(
            (processed[-1].get("record") or {}).get("task_id"),
            self.task["outbox_id"],
            processed,
        )
        self.assertEqual(processed[-1]["result"], "published")
        return processed[-1]

    def test_complete_task_to_medium_lineage_passes(self):
        self.publish()

        report = build_report(self.repo, task_id=self.task["outbox_id"])

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["generation_ok"])
        self.assertEqual(report["chain_count"], 1)
        self.assertEqual(report["chains"][0]["record"]["active_state"], "active")
        self.assertEqual(report["event_to_publication_ms"]["samples"], 1)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["profiles_loaded"])

    def test_missing_publication_is_a_strict_failure(self):
        report = build_report(self.repo, task_id=self.task["outbox_id"])

        self.assertFalse(report["ok"])
        self.assertIn("publication_chain_incomplete", report["errors"])
        self.assertIn("publication_receipt_missing", report["chains"][0]["errors"])

    def test_record_source_event_mismatch_is_detected(self):
        published = self.publish()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE ghost_narrative_medium_records SET source_event_id = 'wrong' "
                "WHERE medium_record_id = ?",
                (published["record"]["medium_record_id"],),
            )

        report = build_report(self.repo, task_id=self.task["outbox_id"])

        self.assertFalse(report["ok"])
        self.assertIn("record_source_event_mismatch", report["chains"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
