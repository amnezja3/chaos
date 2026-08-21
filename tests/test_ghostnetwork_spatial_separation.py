import math
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.repository import haversine_distance_km


KM_PER_RADIAN = 6371.0


def longitude_for_km(distance_km):
    return math.degrees(float(distance_km) / KM_PER_RADIAN)


class BarrierRepository(GhostNetworkRepository):
    barrier = None

    def create_reservation(self, *args, **kwargs):
        if self.barrier is not None:
            self.barrier.wait(timeout=5)
        return super().create_reservation(*args, **kwargs)


class GhostNetworkSpatialSeparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]

    def tearDown(self):
        BarrierRepository.barrier = None
        self.tmp.cleanup()

    @staticmethod
    def player(username="main", clan="virex"):
        return {
            "player_id": username,
            "username": username,
            "clan_code": clan,
            "ghost_clan": clan,
            "ghost_profession": "operator",
        }

    @staticmethod
    def target(target_id, distance_km=0.0):
        return {
            "target_id": target_id,
            "lat": 0.0,
            "lng": longitude_for_km(distance_km),
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }

    def service(self, repository=None, ttl=600):
        return GhostNetworkService(
            repository=repository or self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0, reservation_ttl_seconds=ttl),
        )

    def anchor_part(self, status, distance_km=0.0):
        part = self.repo.list_reservable_parts(self.cycle["cycle_id"])[0]
        self.repo.update_part(
            part["part_id"],
            status=status,
            target_id=f"anchor-{status}-{distance_km}",
            latitude=0.0,
            longitude=longitude_for_km(distance_km),
        )
        return self.repo.get_part(part["part_id"])

    def test_haversine_boundary_contract(self):
        self.assertLess(haversine_distance_km(0, 0, 0, longitude_for_km(49.9)), 50.0)
        self.assertAlmostEqual(haversine_distance_km(0, 0, 0, longitude_for_km(50.0)), 50.0, places=6)
        self.assertGreater(haversine_distance_km(0, 0, 0, longitude_for_km(70.0)), 50.0)

    def test_no_anchor_allows_reservation_and_reserved_anchor_blocks(self):
        service = self.service()
        first = service.on_target_aimed(self.player(), self.target("target-a"))
        self.assertEqual(first["status"], "reserved")
        reserved_part = self.repo.get_part(self.repo.get_reservation(first["reservation_id"])["part_id"])
        self.assertEqual(reserved_part["latitude"], 0.0)
        blocked = service.on_target_aimed(self.player("second"), self.target("target-b", 10.0))
        self.assertEqual(blocked["status"], "roll_missed")
        self.assertEqual(blocked["internal_reason"], "part_too_close")
        self.assertNotIn("part_id", blocked)
        self.assertNotIn("latitude", blocked)
        self.assertNotIn("longitude", blocked)
        self.assertNotIn("distance", blocked)
        self.assertEqual(self.repo.get_reservation_status(self.cycle["cycle_id"])["active"], 1)

    def test_49_9_is_blocked_and_50_and_70_are_allowed(self):
        for distance, allowed in ((49.9, False), (50.0, True), (70.0, True)):
            with self.subTest(distance=distance):
                with tempfile.TemporaryDirectory() as folder:
                    repo = GhostNetworkRepository(db_path=os.path.join(folder, "case.sqlite3"))
                    cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
                    part = repo.list_reservable_parts(cycle["cycle_id"])[0]
                    repo.update_part(part["part_id"], status="public", target_id="anchor", latitude=0.0, longitude=0.0)
                    result = self.service(repo).on_target_aimed(self.player(), self.target("candidate", distance))
                    self.assertEqual(result["status"] == "reserved", allowed)

    def test_public_contained_and_active_all_block(self):
        for status in ("public", "contained", "active"):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as folder:
                    repo = GhostNetworkRepository(db_path=os.path.join(folder, "state.sqlite3"))
                    cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
                    part = repo.list_reservable_parts(cycle["cycle_id"])[0]
                    repo.update_part(part["part_id"], status=status, target_id="anchor", latitude=0.0, longitude=0.0)
                    result = self.service(repo).on_target_aimed(self.player(), self.target("nearby", 10.0))
                    self.assertEqual(result["status"], "roll_missed")
                    self.assertEqual(result["internal_reason"], "part_too_close")

    def test_expiration_releases_anchor_and_pool(self):
        service = self.service(ttl=1)
        first = service.on_target_aimed(self.player(), self.target("expiring"))
        reservation = self.repo.get_reservation(first["reservation_id"])
        with self.repo.transaction():
            self.repo._transaction_conn.execute(
                "UPDATE ghost_part_reservations SET expires_at = ? WHERE reservation_id = ?",
                ("2000-01-01T00:00:00+00:00", reservation["reservation_id"]),
            )
        service.expire_due_reservations()
        released_part = self.repo.get_part(reservation["part_id"])
        self.assertEqual(released_part["status"], "pooled")
        self.assertEqual(released_part["target_id"], "")
        self.assertIsNone(released_part["latitude"])
        second = service.on_target_aimed(self.player("second"), self.target("replacement", 10.0))
        self.assertEqual(second["status"], "reserved")

    def test_pooled_and_previous_cycle_do_not_block(self):
        pooled = self.repo.list_reservable_parts(self.cycle["cycle_id"])[0]
        self.assertIsNone(pooled["latitude"])
        self.assertEqual(self.service().on_target_aimed(self.player(), self.target("current"))["status"], "reserved")

        previous_path = os.path.join(self.tmp.name, "next-cycle.sqlite3")
        repo = GhostNetworkRepository(db_path=previous_path)
        current = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
        old = repo.create_cycle(cycle_id="ghostnetwork_old", status="closed")
        sample = dict(repo.list_parts(current["cycle_id"])[0])
        sample.update({
            "part_id": "ghostnetwork_old_v1",
            "cycle_id": old["cycle_id"],
            "status": "consumed",
            "target_id": "old",
            "latitude": 0.0,
            "longitude": 0.0,
        })
        repo.create_parts([sample])
        result = self.service(repo).on_target_aimed(self.player(), self.target("new", 10.0))
        self.assertEqual(result["status"], "reserved")

    def test_concurrent_nearby_attempts_cannot_both_reserve(self):
        BarrierRepository.barrier = threading.Barrier(2)
        results = []
        repositories = [
            BarrierRepository(db_path=self.db_path),
            BarrierRepository(db_path=self.db_path),
        ]

        def attempt(repo, username, target):
            results.append(self.service(repo).on_target_aimed(self.player(username), target))

        threads = [
            threading.Thread(target=attempt, args=(repositories[0], "alpha", self.target("alpha", 0.0))),
            threading.Thread(target=attempt, args=(repositories[1], "beta", self.target("beta", 20.0))),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(result["status"] == "reserved" for result in results), 1)
        self.assertEqual(sum(result.get("internal_reason") == "part_too_close" for result in results), 1)
        self.assertEqual(self.repo.get_reservation_status(self.cycle["cycle_id"])["active"], 1)

    def test_e2e_a_and_c_discover_while_b_is_rejected(self):
        service = self.service()
        initial_pool = len(self.repo.list_reservable_parts(self.cycle["cycle_id"]))
        player = self.player()

        target_a = self.target("target-a", 0.0)
        reserved_a = service.on_target_aimed(player, target_a)
        discovered_a = self.repo.discover_reserved_part(reserved_a["reservation_id"], player=player, target=target_a)
        self.assertEqual(discovered_a["status"], "discovered")

        rejected_b = service.on_target_aimed(self.player("player-b"), self.target("target-b", 20.0))
        self.assertEqual(rejected_b["status"], "roll_missed")

        target_c = self.target("target-c", 80.0)
        player_c = self.player("player-c")
        reserved_c = service.on_target_aimed(player_c, target_c)
        discovered_c = self.repo.discover_reserved_part(reserved_c["reservation_id"], player=player_c, target=target_c)
        self.assertEqual(discovered_c["status"], "discovered")

        final_pool = len(self.repo.list_reservable_parts(self.cycle["cycle_id"]))
        self.assertEqual(initial_pool - final_pool, 2)
        self.assertIsNone(self.repo.find_part_by_target(self.cycle["cycle_id"], "target-b"))
        self.assertGreaterEqual(
            haversine_distance_km(
                discovered_a["part"]["latitude"], discovered_a["part"]["longitude"],
                discovered_c["part"]["latitude"], discovered_c["part"]["longitude"],
            ),
            50.0,
        )


if __name__ == "__main__":
    unittest.main()
