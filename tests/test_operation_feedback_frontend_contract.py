import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from config import env_csv, env_float


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
        self.assertNotIn("CHAOS_OPERATION_FEEDBACK_SCAN_PORTS", self.config)
        self.assertIn('id="operation-feedback-config"', self.template)
        self.assertLess(
            self.template.index("js/operation_feedback.js"),
            self.template.index("js/terminal.js"),
        )

    def test_feedback_actions_have_global_and_per_operation_flags(self):
        self.assertIn('env_csv("CHAOS_OPERATION_FEEDBACK_ACTIONS")', self.config)
        self.assertNotIn("flags.scan_ports", self.feedback)
        self.assertIn("enabled_actions", self.feedback)
        self.assertIn('flags.enabled === true', self.feedback)

    def test_csv_flag_helper_does_not_regress_float_config(self):
        with patch.dict(os.environ, {
            "OFS_TEST_ACTIONS": " exploit,trace,exploit ",
            "OFS_TEST_FLOAT": "1.25",
        }, clear=False):
            self.assertEqual(env_csv("OFS_TEST_ACTIONS"), ["exploit", "trace"])
            self.assertEqual(env_float("OFS_TEST_FLOAT", 0), 1.25)

    def test_all_twelve_operation_profiles_are_valid_skeletons(self):
        expected_modes = {
            "scan_ports": "button_choice",
            "exploit": "terminal",
            "sniff": "terminal",
            "trace": "window",
            "trace_gps": "window",
            "trace_device": "window",
            "mic_sniff": "terminal",
            "atm_logs": "terminal",
            "install_sniffer": "button_choice",
            "camera_stream": "window",
            "camera_shutdown": "button_choice",
            "car_hack": "button_choice",
        }
        self.assertEqual(set(self.profile["operations"]), set(expected_modes))
        for action_key, mode in expected_modes.items():
            profile = self.profile["operations"][action_key]
            self.assertTrue(profile["enabled"])
            self.assertEqual(profile["action_key"], action_key)
            self.assertEqual(profile["default_presentation_mode"], mode)
            self.assertIn(mode, profile["presentation_modes"])
            self.assertTrue(profile["security"])
            self.assertTrue(profile["scene_pools"])
            self.assertEqual(profile["provisional_profile"]["timeline_profile"], "launch_150s")
            self.assertIn("extended_wait", profile["provisional_profile"]["scene_pool"])

    def test_launch_150s_skeleton_covers_extended_wait(self):
        timeline = self.profile["provisional_timelines"]["launch_150s"]
        self.assertGreaterEqual(timeline["min_coverage_ms"], 150000)
        starts = [stage["start_after_ms"] for stage in timeline["stages"]]
        self.assertEqual(starts, sorted(starts))
        self.assertGreaterEqual(starts[-1], 150000)
        self.assertEqual(timeline["stages"][-1]["family"], "extended_wait")

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
        self.assertNotIn("application_content:", notify)
        self.assertNotIn("application_content:", choice)

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

    def test_progressbar_keeps_authored_steps_and_separate_feedback_viewport(self):
        progress = self.function_source("async function app_progressbar_random", "async function notifyGonnaWin")
        self.assertIn("runNextStep();", progress)
        self.assertIn('class="operation-feedback-host"', progress)
        feedback = self.function_source(
            "function beginOperationFeedbackRequest",
            "function startLegacyAppWaitUnlessFeedbackEnabled",
        )
        self.assertIn("querySelector?.('.operation-feedback-host')", feedback)

    def test_launch_queue_preserves_map_action_for_feedback_profile(self):
        self.assertIn(
            "const action = String(rawItem.action || rawItem.map_action_id || rawItem.action_key || \"\").trim()",
            self.terminal,
        )
        self.assertIn("appData._map_action_id = item.action", self.terminal)

    def test_desktop_menu_and_terminal_resolve_feedback_action_from_app_contract(self):
        resolver = self.function_source(
            "function resolveApplicationFeedbackAction",
            "function buildApplicationLaunchContext",
        )
        context = self.function_source(
            "function buildApplicationLaunchContext",
            "function currentApplicationLaunchContext",
        )
        self.assertIn("appData.map_actions", resolver)
        self.assertIn("resolveApplicationFeedbackAction(appData)", context)
        self.assertIn('launchApplicationFromEntry(app, "desktop_menu")', self.terminal)
        self.assertEqual(
            self.terminal.count('launchApplicationFromEntry(app, "terminal")'),
            2,
        )

    def test_scan_ports_profile_has_required_mvp_libraries(self):
        required = {
            "defaults", "duration_profiles", "provisional_timelines",
            "provisional_wait_bands", "provisional_voice_packs",
            "provisional_scene_library", "scene_library", "security_library",
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

    def test_provisional_package_covers_150_seconds_and_is_manually_editable(self):
        timeline = self.profile["provisional_timelines"]["launch_150s"]
        starts = [stage["start_after_ms"] for stage in timeline["stages"]]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(starts[-1], 150000)
        self.assertEqual(len(timeline["stages"]), 15)
        self.assertEqual(timeline["extended_wait_ms"], [12000, 20000])
        library = self.profile["provisional_scene_library"]
        for stage in timeline["stages"]:
            scene = library[stage["scene_id"]]
            self.assertTrue(scene["cancelable"])
            self.assertTrue(scene["voices"])
        self.assertGreaterEqual(len(library["extended_wait"]["voices"]["default"]), 3)
        self.assertIn("composeProvisionalScene", self.feedback)
        self.assertIn("feedback_extended_wait_entered", self.terminal)

    def test_adaptive_provisional_voice_packs_cover_every_timeline_family(self):
        self.assertEqual(list(self.profile["provisional_wait_bands"]), [
            "instant", "short", "medium", "long", "extended", "overdue",
        ])
        self.assertEqual(
            [band["min_elapsed_ms"] for band in self.profile["provisional_wait_bands"].values()],
            [0, 1500, 8000, 30000, 90000, 150000],
        )
        families = {
            stage["family"]
            for stage in self.profile["provisional_timelines"]["launch_150s"]["stages"]
        }
        for voice in ("terminal", "button_choices", "window", "progressbar_random"):
            pack = self.profile["provisional_voice_packs"][voice]
            self.assertTrue(families.issubset(pack))
            for family in families:
                self.assertGreaterEqual(len(pack[family]), 3)
        self.assertIn("provisionalWaitBandFor", self.feedback)
        self.assertIn("recent_variants", self.feedback)

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
        self.assertIn("durationProfileFor(config, elapsedMs, profile)", self.feedback)
        self.assertIn(
            "this.clearTimers();\n            this.clearChoice(true);\n            this.transition(\"completing\")",
            self.feedback,
        )
        self.assertIn(
            'if (this.disposed || this.state !== "running") return;',
            self.feedback,
        )

    def test_validator_rejects_cross_product_profile_and_html(self):
        self.assertIn('Object.prototype.hasOwnProperty.call(profile, "security_keys")', self.feedback)
        self.assertIn('Object.prototype.hasOwnProperty.call(profile, "interaction_types")', self.feedback)
        self.assertIn("OFS invalid pair", self.feedback)
        self.assertIn("OFS content must be plain text", self.feedback)
        self.assertIn("validation_error", self.feedback)
        self.assertIn("Profil ${operationId} wylaczony", self.feedback)

    def test_composer_builds_varied_valid_scenes(self):
        result = subprocess.run(
            ["node", "tests/js/test_operation_feedback.js"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("operation feedback composer OK", result.stdout)

    def test_three_presentation_choices_are_local_only(self):
        operation = self.profile["operations"]["scan_ports"]
        self.assertEqual(len(operation["choice_pools"]), 3)
        for choice_id in operation["choice_pools"]:
            self.assertTrue(choice_id.startswith("feedback."))
            choice = self.profile["choice_library"][choice_id]
            self.assertEqual(choice["effect_scope"], "presentation")
            self.assertTrue(any(
                option["value"] == choice["default_value"]
                for option in choice["options"]
            ))
        self.assertIn("feedback_choice_shown", self.feedback)
        self.assertIn("feedback_choice_selected", self.feedback)
        self.assertIn("feedback_choice_timed_out", self.feedback)
        self.assertNotIn("/gonna-win", self.feedback)

    def test_application_content_is_private_and_does_not_reuse_gameplay_choices(self):
        self.assertIn("projectApplicationContent(appData)", self.terminal)
        self.assertIn("application_content: applicationContent", self.terminal)
        self.assertNotIn("dataset.applicationContent", self.terminal)
        self.assertIn("level.list", self.feedback)
        self.assertIn("level.logs", self.feedback)
        self.assertIn("level.steps", self.feedback)
        self.assertNotIn("level.buttons", self.feedback)
        self.assertNotIn("level.options", self.feedback)
        self.assertIn("app_structured", self.feedback)
        self.assertIn("app_legacy", self.feedback)
        self.assertIn("global_fallback", self.feedback)

    def test_scene_envelope_and_provisional_renderer_are_separate_from_execution_session(self):
        self.assertIn('const PRESENTATION_MODES = new Set(["ofs_provisional", "terminal", "button_choice", "window"])', self.feedback)
        self.assertIn("function createSceneEnvelope", self.feedback)
        self.assertIn("class ProvisionalSceneRenderer", self.feedback)
        self.assertIn('normalizedMode === "ofs_provisional"', self.feedback)
        self.assertIn('presentation_mode: "ofs_provisional"', self.terminal)
        self.assertIn('createPresentationRenderer?.("ofs_provisional"', self.terminal)
        provisional_source = self.feedback[
            self.feedback.index("class ProvisionalSceneRenderer"):
            self.feedback.index("function createPresentationRenderer")
        ]
        self.assertNotIn("fetch(", provisional_source)
        self.assertNotIn("/gonna-win", provisional_source)
        self.assertNotIn("securityState", provisional_source)

    def test_execution_renderers_share_envelope_and_keep_choices_isolated(self):
        for class_name in (
            "ExecutionSceneRenderer",
            "TerminalSceneRenderer",
            "ButtonChoiceSceneRenderer",
            "WindowSceneRenderer",
        ):
            self.assertIn(f"class {class_name}", self.feedback)
        self.assertIn('normalizedMode === "terminal"', self.feedback)
        self.assertIn('normalizedMode === "button_choice"', self.feedback)
        self.assertIn('normalizedMode === "window"', self.feedback)
        self.assertIn('normalized === "progressbar_random"', self.feedback)
        terminal_source = self.feedback[
            self.feedback.index("class TerminalSceneRenderer"):
            self.feedback.index("class ButtonChoiceSceneRenderer")
        ]
        window_source = self.feedback[
            self.feedback.index("class WindowSceneRenderer"):
            self.feedback.index("function createPresentationRenderer")
        ]
        self.assertNotIn("operation-feedback-choice", terminal_source)
        self.assertNotIn("operation-feedback-choice", window_source)
        self.assertIn('this.presentationMode !== "button_choice"', self.feedback)
        self.assertIn("this.renderer.render({", self.feedback)

    def test_presentation_lifecycle_handoff_and_readability_contract(self):
        self.assertIn("const PRESENTATION_PHASES", self.feedback)
        self.assertIn("function readableSceneDelay", self.feedback)
        self.assertIn("EXECUTION_TIMING_SCALE = 3", self.feedback)
        self.assertIn('this.setPresentationPhase("author_intro")', self.feedback)
        self.assertIn('this.setPresentationPhase("executing")', self.feedback)
        self.assertIn("feedback_author_scene_started", self.feedback)
        self.assertIn("feedback_execution_started", self.feedback)
        self.assertIn("if (this.activeChoice) return;", self.feedback)
        self.assertIn("feedback_provisional_handoff", self.terminal)
        self.assertIn('setApplicationPresentationPhase(session, "hydrating"', self.terminal)
        self.assertIn('setApplicationPresentationPhase(session, "author_intro")', self.terminal)
        self.assertIn('app.dataset.ofsAuthorPresented = "true"', self.terminal)
        self.assertIn("authorIntroPresented:", self.terminal)


if __name__ == "__main__":
    unittest.main()
