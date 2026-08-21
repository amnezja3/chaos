import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostNetworkDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycles = GhostCycleService(repository=self.repo)
        self.cycles.ensure_active_cycle()
        self.service = GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0, reservation_ttl_seconds=600),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def player(self, username="main", clan="virex", profession="broker"):
        return {
            "player_id": username,
            "username": username,
            "clan_code": clan,
            "ghost_clan": clan,
            "ghost_profession": profession,
        }

    def target(self, target_id="map:52.1:21.1:shop"):
        return {
            "target_id": target_id,
            "lat": 52.1,
            "lng": 21.1,
            "label": "Shop",
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }

    def test_final_target_capture_discovers_reserved_part_once(self):
        target = self.target()
        reserved = self.service.on_target_aimed(self.player(), target)
        self.assertEqual(reserved["status"], "reserved")

        attached = self.service.attach_reservation_to_operation("main", target["target_id"], "op-1")
        self.assertEqual(attached["status"], "attached")
        result = self.service.on_target_hacked(
            self.player(),
            target,
            operation={"operation_id": "op-1"},
            result={"target_captured": True},
            context={"reason": "unit_test_capture"},
        )

        self.assertEqual(result["status"], "discovered")
        part = result["part"]
        self.assertEqual(part["status"], "public")
        self.assertEqual(part["target_id"], target["target_id"])
        self.assertEqual(part["discovered_by"], "main")
        self.assertEqual(part["discovered_clan"], "virex")
        self.assertEqual(part["discovery_operation_id"], "op-1")
        self.assertEqual(part["anchor_snapshot"]["label"], "Shop")
        self.assertEqual(part["anchor_snapshot"]["source_type"], "shop")
        self.assertTrue(self.repo.health_check()["ok"])

        repeated = self.service.on_target_hacked(
            self.player(),
            target,
            operation={"operation_id": "op-1"},
            result={"target_captured": True},
        )
        self.assertEqual(repeated["status"], "already_discovered")
        events = [
            event for event in self.repo.list_events(self.repo.get_active_cycle()["cycle_id"], limit=200)
            if event["event_type"] == "ghost.part_discovered"
        ]
        self.assertEqual(len(events), 1)

    def test_partial_success_does_not_emit_part(self):
        target = self.target("map:52.2:21.2:scan")
        reserved = self.service.on_target_aimed(self.player(), target)
        reservation = self.repo.get_reservation(reserved["reservation_id"])

        result = self.service.on_target_hacked(
            self.player(),
            target,
            operation={"operation_id": "op-scan"},
            result={"success": True, "action": "scan_ports"},
        )

        self.assertEqual(result["status"], "not_final_success")
        self.assertEqual(self.repo.get_part(reservation["part_id"])["status"], "reserved")
        self.assertEqual(self.repo.get_part(reservation["part_id"])["target_id"], target["target_id"])

    def test_no_reservation_and_expired_reservation_do_not_emit(self):
        no_reservation = self.service.on_target_hacked(
            self.player(),
            self.target("map:52.3:21.3:none"),
            result={"target_captured": True},
        )
        self.assertEqual(no_reservation["status"], "no_matching_reservation")

        cycle_id = self.repo.get_active_cycle()["cycle_id"]
        part = self.repo.list_reservable_parts(cycle_id, excluded_clan="virex")[0]
        old_reservation = self.repo.create_reservation(
            cycle_id,
            part["part_id"],
            "map:52.4:21.4:expired",
            "main",
            "virex",
            expires_at="2000-01-01T00:00:00+00:00",
        )
        expired = self.service.on_target_hacked(
            self.player(),
            self.target("map:52.4:21.4:expired"),
            result={"target_captured": True},
        )
        self.assertEqual(expired["status"], "no_matching_reservation")
        self.assertEqual(self.repo.get_reservation(old_reservation["reservation_id"])["status"], "expired")
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "pooled")

    def test_own_clan_part_is_blocked_even_if_corrupted_reservation_exists(self):
        cycle_id = self.repo.get_active_cycle()["cycle_id"]
        own_part = next(part for part in self.repo.list_parts(cycle_id) if part["clan_code"] == "virex")
        reservation = self.repo.create_reservation(
            cycle_id,
            own_part["part_id"],
            "map:52.5:21.5:own",
            "main",
            "virex",
            expires_at=future_iso(),
        )

        result = self.repo.discover_reserved_part(
            reservation["reservation_id"],
            player=self.player(),
            target=self.target("map:52.5:21.5:own"),
            operation_id="op-own",
            result={"target_captured": True},
        )

        self.assertEqual(result["status"], "own_clan_part_blocked")
        self.assertEqual(self.repo.get_part(own_part["part_id"])["status"], "reserved")


if __name__ == "__main__":
    unittest.main()
