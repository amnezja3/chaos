import unittest
from unittest.mock import patch

import run


class FirstRespawnTerritoryEdgeTest(unittest.TestCase):
    @staticmethod
    def area(area_id, owner, center_lat=52.2, center_lng=21.0, half_span=0.01, status="active"):
        return {
            "id": area_id,
            "owner_username": owner,
            "status": status,
            "vertices": [
                {"lat": center_lat - half_span, "lng": center_lng - half_span},
                {"lat": center_lat - half_span, "lng": center_lng + half_span},
                {"lat": center_lat + half_span, "lng": center_lng + half_span},
                {"lat": center_lat + half_span, "lng": center_lng - half_span},
            ],
        }

    def test_free_ip_position_is_not_moved(self):
        origin = {"lat": 52.2, "lng": 21.0}

        result = run.resolve_first_respawn_outside_controlled_territory(
            origin,
            areas=[self.area(1, "owner", center_lat=53.0, center_lng=22.0)],
        )

        self.assertFalse(result["adjusted"])
        self.assertEqual(origin, result["position"])
        self.assertEqual("free_origin", result["reason"])

    def test_spawn_inside_territory_moves_beyond_boundary_margin(self):
        area = self.area(1, "owner")

        result = run.resolve_first_respawn_outside_controlled_territory(
            {"lat": 52.2, "lng": 21.0}, areas=[area], margin_m=180,
        )

        self.assertTrue(result["adjusted"])
        self.assertEqual("controlled_territory_edge", result["reason"])
        self.assertEqual(["1"], result["territory_ids"])
        self.assertEqual(["owner"], result["owner_usernames"])
        self.assertFalse(run.territory_point_in_polygon_or_boundary(
            result["position"], area["vertices"],
        ))
        self.assertGreater(result["distance_m"], 800)

    def test_nested_territories_resolve_outside_entire_controlled_union(self):
        inner = self.area(1, "inner_owner", half_span=0.005)
        outer = self.area(2, "outer_owner", half_span=0.02)

        result = run.resolve_first_respawn_outside_controlled_territory(
            {"lat": 52.2, "lng": 21.0}, areas=[inner, outer], margin_m=180,
        )

        self.assertTrue(result["adjusted"])
        self.assertEqual({"1", "2"}, set(result["territory_ids"]))
        for area in (inner, outer):
            self.assertFalse(run.territory_point_in_polygon_or_boundary(
                result["position"], area["vertices"],
            ))

    def test_inactive_territory_does_not_move_spawn(self):
        result = run.resolve_first_respawn_outside_controlled_territory(
            {"lat": 52.2, "lng": 21.0},
            areas=[self.area(1, "owner", status="blocked")],
        )

        self.assertFalse(result["adjusted"])

    def test_registration_persists_resolved_edge_without_movement_pipeline(self):
        area = self.area(1, "owner")
        client = run.app.test_client()
        with patch.object(run.user_store, "username_exists", return_value=False), \
                patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run, "get_start_location_by_ip", return_value={
                    "city": "Warsaw", "lat": 52.2, "lng": 21.0, "source": "test",
                }), \
                patch.object(run.territory_store, "list_player_areas", return_value=[area]), \
                patch.object(run, "UserProfileManager") as manager_cls, \
                patch.object(run, "begin_authenticated_session", return_value="generation"), \
                patch.object(run, "_session_generation_query_token", return_value="token"):
            manager_cls.return_value.add_new_user.return_value = True
            response = client.post("/api/register-finalize", json={
                "username": "edge_player",
                "password": "secret123",
                "faction": "3",
                "role": "1",
                "nick": "Edge Player",
                "email": "edge@example.test",
            })

        self.assertEqual(200, response.status_code)
        profile_update = manager_cls.return_value.update_profile.call_args.args[0]
        position = profile_update["curently_possition"]
        self.assertFalse(run.territory_point_in_polygon_or_boundary(position, area["vertices"]))
        # Registration writes the resolved point directly. It never invokes
        # teleport/travel, target, operation or incident pipelines.
        self.assertNotEqual({"lat": 52.2, "lng": 21.0}, position)


if __name__ == "__main__":
    unittest.main()
