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
        self.assertNotIn("rebuild_player_areas_with_territory_delta", endpoint)
        self.assertNotIn("refresh_and_persist_operations", endpoint)
        self.assertIn("player_operation_store.list_operations", endpoint)
        self.assertIn("refresh_operation_runtime", endpoint)

    def test_desktop_boot_does_not_rebuild_territory(self):
        start = self.source.index('@app.route("/desktop")')
        end = self.source.index("def require_dev_admin", start)
        endpoint = self.source[start:end]

        self.assertIn("rebuild_territory=False", endpoint)
        self.assertIn("persist_normalization=False", endpoint)
        self.assertNotIn("rebuild_player_areas_with_territory_delta", endpoint)
        self.assertIn("redirect_missing_profile_to_login", endpoint)

    def test_login_redirect_does_not_load_or_copy_full_profile(self):
        start = self.source.index('@app.route("/", methods=["GET", "POST"])')
        end = self.source.index('@app.route("/register")', start)
        endpoint = self.source[start:end]

        self.assertIn('session["user"] = username', endpoint)
        self.assertIn('session.pop("profile", None)', endpoint)
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
