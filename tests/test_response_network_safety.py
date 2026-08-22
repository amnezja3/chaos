import json
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from response_network.foundation import (
    RESPONSE_MAP_ENDPOINTS,
    ResponseNetworkAuditLog,
    ResponseNetworkClock,
    ResponseNetworkSafetyConfig,
    build_response_network_safety_snapshot,
)
from tests.session_generation_fixture import SessionGenerationFixture


class ResponseNetworkSafetyFoundationTest(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_response_safety_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)

    def _client_with_user(self, username="admin"):
        client = run.app.test_client()
        headers = self.session_generation.authenticate(client, username)
        return client, headers

    def test_default_config_is_disabled_and_kill_switches_are_closed(self):
        config = ResponseNetworkSafetyConfig.from_runtime()

        self.assertEqual(config.mode, "disabled")
        self.assertFalse(config.active)
        self.assertFalse(config.safe_to_publish)
        self.assertFalse(config.flags["response_incidents_enabled"])
        self.assertTrue(config.kill_switches["new_incidents"])
        self.assertTrue(config.kill_switches["consequences"])

    def test_clock_can_be_fixed_for_scenarios(self):
        clock = ResponseNetworkClock("2026-07-14T12:00:00Z")

        self.assertEqual(clock.iso_now(), "2026-07-14T12:00:00+00:00")

    def test_audit_log_records_map_endpoint_measurements_without_runtime_side_effects(self):
        log = ResponseNetworkAuditLog(limit=4, clock=ResponseNetworkClock("2026-07-14T12:00:00Z"))

        event = log.record_map_endpoint("/api/map/player-areas", 3250, status_code=200, payload_size=59048)
        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "response.map_endpoint_measured")

        ignored = log.record_map_endpoint("/api/profile", 100, status_code=200, payload_size=1000)
        self.assertIsNone(ignored)

        metrics = log.map_metrics()
        self.assertEqual(metrics["map.player_areas"]["count"], 1)
        self.assertEqual(metrics["map.player_areas"]["avg_ms"], 3250)
        self.assertEqual(metrics["map.player_areas"]["last_payload_size"], 59048)

    def test_safety_snapshot_does_not_enable_incidents_or_npc(self):
        snapshot = build_response_network_safety_snapshot()

        self.assertTrue(snapshot["success"])
        self.assertFalse(snapshot["runtime_active"])
        self.assertFalse(snapshot["incidents_enabled"])
        self.assertFalse(snapshot["npc_enabled"])
        self.assertFalse(snapshot["detection_enabled"])
        self.assertFalse(snapshot["consequences_enabled"])
        self.assertIn("/api/map/player-areas", snapshot["observed_map_endpoints"])

    def test_dev_endpoint_requires_admin_and_does_not_sync_profile(self):
        non_admin, non_admin_headers = self._client_with_user("alice")
        self.assertEqual(
            non_admin.get(
                "/api/dev/response-network-safety",
                headers=non_admin_headers,
            ).status_code,
            403,
        )

        admin, admin_headers = self._client_with_user("admin")
        with patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
            response = admin.get(
                "/api/dev/response-network-safety",
                headers=admin_headers,
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(data["runtime_active"])

    def test_fixture_contract_starts_disabled(self):
        fixture_path = Path("tests/fixtures/response_network/sprint85_safety_foundation.json")
        data = json.loads(fixture_path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["deployment_mode"], "disabled")
        self.assertFalse(data["feature_flags"]["response_network_enabled"])
        self.assertTrue(data["kill_switches"]["new_incidents"])
        self.assertEqual(set(data["map_endpoint_baseline"]), set(RESPONSE_MAP_ENDPOINTS.keys()))


if __name__ == "__main__":
    unittest.main()
