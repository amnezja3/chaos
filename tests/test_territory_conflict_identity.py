import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from database import TerritoryConflictStore


class TerritoryConflictIdentityTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        handle.close()
        self.path = Path(handle.name)
        self.store = TerritoryConflictStore(db_path=str(self.path))

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{self.path}{suffix}")
            for attempt in range(5):
                try:
                    if candidate.exists():
                        candidate.unlink()
                    break
                except PermissionError:
                    if attempt == 4:
                        break
                    time.sleep(0.05)

    @staticmethod
    def payload(key="geometry-a", participants=None, intersections=None, targets=None):
        return {
            "conflict_key": key,
            "participants": participants or ["alice", "bob"],
            "area_ids": [1, 2],
            "intersection": [[52.0, 21.0], [52.1, 21.0], [52.0, 21.1]],
            "intersections": intersections or [
                [[52.0, 21.0], [52.1, 21.0], [52.0, 21.1]],
            ],
            "targets": targets or [],
            "status": "active",
            "source_event": "test",
        }

    def test_participant_order_and_geometry_change_keep_stable_identity(self):
        first = self.store.upsert_conflict(self.payload())
        changed = self.payload(
            key="geometry-b",
            participants=["bob", "alice"],
            intersections=[[[52.0, 21.0], [52.2, 21.0], [52.0, 21.2]]],
        )
        second = self.store.upsert_conflict(changed)

        self.assertEqual(second["conflict_id"], first["conflict_id"])
        self.assertEqual(second["conflict_key"], first["conflict_key"])
        self.assertEqual(second["participant_key"], "alice::bob")
        self.assertEqual(second["conflict_version"], first["conflict_version"])
        self.assertEqual(second["geometry_version"], first["geometry_version"] + 1)

    def test_noop_does_not_increment_versions(self):
        first = self.store.upsert_conflict(self.payload())
        second = self.store.upsert_conflict(self.payload(participants=["bob", "alice"]))
        self.assertEqual(second["conflict_version"], first["conflict_version"])
        self.assertEqual(second["geometry_version"], first["geometry_version"])

    def test_domain_change_only_increments_conflict_version(self):
        first = self.store.upsert_conflict(self.payload())
        target = {"target": {"lat": 52.0, "lng": 21.0}, "status": "contested"}
        second = self.store.upsert_conflict(self.payload(targets=[target]))
        self.assertEqual(second["conflict_version"], first["conflict_version"] + 1)
        self.assertEqual(second["geometry_version"], first["geometry_version"])

    @staticmethod
    def pillar(target_id, lat=52.0, lng=21.0, owner="alice"):
        return {
            "target_id": target_id,
            "owner": owner,
            "owner_username": owner,
            "status": "contested",
            "captured": False,
            "target": {
                "target_id": target_id,
                "lat": lat,
                "lng": lng,
                "label": target_id,
                "owner_username": owner,
            },
        }

    def test_pillar_coordinates_are_not_identity_or_domain_version(self):
        first = self.store.upsert_conflict(self.payload(targets=[self.pillar("pillar-a")]))
        moved = self.store.upsert_conflict(self.payload(
            targets=[self.pillar("pillar-a", lat=52.25, lng=21.25)]
        ))

        self.assertEqual(moved["conflict_version"], first["conflict_version"])
        self.assertEqual(len(moved["targets"]), 1)
        self.assertEqual(moved["targets"][0]["target_id"], "pillar-a")
        self.assertEqual(moved["targets"][0]["target"]["lat"], 52.25)

    def test_two_target_ids_can_share_coordinates(self):
        conflict = self.store.upsert_conflict(self.payload(targets=[
            self.pillar("pillar-a"), self.pillar("pillar-b"),
        ]))

        self.assertEqual(
            {item["target_id"] for item in conflict["targets"]},
            {"pillar-a", "pillar-b"},
        )

    def test_capture_is_exact_and_action_receipt_is_idempotent(self):
        conflict = self.store.upsert_conflict(self.payload(targets=[
            self.pillar("pillar-a"), self.pillar("pillar-b"),
        ]))
        first = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", self.pillar("pillar-a"),
            "bob", previous_owner_username="alice", action_id="action-1",
        )
        duplicate = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", self.pillar("pillar-a"),
            "bob", previous_owner_username="alice", action_id="action-1",
        )

        self.assertTrue(first["changed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(duplicate["changed"])
        targets = {item["target_id"]: item for item in first["conflict"]["targets"]}
        self.assertTrue(targets["pillar-a"]["captured"])
        self.assertEqual(targets["pillar-a"]["owner_username"], "bob")
        self.assertFalse(targets["pillar-b"]["captured"])
        self.assertEqual(
            first["conflict"]["conflict_version"],
            conflict["conflict_version"] + 1,
        )
        self.assertEqual(
            first["conflict"]["geometry_version"],
            conflict["geometry_version"],
        )
        self.assertEqual(first["conflict"]["status"], "changing")
        self.assertEqual(first["conflict"]["geometry_status"], "dirty")
        self.assertEqual(duplicate["conflict"]["conflict_version"], first["conflict"]["conflict_version"])
        events = self.store.list_events(conflict["conflict_id"])
        self.assertEqual(sum(event["type"] == "conflict.rebuild_requested" for event in events), 1)

    def test_already_captured_pillar_does_not_change_version_or_request_rebuild(self):
        pillar = self.pillar("pillar-a")
        conflict = self.store.upsert_conflict(self.payload(targets=[pillar]))
        captured = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", pillar,
            "bob", previous_owner_username="alice", action_id="action-1",
        )
        already_captured = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", pillar,
            "bob", previous_owner_username="alice", action_id="action-2",
        )

        self.assertFalse(already_captured["changed"])
        self.assertFalse(already_captured["duplicate"])
        self.assertEqual(already_captured["reason"], "already_captured")
        self.assertEqual(
            already_captured["conflict"]["conflict_version"],
            captured["conflict"]["conflict_version"],
        )
        events = self.store.list_events(conflict["conflict_id"])
        self.assertEqual(
            sum(event["type"] == "conflict.pillar_captured" for event in events),
            1,
        )
        self.assertEqual(
            sum(event["type"] == "conflict.rebuild_requested" for event in events),
            1,
        )

    def test_stale_geometry_snapshot_cannot_revert_captured_pillar(self):
        initial_target = self.pillar("pillar-a")
        conflict = self.store.upsert_conflict(self.payload(targets=[initial_target]))
        captured = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", initial_target,
            "bob", previous_owner_username="alice", action_id="action-2",
        )
        stale = self.store.upsert_conflict({
            **self.payload(targets=[self.pillar("pillar-a", lat=52.5, lng=21.5)]),
            "conflict_id": conflict["conflict_id"],
            "status": "changing",
            "geometry_status": "dirty",
        })

        self.assertEqual(stale["conflict_version"], captured["conflict"]["conflict_version"])
        self.assertTrue(stale["targets"][0]["captured"])
        self.assertEqual(stale["targets"][0]["owner_username"], "bob")
        self.assertEqual(stale["targets"][0]["target"]["lat"], 52.5)

    def test_recapture_without_action_id_is_not_permanently_deduplicated(self):
        pillar = self.pillar("pillar-a")
        conflict = self.store.upsert_conflict(self.payload(targets=[pillar]))

        captured = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", pillar,
            "bob", previous_owner_username="alice",
        )
        recaptured = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", pillar,
            "alice", previous_owner_username="bob",
        )
        captured_again = self.store.capture_pillar(
            conflict["conflict_id"], "pillar-a", pillar,
            "bob", previous_owner_username="alice",
        )

        self.assertTrue(captured["changed"])
        self.assertTrue(recaptured["changed"])
        self.assertTrue(captured_again["changed"])
        self.assertFalse(captured_again["duplicate"])
        self.assertEqual(
            captured_again["conflict"]["conflict_version"],
            conflict["conflict_version"] + 3,
        )
        target = captured_again["conflict"]["targets"][0]
        self.assertTrue(target["captured"])
        self.assertEqual(target["owner_username"], "bob")
        events = self.store.list_events(conflict["conflict_id"])
        self.assertEqual(
            sum(event["type"] == "conflict.pillar_captured" for event in events),
            1,
        )
        self.assertEqual(
            sum(event["type"] == "conflict.pillar_recaptured" for event in events),
            2,
        )
        self.assertEqual(
            sum(event["type"] == "conflict.rebuild_requested" for event in events),
            3,
        )

    def test_disjoint_geometry_for_same_participants_keeps_one_cycle(self):
        first = self.store.upsert_conflict(self.payload(key="front-a"))
        second = self.store.upsert_conflict({
            **self.payload(key="front-b"),
            "area_ids": [10, 11],
        })

        self.assertEqual(second["conflict_id"], first["conflict_id"])
        candidates = self.store.list_open_by_participant_key("alice::bob")
        self.assertEqual([item["conflict_id"] for item in candidates], [first["conflict_id"]])

    def test_geometry_change_selects_cycle_by_area_overlap(self):
        first = self.store.upsert_conflict(self.payload(key="front-a"))
        changed = self.store.upsert_conflict({
            **self.payload(key="front-a-rebuilt"),
            "area_ids": [2, 3],
        })

        self.assertEqual(changed["conflict_id"], first["conflict_id"])
        self.assertEqual(changed["geometry_version"], first["geometry_version"] + 1)

    def test_single_participant_cycle_survives_complete_geometry_replacement(self):
        first = self.store.upsert_conflict(self.payload(key="front-a"))
        changed = self.store.upsert_conflict({
            **self.payload(key="front-b"),
            "area_ids": [10, 11],
        })

        self.assertEqual(changed["conflict_id"], first["conflict_id"])

    def test_resolved_cycle_is_not_reopened(self):
        first = self.store.upsert_conflict(self.payload())
        resolved = self.store.upsert_conflict({
            **first,
            "status": "resolved",
            "resolution_reason": "encirclement",
        })
        second = self.store.upsert_conflict(self.payload())

        self.assertEqual(resolved["status"], "resolved")
        self.assertNotEqual(second["conflict_id"], first["conflict_id"])
        self.assertNotEqual(second["conflict_key"], first["conflict_key"])
        self.assertTrue(second["conflict_key"].startswith("geometry-a:cycle:"))

    def test_stable_numeric_and_legacy_references_resolve_same_cycle(self):
        conflict = self.store.upsert_conflict(self.payload())
        for reference in (
            conflict["id"],
            conflict["conflict_id"],
            conflict["conflict_key"],
            conflict["legacy_conflict_key"],
        ):
            self.assertEqual(
                self.store.get_by_key(reference)["conflict_id"],
                conflict["conflict_id"],
            )

    def test_existing_database_migration_is_idempotent(self):
        original = self.store.upsert_conflict(self.payload())
        first_migration = TerritoryConflictStore(db_path=str(self.path))
        migrated = first_migration.get_by_key(original["id"])
        second_migration = TerritoryConflictStore(db_path=str(self.path))
        repeated = second_migration.get_by_key(original["id"])
        self.assertEqual(migrated["conflict_id"], original["conflict_id"])
        self.assertEqual(repeated["conflict_id"], migrated["conflict_id"])
        self.assertEqual(repeated["conflict_version"], migrated["conflict_version"])
        self.assertEqual(repeated["geometry_version"], migrated["geometry_version"])
        with sqlite3.connect(self.path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(territory_conflicts)")}
            row_count = conn.execute("SELECT COUNT(*) FROM territory_conflicts").fetchone()[0]
        self.assertIn("participant_key", columns)
        self.assertIn("geometry_version", columns)
        self.assertEqual(row_count, 1)

    @staticmethod
    def front_plan(area_ids=None, geometry=None):
        return {
            "participant_key": "alice::bob",
            "area_ids": area_ids or [1, 2],
            "pillar_ids": [],
            "geometry": geometry or [[52.0, 21.0], [52.1, 21.0], [52.0, 21.1]],
        }

    def test_rebuild_requests_keep_highest_version_and_exclusive_lease(self):
        conflict = self.store.upsert_conflict(self.payload())
        first = self.store.request_rebuild(conflict["conflict_id"], "pillar", 2)
        second = self.store.request_rebuild(conflict["conflict_id"], "territory", 5)
        stale = self.store.request_rebuild(conflict["conflict_id"], "retry", 3)

        self.assertEqual(first["requested_version"], 2)
        self.assertEqual(second["requested_version"], 5)
        self.assertEqual(stale["requested_version"], 5)
        lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-a")
        self.assertEqual(lease["processing_version"], 5)
        self.assertIsNone(self.store.claim_rebuild(conflict["conflict_id"], "worker-b"))

    def test_expired_rebuild_lease_can_be_taken_over(self):
        conflict = self.store.upsert_conflict(self.payload())
        self.store.request_rebuild(conflict["conflict_id"], "pillar", 2)
        self.assertIsNotNone(self.store.claim_rebuild(conflict["conflict_id"], "worker-a"))
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE territory_conflict_rebuilds SET lease_until = ? WHERE conflict_id = ?",
                ("2000-01-01T00:00:00", conflict["conflict_id"]),
            )

        takeover = self.store.claim_rebuild(conflict["conflict_id"], "worker-b")
        self.assertIsNotNone(takeover)
        self.assertEqual(takeover["lease_owner"], "worker-b")

    def test_newer_request_during_rebuild_schedules_another_pass(self):
        conflict = self.store.upsert_conflict(self.payload())
        self.store.request_rebuild(conflict["conflict_id"], "pillar", 2)
        lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-a")
        self.store.request_rebuild(conflict["conflict_id"], "newer-pillar", 3)

        result = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-a", lease["processing_version"],
            [self.front_plan()],
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["pending_newer"])
        next_lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-b")
        self.assertEqual(next_lease["processing_version"], 3)

    def test_identical_rebuild_is_noop_and_keeps_snapshot_version(self):
        conflict = self.store.upsert_conflict(self.payload())
        self.store.request_rebuild(conflict["conflict_id"], "initial", 1)
        lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-a")
        first = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-a", lease["processing_version"],
            [self.front_plan()],
        )
        first_snapshot = first["snapshot"]

        self.store.request_rebuild(conflict["conflict_id"], "retry", 1)
        retry_lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-b")
        retry = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-b", retry_lease["processing_version"],
            [self.front_plan()],
        )

        self.assertTrue(retry["ok"])
        self.assertFalse(retry["changed"])
        self.assertEqual(retry["snapshot"]["snapshot_version"], first_snapshot["snapshot_version"])
        self.assertEqual(
            len(self.store.list_events(conflict["conflict_id"], "conflict.geometry_rebuilt")),
            1,
        )

    def test_failed_rebuild_preserves_last_valid_snapshot(self):
        conflict = self.store.upsert_conflict(self.payload())
        self.store.request_rebuild(conflict["conflict_id"], "initial", 1)
        lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-a")
        published = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-a", lease["processing_version"],
            [self.front_plan()],
        )
        snapshot = published["snapshot"]

        self.store.request_rebuild(conflict["conflict_id"], "broken", 2)
        failed_lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-b")
        self.assertTrue(self.store.fail_rebuild(
            conflict["conflict_id"], "worker-b", failed_lease["processing_version"],
            "geometry failed",
        ))

        after = self.store.get_by_key(conflict["conflict_id"])
        self.assertEqual(after["geometry_version"], snapshot["geometry_version"])
        self.assertEqual(after["geometry_status"], "rebuild_failed")
        self.assertEqual(
            self.store.latest_snapshot(conflict["conflict_id"])["snapshot_version"],
            snapshot["snapshot_version"],
        )

    def test_legacy_conflict_without_snapshot_has_read_only_render_fallback(self):
        conflict = self.store.upsert_conflict(self.payload(targets=[self.pillar("pillar-a")]))

        state = self.store.latest_snapshot_state(conflict["conflict_id"])

        self.assertFalse(state["complete"])
        self.assertGreaterEqual(state["snapshot_version"], 1)
        self.assertEqual(len(state["fronts"]), 1)
        self.assertTrue(state["fronts"][0]["front_id"].startswith("front_legacy_"))
        self.assertEqual(state["pillars"][0]["target_id"], "pillar-a")

    def test_front_split_and_merge_preserve_parent_lineage(self):
        conflict = self.store.upsert_conflict(self.payload())
        self.store.request_rebuild(conflict["conflict_id"], "initial", 1)
        lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-a")
        initial = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-a", lease["processing_version"],
            [self.front_plan(area_ids=[1, 2])],
        )
        parent_id = initial["snapshot"]["fronts"][0]["front_id"]

        self.store.request_rebuild(conflict["conflict_id"], "split", 2)
        split_lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-b")
        split = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-b", split_lease["processing_version"],
            [
                self.front_plan(area_ids=[1], geometry=[[52.0, 21.0], [52.05, 21.0], [52.0, 21.05]]),
                self.front_plan(area_ids=[2], geometry=[[52.1, 21.1], [52.15, 21.1], [52.1, 21.15]]),
            ],
        )
        split_fronts = split["snapshot"]["fronts"]
        self.assertEqual(len(split_fronts), 2)
        self.assertTrue(all(front["parent_front_ids"] == [parent_id] for front in split_fronts))
        stored_fronts = {
            front["front_id"]: front
            for front in self.store.list_fronts(conflict["conflict_id"])
        }
        self.assertEqual(stored_fronts[parent_id]["status"], "split")

        self.store.request_rebuild(conflict["conflict_id"], "merge", 3)
        merge_lease = self.store.claim_rebuild(conflict["conflict_id"], "worker-c")
        merged = self.store.publish_rebuild(
            conflict["conflict_id"], "worker-c", merge_lease["processing_version"],
            [self.front_plan(area_ids=[1, 2])],
        )
        merged_front = merged["snapshot"]["fronts"][0]
        split_ids = {front["front_id"] for front in split_fronts}
        self.assertEqual(set(merged_front["parent_front_ids"]), split_ids)
        self.assertEqual(len(self.store.list_fronts(conflict["conflict_id"], active_only=True)), 1)
        events = self.store.list_events(conflict["conflict_id"])
        self.assertTrue(any(event["type"] == "conflict.front_split" for event in events))
        self.assertTrue(any(event["type"] == "conflict.front_merged" for event in events))


if __name__ == "__main__":
    unittest.main()
