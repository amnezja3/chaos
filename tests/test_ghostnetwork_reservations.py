import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostNetworkReservationServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycles = GhostCycleService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def service(self, enabled=True, chance=1.0, ttl=600):
        return GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(
                enabled=enabled,
                chance=chance,
                reservation_ttl_seconds=ttl,
            ),
        )

    def active_cycle(self):
        return self.cycles.ensure_active_cycle()["cycle"]

    def player(self, username="main", clan="virex"):
        return {
            "player_id": username,
            "username": username,
            "clan_code": clan,
            "ghost_clan": clan,
            "ghost_profession": "operator",
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

    def test_no_active_cycle_does_not_reserve(self):
        result = self.service().on_target_aimed(self.player(), self.target())
        self.assertEqual(result["status"], "no_active_cycle")

    def test_disabled_and_zero_chance_do_not_reserve(self):
        self.active_cycle()
        result = self.service(enabled=False).on_target_aimed(self.player(), self.target())
        self.assertEqual(result["status"], "roll_missed")
        result = self.service(enabled=True, chance=0.0).on_target_aimed(self.player(), self.target("target-2"))
        self.assertEqual(result["status"], "roll_missed")

    def test_one_hundred_percent_reserves_foreign_pooled_part(self):
        cycle = self.active_cycle()
        result = self.service().on_target_aimed(self.player(clan="virex"), self.target())
        self.assertEqual(result["status"], "reserved")
        reservation = self.repo.get_reservation(result["reservation_id"])
        self.assertEqual(reservation["cycle_id"], cycle["cycle_id"])
        self.assertEqual(reservation["target_id"], "map:52.1:21.1:shop")
        self.assertEqual(reservation["player_id"], "main")
        part = self.repo.get_part(reservation["part_id"])
        self.assertEqual(part["status"], "reserved")
        self.assertNotEqual(part["clan_code"], "virex")

    def test_same_player_same_target_returns_existing_without_reroll(self):
        self.active_cycle()
        service = self.service()
        first = service.on_target_aimed(self.player(), self.target())
        second = service.on_target_aimed(self.player(), self.target())
        self.assertEqual(first["status"], "reserved")
        self.assertEqual(second["status"], "existing_reservation")
        status = service.get_reservation_status()
        self.assertEqual(status["active"], 1)
        self.assertEqual(status["parts_reserved"], 1)

    def test_other_player_same_target_gets_no_signal(self):
        self.active_cycle()
        service = self.service()
        first = service.on_target_aimed(self.player("main"), self.target())
        second = service.on_target_aimed(self.player("other"), self.target())
        self.assertEqual(first["status"], "reserved")
        self.assertEqual(second["status"], "target_reserved")
        self.assertEqual(service.get_reservation_status()["active"], 1)

    def test_ineligible_targets_and_missing_clan_do_not_reserve(self):
        self.active_cycle()
        service = self.service()
        self.assertEqual(
            service.on_target_aimed(self.player(), {"target_id": "player:robot", "lat": 1, "lng": 1, "target_mode": "player"})["status"],
            "not_eligible",
        )
        self.assertEqual(
            service.on_target_aimed(self.player(), {"target_id": "map:bad", "label": "Bad"})["status"],
            "not_eligible",
        )
        self.assertEqual(
            service.on_target_aimed(self.player(clan=""), self.target("target-missing-clan"))["status"],
            "missing_player_clan",
        )

    def test_transitional_cycle_does_not_reserve(self):
        self.repo.create_cycle(cycle_id="ghostnetwork_0001", status="stabilizing")
        result = self.service().on_target_aimed(self.player(), self.target())
        self.assertEqual(result["status"], "cycle_not_active")

    def test_already_emitted_target_prevents_reroll(self):
        cycle = self.active_cycle()
        part = self.repo.list_parts(cycle["cycle_id"])[0]
        self.repo.update_part(
            part["part_id"],
            status="public",
            target_id="target-emitted",
            latitude=52.2,
            longitude=21.2,
        )
        result = self.service().on_target_aimed(self.player(), self.target("target-emitted"))
        self.assertEqual(result["status"], "target_already_emitted")

    def test_attach_release_expire_and_diagnostics(self):
        self.active_cycle()
        service = self.service(ttl=1)
        reserved = service.on_target_aimed(self.player(), self.target("target-attach"))
        attached = service.attach_reservation_to_operation("main", "target-attach", "op-1")
        self.assertEqual(attached["status"], "attached")
        reservation = self.repo.get_reservation(reserved["reservation_id"])
        self.assertEqual(reservation["operation_id"], "op-1")

        released = service.release_reservation(reserved["reservation_id"], "operation_failed")
        self.assertEqual(released["status"], "released")
        self.assertEqual(self.repo.get_part(reservation["part_id"])["status"], "pooled")

        expiring = service.on_target_aimed(self.player(), self.target("target-expire"))
        self.repo.release_reservation(expiring["reservation_id"], reason="target_abandoned")
        old = self.repo.create_reservation(
            self.repo.get_active_cycle()["cycle_id"],
            self.repo.list_reservable_parts(self.repo.get_active_cycle()["cycle_id"], excluded_clan="virex")[0]["part_id"],
            "target-old",
            "main",
            "virex",
            expires_at="2000-01-01T00:00:00+00:00",
        )
        expired = service.expire_due_reservations()
        self.assertIn(old["reservation_id"], {item["reservation_id"] for item in expired})

        status = service.get_reservation_status()
        self.assertEqual(status["released"], 2)
        self.assertEqual(status["expired"], 1)
        self.assertEqual(status["active"], 0)
        self.assertEqual(status["integrity_errors"], [])


if __name__ == "__main__":
    unittest.main()
