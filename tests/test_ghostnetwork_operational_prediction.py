import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from database import (
    PlayerOperationStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    MAX_OPERATION_SPEED_FACTOR,
    OPERATION_SPEED_POLICIES,
    calculate_operation_speed_factor,
)


class GhostNetworkOperationalPredictionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V5"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-v5",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v5", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "algorithm_curator", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def operation(self, operation_id="op-v5", minutes=10):
        return {
            "operation_id": operation_id,
            "owner_username": "alice",
            "target_id": f"target-{operation_id}",
            "operation_type": "generic_trace",
            "status": "running",
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(minutes=minutes)).isoformat(),
            "duration_seconds": minutes * 60,
        }

    def test_activation_and_new_operation_use_v5_policy_once(self):
        self.operations.upsert_operations("alice", [self.operation("existing")])
        service = GhostNetworkService(repository=self.repo)
        activation = service.activate_player_ability(
            self.player, "prediction-existing", now=self.now,
        )
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)
        existing = self.operations.list_active_operations("alice", limit=8)[0]

        self.assertTrue(activation["ok"])
        self.assertEqual(
            "Predykcja Operacyjna", snapshot["presentation"]["display_name"],
        )
        self.assertEqual(
            "CZAS OBLICZONY", snapshot["presentation"]["activation_tagline"],
        )
        self.assertIn("v5_probability_core", snapshot["presentation"]["visual_asset_url"])
        self.assertEqual(85, existing["remaining_seconds"])
        self.assertEqual(
            "operational_prediction",
            existing["operation_speed_provenance"]["ability_code"],
        )

        new_operation = self.operation("new")
        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, new_operation, now=self.now,
        ))
        self.assertEqual(85, new_operation["duration_seconds"])
        self.assertEqual(
            "operational_prediction",
            new_operation["ability_provenance"]["ability_code"],
        )
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, new_operation, now=self.now,
        ))

    def test_v5_is_bounded_to_eight_operations_and_has_cooldown(self):
        self.operations.upsert_operations(
            "alice", [self.operation(f"op-{index}") for index in range(9)],
        )
        service = GhostNetworkService(repository=self.repo)
        activation = service.activate_player_ability(
            self.player, "prediction-bounded", now=self.now,
        )
        changed = [
            operation for operation in self.operations.list_active_operations(
                "alice", limit=20,
            )
            if operation.get("ability_application_keys")
        ]
        self.assertTrue(activation["ok"])
        self.assertEqual(8, len(changed))

        self.now += timedelta(minutes=16)
        cooldown = service.activate_player_ability(
            self.player, "prediction-during-cooldown", now=self.now,
        )
        self.assertFalse(cooldown["ok"])
        self.assertEqual("cooldown", cooldown["status"])

    def test_replay_expiry_and_part_loss_are_fail_closed(self):
        self.operations.upsert_operations("alice", [self.operation()])
        service = GhostNetworkService(repository=self.repo)
        first = service.activate_player_ability(self.player, "prediction-replay", now=self.now)
        first_expiry = self.operations.list_active_operations("alice", limit=8)[0]["expires_at"]
        replay = service.activate_player_ability(self.player, "prediction-replay", now=self.now)
        self.assertEqual("replayed", replay["status"])
        self.assertEqual(
            first["window"]["window_id"], replay["window"]["window_id"],
        )
        self.assertEqual(
            first_expiry,
            self.operations.list_active_operations("alice", limit=8)[0]["expires_at"],
        )

        self.now += timedelta(minutes=16)
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, self.operation("expired"), now=self.now,
        ))
        self.now -= timedelta(minutes=16)
        self.repo.update_part(self.part["part_id"], status="public")
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, self.operation("lost"), now=self.now,
        ))

    def test_v1_and_v5_policies_are_independent_and_capped(self):
        self.assertIsNot(
            OPERATION_SPEED_POLICIES["insider_feed"],
            OPERATION_SPEED_POLICIES["operational_prediction"],
        )
        self.assertAlmostEqual(7.1, calculate_operation_speed_factor(71, "insider_feed"))
        self.assertAlmostEqual(
            7.1, calculate_operation_speed_factor(71, "operational_prediction"),
        )
        self.assertEqual(
            MAX_OPERATION_SPEED_FACTOR,
            calculate_operation_speed_factor(9999, "operational_prediction"),
        )

    def test_production_path_records_zero_heavy_profile_activity(self):
        self.operations.upsert_operations("alice", [self.operation()])
        service = GhostNetworkService(repository=self.repo)
        token = reset_hot_path_metrics()
        try:
            activation = service.activate_player_ability(
                self.player, "prediction-light", now=self.now,
            )
            changed = service.apply_active_ability_to_new_operation(
                self.player, self.operation("new-light"), now=self.now,
            )
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        self.assertTrue(activation["ok"])
        self.assertTrue(changed)
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
