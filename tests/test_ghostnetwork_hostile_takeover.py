import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import PlayerInventoryStore, PlayerOperationStore
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import replicate_file_yield_files


class GhostNetworkHostileTakeoverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V4"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-v4",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v4", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "profit_enforcer", "level": 50,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def operation(self, operation_id="op-v4", status="running"):
        return {
            "operation_id": operation_id,
            "owner_username": "alice",
            "target_id": f"target-{operation_id}",
            "target": {"lat": 52.1, "lng": 21.2, "label": "Cel"},
            "operation_type": "generic_trace",
            "status": status,
            "started_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(minutes=20)).isoformat(),
            "duration_seconds": 1200,
            "resource_buffer": {
                "resource_types": ["location_history", "internal_recon_state"],
                "items": [],
            },
        }

    def test_activation_marks_existing_and_new_operations_durably(self):
        self.operations.upsert_operations("alice", [self.operation("op-existing")])
        service = GhostNetworkService(repository=self.repo)

        activated = service.activate_player_ability(
            self.player, "hostile-existing", now=self.now,
        )
        existing = self.operations.list_active_operations("alice", limit=8)[0]
        new_operation = self.operation("op-new")

        self.assertEqual("applied", activated["realizer"]["status"])
        self.assertTrue(any(
            marker.endswith(":file_yield")
            for marker in existing["ability_application_keys"]
        ))
        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, new_operation, now=self.now,
        ))
        self.assertTrue(any(
            marker.endswith(":file_yield")
            for marker in new_operation["ability_application_keys"]
        ))

    def test_expiry_stops_new_marks_but_keeps_touched_operation(self):
        service = GhostNetworkService(repository=self.repo)
        service.activate_player_ability(self.player, "hostile-expiry", now=self.now)
        touched = self.operation("op-touched")
        self.assertTrue(service.apply_active_ability_to_new_operation(
            self.player, touched, now=self.now,
        ))

        self.now += timedelta(minutes=16)
        untouched = self.operation("op-after-expiry")
        self.assertFalse(service.apply_active_ability_to_new_operation(
            self.player, untouched, now=self.now,
        ))
        copies = replicate_file_yield_files(touched, [{
            "id": "file-source", "name": "material.json", "file_category": "network",
            "sellable": True, "market_status": "queued_for_market",
        }])
        self.assertEqual(["backup", "fullbackup"], [item["copy_variant"] for item in copies])

    def test_finalizer_persists_original_backup_and_fullbackup_once(self):
        import run

        inventory = PlayerInventoryStore(self.db_path)
        operation = self.operation("op-final", status="completed")
        operation["ability_application_keys"] = ["window-v4:file_yield"]
        operation["file_yield_provenance"] = {
            "window_id": "window-v4", "ability_code": "hostile_takeover",
            "family": "file_yield", "copies_per_source": 2,
        }

        with patch.object(run, "player_inventory_store", inventory):
            first = run.finalize_operation_files_bounded("alice", operation)
            second = run.finalize_operation_files_bounded("alice", operation)

        first_ids = {item["id"] for item in first}
        self.assertEqual(first_ids, {item["id"] for item in second})
        self.assertEqual(4, len(first))
        copies = [item for item in first if item.get("copy_variant")]
        self.assertEqual({"backup", "fullbackup"}, {item["copy_variant"] for item in copies})
        self.assertTrue(all(item.get("file_category") == "gps" for item in copies))
        self.assertTrue(all(item.get("market_status") == "queued_for_market" for item in copies))
        self.assertTrue(all(not str(item.get("name") or "").endswith(".pkg") for item in copies))

    def test_client_projection_exposes_only_safe_persistent_flag(self):
        import run

        operation = self.operation("op-ui")
        operation["ability_application_keys"] = ["private-window:file_yield"]
        operation["file_yield_provenance"] = {"window_id": "private-window"}
        summary = run.summarize_operation_for_client(operation)

        self.assertTrue(summary["yield_boosted"])
        self.assertNotIn("ability_application_keys", summary)
        self.assertNotIn("file_yield_provenance", summary)


if __name__ == "__main__":
    unittest.main()
