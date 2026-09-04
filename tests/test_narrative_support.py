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
            "title": "PRZECHWYT // Ukryty element sieci GhostNetwork",
            "body": (
                "...ujawniono wcześniej ukryty element sieci GhostNetwork "
                "przy obiekcie Zara."
            ),
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }), package)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("voice_canonical_echo", rejected["errors"])

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

    def test_googleplex_polish_ghost_name_is_valid_not_truncated(self):
        task = self.task(medium="googleplex_news")
        package = build_ollama_task_package(task)
        validation = parse_and_validate_ollama_content(json.dumps({
            "title": "Ujawniono ukryty element sieci Ghost",
            "body": "Przy obiekcie Zara ujawniono ukryty element sieci GhostNetwork.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
            "asset_ref": package["allowed_asset_refs"][0],
        }), package)

        self.assertEqual(validation["status"], "accepted", validation)
        self.assertIsNone(NarrativeSupportLayer().apply(
            task, package, validation, parse_and_validate_ollama_content
        ))

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

    def test_part_activated_fallback_covers_every_production_route(self):
        routes = (
            ("blacknet", "public", False),
            ("blacknet", "clan", False),
            ("blacknet", "owner", True),
            ("googleplex_news", "public", False),
        )
        layer = NarrativeSupportLayer()
        for medium, audience, include_part in routes:
            with self.subTest(medium=medium, audience=audience):
                task = self.task(
                    medium=medium, audience=audience, include_part=include_part
                )
                task.update({
                    "source_event_id": f"event-activation-{medium}-{audience}",
                    "task_variant": (
                        "googleplex_world_dispatch"
                        if medium == "googleplex_news" else "part_activated"
                    ),
                    "narrative_intent": "ghost_part_activation",
                    "validation": {
                        "event_family": "part_activated",
                        "significance": "high",
                    },
                    "facts": [attach_semantic_content(
                        {
                            "fact_id": f"fact:activation:{medium}:{audience}",
                            "fact_type": "part_activated",
                        },
                        {
                            "statement": (
                                "Element GhostNetwork został aktywowany przez "
                                "prawidłowe otoczenie terytorium."
                            ),
                            "entities": (
                                [{"role": "miejsce", "kind": "target", "label": "Zara"}]
                                + ([{
                                    "role": "element sieci", "kind": "part",
                                    "label": "Accord Relay",
                                }] if include_part else [])
                            ),
                        },
                    )],
                })
                task = assign_ollama_task_policy(task)
                package = build_ollama_task_package(task)
                output = {
                    "title": "Aktywacja GhostNetwork",
                    "body": (
                        "Element GhostNetwork został aktywowany przez prawidłowe "
                        "otoczenie terytorium."
                    ),
                    "tone": "warning",
                    "fact_refs": ["f01"],
                    "cta_ref": None,
                }
                if medium == "googleplex_news":
                    output["asset_ref"] = package["allowed_asset_refs"][0]
                rejected = parse_and_validate_ollama_content(
                    json.dumps(output, ensure_ascii=False), package
                )
                self.assertEqual(rejected["status"], "rejected", rejected)

                first = layer.apply(
                    task, package, rejected, parse_and_validate_ollama_content
                )
                second = layer.apply(
                    task, package, rejected, parse_and_validate_ollama_content
                )

                self.assertIsNotNone(first)
                self.assertEqual(first["content"], second["content"])
                self.assertEqual(first["validation"]["status"], "accepted")
                self.assertIn("Zara", first["validation"]["output"]["body"])
                if audience == "owner":
                    self.assertIn(
                        "Accord Relay", first["validation"]["output"]["body"]
                    )

    def test_truncated_activation_copy_uses_blacknet_full_fallback(self):
        task = self.task(medium="blacknet", audience="public")
        task.update({
            "source_event_id": "event-activation-truncated",
            "task_variant": "part_activated",
            "narrative_intent": "ghost_part_activation",
            "validation": {
                "event_family": "part_activated",
                "significance": "high",
            },
            "facts": [attach_semantic_content(
                {"fact_id": "fact:activation:truncated", "fact_type": "part_activated"},
                {
                    "statement": (
                        "Element GhostNetwork został aktywowany przez prawidłowe "
                        "otoczenie terytorium."
                    ),
                    "entities": [{
                        "role": "miejsce", "kind": "target", "label": "POI-18D194",
                    }],
                    "location": {"city": "Hartford"},
                },
            )],
        })
        task = assign_ollama_task_policy(task)
        package = build_ollama_task_package(task)
        rejected = parse_and_validate_ollama_content(json.dumps({
            "title": "PRZECHWYT // Element GhostNetwork został aktywow",
            "body": "...wane przez prawidłowe otoczenie terytorium w Hartford.",
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }, ensure_ascii=False), package)

        self.assertEqual(rejected["status"], "rejected", rejected)
        self.assertIn("voice_title_trailing_fragment", rejected["errors"])
        self.assertIn("voice_body_leading_fragment", rejected["errors"])
        supported = NarrativeSupportLayer().apply(
            task, package, rejected, parse_and_validate_ollama_content
        )
        self.assertIsNotNone(supported)
        self.assertEqual(supported["mode"], "full")
        self.assertEqual(supported["validation"]["status"], "accepted")
        self.assertIn("POI-18D194", supported["validation"]["output"]["body"])


if __name__ == "__main__":
    unittest.main()
