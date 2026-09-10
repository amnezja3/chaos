import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import run
from database import db_connect
from ghostnetwork import GhostNetworkRepository, GhostSignalShowService
from ghostnetwork.show import GhostGameplayLocked


class GhostSignalShowHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = GhostNetworkRepository(os.path.join(self.tmp.name, "show.sqlite3"))
        self.cycle = self.repo.create_cycle(cycle_id="cycle", signal_number=1,
            ghostsystem_version=1, status="active")
        self.show = GhostSignalShowService(self.repo)
        self.patcher = patch.object(run, "get_ghostsignal_show_service", return_value=self.show)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def guard(self, path, method="GET", body=None):
        with run.app.test_request_context(path, method=method, json=body):
            run.session["user"] = "fixture-player"
            return run.block_gameplay_writes_during_ghostsignal_show()

    def test_all_registered_nonexempt_routes_locked_in_both_states(self):
        checked = 0
        for state in ("transmitting", "stabilizing"):
            self.repo.update_cycle("cycle", status=state)
            for rule in run.app.url_map.iter_rules():
                for method in rule.methods - {"OPTIONS"}:
                    with self.subTest(state=state, path=rule.rule, method=method):
                        with run.app.test_request_context(rule.rule, method=method):
                            run.session["user"] = "fixture-player"
                            if run.ghostsignal_request_is_exempt():
                                continue
                            response = run.block_gameplay_writes_during_ghostsignal_show()
                            expected = 302 if rule.rule == "/map" and method in {"GET", "HEAD"} else 423
                            self.assertEqual(response.status_code, expected)
                            if expected == 423:
                                self.assertEqual(response.get_json()["cycle_id"], "cycle")
                            checked += 1
        self.assertGreater(checked, 100)

    def test_recovery_boot_logout_and_delta_remain_available(self):
        self.repo.update_cycle("cycle", status="transmitting")
        for path in ("/", "/desktop", "/logout", "/session/recover",
                     "/api/ghostnetwork/show", "/api/state/changes", "/static/js/ghost_signal_show.js"):
            with self.subTest(path=path):
                self.assertIsNone(self.guard(path))
        self.assertIsNone(self.guard("/command", "POST", {"input": "logout"}))
        self.assertEqual(self.guard("/command", "POST", {"input": "scan"}).status_code, 423)

    def test_active_cycle_allows_write_and_read_failure_fails_closed(self):
        self.assertIsNone(self.guard("/hack-action", "POST", {}))
        with patch.object(self.show, "gameplay_lock", side_effect=RuntimeError("unavailable")):
            response, status = self.guard("/hack-action", "POST", {})
            self.assertEqual(status, 503)
            self.assertEqual(response.get_json()["error"], "ghostnetwork_lock_unavailable")

    def test_show_endpoint_is_lightweight_and_uncached(self):
        with run.app.test_request_context("/api/ghostnetwork/show"):
            run.session["user"] = "fixture-player"
            with patch.object(run, "GhostNetworkService", side_effect=AssertionError("heavy facade")):
                response = run.api_ghostnetwork_show()
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertFalse(response.get_json()["show_active"])
        self.assertNotIn("signal_id", response.get_json())

    def test_request_started_before_t0_rolls_back_and_preserves_423(self):
        with db_connect(self.repo.db_path) as conn:
            conn.execute("CREATE TABLE gameplay_fixture (value TEXT)")
        with run.app.test_request_context("/hack-action", method="POST", json={}):
            run.session["user"] = "fixture-player"
            generation_guard = Mock()
            with patch.object(run, "current_request_profile_precommit_guard", return_value=Mock()), \
                 patch.object(run.session_generation_store, "build_transaction_precommit_guard", return_value=generation_guard):
                self.assertIsNone(run.block_gameplay_writes_during_ghostsignal_show())
                self.repo.update_cycle("cycle", status="transmitting")
                run.bind_request_profile_precommit_guard()
                with self.assertRaises(GhostGameplayLocked):
                    with db_connect(self.repo.db_path) as conn:
                        conn.execute("INSERT INTO gameplay_fixture VALUES ('late')")
                response = run.preserve_ghostsignal_commit_rejection(run.jsonify(ok=True))
                self.assertEqual(response.status_code, 423)
                generation_guard.assert_called_once()
        with db_connect(self.repo.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM gameplay_fixture").fetchone()[0], 0)

    def test_transaction_creating_t0_does_not_reject_its_own_lock(self):
        from database import set_request_transaction_precommit_guard, reset_request_transaction_precommit_guard
        token = set_request_transaction_precommit_guard(lambda conn: self.show.assert_gameplay_unlocked(conn))
        try:
            self.repo.update_cycle("cycle", status="transmitting")
        finally:
            reset_request_transaction_precommit_guard(token)
        self.assertTrue(self.show.gameplay_lock()["gameplay_locked"])


if __name__ == "__main__":
    unittest.main()
