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
from ghostnetwork.ability_realizers import (
    TARGET_SECURITY_POLICIES,
    target_security_max_changes,
)


class GhostNetworkGlitchInjectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 7, 14, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "P2"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-p2",
            latitude=52.2, longitude=21.0, discovered_by="virus",
            discovered_clan="phantom_mesh", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-p2", territory_owner_id="virus",
            territory_clan="phantom_mesh", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.player = {
            "username": "virus", "player_id": "virus",
            "clan": "phantom_mesh", "profession": "virologist", "level": 64,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("glitch_injection",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def aim(self, suffix="one"):
        longitude = 21.1 if suffix == "one" else 21.2
        return self.targets.upsert_aimed("virus", {
            "target_id": f"map:52.1:{longitude}:P2-{suffix}",
            "lat": 52.1,
            "lng": longitude,
            "label": f"P2-{suffix}",
            "actions_allowed": {
                "scan_ports": False, "exploit": False,
                "sniff": False, "trace": False,
            },
            "security": {
                "firewall": True, "ids": True, "process_monitor": True,
                "vpn": False, "security_level": 4,
            },
        })

    def assert_two_security_flags_disabled(self, target):
        booleans = {
            key: value for key, value in target["security"].items()
            if isinstance(value, bool)
        }
        self.assertEqual(1, sum(value is True for value in booleans.values()))
        self.assertEqual(3, sum(value is False for value in booleans.values()))
        self.assertTrue(all(value is False for value in target["actions_allowed"].values()))
        self.assertEqual(4, target["security"]["security_level"])

    def test_activation_disables_at_most_two_security_flags(self):
        aimed = self.aim()
        result = GhostNetworkService(repository=self.repo).activate_player_ability(
            self.player, "glitch-now", now=self.now,
        )
        after = self.targets.get("virus")

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(2, result["realizer"]["applied_changes"])
        self.assert_two_security_flags_disabled(after)
        self.assertEqual(aimed["target"]["target_id"], result["window"]["target_id"])

    def test_every_new_aimed_target_gets_same_bounded_effect_once(self):
        service = GhostNetworkService(repository=self.repo)
        activated = service.activate_player_ability(
            self.player, "glitch-window", now=self.now,
        )
        self.assertEqual("no_selected_target", activated["realizer"]["status"])

        for suffix in ("one", "two"):
            aimed = self.aim(suffix)
            first = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            after = self.targets.get("virus")
            self.assertEqual("applied", first["status"])
            self.assertEqual(2, len(first["changed"]))
            self.assert_two_security_flags_disabled(after)
            version = after["version"]
            replay = service.apply_active_ability_to_aimed_target(
                self.player, aimed["target"]["target_id"], now=self.now,
            )
            self.assertEqual("replayed", replay["status"])
            self.assertEqual(version, self.targets.get("virus")["version"])

    def test_p2_policy_is_independent_from_full_bar_variants(self):
        self.assertIsNot(
            TARGET_SECURITY_POLICIES["expose"],
            TARGET_SECURITY_POLICIES["glitch_injection"],
        )
        self.assertIsNone(target_security_max_changes("expose"))
        self.assertIsNone(target_security_max_changes("domino_effect"))
        self.assertEqual(2, target_security_max_changes("glitch_injection"))

    def test_expiry_and_part_loss_stop_future_targets(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "glitch-stop", now=self.now)
        aimed = self.aim()
        expired = service.apply_active_ability_to_aimed_target(
            self.player, aimed["target"]["target_id"],
            now=self.now + timedelta(minutes=16),
        )
        self.assertEqual("inactive", expired["status"])
        self.assertEqual(3, sum(
            value is True for value in self.targets.get("virus")["security"].values()
            if isinstance(value, bool)
        ))

        self.repo.update_part(self.part["part_id"], status="public")
        inactive = service.apply_active_ability_to_aimed_target(
            self.player, aimed["target"]["target_id"], now=self.now,
        )
        self.assertEqual("inactive", inactive["status"])

    def test_presentation_and_runtime_path_are_lightweight(self):
        service = GhostNetworkService(repository=self.repo)
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        self.assertTrue(snapshot["available"])
        self.assertEqual("Glitch Injection", snapshot["presentation"]["display_name"])
        self.assertEqual("SYSTEM PĘKA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("target_security_bar", snapshot["presentation"]["impact_ui"])
        self.assertIn("p2_glitch_reactor", snapshot["presentation"]["visual_asset_url"])

        import run
        source = inspect.getsource(run.apply_active_ghostnetwork_ability_to_aimed_target)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)

        self.aim()
        token = reset_hot_path_metrics()
        try:
            activated = service.activate_player_ability(
                self.player, "glitch-light", now=self.now,
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
