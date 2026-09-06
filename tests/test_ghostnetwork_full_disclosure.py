import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import (
    PlayerInventoryStore,
    PlayerOperationStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    DATA_QUALITY_POLICIES,
    GhostAbilityProductionRealizer,
    enhance_data_quality_files,
)


class GhostNetworkFullDisclosureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 6, 20, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "E3"
        )
        self.part = self.repo.update_part(
            part["part_id"], status="active", target_id="target-e3",
            latitude=52.2, longitude=21.0, discovered_by="echo",
            discovered_clan="echo_freedom", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-e3", territory_owner_id="echo",
            territory_clan="echo_freedom", activated_at=self.now.isoformat(),
            last_activated_at=self.now.isoformat(),
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "echo", "player_id": "echo", "clan": "echo_freedom",
            "profession": "revealer", "level": 71,
        }
        self.allowed = patch(
            "ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES",
            ("full_disclosure",),
        )
        self.allowed.start()

    def tearDown(self):
        self.allowed.stop()
        self.tmp.cleanup()

    def operation(self, operation_id="op-e3", status="running", operation_type="wifi_scanner"):
        return {
            "operation_id": operation_id,
            "owner_username": "echo",
            "target_id": f"target-{operation_id}",
            "target": {"lat": 52.1, "lng": 21.2, "label": "Cel"},
            "operation_type": operation_type,
            "status": status,
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(minutes=20)).isoformat(),
            "duration_seconds": 1200,
            "resource_buffer": {
                "resource_types": ["wifi_networks", "hotspot_database"],
                "items": [],
            },
        }

    def test_activation_marks_existing_and_new_operations_with_e3_presentation(self):
        self.operations.upsert_operations("echo", [self.operation("op-existing")])
        service = GhostNetworkService(repository=self.repo)

        result = service.activate_player_ability(
            self.player, "full-disclosure-existing", now=self.now,
        )
        existing = self.operations.list_active_operations("echo", limit=8)[0]
        new_operation = self.operation("op-new")
        snapshot = service.get_player_ability_window_snapshot(self.player, now=self.now)

        self.assertEqual("applied", result["realizer"]["status"])
        self.assertTrue(any(
            str(marker).endswith(":data_quality")
            for marker in existing["ability_application_keys"]
        ))
        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, new_operation, now=self.now,
        ))
        self.assertEqual("Pełne Ujawnienie", snapshot["presentation"]["display_name"])
        self.assertEqual("PRAWDA BEZ FILTRA", snapshot["presentation"]["activation_tagline"])
        self.assertEqual("data_quality", snapshot["presentation"]["impact_ui"])
        self.assertIn("e3_truth_lens", snapshot["presentation"]["visual_asset_url"])

    def test_every_file_gets_bonus_and_echo_categories_get_priority_bonus(self):
        operation = self.operation()
        window = {
            "window_id": "window-e3", "ability_code": "full_disclosure",
            "activated_at": self.now.isoformat(),
        }
        GhostAbilityProductionRealizer._apply_data_quality_to_row(operation, window)
        categories = [
            "camera", "audio", "network", "personal", "gps", "device",
            "atm", "financial", "credentials", "vehicle", "system",
        ]
        files = [{
            "id": f"file-{category}", "file_category": category,
            "quality_score": 50, "completeness_percent": 50,
            "missing_fields": ["still_missing"],
            "metadata": {"missing_fields": ["still_missing"]},
        } for category in categories]
        import run
        base_price = run.ghost_exchange_price_preview(dict(files[0]))

        first = enhance_data_quality_files(operation, files)
        second = enhance_data_quality_files(operation, files)

        self.assertEqual(len(categories), len(first))
        self.assertEqual([], second)
        by_category = {item["file_category"]: item for item in files}
        for category in DATA_QUALITY_POLICIES["full_disclosure"]["priority_categories"]:
            self.assertEqual(80, by_category[category]["quality_score"])
            self.assertEqual(80, by_category[category]["completeness_percent"])
            self.assertEqual(30, by_category[category]["data_quality_bonus"])
        for category in {"gps", "device", "atm", "financial", "credentials", "vehicle", "system"}:
            self.assertEqual(60, by_category[category]["quality_score"])
            self.assertEqual(60, by_category[category]["completeness_percent"])
            self.assertEqual(10, by_category[category]["data_quality_bonus"])
        self.assertEqual(["still_missing"], by_category["camera"]["missing_fields"])
        self.assertGreater(run.ghost_exchange_price_preview(files[0]), base_price)

    def test_quality_bonus_is_clamped_and_bounded_to_sixteen_files(self):
        operation = self.operation()
        GhostAbilityProductionRealizer._apply_data_quality_to_row(operation, {
            "window_id": "window-cap", "ability_code": "full_disclosure",
            "activated_at": self.now.isoformat(),
        })
        files = [{
            "id": f"camera-{index}", "file_category": "camera",
            "quality_score": 90, "completeness_percent": 95,
        } for index in range(18)]

        changed = enhance_data_quality_files(operation, files)

        self.assertEqual(16, len(changed))
        self.assertEqual(100, files[0]["quality_score"])
        self.assertEqual(100, files[0]["completeness_percent"])
        self.assertEqual(90, files[16]["quality_score"])

    def test_finalizer_persists_priority_network_bonus_once(self):
        import run

        inventory = PlayerInventoryStore(self.db_path)
        operation = self.operation("op-final", status="completed")
        GhostAbilityProductionRealizer._apply_data_quality_to_row(operation, {
            "window_id": "window-final", "ability_code": "full_disclosure",
            "activated_at": self.now.isoformat(),
        })

        with patch.object(run, "player_inventory_store", inventory):
            first = run.finalize_operation_files_bounded("echo", operation)
            second = run.finalize_operation_files_bounded("echo", operation)

        self.assertEqual({item["id"] for item in first}, {item["id"] for item in second})
        self.assertTrue(first)
        self.assertTrue(all(item["data_quality_boosted"] for item in first))
        self.assertTrue(all(item["data_quality_bonus"] == 30 for item in first))
        self.assertTrue(all(item["quality_score"] <= 100 for item in first))

    def test_expiry_stops_new_marks_but_touched_operation_keeps_bonus(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "full-disclosure-expiry", now=self.now)
        touched = self.operation("op-touched")
        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, touched, now=self.now,
        ))

        self.now += timedelta(minutes=16)
        untouched = self.operation("op-after-expiry")
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, untouched, now=self.now,
        ))
        files = [{
            "id": "file-after-expiry", "file_category": "gps",
            "quality_score": 50, "completeness_percent": 50,
        }]
        self.assertEqual(["file-after-expiry"], enhance_data_quality_files(touched, files))
        self.assertEqual(60, files[0]["quality_score"])

    def test_client_projection_is_safe_and_runtime_path_is_lightweight(self):
        import run

        operation = self.operation("op-ui")
        GhostAbilityProductionRealizer._apply_data_quality_to_row(operation, {
            "window_id": "private-window", "ability_code": "full_disclosure",
            "activated_at": self.now.isoformat(),
        })
        summary = run.summarize_operation_for_client(operation)
        self.assertTrue(summary["quality_boosted"])
        self.assertNotIn("ability_application_keys", summary)
        self.assertNotIn("data_quality_provenance", summary)

        source = inspect.getsource(run.apply_active_ghostnetwork_ability_to_new_operation)
        for forbidden in ("get_profile(", "list_profiles(", "sync_session_profile("):
            self.assertNotIn(forbidden, source)
        token = reset_hot_path_metrics()
        try:
            service = GhostNetworkService(repository=self.repo)
            self.operations.upsert_operations("echo", [self.operation()])
            service.activate_player_ability(self.player, "full-disclosure-light", now=self.now)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)


if __name__ == "__main__":
    unittest.main()
