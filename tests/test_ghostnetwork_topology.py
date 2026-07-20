import os
import tempfile
import unittest
from unittest.mock import patch

from database import db_connect
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostTopologyService
from ghostnetwork.catalog import TOPOLOGY_ANCHOR
from ghostnetwork.errors import InvalidStateTransition, RepositoryIntegrityError


class GhostNetworkTopologyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle_service = GhostCycleService(repository=self.repo)
        self.topology = GhostTopologyService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def create_cycle(self):
        return self.cycle_service.create_cycle()["cycle"]

    def part_ids_by_code(self, cycle_id):
        return {part["part_code"]: part["part_id"] for part in self.repo.list_parts(cycle_id)}

    def reset_connections(self, cycle_id):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM ghost_connections WHERE cycle_id = ?", (cycle_id,))
            conn.execute("UPDATE ghost_cycles SET topology_checksum = '' WHERE cycle_id = ?", (cycle_id,))

    def insert_ring(self, cycle_id, code_order, offset=0, prefix="conn"):
        by_code = self.part_ids_by_code(cycle_id)
        with db_connect(self.db_path) as conn:
            for index, code in enumerate(code_order):
                a_id = by_code[code]
                b_id = by_code[code_order[(index + 1) % len(code_order)]]
                conn.execute(
                    """
                    INSERT INTO ghost_connections (
                        connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"{prefix}-{offset + index}", cycle_id, a_id, b_id, offset + index, "2026-07-18T00:00:00+00:00"),
                )

    def test_first_cycle_uses_canonical_closed_ring(self):
        cycle = self.create_cycle()
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["nodes"], 20)
        self.assertEqual(validation["connections"], 20)
        self.assertEqual(validation["ring_codes"], list(TOPOLOGY_ANCHOR))
        self.assertEqual(validation["ring_codes"][0:2], ["V1", "S5"])
        self.assertEqual(self.repo.get_cycle(cycle["cycle_id"])["topology_checksum"], validation["topology_checksum"])
        self.assertTrue(validation["checksum_match"])

    def test_each_node_has_two_neighbors_and_no_same_clan_edges(self):
        cycle = self.create_cycle()
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertEqual(validation["degree_errors"], {})
        self.assertEqual(validation["same_clan_edges"], [])
        for part in self.repo.list_parts(cycle["cycle_id"]):
            self.assertEqual(len(self.topology.get_neighbors(part["part_id"])), 2)

    def test_generation_is_idempotent_after_restart(self):
        cycle = self.create_cycle()
        first_order = self.topology.get_ring_order(cycle["cycle_id"])
        restarted = GhostTopologyService(repository=GhostNetworkRepository(db_path=self.db_path))
        result = restarted.generate_topology(cycle["cycle_id"])
        self.assertFalse(result["created"])
        self.assertEqual(first_order, restarted.get_ring_order(cycle["cycle_id"]))
        self.assertEqual(len(restarted.list_connections(cycle["cycle_id"])), 20)

    def test_activate_cycle_without_topology_is_blocked(self):
        cycle = self.create_cycle()
        self.reset_connections(cycle["cycle_id"])
        with self.assertRaises(InvalidStateTransition):
            self.cycle_service.activate_cycle(cycle["cycle_id"])

    def test_validator_detects_missing_edge(self):
        cycle = self.create_cycle()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM ghost_connections WHERE cycle_id = ? AND position_in_ring = 19",
                (cycle["cycle_id"],),
            )
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertFalse(validation["valid"])
        self.assertIn("topology_connection_count_not_20", validation["errors"])
        self.assertIn("topology_degree_not_2", validation["errors"])

    def test_validator_detects_split_rings(self):
        cycle = self.create_cycle()
        self.reset_connections(cycle["cycle_id"])
        self.insert_ring(cycle["cycle_id"], list(TOPOLOGY_ANCHOR)[:10], prefix="split-a")
        self.insert_ring(cycle["cycle_id"], list(TOPOLOGY_ANCHOR)[10:], offset=10, prefix="split-b")
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertFalse(validation["valid"])
        self.assertIn("topology_not_connected", validation["errors"])
        self.assertEqual(validation["connected_components"], 2)

    def test_validator_detects_duplicate_edge_and_self_loop(self):
        cycle = self.create_cycle()
        self.reset_connections(cycle["cycle_id"])
        by_code = self.part_ids_by_code(cycle["cycle_id"])
        canonical = list(TOPOLOGY_ANCHOR)
        with db_connect(self.db_path) as conn:
            for index in range(18):
                conn.execute(
                    """
                    INSERT INTO ghost_connections (
                        connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"edge-{index}",
                        cycle["cycle_id"],
                        by_code[canonical[index]],
                        by_code[canonical[index + 1]],
                        index,
                        "2026-07-18T00:00:00+00:00",
                    ),
                )
            conn.execute(
                """
                INSERT INTO ghost_connections (
                    connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                )
                VALUES ('duplicate-edge', ?, ?, ?, 18, '2026-07-18T00:00:00+00:00')
                """,
                (cycle["cycle_id"], by_code["S5"], by_code["V1"]),
            )
            conn.execute(
                """
                INSERT INTO ghost_connections (
                    connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                )
                VALUES ('self-loop', ?, ?, ?, 19, '2026-07-18T00:00:00+00:00')
                """,
                (cycle["cycle_id"], by_code["P2"], by_code["P2"]),
            )
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertFalse(validation["valid"])
        self.assertIn("topology_duplicate_edge", validation["errors"])
        self.assertIn("topology_self_loop", validation["errors"])

    def test_validator_detects_same_clan_edge(self):
        cycle = self.create_cycle()
        self.reset_connections(cycle["cycle_id"])
        by_code = self.part_ids_by_code(cycle["cycle_id"])
        same_clan = ("V1", "V2")
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ghost_connections (
                    connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                )
                VALUES ('same-clan', ?, ?, ?, 0, '2026-07-18T00:00:00+00:00')
                """,
                (cycle["cycle_id"], by_code[same_clan[0]], by_code[same_clan[1]]),
            )
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertFalse(validation["valid"])
        self.assertIn("topology_same_clan_edge", validation["errors"])

    def test_validator_detects_changed_checksum(self):
        cycle = self.create_cycle()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE ghost_cycles SET topology_checksum = 'wrong' WHERE cycle_id = ?",
                (cycle["cycle_id"],),
            )
        validation = self.topology.validate_topology(cycle["cycle_id"])
        self.assertFalse(validation["valid"])
        self.assertIn("topology_checksum_mismatch", validation["errors"])

    def test_rollback_after_topology_failure_leaves_no_cycle(self):
        with patch.object(GhostTopologyService, "generate_topology", side_effect=RepositoryIntegrityError("boom")):
            with self.assertRaises(RepositoryIntegrityError):
                self.cycle_service.create_cycle()
        self.assertEqual(self.repo.list_cycles(), [])
        self.assertIsNone(self.repo.get_active_cycle())


if __name__ == "__main__":
    unittest.main()
