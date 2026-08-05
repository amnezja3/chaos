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

    def test_conflict_reveal_uses_current_cluster_pillars_and_inners(self):
        pillar = captured("Pillar", 52.01, 21.01)
        pillar["target_id"] = "pillar-current"
        # Punkt lezy dokladnie na przekatnej granicy trojkata. Musi zostac
        # ujawniony tak samo jak punkt wewnatrz polygonu.
        inner = captured("Inner", 52.05, 21.05)
        inner.update({"target_id": "inner-current", "stationary": False})
        area = {
            "id": 1,
            "owner_username": "alice",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.1, "lng": 21.0},
                {"lat": 52.0, "lng": 21.1},
            ],
        }
        intersection = [
            {"lat": 52.0, "lng": 21.0},
            {"lat": 52.1, "lng": 21.0},
            {"lat": 52.0, "lng": 21.1},
        ]
        with patch.object(run, "territory_area_cluster_members", return_value={
            "pillars": [pillar],
            "inners": [inner],
            "objects": [pillar, inner],
            "valid": True,
        }):
            revealed = run.reveal_conflict_targets_for_group([area], [intersection])

        by_id = {item["target_id"]: item for item in revealed}
        self.assertEqual(by_id["pillar-current"]["node_role"], "pillar")
        self.assertEqual(by_id["inner-current"]["node_role"], "inner")

    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_conflict_detection_ignores_same_clan_but_not_friends(self):
        areas = [
            {
                "id": "alice-area", "owner_username": "alice", "status": "active",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0},
                    {"lat": 52.002, "lng": 21.0},
                    {"lat": 52.0, "lng": 21.002},
                ],
            },
            {
                "id": "bob-area", "owner_username": "bob", "status": "active",
                "vertices": [
                    {"lat": 52.0005, "lng": 21.0002},
                    {"lat": 52.0015, "lng": 21.0002},
                    {"lat": 52.0005, "lng": 21.0015},
                ],
            },
        ]

        with patch.object(run.user_store, "get_profile", side_effect=lambda username: {
            "username": username, "clan": "same-clan"
        }):
            self.assertEqual(run.build_territory_conflict_detection_plan(areas), [])

        with patch.object(run.user_store, "get_profile", side_effect=lambda username: {
            "username": username, "clan": "alpha" if username == "alice" else "beta"
        }), patch.object(run.mail_store, "is_accepted_contact", return_value=True):
            plans = run.build_territory_conflict_detection_plan(areas)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["participants"], ["alice", "bob"])

    def test_conflict_absorbs_foreign_object_left_inside_attacker_area(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            for target in [
                captured("A1", 52.0, 21.0),
                captured("A2", 52.002, 21.0),
                captured("A3", 52.0, 21.002),
            ]:
                store.save_captured_target("alice", target)
            inner = captured("B inner", 52.0005, 21.0005)
            inner["target_id"] = "bob-inner"
            inner["generated"] = True
            inner["stationary"] = False
            store.save_captured_target("bob", inner)
            trigger = captured("B trigger", 52.01, 21.01)
            trigger["target_id"] = "bob-trigger"
            store.save_captured_target("bob", trigger)
            alice_areas = store.rebuild_player_areas("alice", player_level=3)
            conflict = conflict_store.upsert_conflict({
                "conflict_key": "absorption-test",
                "participants": ["alice", "bob"],
                "area_ids": [alice_areas[0]["id"] if alice_areas[0].get("id") else "alice", "bob"],
                "intersection": alice_areas[0]["vertices"],
                "intersections": [alice_areas[0]["vertices"]],
                "targets": [
                    {"target_id": "bob-inner", "owner_username": "bob", "target": inner},
                    {"target_id": "bob-trigger", "owner_username": "bob", "target": trigger},
                ],
                "status": "active",
                "last_actor_username": "alice",
            })

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store), \
                    patch.object(run.user_store, "get_profile", side_effect=lambda username: {
                        "username": username, "clan": "alpha" if username == "alice" else "beta"
                    }):
                self.assertEqual(run.absorb_conflict_objects_inside_attacker_territory(conflict), [])
                captured_trigger = conflict_store.capture_pillar(
                    conflict["conflict_id"], "bob-trigger", trigger, "alice",
                    previous_owner_username="bob", action_id="test-trigger-capture",
                )
                self.assertTrue(captured_trigger["changed"])
                conflict = conflict_store.get_by_key(conflict["conflict_id"])
                absorbed = run.absorb_conflict_objects_inside_attacker_territory(conflict)

            self.assertEqual([item["label"] for item in absorbed], ["B inner"])
            self.assertEqual(
                {item["label"] for item in store.list_captured_targets("bob")},
                {"B trigger"},
            )
            self.assertIn("B inner", {item["label"] for item in store.list_captured_targets("alice")})
            pillars = conflict_store.list_pillars(conflict["conflict_id"])
            self.assertTrue(all(pillar["captured"] for pillar in pillars))
            self.assertEqual({pillar["captured_by"] for pillar in pillars}, {"alice"})
        finally:
            self._cleanup(path)

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

    def test_dense_cluster_uses_fast_hull_area_when_triangle_limit_exceeded(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            for index in range(12):
                lat = 52.0 + (index // 4) * 0.00012
                lng = 21.0 + (index % 4) * 0.00012
                store.save_captured_target("alice", captured(f"D{index}", lat, lng))

            with patch.object(TerritoryStore, "MAX_EXACT_AREA_TARGETS", 32), \
                    patch.object(TerritoryStore, "MAX_EXACT_AREA_TRIANGLES", 10):
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

    def test_same_clan_encirclement_does_not_capture_defender_cluster(self):
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
            ]:
                store.save_captured_target("bob", target)
            store.rebuild_player_areas("alice", player_level=3)
            store.rebuild_player_areas("bob", player_level=3)

            def fake_profile(username):
                return {"username": username, "clan": "Siatka Widmo"}

            with patch.object(run.user_store, "get_profile", side_effect=fake_profile), \
                    patch.object(run.mail_store, "is_accepted_contact", return_value=False), \
                    patch.object(run, "record_territory_areas_delta", return_value=[]), \
                    patch.object(run, "record_territory_encirclement_delta", return_value=[]):
                resolver = run.TerritoryEncirclementResolver(store, conflict_store)
                resolved = resolver.detect_encircled_clusters(apply=True, actor_username="alice")

            self.assertEqual(resolved, [])
            self.assertEqual({target["label"] for target in store.list_captured_targets("bob")}, {"B1", "B2", "B3"})
            self.assertFalse({"B1", "B2", "B3"} & {target["label"] for target in store.list_captured_targets("alice")})
        finally:
            self._cleanup(path)

    def test_map_player_areas_neutralizes_same_clan_stale_encircled_status(self):
        profile = {
            "username": "alice",
            "nick": "Alice",
            "level": 4,
            "clan": "Siatka Widmo",
            "apps": [],
            "files": {},
        }
        areas = [
            {
                "id": "outer",
                "owner_username": "alice",
                "status": "active",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0},
                    {"lat": 52.002, "lng": 21.0},
                    {"lat": 52.002, "lng": 21.002},
                    {"lat": 52.0, "lng": 21.002},
                ],
                "area_size": 4000,
            },
            {
                "id": "inner",
                "owner_username": "bob",
                "status": "encircled",
                "vertices": [
                    {"lat": 52.0005, "lng": 21.0005},
                    {"lat": 52.0010, "lng": 21.0005},
                    {"lat": 52.0008, "lng": 21.0010},
                ],
                "area_size": "legacy dirty size",
            },
        ]

        class FakeTerritoryStoreForMap:
            def list_player_areas(self):
                return list(areas)

            def list_recent_area_intruders(self, username):
                return []

        def fake_profile(username):
            if username == "alice":
                return profile
            if username == "bob":
                return {"username": "bob", "nick": "Bob", "level": 3, "clan": "Siatka Widmo"}
            return None

        client = self._client_with_user("alice")
        with patch.object(run, "territory_store", FakeTerritoryStoreForMap()), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", side_effect=fake_profile), \
                patch.object(run.mail_store, "is_accepted_contact", return_value=False), \
                patch.object(run, "get_active_conflicts_for_player", return_value=[]), \
                patch.object(run, "contested_targets_from_active_conflicts", return_value=[]):
            response = client.get("/api/map/player-areas")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        inner = next(area for area in payload["areas"] if area["id"] == "inner")
        self.assertEqual(inner["status"], "active")
        self.assertFalse(inner["exposed"])

    def test_map_player_areas_survives_optional_read_model_failures(self):
        profile = {
            "username": "alice",
            "nick": "Alice",
            "level": 4,
            "clan": "Siatka Widmo",
            "apps": [],
            "files": {},
        }
        areas = [{
            "id": "alice-area",
            "owner_username": "alice",
            "status": "active",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.002, "lng": 21.0},
                {"lat": 52.0, "lng": 21.002},
            ],
            "area_size": 4000,
            "stale": True,
        }]

        class FragileTerritoryStoreForMap:
            def list_player_areas(self):
                return list(areas)

            def list_recent_area_intruders(self, username):
                raise RuntimeError("intruder store unavailable")

        client = self._client_with_user("alice")
        with patch.object(run, "territory_store", FragileTerritoryStoreForMap()), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_stale_territory_polygons", side_effect=AssertionError("read endpoint must not rebuild")), \
                patch.object(
                    run.territory_conflict_store,
                    "list_latest_snapshots_for_player",
                    side_effect=RuntimeError("conflict snapshot store busy"),
                ):
            response = client.get("/api/map/player-areas")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["areas"]), 1)
        self.assertEqual(payload["areas"][0]["id"], "alice-area")
        self.assertIn("stale_refresh_deferred", payload["warnings"])
        self.assertIn("conflict_snapshots_unavailable", payload["warnings"])
        self.assertIn("intruders_unavailable", payload["warnings"])

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
            resolved_conflict = conflict_store.get_by_key("alice-bob-test")
            self.assertEqual(resolved_conflict["status"], "resolved")
            self.assertEqual(resolved_conflict["resolution_reason"], "encirclement")

            with patch.object(run, "load_profile_readonly", return_value={"level": 3}):
                repeated = run.TerritoryEncirclementResolver(store, conflict_store).detect_encircled_clusters(apply=True)
            self.assertEqual(repeated, [])
            self.assertEqual({target["label"] for target in store.list_captured_targets("bob")}, {"B-outside"})
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
