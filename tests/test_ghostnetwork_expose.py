import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import (
    PlayerTargetRuntimeStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService


class GhostNetworkExposeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 6, 16, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "E1"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-e1",
            latitude=52.2, longitude=21.0, discovered_by="echo",
            discovered_clan="echo_freedom", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-e1", territory_owner_id="echo",
            territory_clan="echo_freedom", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.player = {
            "username": "echo", "player_id": "echo", "clan": "echo_freedom",
            "profession": "hacktivist", "level": 71,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES", ("expose",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def aim(self, suffix="one"):
        return self.targets.upsert_aimed("echo", {
            "target_id": f"map:52.1:21.{1 if suffix == 'one' else 2}:ECHO-{suffix}",
            "lat": 52.1,
            "lng": 21.1 if suffix == "one" else 21.2,
            "label": f"ECHO-{suffix}",
            "actions_allowed": {
                "scan_ports": False, "exploit": False,
                "sniff": False, "trace": False,
            },
            "security": {
                "firewall": True, "ids": True, "vpn": False,
                "process_monitor": True, "security_level": 4,
            },
        })

    def test_activation_clears_complete_security_bar_and_preserves_dots(self):
        aimed = self.aim()
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(self.player, "expose-now", now=self.now)
        after = self.targets.get("echo")

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(3, result["realizer"]["applied_changes"])
        self.assertTrue(all(value is False for value in after["actions_allowed"].values()))
        self.assertTrue(all(
            value is False for value in after["security"].values()
            if isinstance(value, bool)
        ))
        self.assertEqual(4, after["security"]["security_level"])
        self.assertEqual(100, after["disarm_progress"])
        markers = after["target"].get("ability_application_keys") or []
        self.assertEqual(1, len(markers))
        self.assertTrue(markers[0].endswith(":security"))
        self.assertEqual(aimed["target"]["target_id"], result["window"]["target_id"])

    def test_window_applies_to_every_new_aimed_target_exactly_once(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(self.player, "expose-window", now=self.now)
        self.assertEqual("no_selected_target", result["realizer"]["status"])

        for suffix in ("one", "two"):
            aimed = self.aim(suffix)
            first = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            after = self.targets.get("echo")
            self.assertEqual("applied", first["status"])
            self.assertTrue(all(value is False for value in after["actions_allowed"].values()))
            self.assertTrue(all(
                value is False for value in after["security"].values()
                if isinstance(value, bool)
            ))
            version = after["version"]
            replay = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            self.assertEqual("replayed", replay["status"])
            self.assertEqual(version, self.targets.get("echo")["version"])

    def test_expiry_and_part_loss_stop_future_targets_without_restoring_old_one(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "expose-stop", now=self.now)
        first = self.aim("one")
        service.apply_active_ability_to_aimed_target(
            self.player, first["target"]["target_id"], now=self.now,
        )
        self.assertTrue(all(
            value is False for value in self.targets.get("echo")["security"].values()
            if isinstance(value, bool)
        ))

        second = self.aim("two")
        expired = service.apply_active_ability_to_aimed_target(
            self.player, second["target"]["target_id"],
            now=self.now + timedelta(minutes=16),
        )
        self.assertEqual("inactive", expired["status"])
        self.assertTrue(any(
            value is True for value in self.targets.get("echo")["security"].values()
            if isinstance(value, bool)
        ))

        self.repo.update_part(self.part["part_id"], status="public")
        inactive = service.apply_active_ability_to_aimed_target(
            self.player, second["target"]["target_id"], now=self.now,
        )
        self.assertEqual("inactive", inactive["status"])

    def test_replay_does_not_move_bound_effect_to_another_target(self):
        self.aim("one")
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "expose-bound", now=self.now)
        self.aim("two")
        before = self.targets.get("echo")
        replay = service.activate_player_ability(self.player, "expose-bound", now=self.now)
        after = self.targets.get("echo")
        self.assertEqual("replayed", replay["status"])
        self.assertEqual(before["version"], after["version"])
        self.assertTrue(any(
            value is True for value in after["security"].values()
            if isinstance(value, bool)
        ))

    def test_presentation_and_runtime_path_are_lightweight(self):
        service = GhostNetworkService(repository=self.repo)
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        self.assertTrue(snapshot["available"])
        self.assertEqual("Ujawnienie", snapshot["presentation"]["display_name"])
        self.assertEqual("SŁABOŚĆ UJAWNIONA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("target_security_bar", snapshot["presentation"]["impact_ui"])
        self.assertIn("e1_breach_voice", snapshot["presentation"]["visual_asset_url"])

        source = inspect.getsource(__import__("run").apply_active_ghostnetwork_ability_to_aimed_target)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)

        self.aim()
        token = reset_hot_path_metrics()
        try:
            activated = service.activate_player_ability(
                self.player, "expose-light", now=self.now,
            )
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        self.assertTrue(activated["ok"])
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
