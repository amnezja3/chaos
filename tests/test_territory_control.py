import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import TerritoryConflictStore, TerritoryStore


def captured(label, lat, lng, security=None):
    return {
        "label": label,
        "name": label,
        "icon": "\U0001F4CD",
        "source_type": "test",
        "generated": False,
        "stationary": True,
        "lat": lat,
        "lng": lng,
        "security": dict(security or {}),
    }


def installed_profile(username="alice"):
    return {
        "username": username,
        "level": 1,
        "respect": 0,
        "apps": [{"id": "territoryControl", "type": "pro-system-tool", "category": "pro-system-tools"}],
        "curently_possition": {"lat": 52.0, "lng": 21.0},
        "aimed_target": {},
    }


class TerritoryControlTest(unittest.TestCase):
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

    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_one_and_two_pillars_are_alone_without_cluster(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            store.save_captured_target("alice", captured("A", 52.0, 21.0))
            store.save_captured_target("alice", captured("B", 52.001, 21.0))
            store.rebuild_player_areas("alice", player_level=1)

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store):
                snapshot = run.build_territory_control_snapshot("alice", profile=installed_profile())

            self.assertEqual(snapshot["cluster_count"], 0)
            self.assertEqual(snapshot["alone_count"], 2)
            self.assertNotIn("cluster_id", snapshot["alone_pillars"][0])
            self.assertEqual({item["state"] for item in snapshot["alone_pillars"]}, {"alone"})
        finally:
            self._cleanup(path)

    def test_third_pillar_creates_cluster_and_three_pillar_removal_dissolves_it(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            targets = [
                captured("A", 52.0, 21.0),
                captured("B", 52.001, 21.0),
                captured("C", 52.0, 21.001),
            ]
            for target in targets:
                store.save_captured_target("alice", target)
            store.rebuild_player_areas("alice", player_level=1)

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store):
                snapshot = run.build_territory_control_snapshot("alice", profile=installed_profile())

            self.assertEqual(snapshot["cluster_count"], 1)
            self.assertEqual(snapshot["alone_count"], 0)
            cluster = snapshot["clusters"][0]
            self.assertEqual(cluster["pillar_count"], 3)
            self.assertGreater(cluster["area_size"], 0)
            self.assertIsNotNone(cluster["navigation_target"])

            store.remove_captured_target("alice", targets[0]["lat"], targets[0]["lng"], targets[0]["label"])
            store.rebuild_player_areas("alice", player_level=1)

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store):
                dissolved = run.build_territory_control_snapshot("alice", profile=installed_profile())

            self.assertEqual(dissolved["cluster_count"], 0)
            self.assertEqual(dissolved["alone_count"], 2)
            self.assertEqual({item["state"] for item in dissolved["alone_pillars"]}, {"alone"})
        finally:
            self._cleanup(path)

    def test_security_summary_counts_boolean_armament_only(self):
        summary = run.territory_control_security_summary({
            "scan_ports": True,
            "trace": False,
            "risk_score": 80,
            "note": "ignored",
        })

        self.assertEqual(summary["security_enabled"], 1)
        self.assertEqual(summary["security_total"], 2)
        self.assertEqual(summary["security_percent"], 50)

    def test_endpoint_uses_readonly_profile_and_does_not_sync(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            store.save_captured_target("alice", captured("A", 52.0, 21.0))
            client = self._client_with_user("alice")

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store), \
                    patch.object(run, "load_profile_readonly", return_value=installed_profile()), \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
                response = client.get("/api/ghost-control/territory")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["scope"], "territory_control")
            self.assertEqual(data["alone_count"], 1)
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
