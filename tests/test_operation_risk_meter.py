import unittest
import json
import sqlite3
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from database import PlayerInventoryStore, PlayerOperationStore
import run
from tests.session_generation_fixture import SessionGenerationFixture
from response_network.operation_risk_meter import (
    calculate_operation_risk,
    update_operation_risk_meter,
)


def ts(hour, minute=0):
    return datetime(2026, 7, 14, hour, minute, tzinfo=timezone.utc).timestamp()


class OperationRiskMeterTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "game.sqlite3")
        self.original_operation_store = run.player_operation_store
        self.original_inventory_store = run.player_inventory_store
        run.player_operation_store = PlayerOperationStore(db_path=self.db_path)
        run.player_inventory_store = PlayerInventoryStore(db_path=self.db_path)

    def tearDown(self):
        run.player_operation_store = self.original_operation_store
        run.player_inventory_store = self.original_inventory_store
        self.tmpdir.cleanup()

    def _operation(self, **overrides):
        operation = {
            "operation_id": "op-risk-1",
            "operation_type": "persistent_sniffer",
            "owner_username": "neo",
            "target_id": "map:52.1:21.2:test",
            "target": {
                "lat": 52.1,
                "lng": 21.2,
                "label": "Test target",
                "security": {
                    "firewall": True,
                    "camera": True,
                },
            },
            "target_mode": "territory_contest",
            "status": "running",
            "started_at": "2026-07-14T10:00:00+00:00",
            "expires_at": "2026-07-14T11:00:00+00:00",
            "source_app_quality": {
                "creator_power": 90,
                "quality_score": 40,
                "reliability": 30,
            },
        }
        operation.update(overrides)
        return operation

    def test_calculates_observe_meter_from_operation_inputs(self):
        operation = self._operation()

        meter = calculate_operation_risk(operation, now_ts=ts(10, 30))

        self.assertEqual(meter["mode"], "observe")
        self.assertEqual(meter["operation_id"], "op-risk-1")
        self.assertEqual(meter["base_heat"], 20)
        self.assertGreater(meter["time_heat"], 0)
        self.assertGreater(meter["tool_modifier"], 0)
        self.assertGreater(meter["security_modifier"], 0)
        self.assertEqual(meter["conflict_modifier"], 25)
        self.assertGreaterEqual(meter["current_heat"], meter["incident_threshold"])
        self.assertTrue(meter["warning_crossed"])
        self.assertTrue(meter["incident_crossed"])
        self.assertIsNone(meter["warning_issued_at"])
        self.assertIsNone(meter["incident_id"])

    def test_bounded_ability_modifier_changes_input_without_forcing_outcome(self):
        operation = self._operation(target_mode="ordinary", target={"security": {}})
        baseline = calculate_operation_risk(operation, now_ts=ts(10, 30))
        reduced = calculate_operation_risk(
            operation,
            rules={"ability_heat_modifier": -999},
            now_ts=ts(10, 30),
        )

        self.assertEqual(-25, reduced["ability_heat_modifier"])
        self.assertEqual(max(0, baseline["current_heat"] - 25), reduced["current_heat"])
        self.assertEqual(
            reduced["current_heat"] >= reduced["warning_threshold"],
            reduced["warning_crossed"],
        )
        self.assertEqual(
            reduced["current_heat"] >= reduced["incident_threshold"],
            reduced["incident_crossed"],
        )

    def test_threshold_crossing_is_idempotent_for_same_state(self):
        operation = self._operation()

        changed_first = update_operation_risk_meter(operation, now_ts=ts(10, 30))
        first = dict(operation["operation_risk_meter"])
        changed_second = update_operation_risk_meter(operation, now_ts=ts(10, 30))
        second = dict(operation["operation_risk_meter"])

        self.assertTrue(changed_first)
        self.assertFalse(changed_second)
        self.assertEqual(first["risk_version"], second["risk_version"])
        self.assertEqual(first["warning_dedupe_key"], second["warning_dedupe_key"])
        self.assertEqual(first["incident_dedupe_key"], second["incident_dedupe_key"])
        self.assertEqual(first["warning_crossed_at"], second["warning_crossed_at"])
        self.assertEqual(first["incident_crossed_at"], second["incident_crossed_at"])

    def test_cancelled_operation_zeros_active_contribution_and_cancels_threshold_state(self):
        operation = self._operation()
        update_operation_risk_meter(operation, now_ts=ts(10, 30))
        operation["status"] = "cancelled"

        changed = update_operation_risk_meter(operation, now_ts=ts(10, 35))
        meter = operation["operation_risk_meter"]

        self.assertTrue(changed)
        self.assertTrue(meter["cancelled"])
        self.assertEqual(meter["current_heat"], 0)
        self.assertEqual(meter["active_contribution"], 0)
        self.assertFalse(meter["warning_crossed"])
        self.assertFalse(meter["incident_crossed"])
        self.assertTrue(meter["warning_cancelled"])
        self.assertTrue(meter["incident_cancelled"])

    def test_created_operations_get_risk_meter_without_publishing_incidents(self):
        profile = {"operations": [], "risk_events": [], "system_messages": []}
        app = {
            "id": "snfx",
            "name": "Snfx",
            "operation_types": ["persistent_sniffer"],
            "creator_power": 90,
            "quality_score": 40,
            "reliability": 30,
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Test target",
            "target_mode": "territory_contest",
            "security": {"firewall": True},
        }

        created = run.create_operations_for_app_action(profile, "neo", app, "sniff", target)

        self.assertEqual(len(created), 1)
        meter = created[0]["operation_risk_meter"]
        self.assertEqual(meter["mode"], "observe")
        self.assertEqual(meter["risk_version"], 1)
        self.assertEqual(profile["risk_events"], [])
        self.assertEqual(profile["system_messages"], [])

    def test_bounded_store_tick_moves_projection_without_profile_io(self):
        runtime_now = datetime.now(timezone.utc).replace(microsecond=0)
        operation = self._operation(
            operation_type="vehicle_tracking",
            movement_model="road_movement",
            started_at=(runtime_now - timedelta(minutes=1)).isoformat(),
            expires_at=(runtime_now + timedelta(minutes=119)).isoformat(),
        )
        self.assertEqual(len(run.player_operation_store.upsert_operations("neo", [operation])), 1)
        tick_now = datetime.now(timezone.utc).timestamp() + 2
        with patch.object(run.incident_initializer, "sync_operations", return_value={"actions": []}), \
                patch.object(run, "sync_response_warnings", return_value=[]), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("profile hot path")):
            first = run.process_operation_runtime_tick(
                limit_users=1, min_age_seconds=0, now_ts=tick_now
            )
            first_position = dict(
                run.player_operation_store.list_operations("neo")[0]["current_position"]
            )
            second = run.process_operation_runtime_tick(
                limit_users=1, min_age_seconds=0, now_ts=tick_now + 30
            )
        stored = run.player_operation_store.list_operations("neo")[0]
        self.assertEqual(first["operations"], 1)
        self.assertEqual(second["operations"], 1)
        self.assertNotEqual(stored["current_position"], first_position)
        self.assertGreaterEqual(stored["_runtime_version"], 3)

    def test_terminal_tick_finalizes_file_without_profile_io(self):
        runtime_now = datetime.now(timezone.utc).replace(microsecond=0)
        operation = self._operation(
            operation_id="op-wifi-bounded",
            operation_type="wifi_scanner",
            status="running",
            started_at=(runtime_now - timedelta(minutes=11)).isoformat(),
            expires_at=(runtime_now - timedelta(minutes=1)).isoformat(),
            duration_seconds=600,
            resource_types=["wifi_networks"],
        )
        run.player_inventory_store.seed_from_profile("neo", {
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 500,
            "storage_used": 0,
            "storage_unit": "MB",
        })
        self.assertEqual(len(run.player_operation_store.upsert_operations("neo", [operation])), 1)
        with patch.object(run.incident_initializer, "sync_operations", return_value={"actions": []}), \
                patch.object(run, "sync_response_warnings", return_value=[]), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("profile hot path")):
            result = run.process_operation_runtime_tick(
                limit_users=1,
                min_age_seconds=0,
                now_ts=runtime_now.timestamp(),
            )
        files = run.player_inventory_store.list_data_files(
            "neo", operation_id="op-wifi-bounded"
        )
        stored = next(
            item for item in run.player_operation_store.list_operations("neo", include_terminal=True)
            if item.get("operation_id") == "op-wifi-bounded"
        )
        self.assertEqual(result["files"], 1)
        self.assertEqual(stored["status"], "timeout")
        self.assertEqual(stored["artifact_state"]["file_count"], 1)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["file_category"], "network")
        self.assertEqual(files[0]["market_status"], "queued_for_market")
        self.assertTrue(files[0]["sellable"])

    def test_runtime_tick_never_hydrates_thousands_of_terminal_operations(self):
        runtime_now = datetime.now(timezone.utc).replace(microsecond=0)
        terminal_rows = []
        for index in range(3000):
            operation = self._operation(
                operation_id=f"op-timeout-{index:04d}",
                status="timeout",
                started_at=(runtime_now - timedelta(days=2)).isoformat(),
                expires_at=(runtime_now - timedelta(days=1)).isoformat(),
            )
            operation["archive_fixture"] = "x" * 128
            encoded = json.dumps(operation, ensure_ascii=False, separators=(",", ":"))
            terminal_rows.append((
                operation["operation_id"], "neo", operation["target_id"],
                operation["operation_type"], "timeout", encoded, "{}", 1,
                operation["started_at"], operation["expires_at"],
            ))
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO player_operations
                    (operation_id, username, target_key, operation_type, status,
                     operation_json, risk_json, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                terminal_rows,
            )
            conn.commit()
        finally:
            conn.close()

        active = self._operation(
            operation_id="op-live-bounded",
            started_at=(runtime_now - timedelta(minutes=1)).isoformat(),
            expires_at=(runtime_now + timedelta(hours=1)).isoformat(),
        )
        run.player_operation_store.upsert_operations(
            "neo", [active], event_type="operation.started"
        )
        conn = sqlite3.connect(self.db_path)
        try:
            events_before = conn.execute("SELECT COUNT(*) FROM operation_events").fetchone()[0]
        finally:
            conn.close()

        incident_inputs = []

        def capture_incident_input(operations, now=None):
            incident_inputs.append([item.get("operation_id") for item in operations])
            return {"actions": []}

        with patch.object(
            run.incident_initializer, "sync_operations", side_effect=capture_incident_input
        ), patch.object(run, "sync_response_warnings", return_value=[]), patch.object(
            run.user_store, "get_profile", side_effect=AssertionError("profile hot path")
        ):
            result = run.process_operation_runtime_tick(
                limit_users=1,
                min_age_seconds=0,
                now_ts=(runtime_now + timedelta(seconds=2)).timestamp(),
            )

        conn = sqlite3.connect(self.db_path)
        try:
            events_after = conn.execute("SELECT COUNT(*) FROM operation_events").fetchone()[0]
        finally:
            conn.close()
        recent_history = run.player_operation_store.list_recent_terminal_operations(
            "neo", limit=25
        )

        fixture = SessionGenerationFixture("chaos_operation_archive_bound_session_").start()
        self.addCleanup(fixture.stop)
        client = run.app.test_client()
        headers = fixture.authenticate(client, "neo")
        summary = client.get("/api/operations?summary=1", headers=headers)

        self.assertEqual(result["operations"], 1)
        self.assertEqual(incident_inputs, [["op-live-bounded"]])
        self.assertEqual(events_after, events_before)
        self.assertEqual(len(recent_history), 25)
        self.assertTrue(all(item["status"] == "timeout" for item in recent_history))
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.get_json()["active_count"], 1)
        self.assertEqual(summary.get_json()["history_count"], 25)

    def test_runtime_store_cas_rejects_stale_projection(self):
        run.player_operation_store.upsert_operations("neo", [self._operation()])
        first = run.player_operation_store.list_operations("neo")[0]
        stale = dict(first)
        first["remaining_seconds"] = 10
        stale["remaining_seconds"] = 20
        self.assertEqual(len(run.player_operation_store.compare_and_swap_runtime("neo", [first])), 1)
        self.assertEqual(run.player_operation_store.compare_and_swap_runtime("neo", [stale]), [])
        self.assertEqual(run.player_operation_store.list_operations("neo")[0]["remaining_seconds"], 10)

    def test_summary_endpoint_reads_store_without_full_profile(self):
        now = datetime.now(timezone.utc)
        run.player_operation_store.upsert_operations("neo", [self._operation(
            started_at=(now - timedelta(minutes=1)).isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
        )])
        fixture = SessionGenerationFixture("chaos_operation_summary_session_").start()
        self.addCleanup(fixture.stop)
        client = run.app.test_client()
        headers = fixture.authenticate(client, "neo")
        with patch.object(run.user_store, "get_profile", side_effect=AssertionError("profile hot path")):
            response = client.get("/api/operations?summary=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["source"], "player_operations")
        self.assertEqual(response.get_json()["active_count"], 1)

    def test_tick_marks_timeout_cleanup_in_store_only(self):
        now = datetime.now(timezone.utc)
        run.player_operation_store.upsert_operations("neo", [self._operation(
            started_at=(now - timedelta(hours=2)).isoformat(),
            expires_at=(now - timedelta(seconds=1)).isoformat(),
        )])
        with patch.object(run.incident_initializer, "sync_operations", return_value={"actions": []}), \
                patch.object(run, "sync_response_warnings", return_value=[]), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("profile hot path")):
            result = run.process_operation_runtime_tick(
                limit_users=1, min_age_seconds=0, now_ts=now.timestamp() + 2
            )
        operation = run.player_operation_store.list_operations("neo")[0]
        self.assertEqual(result["operations"], 1)
        self.assertEqual(operation["status"], "timeout")
        self.assertFalse(operation["cleanup_state"]["marker_visible"])


if __name__ == "__main__":
    unittest.main()
