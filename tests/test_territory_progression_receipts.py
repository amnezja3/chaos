import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
