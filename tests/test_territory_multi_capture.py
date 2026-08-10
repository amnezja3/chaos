import os
import tempfile
import threading
import unittest

from database import TerritoryStore, TerritoryTargetOwnershipStore, db_connect


class TerritoryMultiCaptureTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.store = TerritoryTargetOwnershipStore(self.db_path)
        self.territory_store = TerritoryStore(self.db_path)
        self.target = {
            "target_id": "map:52.1:21.1:shared",
            "lat": 52.1,
            "lng": 21.1,
            "label": "shared",
            "stationary": True,
            "owner_username": "defender",
        }
        self.territory_store.save_captured_target("defender", self.target)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db_path + suffix)
            except FileNotFoundError:
                pass

    def test_first_committed_capture_wins_and_loser_gets_state_changed(self):
        barrier = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def capture(attacker):
            barrier.wait()
            result = self.store.capture(
                action_id=f"action:{attacker}",
                target_id=self.target["target_id"],
                attacker_username=attacker,
                expected_owner_username="defender",
                target=self.target,
                conflict_ids=[f"conflict:{attacker}:defender"],
                engagement_ids=["engagement:shared"],
            )
            with lock:
                results.append(result)

        threads = [threading.Thread(target=capture, args=(name,)) for name in ("alice", "bob")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        winners = [item for item in results if item["result"] == "captured"]
        losers = [item for item in results if item["result"] == "target_state_changed"]
        self.assertEqual(1, len(winners))
        self.assertEqual(1, len(losers))
        self.assertEqual(winners[0]["winner_username"], losers[0]["current_owner_username"])
        self.assertEqual(2, winners[0]["ownership_version"])
        owned = self.territory_store.list_captured_targets(winners[0]["winner_username"])
        self.assertEqual([self.target["target_id"]], [item.get("target_id") for item in owned])
        losing_owner = "bob" if winners[0]["winner_username"] == "alice" else "alice"
        self.assertEqual([], self.territory_store.list_captured_targets(losing_owner))

    def test_same_action_is_idempotent_and_does_not_increment_version(self):
        first = self.store.capture(
            "action:one", self.target["target_id"], "alice", "defender", self.target,
            conflict_ids=["conflict:a"],
        )
        replay = self.store.capture(
            "action:one", self.target["target_id"], "alice", "defender", self.target,
            conflict_ids=["conflict:a"],
        )
        self.assertTrue(first["ok"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(first["set_id"], replay["set_id"])
        self.assertEqual(2, self.store.get(self.target["target_id"])["ownership_version"])

    def test_late_distinct_action_from_same_winner_is_idempotent_success(self):
        first = self.store.capture(
            "action:first", self.target["target_id"], "alice", "defender", self.target,
            conflict_ids=["conflict:a"],
        )
        late = self.store.capture(
            "action:late", self.target["target_id"], "alice", "defender", self.target,
            expected_version=1,
            conflict_ids=["conflict:a"],
        )

        self.assertEqual("captured", late["result"])
        self.assertTrue(late["duplicate"])
        self.assertEqual("alice", late["winner_username"])
        self.assertEqual(first["set_id"], late["set_id"])
        self.assertEqual(2, self.store.get(self.target["target_id"])["ownership_version"])
        self.assertEqual(late["set_id"], self.store.capture(
            "action:late", self.target["target_id"], "alice", "defender", self.target,
        )["set_id"])

    def test_stale_version_is_rejected_without_new_reconciliation_set(self):
        first = self.store.capture(
            "action:one", self.target["target_id"], "alice", "defender", self.target,
        )
        stale_target = {**self.target, "owner_username": "alice"}
        stale = self.store.capture(
            "action:two", self.target["target_id"], "bob", "alice", stale_target,
            expected_version=1,
        )
        self.assertEqual("target_state_changed", stale["result"])
        claim = self.store.claim_reconciliation_set("worker")
        self.assertEqual(first["set_id"], claim["set_id"])
        self.assertIsNone(self.store.claim_reconciliation_set("other-worker"))

    def test_bootstrap_owner_comes_from_store_not_request(self):
        result = self.store.capture(
            "action:forged", self.target["target_id"], "alice", "somebody_else",
            self.target,
        )
        self.assertEqual("target_state_changed", result["result"])
        self.assertEqual("defender", result["current_owner_username"])
        self.assertEqual("defender", self.store.get(self.target["target_id"])["owner_username"])

    def test_missing_canonical_owner_is_controlled_and_creates_no_set(self):
        missing = {**self.target, "target_id": "map:52.2:21.2:orphan", "lat": 52.2, "lng": 21.2}
        result = self.store.capture(
            "action:orphan", missing["target_id"], "alice", "defender", missing,
        )
        self.assertEqual("canonical_owner_missing", result["result"])
        self.assertFalse(result["ok"])
        self.assertIsNone(self.store.get(missing["target_id"]))
        self.assertIsNone(self.store.claim_reconciliation_set("worker"))

    def test_list_map_returns_one_consistent_ownership_snapshot(self):
        result = self.store.capture(
            "action:one", self.target["target_id"], "alice", "defender", self.target,
        )
        ownership = self.store.list_map()
        self.assertEqual([self.target["target_id"]], list(ownership))
        self.assertEqual("alice", ownership[self.target["target_id"]]["owner_username"])
        self.assertEqual(result["ownership_version"], ownership[self.target["target_id"]]["ownership_version"])

    def test_snapshot_gate_keeps_previous_version_until_set_is_published(self):
        conflict_id = "conflict:alice:defender"
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO territory_conflict_snapshots
                    (snapshot_id, conflict_id, snapshot_version, conflict_version,
                     geometry_version, payload_json, generated_at)
                VALUES ('snapshot:old', ?, 3, 3, 3, '{"snapshot_version":3}', '2026-08-08T10:00:00')
                """,
                (conflict_id,),
            )
        capture = self.store.capture(
            "action:gated", self.target["target_id"], "alice", "defender", self.target,
            conflict_ids=[conflict_id],
        )
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO territory_conflict_snapshots
                    (snapshot_id, conflict_id, snapshot_version, conflict_version,
                     geometry_version, payload_json, generated_at)
                VALUES ('snapshot:new', ?, 4, 4, 4, '{"snapshot_version":4}', '2026-08-08T10:01:00')
                """,
                (conflict_id,),
            )
        self.assertEqual(3, self.store.unpublished_snapshot_caps()[conflict_id])
        self.assertEqual(3, self.store.public_snapshot_version(conflict_id))
        claim = self.store.claim_reconciliation_set("worker")
        self.assertEqual(capture["set_id"], claim["set_id"])
        self.assertTrue(self.store.finish_reconciliation_set(
            capture["set_id"], lease_owner="worker", ok=True,
        ))
        self.assertNotIn(conflict_id, self.store.unpublished_snapshot_caps())


if __name__ == "__main__":
    unittest.main()
