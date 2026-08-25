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
                    patch.object(run.user_store, "get_profile_identity", return_value={"username": "attacker"}), \
                    patch.object(run.player_marked_target_store, "upsert") as marked_upsert, \
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
            marked_upsert.assert_not_called()

    def test_lightweight_aim_is_blocked_on_enemy_territory(self):
        with patch.object(run.user_store, "get_profile_identity", return_value={"username": "attacker"}), \
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

    def test_scan_outside_then_mark_returned_target_inside_is_fail_closed(self):
        scan_center = (52.0000, 21.0000)
        target_point = (52.0010, 21.0010)
        aimed_before = {"target_id": "existing-target", "lat": 51.9, "lng": 20.9}
        profile = {
            "username": "attacker",
            "curently_possition": {"lat": scan_center[0], "lng": scan_center[1]},
            "aimed_target": dict(aimed_before),
        }

        def territory_gate(_username, lat, lng, **_kwargs):
            if round(float(lat), 4) == target_point[0] and round(float(lng), 4) == target_point[1]:
                return self.foreign_area()
            return None

        with self.client.session_transaction() as session_state:
            session_state["profile"] = dict(profile)

        with patch.object(run, "sync_session_profile", return_value=dict(profile)), \
                patch.object(run, "get_player_action_range", return_value=5000), \
                patch.object(run.fetcher, "get_all", return_value=[{
                    "lat": target_point[0], "lon": target_point[1],
                    "name": "Enemy object", "tags": {"amenity": "bench"},
                }]), \
                patch.object(run.player_marked_target_store, "list_targets", return_value=[]), \
                patch.object(run.player_marked_target_store, "upsert") as marked_upsert, \
                patch.object(run.user_store, "get_profile_identity", return_value={"username": "attacker"}), \
                patch.object(run, "record_map_target_delta") as target_delta, \
                patch.object(run, "foreign_territory_action_block", side_effect=territory_gate):
            scan = self.client.post("/map-action", headers=self.headers, json={
                "action": "scan", "lat": scan_center[0], "lng": scan_center[1],
            })
            self.assertEqual(scan.status_code, 200)
            scanned_target = scan.get_json()["markers"][0]
            mark = self.client.post("/map-action", headers=self.headers, json={
                "action": "mark_target",
                "lat": scanned_target["lat"], "lng": scanned_target["lon"],
                "label": scanned_target["name"], "icon": scanned_target["icon"],
                "source_type": scanned_target["source_type"],
            })

        self.assertEqual(mark.status_code, 403)
        self.assertEqual(mark.get_json()["reason"], "foreign_territory_protected")
        marked_upsert.assert_not_called()
        target_delta.assert_not_called()
        with self.client.session_transaction() as session_state:
            self.assertEqual(session_state["profile"]["aimed_target"], aimed_before)

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

    def test_foreign_area_gate_checks_geometry_before_loading_relations(self):
        far_area = {
            **self.foreign_area(),
            "vertices": [
                {"lat": 40.0, "lng": 10.0},
                {"lat": 40.0, "lng": 10.1},
                {"lat": 40.1, "lng": 10.1},
                {"lat": 40.1, "lng": 10.0},
            ],
        }
        with patch.object(run.territory_store, "list_player_areas", return_value=[far_area]), \
                patch.object(run, "territory_combat_relation", side_effect=AssertionError("relation loaded before geometry")):
            self.assertIsNone(run.find_foreign_area_for_point("attacker", 52.0, 21.0))

    def test_snapshot_mode_does_not_publish_parallel_legacy_markers(self):
        source = inspect.getsource(run.map_player_areas)
        guard = source.index("if not conflict_snapshot_mode:")
        legacy_targets = source.index("contested_targets_from_active_conflicts", guard)
        self.assertLess(guard, legacy_targets)

    def test_frontend_treats_expected_403_as_controlled_system_message(self):
        with open("templates/map_template.html", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("function isForeignTerritoryProtectedResponse", source)
        self.assertIn("function handleForeignTerritoryProtectedResponse", source)

        aim_start = source.index("async function aimMapTargetOnly")
        aim_end = source.index("function findClanVulnerabilityForTarget", aim_start)
        mark_start = source.index("async function mapAction")
        mark_end = source.index("const bikeDirectionIcons", mark_start)
        aim_path = source[aim_start:aim_end]
        mark_path = source[mark_start:mark_end]

        self.assertIn("fetch('/api/map/aim-target'", aim_path)
        self.assertIn("handleForeignTerritoryProtectedResponse(response, data)", aim_path)
        self.assertIn("fetch('/map-action'", mark_path)
        self.assertIn("action === 'mark_target'", mark_path)
        self.assertIn("handleForeignTerritoryProtectedResponse(res, data)", mark_path)
        self.assertIn("settlePendingMarkedTarget", mark_path)


if __name__ == "__main__":
    unittest.main()
