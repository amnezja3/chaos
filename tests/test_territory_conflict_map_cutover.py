import inspect
import pathlib
import unittest
from unittest import mock

import run
from response_network.territory_delta import TerritoryDeltaPublisher, _conflict_payload


class TerritoryConflictMapCutoverTests(unittest.TestCase):
    def setUp(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        self.map_template = (root / "templates" / "map_template.html").read_text(encoding="utf-8")

    @staticmethod
    def snapshot():
        return {
            "conflict": {
                "conflict_id": "conflict-1",
                "conflict_key": "alice::bob",
                "participants": ["alice", "bob"],
                "status": "active",
                "conflict_version": 7,
            },
            "fronts": [{
                "front_id": "front-1",
                "geometry": [[52.0, 21.0], [52.1, 21.0], [52.0, 21.1]],
            }],
            "pillars": [{"target_id": "pillar-1", "status": "contested"}],
            "snapshot_version": 9,
            "conflict_version": 7,
            "geometry_version": 5,
            "generated_at": "2026-08-04T10:00:00+00:00",
        }

    def test_projection_and_legacy_fields_share_one_snapshot(self):
        projected = run.project_territory_conflict_snapshot(self.snapshot())
        conflicts, areas, targets, captured = run.legacy_conflict_fields_from_snapshots([projected])

        self.assertEqual(projected["conflict_id"], "conflict-1")
        self.assertEqual(projected["snapshot_version"], 9)
        self.assertEqual(projected["fronts"][0]["front_id"], "front-1")
        self.assertEqual(projected["pillars"][0]["target_id"], "pillar-1")
        self.assertEqual(conflicts[0]["conflict_id"], projected["conflict_id"])
        self.assertEqual(areas[0]["snapshot_version"], projected["snapshot_version"])
        self.assertEqual(targets[0]["target_id"], projected["pillars"][0]["target_id"])
        self.assertEqual(captured, [])

    def test_projection_unwraps_registry_public_target_for_map_and_inners(self):
        snapshot = self.snapshot()
        snapshot["pillars"] = [{
            "target_id": "pillar-1",
            "owner_username": "bob",
            "status": "contested",
            "public_target": {
                "target_id": "pillar-1",
                "target": {"target_id": "pillar-1", "lat": 52.0, "lng": 21.0, "label": "Inner"},
            },
        }]

        projected = run.project_territory_conflict_snapshot(snapshot)
        conflicts, _, _, _ = run.legacy_conflict_fields_from_snapshots([projected])
        with mock.patch.object(run.user_store, "get_profile", return_value={}):
            contested = run.contested_targets_from_active_conflicts("alice", conflicts, areas=[])

        self.assertEqual(projected["pillars"][0]["target"]["lat"], 52.0)
        self.assertEqual(len(contested), 1)
        self.assertEqual(contested[0]["target_mode"], "territory_contest")

    def test_captured_pillar_is_attackable_only_for_opposing_participant(self):
        snapshot = self.snapshot()
        snapshot["pillars"] = [{
            "target_id": "pillar-captured",
            "owner_username": "alice",
            "captured_by": "alice",
            "captured": True,
            "status": "captured",
            "public_target": {
                "target": {"lat": 52.0, "lng": 21.0, "label": "Counter target"},
            },
        }]

        holder_view = run.project_territory_conflict_snapshot(snapshot, viewer_username="alice")
        opponent_view = run.project_territory_conflict_snapshot(snapshot, viewer_username="bob")

        self.assertTrue(holder_view["pillars"][0]["captured"])
        self.assertEqual(holder_view["pillars"][0]["status"], "captured")
        self.assertFalse(opponent_view["pillars"][0]["captured"])
        self.assertEqual(opponent_view["pillars"][0]["status"], "contested")
        self.assertTrue(opponent_view["pillars"][0]["canonical_captured"])

    def test_current_owner_hides_conflict_marker_when_captured_by_is_stale(self):
        snapshot = self.snapshot()
        snapshot["pillars"] = [{
            "target_id": "pillar-stale-capture-actor",
            "owner_username": "alice",
            "captured_by": "bob",
            "captured": True,
            "status": "captured",
            "public_target": {
                "target": {"lat": 52.0, "lng": 21.0, "label": "Owned target"},
            },
        }]

        holder_view = run.project_territory_conflict_snapshot(snapshot, viewer_username="alice")
        opponent_view = run.project_territory_conflict_snapshot(snapshot, viewer_username="bob")

        self.assertTrue(holder_view["pillars"][0]["captured"])
        self.assertEqual(holder_view["pillars"][0]["status"], "captured")
        self.assertFalse(opponent_view["pillars"][0]["captured"])
        self.assertEqual(opponent_view["pillars"][0]["status"], "contested")

    def test_projection_drops_historical_inner_outside_published_front(self):
        snapshot = self.snapshot()
        snapshot["pillars"] = [{
            "target_id": "stale-inner",
            "owner_username": "alice",
            "captured_by": "alice",
            "captured": True,
            "status": "captured",
            "public_target": {
                "target": {
                    "lat": 52.2,
                    "lng": 21.2,
                    "label": "Historical inner",
                    "node_role": "inner",
                },
            },
        }]

        projected = run.project_territory_conflict_snapshot(snapshot, viewer_username="bob")

        self.assertEqual(projected["pillars"], [])

    def test_conflict_delta_keeps_complete_canonical_snapshot(self):
        payload = _conflict_payload(self.snapshot(), reason="pillar_captured")

        self.assertEqual(payload["conflict_id"], "conflict-1")
        self.assertEqual(payload["snapshot_version"], 9)
        self.assertEqual(payload["conflict_version"], 7)
        self.assertEqual(payload["geometry_version"], 5)
        self.assertEqual(payload["fronts"][0]["front_id"], "front-1")
        self.assertEqual(payload["pillars"][0]["target_id"], "pillar-1")
        self.assertTrue(payload["complete"])

    def test_projection_exposes_dirty_snapshot_as_incomplete(self):
        snapshot = self.snapshot()
        snapshot.update({
            "conflict": {**snapshot["conflict"], "status": "changing", "geometry_status": "dirty"},
            "conflict_version": 8,
            "geometry_status": "dirty",
            "complete": False,
        })

        projected = run.project_territory_conflict_snapshot(snapshot)

        self.assertFalse(projected["complete"])
        self.assertEqual(projected["geometry_status"], "dirty")
        self.assertEqual(projected["conflict_version"], 8)

    def test_record_delta_uses_live_snapshot_state(self):
        dirty = {
            **self.snapshot(),
            "conflict": {**self.snapshot()["conflict"], "status": "changing", "geometry_status": "dirty"},
            "conflict_version": 8,
            "geometry_status": "dirty",
            "complete": False,
        }
        with mock.patch.object(run.territory_conflict_store, "latest_snapshot_state", return_value=dirty), \
                mock.patch.object(run.territory_delta_publisher, "record_conflict_changed", return_value=[]) as publish:
            run.record_territory_conflict_delta(dirty["conflict"], reason="pillar_captured")

        self.assertIs(publish.call_args.args[0], dirty)

    def test_conflict_delta_dedupe_uses_stable_conflict_id(self):
        bus = mock.Mock()
        publisher = TerritoryDeltaPublisher(delta_bus=bus)
        first = self.snapshot()
        second = self.snapshot()
        second["conflict"] = {**second["conflict"], "conflict_key": "new-geometry-key"}

        publisher.record_conflict_changed(first, reason="geometry")
        publisher.record_conflict_changed(second, reason="geometry")

        first_key = bus.record_change.call_args_list[0].kwargs["dedupe_key"]
        second_key = bus.record_change.call_args_list[2].kwargs["dedupe_key"]
        self.assertEqual(first_key, second_key)
        self.assertIn("conflict-1", first_key)

    def test_engagement_delta_dedupe_uses_stable_engagement_id_and_version(self):
        bus = mock.Mock()
        publisher = TerritoryDeltaPublisher(delta_bus=bus)
        engagement = {
            "engagement_id": "engagement-1",
            "snapshot_version": 7,
            "engagement_version": 4,
            "geometry_version": 6,
            "participant_usernames": ["a", "b"],
            "geometry": [[
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ]],
        }

        publisher.record_engagement_changed(engagement, usernames=["a"], reason="first")
        publisher.record_engagement_changed(
            {**engagement, "participant_usernames": ["b", "a", "c"]},
            usernames=["a"], reason="second",
        )

        first_key = bus.record_change.call_args_list[0].kwargs["dedupe_key"]
        second_key = bus.record_change.call_args_list[1].kwargs["dedupe_key"]
        self.assertEqual(first_key, second_key)
        self.assertIn("engagement-1:7", first_key)

    def test_player_areas_endpoint_is_read_only(self):
        source = inspect.getsource(run.map_player_areas)

        self.assertIn("list_latest_snapshots_for_player", source)
        self.assertIn("territory_conflict_snapshot_mode", source)
        self.assertNotIn("sync_session_profile", source)
        self.assertNotIn("refresh_stale_territory_polygons", source)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", source)

    def test_every_area_publication_recovers_canonical_polygon_geometry(self):
        source = self.map_template
        self.assertIn("Every\n                // canonical publication may add, reshape or remove a polygon", source)
        self.assertIn("territory_publication:${territoryReason}", source)
        self.assertNotIn("entry.layer._chaosTerritorySnapshot = nextArea", source)

    def test_territory_snapshot_recovery_retries_after_inflight_or_abort(self):
        source = self.map_template
        self.assertIn("recoveryDelays = [900, 1800, 3500]", source)
        self.assertIn("if (!refreshed && recoveryAttempt < recoveryDelays.length - 1)", source)
        self.assertIn("window.requestTerritorySnapshotRecovery(reason, recoveryAttempt + 1)", source)

    def test_full_snapshot_removes_canonical_layers_before_reconciliation(self):
        source = self.map_template
        self.assertIn("function clearCanonicalTerritoryConflictLayers()", source)
        refresh_start = source.index("window.refreshPlayerAreas = async function")
        refresh_source = source[refresh_start:]
        clear_index = refresh_source.index("clearCanonicalTerritoryConflictLayers();")
        reconcile_index = refresh_source.index("reconcileTerritoryConflictSnapshots(")
        self.assertLess(clear_index, reconcile_index)
        for registry in (
            "territoryFrontLayers",
            "territoryConflictPillarLayers",
            "territoryEngagementLayers",
        ):
            self.assertIn(f"Object.keys(window.{registry})", source)

    def test_capture_response_exposes_conflict_consolidation_diagnostics(self):
        source = inspect.getsource(run.gonna_win)

        self.assertIn("territory_conflict_consolidation", source)
        self.assertIn("territory_conflict_capture", source)
        self.assertIn("[TERRITORY_CAPTURE]", source)
        self.assertIn("[TERRITORY_CONSOLIDATION_QUEUED]", source)
        self.assertNotIn("consolidate_conflict_rebuild(", source)
        self.assertNotIn("detect_territory_conflicts(", source)
        self.assertIn("defer_conflict_rebuild", source)
        self.assertIn("sync_session_profile(rebuild_territory=False, persist_normalization=False)", source)
        self.assertIn('"deferred": True', source)
        self.assertIn("TERRITORY_CAPTURE_PROFILE_SYNC_DEFERRED", source)
        self.assertIn("if defer_conflict_rebuild", source)
        self.assertIn("discover_and_queue_new_territory_conflicts", source)
        self.assertIn("defer_conflict_rebuild = True", source)

    def test_ordinary_capture_publishes_map_state_at_commit_boundary(self):
        source = inspect.getsource(run.gonna_win)

        save_index = source.index(
            'territory_store.save_captured_target(session["user"], captured_target)'
        )
        committed_delta_index = source.index('reason="gonna_win_capture_committed"')
        ghostnetwork_index = source.index("safe_ghostnetwork_on_target_hacked(")
        rebuild_index = source.index("rebuild_player_areas_with_territory_delta(")
        profile_update_index = source.index("mgr.update_profile(capture_profile_update)")

        self.assertLess(save_index, committed_delta_index)
        self.assertLess(committed_delta_index, ghostnetwork_index)
        self.assertLess(committed_delta_index, rebuild_index)
        self.assertLess(committed_delta_index, profile_update_index)

    def test_duplicate_map_response_can_reconcile_captured_marker(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        duplicate_index = source.index("if (data.duplicate) {")
        duplicate_branch = source[duplicate_index:duplicate_index + 900]
        self.assertIn("data.captured_target", duplicate_branch)
        self.assertIn("window.markMapTargetHacked(data.captured_target)", duplicate_branch)

    def test_map_boot_projects_canonical_captured_targets_without_rebuild(self):
        source = inspect.getsource(run.map_view)

        self.assertIn("map_profile_boot_payload(profile)", source)
        self.assertIn("/api/map/target-snapshot", source)
        self.assertNotIn('merge_captured_targets_into_profile(session["user"], profile)', source)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", source)

    def test_worker_conflict_publication_triggers_read_only_marker_recovery(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("conflictReason === 'conflict_consolidated'", source)
        self.assertIn(
            "requestTerritorySnapshotRecovery('conflict_consolidated_complete')",
            source,
        )

    def test_encirclement_delta_triggers_read_only_marker_recovery(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("type === 'territory.encirclement_resolved'", source)
        self.assertIn(
            "requestTerritorySnapshotRecovery('territory_encirclement_resolved')",
            source,
        )
        self.assertIn("territoryReason ? `territory_publication:${territoryReason}`", source)

    def test_map_has_manual_full_refresh_control(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("ManualMapRefreshControl", source)
        self.assertIn("Odśwież stan mapy", source)
        self.assertIn("window.location.reload()", source)
        self.assertIn("saveManualMapViewport()", source)
        self.assertIn("restoreManualMapViewport()", source)
        self.assertIn("sessionStorage.removeItem(MANUAL_MAP_VIEW_STORAGE_KEY)", source)
        self.assertIn("chaos-map-refresh-icon", source)
        self.assertIn("showMapPreloader(", source)
        self.assertIn("disableMapGameplay()", source)

        consolidation_source = inspect.getsource(run.consolidate_conflict_rebuild)
        self.assertIn("_conflict_rebuild_targets", consolidation_source)
        self.assertIn("reconcile_rebuild_pillars", consolidation_source)

    def test_stale_conflict_id_does_not_capture_pillar_for_third_party(self):
        stale_conflict = {
            "conflict_id": "old-main-neo1",
            "participants": ["main", "neo1"],
            "status": "active",
        }
        target = {
            "target_id": "pillar-from-old-cycle",
            "conflict_id": "old-main-neo1",
            "lat": 52.32,
            "lng": 21.0,
        }
        with mock.patch.object(
            run.territory_conflict_store, "get_by_key", return_value=stale_conflict
        ), mock.patch.object(run.territory_conflict_store, "capture_pillar") as capture:
            affected = run.capture_conflict_pillar(
                target,
                captured_by_username="trolu2",
                previous_owner_username="main",
            )

        self.assertEqual(affected, [])
        capture.assert_not_called()

    def test_player_actor_snapshot_projects_current_positions_on_current_territory(self):
        source = inspect.getsource(run.map_player_actors)

        self.assertIn('actor_profile.get("current_position")', source)
        self.assertIn("territory_point_in_polygon_or_boundary", source)
        self.assertIn("viewer_areas", source)
        self.assertIn("user_store.list_profiles()", source)
        self.assertNotIn("list_recent_area_intruders", source)
        self.assertNotIn("sync_session_profile", source)

    def test_frontend_has_monotonic_snapshot_registry_contract(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("window.territoryConflictRegistry", source)
        self.assertIn("window.territoryFrontLayers", source)
        self.assertIn("window.territoryConflictPillarLayers", source)
        self.assertIn("territory_conflict_version_gap", source)
        self.assertIn("incomingVersion < currentVersion", source)
        self.assertNotIn("incomingVersion === currentVersion\n                        && incomingConflictVersion", source)
        self.assertIn("conflictVersion < Number(previous.conflictVersion", source)
        self.assertIn("publishedGeometryReplacesPrevious", source)
        self.assertIn("registeredFrontIds", source)
        self.assertIn("polygon._chaosLayerRegistry = 'territoryAreaLayers'", source)
        self.assertIn("territoryClanPalette", source)
        self.assertIn("'phantom mesh': { stroke: '#00CFA6'", source)
        self.assertIn("territoryViewerClan", source)
        self.assertIn("window.mapViewerClan", source)
        self.assertIn("(isMine || isCrew) ? null : '8 6'", source)
        self.assertIn("geometryVersion < Number(previous.geometryVersion", source)
        self.assertIn("reconcileTerritoryConflictSnapshots", source)
        self.assertIn("territory_conflict_snapshot_mode", source)
        self.assertNotIn("!version || snapshot.complete === false", source)
        self.assertIn("if (Array.isArray(vertex))", source)
        self.assertIn("layer._chaosLayerRegistry = 'territoryFrontLayers'", source)
        self.assertIn("layer._chaosTerritoryInteractiveMarker = true", source)
        self.assertIn("'territoryConflictPillarMarker'", source)
        self.assertIn("hasLegacyPillarLayers", source)
        self.assertIn("hasMissingCanonicalLayers", source)
        self.assertIn("expectedPillarIds", source)
        self.assertIn("territoryPillarForViewer", source)
        self.assertIn("territoryPillarIsOwnedByViewer", source)
        self.assertIn("territoryInnerInsideSnapshotFront", source)
        self.assertIn("territoryPointInPolygonOrBoundary", source)
        self.assertIn("window.mapViewerUsername", source)
        self.assertNotIn("const layer = L.circleMarker(point", source)

        self.assertIn("window.territoryEngagementRegistry", source)
        self.assertIn("window.territoryEngagementLayers", source)
        self.assertIn("territory.engagement_changed", source)
        self.assertIn("territory_engagement_version_gap", source)
        self.assertIn("reconcileTerritoryEngagementSnapshots", source)
        self.assertIn("data.territory_engagement_snapshots", source)

    def test_frontend_keeps_large_valid_territories_and_boots_player_actors(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("latSpan <= 1.0 && lngSpan <= 1.0", source)
        self.assertIn("'player_actors', window.refreshPlayerActors", source)
        self.assertIn("fetch('/api/map/player-actors'", source)
        self.assertIn("signal: controller.signal", source)
        self.assertIn("window.playerActorRefreshPromise", source)
        self.assertIn("controller.abort(), 45000", source)
        self.assertIn("[map actors] response received", source)
        self.assertIn("[map actors] marker created", source)
        self.assertIn("[map actors] render complete", source)


if __name__ == "__main__":
    unittest.main()
