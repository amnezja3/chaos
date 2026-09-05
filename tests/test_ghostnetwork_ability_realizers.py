import os
import tempfile
import unittest
import inspect
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    ALLOWED_REALIZER_FAMILIES,
    DEFERRED_REALIZER_FAMILIES,
    GhostAbilityPilotHarness,
)


def fixture_for(family, now):
    common_target = {
        "target": {
            "target_id": "map:52.2:21.0:PILOT",
            "actions_allowed": {"scan_ports": False, "exploit": False, "sniff": False, "trace": False},
            "security": {"firewall": True, "ids": True, "encryption": False, "vpn": False},
            "security_version": 3,
        }
    }
    fixtures = {
        "operation_speed": {
            "operations": [
                {"operation_id": "op-1", "status": "running", "expires_at": (now + timedelta(minutes=10)).isoformat()},
                {"operation_id": "op-2", "status": "active", "expires_at": (now + timedelta(minutes=20)).isoformat()},
            ],
        },
        "file_yield": {"operation_id": "op-ready", "files": []},
        "data_quality": {
            "files": [
                {"file_id": "camera-1", "file_category": "camera", "quality_score": 90, "completeness_percent": 70},
                {"file_id": "audio-1", "file_category": "audio", "quality_score": 40, "completeness_percent": 40},
                {"file_id": "other-1", "file_category": "document", "quality_score": 10, "completeness_percent": 10},
            ],
        },
        "hack_actions": common_target,
        "target_security": common_target,
        "operation_risk": {"operation": {"operation_id": "risk-1", "heat": 61}},
        "scan_range": {"capability": {"action_range": 500}},
        "map_zoom": {"capability": {"map_zoom": 18}},
        "territory_defense": {
            **common_target,
            "owner_checked": True,
            "cas_checked": True,
        },
    }
    return fixtures[family]


class GhostAbilityRealizerCertificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(item for item in self.repo.list_parts(cycle["cycle_id"]) if item["part_code"] == "V1")
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-v1",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v1", territory_owner_id="alice",
            territory_clan="virex",
        )
        self.player = {
            "username": "alice", "player_id": "alice", "clan": "virex",
            "profession": "broker", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_nine_realizers_use_the_same_durable_v1_activation_path(self):
        for family in ALLOWED_REALIZER_FAMILIES:
            with self.subTest(family=family):
                fixture = fixture_for(family, self.now)
                harness = GhostAbilityPilotHarness(family, fixture)
                service = GhostNetworkService(repository=self.repo, ability_pilot_harness=harness)
                result = service.activate_player_ability(
                    self.player, f"certify-{family}", now=self.now,
                )
                self.assertTrue(result["ok"])
                self.assertEqual("activated", result["status"])
                self.assertEqual(family, result["pilot_evidence"]["family"])
                self.assertEqual("fixture_certification", result["pilot_evidence"]["mode"])
                self.assertEqual(1, harness.calls)

                replay = service.activate_player_ability(
                    self.player, f"certify-{family}", now=self.now,
                )
                self.assertEqual("replayed", replay["status"])
                self.assertNotIn("pilot_evidence", replay)
                self.assertEqual(1, harness.calls)

                self.now += timedelta(hours=1, seconds=1)

    def test_family_specific_bounded_evidence(self):
        results = {}
        for family in ALLOWED_REALIZER_FAMILIES:
            harness = GhostAbilityPilotHarness(family, fixture_for(family, self.now))
            service = GhostNetworkService(repository=self.repo, ability_pilot_harness=harness)
            result = service.activate_player_ability(self.player, family, now=self.now)
            results[family] = result["pilot_evidence"]
            self.now += timedelta(hours=1, seconds=1)

        self.assertEqual(2, len(results["operation_speed"]["evidence"]["changed"]))
        self.assertEqual(2, len(results["file_yield"]["evidence"]["changed"]))
        quality_files = results["data_quality"]["after"]["files"]
        self.assertEqual(100, quality_files[0]["quality_score"])
        self.assertEqual(10, quality_files[2]["quality_score"])
        self.assertTrue(results["hack_actions"]["evidence"]["security_unchanged"])
        self.assertLessEqual(len(results["target_security"]["evidence"]["changed"]), 2)
        self.assertEqual(46, results["operation_risk"]["evidence"]["effective_heat"])
        self.assertNotIn("risk_level", results["operation_risk"]["after"]["operation"])
        self.assertGreater(results["scan_range"]["evidence"]["effective"], 500)
        self.assertEqual(20, results["map_zoom"]["evidence"]["effective"])
        self.assertTrue(results["territory_defense"]["evidence"]["owner_checked"])
        self.assertTrue(results["territory_defense"]["evidence"]["cas_checked"])

    def test_deferred_and_unknown_families_fail_closed(self):
        for family in (*DEFERRED_REALIZER_FAMILIES, "unknown"):
            with self.subTest(family=family):
                with self.assertRaisesRegex(ValueError, "not_allowed"):
                    GhostAbilityPilotHarness(family, {})

    def test_production_service_has_no_pilot_realizer_or_evidence(self):
        service = GhostNetworkService(repository=self.repo)
        result = service.activate_player_ability(self.player, "production-default", now=self.now)
        self.assertTrue(result["ok"])
        self.assertNotIn("pilot_evidence", result)
        self.assertIsNone(service.ability_pilot_harness)

    def test_limits_are_enforced_before_fixture_mutation(self):
        window = {
            "window_id": "window-bounds",
            "ability_code": "insider_feed",
            "activated_at": self.now.isoformat(),
            "level_snapshot": 110,
        }
        operations = [
            {
                "operation_id": f"op-{index}",
                "status": "running",
                "expires_at": (self.now + timedelta(minutes=10)).isoformat(),
            }
            for index in range(12)
        ]
        speed = GhostAbilityPilotHarness("operation_speed", {"operations": operations})
        speed_result = speed.apply(window)
        self.assertEqual(8, len(speed_result["evidence"]["changed"]))
        self.assertNotIn("ability_application_keys", operations[8])

        files = [
            {
                "file_id": f"camera-{index}", "file_category": "camera",
                "quality_score": 10, "completeness_percent": 10,
            }
            for index in range(20)
        ]
        quality = GhostAbilityPilotHarness("data_quality", {"files": files})
        quality_result = quality.apply(window)
        self.assertEqual(16, len(quality_result["evidence"]["changed"]))
        self.assertEqual(10, files[16]["quality_score"])

    def test_harness_has_no_heavy_profile_or_deferred_runtime_dependency(self):
        source = inspect.getsource(__import__(
            "ghostnetwork.ability_realizers", fromlist=["GhostAbilityPilotHarness"]
        ))
        for forbidden in (
            "get_profile(", "list_profiles(", "profile_json", "IncidentStore",
            "NPCCapsuleStore", "ghost_exchange", "actor_visibility",
        ):
            if forbidden == "actor_visibility":
                # The name is allowed only in the explicit fail-closed catalog.
                self.assertEqual(1, source.count(forbidden))
            else:
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
