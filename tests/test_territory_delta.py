import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import GameStateDeltaBus, TerritoryConflictStore, TerritoryStore
from response_network.territory_context_reader import TerritoryContextReader
from response_network.territory_delta import (
    TERRITORY_CONFLICT_CHANGED,
    TERRITORY_UPDATED,
    TerritoryDeltaPublisher,
)


def square(lat, lng, size=0.01):
    return [
        {"lat": lat, "lng": lng},
        {"lat": lat, "lng": lng + size},
        {"lat": lat + size, "lng": lng + size},
        {"lat": lat + size, "lng": lng},
    ]


class TerritoryDeltaPublisherTest(unittest.TestCase):
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

    def _client_with_user(self, username="admin"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_area_delta_is_idempotent_and_minimal(self):
        path = self._temp_db()
        try:
            bus = GameStateDeltaBus(db_path=str(path))
            publisher = TerritoryDeltaPublisher(delta_bus=bus)
            area = {
                "id": 7,
                "owner_username": "alice",
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "status": "active",
                "updated_at": "2026-07-14T12:00:00+00:00",
            }

            first = publisher.record_area_updated("alice", area, reason="test")
            second = publisher.record_area_updated("alice", area, reason="test")

            self.assertEqual(first["version"], second["version"])
            self.assertEqual(first["type"], TERRITORY_UPDATED)
            self.assertEqual(first["scope"], "territory")
            self.assertEqual(first["entity_id"], "territory_area:7")
            self.assertNotIn("vertices", first["payload"])
            self.assertEqual(first["payload"]["bbox"]["min_lat"], 52.0)
        finally:
            self._cleanup(path)

    def test_conflict_delta_is_emitted_for_each_participant(self):
        path = self._temp_db()
        try:
            bus = GameStateDeltaBus(db_path=str(path))
            publisher = TerritoryDeltaPublisher(delta_bus=bus)
            conflict = {
                "id": 3,
                "conflict_key": "alice:bob:test",
                "participants": ["alice", "bob"],
                "area_ids": [1, 2],
                "status": "active",
                "updated_at": "2026-07-14T12:05:00+00:00",
            }

            events = publisher.record_conflict_changed(conflict, reason="test_conflict")

            self.assertEqual(len(events), 2)
            self.assertEqual({event["type"] for event in events}, {TERRITORY_CONFLICT_CHANGED})
            self.assertEqual(events[0]["payload"]["conflict_key"], "alice:bob:test")
            alice_changes = bus.get_changes_since("alice", 0, 10)
            bob_changes = bus.get_changes_since("bob", 0, 10)
            self.assertEqual(len(alice_changes["changes"]), 1)
            self.assertEqual(len(bob_changes["changes"]), 1)
        finally:
            self._cleanup(path)

    def test_recovery_snapshot_uses_territory_context_reader(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            reader = TerritoryContextReader(territory_store, conflict_store)
            publisher = TerritoryDeltaPublisher(GameStateDeltaBus(db_path=str(path)), reader)

            snapshot = publisher.recovery_snapshot_for_point(52.004, 21.004, actor_username="alice")

            self.assertEqual(snapshot["scope"], "territory")
            self.assertFalse(snapshot["recovery_required"])
            self.assertTrue(snapshot["snapshot"]["inside_own_territory"])
        finally:
            self._cleanup(path)

    def test_recovery_diagnostics_reports_gap(self):
        publisher = TerritoryDeltaPublisher()
        diagnostics = publisher.recovery_diagnostics({
            "recovery_required": True,
            "reason": "outside_retention",
            "current_version": 12,
            "changes": [],
        })

        self.assertTrue(diagnostics["recovery_required"])
        self.assertEqual(diagnostics["reason"], "outside_retention")
        self.assertEqual(diagnostics["current_version"], 12)

    def test_dev_recovery_endpoint_requires_admin_and_does_not_sync_profile(self):
        path = self._temp_db()
        try:
            territory_store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            territory_store.replace_player_areas("alice", [{
                "vertices": square(52.0, 21.0),
                "centroid_lat": 52.005,
                "centroid_lng": 21.005,
                "area_size": 100,
                "max_edge_distance": 1000,
                "status": "active",
            }])
            bus = GameStateDeltaBus(db_path=str(path))
            publisher = TerritoryDeltaPublisher(bus, TerritoryContextReader(territory_store, conflict_store))

            self.assertEqual(
                self._client_with_user("alice").get("/api/dev/territory-context/recovery?lat=52.004&lng=21.004").status_code,
                403,
            )

            client = self._client_with_user("admin")
            with patch.object(run, "territory_delta_publisher", publisher), \
                    patch.object(run, "delta_bus", bus), \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
                response = client.get("/api/dev/territory-context/recovery?lat=52.004&lng=21.004&actor_username=alice&since=0")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["territory_recovery"]["scope"], "territory")
            self.assertFalse(data["delta_diagnostics"]["recovery_required"])
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
