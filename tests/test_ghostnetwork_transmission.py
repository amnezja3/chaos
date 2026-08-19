import os
import tempfile
import unittest

from database import dumps_json
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostTransmissionService
from ghostnetwork.closure import GhostNetworkClosureService


class GhostNetworkTransmissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle_service = GhostCycleService(repository=self.repo)
        self.closure = GhostNetworkClosureService(repository=self.repo)
        self.transmission = GhostTransmissionService(repository=self.repo, closure_service=self.closure)

    def tearDown(self):
        self.tmp.cleanup()

    def create_locked_cycle(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
        now = self.repo.now()
        for index, part in enumerate(self.repo.list_parts(cycle["cycle_id"])):
            lat = 52.20 + index * 0.001
            lng = 21.00 + index * 0.001
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
                territory_state_version=2000 + index,
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
        lock = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(lock["locked"], lock)
        return self.repo.get_cycle(cycle["cycle_id"]), lock

    def test_locked_cycle_transmits_once_and_starts_restart_window(self):
        cycle, lock = self.create_locked_cycle()
        result = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "sent")
        signal_event = next(
            event for event in self.repo.list_events(cycle["cycle_id"], limit=1000)
            if event["event_type"] == "ghost.signal_sent"
        )
        self.assertEqual(signal_event["audience_scope"], "public")

        signal = result["signal"]
        self.assertEqual(signal["cycle_id"], cycle["cycle_id"])
        self.assertEqual(signal["signal_number"], cycle["signal_number"])
        self.assertEqual(signal["status"], "sent")
        self.assertEqual(signal["outcome"], "pending")
        self.assertEqual(signal["lock_snapshot_id"], lock["snapshot"]["lock_snapshot_id"])
        self.assertTrue(signal["signal_checksum"])

        updated_cycle = self.repo.get_cycle(cycle["cycle_id"])
        self.assertEqual(updated_cycle["status"], "stabilizing")
        self.assertTrue(updated_cycle["restart_required"])
        self.assertEqual(updated_cycle["restart_signal_id"], signal["signal_id"])
        self.assertEqual(updated_cycle["ghostsystem_version"], cycle["ghostsystem_version"] + 1)
        self.assertTrue(updated_cycle["stabilization_until"])

        parts = self.repo.list_parts(cycle["cycle_id"])
        self.assertEqual(len(parts), 20)
        self.assertTrue(all(part["status"] == "consumed" for part in parts))
        self.assertTrue(all(part["consumed_signal_id"] == signal["signal_id"] for part in parts))
        self.assertEqual(self.repo.list_connections(cycle["cycle_id"]), [])
        self.assertEqual(len(self.repo.list_historical_nodes_for_signal(signal["signal_id"])), 20)

        rewards = [reward for reward in self.repo.list_pending_rewards(cycle_id=cycle["cycle_id"], limit=100)]
        self.assertEqual(len(rewards), 21)
        self.assertEqual(len(self.repo.list_signals_for_cycle(cycle["cycle_id"])), 1)

    def test_transmission_retry_is_idempotent(self):
        cycle, _lock = self.create_locked_cycle()
        first = self.transmission.start_transmission(cycle["cycle_id"])
        second = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["signal"]["signal_id"], second["signal"]["signal_id"])
        self.assertEqual(len(self.repo.list_signals_for_cycle(cycle["cycle_id"])), 1)
        self.assertEqual(len(self.repo.list_pending_rewards(cycle_id=cycle["cycle_id"], limit=100)), 21)
        self.assertEqual(len(self.repo.list_historical_nodes_for_signal(first["signal"]["signal_id"])), 20)
        self.assertEqual(self.repo.get_cycle(cycle["cycle_id"])["ghostsystem_version"], cycle["ghostsystem_version"] + 1)

    def test_transmission_requires_valid_lock_snapshot(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
        result = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertFalse(result["ok"])
        self.assertIn("cycle_not_transmitting", result["reasons"])
        self.assertIn("lock_snapshot_missing", result["reasons"])
        self.assertEqual(self.repo.list_signals_for_cycle(cycle["cycle_id"]), [])

    def test_signal_uses_immutable_lock_snapshot_not_late_world_mutation(self):
        cycle, lock = self.create_locked_cycle()
        locked_owner = lock["snapshot"]["snapshot"]["parts"][0]["territory_owner_id"]
        locked_part_id = lock["snapshot"]["snapshot"]["parts"][0]["part_id"]
        self.repo.update_part(locked_part_id, territory_owner_id="late-owner")

        result = self.transmission.start_transmission(cycle["cycle_id"])
        signal_id = result["signal"]["signal_id"]
        node = [
            item
            for item in self.repo.list_historical_nodes_for_signal(signal_id)
            if item["part_id"] == locked_part_id
        ][0]
        self.assertEqual(node["owner_id"], locked_owner)
        self.assertNotEqual(node["owner_id"], "late-owner")


if __name__ == "__main__":
    unittest.main()
