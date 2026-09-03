import os
import tempfile
import unittest

from ghostnetwork.cycles import GhostCycleService
from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.repository import GhostNetworkRepository
from scripts.audit_narrative_output_safety import build_report


class NarrativeOutputSafetyAuditTest(unittest.TestCase):
    def test_active_production_shaped_task_passes_adversarial_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = GhostNetworkRepository(
                db_path=os.path.join(tmp, "output-safety.sqlite3")
            )
            cycle = GhostCycleService(repository=repository).ensure_active_cycle()["cycle"]
            event = repository.append_event(
                "ghost.part_discovered",
                cycle_id=cycle["cycle_id"],
                audience_scope="owner",
                payload={"status": "public"},
            )
            fact = attach_semantic_content(
                {"fact_id": "fact:safety-audit", "fact_type": "part_discovered"},
                {
                    "statement": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
                    "entities": [
                        {"role": "miejsce", "kind": "target", "label": "Zara"},
                        {"role": "element", "kind": "part", "label": "Deep Sensor"},
                    ],
                },
            )
            task = assign_ollama_task_policy({
                "source_scope": "ghostnetwork",
                "source_event_id": event["event_id"],
                "cycle_id": cycle["cycle_id"],
                "processor": "ollama",
                "target_medium": "blacknet",
                "audience_scope": "owner",
                "audience_owner": "alice-secret",
                "truth_class": "canonical",
                "truth_class_policy": "canonical_facts_only",
                "facts": [fact],
                "allowed_actions": [],
                "fixed_action": {},
                "task_variant": "part_discovered",
                "narrative_intent": "ghost_part_discovery",
                "validation": {
                    "event_family": "part_discovered",
                    "significance": "high",
                },
                "status": "ready",
            })
            repository.enqueue_narrative_task(task)

            report = build_report(repository, event_id=event["event_id"])

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["sample_count"], 1)
            probes = report["samples"][0]["probes"]
            self.assertTrue(all(item["ok"] for item in probes.values()), probes)
            self.assertIn("hidden_audience_value", probes)
            self.assertEqual(probes["free_narrative_language"]["errors"], [])


if __name__ == "__main__":
    unittest.main()
