import os
import tempfile
import unittest

from database import dumps_json
from ghostnetwork import (
    GhostCycleService,
    GhostNetworkRepository,
    GhostSignalRankingService,
    GhostTransmissionService,
)
from ghostnetwork.closure import GhostNetworkClosureService


class GhostSignalRankingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ranking.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def transmit_cycle(self):
        cycle = GhostCycleService(repository=self.repo).create_cycle()["cycle"]
        now = self.repo.now()
        for index, part in enumerate(self.repo.list_parts(cycle["cycle_id"])):
            owner = "alpha" if index < 12 else "beta"
            clan = part["clan_code"]
            self.repo.update_part(
                part["part_id"], status="active", target_id=f"rank-{index}",
                latitude=52.0 + index * 0.001, longitude=21.0 + index * 0.001,
                discovered_by=owner, discovered_clan=clan, discovered_at=now,
                anchor_snapshot_json=dumps_json({"target_id": f"rank-{index}"}),
                territory_id=f"rank-territory-{index}", territory_owner_id=owner,
                territory_clan=clan, territory_state_version=index + 1,
                activated_at=now, last_activated_at=now, conflict_state="none",
            )
        closing = self.repo.list_parts(cycle["cycle_id"])[-1]
        event = self.repo.append_event(
            "ghost.part_activated", cycle_id=cycle["cycle_id"],
            part_id=closing["part_id"], entity_id=closing["part_id"],
            player_id="beta", clan_code=closing["clan_code"],
            territory_id=closing["territory_id"],
            event_id=f"ranking-close-{cycle['cycle_id']}",
            dedupe_key=f"ranking-close:{cycle['cycle_id']}",
            payload={"player_id": "beta"},
        )
        closure = GhostNetworkClosureService(repository=self.repo)
        locked = closure.attempt_cycle_lock(cycle["cycle_id"], event["event_id"])
        self.assertTrue(locked.get("locked"), locked)
        transmitted = GhostTransmissionService(
            repository=self.repo, closure_service=closure
        ).start_transmission(cycle["cycle_id"])
        self.assertTrue(transmitted["ok"], transmitted)
        return transmitted["signal"]

    def test_snapshot_is_immutable_idempotent_and_checksum_valid(self):
        signal = self.transmit_cycle()
        service = GhostSignalRankingService(self.repo)
        first = service.finalize(signal["signal_id"])
        second = service.finalize(signal["signal_id"])

        self.assertTrue(first["ok"], first)
        self.assertTrue(second["ok"], second)
        self.assertTrue(second["idempotent"])
        self.assertEqual(
            first["ranking"]["snapshot_checksum"],
            second["ranking"]["snapshot_checksum"],
        )
        self.assertEqual(len(self.repo.list_signal_rankings()), 1)
        snapshot = first["ranking"]["snapshot"]
        self.assertEqual(snapshot["snapshot_schema"], 2)
        self.assertEqual(len(snapshot["parts"]), 20)
        self.assertEqual(sum(row["nodes_held"] for row in snapshot["players"]), 20)
        self.assertEqual(sum(row["rsp_signal"] for row in snapshot["players"]), 180)
        self.assertEqual(sum(row["clan_ghost_score"] for row in snapshot["clans"]), 500)

    def test_all_time_is_rebuilt_from_snapshots(self):
        signal = self.transmit_cycle()
        service = GhostSignalRankingService(self.repo)
        service.finalize(signal["signal_id"])
        result = service.all_time()
        self.assertTrue(result["ok"])
        self.assertEqual(result["rebuilt_from_snapshots"], 1)
        self.assertEqual({row["user_id"] for row in result["players"]}, {"alpha", "beta"})
        self.assertGreaterEqual(len(result["clans"]), 1)
        self.assertEqual(sum(row["signals_participated"] for row in result["players"]), 2)

    def test_largest_remainder_is_deterministic(self):
        from ghostnetwork.ranking import allocate_pool

        self.assertEqual(allocate_pool(5, {"b": 1, "a": 1, "c": 1}), {"a": 2, "b": 2, "c": 1})


if __name__ == "__main__":
    unittest.main()
