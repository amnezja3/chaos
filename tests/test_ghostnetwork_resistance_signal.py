import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    MAX_SCAN_RANGE_METERS,
    GhostAbilityProductionRealizer,
    calculate_scan_range_m,
)


class GhostNetworkResistanceSignalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 6, 14, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "E4"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-e4",
            latitude=52.2, longitude=21.0, discovered_by="echo",
            discovered_clan="echo_freedom", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-e4", territory_owner_id="echo",
            territory_clan="echo_freedom", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.player = {
            "username": "echo", "player_id": "echo", "clan": "echo_freedom",
            "profession": "visionary", "level": 71, "action_range": 2528,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("resistance_signal",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def test_level_formula_and_global_cap_are_frozen(self):
        self.assertEqual(25_000, calculate_scan_range_m(1))
        self.assertEqual(250_000, calculate_scan_range_m(10))
        self.assertEqual(1_775_000, calculate_scan_range_m(71))
        self.assertEqual(7_500_000, calculate_scan_range_m(300))
        self.assertEqual(MAX_SCAN_RANGE_METERS, calculate_scan_range_m(999999))
        self.assertEqual(0, calculate_scan_range_m(71, "other"))

    def test_activation_uses_level_snapshot_and_exposes_e4_presentation(self):
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(
            self.player, "resistance-signal-activation", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        effect = service.active_scan_range_effect(
            self.player, now=self.now, snapshot=snapshot,
        )

        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual("scan_range", result["realizer"]["family"])
        self.assertEqual(1_775_000, result["realizer"]["effective_range_m"])
        self.assertTrue(effect["active"])
        self.assertEqual(1_775_000, effect["effective_range_m"])
        self.assertEqual("Beacon Oporu", snapshot["presentation"]["display_name"])
        self.assertEqual("ŚWIAT W ZASIĘGU", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("scan_range", snapshot["presentation"]["impact_ui"])
        self.assertIn("e4_resonance_beacon", snapshot["presentation"]["visual_asset_url"])

    def test_live_level_change_does_not_change_window_range_and_expiry_restores_base(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(
            self.player, "resistance-signal-window", now=self.now,
        )
        leveled = {**self.player, "level": 300, "action_range": 4000}

        active = service.active_scan_range_effect(leveled, now=self.now)
        self.now += timedelta(minutes=16)
        expired = service.active_scan_range_effect(leveled, now=self.now)

        self.assertEqual(1_775_000, active["effective_range_m"])
        self.assertFalse(expired["active"])
        self.assertEqual(4000, expired["effective_range_m"])

    def test_scan_call_site_is_lightweight_and_keeps_local_poi_radius(self):
        import run

        source = inspect.getsource(run.map_action)
        scan = source[source.index("# Scan is a hot path"):source.index("if action == \"travel\"")]
        self.assertIn("identity_projection_store.get_identity", scan)
        self.assertIn("capability_projection_store.get_capabilities", scan)
        self.assertIn("active_scan_range_effect", scan)
        self.assertIn('"radius_m": int(fetcher.radius)', scan)
        self.assertIn('distance > action_range', scan)
        for forbidden in ("sync_session_profile(", "user_store.get_profile(", "list_profiles("):
            self.assertNotIn(forbidden, scan)


if __name__ == "__main__":
    unittest.main()
