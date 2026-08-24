import unittest
import inspect
from unittest.mock import Mock, patch

import run
from config import PERF_LOG_ENDPOINTS
from tests.session_generation_fixture import SessionGenerationFixture


class GhostNetworkReadPathSafetyTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_ghostnetwork_read_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def _client(self):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, "alice")
        return client, headers

    def test_default_profile_sync_does_not_rebuild_or_bridge(self):
        profile = {"username": "alice", "apps": [], "files": []}
        with run.app.test_request_context("/api/profile"):
            run.session["user"] = "alice"
            with patch.object(run.user_store, "get_profile", return_value=profile), \
                    patch.object(run, "rebuild_player_areas_with_territory_delta") as rebuild, \
                    patch.object(run, "bridge_ghostnetwork_territory_publication") as bridge:
                result = run.sync_session_profile(
                    persist_normalization=False,
                    cache_in_session=False,
                )
        self.assertEqual(result["username"], "alice")
        rebuild.assert_not_called()
        bridge.assert_not_called()

    def test_ghostnetwork_snapshot_is_read_only(self):
        service = Mock()
        service.get_snapshot_for_viewer.return_value = {
            "cycle": {"cycle_id": "ghostnetwork_0001", "state_version": 1},
            "parts": [],
            "connections": [],
            "state_version": 1,
        }
        with run.app.test_request_context("/api/ghostnetwork/snapshot?view=map"):
            run.session["user"] = "alice"
            with patch.object(run.identity_projection_store, "get_identity", return_value={"username": "alice"}) as identity, \
                    patch.object(run, "load_profile_readonly", side_effect=AssertionError("full profile read not expected")), \
                    patch.object(run, "GhostNetworkService", return_value=service), \
                    patch.object(run, "bridge_ghostnetwork_territory_publication") as bridge:
                response = run.api_ghostnetwork_snapshot()
        self.assertEqual(response.status_code, 200)
        identity.assert_called_once_with("alice")
        service.get_snapshot_for_viewer.assert_called_once()
        bridge.assert_not_called()

    def test_critical_map_endpoints_are_in_perf_logging_scope(self):
        self.assertTrue({
            "/map",
            "/api/map/player-areas",
            "/api/map/player-actors",
            "/api/operations",
            "/api/state/changes",
            "/api/ghostnetwork/snapshot",
            "/api/ghost-control/territory",
            "/api/ghost-control/territory/security",
            "/api/ghost-control/territory/security-preset",
            "/api/ghost-control/territory/abandon",
            "/api/blacknet/cta/teleport",
        }.issubset(PERF_LOG_ENDPOINTS))

    def test_sprint_130_12_endpoints_have_no_full_profile_helpers(self):
        forbidden = (
            "load_profile_readonly",
            "get_profile(",
            "get_profile_with_revision",
            "sync_session_profile",
            "UserProfileManager",
            "list_profile_identities",
            "list_profiles",
        )
        functions = (
            run.build_territory_control_snapshot,
            run.territory_control_clusters,
            run.territory_control_cluster_detail,
            run.territory_control_security_toggle,
            run.territory_control_security_preset,
            run.territory_control_abandon,
            run.api_blacknet_cta_teleport,
            run.api_ghostnetwork_snapshot,
        )
        for function in functions:
            source = inspect.getsource(function)
            for token in forbidden:
                self.assertNotIn(token, source, f"{function.__name__}: {token}")

    def test_target_snapshot_excludes_heavy_profile_fields(self):
        profile = {
            "username": "alice",
            "targets": [{
                "lat": 52.1, "lng": 21.1, "label": "Node", "icon": "N",
                "huge_private_runtime": "x" * 10000,
            }],
        }
        client, headers = self._client()
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run.player_marked_target_store, "list_targets", return_value=profile["targets"]), \
                patch.object(run.territory_store, "list_captured_targets", return_value=[]):
            response = client.get("/api/map/target-snapshot", headers=headers)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["targets"]), 1)
        self.assertNotIn("huge_private_runtime", payload["targets"][0])

    def test_map_document_size_does_not_scale_with_target_collection(self):
        base = {
            "username": "alice", "nick": "Alice", "apps": [], "files": {},
            "curently_possition": {"lat": 52.2, "lng": 21.0},
            "aimed_target": {}, "targets": [], "hacked": [],
        }
        heavy = {
            **base,
            "targets": [
                {
                    "lat": 52.0 + index / 10000,
                    "lng": 21.0 + index / 10000,
                    "label": f"Target {index}",
                    "private_runtime": "x" * 5000,
                }
                for index in range(500)
            ],
        }
        client, headers = self._client()
        map_url = self.session_generation.document_url("/map", headers)
        with patch.object(run, "sync_session_profile", side_effect=[base, heavy]):
            small_response = client.get(map_url, headers=headers)
            heavy_response = client.get(map_url, headers=headers)
        self.assertEqual(small_response.status_code, 200)
        self.assertEqual(heavy_response.status_code, 200)
        self.assertLess(
            abs(len(heavy_response.get_data()) - len(small_response.get_data())),
            10000,
        )


if __name__ == "__main__":
    unittest.main()
