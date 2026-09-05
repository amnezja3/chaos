import inspect
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
from ghostnetwork.ability_realizers import GhostAbilityProductionRealizer


class GhostNetworkInsiderFeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V1"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-v1",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v1", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "broker", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def operation(self, operation_id="op-1", minutes=10):
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

    def test_activation_shortens_existing_operations_exactly_once(self):
        self.operations.upsert_operations("alice", [self.operation()])
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(self.player, "insider-existing", now=self.now)
        shortened = self.operations.list_active_operations("alice", limit=8)[0]
        first_expiry = shortened["expires_at"]

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["realizer"]["status"])
        self.assertEqual(1, result["realizer"]["applied_operations"])
        self.assertNotIn("persisted", result["realizer"])
        self.assertNotIn("factor", result["realizer"])
        self.assertEqual(85, shortened["remaining_seconds"])
        self.assertEqual(1, len(shortened["ability_application_keys"]))

        replay = service.activate_player_ability(self.player, "insider-existing", now=self.now)
        self.assertEqual("replayed", replay["status"])
        self.assertEqual(
            first_expiry,
            self.operations.list_active_operations("alice", limit=8)[0]["expires_at"],
        )

    def test_replay_recovers_window_created_before_effect_application(self):
        self.operations.upsert_operations("alice", [self.operation()])
        window_only = GhostNetworkService(
            repository=self.repo, ability_production_realizer=False,
        )
        first = window_only.activate_player_ability(self.player, "recover-effect", now=self.now)
        unchanged = self.operations.list_active_operations("alice", limit=8)[0]
        self.assertEqual(600, unchanged["duration_seconds"])

        recovered = GhostNetworkService(repository=self.repo).activate_player_ability(
            self.player, "recover-effect", now=self.now,
        )
        changed = self.operations.list_active_operations("alice", limit=8)[0]
        self.assertEqual("replayed", recovered["status"])
        self.assertEqual(85, changed["remaining_seconds"])
        self.assertEqual(first["window"]["window_id"], recovered["window"]["window_id"])

    def test_transient_operation_cas_conflict_is_retried_once(self):
        self.operations.upsert_operations("alice", [self.operation()])
        window = GhostNetworkService(
            repository=self.repo, ability_production_realizer=False,
        ).activate_player_ability(self.player, "transient-cas", now=self.now)["window"]

        class TransientConflictStore:
            def __init__(self, delegate):
                self.delegate = delegate
                self.cas_calls = 0

            def list_active_operations(self, username, limit):
                return self.delegate.list_active_operations(username, limit=limit)

            def compare_and_swap_runtime(self, *args, **kwargs):
                self.cas_calls += 1
                if self.cas_calls == 1:
                    return []
                return self.delegate.compare_and_swap_runtime(*args, **kwargs)

        store = TransientConflictStore(self.operations)
        result = GhostAbilityProductionRealizer(store).apply_activation("alice", window)
        shortened = self.operations.list_active_operations("alice", limit=8)[0]

        self.assertTrue(result["ok"])
        self.assertEqual("applied", result["status"])
        self.assertEqual(2, store.cas_calls)
        self.assertEqual(85, shortened["remaining_seconds"])
        self.assertEqual(1, len(shortened["ability_application_keys"]))

    def test_new_operation_started_inside_window_gets_same_factor(self):
        service = GhostNetworkService(repository=self.repo)
        activation = service.activate_player_ability(self.player, "insider-new", now=self.now)
        operation = self.operation("op-new", minutes=10)

        changed = service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        )

        self.assertTrue(changed)
        self.assertEqual(85, operation["duration_seconds"])
        self.assertEqual("operation_speed", operation["ability_provenance"]["family"])
        self.assertEqual(
            activation["window"]["window_id"],
            operation["ability_provenance"]["window_id"],
        )
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))

    def test_unbounded_level_is_capped_for_new_operations(self):
        self.player["level"] = 9999
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "insider-cap", now=self.now)
        operation = self.operation("op-cap", minutes=20)

        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, operation, now=self.now,
        ))
        self.assertEqual(60, operation["duration_seconds"])
        self.assertEqual(20.0, operation["ability_provenance"]["factor"])

    def test_expired_window_and_part_loss_do_not_modify_new_operation(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "insider-expiry", now=self.now)
        self.now += timedelta(minutes=16)
        expired = self.operation("op-expired")
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, expired, now=self.now,
        ))

        self.now -= timedelta(minutes=16)
        self.repo.update_part(self.part["part_id"], status="public")
        lost = self.operation("op-lost")
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, lost, now=self.now,
        ))

    def test_production_mapping_is_frozen_and_runtime_hook_is_lightweight(self):
        self.assertEqual(
            {
                "insider_feed": "operation_speed",
                "service_entrance": "hack_actions",
                "false_image": "operation_risk",
                "hostile_takeover": "file_yield",
            },
            GhostAbilityProductionRealizer.ABILITY_FAMILIES,
        )
        import run
        source = inspect.getsource(run.apply_active_ghostnetwork_ability_to_new_operation)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)

        operation = self.operation("op-run-hook")
        fake_service = unittest.mock.Mock()
        fake_service.apply_active_ability_to_new_operation.return_value = True
        with patch.object(run, "GHOSTNETWORK_ABILITIES_ENABLED", True), patch.object(
            run.identity_projection_store, "get_identity",
            return_value={"username": "alice", "clan_code": "virex", "profession_code": "broker"},
        ), patch.object(
            run.capability_projection_store, "get_capabilities",
            return_value={"username": "alice", "level": 71, "action_range": 2528, "map_zoom": 18},
        ), patch.object(run, "get_ghostnetwork_service", return_value=fake_service):
            self.assertTrue(run.apply_active_ghostnetwork_ability_to_new_operation(
                "alice", operation, now=self.now,
            ))
        fake_service.apply_active_ability_to_new_operation.assert_called_once()

    def test_production_paths_record_zero_heavy_profile_activity(self):
        self.operations.upsert_operations("alice", [self.operation()])
        service = GhostNetworkService(repository=self.repo)
        token = reset_hot_path_metrics()
        try:
            activation = service.activate_player_ability(
                self.player, "insider-light", now=self.now,
            )
            new_operation = self.operation("op-light-new")
            changed = service.apply_active_ability_to_new_operation(
                self.player, new_operation, now=self.now,
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
