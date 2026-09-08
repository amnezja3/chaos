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


class GhostNetworkIntegrityScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "S1"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-s1",
            latitude=52.2, longitude=21.0, discovered_by="pies1",
            discovered_clan="sentinel_order", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-s1", territory_owner_id="pies1",
            territory_clan="sentinel_order", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.player = {
            "username": "pies1", "player_id": "pies1", "clan": "sentinel_order",
            "profession": "analyzer", "level": 50, "action_range": 2421,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("integrity_scan",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def test_s1_reuses_frozen_scan_range_contract_and_presentation(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "integrity-scan-activation", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        effect = service.active_scan_range_effect(
            self.player, now=self.now, snapshot=snapshot,
        )
        internal = service.ability_production_realizer.apply_activation(
            self.player["player_id"], result["window"],
        )

        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual("scan_range", GhostAbilityProductionRealizer.ABILITY_FAMILIES["integrity_scan"])
        self.assertEqual("scan_range", internal["family"])
        self.assertEqual(1_250_000, internal["effective_range_m"])
        self.assertTrue(effect["active"])
        self.assertEqual("integrity_scan", effect["ability_code"])
        self.assertEqual(1_250_000, effect["effective_range_m"])
        self.assertEqual("Skan Integralności", snapshot["presentation"]["display_name"])
        self.assertEqual("SIEĆ PRZEŚWIETLONA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("scan_range", snapshot["presentation"]["impact_ui"])
        self.assertIn("s1_deep_sensor", snapshot["presentation"]["visual_asset_url"])

    def test_level_snapshot_is_stable_and_expiry_restores_base_range(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(
            self.player, "integrity-scan-window", now=self.now,
        )
        leveled = {**self.player, "level": 999999, "action_range": 4100}

        active = service.active_scan_range_effect(leveled, now=self.now)
        self.now += timedelta(minutes=16)
        expired = service.active_scan_range_effect(leveled, now=self.now)

        self.assertEqual(1_250_000, active["effective_range_m"])
        self.assertLess(active["effective_range_m"], MAX_SCAN_RANGE_METERS)
        self.assertFalse(expired["active"])
        self.assertEqual(4100, expired["effective_range_m"])

    def test_policy_rejects_unknown_code_but_accepts_s1(self):
        self.assertEqual(25_000, calculate_scan_range_m(1, "integrity_scan"))
        self.assertEqual(MAX_SCAN_RANGE_METERS, calculate_scan_range_m(999999, "integrity_scan"))
        self.assertEqual(0, calculate_scan_range_m(50, "unknown"))


if __name__ == "__main__":
    unittest.main()
