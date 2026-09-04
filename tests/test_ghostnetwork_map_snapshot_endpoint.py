import unittest
from unittest.mock import patch

import run
from tests.session_generation_fixture import SessionGenerationFixture


class GhostNetworkMapSnapshotEndpointTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_ghostnetwork_snapshot_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def _client(self):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, "alice")
        return client, headers

    def test_snapshot_uses_lightweight_identity_and_viewer_projection(self):
        client, headers = self._client()

        profile = {
            "username": "alice",
            "ghost_clan_code": "VIREX",
            "ghost_profession": "signal_runner",
        }

        class FakeGhostNetworkService:
            viewer = None

            def get_snapshot_for_viewer(self, viewer=None):
                FakeGhostNetworkService.viewer = viewer
                return {
                    "projection": "viewer_visibility",
                    "visibility_version": "ghost-visibility-v1",
                    "state_version": 7,
                    "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 7},
                    "parts": [
                        {
                            "public_entity_id": "ghost-part-public-1",
                            "visibility_level": "full_owner",
                            "module_state": "active",
                            "can_show_on_map": True,
                            "location_visibility": "exact",
                            "latitude": 52.2,
                            "longitude": 21.0,
                            "display_label": "GhostNetwork",
                        }
                    ],
                    "connections": [],
                    "machines": [],
                    "progress": {},
                }

        with patch.object(run.identity_projection_store, "get_identity", return_value=profile) as identity, \
                patch.object(run, "load_profile_readonly", side_effect=AssertionError("full profile read not expected")), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("full sync not expected")), \
                patch.object(run, "GhostNetworkService", return_value=FakeGhostNetworkService()):
            response = client.get("/api/ghostnetwork/snapshot", headers=headers)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["scope"], "ghostnetwork")
        self.assertEqual(data["view"], "map")
        self.assertEqual(data["current_version"], 7)
        self.assertTrue(data["snapshot_checksum"])
        self.assertEqual(data["parts"][0]["public_entity_id"], "ghost-part-public-1")
        identity.assert_called_once_with("alice")
        self.assertEqual(FakeGhostNetworkService.viewer["viewer_id"], "alice")
        self.assertEqual(FakeGhostNetworkService.viewer["viewer_clan"], "VIREX")
        self.assertEqual(FakeGhostNetworkService.viewer["audience_scope"], "player")

    def test_signal_archive_list_uses_lightweight_identity_projection(self):
        client, headers = self._client()
        service = type("Service", (), {
            "list_signal_archive": lambda _self, limit=50: [{
                "signal_id": "signal-public", "signal_number": 1,
            }]
        })()
        with patch.object(
            run.identity_projection_store, "get_identity",
            return_value={"username": "alice", "ghost_clan_code": "VIREX"},
        ) as identity, patch.object(
            run, "load_profile_readonly",
            side_effect=AssertionError("full profile read not expected"),
        ), patch.object(run, "GhostNetworkService", return_value=service):
            response = client.get(
                "/api/ghostnetwork/archive/signals", headers=headers
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["signals"][0]["signal_id"], "signal-public")
        identity.assert_called_once_with("alice")

    def test_signal_archive_detail_cannot_elevate_private_projection(self):
        client, headers = self._client()

        class Service:
            include_private = None

            def get_signal_archive_detail(self, signal_id, include_private=False):
                Service.include_private = include_private
                return {"ok": True, "signal": {"signal_id": signal_id}}

        with patch.object(
            run.identity_projection_store, "get_identity",
            return_value={"username": "alice", "ghost_clan_code": "VIREX"},
        ), patch.object(run, "GhostNetworkService", return_value=Service()):
            response = client.get(
                "/api/ghostnetwork/archive/signals/signal-public?private=1",
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Service.include_private)
        self.assertNotIn("private", response.get_json())

    def test_suite_view_omits_connection_geometry(self):
        client, headers = self._client()

        profile = {"username": "alice", "ghost_clan_code": "VIREX"}

        class FakeGhostNetworkService:
            def get_snapshot_for_viewer(self, viewer=None):
                return {
                    "projection": "viewer_visibility",
                    "visibility_version": "ghost-visibility-v1",
                    "state_version": 9,
                    "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 9},
                    "parts": [],
                    "connections": [
                        {
                            "public_connection_id": "conn-public-1",
                            "state": "active",
                            "state_version": 9,
                            "viewer_relation": "owner",
                            "can_show_on_map": True,
                            "endpoint_a": {"latitude": 52.2, "longitude": 21.0},
                            "endpoint_b": {"latitude": 52.3, "longitude": 21.1},
                        }
                    ],
                    "machines": [],
                    "progress": {},
                }

        with patch.object(run.identity_projection_store, "get_identity", return_value=profile), \
                patch.object(run, "load_profile_readonly", side_effect=AssertionError("full profile read not expected")), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("full sync not expected")), \
                patch.object(run, "GhostNetworkService", return_value=FakeGhostNetworkService()):
            response = client.get(
                "/api/ghostnetwork/snapshot?view=suite",
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["view"], "suite")
        self.assertEqual(data["current_version"], 9)
        self.assertTrue(data["snapshot_checksum"])
        self.assertEqual(data["connections"][0]["public_connection_id"], "conn-public-1")
        self.assertNotIn("endpoint_a", data["connections"][0])
        self.assertNotIn("endpoint_b", data["connections"][0])


if __name__ == "__main__":
    unittest.main()
