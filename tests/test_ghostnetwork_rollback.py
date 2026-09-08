import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import PlayerTargetRuntimeStore
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import GhostAbilityProductionRealizer


class GhostNetworkRollbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 8, 16, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "S3"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-s3",
            latitude=52.2, longitude=21.0, discovered_by="pies1",
            discovered_clan="sentinel_order", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-s3", territory_owner_id="pies1",
            territory_clan="sentinel_order", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.player = {
            "username": "pies1", "player_id": "pies1", "clan": "sentinel_order",
            "profession": "reconstructor", "level": 50,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("rollback",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def aim(self, suffix):
        return self.targets.upsert_aimed("pies1", {
            "target_id": f"map:52.1:21.{suffix}:S3-{suffix}",
            "lat": 52.1,
            "lng": 21 + int(suffix) / 10,
            "label": f"S3-{suffix}",
            "actions_allowed": {
                "scan_ports": False, "exploit": False,
                "sniff": False, "trace": False,
            },
            "security": {
                "firewall": True, "ids": True, "vpn": False,
            },
        })

    def test_activation_repairs_current_target_actions_and_preserves_security(self):
        aimed = self.aim("1")
        before = self.targets.get("pies1")
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(
            self.player, "rollback-current", now=self.now,
        )
        after = self.targets.get("pies1")

        self.assertEqual("hack_actions", GhostAbilityProductionRealizer.ABILITY_FAMILIES["rollback"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(4, result["realizer"]["applied_changes"])
        self.assertTrue(all(after["actions_allowed"].values()))
        self.assertEqual(before["security"], after["security"])
        self.assertEqual(aimed["target"]["target_id"], result["window"]["target_id"])
        self.assertEqual(1, len(after["target"].get("ability_application_keys") or []))

    def test_every_new_aimed_target_during_window_gets_four_actions_once(self):
        service = GhostNetworkService(repository=self.repo)
        activated = service.activate_player_ability(
            self.player, "rollback-window", now=self.now,
        )
        self.assertEqual("no_selected_target", activated["realizer"]["status"])

        for suffix in ("1", "2"):
            aimed = self.aim(suffix)
            before = self.targets.get("pies1")
            security = dict(before["security"])
            first = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            after = self.targets.get("pies1")

            self.assertEqual("applied", first["status"])
            self.assertTrue(all(after["actions_allowed"].values()))
            self.assertEqual(security, after["security"])
            self.assertEqual(1, len(after["target"].get("ability_application_keys") or []))

            version = after["version"]
            replay = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            self.assertEqual("replayed", replay["status"])
            self.assertEqual(version, self.targets.get("pies1")["version"])

    def test_expiry_and_part_loss_stop_future_target_application(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(
            self.player, "rollback-expiry", now=self.now,
        )
        expired_target = self.aim("1")
        expired = service.apply_active_ability_to_aimed_target(
            self.player, expired_target["target"]["target_id"],
            now=self.now + timedelta(minutes=16),
        )
        self.assertEqual("inactive", expired["status"])
        self.assertFalse(any(self.targets.get("pies1")["actions_allowed"].values()))

        second_now = self.now + timedelta(hours=2)
        service.activate_player_ability(
            self.player, "rollback-part-loss", now=second_now,
        )
        self.repo.update_part(self.part["part_id"], status="public")
        lost_target = self.aim("2")
        lost = service.apply_active_ability_to_aimed_target(
            self.player, lost_target["target"]["target_id"], now=second_now,
        )
        self.assertEqual("inactive", lost["status"])
        self.assertFalse(any(self.targets.get("pies1")["actions_allowed"].values()))

    def test_s3_uses_shared_target_action_presentation(self):
        snapshot = GhostNetworkService(
            repository=self.repo,
        ).get_player_ability_window_snapshot(self.player, now=self.now)

        self.assertTrue(snapshot["available"])
        self.assertEqual("Odtworzenie", snapshot["presentation"]["display_name"])
        self.assertEqual("DOSTĘP ODTWORZONY", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("target_action_dots", snapshot["presentation"]["impact_ui"])
        self.assertIn("s3_restoration_engine", snapshot["presentation"]["visual_asset_url"])


if __name__ == "__main__":
    unittest.main()
