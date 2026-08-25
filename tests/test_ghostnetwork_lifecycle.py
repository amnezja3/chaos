import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostPartLifecycleService, GhostNetworkRepository
from ghostnetwork.errors import InvalidPartStateTransition


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostPartLifecycleServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.lifecycle = GhostPartLifecycleService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def target(self, target_id="target-life"):
        return {
            "target_id": target_id,
            "lat": 52.25,
            "lng": 21.0,
            "label": "Lifecycle Target",
            "source_type": "shop",
            "target_mode": "standard",
        }

    def player(self, clan="virex"):
        return {
            "player_id": "main",
            "username": "main",
            "clan_code": clan,
            "ghost_clan": clan,
        }

    def reserve_and_discover(self, target_id="target-life"):
        part = self.repo.list_reservable_parts(self.cycle["cycle_id"], excluded_clan="virex")[0]
        reservation = self.lifecycle.reserve_part(
            self.cycle["cycle_id"],
            part["part_id"],
            target_id,
            "main",
            "virex",
            expires_at=future_iso(),
        )
        result = self.lifecycle.discover_part(
            reservation["reservation_id"],
            player=self.player(),
            target=self.target(target_id),
            operation_id="op-life",
            result={"target_captured": True},
        )
        self.assertEqual(result["status"], "discovered")
        return result["part"]

    def test_full_part_lifecycle_and_terminal_consumed(self):
        part = self.reserve_and_discover()
        original_target_id = part["target_id"]
        original_discoverer = part["discovered_by"]
        self.assertEqual(part["status"], "public")
        self.assertEqual(part["conflict_state"], "none")

        territory = {
            "territory_id": "terr-own",
            "territory_owner_id": "main",
            "territory_clan": part["clan_code"],
            "territory_state_version": 7,
        }
        activated = self.lifecycle.activate_part(
            part["part_id"],
            territory=territory,
            player_id="main",
            player_clan=part["clan_code"],
            source_event_id="territory-7",
        )
        self.assertEqual(activated["status"], "active")
        self.assertEqual(activated["territory_clan"], part["clan_code"])
        self.assertTrue(activated["activated_at"])
        self.assertTrue(activated["last_activated_at"])

        frozen = self.lifecycle.freeze_for_conflict(
            part["part_id"],
            "conflict-1",
            source_event_id="conflict-open-1",
        )
        self.assertEqual(frozen["status"], "active")
        self.assertEqual(frozen["conflict_state"], "contested")
        self.assertEqual(frozen["frozen_status"], "active")

        resolved = self.lifecycle.resolve_after_conflict(
            part["part_id"],
            resolution_status="active",
            conflict_id="conflict-1",
            source_event_id="conflict-close-1",
        )
        self.assertEqual(resolved["status"], "active")
        self.assertEqual(resolved["conflict_state"], "none")
        self.assertEqual(resolved["frozen_status"], "")

        foreign_territory = {
            "territory_id": "terr-foreign",
            "territory_owner_id": "robot",
            "territory_clan": "sentinel_order",
            "territory_state_version": 8,
        }
        contained = self.lifecycle.contain_part(
            part["part_id"],
            territory=foreign_territory,
            source_event_id="territory-8",
        )
        self.assertEqual(contained["status"], "contained")
        self.assertEqual(contained["territory_owner_id"], "robot")

        revealed = self.lifecycle.reveal_part(part["part_id"], source_event_id="territory-neutral")
        self.assertEqual(revealed["status"], "public")
        self.assertEqual(revealed["territory_owner_id"], "")
        self.assertEqual(revealed["target_id"], original_target_id)
        self.assertEqual(revealed["discovered_by"], original_discoverer)

        events = self.repo.list_events(self.cycle["cycle_id"], limit=500)
        contained_event = next(event for event in events if event["event_type"] == "ghost.part_contained")
        contested_event = next(event for event in events if event["event_type"] == "ghost.part_contested")
        self.assertEqual(contained_event["audience_scope"], "owner")
        self.assertEqual(contested_event["audience_scope"], "public")

        consumed = self.lifecycle.consume_part(part["part_id"], "signal-2108")
        self.assertEqual(consumed["status"], "consumed")
        self.assertEqual(consumed["consumed_signal_id"], "signal-2108")
        with self.assertRaises(InvalidPartStateTransition):
            self.lifecycle.activate_part(part["part_id"], territory=territory)

    def test_idempotent_event_does_not_bump_version_or_duplicate_history(self):
        part = self.reserve_and_discover("target-idempotent")
        territory = {
            "territory_id": "terr-own",
            "territory_owner_id": "main",
            "territory_clan": part["clan_code"],
            "territory_state_version": 11,
        }
        before = self.repo.get_state_version(self.cycle["cycle_id"])
        first = self.lifecycle.activate_part(
            part["part_id"],
            territory=territory,
            player_id="main",
            player_clan=part["clan_code"],
            source_event_id="same-territory-event",
        )
        after_first = self.repo.get_state_version(self.cycle["cycle_id"])
        second = self.lifecycle.activate_part(
            part["part_id"],
            territory=territory,
            player_id="main",
            player_clan=part["clan_code"],
            source_event_id="same-territory-event",
        )
        after_second = self.repo.get_state_version(self.cycle["cycle_id"])

        self.assertGreater(after_first, before)
        self.assertEqual(after_second, after_first)
        self.assertEqual(second["status"], first["status"])
        activation_events = [
            event for event in self.repo.list_events(self.cycle["cycle_id"], limit=500)
            if event["event_type"] == "ghost.part_activated"
        ]
        self.assertEqual(len(activation_events), 1)
        self.assertEqual(activation_events[0]["payload"]["previous_status"], "public")
        self.assertEqual(activation_events[0]["payload"]["status"], "active")
        self.assertEqual(activation_events[0]["payload"]["conflict_state"], "none")
        self.assertEqual(activation_events[0]["audience_scope"], "public")

        deactivated = self.lifecycle.deactivate_part(
            part["part_id"],
            next_status="contained",
            territory=territory,
            source_event_id="same-territory-deactivation",
        )
        self.assertEqual(deactivated["status"], "contained")
        deactivation_event = next(
            event for event in self.repo.list_events(self.cycle["cycle_id"], limit=500)
            if event["event_type"] == "ghost.part_deactivated"
        )
        self.assertEqual(deactivation_event["audience_scope"], "public")

    def test_invalid_transitions_and_health_diagnostics(self):
        pooled = self.repo.list_reservable_parts(self.cycle["cycle_id"], excluded_clan="virex")[0]
        with self.assertRaises(InvalidPartStateTransition):
            self.lifecycle.activate_part(
                pooled["part_id"],
                territory={
                    "territory_id": "terr-own",
                    "territory_owner_id": "main",
                    "territory_clan": pooled["clan_code"],
                },
            )

        part = self.reserve_and_discover("target-health")
        self.repo.update_part(part["part_id"], status="active", territory_clan="wrong_clan")
        report = self.repo.health_check()
        self.assertFalse(report["ok"])
        self.assertIn("active_part_wrong_territory_clan", report["errors"])

    def test_replay_detects_status_sequence(self):
        part = self.reserve_and_discover("target-replay")
        revealed = self.lifecycle.reveal_part(part["part_id"], source_event_id="reveal-replay")
        self.assertEqual(revealed["status"], "public")
        replay = self.lifecycle.replay_part_history(part["part_id"])
        self.assertTrue(replay["ok"])
        self.assertEqual(replay["status"], "public")
        self.assertEqual(replay["conflict_state"], "none")


if __name__ == "__main__":
    unittest.main()
