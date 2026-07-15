import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import run
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from response_network.warning_store import ResponseWarningStore


def temp_db_path(prefix):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


def make_warning_operation(status="running"):
    return {
        "operation_id": "op-warning",
        "owner_username": "main",
        "operation_type": "device_tracking",
        "status": status,
        "target_id": "poi-warning",
        "target": {
            "label": "Zabka",
            "lat": 52.23,
            "lng": 21.01,
            "security": {"network": True},
            "risk": "high",
        },
        "started_at": "2026-07-14T10:00:00+00:00",
        "expires_at": "2026-07-14T11:00:00+00:00",
        "duration_seconds": 3600,
        "source_app_quality": {
            "creator_power": 82,
            "quality_score": 45,
            "reliability": 45,
        },
    }


class ResponseWarningVisibleSafeTest(unittest.TestCase):
    def test_warning_store_issues_deduplicated_domain_event(self):
        path = temp_db_path("chaos_response_warning_")
        try:
            store = ResponseWarningStore(db_path=path)
            operation = make_warning_operation()
            operation["operation_risk_meter"] = {
                "warning_dedupe_key": "operation-risk:op-warning:45",
                "current_heat": 50,
                "risk_level": "warning_threshold",
                "actor_id": "main",
                "target_id": "poi-warning",
            }

            first, created_first = store.issue_warning(
                "main",
                operation,
                now="2026-07-14T10:05:00+00:00",
            )
            second, created_second = store.issue_warning(
                "main",
                operation,
                now="2026-07-14T10:05:30+00:00",
            )

            self.assertTrue(created_first)
            self.assertFalse(created_second)
            self.assertEqual(first["warning_id"], second["warning_id"])
            self.assertEqual(first["event_type"], "response_warning_issued")
            self.assertEqual(first["mode"], "visible_safe")
            self.assertFalse(first["penalty_enabled"])
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_refresh_runtime_records_warning_and_player_message_without_penalty(self):
        warning_db = temp_db_path("chaos_response_warning_runtime_")
        incident_db = temp_db_path("chaos_response_warning_incident_")
        try:
            warning_store = ResponseWarningStore(db_path=warning_db)
            incident_store = IncidentStore(db_path=incident_db)
            initializer = IncidentInitializer(incident_store)
            profile = {
                "username": "main",
                "files": {},
                "system_messages": [],
                "operations": [make_warning_operation()],
            }

            with patch.object(run, "response_warning_store", warning_store), \
                    patch.object(run, "incident_store", incident_store), \
                    patch.object(run, "incident_initializer", initializer):
                operations, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc).timestamp(),
                    username="main",
                )

            self.assertTrue(changed)
            meter = operations[0]["operation_risk_meter"]
            self.assertTrue(meter["warning_crossed"])
            self.assertEqual(meter["mode"], "visible_safe")
            self.assertTrue(meter["warning_issued_at"])
            self.assertTrue(meter["warning_arrival_at"])
            self.assertEqual(len(warning_store.recent()), 1)
            self.assertEqual(profile["system_messages"][0]["type"], "warning")
            self.assertIn("Tryb visible_safe", profile["system_messages"][0]["text"])
        finally:
            for path in (warning_db, incident_db):
                if os.path.exists(path):
                    os.remove(path)

    def test_cancelled_operation_cancels_active_warning(self):
        path = temp_db_path("chaos_response_warning_cancel_")
        try:
            store = ResponseWarningStore(db_path=path)
            operation = make_warning_operation()
            operation["operation_risk_meter"] = {
                "warning_dedupe_key": "operation-risk:op-warning:45",
                "current_heat": 50,
                "risk_level": "warning_threshold",
                "actor_id": "main",
            }
            warning, created = store.issue_warning("main", operation, now="2026-07-14T10:05:00+00:00")
            cancelled = store.cancel_for_operation("op-warning", now="2026-07-14T10:06:00+00:00")

            self.assertTrue(created)
            self.assertEqual(len(cancelled), 1)
            self.assertEqual(store.get(warning["warning_id"])["status"], "cancelled")
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
