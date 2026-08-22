import os
import tempfile
import unittest
from unittest.mock import patch

import run
from database import GameStateDeltaBus
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from tests.session_generation_fixture import SessionGenerationFixture


def make_operation(operation_id="op-public", status="running", incident_id=None):
    return {
        "operation_id": operation_id,
        "owner_username": "main",
        "operation_type": "persistent_sniffer",
        "status": status,
        "target_id": "poi-1",
        "target": {
            "lat": 52.23,
            "lng": 21.01,
            "security": {"network": True},
            "risk": "high",
        },
        "target_mode": "territory_contest",
        "started_at": "2026-07-14T10:00:00+00:00",
        "expires_at": "2026-07-14T11:00:00+00:00",
        "duration_seconds": 3600,
        "source_app_quality": {
            "creator_power": 90,
            "quality_score": 35,
            "reliability": 30,
        },
        "operation_risk_meter": {
            "current_heat": 85,
            "active_contribution": 85 if status == "running" else 0,
            "incident_threshold": 60,
            "incident_crossed": status == "running",
            "incident_id": incident_id,
            "actor_id": "main",
            "target_id": "poi-1",
            "risk_version": 3,
            "position": {
                "lat": 52.23,
                "lng": 21.01,
            },
        },
    }


class PublicIncidentMapTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_public_incident_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def temp_paths(self):
        db_fd, db_path = tempfile.mkstemp(prefix="chaos_incident_map_", suffix=".sqlite")
        os.close(db_fd)
        os.remove(db_path)
        return db_path

    def test_public_snapshot_does_not_expose_private_fields(self):
        db_path = self.temp_paths()
        try:
            store = IncidentStore(db_path=db_path)
            store.upsert({
                "incident_id": "incident_public",
                "status": "active",
                "level": 3,
                "heat": 88,
                "center": {"lat": 52.23, "lng": 21.01},
                "search_radius_m": 260,
                "operation_ids": ["op-secret"],
                "suspect_refs": [{"actor_id": "main"}],
                "territory_refs": [{"territory_id": "territory-a"}],
                "npc_capsule_ids": [],
            }, event_type="incident.created", now="2026-07-14T10:00:00+00:00")

            with patch.object(run, "incident_store", store):
                client = run.app.test_client()
                headers = self.session_generation.authenticate(client, "main")
                data = client.get("/api/map/incidents", headers=headers).get_json()

            self.assertTrue(data["success"])
            self.assertEqual(data["scope"], "incident")
            self.assertEqual(len(data["incidents"]), 1)
            public = data["incidents"][0]
            self.assertEqual(public["incident_id"], "incident_public")
            self.assertEqual(public["level"], 3)
            self.assertEqual(public["center"], {"lat": 52.23, "lng": 21.01})
            self.assertNotIn("operation_ids", public)
            self.assertNotIn("suspect_refs", public)
            self.assertNotIn("territory_refs", public)
            self.assertNotIn("operation_refs", public)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_incident_created_and_resolved_deltas_are_public(self):
        incident_db = self.temp_paths()
        delta_db = self.temp_paths()
        try:
            store = IncidentStore(db_path=incident_db)
            initializer = IncidentInitializer(store)
            bus = GameStateDeltaBus(db_path=delta_db)
            profile = {
                "username": "main",
                "files": {},
                "operations": [make_operation()],
            }

            with patch.object(run, "incident_store", store), \
                    patch.object(run, "incident_initializer", initializer), \
                    patch.object(run, "delta_bus", bus):
                operations, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=1784023200,
                    username="main",
                )
                self.assertTrue(changed)
                incident_id = operations[0]["operation_risk_meter"]["incident_id"]
                created_changes = bus.get_changes_since("main", 0)["changes"]

                profile["operations"] = [make_operation(operation_id="op-public", status="cancelled", incident_id=incident_id)]
                operations, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=1784023260,
                    username="main",
                )
                self.assertTrue(changed)
                all_changes = bus.get_changes_since("main", 0)["changes"]

            self.assertEqual(created_changes[0]["scope"], "incident")
            self.assertEqual(created_changes[0]["type"], "incident.created")
            self.assertNotIn("operation_ids", created_changes[0]["payload"])
            self.assertNotIn("suspect_refs", created_changes[0]["payload"])
            self.assertIn("center", created_changes[0]["payload"])

            self.assertEqual(all_changes[-1]["type"], "incident.resolved")
            self.assertTrue(all_changes[-1]["payload"]["removed"])
            self.assertEqual(all_changes[-1]["entity_id"], incident_id)
        finally:
            for path in (incident_db, delta_db):
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    unittest.main()
