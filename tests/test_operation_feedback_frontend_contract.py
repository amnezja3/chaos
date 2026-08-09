import json
import subprocess
import unittest
from pathlib import Path


class OperationFeedbackFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Path("config.py").read_text(encoding="utf-8")
        cls.template = Path("templates/linux.html").read_text(encoding="utf-8")
        cls.feedback = Path("static/js/operation_feedback.js").read_text(encoding="utf-8")
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        cls.profile = json.loads(
            Path("static/data/operation_feedback.v1.json").read_text(encoding="utf-8")
        )

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

    def test_scan_ports_profile_has_required_mvp_libraries(self):
        required = {
            "defaults", "duration_profiles", "scene_library", "security_library",
            "transport_library", "choice_library", "completion_library",
            "failure_library", "operations",
        }
        self.assertTrue(required.issubset(self.profile))
        self.assertEqual(self.profile["schema_version"], "1.0.0")
        operation = self.profile["operations"]["scan_ports"]
        self.assertEqual(operation["action_key"], "scan_ports")
        self.assertNotIn("security_keys", operation)
        self.assertNotIn("interaction_types", operation)
        self.assertGreaterEqual(len(operation["scene_pools"]), 2)
        self.assertGreaterEqual(len(operation["security"]), 3)

    def test_security_matrix_only_references_existing_variants(self):
        operation = self.profile["operations"]["scan_ports"]
        library = self.profile["security_library"]
        for security_key, interactions in operation["security"].items():
            self.assertIn(security_key, library)
            for interaction in interactions:
                variants = library[security_key]["interactions"].get(interaction)
                self.assertIsInstance(variants, list)
                self.assertTrue(variants)

    def test_duration_profiles_reference_allowed_scenes_monotonically(self):
        operation = self.profile["operations"]["scan_ports"]
        allowed = set(operation["scene_pools"])
        thresholds = []
        for duration in self.profile["duration_profiles"].values():
            thresholds.append(duration["min_elapsed_ms"])
            self.assertTrue(set(duration["scene_pool"]).issubset(allowed))
        self.assertEqual(thresholds, sorted(thresholds))
        self.assertEqual(set(self.profile["duration_profiles"]), {
            "instant", "short", "medium", "long", "very_long",
        })

    def test_composer_has_anti_repeat_and_payload_priority_guards(self):
        self.assertIn("history.last_scene", self.feedback)
        self.assertIn("history.last_security", self.feedback)
        self.assertIn("history.last_line", self.feedback)
        self.assertIn("durationProfileFor(config, elapsedMs)", self.feedback)
        self.assertIn("this.clearTimers();\n            this.transition(\"completing\")", self.feedback)
        self.assertIn(
            'if (this.disposed || this.state !== "running") return;',
            self.feedback,
        )

    def test_validator_rejects_cross_product_profile_and_html(self):
        self.assertIn('Object.prototype.hasOwnProperty.call(profile, "security_keys")', self.feedback)
        self.assertIn('Object.prototype.hasOwnProperty.call(profile, "interaction_types")', self.feedback)
        self.assertIn("OFS invalid pair", self.feedback)
        self.assertIn("OFS content must be plain text", self.feedback)

    def test_composer_builds_varied_valid_scenes(self):
        result = subprocess.run(
            ["node", "tests/js/test_operation_feedback.js"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("operation feedback composer OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
