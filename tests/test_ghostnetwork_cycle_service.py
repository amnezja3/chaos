import os
import tempfile
import threading
import unittest

from database import db_connect
from ghostnetwork import GhostCycleService, GhostNetworkRepository, ensure_active_ghostnetwork_cycle
from ghostnetwork.catalog import CATALOG_VERSION, get_catalog_checksum
from ghostnetwork.errors import CycleAlreadyActive, InvalidStateTransition, RepositoryIntegrityError


class GhostNetworkCycleServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.service = GhostCycleService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_first_cycle_with_20_pooled_parts(self):
        result = self.service.create_cycle()
        cycle = result["cycle"]
        parts = result["parts"]
        self.assertTrue(result["ok"])
        self.assertTrue(result["created"])
        self.assertEqual(cycle["status"], "active")
        self.assertEqual(cycle["signal_number"], 1)
        self.assertEqual(cycle["ghostsystem_version"], 1)
        self.assertEqual(cycle["source_version"], "1.0.1")
        self.assertEqual(cycle["catalog_version"], CATALOG_VERSION)
        self.assertEqual(cycle["catalog_checksum"], get_catalog_checksum())
        self.assertEqual(len(parts), 20)
        self.assertEqual(result["parts_summary"]["parts_total"], 20)
        self.assertEqual(result["parts_summary"]["parts_pooled"], 20)
        self.assertEqual(result["parts_summary"]["parts_reserved"], 0)
        self.assertEqual(result["parts_summary"]["parts_discovered"], 0)
        self.assertTrue(all(part["status"] == "pooled" for part in parts))
        self.assertTrue(all(part["catalog_version"] == CATALOG_VERSION for part in parts))
        self.assertTrue(all(not part["target_id"] for part in parts))
        self.assertTrue(all(part["latitude"] is None and part["longitude"] is None for part in parts))

    def test_distribution_is_five_per_clan_and_machine(self):
        result = self.service.create_cycle()
        parts = result["parts"]
        clans = {}
        machines = {}
        codes = set()
        for part in parts:
            clans[part["clan_code"]] = clans.get(part["clan_code"], 0) + 1
            machines[part["machine_code"]] = machines.get(part["machine_code"], 0) + 1
            codes.add(part["part_code"])
        self.assertEqual(set(clans.values()), {5})
        self.assertEqual(set(machines.values()), {5})
        self.assertEqual(len(codes), 20)

    def test_cycle_events_are_written(self):
        cycle = self.service.create_cycle()["cycle"]
        event_types = {event["event_type"] for event in self.repo.list_events(cycle["cycle_id"], limit=50)}
        self.assertIn("ghost.cycle_created", event_types)
        self.assertIn("ghost.parts_created", event_types)
        self.assertIn("ghost.cycle_activated", event_types)
        self.assertIn("ghost.cycle_status_changed", event_types)

    def test_second_transitional_cycle_is_blocked(self):
        self.service.create_cycle()
        with self.assertRaises(CycleAlreadyActive):
            self.service.create_cycle()

    def test_initializer_is_idempotent_after_restart(self):
        first = ensure_active_ghostnetwork_cycle(db_path=self.db_path)
        second_service = GhostCycleService(db_path=self.db_path)
        second = second_service.ensure_active_cycle()
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["cycle"]["cycle_id"], second["cycle"]["cycle_id"])
        self.assertEqual(len(second["parts"]), 20)

    def test_concurrent_initializers_create_one_cycle(self):
        results = []
        errors = []

        def run_initializer():
            try:
                results.append(ensure_active_ghostnetwork_cycle(db_path=self.db_path))
            except Exception as exc:  # pragma: no cover - failure details are asserted below
                errors.append(exc)

        threads = [threading.Thread(target=run_initializer) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertFalse(errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(self.repo.list_cycles()), 1)
        self.assertEqual(len(self.repo.list_parts(self.repo.get_active_cycle()["cycle_id"])), 20)

    def test_rollback_after_failed_part_creation_leaves_no_active_cycle(self):
        original = self.service._build_cycle_parts

        def broken_parts(cycle_id, catalog, catalog_version):
            parts = original(cycle_id, catalog, catalog_version)
            parts[11] = dict(parts[11])
            parts[11]["part_id"] = f"{cycle_id}_forced_duplicate"
            parts[11]["part_code"] = parts[0]["part_code"]
            return parts

        self.service._build_cycle_parts = broken_parts
        with self.assertRaises(RepositoryIntegrityError):
            self.service.create_cycle()
        self.assertIsNone(self.repo.get_active_cycle())
        self.assertEqual(self.repo.list_cycles(), [])

    def test_status_transition_contract(self):
        cycle = self.service.create_cycle()["cycle"]
        with self.assertRaises(InvalidStateTransition):
            self.service.activate_cycle(cycle["cycle_id"])
        transmitting = self.service.lock_cycle(cycle["cycle_id"])
        self.assertEqual(transmitting["status"], "transmitting")
        with self.assertRaises(InvalidStateTransition):
            self.service.activate_cycle(cycle["cycle_id"])
        stabilizing = self.service.begin_stabilization(cycle["cycle_id"])
        self.assertEqual(stabilizing["status"], "stabilizing")
        closed = self.service.close_cycle(cycle["cycle_id"])
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(InvalidStateTransition):
            self.service.activate_cycle(cycle["cycle_id"])

    def test_version_helper_requires_closed_cycle(self):
        cycle = self.service.create_cycle()["cycle"]
        with self.assertRaises(InvalidStateTransition):
            self.service.increment_ghostsystem_version(cycle["cycle_id"])
        self.service.lock_cycle(cycle["cycle_id"])
        self.service.begin_stabilization(cycle["cycle_id"])
        self.service.close_cycle(cycle["cycle_id"])
        self.assertEqual(self.service.increment_ghostsystem_version(cycle["cycle_id"]), "1.0.2")

    def test_health_check_complete_cycle_and_corruptions(self):
        cycle = self.service.create_cycle()["cycle"]
        report = self.repo.health_check()
        self.assertTrue(report["ok"], report)

        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM ghost_parts WHERE part_id = (SELECT part_id FROM ghost_parts WHERE cycle_id = ? LIMIT 1)",
                (cycle["cycle_id"],),
            )
        corrupted = self.repo.health_check()
        self.assertFalse(corrupted["ok"])
        self.assertIn("active_cycle_without_20_parts", corrupted["errors"])

    def test_health_check_detects_catalog_version_mismatch(self):
        cycle = self.service.create_cycle()["cycle"]
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE ghost_parts
                SET catalog_version = 'wrong-catalog'
                WHERE part_id = (
                    SELECT part_id FROM ghost_parts WHERE cycle_id = ? LIMIT 1
                )
                """,
                (cycle["cycle_id"],),
            )
        report = self.repo.health_check()
        self.assertFalse(report["ok"])
        self.assertIn("part_catalog_version_mismatch", report["errors"])


if __name__ == "__main__":
    unittest.main()
