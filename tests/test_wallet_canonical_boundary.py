import json
import shutil
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import database
from database import (
    PROFILE_INTEGRITY_RECOVERY_REQUIRED,
    PlayerInventoryStore,
    ProfileWriteConflict,
    UserStore,
    WalletBalanceStore,
    WalletIdempotencyConflict,
    WalletInsufficientFunds,
    WalletMutationRejected,
    WalletNotInitialized,
    WalletStore,
    db_connect,
    init_db,
    utc_now,
)


def complete_profile(username, balance):
    return {
        "username": username,
        "password": "secret-pass",
        "salt": "seed",
        "nick": username.title(),
        "email": f"{username}@example.test",
        "level": 1,
        "hackcoins": balance,
        "respect": 0,
        "exp": "0 / 1000",
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "operations": [],
        "targets": [],
        "system_messages": [],
    }


class WalletCanonicalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_wallet_boundary_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.users = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )
        self.create("alice", 100)
        self.create("bob", 40)
        self.wallet = WalletBalanceStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def create(self, username, balance):
        return self.users.save_profile_guarded(
            complete_profile(username, balance),
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )

    def table_counts(self):
        with db_connect(self.db_path) as conn:
            return {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "wallet_balances",
                    "wallet_balance_events",
                    "wallet_ledger",
                    "wallet_transactions",
                )
            }

    def test_registration_bootstraps_wallet_and_rejects_orphan_identity(self):
        self.assertEqual(100, self.wallet.get_balance("alice"))
        self.assertEqual(1, self.wallet.get_state("alice")["version"])
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO wallet_balances(username,balance,version,updated_at) "
                "VALUES(?,?,?,?)",
                ("charlie", 999999, 8, now),
            )
            conn.execute(
                """
                INSERT INTO wallet_ledger
                    (ledger_id,username,event_type,amount_delta,balance_after,
                     source,source_id,peer_username,note,dedupe_key,
                     payload_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "orphan-ledger", "charlie", "orphan", 999999, 999999,
                    "orphan", "", "", "", "orphan-key", "{}", now,
                ),
            )

        with self.assertRaises(ProfileWriteConflict):
            self.create("charlie", 25)
        self.assertEqual(0, self.wallet.get_balance("charlie"))

    def test_legacy_transaction_schema_gets_additive_idempotency_key(self):
        legacy_path = str(self.tmpdir / "legacy-wallet.sqlite3")
        conn = sqlite3.connect(legacy_path)
        conn.execute(
            """
            CREATE TABLE wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_username TEXT NOT NULL,
                to_username TEXT NOT NULL,
                amount INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO wallet_transactions"
            "(from_username,to_username,amount,note,created_at) VALUES(?,?,?,?,?)",
            ("old-a", "old-b", 5, "legacy", utc_now()),
        )
        conn.commit()
        conn.close()

        init_db(legacy_path)

        with db_connect(legacy_path) as conn:
            columns = {
                row["name"] for row in conn.execute(
                    "PRAGMA table_info(wallet_transactions)"
                ).fetchall()
            }
            row = conn.execute(
                "SELECT transaction_key FROM wallet_transactions"
            ).fetchone()
            index = conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name='idx_wallet_transactions_key'"
            ).fetchone()
        self.assertIn("transaction_key", columns)
        self.assertEqual("", row["transaction_key"])
        self.assertIn("WHERE transaction_key != ''", index["sql"])

    def test_get_balance_and_mirror_are_pure_canonical_projection(self):
        before = self.table_counts()
        before_state = self.wallet.get_state("alice")
        self.assertEqual(
            100,
            self.wallet.get_balance("alice", fallback_profile={"hackcoins": 999}),
        )
        projection = {"username": "alice", "hackcoins": 999}
        self.wallet.mirror_profile("alice", projection)
        self.assertEqual(100, projection["hackcoins"])
        self.assertEqual(0, self.wallet.get_balance("missing", {"hackcoins": 700}))
        self.assertEqual(before, self.table_counts())
        self.assertEqual(before_state, self.wallet.get_state("alice"))
        with db_connect(self.db_path) as conn:
            self.assertIsNone(conn.execute(
                "SELECT 1 FROM wallet_balances WHERE username = 'missing'"
            ).fetchone())

    def test_apply_delta_replay_is_idempotent_and_versioned(self):
        first = self.wallet.credit(
            "alice", 25, "credit:1", reason="reward", expected_version=1
        )
        replay = self.wallet.credit(
            "alice", 25, "credit:1", reason="reward", expected_version=1
        )
        debit = self.wallet.debit("alice", 15, "debit:1", reason="purchase")

        self.assertTrue(first["applied"])
        self.assertEqual(125, first["balance"])
        self.assertEqual(2, first["version"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(2, replay["version"])
        self.assertEqual(110, debit["balance"])
        self.assertEqual(3, debit["version"])
        with db_connect(self.db_path) as conn:
            event_count = conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events "
                "WHERE username='alice' AND transaction_key IN ('credit:1','debit:1')"
            ).fetchone()[0]
            ledger_count = conn.execute(
                "SELECT COUNT(*) FROM wallet_ledger "
                "WHERE username='alice' AND source_id IN ('credit:1','debit:1')"
            ).fetchone()[0]
        self.assertEqual(2, event_count)
        self.assertEqual(2, ledger_count)

    def test_reused_delta_key_with_other_amount_is_rejected(self):
        self.wallet.credit("alice", 5, "same-key")
        with self.assertRaises(WalletIdempotencyConflict):
            self.wallet.credit("alice", 6, "same-key")
        self.assertEqual(105, self.wallet.get_balance("alice"))

    def test_missing_insufficient_and_zero_do_not_partially_write(self):
        before = self.table_counts()
        with self.assertRaises(WalletInsufficientFunds):
            self.wallet.debit("alice", 101, "too-much")
        with self.assertRaises(WalletNotInitialized):
            self.wallet.credit("missing", 1, "missing-credit")
        self.assertEqual(before, self.table_counts())
        zero = self.wallet.apply_delta("alice", 0, "zero")
        after_zero = self.table_counts()

        self.assertFalse(zero["applied"])
        self.assertEqual(100, zero["balance"])
        self.assertEqual(before["wallet_balances"], after_zero["wallet_balances"])
        self.assertEqual(before["wallet_transactions"], after_zero["wallet_transactions"])
        self.assertEqual(
            before["wallet_balance_events"] + 1,
            after_zero["wallet_balance_events"],
        )
        self.assertEqual(before["wallet_ledger"] + 1, after_zero["wallet_ledger"])

    def test_debit_up_to_zero_persists_receipt_without_changing_balance(self):
        first = self.wallet.debit_up_to("alice", 150, "drain:1")
        after_first = self.table_counts()
        second = self.wallet.debit_up_to("alice", 20, "drain:2")
        after_zero_receipt = self.table_counts()
        self.wallet.credit("alice", 50, "credit:after-zero")
        replay = self.wallet.debit_up_to("alice", 20, "drain:2")

        self.assertEqual(-100, first["amount_delta"])
        self.assertEqual(0, first["balance"])
        self.assertFalse(second["applied"])
        self.assertEqual(0, second["balance"])
        self.assertEqual(
            after_first["wallet_balance_events"] + 1,
            after_zero_receipt["wallet_balance_events"],
        )
        self.assertEqual(
            after_first["wallet_ledger"] + 1,
            after_zero_receipt["wallet_ledger"],
        )
        self.assertTrue(replay["duplicate"])
        self.assertEqual(0, replay["balance"])
        self.assertEqual(50, self.wallet.get_balance("alice"))

    def test_zero_debit_up_to_transfer_receipt_survives_later_credit(self):
        self.wallet.debit("alice", 100, "drain:all")
        zero = self.wallet.transfer(
            "alice",
            "bob",
            10,
            transaction_key="transfer:zero",
            debit_up_to=True,
        )
        self.wallet.credit("alice", 20, "credit:later")
        replay = self.wallet.transfer(
            "alice",
            "bob",
            10,
            transaction_key="transfer:zero",
            debit_up_to=True,
        )

        self.assertFalse(zero["applied"])
        self.assertEqual(0, zero["amount"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(0, replay["amount"])
        self.assertEqual(20, self.wallet.get_balance("alice"))
        self.assertEqual(40, self.wallet.get_balance("bob"))
        with db_connect(self.db_path) as conn:
            self.assertEqual(
                1,
                conn.execute(
                    "SELECT COUNT(*) FROM wallet_transactions "
                    "WHERE transaction_key='transfer:zero'"
                ).fetchone()[0],
            )

    def test_transfer_is_atomic_sum_preserving_and_replay_safe(self):
        before_profile = self.users.get_profile_with_revision("alice")
        first = self.wallet.transfer(
            "alice", "bob", 30,
            transaction_key="transfer:1",
            note="test",
        )
        counts_after_first = self.table_counts()
        replay = self.wallet.transfer(
            "alice", "bob", 30,
            transaction_key="transfer:1",
            note="test",
        )
        after_profile = self.users.get_profile_with_revision("alice")

        self.assertTrue(first["applied"])
        self.assertEqual(70, first["source_balance"])
        self.assertEqual(70, first["target_balance"])
        self.assertEqual(140, self.wallet.get_balance("alice") + self.wallet.get_balance("bob"))
        self.assertEqual(2, first["source_version"])
        self.assertEqual(2, first["target_version"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(counts_after_first, self.table_counts())
        self.assertEqual(before_profile["profile_revision"], after_profile["profile_revision"])
        self.assertEqual(before_profile["checksum"], after_profile["checksum"])
        self.assertEqual(before_profile["profile"], after_profile["profile"])
        with db_connect(self.db_path) as conn:
            transfer_count = conn.execute(
                "SELECT COUNT(*) FROM wallet_transactions "
                "WHERE transaction_key='transfer:1'"
            ).fetchone()[0]
            transfer_events = conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events "
                "WHERE transaction_key IN ('transfer:1:out','transfer:1:in')"
            ).fetchone()[0]
        self.assertEqual(1, transfer_count)
        self.assertEqual(2, transfer_events)

    def test_transfer_key_conflict_and_insufficient_leave_both_sides_unchanged(self):
        self.wallet.transfer(
            "alice", "bob", 10, transaction_key="transfer:key", note="same"
        )
        before = self.table_counts()
        balances = (self.wallet.get_balance("alice"), self.wallet.get_balance("bob"))
        with self.assertRaises(WalletIdempotencyConflict):
            self.wallet.transfer(
                "alice", "bob", 11,
                transaction_key="transfer:key",
                note="same",
            )
        with self.assertRaises(WalletInsufficientFunds):
            self.wallet.transfer(
                "alice", "bob", 1000,
                transaction_key="transfer:insufficient",
            )
        self.assertEqual(balances, (
            self.wallet.get_balance("alice"), self.wallet.get_balance("bob")
        ))
        self.assertEqual(before, self.table_counts())

    def test_transfer_rolls_back_balances_events_ledger_and_transaction(self):
        before = self.table_counts()
        original = database._wallet_record_ledger_with_conn

        def fail_recipient(conn, **kwargs):
            if kwargs.get("username") == "bob" and kwargs.get("source_id") == "transfer:rollback":
                raise RuntimeError("injected ledger failure")
            return original(conn, **kwargs)

        with patch(
            "database._wallet_record_ledger_with_conn",
            side_effect=fail_recipient,
        ):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.wallet.transfer(
                    "alice", "bob", 20,
                    transaction_key="transfer:rollback",
                )

        self.assertEqual(100, self.wallet.get_balance("alice"))
        self.assertEqual(40, self.wallet.get_balance("bob"))
        self.assertEqual(before, self.table_counts())

    def test_concurrent_transfers_preserve_sum_and_nonnegative_balances(self):
        jobs = []
        for index in range(30):
            jobs.append(("alice", "bob", f"parallel:a:{index}"))
            jobs.append(("bob", "alice", f"parallel:b:{index}"))

        def transfer(job):
            source, target, key = job
            return self.wallet.transfer(
                source, target, 1, transaction_key=key
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(transfer, jobs))

        alice = self.wallet.get_balance("alice")
        bob = self.wallet.get_balance("bob")
        self.assertTrue(all(item["applied"] for item in results))
        self.assertGreaterEqual(alice, 0)
        self.assertGreaterEqual(bob, 0)
        self.assertEqual(140, alice + bob)
        with db_connect(self.db_path) as conn:
            self.assertEqual(
                60,
                conn.execute(
                    "SELECT COUNT(*) FROM wallet_transactions "
                    "WHERE transaction_key LIKE 'parallel:%'"
                ).fetchone()[0],
            )

    def test_legacy_set_balance_is_closed_and_explicit_recovery_is_idempotent(self):
        with self.assertRaises(WalletMutationRejected):
            self.wallet.set_balance("alice", 999, "legacy")
        first = self.wallet.recovery_set_balance(
            "alice", 55, "recovery:alice:1", expected_version=1
        )
        replay = self.wallet.recovery_set_balance(
            "alice", 55, "recovery:alice:1", expected_version=1
        )
        self.assertTrue(first["applied"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(55, self.wallet.get_balance("alice"))
        self.assertEqual(2, self.wallet.get_state("alice")["version"])

    def test_existing_consistent_ledger_is_attested_without_duplicate_seed(self):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM profile_store_migrations "
                "WHERE migration_id=? AND username='alice'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            )
            conn.execute("DELETE FROM wallet_ledger WHERE username='alice'")
            conn.execute("DELETE FROM wallet_balance_events WHERE username='alice'")
            conn.execute(
                "UPDATE wallet_balances SET balance=100,version=7,updated_at=? "
                "WHERE username='alice'",
                (now,),
            )
            conn.execute(
                """
                INSERT INTO wallet_ledger
                    (ledger_id,username,event_type,amount_delta,balance_after,
                     source,source_id,peer_username,note,dedupe_key,
                     payload_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "legacy-ledger", "alice", "legacy.seed", 100, 100,
                    "legacy", "seed", "", "", "legacy:seed", "{}", now,
                ),
            )
            conn.execute(
                """
                INSERT INTO wallet_balance_events
                    (event_id,username,transaction_key,amount_delta,balance,
                     version,reason,created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    "legacy-event", "alice", "legacy:event", 100, 100,
                    7, "legacy.seed", now,
                ),
            )

        init_db(self.db_path)
        init_db(self.db_path)

        with db_connect(self.db_path) as conn:
            ledger = conn.execute(
                "SELECT COUNT(*) AS count, SUM(amount_delta) AS total "
                "FROM wallet_ledger WHERE username='alice'"
            ).fetchone()
            events = conn.execute(
                "SELECT COUNT(*) AS count, SUM(amount_delta) AS total "
                "FROM wallet_balance_events WHERE username='alice'"
            ).fetchone()
            receipt_count = conn.execute(
                "SELECT COUNT(*) FROM profile_store_migrations "
                "WHERE migration_id=? AND username='alice' AND status='applied'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            ).fetchone()[0]
        self.assertEqual((1, 100), (ledger["count"], ledger["total"]))
        self.assertEqual((1, 100), (events["count"], events["total"]))
        self.assertEqual(1, receipt_count)
        self.assertEqual(7, self.wallet.get_state("alice")["version"])

    def test_missing_balance_uses_consistent_mature_evidence_before_profile(self):
        self.create("mature", 1000)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM profile_store_migrations "
                "WHERE migration_id=? AND username='mature'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            )
            conn.execute("DELETE FROM wallet_balances WHERE username='mature'")
            conn.execute("DELETE FROM wallet_ledger WHERE username='mature'")
            conn.execute("DELETE FROM wallet_balance_events WHERE username='mature'")
            for index, delta in enumerate((4000, 200), start=1):
                balance_after = 4000 if index == 1 else 4200
                conn.execute(
                    """
                    INSERT INTO wallet_ledger
                        (ledger_id,username,event_type,amount_delta,balance_after,
                         source,source_id,peer_username,note,dedupe_key,
                         payload_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        f"mature-ledger-{index}", "mature", "legacy", delta,
                        balance_after, "legacy", str(index), "", "",
                        f"mature-ledger-key-{index}", "{}", now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO wallet_balance_events
                        (event_id,username,transaction_key,amount_delta,balance,
                         version,reason,created_at)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        f"mature-event-{index}", "mature", f"legacy:{index}",
                        delta, balance_after, index + 1, "legacy", now,
                    ),
                )

        init_db(self.db_path)

        state = WalletBalanceStore(self.db_path).get_state("mature")
        with db_connect(self.db_path) as conn:
            ledger = conn.execute(
                "SELECT COUNT(*) AS count,SUM(amount_delta) AS total "
                "FROM wallet_ledger WHERE username='mature'"
            ).fetchone()
            events = conn.execute(
                "SELECT COUNT(*) AS count,SUM(amount_delta) AS total "
                "FROM wallet_balance_events WHERE username='mature'"
            ).fetchone()
        self.assertEqual(4200, state["balance"])
        self.assertEqual(3, state["version"])
        self.assertEqual((2, 4200), (ledger["count"], ledger["total"]))
        self.assertEqual((2, 4200), (events["count"], events["total"]))

    def test_divergent_mature_evidence_blocks_migration_without_mutation(self):
        self.create("divergent", 1000)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM profile_store_migrations "
                "WHERE migration_id=? AND username='divergent'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            )
            conn.execute("DELETE FROM wallet_balances WHERE username='divergent'")
            conn.execute("DELETE FROM wallet_ledger WHERE username='divergent'")
            conn.execute("DELETE FROM wallet_balance_events WHERE username='divergent'")
            conn.execute(
                """
                INSERT INTO wallet_ledger
                    (ledger_id,username,event_type,amount_delta,balance_after,
                     source,source_id,peer_username,note,dedupe_key,
                     payload_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "divergent-ledger", "divergent", "legacy", 4200, 4200,
                    "legacy", "ledger", "", "", "divergent-ledger-key",
                    "{}", now,
                ),
            )
            conn.execute(
                """
                INSERT INTO wallet_balance_events
                    (event_id,username,transaction_key,amount_delta,balance,
                     version,reason,created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    "divergent-event", "divergent", "legacy:event", 4100,
                    4100, 9, "legacy", now,
                ),
            )

        init_db(self.db_path)
        init_db(self.db_path)

        with db_connect(self.db_path) as conn:
            balance = conn.execute(
                "SELECT 1 FROM wallet_balances WHERE username='divergent'"
            ).fetchone()
            ledger = conn.execute(
                "SELECT COUNT(*) AS count,SUM(amount_delta) AS total "
                "FROM wallet_ledger WHERE username='divergent'"
            ).fetchone()
            events = conn.execute(
                "SELECT COUNT(*) AS count,SUM(amount_delta) AS total "
                "FROM wallet_balance_events WHERE username='divergent'"
            ).fetchone()
            migration = conn.execute(
                "SELECT status,error_json FROM profile_store_migrations "
                "WHERE migration_id=? AND username='divergent'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            ).fetchone()
        self.assertIsNone(balance)
        self.assertEqual((1, 4200), (ledger["count"], ledger["total"]))
        self.assertEqual((1, 4100), (events["count"], events["total"]))
        self.assertEqual("blocked", migration["status"])
        self.assertIn("wallet_canonical_evidence_conflict", migration["error_json"])
        with self.assertRaises(WalletNotInitialized) as balance_error:
            WalletBalanceStore(self.db_path).get_balance("divergent")
        self.assertEqual("migration_blocked", balance_error.exception.reason)
        with self.assertRaises(WalletNotInitialized):
            WalletStore(self.db_path).get_wallet("divergent")

    def test_existing_balance_with_divergent_evidence_is_fail_closed(self):
        self.create("existing-divergent", 100)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM profile_store_migrations "
                "WHERE migration_id=? AND username='existing-divergent'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            )
            conn.execute(
                """
                INSERT INTO wallet_ledger
                    (ledger_id,username,event_type,amount_delta,balance_after,
                     source,source_id,peer_username,note,dedupe_key,
                     payload_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "existing-divergent-extra", "existing-divergent", "legacy",
                    1, 101, "legacy", "extra", "", "",
                    "existing-divergent-extra-key", "{}", now,
                ),
            )

        init_db(self.db_path)
        wallet = WalletBalanceStore(self.db_path)
        with db_connect(self.db_path) as conn:
            before = {
                "balance": conn.execute(
                    "SELECT balance FROM wallet_balances "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
                "events": conn.execute(
                    "SELECT COUNT(*) FROM wallet_balance_events "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
                "ledger": conn.execute(
                    "SELECT COUNT(*) FROM wallet_ledger "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
            }
            migration = conn.execute(
                "SELECT status FROM profile_store_migrations "
                "WHERE migration_id=? AND username='existing-divergent'",
                (database.WALLET_CANONICAL_MIGRATION_ID,),
            ).fetchone()

        self.assertEqual("blocked", migration["status"])
        for read in (
            lambda: wallet.get_balance("existing-divergent"),
            lambda: wallet.get_state("existing-divergent"),
            lambda: WalletStore(self.db_path).get_wallet("existing-divergent"),
        ):
            with self.assertRaises(WalletNotInitialized) as error:
                read()
            self.assertEqual("migration_blocked", error.exception.reason)
        with self.assertRaises(WalletNotInitialized) as error:
            wallet.credit(
                "existing-divergent",
                5,
                "blocked-existing:credit",
            )
        self.assertEqual("migration_blocked", error.exception.reason)
        with self.assertRaises(WalletNotInitialized) as error:
            wallet.recovery_set_balance(
                "existing-divergent",
                100,
                "blocked-existing:recovery",
                reason="test.explicit_recovery_without_attestation",
            )
        self.assertEqual("migration_blocked", error.exception.reason)

        with db_connect(self.db_path) as conn:
            after = {
                "balance": conn.execute(
                    "SELECT balance FROM wallet_balances "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
                "events": conn.execute(
                    "SELECT COUNT(*) FROM wallet_balance_events "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
                "ledger": conn.execute(
                    "SELECT COUNT(*) FROM wallet_ledger "
                    "WHERE username='existing-divergent'"
                ).fetchone()[0],
            }
        self.assertEqual(before, after)

    def test_invalid_profile_is_never_bootstrapped_into_wallet(self):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username,password,salt,profile_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("broken", "pw", "", json.dumps({"username": "broken"}), now, now),
            )

        init_db(self.db_path)

        with db_connect(self.db_path) as conn:
            user = conn.execute(
                "SELECT profile_integrity_status FROM users WHERE username='broken'"
            ).fetchone()
            wallet = conn.execute(
                "SELECT 1 FROM wallet_balances WHERE username='broken'"
            ).fetchone()
        self.assertEqual(PROFILE_INTEGRITY_RECOVERY_REQUIRED, user[0])
        self.assertIsNone(wallet)

    def test_inventory_mirror_does_not_seed_on_read(self):
        inventory = PlayerInventoryStore(self.db_path)
        profile = complete_profile("alice", 100)
        profile.update({
            "apps": [{"id": "legacy-app", "name": "Legacy"}],
            "files": {"tools": ["legacy.sh"]},
            "storage_capacity": 4096,
        })

        inventory.mirror_profile("alice", profile)

        self.assertEqual(["legacy-app"], [app["id"] for app in profile["apps"]])
        self.assertEqual(["legacy.sh"], profile["files"]["tools"])
        with db_connect(self.db_path) as conn:
            counts = tuple(conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE username='alice'"
            ).fetchone()[0] for table in (
                "player_apps", "player_tool_files", "player_storage"
            ))
        self.assertEqual((0, 0, 0), counts)

    def test_empty_initialized_inventory_overlays_stale_profile_without_resurrection(self):
        inventory = PlayerInventoryStore(self.db_path)
        canonical_seed = complete_profile("alice", 100)
        canonical_seed.update({
            "apps": [],
            "files": {"tools": [], "download": []},
            "storage_capacity": 4096,
            "storage_used": 0,
            "storage_unit": "MB",
        })
        seeded = inventory.seed_from_profile("alice", canonical_seed)
        self.assertTrue(seeded["initialized"])
        self.assertEqual([], seeded["apps"])
        self.assertEqual([], seeded["files"]["tools"])

        stale_profile = complete_profile("alice", 100)
        stale_profile.update({
            "apps": [{"id": "resurrected-app", "name": "Stale"}],
            "files": {
                "tools": ["resurrected.sh"],
                "download": ["keep-noncanonical-scope.bin"],
            },
        })

        inventory.mirror_profile("alice", stale_profile)
        inventory.mirror_profile("alice", stale_profile)

        self.assertEqual([], stale_profile["apps"])
        self.assertEqual([], stale_profile["files"]["tools"])
        self.assertEqual(
            ["keep-noncanonical-scope.bin"],
            stale_profile["files"]["download"],
        )
        self.assertEqual(4096, stale_profile["storage_capacity"])
        with db_connect(self.db_path) as conn:
            counts = tuple(conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE username='alice'"
            ).fetchone()[0] for table in (
                "player_apps", "player_tool_files", "player_storage"
            ))
        self.assertEqual((0, 0, 1), counts)

    def test_wallet_store_delegates_without_profile_json_writes(self):
        before_alice = self.users.get_profile_with_revision("alice")
        before_bob = self.users.get_profile_with_revision("bob")
        result = WalletStore(self.db_path).transfer(
            "alice", "bob", 5, "delegated",
            transaction_key="wallet-store:1",
        )
        after_alice = self.users.get_profile_with_revision("alice")
        after_bob = self.users.get_profile_with_revision("bob")

        self.assertEqual(95, result["balance"])
        self.assertEqual(45, result["recipient_balance"])
        self.assertEqual(before_alice["checksum"], after_alice["checksum"])
        self.assertEqual(before_bob["checksum"], after_bob["checksum"])
        self.assertEqual(before_alice["profile_revision"], after_alice["profile_revision"])
        self.assertEqual(before_bob["profile_revision"], after_bob["profile_revision"])

    def test_wallet_store_get_wallet_is_read_only(self):
        store = WalletStore(self.db_path)
        before = self.table_counts()

        wallet = store.get_wallet("alice")

        self.assertEqual(100, wallet["balance"])
        self.assertTrue(wallet["ledger_audit"]["ok"])
        self.assertEqual(before, self.table_counts())


if __name__ == "__main__":
    unittest.main()
