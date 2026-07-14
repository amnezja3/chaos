import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import run
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from response_network.operation_risk_meter import update_operation_risk_meter


def ts(hour, minute=0):
    return datetime(2026, 7, 14, hour, minute, tzinfo=timezone.utc).timestamp()


def operation(operation_id, lat=52.1, lng=21.2, owner="neo", heat=True):
    op = {
        "operation_id": operation_id,
        "operation_type": "persistent_sniffer",
        "owner_username": owner,
        "target_id": f"map:{lat}:{lng}:{operation_id}",
        "target": {
            "lat": lat,
            "lng": lng,
            "label": operation_id,
            "security": {"firewall": True, "camera": True},
        },
        "target_mode": "territory_contest",
        "status": "running",
        "started_at": "2026-07-14T10:00:00+00:00",
        "expires_at": "2026-07-14T11:00:00+00:00",
        "source_app_quality": {
            "creator_power": 90,
            "quality_score": 35,
            "reliability": 30,
        },
    }
    update_operation_risk_meter(op, now_ts=ts(10, 45) if heat else ts(10, 0))
    return op


class IncidentInitializerTest(unittest.TestCase):
    def _temp_db(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        handle.close()
        return Path(handle.name)

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{path}{suffix}")
            if candidate.exists():
                try:
                    candidate.unlink()
                except PermissionError:
                    pass

    def test_incident_is_created_from_threshold_crossed_operation(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            op = operation("op-a")

            result = initializer.sync_operations([op], now="2026-07-14T10:45:00+00:00")

            self.assertEqual(result["candidates"], 1)
            self.assertEqual(result["actions"][0]["action"], "created")
            self.assertTrue(op["operation_risk_meter"]["incident_id"])
            incident = store.get(op["operation_risk_meter"]["incident_id"])
            self.assertEqual(incident["status"], "escalated")
            self.assertEqual(incident["operation_ids"], ["op-a"])
            self.assertFalse(incident["visible"])
            self.assertFalse(incident["npc_enabled"])
            self.assertFalse(incident["consequences_enabled"])
        finally:
            self._cleanup(path)

    def test_nearby_operations_are_merged_and_recalculated(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            op_a = operation("op-a", 52.1, 21.2)
            op_b = operation("op-b", 52.1005, 21.2005)

            initializer.sync_operations([op_a], now="2026-07-14T10:45:00+00:00")
            initializer.sync_operations([op_a, op_b], now="2026-07-14T10:46:00+00:00")

            self.assertEqual(op_a["operation_risk_meter"]["incident_id"], op_b["operation_risk_meter"]["incident_id"])
            incident = store.get(op_a["operation_risk_meter"]["incident_id"])
            self.assertEqual(set(incident["operation_ids"]), {"op-a", "op-b"})
            self.assertGreaterEqual(incident["version"], 2)
            self.assertEqual(incident["heat"], 100)
            self.assertEqual(incident["level"], 4)
        finally:
            self._cleanup(path)

    def test_cancelled_operation_removes_contribution_and_cancels_empty_incident(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            op = operation("op-a")
            initializer.sync_operations([op], now="2026-07-14T10:45:00+00:00")
            incident_id = op["operation_risk_meter"]["incident_id"]

            op["status"] = "cancelled"
            update_operation_risk_meter(op, now_ts=ts(10, 50))
            result = initializer.sync_operations([op], now="2026-07-14T10:50:00+00:00")

            self.assertEqual(result["actions"][0]["action"], "cancelled")
            self.assertIsNone(op["operation_risk_meter"]["incident_id"])
            incident = store.get(incident_id)
            self.assertEqual(incident["status"], "cancelled")
            self.assertEqual(incident["heat"], 0)
            self.assertEqual(incident["operation_ids"], [])
        finally:
            self._cleanup(path)

    def test_replay_contains_create_and_cancel_events(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            op = operation("op-a")
            initializer.sync_operations([op], now="2026-07-14T10:45:00+00:00")
            incident_id = op["operation_risk_meter"]["incident_id"]
            op["status"] = "cancelled"
            update_operation_risk_meter(op, now_ts=ts(10, 50))
            initializer.sync_operations([op], now="2026-07-14T10:50:00+00:00")

            events = store.replay(incident_id)

            self.assertIn("incident.created", [event["event_type"] for event in events])
            self.assertIn("incident.cancelled", [event["event_type"] for event in events])
        finally:
            self._cleanup(path)

    def test_repeated_sync_without_changes_does_not_bump_version_or_audit(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            op = operation("op-a")
            initializer.sync_operations([op], now="2026-07-14T10:45:00+00:00")
            incident_id = op["operation_risk_meter"]["incident_id"]
            first = store.get(incident_id)

            initializer.sync_operations([op], now="2026-07-14T10:45:00+00:00")
            second = store.get(incident_id)
            events = store.replay(incident_id)

            self.assertEqual(first["version"], second["version"])
            self.assertEqual(len(events), 1)
        finally:
            self._cleanup(path)

    def test_refresh_operations_runtime_uses_initializer_without_publication(self):
        path = self._temp_db()
        try:
            store = IncidentStore(db_path=str(path))
            initializer = IncidentInitializer(store)
            profile = {"operations": [operation("op-a")], "files": {}, "risk_events": [], "system_messages": []}

            with patch.object(run, "incident_initializer", initializer):
                refreshed, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=ts(10, 45),
                )

            self.assertTrue(changed)
            incident_id = profile["operations"][0]["operation_risk_meter"]["incident_id"]
            self.assertEqual(refreshed[0]["operation_risk_meter"]["incident_id"], incident_id)
            self.assertTrue(store.get(incident_id))
            self.assertEqual(profile["system_messages"], [])
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
