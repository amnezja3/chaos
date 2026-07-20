import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from database import db_connect
from ghostnetwork import GhostNetworkRepository, GhostNetworkService
from ghostnetwork.errors import (
    CycleAlreadyActive,
    InvalidStateTransition,
    RepositoryIntegrityError,
    ReservationConflict,
)


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostNetworkRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def create_cycle(self, cycle_id="ghostnetwork_0001"):
        return self.repo.create_cycle(
            cycle_id=cycle_id,
            signal_number=1,
            ghostsystem_version=7,
            status="active",
            topology_seed="seed-1",
        )

    def create_part(self, part_code="oracle", target_id="", latitude=None, longitude=None):
        if not self.repo.get_cycle("ghostnetwork_0001"):
            self.create_cycle()
        return self.repo.create_parts([
            {
                "cycle_id": "ghostnetwork_0001",
                "part_id": f"part-{part_code}",
                "part_code": part_code,
                "clan_code": "virex",
                "machine_code": "virex_oracle",
                "profession_code": "operator",
                "status": "pooled",
                "target_id": target_id,
                "latitude": latitude,
                "longitude": longitude,
            }
        ])[0]

    def test_empty_repository_has_no_active_cycle(self):
        self.assertIsNone(self.repo.get_active_cycle())
        self.assertEqual(self.repo.get_state_version(), 0)
        self.assertTrue(self.repo.health_check()["ok"])

    def test_create_cycle_and_block_second_active_cycle(self):
        cycle = self.create_cycle()
        self.assertEqual(cycle["cycle_id"], "ghostnetwork_0001")
        self.assertEqual(cycle["status"], "active")
        self.assertGreaterEqual(cycle["state_version"], 1)

        with self.assertRaises(CycleAlreadyActive):
            self.repo.create_cycle(cycle_id="ghostnetwork_0002", status="preparing")

    def test_create_part_and_block_duplicate_part_code(self):
        self.create_part(target_id="target-1", latitude=52.1, longitude=21.1)
        with self.assertRaises(RepositoryIntegrityError):
            self.repo.create_parts([
                {
                    "cycle_id": "ghostnetwork_0001",
                    "part_id": "part-duplicate",
                    "part_code": "oracle",
                    "clan_code": "virex",
                    "machine_code": "virex_oracle",
                    "profession_code": "operator",
                    "status": "pooled",
                    "target_id": "target-2",
                }
            ])

    def test_block_duplicate_target_id_in_cycle(self):
        self.create_part(target_id="target-1", latitude=52.1, longitude=21.1)
        with self.assertRaises(RepositoryIntegrityError):
            self.repo.create_parts([
                {
                    "cycle_id": "ghostnetwork_0001",
                    "part_id": "part-broker",
                    "part_code": "broker",
                    "clan_code": "echo_freedom",
                    "machine_code": "ledger_nexus",
                    "profession_code": "broker",
                    "status": "pooled",
                    "target_id": "target-1",
                }
            ])

    def test_reservation_lifecycle_conflict_commit_and_expire(self):
        part = self.create_part()
        reservation = self.repo.create_reservation(
            "ghostnetwork_0001",
            part["part_id"],
            "target-1",
            "main",
            "virex",
            expires_at=future_iso(),
        )
        self.assertEqual(reservation["status"], "active")
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "reserved")

        with self.assertRaises(ReservationConflict):
            self.repo.create_reservation(
                "ghostnetwork_0001",
                part["part_id"],
                "target-1",
                "other",
                "virex",
                expires_at=future_iso(),
            )

        committed = self.repo.commit_reservation(reservation["reservation_id"], operation_id="op-1")
        self.assertEqual(committed["status"], "committed")
        with self.assertRaises(InvalidStateTransition):
            self.repo.commit_reservation(reservation["reservation_id"], operation_id="op-1")

        self.repo.create_parts([
            {
                "cycle_id": "ghostnetwork_0001",
                "part_id": "part-expiring",
                "part_code": "expiring",
                "clan_code": "sentinel_order",
                "machine_code": "sentinel_core",
                "profession_code": "sentinel",
                "status": "pooled",
                "target_id": "",
            }
        ])
        expired_res = self.repo.create_reservation(
            "ghostnetwork_0001",
            "part-expiring",
            "target-expiring",
            "main",
            "virex",
            expires_at="2000-01-01T00:00:00+00:00",
        )
        expired = self.repo.expire_reservations()
        self.assertIn(expired_res["reservation_id"], {item["reservation_id"] for item in expired})
        self.assertEqual(self.repo.get_part("part-expiring")["status"], "pooled")

    def test_append_event_dedupe_and_monotonic_version(self):
        cycle = self.create_cycle()
        first_version = cycle["state_version"]
        event = self.repo.append_event(
            "ghost.test_event",
            cycle_id="ghostnetwork_0001",
            entity_id="ghostnetwork_0001",
            dedupe_key="ghost:test:1",
            payload={"ok": True},
        )
        self.assertGreater(event["state_version"], first_version)

        with self.assertRaises(RepositoryIntegrityError):
            self.repo.append_event(
                "ghost.test_event",
                cycle_id="ghostnetwork_0001",
                entity_id="ghostnetwork_0001",
                dedupe_key="ghost:test:1",
            )

    def test_transaction_rolls_back_all_changes(self):
        self.create_cycle()
        with self.assertRaises(RepositoryIntegrityError):
            with self.repo.transaction():
                self.repo.create_parts([
                    {
                        "cycle_id": "ghostnetwork_0001",
                        "part_id": "part-a",
                        "part_code": "a",
                        "clan_code": "virex",
                        "machine_code": "virex_oracle",
                        "profession_code": "operator",
                        "status": "pooled",
                        "target_id": "rollback-target",
                    }
                ])
                self.repo.create_parts([
                    {
                        "cycle_id": "ghostnetwork_0001",
                        "part_id": "part-b",
                        "part_code": "b",
                        "clan_code": "virex",
                        "machine_code": "virex_oracle",
                        "profession_code": "operator",
                        "status": "pooled",
                        "target_id": "rollback-target",
                    }
                ])
        self.assertIsNone(self.repo.get_part("part-a"))
        self.assertIsNone(self.repo.get_part("part-b"))

    def test_internal_snapshot_and_service_health(self):
        part = self.create_part()
        reservation = self.repo.create_reservation(
            "ghostnetwork_0001",
            part["part_id"],
            "target-1",
            "main",
            "virex",
            expires_at=future_iso(),
        )
        snapshot = self.repo.build_internal_snapshot("ghostnetwork_0001")
        self.assertEqual(snapshot["cycle"]["cycle_id"], "ghostnetwork_0001")
        self.assertEqual(len(snapshot["parts"]), 1)
        self.assertEqual(snapshot["active_reservations"][0]["reservation_id"], reservation["reservation_id"])

        service = GhostNetworkService(repository=self.repo)
        self.assertTrue(service.health_check()["ok"])
        self.assertEqual(service.get_active_cycle()["cycle_id"], "ghostnetwork_0001")
        self.assertEqual(
            service.get_snapshot_for_viewer("admin")["projection"],
            "internal_recovery",
        )

    def test_health_check_reports_corrupted_data(self):
        self.create_cycle()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ghost_part_reservations (
                    reservation_id, cycle_id, part_id, target_id, player_id,
                    player_clan, status, reserved_at, expires_at
                )
                VALUES ('bad-res', 'ghostnetwork_0001', 'missing-part', 't', 'p', '', 'active', '2000', '2000')
                """
            )
            conn.execute(
                """
                INSERT INTO ghost_connections (
                    connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                )
                VALUES ('bad-conn', 'ghostnetwork_0001', 'missing-a', 'missing-b', 1, '2000')
                """
            )
        report = self.repo.health_check()
        self.assertFalse(report["ok"])
        self.assertIn("broken_connections", report["errors"])
        self.assertIn("active_reservations_after_expires_at", report["warnings"])


if __name__ == "__main__":
    unittest.main()
