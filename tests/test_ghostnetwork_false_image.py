import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import PlayerOperationStore, get_hot_path_metrics, reset_hot_path_metrics, restore_hot_path_metrics
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import GhostAbilityProductionRealizer


class GhostNetworkFalseImageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V3"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-v3",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v3", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "manipulator", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def operation(self, operation_id="op-mask"):
        return {
            "operation_id": operation_id,
            "owner_username": "alice",
            "target_id": f"target-{operation_id}",
            "operation_type": "persistent_sniffer",
            "target": {"security": {}},
            "target_mode": "ordinary",
            "status": "running",
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "duration_seconds": 3600,
        }

    def test_activation_masks_all_existing_operations_and_presentation(self):
        self.operations.upsert_operations(
            "alice", [self.operation("op-a"), self.operation("op-b")],
        )
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(self.player, "false-image", now=self.now)
        rows = self.operations.list_active_operations("alice", limit=8)

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(2, result["realizer"]["applied_operations"])
        self.assertEqual({-15}, {
            row["operation_risk_meter"]["ability_heat_modifier"] for row in rows
        })
        self.assertTrue(all(
            len(row.get("ability_application_keys") or []) == 1 for row in rows
        ))
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        self.assertEqual("Fałszywy Obraz", snapshot["presentation"]["display_name"])
        self.assertEqual("NIE WIERZ OCZOM", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("operation_risk", snapshot["presentation"]["impact_ui"])
        self.assertIn("v3_mimicry_engine.png", snapshot["presentation"]["visual_asset_url"])

    def test_new_operation_and_active_rules_use_same_bounded_modifier(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "false-image-new", now=self.now)
        operation = self.operation("op-new")

        changed = service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        )

        self.assertTrue(changed)
        self.assertEqual(-15, operation["operation_risk_meter"]["ability_heat_modifier"])
        self.assertEqual(
            {"ability_heat_modifier": -15},
            service.active_operation_risk_rules(self.player, now=self.now),
        )
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))
        self.assertEqual(1, len(operation["ability_application_keys"]))

    def test_canonical_operation_builder_keeps_new_operation_masked(self):
        import run

        window = GhostNetworkService(repository=self.repo).activate_player_ability(
            self.player, "false-image-builder", now=self.now,
        )["window"]
        fake_service = unittest.mock.Mock()
        fake_service.apply_active_ability_to_new_operation.side_effect = (
            lambda _context, operation, now=None:
            GhostAbilityProductionRealizer._apply_operation_risk_to_row(
                operation, window, now=now,
            )
        )
        with patch.object(run, "GHOSTNETWORK_ABILITIES_ENABLED", True), patch.object(
            run.identity_projection_store, "get_identity",
            return_value={"username": "alice", "clan_code": "virex", "profession_code": "manipulator"},
        ), patch.object(
            run.capability_projection_store, "get_capabilities",
            return_value={"username": "alice", "level": 71},
        ), patch.object(run, "get_ghostnetwork_service", return_value=fake_service):
            operation = run.build_operation_instance(
                "alice",
                {"id": "snfx", "name": "Snfx", "quality_score": 50, "reliability": 70},
                "sniff", "persistent_sniffer", {"security": {}},
            )
        self.assertEqual(-15, operation["operation_risk_meter"]["ability_heat_modifier"])

    def test_rules_stop_after_expiry_or_part_loss(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "false-image-stop", now=self.now)

        self.now += timedelta(minutes=16)
        self.assertEqual({}, service.active_operation_risk_rules(self.player, now=self.now))

        self.now -= timedelta(minutes=16)
        self.repo.update_part(self.part["part_id"], status="public")
        self.assertEqual({}, service.active_operation_risk_rules(self.player, now=self.now))

    def test_runtime_tick_reads_ability_once_per_player_and_clears_expired_modifier(self):
        import run

        operation = self.operation("op-tick")
        self.operations.upsert_operations("alice", [operation])
        original_store = run.player_operation_store
        run.player_operation_store = self.operations
        try:
            with patch.object(
                run, "active_ghostnetwork_operation_risk_rules",
                return_value={"ability_heat_modifier": -15},
            ) as rules, patch.object(
                self.operations, "list_runtime_usernames", return_value=["alice"],
            ), patch.object(
                run.incident_initializer, "sync_operations", return_value={"actions": []},
            ), patch.object(run, "sync_response_warnings", return_value=[]):
                run.process_operation_runtime_tick(
                    limit_users=1, min_age_seconds=0, now_ts=self.now.timestamp() + 2,
                )
            self.assertEqual(1, rules.call_count)
            masked = self.operations.list_active_operations("alice", limit=8)[0]
            self.assertEqual(-15, masked["operation_risk_meter"]["ability_heat_modifier"])

            with patch.object(
                run, "active_ghostnetwork_operation_risk_rules", return_value={},
            ), patch.object(
                self.operations, "list_runtime_usernames", return_value=["alice"],
            ), patch.object(
                run.incident_initializer, "sync_operations", return_value={"actions": []},
            ), patch.object(run, "sync_response_warnings", return_value=[]):
                run.process_operation_runtime_tick(
                    limit_users=1, min_age_seconds=0, now_ts=self.now.timestamp() + 4,
                )
            unmasked = self.operations.list_active_operations("alice", limit=8)[0]
            self.assertEqual(0, unmasked["operation_risk_meter"]["ability_heat_modifier"])
        finally:
            run.player_operation_store = original_store

    def test_runtime_hook_is_lightweight(self):
        import run

        source = inspect.getsource(run.active_ghostnetwork_operation_risk_rules)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)

        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "false-image-light", now=self.now)
        token = reset_hot_path_metrics()
        try:
            rules = service.active_operation_risk_rules(self.player, now=self.now)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        self.assertEqual({"ability_heat_modifier": -15}, rules)
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
