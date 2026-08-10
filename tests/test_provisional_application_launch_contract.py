import unittest
from pathlib import Path


class ProvisionalApplicationLaunchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Path("config.py").read_text(encoding="utf-8")
        cls.run_source = Path("run.py").read_text(encoding="utf-8")
        cls.template = Path("templates/linux.html").read_text(encoding="utf-8")
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")

    def function_source(self, start, end):
        start_index = self.terminal.index(start)
        end_index = self.terminal.index(end, start_index)
        return self.terminal[start_index:end_index]

    def test_feature_flag_is_off_by_default_and_injected_as_json(self):
        self.assertIn('"CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED",', self.config)
        self.assertIn("False,", self.config)
        self.assertIn('id="provisional-app-launch-config"', self.template)
        self.assertIn("provisional_app_launch_flags | tojson", self.template)

    def test_single_app_discovery_uses_backend_match_and_auto_select(self):
        self.assertIn("len(preflight_matched_apps) > 1 or PROVISIONAL_APP_LAUNCH_ENABLED", self.run_source)
        self.assertIn('"auto_select": auto_select', self.run_source)
        self.assertIn("serialize_tool_selection_app(app)", self.run_source)
        opener = self.function_source(
            "window.openToolSelectionForMapAction = async function(payload)",
            "async function createFileManager",
        )
        self.assertIn("payload?.auto_select === true", opener)
        self.assertIn("matching_apps.length === 1", opener)
        self.assertIn("await selectMapActionTool", opener)
        self.assertLess(opener.index("await selectMapActionTool"), opener.index("createMapToolPicker"))

    def test_provisional_window_does_not_issue_gameplay_requests(self):
        source = self.function_source(
            "function beginProvisionalLaunch",
            "window.beginProvisionalLaunch = beginProvisionalLaunch",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("/gonna-win", source)
        self.assertNotIn("notifyGonnaWin", source)
        self.assertIn("provisionalApplicationSessions.set", source)
        self.assertIn("disposeProvisionalApplicationSession", source)

    def test_shell_is_created_before_selected_app_request(self):
        source = self.function_source(
            "async function selectMapActionTool",
            "function closeMapToolPicker",
        )
        self.assertLess(source.index("beginProvisionalLaunch(selection, app)"), source.index("fetch('/hack-action'"))

    def test_tool_picker_closes_when_provisional_window_takes_over(self):
        source = self.function_source(
            "async function selectMapActionTool",
            "function closeMapToolPicker",
        )
        created = source.index("provisionalSession = beginProvisionalLaunch(selection, app)")
        closed = source.index("closeMapToolPicker(false)", created)
        request = source.index("fetch('/hack-action'", created)
        self.assertLess(created, closed)
        self.assertLess(closed, request)
        self.assertIn("provisionalSession?.appWindow?.isConnected", source)
        self.assertIn("selected_app_id: app.id", source)
        self.assertIn("updateProvisionalApplicationSession", source)

    def test_registry_identity_is_not_interface_and_app_id_only(self):
        source = self.function_source(
            "function buildProvisionalLaunchSessionKey",
            "function updateProvisionalApplicationSession",
        )
        self.assertIn("pending._client_action_key", source)
        self.assertIn("flowId", source)
        self.assertIn("appId", source)
        self.assertNotIn("buildApplicationWindowLaunchKey", source)

    def test_launcher_hydrates_existing_window_before_legacy_launch(self):
        poller = self.function_source(
            "async function pollLaunchQueue",
            "// Uruchom po załadowaniu strony",
        )
        self.assertIn("resolveProvisionalApplicationLaunch(item)", poller)
        self.assertIn("hydrateProvisionalApplicationSession", poller)
        self.assertLess(
            poller.index("hydrateProvisionalApplicationSession"),
            poller.rindex("launchApplicationEffect(appData)"),
        )
        self.assertIn('currentResolution.outcome === "tombstoned"', poller)

    def test_hydration_reuses_the_exact_provisional_dom_window(self):
        source = self.function_source(
            "function consumeProvisionalHydrationWindow",
            "function buildApplicationLaunchContext",
        )
        self.assertIn("const app = session.appWindow", source)
        self.assertIn("prepareApplicationRenderWindow", source)
        self.assertIn("if (!app.isConnected) document.body.appendChild(app)", source)
        for interface in ("window", "progressbar_random", "terminal", "button_choices"):
            self.assertIn(f'prepareApplicationRenderWindow(id, "{interface}")', self.terminal)

    def test_hydration_rebinds_drag_handle_replaced_by_authoritative_renderer(self):
        consume = self.function_source(
            "function consumeProvisionalHydrationWindow",
            "function beginApplicationRenderLaunch",
        )
        finish = self.function_source(
            "function finishApplicationRenderWindow",
            "function hydrateProvisionalApplicationSession",
        )
        self.assertIn("delete app.dataset.draggableBound", consume)
        self.assertIn("makeDraggable(app)", finish)
        self.assertNotIn("if (!hydrated) makeDraggable(app)", finish)

    def test_receipt_client_key_and_tombstone_protect_parallel_and_late_launches(self):
        resolver = self.function_source(
            "function provisionalSessionMatchesLaunch",
            "function bindProvisionalApplicationReceipt",
        )
        self.assertIn("session.receipt", resolver)
        self.assertIn("session.clientActionKey", resolver)
        self.assertIn("session.flowId", resolver)
        self.assertIn("session.action", resolver)
        self.assertIn('outcome: "tombstoned"', resolver)
        normalizer = self.function_source(
            "function normalizeLaunchQueueItem",
            "function shouldSkipRecentLaunchQueueApp",
        )
        self.assertIn("client_action_key", normalizer)
        self.assertIn("has_explicit_receipt", normalizer)

    def test_operation_feedback_transitions_the_same_session_lifecycle(self):
        source = self.function_source(
            "function beginOperationFeedbackRequest",
            "function startLegacyAppWaitUnlessFeedbackEnabled",
        )
        self.assertIn('"executing"', source)
        self.assertIn('"completing"', source)
        self.assertIn('"failed"', source)

    def test_pre_execution_scenes_are_local_and_do_not_issue_gameplay_requests(self):
        source = self.function_source(
            "function buildPreExecutionScenes",
            "function disposeProvisionalApplicationSession",
        )
        for family in ("app_identity", "local_init", "context_bind", "runtime_prepare", "hydration_wait"):
            self.assertIn(f'family: "{family}"', source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("notifyGonnaWin", source)
        self.assertNotIn("sendGonnaWinRequest", source)
        self.assertIn("Math.min(9000", source)

    def test_hydration_and_dispose_stop_pre_execution_scheduler(self):
        consume = self.function_source(
            "function consumeProvisionalHydrationWindow",
            "function beginApplicationRenderLaunch",
        )
        dispose = self.function_source(
            "function disposeProvisionalApplicationSession",
            "function beginProvisionalLaunch",
        )
        self.assertIn('stopPreExecutionPresentation(session, "hydration")', consume)
        self.assertIn("stopPreExecutionPresentation(session, reason)", dispose)
        self.assertLess(
            consume.index("stopPreExecutionPresentation"),
            consume.index('updateProvisionalApplicationSession(session, "hydrating"'),
        )

    def test_pre_execution_viewport_starts_after_window_is_attached(self):
        source = self.function_source(
            "function beginProvisionalLaunch",
            "window.beginProvisionalLaunch = beginProvisionalLaunch",
        )
        self.assertIn('class="provisional-app-scenes"', source)
        self.assertIn("startPreExecutionPresentation", source)
        self.assertLess(source.index("document.body.appendChild(appWindow)"), source.index("startPreExecutionPresentation"))


if __name__ == "__main__":
    unittest.main()
