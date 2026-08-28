import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

from googleplex_news import (
    ASSET_FAMILIES,
    GoogleplexNewsConfigurationError,
    build_googleplex_news_snapshot,
    load_asset_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "static" / "images" / "googleplx" / "asset_registry.json"


class GoogleplexNewsFoundationTest(unittest.TestCase):
    def setUp(self):
        load_asset_registry.cache_clear()
        self.now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
        self.catalog = [
            {
                "id": "tool_alpha",
                "name": "Alpha Tool",
                "description": "Canonical tool projection.",
                "published": True,
                "downloads": 42,
            },
            {
                "id": "tool_hidden",
                "name": "Hidden Tool",
                "published": False,
                "downloads": 999,
            },
        ]

    def build(self, **changes):
        arguments = {
            "catalog": self.catalog,
            "viewer_key": "main",
            "session_generation": "generation-a",
            "limit": 20,
            "now": self.now,
            "registry_path": str(REGISTRY_PATH),
        }
        arguments.update(changes)
        return build_googleplex_news_snapshot(**arguments)

    def test_snapshot_has_deterministic_editorial_hierarchy(self):
        first = self.build()
        second = self.build(now=datetime(2026, 8, 28, 12, 5, tzinfo=timezone.utc))
        weights = [entry["presentation"]["weight"] for entry in first["entries"]]
        self.assertEqual(weights.count("hero"), 1)
        self.assertEqual(weights.count("large"), 2)
        self.assertEqual(weights.count("medium"), 3)
        self.assertEqual(weights.count("small"), 6)
        self.assertEqual(first["state_version"], second["state_version"])
        self.assertEqual(first["entries"], second["entries"])
        self.assertNotEqual(first["generated_at"], second["generated_at"])
        self.assertEqual(len(first["entries"]), 12)

    def test_snapshot_is_read_only_and_never_claims_llm_publication(self):
        snapshot = self.build()
        self.assertFalse(snapshot["protocol_status"]["ollama_used"])
        self.assertFalse(snapshot["protocol_status"]["llm_task_enqueued"])
        self.assertFalse(snapshot["protocol_status"]["publication_enabled"])
        self.assertEqual(snapshot["diagnostics"]["profile_full_read"], 0)
        self.assertEqual(snapshot["diagnostics"]["profile_full_write"], 0)
        self.assertEqual(snapshot["diagnostics"]["profile_bytes"], 0)
        serialized = json.dumps(snapshot, ensure_ascii=False).lower()
        for forbidden in ("prompt", "raw_output", "quarantine", "profile_json", "publication_receipt_id"):
            self.assertNotIn(forbidden, serialized)

    def test_viewer_revision_is_session_bound_but_content_is_public(self):
        first = self.build()
        replaced = self.build(session_generation="generation-b")
        other = self.build(viewer_key="neo1")
        self.assertEqual(first["entries"], replaced["entries"])
        self.assertEqual(first["entries"], other["entries"])
        self.assertNotEqual(first["viewer_scope_revision"], replaced["viewer_scope_revision"])
        self.assertNotEqual(first["viewer_scope_revision"], other["viewer_scope_revision"])

    def test_catalog_projection_is_bounded_and_ignores_unpublished_products(self):
        snapshot = self.build(catalog=self.catalog * 5000)
        featured = next(entry for entry in snapshot["entries"] if entry["content"]["news_id"] == "gp-home-featured")
        catalog_stat = next(item for item in snapshot["global_stats"] if item["key"] == "catalog")
        self.assertEqual(featured["content"]["source_ref"], "tool_alpha")
        self.assertEqual(featured["action"]["action_type"], "open_googleplex_search")
        self.assertEqual(catalog_stat["value"], 5000)
        self.assertLessEqual(len(snapshot["entries"]), 24)

    def test_every_action_and_asset_is_fail_closed_and_allowlisted(self):
        snapshot = self.build()
        registry = load_asset_registry(str(REGISTRY_PATH))
        for entry in snapshot["entries"]:
            action = entry["action"]
            if action["kind"] == "ACTIONABLE":
                self.assertTrue(action["action_type"])
            else:
                self.assertEqual(action["action_type"], "")
                self.assertEqual(action["action_target"], "")
            presentation = entry["presentation"]
            self.assertIn(presentation["asset_family"], ASSET_FAMILIES)
            self.assertIn(presentation["asset_id"], registry)
            self.assertTrue(presentation["asset_path"].startswith("/static/images/googleplx/"))

    def test_registry_has_four_hero_states_and_all_family_fallbacks(self):
        registry = load_asset_registry(str(REGISTRY_PATH))
        for state in ("neutral", "danger", "victory", "defence"):
            record = registry[f"gp_scene_world_{state}_01"]
            self.assertEqual(record["status"], "ready")
            self.assertEqual(record["asset_family"], "scene")
            self.assertEqual(record["asset_state"], state)
            self.assertIn("hero", record["allowed_presentation_weights"])
            asset_path = ROOT / record["path"].lstrip("/")
            self.assertTrue(asset_path.is_file(), asset_path)
            self.assertGreater(asset_path.stat().st_size, 100_000)
        for family in ASSET_FAMILIES:
            self.assertEqual(registry[f"gp_fallback_{family}"]["status"], "ready")

    def test_invalid_registry_fails_closed(self):
        broken = ROOT / "tests" / "_tmp_googleplex_asset_registry.json"
        try:
            broken.write_text(json.dumps({"assets": [{"asset_id": "unsafe"}]}), encoding="utf-8")
            load_asset_registry.cache_clear()
            with self.assertRaises(GoogleplexNewsConfigurationError):
                load_asset_registry(str(broken))
        finally:
            broken.unlink(missing_ok=True)
            load_asset_registry.cache_clear()

    def test_runtime_route_has_no_heavy_profile_or_ollama_callsite(self):
        source = (ROOT / "run.py").read_text(encoding="utf-8")
        start = source.index('def api_googleplex_news():')
        end = source.index('\n\n@app.route', start + 1)
        route = source[start:end]
        for forbidden in (
            "load_profile", "get_profile", "list_profiles", "profile_json",
            "Ollama", "narrative_outbox", "narrative_candidate",
        ):
            self.assertNotIn(forbidden, route)


if __name__ == "__main__":
    unittest.main()
