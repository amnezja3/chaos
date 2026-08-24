import copy
import hashlib
import io
import os
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import run
from database import (
    InstrumentedConnection,
    PlayerOperationStore,
    ProfilePrecommitRejected,
    TerritoryStore,
    UserStore,
    WalletBalanceStore,
    db_connect,
    reset_request_transaction_precommit_guard,
    set_request_transaction_precommit_guard,
)
from profileManagment import UserProfileManager
from session_generation_store import SessionGenerationStore


def complete_profile(username="alice"):
    return {
        "username": username,
        "password": "secret",
        "salt": "seed",
        "nick": username.title(),
        "email": f"{username}@example.test",
        "level": 1,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "inventory": [],
        "files": {"tools": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
    }


class FakeResources:
    def __init__(self, profiles):
        self.profiles = profiles

    def get(self, _key, seed_path=None, default=None):
        username = next(iter(self.profiles))
        return copy.deepcopy(self.profiles.get(username, default))


class SessionGenerationPrecommitTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_generation_precommit_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.user_store = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )
        self.generation_store = SessionGenerationStore(self.db_path)
        self.territory_store = TerritoryStore(self.db_path)
        self.operation_store = PlayerOperationStore(self.db_path)
        self.wallet_store = WalletBalanceStore(self.db_path)
        self.profiles = {
            "alice": complete_profile("alice"),
            "victim": complete_profile("victim"),
        }
        for profile in self.profiles.values():
            self.user_store.save_profile_guarded(
                profile,
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )

        self.original_user_store = run.user_store
        self.original_generation_store = run.session_generation_store
        self.original_territory_store = run.territory_store
        self.original_testing = run.app.config.get("TESTING")
        self.original_propagate = run.app.config.get("PROPAGATE_EXCEPTIONS")
        run.user_store = self.user_store
        run.session_generation_store = self.generation_store
        run.territory_store = self.territory_store
        run.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        self.client = run.app.test_client()

    def tearDown(self):
        run.user_store = self.original_user_store
        run.session_generation_store = self.original_generation_store
        run.territory_store = self.original_territory_store
        run.app.config.update(
            TESTING=self.original_testing,
            PROPAGATE_EXCEPTIONS=self.original_propagate,
        )
        shutil.rmtree(self.tmpdir)

    def _seed_client(self, lineage, generation, username="alice", client=None):
        client = client or self.client
        self.generation_store.activate(
            lineage,
            generation,
            username,
            reason="test_login",
        )
        with client.session_transaction() as flask_session:
            flask_session["user"] = username
            flask_session[run.SESSION_LINEAGE_KEY] = lineage
            flask_session[run.SESSION_GENERATION_KEY] = generation

    def _manager(self, username):
        return UserProfileManager(
            username,
            store=self.user_store,
            resource_store=FakeResources({username: self.profiles[username]}),
        )

    def test_endpoint_write_started_by_a_is_rolled_back_when_lineage_becomes_b(self):
        lineage = "browser-lineage"
        generation_a = "generation-a"
        generation_b = "generation-b"
        self._seed_client(lineage, generation_a)
        before = self.user_store.get_profile_with_revision("alice")
        lkg_before = self.user_store.get_last_known_good("alice")

        def manager_after_replacement(username):
            # The request and manager have already observed generation A. Move
            # the same durable lineage to B immediately before update_profile
            # obtains its writer transaction and runs the central hook.
            manager = self._manager(username)
            self.generation_store.activate(
                lineage,
                generation_b,
                "alice",
                reason="concurrent_login_b",
            )
            return manager

        with patch.object(
            run,
            "UserProfileManager",
            side_effect=manager_after_replacement,
        ):
            response = self.client.post(
                "/api/profile/desktop",
                json={"wallpaper": "wall-1"},
                headers={run.SESSION_GENERATION_HEADER: generation_a},
            )

        after = self.user_store.get_profile_with_revision("alice")
        lkg_after = self.user_store.get_last_known_good("alice")
        self.assertEqual(409, response.status_code)
        self.assertEqual(
            "durable_response_generation_replaced",
            response.get_json()["reason"],
        )
        self.assertEqual(before["profile_revision"], after["profile_revision"])
        self.assertEqual(before["checksum"], after["checksum"])
        self.assertEqual(before["profile"], after["profile"])
        self.assertEqual(lkg_before, lkg_after)

    def test_real_self_delete_commits_cleanup_before_revoking_lineage(self):
        lineage = "delete-browser"
        generation = "delete-generation"
        self._seed_client(lineage, generation)

        response = self.client.post(
            "/api/users/delete",
            json={"username": "alice"},
            headers={run.SESSION_GENERATION_HEADER: generation},
        )

        self.assertEqual(200, response.status_code)
        self.assertFalse(self.user_store.has_user("alice"))
        self.assertFalse(
            self.generation_store.is_current(lineage, generation, "alice")
        )
        with self.client.session_transaction() as flask_session:
            self.assertIsNone(flask_session.get("user"))

    def test_real_delete_tombstones_login_and_revokes_every_browser_lineage(self):
        second = run.app.test_client()
        self._seed_client("delete-primary", "delete-primary-a")
        self._seed_client(
            "delete-secondary",
            "delete-secondary-a",
            client=second,
        )

        response = second.post(
            "/api/users/delete",
            json={"username": "alice"},
            headers={run.SESSION_GENERATION_HEADER: "delete-secondary-a"},
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(self.user_store.has_user("alice"))
        self.assertEqual(
            "identity_tombstoned",
            self.user_store.identity_reuse_block_reason("alice"),
        )

        stale = self.client.get(
            "/api/state/changes",
            headers={run.SESSION_GENERATION_HEADER: "delete-primary-a"},
        )
        self.assertEqual(409, stale.status_code)
        self.assertEqual("durable_lineage_replaced", stale.get_json()["reason"])

        with patch.object(run, "UserProfileManager") as manager_cls:
            registration = second.post(
                "/api/register-finalize",
                json={
                    "username": "alice",
                    "password": "new-secret-2",
                    "faction": "ghost",
                    "role": "runner",
                    "nick": "Alice Again",
                    "email": "alice-again@example.test",
                },
            )
        self.assertEqual(409, registration.status_code)
        manager_cls.assert_not_called()

    def test_stale_actor_guard_rejects_cross_account_profile_write(self):
        lineage = "actor-browser"
        generation_a = "actor-generation-a"
        self.generation_store.activate(
            lineage, generation_a, "alice", reason="test_login"
        )
        victim_before = self.user_store.get_profile_with_revision("victim")

        with run.app.test_request_context(
            "/api/profile/account",
            method="POST",
            headers={run.SESSION_GENERATION_HEADER: generation_a},
        ):
            run.session["user"] = "alice"
            run.session[run.SESSION_LINEAGE_KEY] = lineage
            run.session[run.SESSION_GENERATION_KEY] = generation_a
            self.assertIsNone(run.app.preprocess_request())
            manager = self._manager("victim")
            self.generation_store.activate(
                lineage,
                "actor-generation-b",
                "alice",
                reason="concurrent_login_b",
            )
            with self.assertRaises(ProfilePrecommitRejected):
                manager.update_profile({"respect": 9})

        victim_after = self.user_store.get_profile_with_revision("victim")
        self.assertEqual(
            victim_before["profile_revision"], victim_after["profile_revision"]
        )
        self.assertEqual(victim_before["profile"], victim_after["profile"])

    def test_latest_browser_login_blocks_previous_session_precommit(self):
        self.generation_store.activate(
            "browser-one", "generation-one-a", "alice", reason="login"
        )
        self.generation_store.activate(
            "browser-two", "generation-two", "alice", reason="login"
        )
        # The latest login on browser one replaces browser two account-wide.
        self.generation_store.activate(
            "browser-one", "generation-one-b", "alice", reason="switch"
        )

        with run.app.test_request_context(
            "/api/profile/account",
            method="POST",
            headers={run.SESSION_GENERATION_HEADER: "generation-two"},
        ):
            run.session["user"] = "alice"
            run.session[run.SESSION_LINEAGE_KEY] = "browser-two"
            run.session[run.SESSION_GENERATION_KEY] = "generation-two"
            response = run.app.preprocess_request()
            self.assertIsNotNone(response)
            self.assertEqual(409, response.status_code)

        current = self.user_store.get_profile_with_revision("alice")
        self.assertEqual(1, current["profile_revision"])
        self.assertEqual(0, current["profile"]["respect"])

    def test_request_profile_telemetry_uses_only_bounded_one_way_ids(self):
        lineage = "telemetry-browser-lineage"
        generation = "raw-generation-secret-never-log"
        request_id = "raw-request-id-never-log"
        self._seed_client(lineage, generation)
        output = io.StringIO()

        with patch.dict(os.environ, {"CHAOS_PROFILE_WRITE_METRICS": "1"}), \
                patch.object(
                    run,
                    "UserProfileManager",
                    side_effect=lambda username: self._manager(username),
                ), redirect_stdout(output):
            response = self.client.post(
                "/api/profile/desktop",
                json={"wallpaper": "wall-1"},
                headers={
                    run.SESSION_GENERATION_HEADER: generation,
                    "X-Request-Id": request_id,
                },
            )

        events = output.getvalue()
        self.assertEqual(200, response.status_code)
        self.assertIn("profile.write_attempt", events)
        self.assertIn("profile.write_applied", events)
        self.assertNotIn(generation, events)
        self.assertNotIn(request_id, events)
        self.assertIn(
            hashlib.sha256(generation.encode("utf-8")).hexdigest()[:16],
            events,
        )
        self.assertIn(
            hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:16],
            events,
        )

    def test_plain_store_transaction_rolls_back_when_request_generation_is_stale(self):
        lineage = "plain-store-browser"
        generation_a = "plain-store-a"
        self.generation_store.activate(
            lineage, generation_a, "alice", reason="login"
        )
        with db_connect(self.db_path, enforce_request_guard=False) as conn:
            conn.execute(
                "CREATE TABLE ordinary_mutations (value TEXT NOT NULL)"
            )

        guard = self.generation_store.build_transaction_precommit_guard(
            lineage,
            generation_a,
            "alice",
        )
        token = set_request_transaction_precommit_guard(guard)
        try:
            self.generation_store.activate(
                lineage,
                "plain-store-b",
                "alice",
                reason="concurrent_login_b",
            )
            with self.assertRaises(ProfilePrecommitRejected):
                with db_connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO ordinary_mutations(value) VALUES (?)",
                        ("must-rollback",),
                    )
        finally:
            reset_request_transaction_precommit_guard(token)

        with db_connect(self.db_path, enforce_request_guard=False) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM ordinary_mutations"
            ).fetchone()[0]
        self.assertEqual(0, count)

    def test_replaced_login_rolls_back_wallet_territory_and_operation_commits(self):
        lineage_a = "canonical-browser-a"
        generation_a = "canonical-generation-a"
        self.generation_store.activate(
            lineage_a, generation_a, "alice", reason="login_a"
        )
        wallet_before = self.wallet_store.get_balance("alice")
        guard = self.generation_store.build_transaction_precommit_guard(
            lineage_a,
            generation_a,
            "alice",
        )
        token = set_request_transaction_precommit_guard(guard)
        try:
            self.generation_store.activate(
                "canonical-browser-b",
                "canonical-generation-b",
                "alice",
                reason="login_b",
            )
            mutations = (
                lambda: self.wallet_store.credit(
                    "alice",
                    77,
                    transaction_key="stale-wallet-credit",
                ),
                lambda: self.territory_store.save_captured_target(
                    "alice",
                    {"lat": 52.1, "lng": 21.0, "label": "stale-territory"},
                ),
                lambda: self.operation_store.upsert_operations(
                    "alice",
                    [{
                        "operation_id": "stale-operation",
                        "type": "hack",
                        "status": "active",
                        "target": {"username": "victim"},
                    }],
                    dedupe_key_prefix="stale-operation",
                ),
            )
            for mutate in mutations:
                with self.subTest(mutation=mutate):
                    with self.assertRaises(ProfilePrecommitRejected):
                        mutate()
        finally:
            reset_request_transaction_precommit_guard(token)

        self.assertEqual(wallet_before, self.wallet_store.get_balance("alice"))
        self.assertEqual([], self.territory_store.list_captured_targets("alice"))
        self.assertEqual([], self.operation_store.list_operations("alice"))

    def test_native_connection_context_dispatches_guarded_exit(self):
        lineage = "native-context-browser"
        generation_a = "native-context-a"
        self.generation_store.activate(
            lineage, generation_a, "alice", reason="login"
        )
        with db_connect(self.db_path, enforce_request_guard=False) as conn:
            conn.execute("CREATE TABLE native_mutations (value TEXT NOT NULL)")

        guard = self.generation_store.build_transaction_precommit_guard(
            lineage,
            generation_a,
            "alice",
        )
        token = set_request_transaction_precommit_guard(guard)
        conn = sqlite3.connect(
            self.db_path,
            timeout=15,
            factory=InstrumentedConnection,
        )
        try:
            self.generation_store.activate(
                lineage,
                "native-context-b",
                "alice",
                reason="concurrent_login_b",
            )
            with self.assertRaises(ProfilePrecommitRejected):
                with conn:
                    conn.execute(
                        "INSERT INTO native_mutations(value) VALUES (?)",
                        ("must-rollback",),
                    )
        finally:
            conn.close()
            reset_request_transaction_precommit_guard(token)

        with db_connect(self.db_path, enforce_request_guard=False) as probe:
            count = probe.execute(
                "SELECT COUNT(*) FROM native_mutations"
            ).fetchone()[0]
        self.assertEqual(0, count)


if __name__ == "__main__":
    unittest.main()
