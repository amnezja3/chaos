import shutil
import sqlite3
import tempfile
import unittest
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

    def test_two_lineages_for_same_user_remain_independently_current(self):
        self.store.activate("browser-one", "generation-one", "alice", reason="login")
        self.store.activate("browser-two", "generation-two", "alice", reason="login")

        self.assertTrue(
            self.store.is_current("browser-one", "generation-one", "alice")
        )
        self.assertTrue(
            self.store.is_current("browser-two", "generation-two", "alice")
        )
        self.store.revoke("browser-one", "generation-one", reason="logout")
        self.assertFalse(
            self.store.is_current("browser-one", "generation-one", "alice")
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

        self.assertEqual(2, revoked)
        self.assertFalse(self.store.is_current("alice-one", "alice-a", "alice"))
        self.assertFalse(self.store.is_current("alice-two", "alice-b", "alice"))
        self.assertTrue(self.store.is_current("bob-one", "bob-a", "bob"))


if __name__ == "__main__":
    unittest.main()
