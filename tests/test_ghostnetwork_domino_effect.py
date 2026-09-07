import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import PlayerTargetRuntimeStore
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService


class GhostNetworkDominoEffectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "E5"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-e5",
            latitude=52.2, longitude=21.0, discovered_by="igniter",
            discovered_clan="echo_freedom", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-e5", territory_owner_id="igniter",
            territory_clan="echo_freedom", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.player = {
            "username": "igniter", "player_id": "igniter", "clan": "echo_freedom",
            "profession": "igniter", "level": 71,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES", ("domino_effect",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def aim(self, suffix="one"):
        longitude = 21.1 if suffix == "one" else 21.2
        return self.targets.upsert_aimed("igniter", {
            "target_id": f"map:52.1:{longitude}:E5-{suffix}",
            "lat": 52.1,
            "lng": longitude,
            "label": f"E5-{suffix}",
            "actions_allowed": {
                "scan_ports": False, "exploit": False,
                "sniff": False, "trace": False,
            },
            "security": {
                "firewall": True, "ids": True, "vpn": False,
                "process_monitor": True, "security_level": 4,
            },
        })

    def assert_complete_security_bar_disabled(self, target):
        self.assertTrue(all(
            value is False for value in target["security"].values()
            if isinstance(value, bool)
        ))
        self.assertTrue(all(value is False for value in target["actions_allowed"].values()))
        self.assertEqual(4, target["security"]["security_level"])
        self.assertEqual(100, target["disarm_progress"])

    def test_activation_disables_complete_security_bar_and_preserves_dots(self):
        aimed = self.aim()
        result = GhostNetworkService(repository=self.repo).activate_player_ability(
            self.player, "domino-now", now=self.now,
        )
        after = self.targets.get("igniter")

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(3, result["realizer"]["applied_changes"])
        self.assert_complete_security_bar_disabled(after)
        self.assertEqual(aimed["target"]["target_id"], result["window"]["target_id"])

    def test_every_new_aimed_target_gets_the_same_full_bar_effect(self):
        service = GhostNetworkService(repository=self.repo)
        activated = service.activate_player_ability(self.player, "domino-window", now=self.now)
        self.assertEqual("no_selected_target", activated["realizer"]["status"])

        for suffix in ("one", "two"):
            aimed = self.aim(suffix)
            first = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            after = self.targets.get("igniter")
            self.assertEqual("applied", first["status"])
            self.assert_complete_security_bar_disabled(after)
            version = after["version"]
            replay = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            self.assertEqual("replayed", replay["status"])
            self.assertEqual(version, self.targets.get("igniter")["version"])

    def test_expiry_and_part_loss_stop_future_aimed_targets(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "domino-stop", now=self.now)
        aimed = self.aim()
        expired = service.apply_active_ability_to_aimed_target(
            self.player, aimed["target"]["target_id"],
            now=self.now + timedelta(minutes=16),
        )
        self.assertEqual("inactive", expired["status"])
        self.assertTrue(any(
            value is True for value in self.targets.get("igniter")["security"].values()
            if isinstance(value, bool)
        ))

        self.repo.update_part(self.part["part_id"], status="public")
        inactive = service.apply_active_ability_to_aimed_target(
            self.player, aimed["target"]["target_id"], now=self.now,
        )
        self.assertEqual("inactive", inactive["status"])

    def test_presentation_and_runtime_path_reuse_expose_contract(self):
        service = GhostNetworkService(repository=self.repo)
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        self.assertTrue(snapshot["available"])
        self.assertEqual("Efekt Domina", snapshot["presentation"]["display_name"])
        self.assertEqual("ISKRA POSZŁA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("target_security_bar", snapshot["presentation"]["impact_ui"])
        self.assertIn("e5_spark_chamber", snapshot["presentation"]["visual_asset_url"])

        import run
        source = inspect.getsource(run.apply_active_ghostnetwork_ability_to_aimed_target)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
