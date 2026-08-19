import unittest
from unittest.mock import patch

import run


class GhostNetworkRuntimeReadinessEndpointTest(unittest.TestCase):
    def test_endpoint_requires_dev_admin(self):
        with patch.object(run, "require_dev_admin", return_value=False):
            response = run.app.test_client().get("/api/dev/ghostnetwork/readiness")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "admin_required")

    def test_endpoint_returns_503_for_not_ready_without_mutation(self):
        class FakeService:
            def get_runtime_readiness(self):
                return {"ok": False, "ready": False, "status": "NOT READY", "errors": ["no_active_cycle"]}

        with patch.object(run, "require_dev_admin", return_value=True), patch.object(
            run, "GhostNetworkService", return_value=FakeService()
        ):
            response = run.app.test_client().get("/api/dev/ghostnetwork/readiness")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["errors"], ["no_active_cycle"])


if __name__ == "__main__":
    unittest.main()
