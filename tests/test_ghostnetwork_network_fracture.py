import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    GhostAbilityProductionRealizer,
    calculate_map_zoom_scale,
)


class GhostNetworkNetworkFractureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 7, 18, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "P4"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-p4",
            latitude=52.2, longitude=21.0, discovered_by="phantom",
            discovered_clan="phantom_mesh", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-p4", territory_owner_id="phantom",
            territory_clan="phantom_mesh", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.player = {
            "username": "phantom", "player_id": "phantom", "clan": "phantom_mesh",
            "profession": "network_splitter", "level": 73, "action_range": 2600,
            "map_zoom": 18,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("network_fracture",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def test_strategic_scale_thresholds_are_frozen(self):
        expected = {
            1: ("local", 3_000, False, 14),
            9: ("local", 27_000, False, 10),
            10: ("city", 30_000, False, 10),
            50: ("country", 500_000, False, 6),
            75: ("country", 1_750_000, False, 5),
            100: ("continent", 3_000_000, False, 4),
            150: ("continent", 11_500_000, False, 3),
            200: ("world", 20_000_000, True, 2),
        }
        for level, contract in expected.items():
            with self.subTest(level=level):
                effect = calculate_map_zoom_scale(level)
                self.assertEqual(contract, (
                    effect["scale"], effect["radius_m"], effect["fit_world"],
                    effect["min_zoom"],
                ))
        self.assertFalse(calculate_map_zoom_scale(100, "other")["active"])

    def test_activation_uses_snapshot_and_exposes_p4_presentation(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "network-fracture-activation", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        effect = service.active_map_zoom_effect(
            self.player, now=self.now, snapshot=snapshot,
        )
        internal = service.ability_production_realizer.apply_activation(
            self.player["player_id"], result["window"],
        )

        self.assertEqual("map_zoom", GhostAbilityProductionRealizer.ABILITY_FAMILIES["network_fracture"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual("map_zoom", internal["family"])
        self.assertEqual("country", effect["scale"])
        self.assertEqual(1_650_000, effect["radius_m"])
        self.assertEqual(5, effect["min_zoom"])
        self.assertEqual("Pęknięcie Sieci", snapshot["presentation"]["display_name"])
        self.assertEqual("HORYZONT PĘKA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("map_zoom", snapshot["presentation"]["impact_ui"])
        self.assertIn("p4_fracture_engine", snapshot["presentation"]["visual_asset_url"])

    def test_live_level_change_does_not_change_window_scale_and_expiry_restores_base(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(
            self.player, "network-fracture-window", now=self.now,
        )
        leveled = {**self.player, "level": 250}

        active = service.active_map_zoom_effect(leveled, now=self.now)
        self.now += timedelta(minutes=16)
        expired = service.active_map_zoom_effect(leveled, now=self.now)

        self.assertEqual("country", active["scale"])
        self.assertEqual(1_650_000, active["radius_m"])
        self.assertEqual(5, active["min_zoom"])
        self.assertFalse(expired["active"])
        self.assertEqual("", expired["scale"])

    def test_frontend_unlocks_zoom_without_moving_view_and_restores_base_limit(self):
        source = Path("templates/map_template.html").read_text(encoding="utf-8")
        for token in (
            "function applyGhostAbilityMapZoom",
            "runtime.mapZoomWindowId === windowId",
            "player.effective_min_map_zoom",
            "player.base_min_map_zoom",
            "saveManualMapViewport()",
            "window.location.reload()",
            "map.setMinZoom(effectiveMinZoom)",
            "map.setMinZoom(normalMinZoom)",
            "window.ghostAbilityRuntime.mapZoomActive",
            "SKALA ${ghostAbilityMapScaleLabel(strategicScale)}",
        ):
            self.assertIn(token, source)
        zoom_runtime = source[
            source.index("function applyGhostAbilityMapZoom"):
            source.index("function stopGhostAbilityAudio")
        ]
        for forbidden in (
            "map.fitBounds(", "map.fitWorld(", "map.setView(", "map.panTo(",
            "map.getBoundsZoom(", "toBounds(radiusM",
        ):
            self.assertNotIn(forbidden, zoom_runtime)
        map_view = inspect.getsource(__import__("run").map_view)
        self.assertIn("active_map_zoom_effect", map_view)
        self.assertIn("min_zoom = min(min_zoom", map_view)
        self.assertLess(map_view.index("min_zoom = min(min_zoom"), map_view.index("folium.Map("))
        endpoint = inspect.getsource(__import__("run").api_ghostnetwork_ability)
        for field in (
            "map_zoom_active", "map_zoom_scale", "map_zoom_radius_m",
            "map_zoom_fit_world", "base_min_map_zoom", "effective_min_map_zoom",
        ):
            self.assertIn(field, endpoint)


if __name__ == "__main__":
    unittest.main()
