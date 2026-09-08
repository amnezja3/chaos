import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import GhostAbilityProductionRealizer
from ghostnetwork.territory_defense import MAX_TERRITORY_DEFENSE_SWARM


class GhostNetworkBastionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 8, 14, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "S2"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-s2",
            latitude=52.2, longitude=21.0, discovered_by="pies1",
            discovered_clan="sentinel_order", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-s2", territory_owner_id="pies1",
            territory_clan="sentinel_order", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.player = {
            "username": "pies1", "player_id": "pies1", "clan": "sentinel_order",
            "profession": "defender", "level": 50,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("bastion",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def test_s2_arms_the_frozen_territory_defense_report_gate(self):
        service = GhostNetworkService(repository=self.repo)
        activated = service.activate_player_ability(
            self.player, "bastion-activation", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        effect = service.active_territory_defense_effect(
            self.player, now=self.now, snapshot=snapshot,
        )

        self.assertEqual("armed", activated["realizer"]["status"])
        self.assertEqual(
            "territory_defense",
            GhostAbilityProductionRealizer.ABILITY_FAMILIES["bastion"],
        )
        self.assertTrue(effect["active"])
        self.assertEqual("bastion", effect["ability_code"])
        self.assertEqual(activated["window"]["window_id"], effect["window_id"])
        self.assertEqual(activated["window"]["cooldown_until"], effect["cooldown_until"])
        self.assertEqual(MAX_TERRITORY_DEFENSE_SWARM, effect["swarm_limit"])

        self.assertEqual("Bastion", snapshot["presentation"]["display_name"])
        self.assertEqual("MUR PODNIESIONY", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("territory_defense", snapshot["presentation"]["impact_ui"])
        self.assertIn("s2_bastion_matrix", snapshot["presentation"]["visual_asset_url"])

    def test_expiry_disarms_the_report_gate_without_changing_family_policy(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(
            self.player, "bastion-window", now=self.now,
        )

        self.now += timedelta(minutes=16)
        effect = service.active_territory_defense_effect(self.player, now=self.now)

        self.assertFalse(effect["active"])
        self.assertEqual(1, effect["swarm_limit"])


if __name__ == "__main__":
    unittest.main()
