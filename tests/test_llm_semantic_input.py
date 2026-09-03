import json
import unittest
from pathlib import Path

from ghostnetwork.llm.semantic_input import (
    SEMANTIC_INPUT_CONTRACT_VERSION,
    attach_semantic_content,
    infer_scan_location,
    model_visible_semantic_fact,
    normalize_semantic_content,
    project_poi_location,
)
from ghostnetwork.semantic import GHOST_EVENT_STATEMENTS, GhostNetworkSemanticConverter


class SharedSemanticInputTest(unittest.TestCase):
    def test_poi_location_is_bounded_and_uses_declared_osm_keys(self):
        location = project_poi_location({
            "addr:city": "  Warszawa ",
            "addr:country": "Polska",
            "addr:country_code": "pl",
            "addr:street": "Pole niewchodzące do kontraktu",
            "unbounded": "x" * 5000,
        })
        self.assertEqual(location, {
            "city": "Warszawa", "country": "Polska", "country_code": "PL",
        })

    def test_scan_location_accepts_agreement_and_ignores_missing_votes(self):
        result = infer_scan_location([
            {"tags": {"addr:city": "Warszawa", "addr:country": "Polska"}},
            {"tags": {"city": " warszawa ", "country": "POLSKA"}},
            {"tags": {}},
        ])
        self.assertEqual(result["location"], {"city": "Warszawa", "country": "Polska"})
        self.assertEqual(result["conflicts"], [])

    def test_scan_location_missing_stays_unknown(self):
        result = infer_scan_location([{"tags": {}}, {"tags": {"amenity": "cafe"}}])
        self.assertEqual(result["location"], {})

    def test_scan_location_conflict_stays_unknown(self):
        result = infer_scan_location([
            {"tags": {"addr:city": "Warszawa", "addr:country": "Polska"}},
            {"tags": {"addr:city": "Łódź", "addr:country": "Polska"}},
        ])
        self.assertNotIn("city", result["location"])
        self.assertEqual(result["location"]["country"], "Polska")
        self.assertEqual(result["conflicts"], ["city"])

    def test_single_source_poi_is_sufficient_but_coordinates_never_infer_city(self):
        known = infer_scan_location([{"lat": 52.1, "lon": 21.1, "tags": {"addr:city": "Warszawa"}}])
        unknown = infer_scan_location([{"lat": 52.1, "lon": 21.1, "tags": {}}])
        self.assertEqual(known["location"], {"city": "Warszawa"})
        self.assertEqual(unknown["location"], {})

    def test_model_projection_keeps_lineage_alias_but_rejects_technical_content(self):
        fact = attach_semantic_content(
            {"fact_id": "event_secret_1234567890"},
            {"statement": "Wykryto element GhostNetwork."},
        )
        self.assertEqual(model_visible_semantic_fact(fact, "f01"), {
            "fact_ref": "f01", "statement": "Wykryto element GhostNetwork.",
        })
        with self.assertRaisesRegex(ValueError, "technical_id"):
            normalize_semantic_content({"statement": "Wykryto event_deadbeef123456."})
        with self.assertRaisesRegex(ValueError, "technical_id"):
            normalize_semantic_content({"statement": "Cykl ghostnetwork_0001 zamknięty."})

    def test_converter_is_deterministic_and_covers_every_active_family(self):
        converter = GhostNetworkSemanticConverter()
        for family in GHOST_EVENT_STATEMENTS:
            fact = {"fact_id": f"canonical:{family}", "fact_type": family}
            event = {"event_type": f"ghost.{family}", "payload": {}}
            first = converter.enrich(fact, event, {"scope": "public"})
            second = converter.enrich(fact, event, {"scope": "public"})
            self.assertEqual(
                json.dumps(first, ensure_ascii=False, sort_keys=True),
                json.dumps(second, ensure_ascii=False, sort_keys=True),
            )
            self.assertEqual(first["semantic_contract"], SEMANTIC_INPUT_CONTRACT_VERSION)
            self.assertTrue(first["semantic"]["statement"])
            self.assertNotIn("location", first["semantic"])

    def test_audience_projection_resolves_labels_before_model(self):
        converter = GhostNetworkSemanticConverter()
        fact = {"fact_id": "canonical", "fact_type": "part_discovered"}
        event = {"event_type": "ghost.part_discovered", "payload": {}}
        part = {
            "part_code": "P1", "machine_code": "phantom_veil",
            "clan_code": "phantom_mesh",
            "anchor_snapshot": {
                "label": "Biblioteka Główna",
                "location": {"city": "Warszawa", "country": "Polska"},
            },
        }
        public = converter.enrich(fact, event, {"scope": "public"}, part, {})
        clan = converter.enrich(
            fact, event, {"scope": "clan", "clan": "phantom_mesh"}, part,
            {"target_clan": "phantom_mesh"},
        )
        owner = converter.enrich(fact, event, {"scope": "owner"}, part, {})

        public_kinds = {item["kind"] for item in public["semantic"].get("entities", [])}
        public_roles = {item["role"] for item in public["semantic"].get("entities", [])}
        clan_labels = {item["label"] for item in clan["semantic"].get("entities", [])}
        clan_roles = {item["role"] for item in clan["semantic"].get("entities", [])}
        owner_labels = {item["label"] for item in owner["semantic"].get("entities", [])}
        owner_roles = {item["role"] for item in owner["semantic"].get("entities", [])}
        self.assertEqual(public_kinds, {"target"})
        self.assertEqual(public_roles, {"lokalizacja zakotwiczenia zdarzenia"})
        self.assertIn("Siatka Widmo", clan_labels)
        self.assertIn("klan odbiorcy", clan_roles)
        self.assertTrue({"Mirage Projector", "PHANTOM VEIL", "Siatka Widmo"}.issubset(owner_labels))
        self.assertIn("maszyna powiązana z elementem", owner_roles)
        self.assertEqual(public["semantic"]["location"]["city"], "Warszawa")

    def test_frontend_contract_forwards_location_from_scan_to_mark(self):
        root = Path(__file__).resolve().parents[1]
        map_source = (root / "templates" / "map_template.html").read_text(encoding="utf-8")
        terminal_source = (root / "static" / "js" / "terminal.js").read_text(encoding="utf-8")
        self.assertIn("location: obj.location || data.scan_context?.location || null", map_source)
        self.assertIn("location: targetContext?.location || null", map_source)
        self.assertIn("location: normalized.location || null", map_source)
        self.assertIn("menuTarget.stable_conflict_id || menuTarget.conflict_id || null,\n                        menuTarget", map_source)
        self.assertIn("location: scan.location || null", terminal_source)


if __name__ == "__main__":
    unittest.main()
