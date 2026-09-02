import os
import tempfile
import unittest

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.narrative import GHOST_EVENT_POLICY


class GhostNetworkStrategicConflictTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.service = GhostNetworkService(repository=self.repo)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.part = self.repo.list_parts(self.cycle["cycle_id"])[0]
        self.part = self.repo.update_part(
            self.part["part_id"],
            status="active",
            territory_id="territory-alpha",
            territory_owner_id="owner-main",
            territory_clan=self.part["clan_code"],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _start_conflict(self, owner_id="owner-main", clan_code=None, started_at="2026-07-19T10:00:00+00:00"):
        clan_code = clan_code or self.part["clan_code"]
        result = self.service.on_ghost_conflict_started(
            self.part,
            territory_snapshot={
                "territory_id": "territory-alpha",
                "owner_id": owner_id,
                "clan_code": clan_code,
                "integrity": 100,
                "security_score": 8,
                "active_offensive_operations": 2,
                "participants": ["attacker-a"],
            },
            context={"started_at": started_at, "dedupe_key": f"conflict:{self.part['part_id']}:{started_at}"},
        )
        self.assertTrue(result["ok"])
        return result["conflict"]

    def test_real_defense_creates_capped_owner_and_support_rewards_once(self):
        conflict = self._start_conflict()
        self.service.record_ghost_offensive_action(
            conflict["conflict_id"],
            "security_disarmed",
            player_id="attacker-a",
            clan_code="nova",
            mechanical_value=35,
            source_event_id="offense-1",
        )
        self.service.record_ghost_defensive_action(
            conflict["conflict_id"],
            "security_rebuilt",
            player_id="support-a",
            clan_code=self.part["clan_code"],
            mechanical_value=7,
            source_event_id="defense-1",
        )

        result = self.service.resolve_ghost_conflict_outcome(
            conflict["conflict_id"],
            final_state={
                "owner_id": "owner-main",
                "clan_code": self.part["clan_code"],
                "territory_state": "stable",
                "integrity": 92,
                "resolved_at": "2026-07-19T10:05:00+00:00",
            },
        )
        retry = self.service.resolve_ghost_conflict_outcome(conflict["conflict_id"])
        owner_summary = self.service.get_player_reward_summary("owner-main", cycle_id=self.cycle["cycle_id"])
        support_summary = self.service.get_player_reward_summary("support-a", cycle_id=self.cycle["cycle_id"])
        event = next(
            item for item in self.repo.list_events(self.cycle["cycle_id"], limit=200)
            if item["event_type"] == "ghost.part_defended"
        )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["defense"]["status"], "full_reward")
        self.assertEqual(retry["status"], "already_resolved")
        self.assertEqual(owner_summary["by_type"]["part_defended"]["count"], 1)
        self.assertEqual(support_summary["by_type"]["defense_support"]["count"], 1)
        self.assertLessEqual(owner_summary["pending_rsp"] + support_summary["pending_rsp"], 60)
        self.assertNotIn("part_code", event["payload"])
        self.assertNotIn("machine_code", event["payload"])
        self.assertNotIn("profession_code", event["payload"])
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event["event_id"], limit=10,
        )
        self.assertEqual(
            {task["target_medium"] for task in tasks},
            set(GHOST_EVENT_POLICY["ghost.part_defended"]["target_media"]),
        )
        self.assertTrue(all(task["audience_scope"] == "public" for task in tasks))

    def test_minor_attack_is_audited_without_full_defense_reward(self):
        conflict = self._start_conflict(started_at="2026-07-19T11:00:00+00:00")
        self.service.record_ghost_offensive_action(
            conflict["conflict_id"],
            "security_disarmed",
            player_id="attacker-a",
            clan_code="nova",
            mechanical_value=3,
            source_event_id="minor-offense",
        )
        self.service.record_ghost_defensive_action(
            conflict["conflict_id"],
            "security_rebuilt",
            player_id="owner-main",
            clan_code=self.part["clan_code"],
            mechanical_value=1,
            source_event_id="minor-defense",
        )

        result = self.service.resolve_ghost_conflict_outcome(
            conflict["conflict_id"],
            final_state={
                "owner_id": "owner-main",
                "clan_code": self.part["clan_code"],
                "territory_state": "stable",
                "integrity": 100,
                "resolved_at": "2026-07-19T11:05:00+00:00",
            },
        )
        summary = self.service.get_player_reward_summary("owner-main", cycle_id=self.cycle["cycle_id"])

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["defense"]["status"], "no_reward")
        self.assertEqual(summary["by_type"].get("part_defended", {}).get("count", 0), 0)

    def test_recovery_requires_previous_foreign_control_and_real_disarm(self):
        self.part = self.repo.update_part(
            self.part["part_id"],
            status="active",
            territory_owner_id="liberator",
            territory_clan=self.part["clan_code"],
        )
        period = self.repo.insert_control_period({
            "cycle_id": self.cycle["cycle_id"],
            "part_id": self.part["part_id"],
            "owner_id": "foreign-owner",
            "clan_code": "nova",
            "territory_id": "territory-foreign",
            "status": "stable",
            "started_at": "2026-07-19T08:00:00+00:00",
            "ended_at": "2026-07-19T10:00:00+00:00",
            "duration_seconds": 7200,
            "end_reason": "recovered",
            "dedupe_key": "period:foreign-control",
        })
        conflict = self._start_conflict(
            owner_id="foreign-owner",
            clan_code="nova",
            started_at="2026-07-19T10:05:00+00:00",
        )
        self.service.record_ghost_offensive_action(
            conflict["conflict_id"],
            "security_disarmed",
            player_id="liberator",
            clan_code=self.part["clan_code"],
            mechanical_value=12,
            source_event_id="recover-disarm",
        )

        result = self.service.resolve_ghost_conflict_outcome(
            conflict["conflict_id"],
            final_state={
                "owner_id": "liberator",
                "clan_code": self.part["clan_code"],
                "territory_state": "stable",
                "integrity": 88,
                "activator_id": "liberator",
                "resolved_at": "2026-07-19T10:08:00+00:00",
            },
            context={"previous_period": period},
        )
        summary = self.service.get_player_reward_summary("liberator", cycle_id=self.cycle["cycle_id"])
        transfer = self.repo.list_transfer_history(part_id=self.part["part_id"], limit=5)[0]

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["recovery"]["status"], "full_reward")
        self.assertEqual(summary["by_type"]["part_recovered"]["count"], 1)
        self.assertEqual(transfer["reward_status"], "full_reward")
        event = next(
            item for item in self.repo.list_events(self.cycle["cycle_id"], limit=200)
            if item["event_type"] == "ghost.part_recovered"
        )
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event["event_id"], limit=10,
        )
        self.assertEqual(
            {task["target_medium"] for task in tasks},
            set(GHOST_EVENT_POLICY["ghost.part_recovered"]["target_media"]),
        )

    def test_fast_same_pair_transfer_enters_cooldown_without_blocking_resolution(self):
        self.repo.insert_transfer_history({
            "cycle_id": self.cycle["cycle_id"],
            "part_id": self.part["part_id"],
            "previous_owner_id": "foreign-owner",
            "new_owner_id": "owner-main",
            "previous_clan": "nova",
            "new_clan": self.part["clan_code"],
            "conflict_id": "old-conflict",
            "reward_status": "full_reward",
            "reward_amount": 20,
            "dedupe_key": "transfer:old",
            "created_at": "2026-07-19T10:00:00+00:00",
        })
        conflict = self._start_conflict(started_at="2026-07-19T10:05:00+00:00")
        self.service.record_ghost_offensive_action(
            conflict["conflict_id"],
            "security_disarmed",
            player_id="attacker-a",
            clan_code="nova",
            mechanical_value=30,
            source_event_id="pair-offense",
        )
        self.service.record_ghost_defensive_action(
            conflict["conflict_id"],
            "security_rebuilt",
            player_id="owner-main",
            clan_code=self.part["clan_code"],
            mechanical_value=5,
            source_event_id="pair-defense",
        )

        result = self.service.resolve_ghost_conflict_outcome(
            conflict["conflict_id"],
            final_state={
                "owner_id": "foreign-owner",
                "clan_code": "nova",
                "territory_state": "stable",
                "integrity": 90,
                "resolved_at": "2026-07-19T10:10:00+00:00",
            },
        )

        self.assertEqual(result["status"], "resolved")
        self.assertIn(result["defense"]["status"], {"cooldown", "no_reward"})


if __name__ == "__main__":
    unittest.main()
