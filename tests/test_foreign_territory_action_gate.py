import inspect
import unittest
from unittest.mock import patch

import run
from tests.session_generation_fixture import SessionGenerationFixture


class ForeignTerritoryActionGateTests(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_foreign_territory_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)
        self.client = run.app.test_client()
        self.headers = self.session_generation.authenticate(self.client, "attacker")

    @staticmethod
    def foreign_area():
        return {
            "id": "territory-enemy",
            "owner_username": "defender",
            "owner_nick": "Defender",
            "status": "active",
        }

    def test_scan_and_mark_are_blocked_before_mutation(self):
        profile = {
            "username": "attacker",
            "targets": [],
            "curently_possition": {"lat": 52.0, "lng": 21.0},
        }
        for action in ("scan", "mark_target"):
            with self.subTest(action=action), \
                    patch.object(run, "sync_session_profile", return_value=dict(profile)), \
                    patch.object(run, "foreign_territory_action_block", return_value=self.foreign_area()):
                response = self.client.post("/map-action", headers=self.headers, json={
                    "action": action,
                    "lat": 52.001,
                    "lng": 21.001,
                    "label": "Enemy object",
                    "icon": "X",
                })
            self.assertEqual(response.status_code, 403)
            self.assertTrue(response.get_json()["blocked"])
            self.assertEqual(response.get_json()["reason"], "foreign_territory_protected")

    def test_lightweight_aim_is_blocked_on_enemy_territory(self):
        with patch.object(run, "load_profile_readonly", return_value={"username": "attacker"}), \
                patch.object(run, "find_contested_target", return_value=None), \
                patch.object(run, "foreign_territory_action_block", return_value=self.foreign_area()):
            response = self.client.post("/api/map/aim-target", headers=self.headers, json={
                "lat": 52.001,
                "lng": 21.001,
                "label": "Enemy object",
                "target_mode": "standard",
            })
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.get_json()["blocked"])
        self.assertEqual(response.get_json()["error"], "foreign_territory_protected")

    def test_canonical_conflict_target_is_the_only_territory_exception(self):
        area = self.foreign_area()
        with patch.object(run, "find_foreign_area_for_point", return_value=area):
            self.assertEqual(
                run.foreign_territory_action_block("attacker", 52.0, 21.0),
                area,
            )
            self.assertIsNone(run.foreign_territory_action_block(
                "attacker", 52.0, 21.0,
                contested_target={"target_id": "conflict-pillar"},
            ))

        hack_source = inspect.getsource(run.hack_action)
        self.assertIn("foreign_area and not contested_target", hack_source)
        self.assertNotIn(
            "foreign_area and not vulnerability_report and not contested_target",
            hack_source,
        )

    def test_enemy_clan_area_is_protected_but_same_clan_area_is_not_enemy(self):
        area = {
            **self.foreign_area(),
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        with patch.object(run.territory_store, "list_player_areas", return_value=[area]), \
                patch.object(run, "territory_combat_relation", return_value="hostile"), \
                patch.object(run, "_territory_relation_profile", return_value={"nick": "Defender", "clan": "red"}):
            protected = run.find_foreign_area_for_point("attacker", 52.005, 21.005)
        self.assertEqual(protected["owner_username"], "defender")

        with patch.object(run.territory_store, "list_player_areas", return_value=[area]), \
                patch.object(run, "territory_combat_relation", return_value="protected_same_clan"):
            self.assertIsNone(run.find_foreign_area_for_point("attacker", 52.005, 21.005))

    def test_snapshot_mode_does_not_publish_parallel_legacy_markers(self):
        source = inspect.getsource(run.map_player_areas)
        guard = source.index("if not conflict_snapshot_mode:")
        legacy_targets = source.index("contested_targets_from_active_conflicts", guard)
        self.assertLess(guard, legacy_targets)


if __name__ == "__main__":
    unittest.main()
