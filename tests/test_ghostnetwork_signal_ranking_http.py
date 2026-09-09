import unittest
from unittest.mock import Mock, patch

import run


class GhostSignalRankingHttpTest(unittest.TestCase):
    def test_list_endpoint_is_authenticated_and_viewer_safe(self):
        service = Mock()
        service.list_signal_rankings.return_value = [{
            "signal_id": "ghost_signal_1",
            "players": [{"user_id": "alice", "rsp_signal": 20}],
            "clans": [{"clan_id": "echo", "clan_ghost_score": 500}],
        }]
        with run.app.test_request_context("/api/ghostnetwork/rankings"):
            run.session["user"] = "fixture-player"
            with patch.object(run.identity_projection_store, "get_identity", return_value={"clan_code": "echo"}), \
                    patch.object(run, "get_ghostnetwork_service", return_value=service):
                response = run.api_ghostnetwork_rankings()
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["available"])
        self.assertEqual(payload["product_name"], "Signal Registry")
        self.assertNotIn("parts", payload["rankings"][0])

    def test_detail_does_not_accept_audience_escalation(self):
        service = Mock()
        service.get_signal_ranking.return_value = {
            "ok": True, "ranking": {"signal_id": "signal-1", "players": [], "clans": []}
        }
        with run.app.test_request_context("/api/ghostnetwork/rankings/signal-1?include_private=1"):
            run.session["user"] = "fixture-player"
            with patch.object(run.identity_projection_store, "get_identity", return_value={"clan_code": "echo"}), \
                    patch.object(run, "get_ghostnetwork_service", return_value=service):
                response, status = run.api_ghostnetwork_ranking_detail("signal-1")
        self.assertEqual(status, 200)
        self.assertTrue(response.get_json()["ok"])
        service.get_signal_ranking.assert_called_once_with("signal-1")

    def test_all_time_is_rebuilt_server_side(self):
        service = Mock()
        service.rebuild_signal_rankings_all_time.return_value = {
            "ok": True, "rebuilt_from_snapshots": 1, "players": [], "clans": []
        }
        with run.app.test_request_context("/api/ghostnetwork/rankings/all-time"):
            run.session["user"] = "fixture-player"
            with patch.object(run.identity_projection_store, "get_identity", return_value={"clan_code": "echo"}), \
                    patch.object(run, "get_ghostnetwork_service", return_value=service):
                response = run.api_ghostnetwork_rankings_all_time()
        self.assertEqual(response.get_json()["rebuilt_from_snapshots"], 1)


if __name__ == "__main__":
    unittest.main()
