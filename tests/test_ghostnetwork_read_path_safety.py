import unittest
from unittest.mock import Mock, patch

import run
from config import PERF_LOG_ENDPOINTS


class GhostNetworkReadPathSafetyTest(unittest.TestCase):
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
            with patch.object(run, "load_profile_readonly", return_value={"username": "alice"}), \
                    patch.object(run, "GhostNetworkService", return_value=service), \
                    patch.object(run, "bridge_ghostnetwork_territory_publication") as bridge:
                response = run.api_ghostnetwork_snapshot()
        self.assertEqual(response.status_code, 200)
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
        }.issubset(PERF_LOG_ENDPOINTS))


if __name__ == "__main__":
    unittest.main()
