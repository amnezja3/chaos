import unittest
from unittest.mock import patch

import run


def projection(part, cycle_status="active"):
    return {"snapshot": {"cycle": {"status": cycle_status}, "parts": [part]}}


class GhostNetworkSuiteNavigationTests(unittest.TestCase):
    def _resolve(self, part, payload, cycle_status="active"):
        service = type("Service", (), {
            "get_snapshot_for_viewer": lambda _self, _viewer: projection(part, cycle_status)
        })()
        with patch.object(run.identity_projection_store, "get_identity", return_value={"username": "alice"}), \
                patch.object(run, "get_ghostnetwork_service", return_value=service), \
                patch.object(run, "ghostnetwork_player_payload", return_value={"viewer_id": "alice"}):
            return run.resolve_ghostnetwork_teleport_target("alice", payload)

    def test_exact_part_resolves_without_client_coordinates(self):
        resolved, error = self._resolve({
            "public_entity_id": "ghost-node:one", "status": "active",
            "location_visibility": "exact", "latitude": 52.2, "longitude": 21.1,
            "territory_id": "territory:one", "display_label": "Visible",
        }, {
            "target_type": "ghostnetwork_part", "public_entity_id": "ghost-node:one",
        })
        self.assertEqual(error, "")
        self.assertEqual(resolved["position"], run.ghostnetwork_teleport_vicinity_position(
            52.2, 21.1, "alice", "ghost-node:one"
        ))
        self.assertNotEqual(resolved["position"], {"lat": 52.2, "lng": 21.1})
        self.assertEqual(resolved["target"]["location_precision"], "vicinity")
        self.assertNotIn("part_id", resolved["target"])

    def test_changed_visibility_fails_closed(self):
        resolved, error = self._resolve({
            "public_entity_id": "ghost-node:one", "status": "contained",
            "location_visibility": "territory_only", "latitude": None, "longitude": None,
            "territory_id": "territory:one",
        }, {
            "target_type": "ghostnetwork_part", "public_entity_id": "ghost-node:one",
        })
        self.assertIsNone(resolved)
        self.assertEqual(error, "ghostnetwork_target_changed")

    def test_inactive_cycle_and_consumed_part_are_blocked(self):
        part = {
            "public_entity_id": "ghost-node:one", "status": "active",
            "location_visibility": "exact", "latitude": 52.2, "longitude": 21.1,
        }
        resolved, error = self._resolve(part, {
            "target_type": "ghostnetwork_part", "public_entity_id": "ghost-node:one",
        }, cycle_status="transmitting")
        self.assertIsNone(resolved)
        self.assertEqual(error, "ghostnetwork_cycle_not_active")

        part["status"] = "consumed"
        resolved, error = self._resolve(part, {
            "target_type": "ghostnetwork_part", "public_entity_id": "ghost-node:one",
        })
        self.assertIsNone(resolved)
        self.assertEqual(error, "ghostnetwork_target_inactive")

    def test_client_coordinates_are_rejected_first(self):
        resolved, error = run.resolve_ghostnetwork_teleport_target("alice", {
            "target_type": "ghostnetwork_part", "public_entity_id": "ghost-node:one",
            "lat": 1, "lng": 2,
        })
        self.assertIsNone(resolved)
        self.assertEqual(error, "client_coordinates_forbidden")

    def test_territory_control_uses_canonical_viewer_projection(self):
        part = {"part_id": "private", "territory_id": "territory:one"}
        service = type("Service", (), {
            "repository": type("Repository", (), {
                "list_parts": lambda _self, _cycle_id: [part]
            })(),
            "get_active_cycle": lambda _self: {"cycle_id": "cycle:one"},
        })()
        visibility = type("Visibility", (), {
            "project_territory_component_for_viewer": lambda _self, cluster, viewer: {
                "cluster_id": cluster["cluster_id"],
                "contains_ghost_part": bool(cluster["parts"]),
                "ghost_part_count": len(cluster["parts"]),
                "parts": [{"public_entity_id": "ghost-node:safe", "identity_visible": False}],
            }
        })()
        with patch.object(run, "get_ghostnetwork_service", return_value=service), \
                patch.object(run, "GhostVisibilityService", return_value=visibility), \
                patch.object(run, "ghostnetwork_player_payload", return_value={"viewer_id": "alice"}):
            result = run.territory_control_ghost_components(
                "alice", [{"id": "territory:one"}], {"username": "alice"}
            )
        self.assertTrue(result["territory:one"]["contains_ghost_part"])
        self.assertEqual(result["territory:one"]["parts"], [{
            "public_entity_id": "ghost-node:safe", "identity_visible": False,
        }])


if __name__ == "__main__":
    unittest.main()
