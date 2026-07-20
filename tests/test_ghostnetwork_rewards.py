import os
import tempfile
import unittest

from ghostnetwork import (
    GhostCycleService,
    GhostNetworkRepository,
    GhostNetworkService,
)


class GhostNetworkRewardLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.service = GhostNetworkService(repository=self.repo)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]

    def tearDown(self):
        self.tmp.cleanup()

    def profile(self):
        return {"username": "main", "respect": 7, "level": 3, "clan": "virex"}

    def event(self, event_type, **payload):
        body = {
            "event_id": payload.pop("event_id", f"{event_type}:event"),
            "event_type": event_type,
            "cycle_id": self.cycle["cycle_id"],
            "part_id": payload.pop("part_id", "part-001"),
            "player_id": payload.pop("player_id", "main"),
            "clan_code": payload.pop("clan_code", "virex"),
            "payload": payload,
        }
        body["payload"].setdefault("score", 10)
        return body

    def test_record_contribution_is_idempotent_and_aggregates(self):
        first = self.service.record_contribution(
            cycle_id=self.cycle["cycle_id"],
            player_id="main",
            clan_code="virex",
            profession_code="broker",
            contribution_type="part_discovered",
            part_id="part-001",
            score=10,
            weight=1.5,
            dedupe_key="contrib:main:part-001:discover",
        )
        second = self.service.record_contribution(
            cycle_id=self.cycle["cycle_id"],
            player_id="main",
            clan_code="virex",
            profession_code="broker",
            contribution_type="part_discovered",
            part_id="part-001",
            score=10,
            weight=1.5,
            dedupe_key="contrib:main:part-001:discover",
        )

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(first["contribution"]["contribution_id"], second["contribution"]["contribution_id"])
        self.assertTrue(second["contribution"]["idempotent"])

        player = self.service.aggregate_player_contribution("main", cycle_id=self.cycle["cycle_id"])
        clan = self.service.aggregate_clan_contribution("virex", cycle_id=self.cycle["cycle_id"])
        self.assertEqual(player["count"], 1)
        self.assertEqual(player["score"], 10)
        self.assertEqual(player["weighted_score"], 15.0)
        self.assertEqual(clan["count"], 1)

    def test_discovery_reward_applies_rsp_once(self):
        profile = self.profile()
        result = self.service.handle_reward_event(
            self.event("ghost.part_discovered", discovered_by="main", event_id="discover-1"),
            profile=profile,
            apply=True,
        )
        duplicate = self.service.handle_reward_event(
            self.event("ghost.part_discovered", discovered_by="main", event_id="discover-retry"),
            profile=profile,
            apply=True,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["applied"]["status"], "applied")
        self.assertGreater(profile["respect"], 7)
        self.assertEqual(duplicate["created"]["status"], "exists")
        self.assertIsNone(duplicate["applied"])

        summary = self.service.get_player_reward_summary("main", cycle_id=self.cycle["cycle_id"])
        self.assertEqual(summary["by_type"]["part_discovered"]["count"], 1)
        self.assertEqual(summary["applied_rsp"], result["applied"]["rsp"])
        self.assertEqual(profile["ghostnetwork_stats"]["parts_discovered"], 1)

    def test_first_containment_and_activation_have_separate_rewards(self):
        profile = self.profile()
        contained = self.service.handle_reward_event(
            self.event("ghost.part_first_contained", part_id="part-002", territory_id="territory-a"),
            profile=profile,
            apply=False,
        )
        activated = self.service.handle_reward_event(
            self.event("ghost.part_activated", part_id="part-002", territory_id="territory-a"),
            profile=profile,
            apply=False,
        )

        self.assertEqual(contained["plan"]["reward_type"], "part_first_contained")
        self.assertEqual(activated["plan"]["reward_type"], "part_first_activated")
        self.assertNotEqual(contained["created"]["reward"]["reward_key"], activated["created"]["reward"]["reward_key"])

    def test_hold_rewards_are_periodic_and_pause_in_conflict(self):
        contested = self.service.handle_reward_event(
            self.event(
                "ghost.part_stable_held",
                part_id="part-003",
                owner_id="main",
                owner_clan="virex",
                part_clan="virex",
                period_start="2026-07-19T10:00:00Z",
                conflict_state="contested",
            ),
            profile=self.profile(),
        )
        foreign = self.service.handle_reward_event(
            self.event(
                "ghost.part_stable_held",
                part_id="part-003",
                owner_id="main",
                owner_clan="virex",
                part_clan="nova",
                period_start="2026-07-19T11:00:00Z",
                conflict_state="none",
            ),
            profile=self.profile(),
        )
        valid = self.service.handle_reward_event(
            self.event(
                "ghost.part_stable_held",
                part_id="part-003",
                owner_id="main",
                owner_clan="virex",
                part_clan="virex",
                period_start="2026-07-19T12:00:00Z",
                conflict_state="none",
            ),
            profile=self.profile(),
        )

        self.assertFalse(contested["ok"])
        self.assertEqual(contested["reason"], "hold_paused_by_conflict")
        self.assertFalse(foreign["ok"])
        self.assertEqual(foreign["reason"], "foreign_hold_not_rewarded")
        self.assertTrue(valid["ok"])
        self.assertEqual(valid["created"]["reward"]["status"], "pending")

    def test_clan_reputation_updates_on_reward_apply(self):
        profile = self.profile()
        result = self.service.handle_reward_event(
            self.event("ghost.part_activated", part_id="part-004", score=12),
            profile=profile,
            apply=True,
        )

        reputation = self.repo.get_clan_reputation("virex")
        self.assertEqual(result["applied"]["status"], "applied")
        self.assertGreater(reputation["total_reputation"], 0)
        self.assertEqual(reputation["parts_activated"], 1)

    def test_reconcile_detects_contribution_without_reward(self):
        recorded = self.service.record_contribution(
            cycle_id=self.cycle["cycle_id"],
            player_id="main",
            clan_code="virex",
            contribution_type="part_discovered",
            part_id="part-orphan",
            score=4,
            source_event_id="orphan-event",
            dedupe_key="contrib:orphan",
        )
        report = self.service.reconcile_ghost_rewards(cycle_id=self.cycle["cycle_id"], dry_run=True)

        self.assertTrue(recorded["ok"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["issues"][0]["type"], "contribution_without_reward")


if __name__ == "__main__":
    unittest.main()
