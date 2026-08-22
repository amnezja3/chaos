import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import (
    ProfileDestructiveWriteRejected,
    ProfileRecoveryRequired,
    ProfileValidationError,
    ProfileWriteConflict,
)
from session_generation_store import SessionGenerationStore


class SessionGenerationIsolationTests(unittest.TestCase):
    def setUp(self):
        run.app.config.update(TESTING=True)
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_session_generation_"))
        self.original_generation_store = run.session_generation_store
        run.session_generation_store = SessionGenerationStore(
            str(self.tmpdir / "game.sqlite3")
        )
        self.client = run.app.test_client()

    def tearDown(self):
        run.session_generation_store = self.original_generation_store
        shutil.rmtree(self.tmpdir)

    @staticmethod
    def generation_headers(generation):
        return {run.SESSION_GENERATION_HEADER: generation}

    def seed_session(self, username="alice", generation="generation-alice"):
        lineage = f"lineage-{username}-{id(self)}"
        run.session_generation_store.activate(
            lineage,
            generation,
            username,
            reason="test_seed",
        )
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = username
            flask_session[run.SESSION_LINEAGE_KEY] = lineage
            flask_session[run.SESSION_GENERATION_KEY] = generation
        return lineage

    def read_session(self, client=None):
        client = client or self.client
        with client.session_transaction() as flask_session:
            return {
                "user": flask_session.get("user"),
                "lineage": flask_session.get(run.SESSION_LINEAGE_KEY),
                "generation": flask_session.get(run.SESSION_GENERATION_KEY),
                "sid": getattr(flask_session, "sid", None),
            }

    def assert_desktop_generation(self, response, username, generation):
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        marker = '<script id="session-generation-config" type="application/json">'
        config_start = html.index(marker) + len(marker)
        config_end = html.index("</script>", config_start)
        context = json.loads(html[config_start:config_end].strip())

        self.assertEqual(context["generation"], generation)
        self.assertEqual(context["username"], username)
        self.assertEqual(context["header"], run.SESSION_GENERATION_HEADER)
        self.assertEqual(
            context["query_token"],
            run._session_generation_query_token(generation),
        )
        self.assertEqual(
            response.headers[run.SESSION_GENERATION_HEADER],
            generation,
        )

    def test_successful_anonymous_login_rotates_sid_and_starts_generation(self):
        before = self.read_session()

        with patch.object(run, "authenticate_user", return_value=True):
            response = self.client.post(
                "/",
                data={"username": "alice", "password": "secret"},
            )

        after = self.read_session()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(after["user"], "alice")
        self.assertTrue(after["generation"])
        if before["sid"] and after["sid"]:
            self.assertNotEqual(after["sid"], before["sid"])

    def test_failed_durable_activation_leaves_existing_session_intact(self):
        before = self.read_session()
        with patch.object(run, "authenticate_user", return_value=True), \
                patch.object(
                    run.session_generation_store,
                    "activate",
                    side_effect=RuntimeError("database unavailable"),
                ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/",
                    data={"username": "bob", "password": "secret"},
                )

        after = self.read_session()
        self.assertEqual(before["user"], after["user"])
        self.assertEqual(before["lineage"], after["lineage"])
        self.assertEqual(before["generation"], after["generation"])

    def test_rotation_failure_after_activation_leaves_no_authenticated_cookie(self):
        activated = {}
        real_activate = run.session_generation_store.activate

        def capture_activation(lineage, generation, username, **kwargs):
            activated.update({
                "lineage": lineage,
                "generation": generation,
                "username": username,
            })
            return real_activate(lineage, generation, username, **kwargs)

        with patch.object(run, "authenticate_user", return_value=True), \
                patch.object(
                    run.session_generation_store,
                    "activate",
                    side_effect=capture_activation,
                ), \
                patch.object(
                    run,
                    "_rotate_server_session_id",
                    side_effect=RuntimeError("session backend unavailable"),
                ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/",
                    data={"username": "bob", "password": "secret"},
                )

        self.assertIsNone(self.read_session()["user"])
        self.assertTrue(
            run.session_generation_store.is_current(
                activated["lineage"],
                activated["generation"],
                "bob",
            )
        )

    def test_failed_login_preserves_anonymous_session(self):
        before = self.read_session()

        with patch.object(run, "authenticate_user", return_value=False):
            response = self.client.post(
                "/",
                data={"username": "bob", "password": "bad"},
            )

        after = self.read_session()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before["user"], after["user"])
        self.assertEqual(before["lineage"], after["lineage"])
        self.assertEqual(before["generation"], after["generation"])

    def test_successful_registration_starts_fresh_session_and_renders_desktop(self):
        with patch.object(run.user_store, "username_exists", return_value=False), \
                patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run.user_store, "has_user", return_value=True), \
                patch.object(run, "get_start_location_by_ip", return_value={
                    "city": "Warsaw", "lat": 52.2, "lng": 21.0, "source": "test",
                }), \
                patch.object(run, "UserProfileManager") as manager_cls:
            manager_cls.return_value.add_new_user.return_value = True
            response = self.client.post("/api/register-finalize", json={
                "username": "new_player",
                "password": "secret123",
                "faction": "ghost",
                "role": "runner",
                "nick": "New Player",
                "email": "new@example.test",
            })
            desktop = self.client.get(response.get_json()["redirect"])
        state = self.read_session()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(state["user"], "new_player")
        self.assertTrue(state["generation"])
        self.assert_desktop_generation(
            desktop,
            "new_player",
            state["generation"],
        )

    def test_missing_or_stale_generation_is_rejected_before_read(self):
        self.seed_session()
        with patch.object(run.delta_bus, "get_changes_since") as read_changes:
            missing = self.client.get("/api/state/changes")
            stale = self.client.get(
                "/api/state/changes",
                headers=self.generation_headers("stale-generation"),
            )

        self.assertEqual(missing.status_code, 409)
        self.assertEqual(missing.get_json()["reason"], "missing_generation")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["reason"], "stale_generation")
        self.assertEqual(stale.headers[run.SESSION_GENERATION_ERROR_HEADER], "mismatch")
        read_changes.assert_not_called()

    def test_matching_generation_is_reflected_and_response_is_not_cached(self):
        self.seed_session()
        payload = {"current_version": 7, "changes": [], "recovery_required": False}
        with patch.object(run.delta_bus, "get_changes_since", return_value=payload):
            response = self.client.get(
                "/api/state/changes?since=6",
                headers=self.generation_headers("generation-alice"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers[run.SESSION_GENERATION_HEADER], "generation-alice")
        self.assertEqual(response.headers[run.SESSION_GENERATION_USER_HEADER], "alice")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_in_flight_response_is_rejected_if_lineage_changes_during_read(self):
        lineage = self.seed_session()

        def replace_generation(*_args, **_kwargs):
            run.session_generation_store.activate(
                lineage,
                "generation-b",
                "alice",
                reason="concurrent_login_b",
            )
            return {
                "current_version": 7,
                "changes": [{"must_not_escape": True}],
                "recovery_required": False,
            }

        with patch.object(
            run.delta_bus,
            "get_changes_since",
            side_effect=replace_generation,
        ):
            response = self.client.get(
                "/api/state/changes?since=6",
                headers=self.generation_headers("generation-alice"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["reason"],
            "durable_response_generation_replaced",
        )
        self.assertNotIn("changes", response.get_json())

    def test_replaced_in_flight_request_cannot_restore_its_old_session_cookie(self):
        lineage = self.seed_session()

        def replace_after_legacy_session_write(*_args, **_kwargs):
            # Reproduce a legacy request which marked its old server-side
            # session dirty before a newer login won the durable lineage.
            run.session["profile"] = {"stale": "must-not-set-cookie"}
            run.session_generation_store.activate(
                lineage,
                "generation-b",
                "alice",
                reason="concurrent_login_b",
            )
            return {
                "current_version": 7,
                "changes": [{"must_not_escape": True}],
                "recovery_required": False,
            }

        with patch.object(
            run.delta_bus,
            "get_changes_since",
            side_effect=replace_after_legacy_session_write,
        ):
            response = self.client.get(
                "/api/state/changes?since=6",
                headers=self.generation_headers("generation-alice"),
            )

        self.assertEqual(409, response.status_code)
        self.assertEqual(
            "durable_response_generation_replaced",
            response.get_json()["reason"],
        )
        self.assertNotIn("Set-Cookie", response.headers)

    def test_legacy_unit_fixture_remains_compatible_only_in_testing_mode(self):
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        payload = {"current_version": 0, "changes": [], "recovery_required": False}
        with patch.object(run.delta_bus, "get_changes_since", return_value=payload):
            response = self.client.get("/api/state/changes")
        self.assertEqual(response.status_code, 200)

    def test_runtime_api_without_generation_requires_document_bootstrap(self):
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        previous_testing = run.app.testing
        run.app.config["TESTING"] = False
        try:
            response = self.client.get("/api/state/changes")
        finally:
            run.app.config["TESTING"] = previous_testing
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["reason"], "generation_bootstrap_required")

    def test_desktop_bootstraps_generation_and_loads_bridge_before_runtime(self):
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        with patch.object(run.user_store, "has_user", return_value=True):
            canonical = self.client.get("/desktop")
            state = self.read_session()
            response = self.client.get(canonical.headers["Location"])

        html = response.get_data(as_text=True)
        self.assertEqual(canonical.status_code, 302)
        self.assertIn(
            run._session_generation_query_token(state["generation"]),
            canonical.headers["Location"],
        )
        self.assertNotIn(state["generation"], canonical.headers["Location"])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(state["generation"])
        self.assertIn("session-generation-config", html)
        self.assertLess(html.index("session_generation.js"), html.index("terminal.js"))

    def test_direct_map_url_is_canonicalized_and_stale_refresh_is_rejected(self):
        lineage = self.seed_session(generation="generation-map-a")
        canonical = self.client.get("/map?scheme=opentopo")

        self.assertEqual(302, canonical.status_code)
        canonical_url = canonical.headers["Location"]
        self.assertIn("scheme=opentopo", canonical_url)
        self.assertIn(
            run._session_generation_query_token("generation-map-a"),
            canonical_url,
        )
        self.assertNotIn("generation-map-a", canonical_url)

        run.session_generation_store.activate(
            lineage,
            "generation-map-b",
            "alice",
            reason="concurrent_login_b",
        )
        with self.client.session_transaction() as flask_session:
            flask_session[run.SESSION_GENERATION_KEY] = "generation-map-b"

        stale_refresh = self.client.get(canonical_url)
        self.assertEqual(409, stale_refresh.status_code)
        self.assertEqual(
            "stale_generation",
            stale_refresh.get_json()["reason"],
        )

    def test_account_switch_a_to_b_to_a_never_reuses_first_a_generation(self):
        with patch.object(run, "authenticate_user", return_value=True):
            first_login = self.client.post(
                "/",
                data={"username": "alice", "password": "secret"},
            )
            first_a = self.read_session()["generation"]
            first_desktop_url = first_login.headers["Location"]
            self.assertIn(
                run._session_generation_query_token(first_a),
                first_desktop_url,
            )
            self.assertNotIn(first_a, first_desktop_url)
            self.client.get(
                "/logout?_session_generation="
                f"{run._session_generation_query_token(first_a)}"
            )
            self.client.post(
                "/",
                data={"username": "bob", "password": "secret"},
            )
            bob = self.read_session()["generation"]
            stale_desktop = self.client.get(first_desktop_url)
            self.assertEqual(409, stale_desktop.status_code)
            self.assertEqual("stale_generation", stale_desktop.get_json()["reason"])
            self.assertEqual("bob", self.read_session()["user"])
            self.client.get(
                "/logout?_session_generation="
                f"{run._session_generation_query_token(bob)}"
            )
            self.client.post(
                "/",
                data={"username": "alice", "password": "secret"},
            )
            second_a = self.read_session()["generation"]

        self.assertNotEqual(first_a, bob)
        self.assertNotEqual(first_a, second_a)
        self.assertNotEqual(bob, second_a)
        rejected = self.client.get(
            "/api/state/changes",
            headers=self.generation_headers(first_a),
        )
        self.assertEqual(rejected.status_code, 409)

        stale_map = self.client.get(
            "/map?_embedded=1&_session_generation="
            f"{run._session_generation_query_token(first_a)}",
        )
        self.assertEqual(stale_map.status_code, 409)
        self.assertEqual(stale_map.get_json()["reason"], "stale_generation")

        stale_logout = self.client.get(
            "/logout?_session_generation="
            f"{run._session_generation_query_token(first_a)}"
        )
        self.assertEqual(stale_logout.status_code, 409)
        self.assertEqual(self.read_session()["generation"], second_a)

    def test_account_switch_a_to_b_to_a_renders_each_desktop_generation(self):
        def login_and_open_desktop(username):
            login = self.client.post(
                "/",
                data={"username": username, "password": "secret"},
            )
            self.assertEqual(login.status_code, 302)
            state = self.read_session()
            desktop = self.client.get(login.headers["Location"])
            self.assert_desktop_generation(
                desktop,
                username,
                state["generation"],
            )
            return state

        def logout_generation(generation):
            response = self.client.get(
                "/logout?_session_generation="
                f"{run._session_generation_query_token(generation)}"
            )
            self.assertEqual(response.status_code, 302)
            self.assertIsNone(self.read_session()["user"])

        with patch.object(run, "authenticate_user", return_value=True), \
                patch.object(run.user_store, "has_user", return_value=True):
            first_a = login_and_open_desktop("alice")
            logout_generation(first_a["generation"])
            bob = login_and_open_desktop("bob")
            logout_generation(bob["generation"])
            second_a = login_and_open_desktop("alice")

        self.assertNotEqual(first_a["generation"], bob["generation"])
        self.assertNotEqual(first_a["generation"], second_a["generation"])
        self.assertNotEqual(bob["generation"], second_a["generation"])

    def test_two_independent_sessions_for_same_user_do_not_invalidate_each_other(self):
        first = run.app.test_client()
        second = run.app.test_client()
        with patch.object(run, "authenticate_user", return_value=True):
            first.post("/", data={"username": "alice", "password": "secret"})
            second.post("/", data={"username": "alice", "password": "secret"})

        first_state = self.read_session(first)
        second_state = self.read_session(second)
        self.assertNotEqual(first_state["generation"], second_state["generation"])

        first.get(
            "/logout?_session_generation="
            f"{run._session_generation_query_token(first_state['generation'])}"
        )
        payload = {"current_version": 0, "changes": [], "recovery_required": False}
        with patch.object(run.delta_bus, "get_changes_since", return_value=payload):
            response = second.get(
                "/api/state/changes",
                headers=self.generation_headers(second_state["generation"]),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.read_session(second)["user"], "alice")

    def test_delete_revokes_all_sessions_and_same_login_cannot_be_registered_again(self):
        first = run.app.test_client()
        second = run.app.test_client()
        with patch.object(run, "authenticate_user", return_value=True):
            first.post("/", data={"username": "alice", "password": "secret"})
            second.post("/", data={"username": "alice", "password": "secret"})
        first_state = self.read_session(first)
        second_state = self.read_session(second)

        with patch.object(run.territory_store, "delete_user_data"), \
                patch.object(run.user_store, "delete_user", return_value=True):
            deleted = first.post(
                "/api/users/delete",
                json={"username": "alice"},
                headers=self.generation_headers(first_state["generation"]),
            )
        self.assertEqual(200, deleted.status_code)

        stale = second.get(
            "/api/state/changes",
            headers=self.generation_headers(second_state["generation"]),
        )
        self.assertEqual(409, stale.status_code)
        self.assertEqual("durable_lineage_revoked", stale.get_json()["reason"])

        with patch.object(run.user_store, "username_exists", return_value=True):
            registered = first.post("/api/register-finalize", json={
                "username": "alice",
                "password": "new-secret-2",
                "faction": "ghost",
                "role": "runner",
                "nick": "Alice Again",
                "email": "alice-again@example.test",
            })
        self.assertEqual(409, registered.status_code)
        self.assertIsNone(self.read_session(first)["user"])

        still_stale = second.get(
            "/api/state/changes",
            headers=self.generation_headers(second_state["generation"]),
        )
        self.assertEqual(409, still_stale.status_code)
        self.assertEqual(
            "durable_lineage_revoked",
            still_stale.get_json()["reason"],
        )

    def test_authenticated_account_switch_requires_current_generation_before_auth(self):
        self.seed_session("alice", "generation-alice")
        with patch.object(run, "authenticate_user", return_value=True) as authenticate:
            missing = self.client.post(
                "/",
                data={"username": "bob", "password": "secret"},
            )
            stale = self.client.post(
                "/",
                data={"username": "bob", "password": "secret"},
                headers=self.generation_headers("stale-generation"),
            )
            current = self.client.post(
                "/",
                data={"username": "bob", "password": "secret"},
                headers=self.generation_headers("generation-alice"),
            )

        self.assertEqual(409, missing.status_code)
        self.assertEqual("missing_generation", missing.get_json()["reason"])
        self.assertEqual(409, stale.status_code)
        self.assertEqual("stale_generation", stale.get_json()["reason"])
        self.assertEqual(409, current.status_code)
        self.assertEqual(
            "account_switch_requires_logout",
            current.get_json()["error"],
        )
        self.assertEqual("alice", self.read_session()["user"])
        authenticate.assert_not_called()

    def test_login_after_restart_replaces_incomplete_legacy_session(self):
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        before = self.read_session()

        with patch.object(run, "authenticate_user", return_value=True) as authenticate, \
                patch.object(run.user_store, "has_user", return_value=True):
            login = self.client.post(
                "/",
                data={"username": "alice", "password": "secret"},
            )
            state = self.read_session()
            desktop = self.client.get(login.headers["Location"])

        self.assertEqual(login.status_code, 302)
        authenticate.assert_called_once_with("alice", "secret")
        self.assertEqual(state["user"], "alice")
        self.assertTrue(state["lineage"])
        self.assertTrue(state["generation"])
        if before["sid"] and state["sid"]:
            self.assertNotEqual(before["sid"], state["sid"])
        self.assertTrue(
            run.session_generation_store.is_current(
                state["lineage"],
                state["generation"],
                "alice",
            )
        )
        self.assert_desktop_generation(
            desktop,
            "alice",
            state["generation"],
        )

    def test_old_tab_mutation_is_rejected_before_store_write(self):
        self.seed_session("bob", "generation-bob")
        with patch.object(run.system_message_store, "add_message") as add_message:
            response = self.client.post(
                "/add-system-message",
                json={"type": "info", "title": "stale", "text": "must not apply"},
                headers=self.generation_headers("generation-alice"),
            )
        self.assertEqual(response.status_code, 409)
        add_message.assert_not_called()

    def test_desktop_beacon_accepts_generation_in_json_body(self):
        self.seed_session()
        profile = {"username": "alice", "desktop_settings": {}}
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "UserProfileManager") as manager_cls:
            response = self.client.post("/api/profile/desktop", json={
                "wallpaper": "wall-1",
                "_session_generation": "generation-alice",
            })
        self.assertEqual(response.status_code, 200)
        manager_cls.return_value.update_profile.assert_called_once()

    def test_non_admin_cannot_delete_another_account(self):
        self.seed_session()
        with patch.object(run.territory_store, "delete_user_data") as delete_territory, \
                patch.object(run.user_store, "delete_user") as delete_user:
            response = self.client.post(
                "/api/users/delete",
                json={"username": "bob"},
                headers=self.generation_headers("generation-alice"),
            )
        self.assertEqual(response.status_code, 403)
        delete_territory.assert_not_called()
        delete_user.assert_not_called()

    def test_self_delete_invalidates_current_session(self):
        self.seed_session()
        with patch.object(run.territory_store, "delete_user_data"), \
                patch.object(run.user_store, "delete_user", return_value=True):
            response = self.client.post(
                "/api/users/delete",
                json={"username": "alice"},
                headers=self.generation_headers("generation-alice"),
            )
        state = self.read_session()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["logout"])
        self.assertIsNone(state["user"])
        self.assertIsNone(state["generation"])

    def test_revoke_failure_does_not_clear_still_active_session(self):
        self.seed_session()
        before = self.read_session()
        with patch.object(
            run.session_generation_store,
            "revoke",
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.get(
                    "/logout?_session_generation="
                    f"{run._session_generation_query_token(before['generation'])}"
                )

        self.assertEqual(before, self.read_session())

    def test_frontend_contract_covers_broadcast_iframe_and_beacon(self):
        bridge = Path("static/js/session_generation.js").read_text(encoding="utf-8")
        terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")
        self.assertIn("BroadcastChannel", bridge)
        self.assertIn("browser_session_replaced", bridge)
        self.assertIn("response_generation_mismatch", bridge)
        self.assertIn('root.sessionStorage?.clear?.()', bridge)
        self.assertIn("_session_generation: generation", terminal)
        self.assertEqual(terminal.count("currentSessionGenerationQuery()"), 3)
        self.assertEqual(terminal.count("authenticatedLogoutUrl()"), 4)

    def test_profile_write_errors_use_controlled_status_without_exception_details(self):
        self.seed_session()
        cases = (
            (ProfileWriteConflict("secret conflict detail"), 409, "profile_write_conflict"),
            (ProfileRecoveryRequired("secret recovery detail"), 409, "profile_recovery_required"),
            (ProfileValidationError(("secret_validation_detail",)), 422, "profile_candidate_rejected"),
            (ProfileDestructiveWriteRejected("secret destructive detail"), 422, "profile_candidate_rejected"),
        )
        for error, expected_status, expected_code in cases:
            with self.subTest(error=error.__class__.__name__), patch.object(
                run,
                "load_profile_write_record",
                side_effect=error,
            ):
                response = self.client.post(
                    "/api/profile/account",
                    json={"email": "alice-new@example.test"},
                    headers=self.generation_headers("generation-alice"),
                )

            self.assertEqual(expected_status, response.status_code)
            self.assertEqual(expected_code, response.get_json()["error"])
            self.assertNotIn("secret", response.get_data(as_text=True).lower())

    def test_profile_recovery_document_redirect_is_generic(self):
        self.seed_session()
        query_token = run._session_generation_query_token("generation-alice")
        with patch.object(
            run,
            "sync_session_profile",
            side_effect=ProfileRecoveryRequired("secret profile corruption detail"),
        ):
            response = self.client.get(
                f"/map?_session_generation={query_token}",
            )

        self.assertEqual(302, response.status_code)
        self.assertIn("profile_error=recovery_required", response.headers["Location"])
        self.assertNotIn("secret", response.headers["Location"].lower())


if __name__ == "__main__":
    unittest.main()
