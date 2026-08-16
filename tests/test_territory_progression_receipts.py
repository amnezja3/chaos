import os
import tempfile
import unittest
from unittest.mock import patch

import run
from database import TerritoryProgressionReceiptStore, UserStore


class TerritoryProgressionReceiptTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.users = UserStore(self.db_path, seed_path=self.db_path + ".missing")
        self.users.save_profile({
            "username": "alice",
            "level": 2,
            "respect": 10,
            "system_messages": [],
            "territory_stats": {"effective_area": 1000, "area_baseline": 1000},
        })
        self.receipts = TerritoryProgressionReceiptStore(self.db_path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db_path + suffix)
            except FileNotFoundError:
                pass

    def test_same_source_event_keeps_first_baseline(self):
        first = self.receipts.ensure(
            "capture:1", "alice",
            {"territory_stats": {"effective_area": 1000}},
            conflict_ids=["conflict:1"],
        )
        replay = self.receipts.ensure(
            "capture:1", "alice",
            {"territory_stats": {"effective_area": 9999}},
            conflict_ids=["conflict:other"],
        )
        self.assertEqual(first["receipt_id"], replay["receipt_id"])
        self.assertEqual(1000, replay["baseline"]["territory_stats"]["effective_area"])
        self.assertEqual(["conflict:1"], replay["conflict_ids"])

    def test_capture_finalizer_does_not_consume_pending_strategic_receipt(self):
        capture = self.receipts.ensure("capture:pending", "alice", {})
        strategic = self.receipts.ensure(
            "territory_strategic:pending", "alice",
            {"reward_type": "territory_strategic"},
        )

        regular = self.receipts.list_pending(actor_username="alice")
        strategic_only = self.receipts.list_pending(
            actor_username="alice", strategic_only=True
        )
        self.assertEqual([capture["receipt_id"]], [item["receipt_id"] for item in regular])
        self.assertEqual(
            [strategic["receipt_id"]],
            [item["receipt_id"] for item in strategic_only],
        )

    def test_settle_is_atomic_and_idempotent(self):
        receipt = self.receipts.ensure(
            "capture:2", "alice",
            {"territory_stats": {"effective_area": 1000}},
        )
        progression = {"respect_gain": 4, "levels_gained": 1}
        first = self.receipts.settle(
            receipt["receipt_id"], progression,
            {"effective_area": 1200, "area_baseline": 1100},
            "1200 m2 efektywne",
            system_messages=[{"type": "success", "title": "reward"}],
        )
        replay = self.receipts.settle(
            receipt["receipt_id"], progression,
            {"effective_area": 1200}, "ignored",
        )
        profile = self.users.get_profile("alice")
        self.assertTrue(first["ok"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(14, profile["respect"])
        self.assertEqual(3, profile["level"])
        self.assertEqual(1, len(profile["system_messages"]))

    def test_strategic_settlement_combines_encirclement_and_conflicts_once(self):
        receipt = self.receipts.ensure(
            "territory_strategic:encirclement:1", "alice", {},
            conflict_ids=["conflict:1", "conflict:2"],
        )
        first = self.receipts.settle_strategic(
            receipt["receipt_id"],
            encirclement={"awarded": True, "transferred_pillar_count": 3},
            conflict_resolutions=[
                {"conflict_id": "conflict:1", "resolution_version": 4},
                {"conflict_id": "conflict:2", "resolution_version": 7},
            ],
        )
        replay = self.receipts.settle_strategic(
            receipt["receipt_id"],
            encirclement={"awarded": True, "transferred_pillar_count": 99},
            conflict_resolutions=[
                {"conflict_id": "conflict:1", "resolution_version": 4},
            ],
        )

        profile = self.users.get_profile("alice")
        self.assertTrue(first["ok"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(5, profile["level"])
        self.assertEqual(17, profile["respect"])
        self.assertEqual(2, len(first["result"]["conflict_resolutions"]))
        self.assertEqual(2, first["result"]["totals"]["level_before"])
        self.assertEqual(3, first["result"]["totals"]["levels_gained"])

    def test_conflict_resolution_reward_uses_closing_actor_level_and_version(self):
        snapshot = {
            "conflict_version": 4,
            "geometry_version": 9,
            "conflict": {
                "conflict_id": "conflict:standalone",
                "status": "resolved",
                "participants": ["alice", "bob"],
                "last_actor_username": "alice",
                "resolution_reason": "no_active_fronts",
            },
        }
        first = run.settle_conflict_resolution_reward(
            snapshot, progression_store=self.receipts
        )
        replay = run.settle_conflict_resolution_reward(
            snapshot, progression_store=self.receipts
        )

        profile = self.users.get_profile("alice")
        self.assertTrue(first["ok"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(3, profile["level"])
        self.assertEqual(12, profile["respect"])
        reward = first["result"]["conflict_resolutions"][0]
        self.assertEqual(4, reward["resolution_version"])
        self.assertEqual(2, reward["respect_gain"])

    def test_same_clan_conflict_resolution_creates_no_reward_receipt(self):
        snapshot = {
            "geometry_version": 3,
            "conflict": {
                "conflict_id": "conflict:protected",
                "status": "resolved",
                "participants": ["alice", "bob"],
                "last_actor_username": "alice",
            },
        }
        with patch.object(run, "territory_owners_are_protected_relation", return_value=True):
            result = run.settle_conflict_resolution_reward(
                snapshot, progression_store=self.receipts
            )
        self.assertEqual("protected_relation", result["reason"])
        self.assertEqual([], self.receipts.list_pending(include_strategic=True))

    def test_progression_uses_receipt_baseline_not_newer_read_snapshot(self):
        profile = self.users.get_profile("alice")
        profile["territory_stats"]["effective_area"] = 2000
        areas = [{
            "area_size": 50000,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ]
        }]
        current = run.summarize_territory_metrics(areas, 2)["effective_area"]
        baseline = max(1, current / 2)
        result = run.apply_territory_progression(
            profile,
            areas,
            previous_stats={"effective_area": baseline, "area_baseline": baseline},
        )
        self.assertGreater(result["effective_gain"], 0)
        self.assertGreater(result["respect_gain"], 0)

    def test_level_growth_is_scoped_to_cluster_containing_captured_target(self):
        profile = self.users.get_profile("alice")
        changed = {
            "id": 1, "area_size": 15000,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        other = {
            "id": 2, "area_size": 11000000,
            "vertices": [
                {"lat": 53.0, "lng": 22.0},
                {"lat": 53.0, "lng": 22.1},
                {"lat": 53.1, "lng": 22.0},
            ],
        }
        baseline = run.build_territory_progression_baseline(
            profile, [changed, other],
            target={"lat": 52.004, "lng": 21.004, "target_id": "target:1"},
        )
        result = run.apply_territory_progression(
            profile,
            [dict(changed, id=10, area_size=16800), dict(other, id=20)],
            previous_stats=baseline["territory_stats"],
            baseline_clusters=baseline["cluster_snapshots"],
            progression_target=baseline["target"],
        )
        self.assertEqual(1, result["levels_gained"])
        self.assertEqual("10", result["progression_cluster_id"])

    def test_other_cluster_growth_does_not_qualify_changed_cluster(self):
        profile = self.users.get_profile("alice")
        changed = {
            "id": 1, "area_size": 15000,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        other = {
            "id": 2, "area_size": 100000,
            "vertices": [
                {"lat": 53.0, "lng": 22.0},
                {"lat": 53.0, "lng": 22.1},
                {"lat": 53.1, "lng": 22.0},
            ],
        }
        baseline = run.build_territory_progression_baseline(
            profile, [changed, other], target={"lat": 52.004, "lng": 21.004},
        )
        result = run.apply_territory_progression(
            profile,
            [dict(changed, id=10, area_size=15100), dict(other, id=20, area_size=200000)],
            previous_stats=baseline["territory_stats"],
            baseline_clusters=baseline["cluster_snapshots"],
            progression_target=baseline["target"],
        )
        self.assertEqual(0, result["levels_gained"])

    def test_small_growths_accumulate_against_same_cluster_baseline(self):
        profile = self.users.get_profile("alice")
        area = {
            "id": 1, "area_size": 10000,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        target = {"lat": 52.004, "lng": 21.004}
        first_baseline = run.build_territory_progression_baseline(
            profile, [area], target=target,
        )
        first = run.apply_territory_progression(
            profile, [dict(area, id=2, area_size=10500)],
            previous_stats=first_baseline["territory_stats"],
            baseline_clusters=first_baseline["cluster_snapshots"],
            progression_target=first_baseline["target"],
        )
        self.assertEqual(0, first["levels_gained"])

        second_baseline = run.build_territory_progression_baseline(
            profile, [dict(area, id=2, area_size=10500)], target=target,
        )
        second = run.apply_territory_progression(
            profile, [dict(area, id=3, area_size=11100)],
            previous_stats=second_baseline["territory_stats"],
            baseline_clusters=second_baseline["cluster_snapshots"],
            progression_target=second_baseline["target"],
        )
        self.assertEqual(1, second["levels_gained"])


if __name__ == "__main__":
    unittest.main()
