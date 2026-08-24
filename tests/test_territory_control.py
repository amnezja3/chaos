import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import (
    PlayerMarkedTargetStore,
    TerritoryConflictStore,
    TerritoryStore,
    TerritoryTargetOwnershipStore,
    UserStore,
)
from tests.session_generation_fixture import SessionGenerationFixture


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


def installed_profile(username="alice", **updates):
    profile = {
        "username": username,
        "nick": username.title(),
        "email": f"{username}@example.test",
        "avatar": "/static/images/default_avatar.png",
        "level": 1,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "clan": "",
        "fraction": {},
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [{"id": "territoryControl", "type": "pro-system-tool", "category": "pro-system-tools"}],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "system_messages": [],
        "operations": [],
        "targets": [],
        "launch_queue": [],
        "curently_possition": {"lat": 52.0, "lng": 21.0},
        "aimed_target": {},
    }
    profile.update(updates)
    return profile


def territory_context(username="alice", **updates):
    context = {
        "identity": {
            "username": username,
            "display_alias": username.title(),
            "clan_code": "",
            "profession_code": "",
        },
        "app_installed": True,
        "position": {"lat": 52.0, "lng": 21.0},
        "aimed_target": {},
    }
    context.update(updates)
    return context


class TerritoryControlTest(unittest.TestCase):
    def setUp(self):
        self.original_testing = run.app.config.get("TESTING")
        run.app.config["TESTING"] = True
        self.session_generation = SessionGenerationFixture(
            "chaos_territory_control_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def tearDown(self):
        run.app.config["TESTING"] = self.original_testing

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

    def _assert_cluster_transfer_abandon_worker_refresh(self, abandoned_label):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            ownership = TerritoryTargetOwnershipStore(str(path))
            local_users = UserStore(db_path=str(path), seed_path=str(path) + ".missing")
            for username, clan in (("alice", "Alpha"), ("bob", "Beta")):
                local_users.save_profile_guarded(
                    installed_profile(username, level=3, clan=clan),
                    expected_revision=0,
                    source="test.territory_control.create",
                    allow_create=True,
                )
            marked_targets = PlayerMarkedTargetStore(db_path=str(path))
            for item in (
                captured("A1", 52.0, 21.0), captured("A2", 52.0018, 21.0),
                captured("A3", 52.0018, 21.0018), captured("A4", 52.0, 21.0018),
            ):
                store.save_captured_target("alice", item)
            for item in (
                captured("B1", 52.0006, 21.0006),
                captured("B2", 52.0010, 21.0006),
                captured("B3", 52.0008, 21.0010),
                captured("B-inner", 52.0008, 21.00075),
            ):
                store.save_captured_target("bob", item)
            store.rebuild_player_areas("alice", 3)
            store.rebuild_player_areas("bob", 3)
            attacker_area = store.list_player_areas("alice")[0]
            defender_area = store.list_player_areas("bob")[0]
            conflict_store.upsert_conflict({
                "conflict_key": "transfer-abandon-refresh",
                "participants": ["alice", "bob"],
                "area_ids": [attacker_area["id"], defender_area["id"]],
                "targets": [], "status": "active",
            })
            with patch.object(run, "record_territory_areas_delta", return_value=[]), \
                    patch.object(run, "record_territory_encirclement_delta", return_value=[]), \
                    patch.object(run, "record_territory_conflict_delta", return_value=[]), \
                    patch.object(run, "load_profile_readonly", return_value={"level": 3}):
                result = run.TerritoryEncirclementResolver(
                    store, conflict_store, ownership_store=ownership,
                ).resolve_encirclement(
                    attacker_area["id"], defender_area["id"],
                    actor_username="alice", reason="contract_test",
                )
            self.assertEqual(result["status"], "resolved")
            inherited = next(
                item for item in store.list_captured_targets("alice")
                if item["label"] == abandoned_label
            )
            abandoned_target_id = inherited["target_id"]
            abandoned = store.abandon_captured_target(
                "alice", inherited, abandoned_target_id,
                expected_version=inherited["ownership_version"],
            )
            self.assertTrue(abandoned["ok"])

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "user_store", local_users), \
                    patch.object(run, "player_marked_target_store", marked_targets), \
                    patch.object(run.player_target_runtime_store, "clear_if_matches"), \
                    patch.object(run, "record_territory_areas_delta", return_value=[]), \
                    patch.object(run, "sync_static_area_intruders_for_owner", return_value=[]), \
                    patch.object(run, "resolve_territory_encirclements_after_change", return_value=[]), \
                    patch.object(run, "detect_territory_conflicts", return_value=[]):
                worker_result = run.process_territory_rebuild_job("contract-worker")
                client = run.app.test_client()
                headers = self.session_generation.authenticate(client, "alice")
                refreshed = client.get(
                    "/api/map/target-snapshot",
                    headers=headers,
                ).get_json()

            self.assertTrue(worker_result["ok"])
            self.assertIsNone(ownership.get(abandoned_target_id))
            self.assertNotIn(
                abandoned_label,
                {item["label"] for item in store.list_captured_targets("alice")},
            )
            self.assertNotIn(
                abandoned_target_id,
                {item.get("target_id") for item in refreshed["captured_targets"]},
            )
            self.assertTrue(all(
                abandoned_label not in {vertex.get("label") for vertex in area.get("vertices") or []}
                for area in store.list_player_areas("alice")
            ))
        finally:
            self._cleanup(path)

    def test_inherited_cluster_pillar_transfer_abandon_worker_refresh(self):
        self._assert_cluster_transfer_abandon_worker_refresh("B1")

    def test_inherited_cluster_inner_transfer_abandon_worker_refresh(self):
        self._assert_cluster_transfer_abandon_worker_refresh("B-inner")

    def test_encirclement_pair_scan_caches_profiles_and_rejects_geometry_before_store_members(self):
        attacker = {
            "id": 1,
            "owner_username": "alice",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        defender = {
            "id": 2,
            "owner_username": "bob",
            "vertices": [
                {"lat": 53.0, "lng": 22.0},
                {"lat": 53.0, "lng": 22.01},
                {"lat": 53.01, "lng": 22.0},
            ],
        }

        resolver = run.TerritoryEncirclementResolver(store=object(), conflict_store=object())
        with patch.object(
            run.user_store,
            "get_profile_identity",
            side_effect=lambda username: {"username": username, "clan": username},
        ) as get_profile, patch.object(
            run,
            "territory_area_cluster_members",
        ) as cluster_members:
            self.assertFalse(resolver.is_cluster_fully_encircled(attacker, defender))
            self.assertFalse(resolver.is_cluster_fully_encircled(attacker, defender))

        self.assertEqual(get_profile.call_count, 2)
        cluster_members.assert_not_called()

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

    def test_conflict_reveals_boundary_pillar_supporting_front_from_outside(self):
        supporting = captured("Supporting", 52.0, 21.0)
        supporting["target_id"] = "pillar-supporting"
        remote = captured("Remote", 52.01, 21.0)
        remote["target_id"] = "pillar-remote"
        outside_inner = captured("Outside inner", 52.08, 21.01)
        outside_inner.update({"target_id": "inner-outside", "stationary": False})
        area = {
            "id": 1,
            "owner_username": "alice",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        # Front przecina krawedz miedzy pierwszym i drugim filarem, ale oba
        # filary leza poza samym polygonem overlapu.
        intersection = [
            {"lat": 51.999, "lng": 21.004},
            {"lat": 52.001, "lng": 21.004},
            {"lat": 52.001, "lng": 21.006},
            {"lat": 51.999, "lng": 21.006},
        ]
        with patch.object(run, "territory_area_cluster_members", return_value={
            "pillars": [supporting, remote],
            "inners": [outside_inner],
            "objects": [supporting, remote, outside_inner],
            "valid": True,
        }):
            revealed = run.reveal_conflict_targets_for_group([area], [intersection])

        by_id = {item["target_id"]: item for item in revealed}
        self.assertIn("pillar-supporting", by_id)
        self.assertNotIn("pillar-remote", by_id)
        self.assertNotIn("inner-outside", by_id)

    def test_conflict_does_not_reveal_remote_edge_anchor(self):
        remote = captured("Remote support", 52.0, 21.0)
        remote["target_id"] = "pillar-remote-support"
        area = {
            "id": 1,
            "owner_username": "alice",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.1},
                {"lat": 52.1, "lng": 21.1},
                {"lat": 52.1, "lng": 21.0},
            ],
        }
        intersection = [
            {"lat": 51.999, "lng": 21.049},
            {"lat": 52.001, "lng": 21.049},
            {"lat": 52.001, "lng": 21.051},
            {"lat": 51.999, "lng": 21.051},
        ]
        with patch.object(run, "territory_area_cluster_members", return_value={
            "pillars": [remote], "inners": [], "objects": [remote], "valid": True,
        }):
            revealed, diagnostics = run.reveal_conflict_targets_for_group(
                [area], [intersection], return_diagnostics=True
            )

        self.assertEqual(revealed, [])
        self.assertEqual(diagnostics[0]["target_id"], "pillar-remote-support")
        self.assertGreater(
            diagnostics[0]["distance_meters"],
            run.TERRITORY_CONFLICT_REVEAL_MAX_DISTANCE_METERS,
        )

    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, username)
        return client, headers

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

        with patch.object(run.user_store, "get_profile_identity", side_effect=lambda username: {
            "username": username, "clan": "same-clan"
        }):
            self.assertEqual(run.build_territory_conflict_detection_plan(areas), [])

        with patch.object(run.user_store, "get_profile_identity", side_effect=lambda username: {
            "username": username, "clan": "alpha" if username == "alice" else "beta"
        }), patch.object(run.mail_store, "is_accepted_contact", return_value=True):
            plans = run.build_territory_conflict_detection_plan(areas)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["participants"], ["alice", "bob"])

    def test_periodic_reconciler_queues_missing_visible_pillar(self):
        conflict = {
            "conflict_id": "conflict-watchdog",
            "participants": ["alice", "bob"],
            "conflict_version": 4,
            "status": "active",
        }
        target = captured("Missing", 52.0, 21.0)
        target["target_id"] = "pillar-missing"
        expected = [{
            "target_id": "pillar-missing",
            "owner_username": "bob",
            "status": "contested",
            "captured": False,
            "target": target,
        }]
        with patch.object(run.territory_store, "list_player_areas", return_value=[]), \
                patch.object(run.territory_store, "list_all_captured_targets", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[conflict]), \
                patch.object(run.territory_conflict_store, "list_pillars", return_value=[]), \
                patch.object(run, "build_territory_conflict_detection_plan", return_value=[]), \
                patch.object(run, "_conflict_rebuild_targets", return_value=expected), \
                patch.object(run, "request_conflict_rebuild", return_value={}) as enqueue:
            reports = run.reconcile_active_territory_conflicts(reduce_unlinkable=True)

        self.assertEqual(reports[0]["missing_ids"], ["pillar-missing"])
        self.assertEqual(reports[0]["action"], "rebuild_queued")
        enqueue.assert_called_once_with(
            "conflict-watchdog",
            reason="periodic_consistency_reconcile",
            requested_version=4,
        )

    def test_periodic_reconciler_never_reduces_remote_supports(self):
        conflict = {
            "conflict_id": "conflict-read-only-watchdog",
            "participants": ["alice", "bob"],
            "conflict_version": 7,
            "status": "active",
        }
        remote = captured("Remote support", 52.08, 21.08)
        remote["target_id"] = "pillar-remote"
        diagnostics = [{
            "target_id": "pillar-remote",
            "distance_meters": 5619.1,
            "target": remote,
        }]
        with patch.object(run.territory_store, "list_player_areas", return_value=[]), \
                patch.object(run.territory_store, "list_all_captured_targets", return_value=[remote]), \
                patch.object(run.territory_store, "save_captured_target") as save, \
                patch.object(run.territory_conflict_store, "list_active", return_value=[conflict]), \
                patch.object(run.territory_conflict_store, "list_pillars", return_value=[]), \
                patch.object(run, "build_territory_conflict_detection_plan", return_value=[]), \
                patch.object(run, "_conflict_rebuild_targets", return_value=[]), \
                patch.object(run, "_conflict_rebuild_scope", return_value=([], [])), \
                patch.object(run, "reveal_conflict_targets_for_group", return_value=([], diagnostics)), \
                patch.object(run, "request_conflict_rebuild") as enqueue:
            reports = run.reconcile_active_territory_conflicts(reduce_unlinkable=True)

        self.assertEqual(reports[0]["action"], "remote_anomaly")
        self.assertEqual(reports[0]["reduced_ids"], [])
        self.assertEqual(reports[0]["deferred_remote_ids"], ["pillar-remote"])
        save.assert_not_called()
        enqueue.assert_not_called()

    def test_conflict_plan_selection_rejects_remote_same_participants_front(self):
        conflict = {
            "conflict_id": "conflict-local",
            "participants": ["alice", "bob"],
            "area_ids": ["old-a", "old-b"],
        }
        local_geometry = [
            {"lat": 52.0, "lng": 21.0},
            {"lat": 52.002, "lng": 21.0},
            {"lat": 52.0, "lng": 21.002},
        ]
        remote_geometry = [
            {"lat": 52.1, "lng": 21.1},
            {"lat": 52.102, "lng": 21.1},
            {"lat": 52.1, "lng": 21.102},
        ]
        local_plan = {
            "participants": ["alice", "bob"],
            "area_ids": ["new-a", "new-b"],
            "intersections": [local_geometry],
        }
        remote_plan = {
            "participants": ["alice", "bob"],
            "area_ids": ["remote-a", "remote-b"],
            "intersections": [remote_geometry],
        }
        with patch.object(run.territory_conflict_store, "list_fronts", return_value=[{
            "front_id": "front-local", "geometry": local_geometry,
        }]):
            selected = run._matching_conflict_detection_plans(
                conflict, [local_plan, remote_plan]
            )

        self.assertEqual(selected, [local_plan])

    def test_reconcile_rollback_restores_stationary_geometry_target(self):
        conflict = {
            "conflict_id": "conflict-rollback",
            "participants": ["alice", "bob"],
            "conflict_version": 8,
        }
        reduced = captured("Reduced", 52.0, 21.0)
        reduced.update({
            "target_id": "pillar-reduced",
            "stationary": False,
            "territory_reconcile_reason": "remote_front_support",
        })
        with patch.object(run.territory_conflict_store, "list_active", return_value=[conflict]), \
                patch.object(run.territory_store, "list_captured_targets", side_effect=lambda owner: [reduced] if owner == "bob" else []), \
                patch.object(run.territory_store, "save_captured_target", side_effect=lambda owner, target: target) as save, \
                patch.object(run.user_store, "get_profile", return_value={"level": 3}), \
                patch.object(run, "rebuild_player_areas_with_territory_delta", return_value=[]) as rebuild, \
                patch.object(run, "request_conflict_rebuild", return_value={}) as enqueue:
            restored = run.restore_territory_reconcile_targets()

        self.assertEqual(restored, {"bob": ["pillar-reduced"]})
        recovered = save.call_args.args[1]
        self.assertTrue(recovered["stationary"])
        self.assertNotIn("territory_reconcile_reason", recovered)
        rebuild.assert_called_once()
        enqueue.assert_called_once()

    def test_single_pillar_capture_does_not_absorb_foreign_inner(self):
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
                captured_trigger = conflict_store.capture_pillar(
                    conflict["conflict_id"], "bob-trigger", trigger, "alice",
                    previous_owner_username="bob", action_id="test-trigger-capture",
                )
                self.assertTrue(captured_trigger["changed"])
                resolver = run.TerritoryEncirclementResolver(store, conflict_store)
                resolved = resolver.detect_encircled_clusters(
                    apply=True, actor_username="alice"
                )

            self.assertEqual(resolved, [])
            self.assertEqual(
                {item["label"] for item in store.list_captured_targets("bob")},
                {"B inner", "B trigger"},
            )
            self.assertNotIn("B inner", {item["label"] for item in store.list_captured_targets("alice")})
            pillars = conflict_store.list_pillars(conflict["conflict_id"])
            self.assertEqual(sum(bool(pillar["captured"]) for pillar in pillars), 1)
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
                snapshot = run.build_territory_control_snapshot(
                    "alice", context=territory_context()
                )

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
                snapshot = run.build_territory_control_snapshot(
                    "alice", context=territory_context()
                )

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
                dissolved = run.build_territory_control_snapshot(
                    "alice", context=territory_context()
                )

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

    def test_endpoint_uses_canonical_context_and_never_loads_profile(self):
        path = self._temp_db()
        try:
            store = TerritoryStore(db_path=str(path))
            conflict_store = TerritoryConflictStore(db_path=str(path))
            store.save_captured_target("alice", captured("A", 52.0, 21.0))
            client, headers = self._client_with_user("alice")

            with patch.object(run, "territory_store", store), \
                    patch.object(run, "territory_conflict_store", conflict_store), \
                    patch.object(run, "territory_control_load_context", return_value=territory_context()), \
                    patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile load should not run")), \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
                response = client.get("/api/ghost-control/territory", headers=headers)

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

            with patch.object(run.user_store, "get_profile_identity", side_effect=fake_profile), \
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
        profile = installed_profile(
            "alice", level=4, clan="Siatka Widmo", apps=[]
        )
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
                return installed_profile(
                    "bob", level=3, clan="Siatka Widmo", apps=[]
                )
            return None

        client, headers = self._client_with_user("alice")
        with patch.object(run, "territory_store", FakeTerritoryStoreForMap()), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", side_effect=fake_profile), \
                patch.object(run.mail_store, "is_accepted_contact", return_value=False), \
                patch.object(run, "get_active_conflicts_for_player", return_value=[]), \
                patch.object(run, "contested_targets_from_active_conflicts", return_value=[]):
            response = client.get("/api/map/player-areas", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        inner = next(area for area in payload["areas"] if area["id"] == "inner")
        self.assertEqual(inner["status"], "active")
        self.assertFalse(inner["exposed"])

    def test_map_player_areas_survives_optional_read_model_failures(self):
        profile = installed_profile(
            "alice", level=4, clan="Siatka Widmo", apps=[]
        )
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

        client, headers = self._client_with_user("alice")
        with patch.object(run, "territory_store", FragileTerritoryStoreForMap()), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_stale_territory_polygons", side_effect=AssertionError("read endpoint must not rebuild")), \
                patch.object(
                    run.territory_conflict_store,
                    "list_latest_snapshots_for_player",
                    side_effect=RuntimeError("conflict snapshot store busy"),
                ):
            response = client.get("/api/map/player-areas", headers=headers)

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
            local_users = UserStore(db_path=str(path), seed_path=str(path) + ".missing")
            for username, clan in (("alice", "Alpha"), ("bob", "Beta")):
                local_users.save_profile_guarded(
                    installed_profile(username, level=3, clan=clan),
                    expected_revision=0,
                    source="test.territory_control.create",
                    allow_create=True,
                )
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
            ownership = TerritoryTargetOwnershipStore(str(path))
            for transferred_label in ("B1", "B2", "B3", "B-inner"):
                transferred_target = next(
                    target for target in store.list_captured_targets("alice")
                    if target["label"] == transferred_label
                )
                canonical = ownership.get(transferred_target["target_id"])
                self.assertIsNotNone(canonical)
                self.assertEqual(canonical["owner_username"], "alice")
                self.assertEqual(canonical["target"]["previous_owner_username"], "bob")
            self.assertEqual(store.list_player_areas("bob"), [])
            self.assertGreaterEqual(len(store.list_player_areas("alice")), 1)
            resolved_conflict = conflict_store.get_by_key("alice-bob-test")
            self.assertEqual(resolved_conflict["status"], "resolved")
            self.assertEqual(resolved_conflict["resolution_reason"], "encirclement")
            rewarded_profile = local_users.get_profile("alice")
            self.assertEqual(result["transferred_pillar_count"], 3)
            self.assertTrue(result["strategic_reward"]["ok"])
            self.assertEqual(rewarded_profile["level"], 5)
            self.assertEqual(rewarded_profile["respect"], 6)

            with patch.object(run, "load_profile_readonly", return_value={"level": 3}):
                repeated = run.TerritoryEncirclementResolver(store, conflict_store).detect_encircled_clusters(apply=True)
            self.assertEqual(repeated, [])
            self.assertEqual({target["label"] for target in store.list_captured_targets("bob")}, {"B-outside"})
        finally:
            self._cleanup(path)


if __name__ == "__main__":
    unittest.main()
