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


class GhostNetworkQuarantineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 8, 18, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "S5"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-s5",
            latitude=52.2, longitude=21.0, discovered_by="sentinel",
            discovered_clan="sentinel_order", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-s5", territory_owner_id="sentinel",
            territory_clan="sentinel_order", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.player = {
            "username": "sentinel", "player_id": "sentinel",
            "clan": "sentinel_order", "profession": "executor", "level": 75,
            "action_range": 2600, "map_zoom": 18,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("quarantine",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def test_s5_reuses_frozen_p4_calibration(self):
        for level in (1, 9, 10, 50, 75, 100, 150, 200, 500):
            with self.subTest(level=level):
                p4 = calculate_map_zoom_scale(level, "network_fracture")
                s5 = calculate_map_zoom_scale(level, "quarantine")
                self.assertEqual(p4, s5)
        self.assertFalse(calculate_map_zoom_scale(75, "other")["active"])

    def test_activation_uses_snapshot_and_exposes_s5_presentation(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "quarantine-activation", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        effect = service.active_map_zoom_effect(
            self.player, now=self.now, snapshot=snapshot,
        )
        internal = service.ability_production_realizer.apply_activation(
            self.player["player_id"], result["window"],
        )

        self.assertEqual("map_zoom", GhostAbilityProductionRealizer.ABILITY_FAMILIES["quarantine"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual("map_zoom", internal["family"])
        self.assertEqual("country", effect["scale"])
        self.assertEqual(1_750_000, effect["radius_m"])
        self.assertEqual(7, effect["min_zoom"])
        self.assertEqual(7, effect["zoom_out_bonus"])
        self.assertEqual("Kwarantanna", snapshot["presentation"]["display_name"])
        self.assertEqual("GRANICA WYZNACZONA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("map_zoom", snapshot["presentation"]["impact_ui"])
        self.assertIn("s5_judgment_core", snapshot["presentation"]["visual_asset_url"])

    def test_window_uses_level_snapshot_and_expiry_or_part_loss_restores_base(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "quarantine-window", now=self.now)
        leveled = {**self.player, "level": 250}

        active = service.active_map_zoom_effect(leveled, now=self.now)
        expired = service.active_map_zoom_effect(
            leveled, now=self.now + timedelta(minutes=16),
        )

        self.assertEqual("country", active["scale"])
        self.assertEqual(1_750_000, active["radius_m"])
        self.assertEqual(7, active["min_zoom"])
        self.assertFalse(expired["active"])

        self.repo.update_part(self.part["part_id"], status="public")
        self.assertFalse(service.active_map_zoom_effect(leveled, now=self.now)["active"])

    def test_frontend_reuses_zoom_handoff_with_sentinel_narration(self):
        source = Path("templates/map_template.html").read_text(encoding="utf-8")
        for token in (
            "ability.ability_code === 'quarantine'",
            "JUDGMENT CORE // CONTAINMENT GRID",
            "AKTYWACJA PIERŚCIENIA KWARANTANNY",
            "ROZSZERZANIE STREFY NADZORU",
            "showGhostMapZoomHandoff(snapshot)",
            "saveManualMapViewport()",
            "window.location.reload()",
        ):
            self.assertIn(token, source)
        zoom_runtime = source[
            source.index("function applyGhostAbilityMapZoom"):
            source.index("function stopGhostAbilityAudio")
        ]
        for forbidden in (
            "map.fitBounds(", "map.fitWorld(", "map.setView(", "map.panTo(",
        ):
            self.assertNotIn(forbidden, zoom_runtime)
        map_view = inspect.getsource(__import__("run").map_view)
        self.assertIn("active_map_zoom_effect", map_view)
        self.assertIn("min_zoom = min(min_zoom", map_view)


if __name__ == "__main__":
    unittest.main()
