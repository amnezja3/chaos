import unittest
from pathlib import Path


class OperationFeedbackFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Path("config.py").read_text(encoding="utf-8")
        cls.template = Path("templates/linux.html").read_text(encoding="utf-8")
        cls.feedback = Path("static/js/operation_feedback.js").read_text(encoding="utf-8")
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")

    def function_source(self, start_marker, end_marker):
        start = self.terminal.index(start_marker)
        end = self.terminal.index(end_marker, start)
        return self.terminal[start:end]

    def test_feature_flags_are_disabled_by_default_and_reach_desktop(self):
        self.assertIn('env_bool("CHAOS_OPERATION_FEEDBACK_ENABLED", False)', self.config)
        self.assertIn('env_bool("CHAOS_OPERATION_FEEDBACK_SCAN_PORTS", False)', self.config)
        self.assertIn('id="operation-feedback-config"', self.template)
        self.assertLess(
            self.template.index("js/operation_feedback.js"),
            self.template.index("js/terminal.js"),
        )

    def test_scan_ports_is_the_only_enabled_action_in_spike(self):
        self.assertIn('action === "scan_ports"', self.feedback)
        self.assertIn('flags.scan_ports === true', self.feedback)
        self.assertIn('flags.enabled === true', self.feedback)

    def test_session_owns_lifecycle_timers_and_cleanup(self):
        for state in (
            "idle", "starting", "running", "awaiting_payload", "completing",
            "failed", "cancelled", "disposed",
        ):
            self.assertIn(state, self.feedback)
        self.assertIn("this.timers = new Set()", self.feedback)
        self.assertIn("this.clearTimers()", self.feedback)
        self.assertIn('options.appWindow._operationFeedbackSession.cancel("new_request")', self.feedback)
        self.assertIn('disposeWindowSession(appWindow, reason = "window_closed")', self.feedback)

    def test_security_projection_is_local_and_not_added_to_gonna_win_body(self):
        self.assertIn("sanitizeSecurityState", self.feedback)
        self.assertIn("Object.freeze(normalized)", self.feedback)
        self.assertIn("toolbarTargetMatchesCaptured(aimedTarget, expectedTarget)", self.terminal)

        notify = self.function_source("async function notifyGonnaWin", "function notifyOpenMapsTargetHacked")
        choice = self.function_source("async function sendGonnaWinRequest", "function app_terminal")
        self.assertNotIn("security_state:", notify)
        self.assertNotIn("security_state:", choice)

    def test_existing_request_paths_are_wrapped_not_duplicated(self):
        notify = self.function_source("async function notifyGonnaWin", "function notifyOpenMapsTargetHacked")
        choice = self.function_source("async function sendGonnaWinRequest", "function app_terminal")
        self.assertEqual(notify.count("fetch('/gonna-win'"), 1)
        self.assertEqual(choice.count("fetch('/gonna-win'"), 1)
        self.assertIn("beginOperationFeedbackRequest", notify)
        self.assertIn("beginOperationFeedbackRequest", choice)
        self.assertIn("feedback.complete(data)", notify)
        self.assertIn("feedback.complete(data)", choice)
        self.assertIn("feedback.fail", notify)
        self.assertIn("feedback.fail", choice)

    def test_progressbar_keeps_legacy_path_when_feedback_is_off(self):
        progress = self.function_source("async function app_progressbar_random", "async function notifyGonnaWin")
        self.assertIn("if (feedbackEnabled)", progress)
        self.assertIn("runNextStep();", progress)
        self.assertIn("OperationFeedbackSystem.isEnabled(feedbackContext.action_key)", progress)

    def test_launch_queue_preserves_map_action_for_feedback_profile(self):
        self.assertIn(
            "const action = String(rawItem.action || rawItem.map_action_id || rawItem.action_key || \"\").trim()",
            self.terminal,
        )
        self.assertIn("appData._map_action_id = item.action", self.terminal)


if __name__ == "__main__":
    unittest.main()
