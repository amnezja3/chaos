import unittest
from pathlib import Path


class ProfileBootSnapshotContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("run.py").read_text(encoding="utf-8")

    def test_api_profile_does_not_rebuild_territory(self):
        start = self.source.index('@app.route("/api/profile")')
        end = self.source.index('@app.route("/api/dev/bug-reports")', start)
        endpoint = self.source[start:end]

        self.assertIn("rebuild_territory=False", endpoint)
        self.assertIn("persist_normalization=False", endpoint)
        self.assertIn("cache_in_session=False", endpoint)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", endpoint)
        self.assertNotIn("refresh_and_persist_operations", endpoint)
        self.assertIn("bounded_operations_from_store", endpoint)
        self.assertIn("refresh_operation_runtime", endpoint)

    def test_api_profile_exposes_canonical_profession_name_without_another_profile_read(self):
        start = self.source.index('@app.route("/api/profile")')
        end = self.source.index('@app.route("/api/dev/bug-reports")', start)
        endpoint = self.source[start:end]

        self.assertIn("normalize_ghostnetwork_profile_identity(profile)", endpoint)
        self.assertIn('profile["ghost_profession_name"]', endpoint)
        self.assertEqual(endpoint.count("sync_session_profile("), 1)

    def test_profile_window_renders_profession_under_clan(self):
        terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        start = terminal.index("async function createProfile()")
        end = terminal.index("async function getUserProfile()", start)
        renderer = terminal[start:end]

        self.assertIn("profileData.ghost_profession_name", renderer)
        self.assertIn("Profesja:", renderer)
        self.assertLess(renderer.index("Klan:"), renderer.index("Profesja:"))

    def test_desktop_boot_does_not_rebuild_territory(self):
        start = self.source.index('@app.route("/desktop")')
        end = self.source.index("def require_dev_admin", start)
        endpoint = self.source[start:end]

        self.assertIn('session.pop("profile", None)', endpoint)
        self.assertIn("user_store.has_user(user)", endpoint)
        self.assertNotIn("sync_session_profile", endpoint)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", endpoint)
        self.assertIn("redirect_missing_profile_to_login", endpoint)

    def test_desktop_template_does_not_receive_full_profile(self):
        start = self.source.index('@app.route("/desktop")')
        end = self.source.index("def require_dev_admin", start)
        endpoint = self.source[start:end]

        self.assertNotIn("inventory=", endpoint)
        self.assertNotIn("profile=profile", endpoint)

    def test_every_desktop_template_render_has_explicit_canonical_generation(self):
        start = self.source.index('@app.route("/desktop")')
        end = self.source.index("def require_dev_admin", start)
        endpoint = self.source[start:end]

        generation_assignment = (
            "session_generation = session_generation_client_context()"
        )
        template_render = 'render_template(\n        "linux.html",'
        self.assertEqual(self.source.count('"linux.html"'), 1)
        self.assertIn(generation_assignment, endpoint)
        self.assertIn("session_generation=session_generation", endpoint)
        self.assertLess(
            endpoint.index(generation_assignment),
            endpoint.index(template_render),
        )

    def test_map_document_boot_does_not_rebuild_territory(self):
        start = self.source.index('@app.route("/map")')
        end = self.source.index("@app.route('/map-action'", start)
        endpoint = self.source[start:end]

        self.assertIn("rebuild_territory=False", endpoint)
        self.assertIn("persist_normalization=False", endpoint)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", endpoint)

    def test_map_actions_and_hack_launch_use_lightweight_profile_sync(self):
        map_start = self.source.index("@app.route('/map-action'")
        map_end = self.source.index("@app.route('/hack-action'", map_start)
        map_endpoint = self.source[map_start:map_end]
        self.assertIn("rebuild_territory=False", map_endpoint)
        self.assertIn("persist_normalization=False", map_endpoint)

        hack_start = map_end
        hack_end = self.source.index('@app.route("/api/profile")', hack_start)
        hack_endpoint = self.source[hack_start:hack_end]
        self.assertIn("rebuild_territory=False", hack_endpoint)
        self.assertIn("persist_normalization=False", hack_endpoint)

    def test_every_terminal_command_skips_territory_rebuild(self):
        start = self.source.index('@app.route("/command"')
        end = self.source.index("@app.route", start + 20)
        endpoint = self.source[start:end]

        self.assertIn("rebuild_territory=False", endpoint)
        self.assertIn("persist_normalization=False", endpoint)
        self.assertNotIn("rebuild_territory=not skip_map_runtime", endpoint)

    def test_terminal_command_only_launches_app_and_defers_target_mutation(self):
        start = self.source.index('@app.route("/command"')
        end = self.source.index("@app.route", start + 20)
        endpoint = self.source[start:end]

        self.assertIn("command_defer_map_runtime_to_application", endpoint)
        self.assertIn('"target": None', endpoint)
        self.assertNotIn("apply_app_map_actions_to_aimed_target", endpoint)
        self.assertNotIn("create_missing_operations_for_app_target", endpoint)

    def test_non_choice_feedback_does_not_reference_choice_variable(self):
        terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        start = terminal.index("async function notifyGonnaWin(")
        end = terminal.index("function notifyOpenMapsTargetHacked", start)
        helper = terminal[start:end]

        self.assertNotIn("choiceId", helper)
        self.assertIn("choice_id: null", helper)

    def test_lightweight_sync_can_skip_filesystem_session_cache(self):
        start = self.source.index("def sync_session_profile")
        end = self.source.index("def merge_captured_targets_into_profile", start)
        helper = self.source[start:end]

        self.assertIn("cache_in_session=True", helper)
        self.assertGreaterEqual(helper.count("if cache_in_session:"), 2)

    def test_successful_profile_refresh_repairs_toolbar_snapshot(self):
        terminal_source = Path("static/js/terminal.js").read_text(encoding="utf-8")
        start = terminal_source.index("async function getUserProfile()")
        end = terminal_source.index("function rememberProcessedDelta", start)
        helper = terminal_source[start:end]

        self.assertIn("const data = await res.json();", helper)
        self.assertIn("setToolbarProfile(data);", helper)
        self.assertLess(helper.index("setToolbarProfile(data);"), helper.index("return data;"))

    def test_login_redirect_does_not_load_or_copy_full_profile(self):
        start = self.source.index('@app.route("/", methods=["GET", "POST"])')
        end = self.source.index('@app.route("/register")', start)
        endpoint = self.source[start:end]

        self.assertIn("begin_authenticated_session(username)", endpoint)
        self.assertNotIn("UserProfileManager", endpoint)
        self.assertNotIn("sync_session_profile", endpoint)
        self.assertNotIn("set_profile_session", endpoint)

    def test_frontend_coalesces_concurrent_profile_requests(self):
        terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        declaration = terminal.index("let userProfileRequestPromise = null")
        first_boot_call = terminal.index("const profileData = await getUserProfile()")
        start = terminal.index("async function getUserProfile()")
        end = terminal.index("function rememberProcessedDelta", start)
        helper = terminal[start:end]

        self.assertLess(declaration, first_boot_call)
        self.assertIn("if (userProfileRequestPromise) return userProfileRequestPromise", helper)
        self.assertEqual(helper.count("fetch('/api/profile')"), 1)
        self.assertIn("userProfileRequestPromise = null", helper)


if __name__ == "__main__":
    unittest.main()
