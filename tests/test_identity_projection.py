import shutil
import tempfile
import unittest
from pathlib import Path

from database import (
    ProfileRecoveryRequired,
    UserCapabilityProjectionStore,
    UserIdentityProjectionStore,
    UserStore,
    db_connect,
    dumps_json,
    hash_password,
    init_db,
    utc_now,
)
from tools.migrate_identity_projection import dry_run


def build_profile(username, *, clan="virex", profession="broker", nick=""):
    password_hash, salt = hash_password("secret-pass")
    return {
        "username": username,
        "password": password_hash,
        "salt": salt,
        "nick": nick or username,
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
        "ghost_clan_code": clan,
        "ghost_profession": profession,
    }


class UserIdentityProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_identity_projection_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.users = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing.json"),
        )
        self.identities = UserIdentityProjectionStore(self.db_path)
        self.capabilities = UserCapabilityProjectionStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_guarded_create_and_patch_update_projection_atomically(self):
        created = self.users.save_profile_guarded(
            build_profile("alice", nick="Alice"),
            expected_revision=0,
            source="test.identity.create",
            allow_create=True,
        )
        identity = self.identities.get_identity("alice")
        self.assertEqual("Alice", identity["display_alias"])
        self.assertEqual("virex", identity["clan_code"])
        self.assertEqual(created["profile_revision"], identity["source_profile_revision"])
        self.assertEqual(created["checksum"], identity["source_profile_checksum"])
        capability = self.capabilities.get_capabilities("alice")
        self.assertEqual(1, capability["level"])
        self.assertEqual(300, capability["action_range"])
        self.assertEqual(18, capability["map_zoom"])

        patched = self.users.patch_profile_guarded(
            "alice",
            {"nick": "Alicja", "ghost_clan_code": "echo_freedom"},
            source="test.identity.patch",
            expected_revision=created["profile_revision"],
        )
        identity = self.identities.get_identity("alice")
        self.assertEqual("Alicja", identity["display_alias"])
        self.assertEqual("echo_freedom", identity["clan_code"])
        self.assertEqual(patched["profile_revision"], identity["source_profile_revision"])

        patched = self.users.patch_profile_guarded(
            "alice",
            {"level": 71, "scan_range_bonus": 300, "map_zoom_bonus": 2},
            source="test.capability.patch",
            expected_revision=patched["profile_revision"],
        )
        capability = self.capabilities.get_capabilities("alice")
        self.assertEqual(71, capability["level"])
        self.assertEqual(2828, capability["action_range"])
        self.assertEqual(20, capability["map_zoom"])
        self.assertEqual(patched["profile_revision"], capability["source_profile_revision"])

    def test_batch_and_recipient_reads_are_bounded_and_indexed(self):
        for username, clan in (("alice", "virex"), ("bob", "virex"), ("eve", "echo_freedom")):
            self.users.save_profile_guarded(
                build_profile(username, clan=clan),
                expected_revision=0,
                source="test.identity.create",
                allow_create=True,
            )

        batch = self.identities.get_identities(["bob", "missing", "alice"], max_items=3)
        self.assertEqual(["bob", "alice"], [item["username"] for item in batch])
        self.assertEqual(
            ["alice", "bob"],
            self.identities.list_recipient_ids("clan", clan_code="virex", limit=3),
        )
        self.assertEqual(
            ["bob", "eve"],
            self.identities.list_recipient_ids(
                "public", after_username="alice", limit=3,
            ),
        )
        self.assertEqual(
            ["eve", "alice"],
            self.identities.list_recipient_ids(
                "owners", owner_ids=["eve", "alice"], limit=2
            ),
        )
        with self.assertRaises(ValueError):
            self.identities.get_identities(["alice", "bob"], max_items=1)

    def test_revision_mismatch_fails_closed(self):
        self.users.save_profile_guarded(
            build_profile("alice"),
            expected_revision=0,
            source="test.identity.create",
            allow_create=True,
        )
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile_revision = profile_revision + 1 WHERE username = ?",
                ("alice",),
            )

        with self.assertRaises(ProfileRecoveryRequired):
            self.identities.get_identity("alice")
        with self.assertRaises(ProfileRecoveryRequired):
            self.capabilities.get_capabilities("alice")
        self.assertEqual([], self.identities.list_recipient_ids("public", limit=10))

    def test_backfill_is_explicit_and_skips_no_valid_rows(self):
        profile = build_profile("legacy")
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username, password, salt, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy",
                    profile["password"],
                    profile["salt"],
                    dumps_json(profile),
                    utc_now(),
                    utc_now(),
                ),
            )
        init_db(self.db_path)
        self.assertIsNone(self.identities.get_identity("legacy"))

        before = Path(self.db_path).read_bytes()
        preview = dry_run(self.db_path, limit=10)
        after = Path(self.db_path).read_bytes()
        self.assertFalse(preview["database_mutated"])
        self.assertEqual(before, after)

        result = self.identities.backfill_page(limit=10)
        self.assertIn("legacy", result["projected"])
        self.assertEqual("legacy", self.identities.get_identity("legacy")["username"])
        self.assertEqual("legacy", self.capabilities.get_capabilities("legacy")["username"])
        with db_connect(self.db_path) as conn:
            revision_before = conn.execute(
                "SELECT profile_revision FROM users WHERE username = 'legacy'"
            ).fetchone()[0]
        retry = self.identities.backfill_page(limit=10)
        self.assertIn("legacy", retry["projected"])
        with db_connect(self.db_path) as conn:
            projection_count = conn.execute(
                "SELECT COUNT(*) FROM user_identity_projection WHERE username = 'legacy'"
            ).fetchone()[0]
            revision_after = conn.execute(
                "SELECT profile_revision FROM users WHERE username = 'legacy'"
            ).fetchone()[0]
        self.assertEqual(1, projection_count)
        self.assertEqual(revision_before, revision_after)


if __name__ == "__main__":
    unittest.main()
