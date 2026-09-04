import json
import tempfile
import unittest
from pathlib import Path

from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    parse_and_validate_ollama_content,
)
from ghostnetwork.narrative_support import NarrativeSupportLayer


class NarrativeSupportLayerTest(unittest.TestCase):
    ENDGAME_FAMILIES = {
        "machine_online": ("ghost_machine_state", "high", "Maszyna GhostNetwork osiągnęła stan online."),
        "cycle_locked": ("ghost_cycle_state", "critical", "Bieżący cykl GhostNetwork został nieodwracalnie zamknięty."),
        "signal_sent": ("ghost_signal_transmission", "critical", "GhostSignal został wysłany z zamkniętej sieci."),
        "version_changed": ("ghost_system_transition", "critical", "Ghost System przeszedł do kolejnej wersji."),
        "stabilization_started": ("ghost_cycle_state", "normal", "Rozpoczęła się stabilizacja zamkniętej sieci GhostNetwork."),
        "cycle_activated": ("ghost_cycle_state", "high", "Nowy cykl GhostNetwork został aktywowany."),
    }

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

    def test_endgame_fallbacks_cover_guaranteed_blacknet_and_googleplex_routes(self):
        layer = NarrativeSupportLayer()
        for family, (intent, significance, statement) in self.ENDGAME_FAMILIES.items():
            routes = [
                ("blacknet", "public"),
                ("blacknet", "clan"),
                ("blacknet", "owner"),
                ("googleplex_news", "public"),
            ]
            for medium, audience in routes:
                with self.subTest(family=family, medium=medium, audience=audience):
                    fixed_action = {
                        "cta_action": (
                            "open_ghostsignal_archive"
                            if family == "signal_sent"
                            else "open_ghostnetwork_suite"
                        ),
                        "payload": {"signal_id": "signal-one"}
                        if family == "signal_sent" else {},
                    }
                    task = assign_ollama_task_policy({
                        "source_scope": "ghostnetwork",
                        "source_event_id": f"event-{family}-{medium}-{audience}",
                        "target_medium": medium,
                        "audience_scope": audience,
                        "truth_class": "canonical",
                        "truth_class_policy": "canonical_facts_only",
                        "facts": [attach_semantic_content(
                            {"fact_id": f"fact:{family}", "fact_type": family},
                            {"statement": statement},
                        )],
                        "allowed_actions": [fixed_action],
                        "fixed_action": fixed_action,
                        "task_variant": (
                            "googleplex_world_dispatch"
                            if medium == "googleplex_news" else family
                        ),
                        "narrative_intent": intent,
                        "narrative_thread_id": f"ghost-endgame:{family}",
                        "validation": {
                            "event_family": family,
                            "significance": significance,
                        },
                    })
                    package = build_ollama_task_package(task)
                    result = layer.apply(
                        task,
                        package,
                        {"status": "rejected", "errors": ["invalid_body"], "output": None},
                        parse_and_validate_ollama_content,
                    )

                    self.assertIsNotNone(result)
                    self.assertEqual(result["validation"]["status"], "accepted", result)
                    self.assertEqual(
                        result["validation"]["resolved_cta"]["cta_action"],
                        fixed_action["cta_action"],
                    )

    def test_private_endgame_route_can_only_inherit_public_safe_template(self):
        layer = NarrativeSupportLayer()
        public = layer._definition("blacknet", "signal_sent", "public")
        self.assertIs(layer._definition("blacknet", "signal_sent", "clan"), public)
        self.assertIs(layer._definition("blacknet", "signal_sent", "owner"), public)

    def test_verify_fails_closed_when_required_endgame_fallback_is_missing(self):
        source = Path("ghostnetwork/llm/narrative_support.v1.yaml").read_text(
            encoding="utf-8"
        )
        source = source.replace("    cycle_activated:\n", "    omitted_cycle_activated:\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "support.yaml"
            path.write_text(source, encoding="utf-8")
            result = NarrativeSupportLayer(path).verify()

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["required_endgame_routes"], 12)
        self.assertEqual(
            result["missing_required_endgame_routes"],
            ["blacknet:cycle_activated:public"],
        )

    def test_verify_confirms_all_required_endgame_fallbacks(self):
        result = NarrativeSupportLayer().verify()

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["required_endgame_routes"], 12)
        self.assertEqual(result["missing_required_endgame_routes"], [])


if __name__ == "__main__":
    unittest.main()
