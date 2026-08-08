import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from database import TerritoryConflictEngagementStore, TerritoryConflictStore


def candidate(conflicts=("a-d", "b-d"), suffix="one", bbox=None):
    bbox = bbox or {
        "min_lat": 52.0, "min_lng": 21.0,
        "max_lat": 52.01, "max_lng": 21.01,
    }
    memberships = [
        {"conflict_id": conflict_id, "front_id": f"{conflict_id}:{suffix}"}
        for conflict_id in conflicts
    ]
    return {
        "member_conflict_ids": list(conflicts),
        "member_front_ids": [item["front_id"] for item in memberships],
        "member_front_memberships": memberships,
        "participant_usernames": ["a", "b", "d"],
        "hostile_clan_groups": {
            "clan:red": ["a"], "clan:blue": ["b"], "clan:green": ["d"],
        },
        "overlap_geometry": [[
            {"lat": bbox["min_lat"], "lng": bbox["min_lng"]},
            {"lat": bbox["min_lat"], "lng": bbox["max_lng"]},
            {"lat": bbox["max_lat"], "lng": bbox["max_lng"]},
        ]],
        "overlap_bbox": bbox,
    }


class TerritoryConflictEngagementStoreTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        handle.close()
        self.path = Path(handle.name)
        self.store = TerritoryConflictEngagementStore(str(self.path))

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            path = Path(f"{self.path}{suffix}")
            for attempt in range(5):
                try:
                    if path.exists():
                        path.unlink()
                    break
                except PermissionError:
                    if attempt == 4:
                        break
                    time.sleep(0.05)

    def publish(self, candidates, owner="worker-a"):
        return self.store.reconcile_candidates(candidates, owner, lease_seconds=30)

    def test_stable_id_and_noop_keep_all_versions(self):
        first_result = self.publish([candidate()])
        first = first_result["changed"][0]
        second_result = self.publish([candidate()])
        second = self.store.get(first["engagement_id"])

        self.assertEqual(second_result["changed"], [])
        self.assertEqual(second["engagement_id"], first["engagement_id"])
        self.assertEqual(second["engagement_version"], first["engagement_version"])
        self.assertEqual(second["geometry_version"], first["geometry_version"])
        self.assertEqual(second["snapshot_version"], first["snapshot_version"])

    def test_join_and_leave_update_many_to_many_membership(self):
        first = self.publish([candidate()])["changed"][0]
        joined_candidate = candidate(("a-d", "b-d", "c-d"))
        joined_candidate["participant_usernames"].append("c")
        joined = self.publish([joined_candidate])["changed"][0]

        self.assertEqual(joined["engagement_id"], first["engagement_id"])
        self.assertEqual(joined["engagement_version"], first["engagement_version"] + 1)
        self.assertEqual(len(self.store.list_members(first["engagement_id"], True)), 3)

        left = self.publish([candidate()])["changed"][0]
        self.assertEqual(left["engagement_id"], first["engagement_id"])
        self.assertEqual(len(self.store.list_members(first["engagement_id"], True)), 2)
        all_members = self.store.list_members(first["engagement_id"])
        self.assertEqual(sum(item["status"] == "left" for item in all_members), 1)

    def test_two_missing_publications_resolve_with_hysteresis(self):
        engagement = self.publish([candidate()])["changed"][0]
        first_miss = self.publish([])["changed"][0]
        self.assertEqual(first_miss["status"], "changing")
        self.assertEqual(first_miss["missed_publications"], 1)

        second_miss = self.publish([])["changed"][0]
        self.assertEqual(second_miss["status"], "resolved")
        self.assertEqual(second_miss["engagement_id"], engagement["engagement_id"])
        self.assertEqual(self.store.list_members(engagement["engagement_id"], True), [])

    def test_overlap_return_before_second_miss_recovers_same_cycle(self):
        engagement = self.publish([candidate()])["changed"][0]
        self.publish([])
        recovered = self.publish([candidate()])["changed"][0]
        self.assertEqual(recovered["engagement_id"], engagement["engagement_id"])
        self.assertEqual(recovered["status"], "active")
        self.assertEqual(recovered["missed_publications"], 0)

    def test_incomplete_member_snapshot_does_not_advance_hysteresis(self):
        engagement = self.publish([candidate()])["changed"][0]
        result = self.store.reconcile_candidates(
            [], "worker-a", protected_conflict_ids=["a-d"]
        )
        unchanged = self.store.get(engagement["engagement_id"])
        self.assertEqual(result["changed"], [])
        self.assertEqual(unchanged["status"], "active")
        self.assertEqual(unchanged["missed_publications"], 0)
        self.assertEqual(unchanged["snapshot_version"], engagement["snapshot_version"])

    def test_split_creates_parallel_engagement_and_resolved_cycle_is_not_reopened(self):
        original = self.publish([candidate()])["changed"][0]
        distant_bbox = {
            "min_lat": 52.1, "min_lng": 21.1,
            "max_lat": 52.11, "max_lng": 21.11,
        }
        split = self.publish([
            candidate(), candidate(suffix="two", bbox=distant_bbox),
        ])
        active = self.store.list_active()
        self.assertEqual(len(active), 2)
        self.assertIn(original["engagement_id"], {item["engagement_id"] for item in active})

        self.publish([])
        self.publish([])
        reopened = self.publish([candidate()])["changed"][0]
        self.assertNotEqual(reopened["engagement_id"], original["engagement_id"])

    def test_busy_lease_and_expired_lease_takeover(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO territory_conflict_engagement_coordinator "
                "(coordinator_key, lease_owner, lease_until, updated_at) "
                "VALUES ('global', 'worker-a', '2999-01-01T00:00:00', 'now')"
            )
        busy = self.publish([candidate()], owner="worker-b")
        self.assertFalse(busy["ok"])
        self.assertEqual(busy["reason"], "lease_busy")

        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE territory_conflict_engagement_coordinator "
                "SET lease_until = '2000-01-01T00:00:00' WHERE coordinator_key = 'global'"
            )
        takeover = self.publish([candidate()], owner="worker-b")
        self.assertTrue(takeover["ok"])

    def test_engagement_publication_does_not_change_base_conflict_identity(self):
        conflicts = TerritoryConflictStore(str(self.path))
        base = conflicts.upsert_conflict({
            "conflict_key": "geometry-a",
            "participants": ["a", "d"],
            "area_ids": [1, 2],
            "intersections": [],
            "targets": [],
            "status": "active",
        })
        self.publish([candidate()])
        unchanged = conflicts.get_by_key(base["conflict_id"])
        self.assertEqual(unchanged["conflict_id"], base["conflict_id"])
        self.assertEqual(unchanged["participant_key"], base["participant_key"])
        self.assertEqual(unchanged["conflict_version"], base["conflict_version"])


if __name__ == "__main__":
    unittest.main()
