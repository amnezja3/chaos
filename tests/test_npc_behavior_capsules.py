import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import run
from database import GameStateDeltaBus
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from response_network.npc_capsule_factory import (
    SNIKER_DIRECTIONS_8,
    VISUAL_FAMILIES,
    NPCCapsuleFactory,
    position_at,
)
from response_network.npc_capsule_store import NPCCapsuleStore
from response_network.response_dispatcher import ResponseDispatcher


def temp_db_path(prefix):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


def make_operation(operation_id="op-capsule", status="running", incident_id=None):
    return {
        "operation_id": operation_id,
        "owner_username": "main",
        "operation_type": "persistent_sniffer",
        "status": status,
        "target_id": "poi-capsule",
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
            "current_heat": 86,
            "active_contribution": 86 if status == "running" else 0,
            "incident_threshold": 60,
            "incident_crossed": status == "running",
            "incident_id": incident_id,
            "actor_id": "main",
            "target_id": "poi-capsule",
            "risk_version": 4,
            "position": {
                "lat": 52.23,
                "lng": 21.01,
            },
        },
    }


class NPCBehaviorCapsulesTest(unittest.TestCase):
    def test_factory_builds_complete_versioned_capsules(self):
        factory = NPCCapsuleFactory()
        incident = {
            "incident_id": "incident_capsule",
            "status": "escalated",
            "level": 4,
            "seed": "incident-seed",
            "center": {"lat": 52.23, "lng": 21.01},
            "search_radius_m": 260,
            "expires_at": "2026-07-14T10:30:00+00:00",
        }

        capsules = factory.build_for_incident(incident, now="2026-07-14T10:00:00+00:00")

        self.assertEqual(len(capsules), 3)
        for capsule in capsules:
            self.assertEqual(capsule["actor_type"], "response_npc")
            self.assertEqual(capsule["incident_id"], "incident_capsule")
            self.assertIn(capsule["visual_family"], VISUAL_FAMILIES)
            self.assertEqual(capsule["sniker_directions"], list(SNIKER_DIRECTIONS_8))
            self.assertIn(capsule["trajectory_type"], {"orbital_search", "spiral_sweep", "intercept_loop"})
            self.assertTrue(capsule["trajectory_seed"])
            self.assertGreaterEqual(capsule["trajectory_phase_deg"], 0)
            self.assertLess(capsule["trajectory_phase_deg"], 360)
            self.assertEqual(capsule["behavior_version"], 1)
            self.assertGreater(capsule["speed_mps"], 0)
            self.assertGreater(capsule["patrol_radius_m"], 0)
            self.assertGreater(capsule["detection_radius_m"], 0)
            self.assertEqual(len(capsule["tracking_tokens"]), 1)

    def test_position_at_is_deterministic_and_time_based(self):
        capsule = NPCCapsuleFactory().build_for_incident({
            "incident_id": "incident_position",
            "status": "active",
            "level": 2,
            "seed": "position-seed",
            "center": {"lat": 52.23, "lng": 21.01},
            "search_radius_m": 220,
            "expires_at": "2026-07-14T10:30:00+00:00",
        }, now="2026-07-14T10:00:00+00:00")[0]

        first = position_at(capsule, "2026-07-14T10:05:00+00:00")
        repeated = position_at(capsule, "2026-07-14T10:05:00+00:00")
        later = position_at(capsule, "2026-07-14T10:06:00+00:00")

        self.assertEqual(first, repeated)
        self.assertNotEqual((first["lat"], first["lng"]), (later["lat"], later["lng"]))
        self.assertIn(first["direction"], SNIKER_DIRECTIONS_8)
        self.assertIn(first["animation_state"], {"patrol", "scan", "pursuit"})

    def test_dispatcher_deduplicates_and_updates_capsule_versions(self):
        path = temp_db_path("chaos_npc_capsule_store_")
        try:
            store = NPCCapsuleStore(db_path=path)
            dispatcher = ResponseDispatcher(store, NPCCapsuleFactory())
            incident = {
                "incident_id": "incident_dispatch",
                "status": "active",
                "level": 2,
                "seed": "dispatch-seed",
                "center": {"lat": 52.23, "lng": 21.01},
                "search_radius_m": 220,
                "expires_at": "2026-07-14T10:30:00+00:00",
            }

            created = dispatcher.dispatch_incident(incident, now="2026-07-14T10:00:00+00:00")
            repeated = dispatcher.dispatch_incident(incident, now="2026-07-14T10:00:00+00:00")
            incident["level"] = 4
            updated = dispatcher.dispatch_incident(incident, now="2026-07-14T10:01:00+00:00")

            self.assertEqual([item["action"] for item in created], ["spawned", "spawned"])
            self.assertEqual(repeated, [])
            self.assertTrue(any(item["action"] in {"spawned", "updated"} for item in updated))
            self.assertEqual(len(store.list_public()), 3)
            self.assertTrue(any(capsule["version"] >= 2 for capsule in store.list_public()))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_refresh_runtime_emits_capsule_deltas_and_recovery_snapshot(self):
        incident_db = temp_db_path("chaos_incident_capsule_")
        capsule_db = temp_db_path("chaos_npc_capsule_")
        delta_db = temp_db_path("chaos_delta_capsule_")
        try:
            incident_store = IncidentStore(db_path=incident_db)
            initializer = IncidentInitializer(incident_store)
            capsule_store = NPCCapsuleStore(db_path=capsule_db)
            dispatcher = ResponseDispatcher(capsule_store, NPCCapsuleFactory())
            bus = GameStateDeltaBus(db_path=delta_db)
            profile = {
                "username": "main",
                "files": {},
                "operations": [make_operation()],
            }

            with patch.object(run, "incident_store", incident_store), \
                    patch.object(run, "incident_initializer", initializer), \
                    patch.object(run, "npc_capsule_store", capsule_store), \
                    patch.object(run, "response_dispatcher", dispatcher), \
                    patch.object(run, "delta_bus", bus):
                operations, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc).timestamp(),
                    username="main",
                )
                self.assertTrue(changed)
                incident_id = operations[0]["operation_risk_meter"]["incident_id"]
                created_changes = bus.get_changes_since("main", 0)["changes"]

                client = run.app.test_client()
                with client.session_transaction() as sess:
                    sess["user"] = "main"
                snapshot = client.get("/api/map/incident-npc-capsules").get_json()

                profile["operations"] = [make_operation(status="cancelled", incident_id=incident_id)]
                operations, changed = run.refresh_operations_runtime(
                    profile,
                    persist_timeouts=False,
                    now_ts=datetime(2026, 7, 14, 10, 2, tzinfo=timezone.utc).timestamp(),
                    username="main",
                )
                all_changes = bus.get_changes_since("main", 0)["changes"]

            self.assertTrue(any(event["type"] == "npc.spawned" for event in created_changes))
            self.assertFalse(any(event["type"] == "npc.moved" for event in all_changes))
            self.assertTrue(snapshot["success"])
            self.assertEqual(snapshot["scope"], "npc")
            self.assertGreaterEqual(len(snapshot["capsules"]), 1)
            self.assertNotIn("suspect_refs", snapshot["capsules"][0])
            self.assertNotIn("operation_ids", snapshot["capsules"][0])
            self.assertTrue(any(event["type"] == "npc.removed" for event in all_changes))
            self.assertEqual(capsule_store.list_public(), [])
        finally:
            for path in (incident_db, capsule_db, delta_db):
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    unittest.main()
