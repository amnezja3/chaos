import shutil
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

from session_generation_store import (
    SessionGenerationStateError,
    SessionGenerationStore,
    generation_digest,
    lineage_digest,
    username_digest,
)


class SessionGenerationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_session_lineage_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.store = SessionGenerationStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_only_domain_separated_hashes_are_persisted(self):
        lineage = "raw-lineage-secret-never-persist"
        generation = "raw-generation-secret-never-persist"
        username = "Alice"
        self.store.activate(
            lineage,
            generation,
            username,
            reason="test_activation",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT lineage_hash, generation_hash, username_hash, last_reason
                FROM session_generation_lineages
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(lineage_digest(lineage), row[0])
        self.assertEqual(generation_digest(generation), row[1])
        self.assertEqual(username_digest(username), row[2])
        self.assertEqual("test_activation", row[3])
        persisted = " ".join(str(value) for value in row)
        self.assertNotIn(lineage, persisted)
        self.assertNotIn(generation, persisted)
        self.assertNotIn(username, persisted)

    def test_replacement_is_atomic_and_stale_revoke_cannot_revoke_current(self):
        self.store.activate("lineage-a", "generation-a", "alice", reason="login_a")
        replacement = self.store.activate(
            "lineage-a", "generation-b", "alice", reason="login_b"
        )

        self.assertEqual(2, replacement["revision"])
        self.assertFalse(
            self.store.revoke(
                "lineage-a", "generation-a", reason="delayed_logout_a"
            )
        )
        self.assertTrue(
            self.store.is_current("lineage-a", "generation-b", "alice")
        )
        with self.assertRaises(SessionGenerationStateError) as rejected:
            self.store.assert_current(
                "lineage-a", "generation-a", "alice"
            )
        self.assertEqual("generation_replaced", rejected.exception.reason)

    def test_new_login_replaces_previous_lineage_for_same_account(self):
        self.store.activate("browser-one", "generation-one", "alice", reason="login")
        replacement = self.store.activate(
            "browser-two", "generation-two", "alice", reason="login"
        )

        self.assertFalse(
            self.store.is_current("browser-one", "generation-one", "alice")
        )
        self.assertTrue(
            self.store.is_current("browser-two", "generation-two", "alice")
        )
        self.assertEqual(2, replacement["account_revision"])
        with self.assertRaises(SessionGenerationStateError) as rejected:
            self.store.assert_current(
                "browser-one", "generation-one", "alice"
            )
        self.assertEqual("lineage_replaced", rejected.exception.reason)

        # Delayed logout A is CAS-safe and cannot clear ownership B.
        self.assertFalse(
            self.store.revoke("browser-one", "generation-one", reason="logout")
        )
        self.assertTrue(
            self.store.is_current("browser-two", "generation-two", "alice")
        )

    def test_account_revocation_covers_every_lineage_but_not_other_users(self):
        self.store.activate("alice-one", "alice-a", "alice", reason="login")
        self.store.activate("alice-two", "alice-b", "alice", reason="login")
        self.store.activate("bob-one", "bob-a", "bob", reason="login")

        revoked = self.store.revoke_all_by_username(
            "alice",
            reason="account_deleted",
        )

        self.assertEqual(1, revoked)
        self.assertFalse(self.store.is_current("alice-one", "alice-a", "alice"))
        self.assertFalse(self.store.is_current("alice-two", "alice-b", "alice"))
        self.assertTrue(self.store.is_current("bob-one", "bob-a", "bob"))

    def test_concurrent_logins_serialize_account_revision_and_one_wins(self):
        self.store.activate("browser-a", "generation-a", "alice", reason="login")
        barrier = Barrier(2)

        def login(browser):
            barrier.wait()
            return self.store.activate(
                browser,
                f"generation-{browser}",
                "alice",
                reason="concurrent_login",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(login, ("browser-b", "browser-c")))

        self.assertEqual({2, 3}, {item["account_revision"] for item in results})
        winner = max(results, key=lambda item: item["account_revision"])
        winner_browser = next(
            browser
            for browser in ("browser-b", "browser-c")
            if lineage_digest(browser) == winner["lineage_hash"]
        )
        loser_browser = "browser-c" if winner_browser == "browser-b" else "browser-b"
        self.assertTrue(self.store.is_current(
            winner_browser, f"generation-{winner_browser}", "alice"
        ))
        self.assertFalse(self.store.is_current(
            loser_browser, f"generation-{loser_browser}", "alice"
        ))


if __name__ == "__main__":
    unittest.main()
