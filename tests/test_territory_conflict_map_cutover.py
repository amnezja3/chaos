import inspect
import unittest
from unittest import mock

import run
from response_network.territory_delta import TerritoryDeltaPublisher, _conflict_payload


class TerritoryConflictMapCutoverTests(unittest.TestCase):
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

    def test_player_areas_endpoint_is_read_only(self):
        source = inspect.getsource(run.map_player_areas)

        self.assertIn("list_latest_snapshots_for_player", source)
        self.assertIn("territory_conflict_snapshot_mode", source)
        self.assertNotIn("sync_session_profile", source)
        self.assertNotIn("refresh_stale_territory_polygons", source)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", source)

    def test_capture_response_exposes_conflict_consolidation_diagnostics(self):
        source = inspect.getsource(run.gonna_win)

        self.assertIn("territory_conflict_consolidation", source)
        self.assertIn("territory_conflict_capture", source)
        self.assertIn("[TERRITORY_CAPTURE]", source)
        self.assertIn("[TERRITORY_CONSOLIDATION]", source)

    def test_frontend_has_monotonic_snapshot_registry_contract(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("window.territoryConflictRegistry", source)
        self.assertIn("window.territoryFrontLayers", source)
        self.assertIn("window.territoryConflictPillarLayers", source)
        self.assertIn("territory_conflict_version_gap", source)
        self.assertIn("incomingVersion < currentVersion", source)
        self.assertIn("conflictVersion < Number(previous.conflictVersion", source)
        self.assertIn("geometryVersion < Number(previous.geometryVersion", source)
        self.assertIn("reconcileTerritoryConflictSnapshots", source)
        self.assertIn("territory_conflict_snapshot_mode", source)
        self.assertNotIn("!version || snapshot.complete === false", source)
        self.assertIn("if (Array.isArray(vertex))", source)
        self.assertIn("layer._chaosLayerRegistry = 'territoryFrontLayers'", source)


if __name__ == "__main__":
    unittest.main()
