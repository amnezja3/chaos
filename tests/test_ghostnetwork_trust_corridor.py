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
from ghostnetwork.ability_realizers import OPERATION_RISK_POLICIES, operation_risk_modifier


class GhostNetworkTrustCorridorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "S4"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-s4",
            latitude=52.2, longitude=21.0, discovered_by="sentinel",
            discovered_clan="sentinel_order", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-s4", territory_owner_id="sentinel",
            territory_clan="sentinel_order", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "sentinel", "player_id": "sentinel",
            "clan": "sentinel_order", "profession": "mediator", "level": 68,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("trust_corridor",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def operation(self, operation_id="op-s4"):
        return {
            "operation_id": operation_id,
            "owner_username": "sentinel",
            "target_id": f"target-{operation_id}",
            "operation_type": "persistent_sniffer",
            "target": {"security": {}},
            "target_mode": "ordinary",
            "status": "running",
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "duration_seconds": 3600,
        }

    def test_activation_masks_existing_operations_and_uses_s4_presentation(self):
        self.operations.upsert_operations(
            "sentinel", [self.operation("op-a"), self.operation("op-b")],
        )
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(
            self.player, "trust-existing", now=self.now,
        )
        rows = self.operations.list_active_operations("sentinel", limit=8)
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(2, result["realizer"]["applied_operations"])
        self.assertEqual({-15}, {
            row["operation_risk_meter"]["ability_heat_modifier"] for row in rows
        })
        self.assertTrue(all(
            row["ability_provenance"]["ability_code"] == "trust_corridor"
            for row in rows
        ))
        self.assertEqual("Korytarz Zaufania", snapshot["presentation"]["display_name"])
        self.assertEqual(
            "PRZEJŚCIE ZABEZPIECZONE",
            snapshot["presentation"]["activation_tagline"],
        )
        self.assertEqual("operation_risk", snapshot["presentation"]["impact_ui"])
        self.assertIn("s4_accord_relay", snapshot["presentation"]["visual_asset_url"])

    def test_new_operation_tick_rules_and_replay_use_same_policy_once(self):
        import run

        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "trust-new", now=self.now)
        operation = self.operation("op-new")

        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))
        self.assertEqual(-15, operation["operation_risk_meter"]["ability_heat_modifier"])
        self.assertEqual("trust_corridor", operation["ability_provenance"]["ability_code"])
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

    def test_s4_has_an_independent_bounded_policy(self):
        for ability_code in ("false_image", "narrative_takeover", "phantom_node"):
            self.assertIsNot(
                OPERATION_RISK_POLICIES[ability_code],
                OPERATION_RISK_POLICIES["trust_corridor"],
            )
        self.assertEqual(-15, operation_risk_modifier("trust_corridor"))

    def test_expiry_and_part_loss_stop_modifier(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "trust-stop", now=self.now)
        self.assertEqual({}, service.active_operation_risk_rules(
            self.player, now=self.now + timedelta(minutes=16),
        ))
        self.repo.update_part(self.part["part_id"], status="public")
        self.assertEqual({}, service.active_operation_risk_rules(self.player, now=self.now))

    def test_runtime_path_records_zero_heavy_profile_activity(self):
        self.operations.upsert_operations("sentinel", [self.operation()])
        service = GhostNetworkService(repository=self.repo)
        token = reset_hot_path_metrics()
        try:
            result = service.activate_player_ability(
                self.player, "trust-light", now=self.now,
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
