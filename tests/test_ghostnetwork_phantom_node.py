import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import (
    PlayerOperationStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    OPERATION_RISK_POLICIES,
    operation_risk_modifier,
)


class GhostNetworkPhantomNodeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "P1"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-p1",
            latitude=52.2, longitude=21.0, discovered_by="phantom",
            discovered_clan="phantom_mesh", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-p1", territory_owner_id="phantom",
            territory_clan="phantom_mesh", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "phantom", "player_id": "phantom",
            "clan": "phantom_mesh", "profession": "illusionist", "level": 64,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("phantom_node",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def operation(self, operation_id="op-p1"):
        return {
            "operation_id": operation_id,
            "owner_username": "phantom",
            "target_id": f"target-{operation_id}",
            "operation_type": "persistent_sniffer",
            "target": {"security": {}},
            "target_mode": "ordinary",
            "status": "running",
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "duration_seconds": 3600,
        }

    def test_activation_masks_existing_operations_and_uses_p1_presentation(self):
        self.operations.upsert_operations(
            "phantom", [self.operation("op-a"), self.operation("op-b")],
        )
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "phantom-existing", now=self.now,
        )
        rows = self.operations.list_active_operations("phantom", limit=8)
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(2, result["realizer"]["applied_operations"])
        self.assertEqual({-15}, {
            row["operation_risk_meter"]["ability_heat_modifier"] for row in rows
        })
        self.assertTrue(all(
            row["ability_provenance"]["ability_code"] == "phantom_node"
            for row in rows
        ))
        self.assertEqual("Węzeł Widmo", snapshot["presentation"]["display_name"])
        self.assertEqual("RUCH POZORNY", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("operation_risk", snapshot["presentation"]["impact_ui"])
        self.assertIn("p1_mirage_projector", snapshot["presentation"]["visual_asset_url"])

    def test_new_operation_and_tick_rules_use_same_policy_once(self):
        import run

        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "phantom-new", now=self.now)
        operation = self.operation("op-new")

        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))
        self.assertEqual(-15, operation["operation_risk_meter"]["ability_heat_modifier"])
        self.assertEqual("phantom_node", operation["ability_provenance"]["ability_code"])
        self.assertEqual(
            {"ability_heat_modifier": -15},
            service.active_operation_risk_rules(self.player, now=self.now),
        )
        self.assertEqual(
            {"ability_heat_modifier": -15},
            run.embedded_ghostnetwork_operation_risk_rules(operation),
        )
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))
        self.assertEqual(1, len(operation["ability_application_keys"]))

    def test_p1_has_an_independent_bounded_policy(self):
        self.assertIsNot(
            OPERATION_RISK_POLICIES["false_image"],
            OPERATION_RISK_POLICIES["phantom_node"],
        )
        self.assertIsNot(
            OPERATION_RISK_POLICIES["narrative_takeover"],
            OPERATION_RISK_POLICIES["phantom_node"],
        )
        self.assertEqual(-15, operation_risk_modifier("phantom_node"))

    def test_expiry_and_part_loss_stop_modifier(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "phantom-stop", now=self.now)
        self.assertEqual({}, service.active_operation_risk_rules(
            self.player, now=self.now + timedelta(minutes=16),
        ))
        self.repo.update_part(self.part["part_id"], status="public")
        self.assertEqual({}, service.active_operation_risk_rules(self.player, now=self.now))

    def test_runtime_path_records_zero_heavy_profile_activity(self):
        self.operations.upsert_operations("phantom", [self.operation()])
        service = GhostNetworkService(repository=self.repo)
        token = reset_hot_path_metrics()
        try:
            result = service.activate_player_ability(
                self.player, "phantom-light", now=self.now,
            )
            rules = service.active_operation_risk_rules(self.player, now=self.now)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        self.assertTrue(result["ok"])
        self.assertEqual({"ability_heat_modifier": -15}, rules)
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
