import os
import tempfile
import unittest

from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService, GhostRuntimeCoordinator


class GhostNetworkRuntimeDurabilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghost-runtime.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=self.repo).ensure_active_cycle()
        self.service = GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
        )
        self.player = {"player_id": "alice", "username": "alice", "clan_code": "virex"}
        self.target = {
            "target_id": "map:52.1:21.1:durable",
            "lat": 52.1,
            "lng": 21.1,
            "label": "Durable target",
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_committed_capture_is_reconciled_and_drained_exactly_once(self):
        aimed = self.service.on_target_aimed(self.player, self.target)
        self.assertEqual(aimed["status"], "reserved")
        profiles = {"alice": {"username": "alice", "respect": 0, "ghost_clan_code": "virex"}}

        coordinator = GhostRuntimeCoordinator(
            service=self.service,
            captured_target_reader=lambda player_id, target_id: (
                dict(self.target) if (player_id, target_id) == ("alice", self.target["target_id"]) else None
            ),
            profile_loader=lambda player_id: dict(profiles[player_id]),
            profile_saver=lambda profile: profiles.__setitem__(profile["username"], dict(profile)),
        )

        first = coordinator.drain()
        self.assertTrue(first["ok"], first)
        self.assertEqual(first["reconciliation"]["enqueued"], 1)
        self.assertEqual(first["processed"], 1)
        self.assertEqual(first["summary"]["applied"], 1)
        part = self.repo.find_part_by_target(self.repo.get_active_cycle()["cycle_id"], self.target["target_id"])
        self.assertEqual(part["status"], "public")
        self.assertGreater(profiles["alice"]["respect"], 0)
        contributions = self.repo.list_player_contributions("alice", cycle_id=self.repo.get_active_cycle()["cycle_id"])
        self.assertEqual(len(contributions), 1)
        discovery = next(
            event for event in self.repo.list_events(limit=1000)
            if event["event_type"] == "ghost.part_discovered"
            and event["part_id"] == part["part_id"]
        )
        narrative_tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=discovery["event_id"], limit=10,
        )
        self.assertEqual(
            {task["target_medium"] for task in narrative_tasks},
            {"blacknet", "googleplex_news"},
        )
        self.assertTrue(all(task["audience_scope"] == "public" for task in narrative_tasks))

        second = coordinator.drain()
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["reconciliation"]["enqueued"], 0)
        self.assertEqual(second["processed"], 0)
        self.assertEqual(len(self.repo.list_player_contributions("alice", cycle_id=self.repo.get_active_cycle()["cycle_id"])), 1)
        self.assertEqual(profiles["alice"]["ghostnetwork_reward_history"].__len__(), 1)
        self.assertEqual(
            len(self.repo.list_narrative_outbox(
                source_scope="ghostnetwork", source_event_id=discovery["event_id"], limit=10,
            )),
            len(narrative_tasks),
        )

    def test_capture_without_reservation_does_not_create_failed_effect(self):
        coordinator = GhostRuntimeCoordinator(
            service=self.service,
            captured_target_reader=lambda *_: dict(self.target),
        )
        drained = coordinator.drain()
        self.assertTrue(drained["ok"])
        self.assertEqual(drained["processed"], 0)
        self.assertEqual(self.repo.get_capture_effect_summary()["total"], 0)


if __name__ == "__main__":
    unittest.main()
