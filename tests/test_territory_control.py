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

    def test_large_cluster_uses_fast_hull_area(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            for index in range(12):
                lat = 52.0 + (index // 4) * 0.00035
                lng = 21.0 + (index % 4) * 0.00035
                store.save_captured_target("alice", captured(f"P{index}", lat, lng))

            with patch.object(TerritoryStore, "MAX_EXACT_AREA_TARGETS", 5):
                areas = store.rebuild_player_areas("alice", player_level=1)

            self.assertEqual(len(areas), 1)
            self.assertGreater(areas[0]["area_size"], 0)
            self.assertGreaterEqual(len(areas[0]["vertices"]), 3)
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

    def test_area_threat_uses_matching_area_id_not_only_participant(self):
        conflict = {
            "status": "active",
            "area_ids": ["cluster-b"],
            "participants": ["alice", "bob"],
            "targets": [],
        }

        unrelated = run.territory_control_area_threat("alice", {"id": "cluster-a"}, [conflict])
        related = run.territory_control_area_threat("alice", {"id": "cluster-b"}, [conflict])

        self.assertEqual(unrelated["threat_state"], "clear")
        self.assertEqual(unrelated["conflict_count"], 0)
        self.assertFalse(unrelated["threat_flags"]["collision"])
        self.assertEqual(related["threat_state"], "collision")
        self.assertEqual(related["conflict_count"], 1)
        self.assertTrue(related["threat_flags"]["collision"])

    def test_area_threat_matches_conflict_target_inside_area_after_area_id_changes(self):
        area = {
            "id": "new-cluster-id",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.01, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
            ],
        }
        conflict = {
            "status": "active",
            "area_ids": ["old-cluster-id"],
            "participants": ["alice", "bob"],
            "targets": [{
                "owner_username": "alice",
                "target": captured("Inside", 52.001, 21.001),
            }],
        }

        threat = run.territory_control_area_threat("alice", area, [conflict])

        self.assertEqual(threat["threat_state"], "collision")
        self.assertEqual(threat["conflict_count"], 1)
        self.assertTrue(threat["threat_flags"]["collision"])
        self.assertEqual(len(threat["attacked_positions"]), 1)

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

    def test_partial_encirclement_does_not_capture_defender_cluster(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            for target in [
                captured("A1", 52.0, 21.0),
                captured("A2", 52.0018, 21.0),
                captured("A3", 52.0018, 21.0018),
                captured("A4", 52.0, 21.0018),
            ]:
                store.save_captured_target("alice", target)
            for target in [
                captured("B1", 52.0006, 21.0006),
                captured("B2", 52.0010, 21.0006),
                captured("B3", 52.0022, 21.0010),
            ]:
                store.save_captured_target("bob", target)
            store.rebuild_player_areas("alice", player_level=3)
            store.rebuild_player_areas("bob", player_level=3)

            with patch.object(run, "record_territory_areas_delta", return_value=[]), \
                    patch.object(run, "record_territory_encirclement_delta", return_value=[]):
                resolver = run.TerritoryEncirclementResolver(store, conflict_store)
                resolved = resolver.detect_encircled_clusters(apply=True, actor_username="alice")

            self.assertEqual(resolved, [])
            self.assertEqual({target["label"] for target in store.list_captured_targets("bob")}, {"B1", "B2", "B3"})
            self.assertFalse({"B1", "B2", "B3"} & {target["label"] for target in store.list_captured_targets("alice")})
        finally:
            self._cleanup(path)

    def test_full_encirclement_transfers_cluster_members_and_preserves_outside_points(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            for target in [
                captured("A1", 52.0, 21.0),
                captured("A2", 52.0018, 21.0),
                captured("A3", 52.0018, 21.0018),
                captured("A4", 52.0, 21.0018),
            ]:
                store.save_captured_target("alice", target)
            for target in [
                captured("B1", 52.0006, 21.0006),
                captured("B2", 52.0010, 21.0006),
                captured("B3", 52.0008, 21.0010),
                captured("B-inner", 52.0008, 21.00075),
                captured("B-outside", 52.01, 21.01),
            ]:
                store.save_captured_target("bob", target)
            store.rebuild_player_areas("alice", player_level=3)
            store.rebuild_player_areas("bob", player_level=3)
            attacker_area = store.list_player_areas("alice")[0]
            defender_area = store.list_player_areas("bob")[0]
            conflict_store.upsert_conflict({
                "conflict_key": "alice-bob-test",
                "participants": ["alice", "bob"],
                "area_ids": [attacker_area["id"], defender_area["id"]],
                "targets": [],
                "status": "active",
            })

            with patch.object(run, "record_territory_areas_delta", return_value=[]), \
                    patch.object(run, "record_territory_encirclement_delta", return_value=[]), \
                    patch.object(run, "record_territory_conflict_delta", return_value=[]), \
                    patch.object(run, "load_profile_readonly", return_value={"level": 3}):
                resolver = run.TerritoryEncirclementResolver(store, conflict_store)
                result = resolver.resolve_encirclement(
                    attacker_area["id"],
                    defender_area["id"],
                    actor_username="alice",
                    reason="unit_test",
                )

            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "resolved")
            self.assertEqual(result["captured_count"], 4)
            alice_labels = {target["label"] for target in store.list_captured_targets("alice")}
            bob_labels = {target["label"] for target in store.list_captured_targets("bob")}
            self.assertTrue({"B1", "B2", "B3", "B-inner"} <= alice_labels)
            self.assertEqual(bob_labels, {"B-outside"})
            self.assertEqual(store.list_player_areas("bob"), [])
            self.assertGreaterEqual(len(store.list_player_areas("alice")), 1)
            self.assertEqual(conflict_store.get_by_key("alice-bob-test")["status"], "resolved_by_encirclement")

            with patch.object(run, "load_profile_readonly", return_value={"level": 3}):
                repeated = run.TerritoryEncirclementResolver(store, conflict_store).detect_encircled_clusters(apply=True)
            self.assertEqual(repeated, [])
            self.assertEqual({target["label"] for target in store.list_captured_targets("bob")}, {"B-outside"})
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
