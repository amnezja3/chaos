import json
import unittest

from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    parse_and_validate_ollama_content,
)
from ghostnetwork.narrative_support import NarrativeSupportLayer


class NarrativeSupportLayerTest(unittest.TestCase):
    def task(self, medium="blacknet", audience="public", include_part=False):
        entities = [{"role": "miejsce", "kind": "target", "label": "Zara"}]
        if include_part:
            entities.append({
                "role": "element sieci", "kind": "part", "label": "Accord Relay",
            })
        fact = attach_semantic_content(
            {"fact_id": "fact:drop-1", "fact_type": "part_discovered"},
            {
                "statement": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
                "entities": entities,
            },
        )
        return assign_ollama_task_policy({
            "source_scope": "ghostnetwork",
            "source_event_id": "event-drop-1",
            "target_medium": medium,
            "audience_scope": audience,
            "truth_class": "canonical",
            "truth_class_policy": "canonical_facts_only",
            "facts": [fact],
            "allowed_actions": [],
            "fixed_action": {},
            "task_variant": (
                "googleplex_world_dispatch"
                if medium == "googleplex_news" else "part_discovered"
            ),
            "narrative_intent": "ghost_part_discovery",
            "narrative_thread_id": "ghost-part:test",
            "validation": {
                "event_family": "part_discovered",
                "significance": "high",
            },
        })

    def test_blacknet_rejection_gets_deterministic_safe_full_fallback(self):
        task = self.task()
        package = build_ollama_task_package(task)
        rejected = parse_and_validate_ollama_content(json.dumps({
            "title": "PRZECHWYT // ELEMENT",
            "body": "...ukryty element sieci został ujawniony.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }), package)
        self.assertEqual(rejected["status"], "rejected")

        layer = NarrativeSupportLayer()
        first = layer.apply(task, package, rejected, parse_and_validate_ollama_content)
        second = layer.apply(task, package, rejected, parse_and_validate_ollama_content)

        self.assertEqual(first["mode"], "full")
        self.assertEqual(first["content"], second["content"])
        self.assertEqual(first["validation"]["status"], "accepted")
        self.assertIn("Zara", first["validation"]["output"]["body"])
        self.assertEqual(first["validation"]["output"]["fact_refs"], ["fact:drop-1"])

    def test_googleplex_can_replace_only_invalid_title(self):
        task = self.task(medium="googleplex_news")
        package = build_ollama_task_package(task)
        good_body = "Przy obiekcie Zara ujawniono ukryty element sieci GhostNetwork."
        rejected = parse_and_validate_ollama_content(json.dumps({
            "title": "",
            "body": good_body,
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
            "asset_ref": package["allowed_asset_refs"][0],
        }), package)
        self.assertEqual(rejected["status"], "rejected")

        result = NarrativeSupportLayer().apply(
            task, package, rejected, parse_and_validate_ollama_content
        )

        self.assertEqual(result["mode"], "title")
        self.assertEqual(result["validation"]["status"], "accepted")
        self.assertEqual(result["validation"]["output"]["body"], good_body)

    def test_missing_owner_part_fails_closed_without_inventing_value(self):
        task = self.task(audience="owner", include_part=False)
        package = build_ollama_task_package(task)
        result = NarrativeSupportLayer().apply(
            task,
            package,
            {"status": "rejected", "errors": ["invalid_body"], "output": None},
            parse_and_validate_ollama_content,
        )
        self.assertIsNone(result)

    def test_accepted_model_output_is_never_rewritten(self):
        task = self.task()
        package = build_ollama_task_package(task)
        accepted = parse_and_validate_ollama_content(json.dumps({
            "title": "PRZECHWYT // ZARA",
            "body": "...przy obiekcie Zara ujawniono ukryty element GhostNetwork.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }), package)
        self.assertEqual(accepted["status"], "accepted")
        self.assertIsNone(NarrativeSupportLayer().apply(
            task, package, accepted, parse_and_validate_ollama_content
        ))


if __name__ == "__main__":
    unittest.main()
