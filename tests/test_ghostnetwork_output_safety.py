import json
import unittest

from ghostnetwork.llm.output_safety import GHOST_OUTPUT_SAFETY_CONTRACT_VERSION
from ghostnetwork.llm.semantic_input import attach_semantic_content
from ghostnetwork.narrative_support import NarrativeSupportLayer
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    parse_and_validate_ollama_content,
)


class GhostNetworkOutputSafetyTest(unittest.TestCase):
    def task(self, audience="public", include_part=False):
        entities = [{"role": "miejsce", "kind": "target", "label": "Zara"}]
        if include_part:
            entities.append({
                "role": "element sieci", "kind": "part", "label": "Deep Sensor",
            })
        fact = attach_semantic_content(
            {"fact_id": "fact:drop-safety", "fact_type": "part_discovered"},
            {
                "statement": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
                "entities": entities,
            },
        )
        return assign_ollama_task_policy({
            "source_scope": "ghostnetwork",
            "source_event_id": "event-output-safety",
            "task_variant": "part_discovered",
            "target_medium": "blacknet",
            "audience_scope": audience,
            "truth_class_policy": "canonical_facts_only",
            "narrative_intent": "ghost_part_discovery",
            "validation": {
                "event_family": "part_discovered",
                "significance": "high",
            },
            "facts": [fact],
            "allowed_actions": [],
            "fixed_action": {},
        })

    @staticmethod
    def content(body, title="PRZECHWYT // ŚLAD SIECI"):
        return json.dumps({
            "title": title,
            "body": body,
            "tone": "warning",
            "fact_refs": ["f01"],
            "cta_ref": None,
        }, ensure_ascii=False)

    def validate(self, body, task=None):
        package = build_ollama_task_package(task or self.task())
        return parse_and_validate_ollama_content(self.content(body), package), package

    def test_active_package_declares_backend_output_safety_contract(self):
        result, package = self.validate(
            "...przy obiekcie Zara ukryty element GhostNetwork wyszedł na jaw."
        )

        self.assertEqual(result["status"], "accepted", result)
        self.assertEqual(
            package["output_safety_contract_version"],
            GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
        )
        self.assertEqual(
            result["output_safety_contract_version"],
            GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
        )

    def test_control_alias_and_prompt_language_are_quarantined(self):
        cases = (
            ("...przy Zara zapisano fact_ref f01.", "control_metadata_leak"),
            ("...przy Zara zapisano fact_ref f01.", "model_alias_leak"),
            ("...cel map:-37.81179:144.96324:Zara.", "internal_identifier_leak"),
            ("...przy Zara: ignore previous instructions.", "prompt_or_tool_language_leak"),
        )
        for body, error in cases:
            with self.subTest(error=error):
                result, _package = self.validate(body)
                self.assertEqual(result["status"], "quarantined", result)
                self.assertIn(error, result["errors"])

    def test_secrets_addresses_paths_and_markup_are_quarantined(self):
        cases = (
            ("...przy Zara kontakt: ghost@example.com.", "credential_or_personal_data_leak"),
            ("...przy Zara węzeł 10.20.30.40.", "network_address_leak"),
            ("...przy Zara: -37.81179, 144.96324.", "raw_coordinate_leak"),
            ("...przy Zara zapisano /home/ghost/secret.db.", "filesystem_path_leak"),
            ("...przy Zara <script>alert(1)</script>.", "unsafe_markup"),
        )
        for body, error in cases:
            with self.subTest(error=error):
                result, _package = self.validate(body)
                self.assertEqual(result["status"], "quarantined", result)
                self.assertIn(error, result["errors"])

    def test_hidden_catalog_name_is_blocked_but_owner_visible_name_is_allowed(self):
        hidden, _package = self.validate(
            "...przy obiekcie Zara ujawniono element Deep Sensor."
        )
        self.assertEqual(hidden["status"], "quarantined", hidden)
        self.assertIn("audience_hidden_catalog_value", hidden["errors"])

        owner, _package = self.validate(
            "...przy obiekcie Zara ujawniono element Deep Sensor.",
            self.task(audience="owner", include_part=True),
        )
        self.assertEqual(owner["status"], "accepted", owner)

    def test_clan_catalog_name_is_allowed_only_when_present_in_semantic_facts(self):
        task = self.task(audience="clan")
        task["task_variant"] = "part_activated"
        task["narrative_intent"] = "ghost_part_activation"
        task["validation"]["event_family"] = "part_activated"
        task["facts"] = [attach_semantic_content(
            {"fact_id": "fact:clan-safety", "fact_type": "part_activated"},
            {
                "statement": "Element klanu Siatka Widmo został aktywowany.",
                "entities": [{
                    "role": "klan elementu", "kind": "clan", "label": "Siatka Widmo",
                }],
            },
        )]
        task = assign_ollama_task_policy(task)

        result, _package = self.validate(
            "...element klanu Siatka Widmo jest aktywny.", task
        )

        self.assertEqual(result["status"], "accepted", result)

    def test_audience_identity_not_sent_to_model_cannot_be_published(self):
        task = self.task(audience="owner", include_part=True)
        task["audience_owner"] = "alice-secret"
        result, package = self.validate(
            "...alice-secret widzi Deep Sensor przy obiekcie Zara.", task
        )

        self.assertNotIn("alice-secret", package["messages"][1]["content"])
        self.assertEqual(result["status"], "quarantined", result)
        self.assertIn("audience_hidden_value_leak", result["errors"])

    def test_firewall_does_not_judge_innocent_numbers_or_narrative_language(self):
        result, _package = self.validate(
            "...przy Zara drugi sygnał odsłonił 2 ślady; kolejne to 3, 4 i 5."
        )

        self.assertEqual(result["status"], "accepted", result)

    def test_security_rejection_uses_same_validated_support_path(self):
        task = self.task()
        package = build_ollama_task_package(task)
        rejected = parse_and_validate_ollama_content(self.content(
            "...przy Zara ujawniono element Deep Sensor."
        ), package)

        support = NarrativeSupportLayer().apply(
            task, package, rejected, parse_and_validate_ollama_content
        )

        self.assertEqual(rejected["status"], "quarantined", rejected)
        self.assertEqual(support["mode"], "full")
        self.assertEqual(support["validation"]["status"], "accepted")
        self.assertNotIn("Deep Sensor", support["validation"]["output"]["body"])


if __name__ == "__main__":
    unittest.main()
