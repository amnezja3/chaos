import copy
import json
import shutil
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from database import (
    PROFILE_INTEGRITY_RECOVERY_REQUIRED,
    PROFILE_INTEGRITY_VALID,
    ProfileDestructiveWriteRejected,
    ProfilePrecommitRejected,
    ProfileRecoveryRequired,
    ProfileValidationError,
    ProfileWriteConflict,
    UserStore,
    WalletBalanceStore,
    db_connect,
    init_db,
    profile_payload_checksum,
    reset_profile_precommit_guard,
    set_profile_precommit_guard,
    utc_now,
)


def complete_profile(username="alice", **updates):
    profile = {
        "username": username,
        "password": "secret-pass",
        "salt": "seed",
        "nick": username.title(),
        "email": f"{username}@example.test",
        "avatar": "/static/images/default_avatar.png",
        "level": 1,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "clan": "Alpha",
        "fraction": {"id": "alpha"},
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "operations": [],
        "targets": [],
        "market_history": [],
        "product_purchases": [],
        "storage_upgrades": [],
        "ghostnetwork_reward_history": [],
        "risk_events": [],
        "system_messages": [],
        "launch_queue": [],
    }
    profile.update(copy.deepcopy(updates))
    return profile


class ProfileWriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_profile_guard_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.store = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def create(self, profile=None):
        return self.store.save_profile_guarded(
            profile or complete_profile(),
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )

    def test_guarded_registration_creates_revision_and_verified_lkg(self):
        result = self.create()

        record = self.store.get_profile_with_revision("alice")
        lkg = self.store.get_last_known_good("alice")
        self.assertEqual(1, result["profile_revision"])
        self.assertEqual(1, record["profile_revision"])
        self.assertEqual("valid", record["state"])
        self.assertEqual(PROFILE_INTEGRITY_VALID, record["integrity_status"])
        self.assertTrue(record["checksum_valid"])
        self.assertTrue(lkg["checksum_valid"])
        self.assertEqual(1, lkg["profile_revision"])
        self.assertNotIn("password", lkg["snapshot"])
        self.assertNotIn("salt", lkg["snapshot"])
        self.assertNotIn("launch_queue", lkg["snapshot"])

    def test_guarded_creation_rejects_partial_profile_without_persisting(self):
        with self.assertRaises(ProfileValidationError):
            self.store.save_profile_guarded(
                {"username": "alice", "level": 1},
                expected_revision=0,
                source="test.invalid_registration",
                allow_create=True,
            )

        self.assertIsNone(self.store.get_profile_with_revision("alice"))
        self.assertIsNone(self.store.get_last_known_good("alice"))

    def test_legacy_create_rejects_partial_profile_without_persisting(self):
        with self.assertRaises(ProfileValidationError):
            self.store.save_profile({"username": "alice", "level": 1})

        self.assertIsNone(self.store.get_profile_with_revision("alice"))
        self.assertIsNone(self.store.get_last_known_good("alice"))

    def test_legacy_full_update_is_fail_closed_for_existing_profile(self):
        self.store.save_profile(complete_profile())
        before = self.store.get_profile_with_revision("alice")
        candidate = before["profile"]
        candidate["respect"] = 50

        with self.assertRaises(ProfileWriteConflict):
            self.store.save_profile(candidate)

        after = self.store.get_profile_with_revision("alice")
        self.assertEqual(before["profile_revision"], after["profile_revision"])
        self.assertEqual(before["checksum"], after["checksum"])
        self.assertEqual(0, after["profile"]["respect"])

    def test_launch_queue_does_not_mask_or_write_malformed_profile(self):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username,password,salt,profile_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "pw", "", "{truncated", now, now),
            )

        with self.assertRaises(ProfileRecoveryRequired):
            self.store.consume_launch_queue("alice")

        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT profile_json, profile_revision, profile_integrity_status
                FROM users WHERE username = 'alice'
                """
            ).fetchone()
        self.assertEqual("{truncated", row["profile_json"])
        self.assertEqual(0, row["profile_revision"])
        self.assertEqual(PROFILE_INTEGRITY_RECOVERY_REQUIRED, row["profile_integrity_status"])
        self.assertIsNone(self.store.get_last_known_good("alice"))

    def test_password_upgrade_does_not_write_partial_profile(self):
        now = utc_now()
        partial_json = json.dumps({"username": "alice", "password": "pw"})
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username,password,salt,profile_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "pw", "", partial_json, now, now),
            )

        with self.assertRaises(ProfileRecoveryRequired):
            self.store.authenticate("alice", "pw")

        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT password, profile_json, profile_revision,
                       profile_integrity_status
                FROM users WHERE username = 'alice'
                """
            ).fetchone()
        self.assertEqual("pw", row["password"])
        self.assertEqual(partial_json, row["profile_json"])
        self.assertEqual(0, row["profile_revision"])
        self.assertEqual(PROFILE_INTEGRITY_RECOVERY_REQUIRED, row["profile_integrity_status"])
        self.assertIsNone(self.store.get_last_known_good("alice"))

    def test_hashed_authentication_is_fail_closed_for_invalid_schema(self):
        self.create()
        partial = {"username": "alice", "password": "irrelevant"}
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE users
                SET profile_json = ?, profile_checksum = ?,
                    profile_integrity_status = ?
                WHERE username = 'alice'
                """,
                (
                    json.dumps(partial),
                    profile_payload_checksum(partial),
                    PROFILE_INTEGRITY_VALID,
                ),
            )

        with self.assertRaises(ProfileRecoveryRequired):
            self.store.authenticate("alice", "secret-pass")

        record = self.store.get_profile_with_revision("alice")
        self.assertEqual("invalid_schema", record["state"])
        self.assertEqual(
            PROFILE_INTEGRITY_RECOVERY_REQUIRED,
            record["integrity_status"],
        )

    def test_registration_rejects_orphan_canonical_rows_without_mutating_them(self):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO wallet_balances(username,balance,version,updated_at) VALUES(?,?,?,?)",
                ("alice", 999999, 1, now),
            )
            conn.execute(
                """
                INSERT INTO player_apps(username,app_id,app_json,status,version,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "orphan-app", json.dumps({"name": "Orphan"}), "installed", 1, now),
            )

        with self.assertRaises(ProfileWriteConflict):
            self.create()

        self.assertIsNone(self.store.get_profile_with_revision("alice"))
        self.assertTrue(self.store.username_exists("alice"))
        self.assertEqual(
            "canonical_orphan:wallet_balances",
            self.store.identity_reuse_block_reason("alice"),
        )
        with db_connect(self.db_path) as conn:
            balance = conn.execute(
                "SELECT balance FROM wallet_balances WHERE username = ?",
                ("alice",),
            ).fetchone()["balance"]
            app = conn.execute(
                "SELECT app_id FROM player_apps WHERE username = ?",
                ("alice",),
            ).fetchone()["app_id"]
        self.assertEqual(999999, balance)
        self.assertEqual("orphan-app", app)

    def test_deleted_identity_is_tombstoned_and_cannot_be_re_registered(self):
        self.create()
        self.assertTrue(self.store.delete_user("alice"))

        self.assertFalse(self.store.has_user("alice"))
        self.assertTrue(self.store.username_exists("alice"))
        self.assertEqual(
            "identity_tombstoned",
            self.store.identity_reuse_block_reason("alice"),
        )
        with db_connect(self.db_path) as conn:
            tombstone = conn.execute(
                """
                SELECT reason, profile_revision
                FROM deleted_user_tombstones
                WHERE username = ?
                """,
                ("alice",),
            ).fetchone()
        self.assertEqual("account_deleted", tombstone["reason"])
        self.assertEqual(1, tombstone["profile_revision"])

        with self.assertRaises(ProfileWriteConflict):
            self.create(complete_profile("alice", password="replacement"))
        with self.assertRaises(ProfileWriteConflict):
            self.store.save_profile(complete_profile("alice", password="legacy"))
        self.assertFalse(self.store.has_user("alice"))

    def test_stale_writer_loses_cas_and_does_not_change_lkg(self):
        self.create()
        first = self.store.get_profile_with_revision("alice")
        second = self.store.get_profile_with_revision("alice")
        first_candidate = first["profile"]
        first_candidate["respect"] = 5
        applied = self.store.save_profile_guarded(
            first_candidate,
            expected_revision=first["profile_revision"],
            source="test.first_writer",
        )
        lkg_before = self.store.get_last_known_good("alice")

        second_candidate = second["profile"]
        second_candidate["respect"] = 9
        with self.assertRaises(ProfileWriteConflict):
            self.store.save_profile_guarded(
                second_candidate,
                expected_revision=second["profile_revision"],
                source="test.stale_writer",
            )

        current = self.store.get_profile_with_revision("alice")
        lkg_after = self.store.get_last_known_good("alice")
        self.assertEqual(2, applied["profile_revision"])
        self.assertEqual(5, current["profile"]["respect"])
        self.assertEqual(lkg_before["checksum"], lkg_after["checksum"])
        self.assertEqual(lkg_before["profile_revision"], lkg_after["profile_revision"])

    def test_concurrent_independent_semantic_patches_do_not_lose_changes(self):
        self.create()

        def apply(updates, source):
            return self.store.patch_profile_guarded(
                "alice",
                updates,
                source,
                expected_revision=None,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(apply, {"respect": 7}, "test.patch.respect"),
                executor.submit(apply, {"nick": "Alice Prime"}, "test.patch.nick"),
            ]
            results = [future.result() for future in futures]

        current = self.store.get_profile_with_revision("alice")
        self.assertEqual([2, 3], sorted(item["profile_revision"] for item in results))
        self.assertEqual(3, current["profile_revision"])
        self.assertEqual(7, current["profile"]["respect"])
        self.assertEqual("Alice Prime", current["profile"]["nick"])
        self.assertTrue(current["checksum_valid"])

    def test_semantic_patch_honors_optional_expected_revision(self):
        self.create()
        first = self.store.patch_profile_guarded(
            "alice", {"respect": 1}, "test.patch.first", expected_revision=1
        )

        with self.assertRaises(ProfileWriteConflict):
            self.store.patch_profile_guarded(
                "alice", {"nick": "stale"}, "test.patch.stale", expected_revision=1
            )

        current = self.store.get_profile_with_revision("alice")
        self.assertEqual(first["profile_revision"], current["profile_revision"])
        self.assertNotEqual("stale", current["profile"]["nick"])

    def test_precommit_rejection_rolls_back_callback_profile_revision_and_lkg(self):
        self.create()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE precommit_probe(value TEXT NOT NULL)"
            )
        before = self.store.get_profile_with_revision("alice")
        lkg_before = self.store.get_last_known_good("alice")
        candidate = before["profile"]
        candidate["respect"] = 99
        observed = {}

        def reject(*, conn, username, current_revision):
            observed.update({
                "username": username,
                "current_revision": current_revision,
            })
            conn.execute("INSERT INTO precommit_probe(value) VALUES ('must-rollback')")
            raise ProfilePrecommitRejected("session_generation_mismatch")

        with self.assertRaises(ProfilePrecommitRejected):
            self.store.save_profile_guarded(
                candidate,
                expected_revision=before["profile_revision"],
                source="test.precommit",
                precommit_guard=reject,
            )

        after = self.store.get_profile_with_revision("alice")
        lkg_after = self.store.get_last_known_good("alice")
        with db_connect(self.db_path) as conn:
            probe_count = conn.execute("SELECT COUNT(*) FROM precommit_probe").fetchone()[0]
        self.assertEqual("alice", observed["username"])
        self.assertEqual(before["profile_revision"], observed["current_revision"])
        self.assertEqual(0, probe_count)
        self.assertEqual(before["profile_revision"], after["profile_revision"])
        self.assertEqual(before["checksum"], after["checksum"])
        self.assertEqual(0, after["profile"]["respect"])
        self.assertEqual(lkg_before["checksum"], lkg_after["checksum"])

    def test_context_precommit_guard_covers_patch_and_is_not_called_twice(self):
        self.create()
        observed = []

        def guard(*, conn, username, current_revision):
            observed.append((username, current_revision))

        token = set_profile_precommit_guard(guard)
        try:
            result = self.store.patch_profile_guarded(
                "alice",
                {"respect": 2},
                "test.context_guard",
                precommit_guard=guard,
            )
        finally:
            reset_profile_precommit_guard(token)

        self.assertEqual(2, result["profile_revision"])
        self.assertEqual([("alice", 1)], observed)

    def test_invalid_candidate_does_not_overwrite_profile_or_lkg(self):
        self.create()
        record = self.store.get_profile_with_revision("alice")
        lkg_before = self.store.get_last_known_good("alice")
        candidate = record["profile"]
        candidate.pop("security")

        with self.assertRaises(ProfileValidationError):
            self.store.save_profile_guarded(
                candidate,
                expected_revision=record["profile_revision"],
                source="test.invalid_candidate",
            )

        current = self.store.get_profile_with_revision("alice")
        lkg_after = self.store.get_last_known_good("alice")
        self.assertEqual(1, current["profile_revision"])
        self.assertIn("security", current["profile"])
        self.assertEqual(lkg_before["checksum"], lkg_after["checksum"])

    def test_destructive_multi_scope_drop_requires_reset_receipt(self):
        rich = complete_profile(
            level=12,
            hackcoins=9000,
            respect=450,
            exp="8500 / 9000",
            inventory=["one", "two", "three", "four"],
            files={"tools": ["a", "b", "c", "d"], "download": ["x"]},
            apps=["app-a", "app-b", "app-c"],
            hacked=[{"id": index} for index in range(4)],
            operations=[{"id": index} for index in range(4)],
            product_purchases=[{"id": index} for index in range(3)],
            storage_capacity=8192,
            storage_upgrades=[{"id": "storage"}],
        )
        self.create(rich)
        record = self.store.get_profile_with_revision("alice")
        reset = complete_profile()

        with self.assertRaises(ProfileDestructiveWriteRejected):
            self.store.save_profile_guarded(
                reset,
                expected_revision=record["profile_revision"],
                source="test.accidental_reset",
            )

        receipt = {
            "receipt_id": "reset:alice:1",
            "reason": "operator requested reset",
            "authorized_by": "admin",
            "created_at": "2026-08-21T00:00:00Z",
        }
        with self.assertRaises(ProfileDestructiveWriteRejected):
            self.store.save_profile_guarded(
                reset,
                expected_revision=record["profile_revision"],
                source="test.forged_reset",
                reset_receipt=receipt,
            )

        applied = self.store.save_profile_guarded(
            reset,
            expected_revision=record["profile_revision"],
            source="admin.explicit_reset",
            reset_receipt=receipt,
        )
        self.assertEqual(2, applied["profile_revision"])
        self.assertEqual(1, applied["profile"]["level"])
        self.assertEqual(12, self.store.get_last_known_good("alice")["snapshot"]["level"])

    def test_legal_progression_purchase_and_wallet_spend_pass(self):
        self.create()
        WalletBalanceStore(self.db_path).debit(
            "alice",
            300,
            transaction_key="test:purchase:1",
            reason="test.purchase",
        )
        record = self.store.get_profile_with_revision("alice")
        candidate = record["profile"]
        candidate["level"] = 2
        candidate["respect"] = 20
        candidate["exp"] = "250 / 2000"
        candidate["hackcoins"] = 5  # stale mirror; canonical wallet wins.
        candidate["product_purchases"] = [{"purchase_id": "purchase:1"}]

        result = self.store.save_profile_guarded(
            candidate,
            expected_revision=record["profile_revision"],
            source="test.legal_progression",
        )

        self.assertEqual(2, result["profile_revision"])
        self.assertEqual(700, result["profile"]["hackcoins"])
        self.assertEqual(1, len(result["profile"]["product_purchases"]))

    def test_guarded_save_overlays_existing_canonical_wallet_and_inventory(self):
        self.create()
        now = utc_now()
        WalletBalanceStore(self.db_path).recovery_set_balance(
            "alice",
            777,
            transaction_key="test:recovery:canonical-wallet-777",
            reason="test.recovery",
        )
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO player_apps(username,app_id,app_json,status,version,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "canonical-app", json.dumps({"name": "Canonical"}), "installed", 1, now),
            )
            conn.execute(
                """
                INSERT INTO player_tool_files(username,tool_id,app_id,tool_json,version,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "canonical.sh", "canonical-app", json.dumps({"name": "canonical.sh"}), 1, now),
            )
            conn.execute(
                """
                INSERT INTO player_storage(username,capacity,used,unit,modifiers_json,version,updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                ("alice", 4096, 321, "MB", json.dumps({"storage_upgrades": ["disk-1"]}), 1, now),
            )

        record = self.store.get_profile_with_revision("alice")
        stale = record["profile"]
        stale["hackcoins"] = 5
        stale["apps"] = [{"id": "stale-app"}]
        stale["files"]["tools"] = ["stale.sh"]
        stale["storage_capacity"] = 1
        result = self.store.save_profile_guarded(
            stale,
            expected_revision=record["profile_revision"],
            source="test.canonical_overlay",
        )

        saved = result["profile"]
        self.assertEqual(("wallet", "inventory"), result["canonical_overlays"])
        self.assertEqual(777, saved["hackcoins"])
        self.assertEqual(["canonical-app"], [item["id"] for item in saved["apps"]])
        self.assertEqual(["canonical.sh"], [item["tool_id"] for item in saved["files"]["tools"]])
        self.assertEqual(4096, saved["storage_capacity"])
        self.assertEqual(["disk-1"], saved["storage_upgrades"])

        lkg = self.store.get_last_known_good("alice")["snapshot"]
        self.assertNotIn("hackcoins", lkg)
        self.assertNotIn("apps", lkg)
        self.assertNotIn("tools", lkg["files"])

    def test_lkg_strips_nested_credentials_and_geometry(self):
        profile = complete_profile(
            security={
                "password": "nested-secret",
                "token": "nested-token",
                "firewall": True,
            },
            areas=[{"polygon": [[1, 2], [3, 4]]}],
            custom={
                "geometry": {"coordinates": [[1, 2]]},
                "safe": "value",
            },
        )
        self.create(profile)

        snapshot = self.store.get_last_known_good("alice")["snapshot"]
        self.assertNotIn("areas", snapshot)
        self.assertNotIn("password", snapshot["security"])
        self.assertNotIn("token", snapshot["security"])
        self.assertTrue(snapshot["security"]["firewall"])
        self.assertNotIn("geometry", snapshot["custom"])
        self.assertEqual("value", snapshot["custom"]["safe"])

    def test_lkg_checksum_tampering_is_reported(self):
        self.create()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE profile_last_known_good SET snapshot_json = ? WHERE username = ?",
                (json.dumps({"username": "alice", "level": 99}), "alice"),
            )

        self.assertFalse(self.store.get_last_known_good("alice")["checksum_valid"])

    def test_checksum_mismatch_requires_recovery_instead_of_writing(self):
        self.create()
        record = self.store.get_profile_with_revision("alice")
        candidate = record["profile"]
        candidate["respect"] = 1
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile_checksum = 'tampered' WHERE username = 'alice'"
            )

        self.assertFalse(self.store.get_profile_with_revision("alice")["checksum_valid"])
        self.assertEqual(
            "recovery_required",
            self.store.get_profile_with_revision("alice")["state"],
        )
        # Runtime reads trust integrity metadata established by guarded writes;
        # the explicit heavy/audit path detects out-of-band checksum tampering.
        self.assertEqual("alice", self.store.get_profile("alice")["username"])

        with self.assertRaises(ProfileRecoveryRequired):
            self.store.save_profile_guarded(
                candidate,
                expected_revision=record["profile_revision"],
                source="test.checksum_mismatch",
            )
        self.assertEqual(
            PROFILE_INTEGRITY_RECOVERY_REQUIRED,
            self.store.get_profile_with_revision("alice")["integrity_status"],
        )


class ProfileIntegrityBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_profile_bootstrap_"))
        self.db_path = str(self.tmpdir / "legacy.sqlite3")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        now = utc_now()
        valid = complete_profile("valid-user")
        partial = {"username": "partial-user", "level": 7}
        conn.execute(
            "INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("valid-user", "pw", "salt", json.dumps(valid), now, now),
        )
        conn.execute(
            "INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("partial-user", "pw", "salt", json.dumps(partial), now, now),
        )
        conn.execute(
            "INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("broken-user", "pw", "salt", "{truncated", now, now),
        )
        conn.execute(
            "INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("list-user", "pw", "salt", "[]", now, now),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_bootstrap_is_idempotent_and_never_rewrites_profile_json(self):
        conn = sqlite3.connect(self.db_path)
        before = dict(conn.execute("SELECT username, profile_json FROM users"))
        conn.close()

        init_db(self.db_path)
        store = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )
        valid_first = store.get_profile_with_revision("valid-user")
        lkg_first = store.get_last_known_good("valid-user")
        init_db(self.db_path)
        valid_second = store.get_profile_with_revision("valid-user")
        lkg_second = store.get_last_known_good("valid-user")

        conn = sqlite3.connect(self.db_path)
        after = dict(conn.execute("SELECT username, profile_json FROM users"))
        lkg_count = conn.execute(
            "SELECT COUNT(*) FROM profile_last_known_good"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(before, after)
        self.assertEqual(1, valid_first["profile_revision"])
        self.assertEqual("valid", valid_first["state"])
        self.assertEqual(valid_first["profile_revision"], valid_second["profile_revision"])
        self.assertEqual(lkg_first["checksum"], lkg_second["checksum"])
        self.assertEqual(1, lkg_count)

    def test_partial_and_invalid_json_are_recovery_required_without_lkg(self):
        store = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )

        partial = store.get_profile_with_revision("partial-user")
        broken = store.get_profile_with_revision("broken-user")
        root_list = store.get_profile_with_revision("list-user")
        self.assertEqual(PROFILE_INTEGRITY_RECOVERY_REQUIRED, partial["integrity_status"])
        self.assertEqual(PROFILE_INTEGRITY_RECOVERY_REQUIRED, broken["integrity_status"])
        self.assertEqual("invalid_schema", partial["state"])
        self.assertEqual("invalid_json", broken["state"])
        self.assertEqual("invalid_schema", root_list["state"])
        self.assertEqual(0, partial["profile_revision"])
        self.assertEqual(0, broken["profile_revision"])
        self.assertIsNone(store.get_last_known_good("partial-user"))
        self.assertIsNone(store.get_last_known_good("broken-user"))
        self.assertIn("invalid_json", broken["errors"])
        with self.assertRaises(ProfileRecoveryRequired):
            store.get_profile("partial-user")
        with self.assertRaises(ProfileRecoveryRequired):
            store.get_profile("broken-user")


if __name__ == "__main__":
    unittest.main()
