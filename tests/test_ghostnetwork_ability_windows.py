import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService


class GhostAbilityWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(
            db_path=self.db_path, clock=lambda: self.now,
        )
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(self.cycle["cycle_id"])
            if item["part_code"] == "V1"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-v1",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v1", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.service = GhostNetworkService(repository=self.repo)
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "broker", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_activation_is_durable_idempotent_and_has_cooldown(self):
        first = self.service.activate_player_ability(self.player, "request-1")
        self.assertTrue(first["ok"])
        self.assertEqual("activated", first["status"])
        self.assertEqual(71, first["window"]["level_snapshot"])

        replay = self.service.activate_player_ability(self.player, "request-1")
        self.assertTrue(replay["ok"])
        self.assertEqual("replayed", replay["status"])
        self.assertEqual(first["window"]["window_id"], replay["window"]["window_id"])

        duplicate = self.service.activate_player_ability(self.player, "request-2")
        self.assertFalse(duplicate["ok"])
        self.assertEqual("already_active", duplicate["status"])
        snapshot = self.service.get_player_ability_window_snapshot(self.player)
        self.assertTrue(snapshot["active"])
        self.assertEqual("ghost-clan-virex", snapshot["presentation"]["clan_color_token"])
        self.assertEqual(
            "/static/images/ghostnetwork/superpower/v1_ledger_nexus.png",
            snapshot["presentation"]["visual_asset_url"],
        )
        self.assertEqual(
            "/static/images/ghostnetwork/parts/v1_ledger_nexus.png",
            snapshot["presentation"]["timer_asset_url"],
        )
        self.assertEqual(6000, snapshot["presentation"]["show_duration_ms"])
        self.assertEqual(
            "ghostnetwork.part_activated",
            snapshot["presentation"]["sound_event"],
        )
        self.assertEqual(560, snapshot["presentation"]["visual_asset_max_px"])
        self.assertEqual(52, snapshot["presentation"]["visual_asset_padding_px"])
        self.assertEqual("shake", snapshot["presentation"]["visual_asset_motion"])
        self.assertEqual("Insider Feed", snapshot["presentation"]["display_name"])
        self.assertEqual("MEGA HOSSA", snapshot["presentation"]["activation_tagline"])
        self.assertTrue(snapshot["presentation"]["semantic_description"])

        self.now += timedelta(minutes=16)
        cooldown = self.service.activate_player_ability(self.player, "request-3")
        self.assertFalse(cooldown["ok"])
        self.assertEqual("cooldown", cooldown["status"])

        self.now += timedelta(minutes=45)
        second = self.service.activate_player_ability(self.player, "request-4")
        self.assertTrue(second["ok"])
        self.assertEqual("activated", second["status"])

    def test_part_loss_terminates_effect_without_deleting_window(self):
        activated = self.service.activate_player_ability(self.player, "request-loss")
        self.repo.update_part(self.part["part_id"], status="public")
        replay = self.service.activate_player_ability(self.player, "request-loss")
        self.assertTrue(replay["ok"])
        self.assertEqual("replayed", replay["status"])
        snapshot = self.service.get_player_ability_window_snapshot(self.player)
        self.assertFalse(snapshot["active"])
        self.assertTrue(snapshot["cooldown"])
        self.assertEqual(activated["window"]["window_id"], snapshot["window"]["window_id"])

        self.now += timedelta(seconds=1)
        self.repo.update_part(
            self.part["part_id"], status="active",
            last_activated_at=self.now.isoformat(),
        )
        resurrected = self.service.get_player_ability_window_snapshot(self.player)
        self.assertFalse(resurrected["active"])
        self.assertTrue(resurrected["cooldown"])

    def test_unrelated_world_version_does_not_terminate_active_window(self):
        activated = self.service.activate_player_ability(self.player, "request-world")
        other = next(
            item for item in self.repo.list_parts(self.cycle["cycle_id"])
            if item["part_code"] == "E1"
        )
        self.repo.update_part(other["part_id"], source_state="unrelated-change")

        snapshot = self.service.get_player_ability_window_snapshot(self.player)
        self.assertTrue(snapshot["active"])
        self.assertEqual(activated["window"]["window_id"], snapshot["window"]["window_id"])

    def test_client_cannot_choose_realizer_contract(self):
        import inspect
        import run

        source = inspect.getsource(run.api_ghostnetwork_ability)
        for field in ("realizer", "family", "multiplier", "parameters"):
            self.assertIn(f'"{field}"', source)

    def test_non_allowlisted_catalog_ability_fails_closed(self):
        with patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES", tuple()
        ):
            snapshot = self.service.get_player_ability_window_snapshot(self.player)
            self.assertFalse(snapshot["available"])
            self.assertEqual("realizer_unavailable", snapshot["reason"])
            activation = self.service.activate_player_ability(self.player, "blocked")
            self.assertFalse(activation["ok"])
            self.assertEqual("realizer_unavailable", activation["status"])

    def test_ability_telemetry_is_bounded_aggregate_without_player_payload(self):
        first = self.service.activate_player_ability(self.player, "metrics-1")
        self.assertTrue(first["ok"])
        self.service.activate_player_ability(self.player, "metrics-1")
        self.service.activate_player_ability(self.player, "metrics-2")

        summary = self.repo.get_ability_telemetry_summary(self.cycle["cycle_id"])
        outcomes = {
            (item["phase"], item["outcome"]): item["count"]
            for item in summary["metrics"]
        }
        self.assertEqual(1, outcomes[("activation", "activated")])
        self.assertEqual(1, outcomes[("activation", "replayed")])
        self.assertEqual(1, outcomes[("activation", "already_active")])
        self.assertGreaterEqual(outcomes[("realizer", "no_active_operations")], 2)
        self.assertEqual("ghostnetwork-ability-telemetry-v1", summary["contract_version"])

        with self.repo._conn() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(ghost_ability_telemetry)")
            }
        self.assertNotIn("player_id", columns)
        self.assertNotIn("payload_json", columns)


if __name__ == "__main__":
    unittest.main()
