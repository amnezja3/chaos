import unittest
from unittest.mock import patch

import run
from tests.session_generation_fixture import SessionGenerationFixture


def operation_control_profile(username="alice"):
    return {
        "username": username,
        "apps": [{"id": "operationControl", "type": "pro-system-tool", "category": "pro-system-tools"}],
        "curently_possition": {"lat": 52.0, "lng": 21.0},
        "operations": [],
        "files": {},
        "risk_events": [],
        "system_messages": [],
    }


def operation(
    operation_id,
    operation_type="vehicle_tracking",
    status="running",
    lat=52.001,
    lng=21.001,
    resource_files=None,
    risk_meter=None,
):
    return {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "owner_username": "alice",
        "source_app_id": "tester",
        "map_action_id": operation_type,
        "target_id": f"target-{operation_id}",
        "target": {
            "label": f"Target {operation_id}",
            "lat": lat,
            "lng": lng,
            "target_type": "test",
            "target_mode": "standard",
        },
        "status": status,
        "started_at": "2026-12-18T10:00:00Z",
        "expires_at": "2026-12-18T11:00:00Z",
        "remaining_seconds": 120,
        "current_position": {"lat": lat, "lng": lng},
        "resource_buffer": {"files": list(resource_files or [])},
        "operation_risk_meter": dict(risk_meter or {}),
    }


class FakeUserProfileManager:
    updates = []

    def __init__(self, username):
        self.username = username

    def update_profile(self, payload):
        self.__class__.updates.append((self.username, payload))
        return True


class OperationControlTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_operation_control_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, username)
        return client, headers

    def test_snapshot_extends_existing_operation_summary_with_distance_output_and_incident(self):
        profile = operation_control_profile()
        op = operation(
            "op-gps",
            operation_type="vehicle_tracking",
            resource_files=[{
                "file_category": "gps",
                "directory": "/data/gps",
                "preview_mode": "table",
                "file_size": 12,
                "metadata": {"resource_types": ["gps_logs"]},
            }],
            risk_meter={
                "current_heat": 72,
                "warning_crossed": True,
                "warning_arrival_at": "2026-07-18T10:30:00Z",
                "incident_id": "incident-1",
            },
        )

        with patch.object(run.incident_store, "get", return_value={
            "incident_id": "incident-1",
            "level": 2,
            "status": "active",
            "response_units": ["police"],
        }):
            snapshot = run.build_operation_control_snapshot("alice", profile, operations=[op])

        self.assertTrue(snapshot["success"])
        self.assertEqual(snapshot["active_count"], 1)
        item = snapshot["operations"][0]
        self.assertEqual(item["operation_family"], "gps")
        self.assertTrue(item["distance_available"])
        self.assertGreater(item["distance_from_bike"], 0)
        self.assertEqual(item["output"]["file_category"], "gps")
        self.assertEqual(item["output"]["expected_size_mb"], 12)
        self.assertEqual(item["output"]["output_status"], "created")
        self.assertTrue(item["incident"]["active"])
        self.assertEqual(item["incident"]["incident_id"], "incident-1")
        self.assertEqual(item["incident"]["level"], 2)
        self.assertTrue(item["can_cancel"])

    def test_operation_without_position_reports_distance_unavailable(self):
        profile = operation_control_profile()
        op = operation("op-atm", operation_type="atm_log_extraction")
        op.pop("current_position", None)

        snapshot = run.build_operation_control_snapshot("alice", profile, operations=[op])
        item = snapshot["operations"][0]

        self.assertEqual(item["operation_family"], "atm")
        self.assertIsNone(item["position"])
        self.assertFalse(item["distance_available"])
        self.assertIsNone(item["distance_from_bike"])
        self.assertEqual(item["output"]["file_category"], "atm")

    def test_snapshot_includes_terminal_history_without_cancel_action(self):
        profile = operation_control_profile()
        active = operation("op-active", operation_type="vehicle_tracking")
        completed = operation("op-history", operation_type="atm_log_extraction", status="completed")

        snapshot = run.build_operation_control_snapshot("alice", profile, operations=[active, completed])

        self.assertEqual(snapshot["active_count"], 1)
        self.assertEqual(snapshot["history_count"], 1)
        history_item = snapshot["operation_history"][0]
        self.assertEqual(history_item["operation_id"], "op-history")
        self.assertEqual(history_item["operation_family"], "atm")
        self.assertFalse(history_item["can_cancel"])
        self.assertEqual(history_item["disabled_reason"], "already_terminal")

    def test_snapshot_exposes_only_safe_acceleration_flag(self):
        profile = operation_control_profile()
        accelerated = operation("op-fast")
        accelerated["ability_application_keys"] = [
            "ghost_ability_window_private:operation_speed",
        ]
        ordinary = operation("op-normal")

        snapshot = run.build_operation_control_snapshot(
            "alice", profile, operations=[accelerated, ordinary],
        )
        items = {item["operation_id"]: item for item in snapshot["operations"]}

        self.assertTrue(items["op-fast"]["accelerated"])
        self.assertFalse(items["op-normal"]["accelerated"])
        self.assertNotIn("ability_application_keys", items["op-fast"])
        self.assertNotIn("ability_provenance", items["op-fast"])

    def test_snapshot_exposes_only_safe_risk_mask_flag(self):
        profile = operation_control_profile()
        masked = operation("op-mask")
        masked["operation_risk_meter"] = {
            "current_heat": 31,
            "ability_heat_modifier": -15,
        }

        snapshot = run.build_operation_control_snapshot(
            "alice", profile, operations=[masked],
        )
        item = snapshot["operations"][0]

        self.assertTrue(item["risk_masked"])
        self.assertNotIn("ability_application_keys", item)
        self.assertNotIn("ability_provenance", item)

    def test_snapshot_exposes_only_safe_file_yield_flag(self):
        profile = operation_control_profile()
        touched = operation("op-yield")
        touched["ability_application_keys"] = ["private-window:file_yield"]
        touched["file_yield_provenance"] = {"window_id": "private-window"}

        snapshot = run.build_operation_control_snapshot(
            "alice", profile, operations=[touched],
        )
        item = snapshot["operations"][0]

        self.assertTrue(item["yield_boosted"])
        self.assertNotIn("ability_application_keys", item)
        self.assertNotIn("file_yield_provenance", item)

    def test_snapshot_endpoint_requires_operation_control_app_and_does_not_use_full_sync(self):
        client, headers = self._client_with_user()
        profile = operation_control_profile()
        op = operation("op-network", operation_type="wifi_scanner")

        with patch.object(run, "load_profile_readonly", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", return_value=profile), \
                patch.object(run, "operations_from_store_or_profile", return_value=[op]), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("full sync not expected")):
            response = client.get("/api/ghost-control/operations", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["operations"][0]["operation_family"], "network")

    def test_single_cancel_uses_existing_helper_and_returns_snapshot(self):
        client, headers = self._client_with_user()
        active = operation("op-active", operation_type="vehicle_tracking")
        profile = operation_control_profile()
        profile["operations"] = [active]
        FakeUserProfileManager.updates = []

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "refresh_operations_runtime", side_effect=lambda prof, **kwargs: (prof.get("operations", []), False)), \
                patch.object(run, "UserProfileManager", FakeUserProfileManager):
            response = client.post("/api/ghost-control/operations/cancel", headers=headers, json={
                "operation_id": "op-active",
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["result"], "cancelled")
        self.assertEqual(profile["operations"][0]["status"], "cancelled")
        self.assertEqual(payload["remaining_active"], 0)
        self.assertEqual(len(FakeUserProfileManager.updates), 1)

    def test_group_cancel_uses_existing_cancel_helper_and_saves_once(self):
        client, headers = self._client_with_user()
        active = operation("op-active", operation_type="vehicle_tracking")
        done = operation("op-done", operation_type="vehicle_tracking", status="completed")
        profile = operation_control_profile()
        profile["operations"] = [active, done]
        FakeUserProfileManager.updates = []

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "refresh_operations_runtime", side_effect=lambda prof, **kwargs: (prof.get("operations", []), False)), \
                patch.object(run, "UserProfileManager", FakeUserProfileManager):
            response = client.post("/api/pro-system/operation-control/cancel-group", headers=headers, json={
                "operation_family": "gps",
                "operation_ids": ["op-active", "op-done", "missing"],
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["cancelled"], ["op-active"])
        self.assertEqual(payload["already_terminal"], ["op-done"])
        self.assertEqual(payload["not_found"], ["missing"])
        self.assertEqual(profile["operations"][0]["status"], "cancelled")
        self.assertEqual(len(FakeUserProfileManager.updates), 1)
        self.assertEqual(payload["remaining_active"], 0)


if __name__ == "__main__":
    unittest.main()
