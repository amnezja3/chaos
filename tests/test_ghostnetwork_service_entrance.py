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


class GhostNetworkServiceEntranceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(
            db_path=self.db_path, clock=lambda: self.now,
        )
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V2"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-v2",
            latitude=52.2, longitude=21.0, discovered_by="architect",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v2",
            territory_owner_id="architect", territory_clan="virex",
            activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.player = {
            "username": "architect", "player_id": "architect",
            "clan": "virex", "profession": "architect", "level": 71,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("insider_feed", "service_entrance"),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def aim(self, suffix="one"):
        return self.targets.upsert_aimed("architect", {
            "target_id": f"map:52.1:21.{1 if suffix == 'one' else 2}:TARGET-{suffix}",
            "lat": 52.1,
            "lng": 21.1 if suffix == "one" else 21.2,
            "label": f"TARGET-{suffix}",
            "actions_allowed": {
                "scan_ports": False,
                "exploit": False,
                "sniff": False,
                "trace": False,
            },
            "security": {
                "firewall": True,
                "ids": True,
                "vpn": False,
            },
        })

    def test_activation_requires_selected_target_without_consuming_window(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "service-no-target", now=self.now,
        )

        self.assertFalse(result["ok"])
        self.assertEqual("target_unavailable", result["status"])
        self.assertEqual("select_target_before_activation", result["reason"])
        self.assertEqual("Najpierw oznacz cel na mapie.", result["message"])
        self.assertIsNone(self.repo.get_latest_ability_window("architect"))

    def test_activation_completes_four_actions_and_preserves_security(self):
        aimed = self.aim()
        before = self.targets.get("architect")
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(
            self.player, "service-actions", now=self.now,
        )
        after = self.targets.get("architect")

        self.assertTrue(result["ok"])
        self.assertEqual("activated", result["status"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(1, result["realizer"]["applied_targets"])
        self.assertEqual(4, result["realizer"]["applied_changes"])
        self.assertEqual(before["security"], after["security"])
        self.assertTrue(all(
            after["actions_allowed"].get(key) is True
            for key in ("scan_ports", "exploit", "sniff", "trace")
        ))
        markers = after["target"].get("ability_application_keys") or []
        self.assertEqual(1, len(markers))
        self.assertTrue(markers[0].endswith(":actions"))
        self.assertEqual(aimed["target"]["target_id"], result["window"]["target_id"])

        first_version = after["version"]
        replay = service.activate_player_ability(
            self.player, "service-actions", now=self.now,
        )
        self.assertEqual("replayed", replay["status"])
        self.assertEqual(first_version, self.targets.get("architect")["version"])

    def test_replay_never_moves_bound_effect_to_another_target(self):
        self.aim("one")
        service = GhostNetworkService(repository=self.repo)
        first = service.activate_player_ability(
            self.player, "service-bound", now=self.now,
        )
        self.assertTrue(first["ok"])

        self.aim("two")
        second_before = self.targets.get("architect")
        replay = service.activate_player_ability(
            self.player, "service-bound", now=self.now,
        )
        second_after = self.targets.get("architect")

        self.assertEqual("replayed", replay["status"])
        self.assertEqual(second_before["version"], second_after["version"])
        self.assertFalse(any(second_after["actions_allowed"].values()))
        self.assertEqual([], second_after["target"].get("ability_application_keys") or [])

    def test_v2_presentation_uses_shared_superpower_contract(self):
        snapshot = GhostNetworkService(
            repository=self.repo,
        ).get_player_ability_window_snapshot(self.player, now=self.now)

        self.assertTrue(snapshot["available"])
        self.assertEqual("Wejście Serwisowe", snapshot["presentation"]["display_name"])
        self.assertEqual("BACKDOOR GOTOWY", snapshot["presentation"]["activation_tagline"])
        self.assertEqual(
            "/static/images/ghostnetwork/superpower/v2_backdoor_forge.png",
            snapshot["presentation"]["visual_asset_url"],
        )
        self.assertEqual(6000, snapshot["presentation"]["show_duration_ms"])

    def test_activation_path_has_zero_heavy_profile_activity(self):
        self.aim()
        token = reset_hot_path_metrics()
        try:
            result = GhostNetworkService(repository=self.repo).activate_player_ability(
                self.player, "service-light", now=self.now,
            )
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)

        self.assertTrue(result["ok"])
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
