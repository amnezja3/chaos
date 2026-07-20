import os
import tempfile
import unittest

from database import db_connect, dumps_json
from ghostnetwork import GhostCycleService, GhostNetworkClosureService, GhostNetworkRepository


class GhostNetworkClosureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle_service = GhostCycleService(repository=self.repo)
        self.closure = GhostNetworkClosureService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def create_ready_cycle(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
        parts = self.repo.list_parts(cycle["cycle_id"])
        now = self.repo.now()
        for index, part in enumerate(parts):
            lat = 52.10 + index * 0.001
            lng = 21.10 + index * 0.001
            self.repo.update_part(
                part["part_id"],
                status="active",
                target_id=f"POI-{part['part_code']}",
                latitude=lat,
                longitude=lng,
                discovered_by=f"operator-{index}",
                discovered_clan=part["clan_code"],
                discovered_at=now,
                anchor_snapshot_json=dumps_json(
                    {
                        "target_id": f"POI-{part['part_code']}",
                        "lat": lat,
                        "lng": lng,
                        "label": part["part_code"],
                    }
                ),
                territory_id=f"territory-{part['part_code']}",
                territory_owner_id=f"operator-{index}",
                territory_clan=part["clan_code"],
                territory_state_version=1000 + index,
                activated_at=now,
                last_activated_at=now,
                conflict_state="none",
                conflict_id="",
            )
        closing_part = self.repo.list_parts(cycle["cycle_id"])[-1]
        closing_event = self.repo.append_event(
            "ghost.part_activated",
            cycle_id=cycle["cycle_id"],
            part_id=closing_part["part_id"],
            entity_id=closing_part["part_id"],
            player_id="closing-operator",
            clan_code=closing_part["clan_code"],
            territory_id=closing_part["territory_id"],
            dedupe_key=f"test:closing:{cycle['cycle_id']}",
            event_id=f"event-closing-{cycle['cycle_id']}",
            payload={"player_id": "closing-operator"},
        )
        return self.repo.get_cycle(cycle["cycle_id"]), closing_event

    def test_ready_cycle_locks_atomically_and_creates_immutable_snapshot(self):
        cycle, closing_event = self.create_ready_cycle()
        readiness = self.closure.evaluate_network_readiness(cycle["cycle_id"])
        self.assertTrue(readiness["ready"], readiness)

        result = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(result["locked"], result)
        locked_cycle = self.repo.get_cycle(cycle["cycle_id"])
        self.assertEqual(locked_cycle["status"], "transmitting")
        self.assertEqual(locked_cycle["lock_event_id"], closing_event["event_id"])

        snapshot = self.closure.get_locked_cycle_snapshot(cycle["cycle_id"])
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["snapshot"]["cycle_id"], cycle["cycle_id"])
        self.assertEqual(len(snapshot["snapshot"]["parts"]), 20)
        self.assertEqual(len(snapshot["snapshot"]["topology"]["connections"]), 20)
        self.assertEqual(snapshot["snapshot"]["closing"]["closing_player_id"], "closing-operator")
        self.assertTrue(self.closure.validate_locked_snapshot(cycle["cycle_id"])["valid"])

        first_checksum = snapshot["snapshot_checksum"]
        first_owner = snapshot["snapshot"]["parts"][0]["territory_owner_id"]
        first_part_id = snapshot["snapshot"]["parts"][0]["part_id"]
        self.repo.update_part(first_part_id, territory_owner_id="late-attacker")
        snapshot_after_mutation = self.closure.get_locked_cycle_snapshot(cycle["cycle_id"])
        self.assertEqual(snapshot_after_mutation["snapshot_checksum"], first_checksum)
        self.assertEqual(snapshot_after_mutation["snapshot"]["parts"][0]["territory_owner_id"], first_owner)

    def test_lock_is_idempotent_after_snapshot_exists(self):
        cycle, closing_event = self.create_ready_cycle()
        first = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        second = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(first["locked"])
        self.assertTrue(second["locked"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(
            first["snapshot"]["snapshot_checksum"],
            second["snapshot"]["snapshot_checksum"],
        )

    def test_unresolved_conflict_blocks_lock(self):
        cycle, closing_event = self.create_ready_cycle()
        part = self.repo.list_parts(cycle["cycle_id"])[0]
        self.repo.insert_strategic_conflict(
            {
                "cycle_id": cycle["cycle_id"],
                "part_id": part["part_id"],
                "territory_id": part["territory_id"],
                "initial_owner_id": part["territory_owner_id"],
                "initial_clan": part["clan_code"],
                "status": "active",
                "dedupe_key": "test:conflict",
            }
        )
        readiness = self.closure.evaluate_network_readiness(cycle["cycle_id"])
        self.assertFalse(readiness["ready"])
        self.assertIn("unresolved_strategic_conflict", readiness["reasons"])
        result = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertFalse(result["locked"])

    def test_existing_signal_blocks_lock(self):
        cycle, closing_event = self.create_ready_cycle()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ghost_signals (
                    signal_id, signal_number, cycle_id, source_version, status, sent_at
                )
                VALUES ('signal-existing', 127, ?, 1, 'sent', ?)
                """,
                (cycle["cycle_id"], self.repo.now()),
            )
        readiness = self.closure.evaluate_network_readiness(cycle["cycle_id"])
        self.assertFalse(readiness["ready"])
        self.assertIn("ghost_signal_already_exists", readiness["reasons"])
        result = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertFalse(result["locked"])

    def test_inactive_part_blocks_lock(self):
        cycle, closing_event = self.create_ready_cycle()
        part = self.repo.list_parts(cycle["cycle_id"])[0]
        self.repo.update_part(part["part_id"], status="contained")
        readiness = self.closure.evaluate_network_readiness(cycle["cycle_id"])
        self.assertFalse(readiness["ready"])
        self.assertTrue(any(reason.startswith("part_not_active:") for reason in readiness["reasons"]))
        result = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertFalse(result["locked"])


if __name__ == "__main__":
    unittest.main()
