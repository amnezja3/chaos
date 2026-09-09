import unittest
from unittest.mock import Mock, patch

import run


class GhostSignalShowHttpTest(unittest.TestCase):
    def test_authenticated_gameplay_write_is_locked_by_backend(self):
        service = Mock()
        service.get_active_cycle.return_value = {
            "status": "stabilizing",
            "stabilization_until": "2026-09-09T10:15:00+00:00",
        }
        with run.app.test_request_context("/hack-action", method="POST", json={}):
            run.session["user"] = "fixture-player"
            with patch.object(run, "GhostNetworkService", return_value=service):
                response, status = run.block_gameplay_writes_during_ghostsignal_show()
        self.assertEqual(status, 423)
        self.assertEqual(response.get_json()["error"], "ghostsignal_show_active")

    def test_logout_command_remains_available(self):
        with run.app.test_request_context("/command", method="POST", json={"input": "logout"}):
            run.session["user"] = "fixture-player"
            self.assertIsNone(run.block_gameplay_writes_during_ghostsignal_show())

    def test_ordinary_active_cycle_does_not_block_write(self):
        service = Mock()
        service.get_active_cycle.return_value = {"status": "active"}
        with run.app.test_request_context("/hack-action", method="POST", json={}):
            run.session["user"] = "fixture-player"
            with patch.object(run, "GhostNetworkService", return_value=service):
                self.assertIsNone(run.block_gameplay_writes_during_ghostsignal_show())

    def test_show_endpoint_returns_only_viewer_projection(self):
        service = Mock()
        service.get_signal_show_for_viewer.return_value = {
            "show_active": True,
            "signal_public_id": "GHOSTSIGNAL-0001",
            "show_phase": {"code": "network_lock"},
        }
        with run.app.test_request_context("/api/ghostnetwork/show"):
            run.session["user"] = "fixture-player"
            with patch.object(run, "GhostNetworkService", return_value=service):
                response = run.api_ghostnetwork_show()
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["show_active"])
        self.assertNotIn("signal_id", payload)
        self.assertNotIn("show_id", payload)


if __name__ == "__main__":
    unittest.main()
