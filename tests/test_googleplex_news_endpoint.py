import unittest
from unittest.mock import Mock, patch

from flask import g, session

from database import get_hot_path_metrics, reset_hot_path_metrics, restore_hot_path_metrics
import run


class GoogleplexNewsEndpointTest(unittest.TestCase):
    def test_route_is_registered(self):
        rules = {rule.rule: rule.endpoint for rule in run.app.url_map.iter_rules()}
        self.assertEqual(rules.get("/api/googleplex/news"), "api_googleplex_news")

    def test_endpoint_is_bounded_and_has_zero_profile_metrics(self):
        heavy_profile_fixture = {"payload": "x" * (35 * 1024 * 1024)}
        self.assertGreaterEqual(len(heavy_profile_fixture["payload"]), 35 * 1024 * 1024)
        token = reset_hot_path_metrics()
        try:
            with run.app.test_request_context("/api/googleplex/news?view=home&limit=20"):
                session["user"] = "main"
                g.session_generation = "generation-a"
                with patch.object(run, "get_app_catalog", return_value=[{
                    "id": "tool_alpha",
                    "name": "Alpha Tool",
                    "published": True,
                    "downloads": 1,
                }]), patch.object(
                    run.user_store,
                    "get_profile",
                    side_effect=AssertionError("35 MB full profile read"),
                ) as profile_read, patch.object(
                    run.user_store,
                    "list_profiles",
                    side_effect=AssertionError("profile scan"),
                ) as profile_scan:
                    response = run.api_googleplex_news()
                self.assertFalse(profile_read.called)
                self.assertFalse(profile_scan.called)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["view"], "home")
        self.assertLessEqual(len(payload["entries"]), 24)
        self.assertEqual(metrics["profile_full_read"], 0)
        self.assertEqual(metrics["profile_full_write"], 0)
        self.assertEqual(metrics["profile_bytes"], 0)

    def test_unknown_view_is_fail_closed(self):
        with run.app.test_request_context("/api/googleplex/news?view=raw-inbox"):
            session["user"] = "main"
            response, status = run.api_googleplex_news()
        self.assertEqual(status, 400)
        self.assertEqual(response.get_json()["error"], "unsupported_news_view")

    def test_endpoint_reads_every_refreshable_publication_slot(self):
        repository = Mock()
        repository.list_active_narrative_slot_records_for_viewer.return_value = []
        service = Mock(repository=repository)
        expected_limit = sum(
            1 for contract in run.GOOGLEPLEX_HOME_SLOT_REGISTRY.values()
            if isinstance(contract, dict)
            and contract.get("llm_refresh_enabled") is True
        )
        self.assertGreater(expected_limit, 6)
        with run.app.test_request_context("/api/googleplex/news?view=home&limit=20"):
            session["user"] = "main"
            g.session_generation = "generation-a"
            with patch.object(run, "get_app_catalog", return_value=[]), patch.object(
                run.identity_projection_store, "get_identity", return_value={}
            ), patch.object(run, "get_ghostnetwork_service", return_value=service):
                response = run.api_googleplex_news()

        self.assertEqual(response.status_code, 200)
        repository.list_active_narrative_slot_records_for_viewer.assert_called_once_with(
            "googleplex_news", owner="main", clan="", limit=expected_limit
        )

    def test_endpoint_requires_login(self):
        with run.app.test_request_context("/api/googleplex/news"):
            response, status = run.api_googleplex_news()
        self.assertEqual(status, 401)
        self.assertEqual(response.get_json()["error"], "not_logged_in")


if __name__ == "__main__":
    unittest.main()
