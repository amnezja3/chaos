import shutil
import tempfile
import unittest
from pathlib import Path

from database import (
    ProfileWriteConflict,
    UserStore,
    WalletBalanceStore,
    db_connect,
    dumps_json,
    hash_password,
    init_db,
    utc_now,
)


class UserStoreCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_user_credentials_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        init_db(self.db_path)
        password_hash, salt = hash_password("secret-pass")
        profile = {
            "username": "robot",
            "password": password_hash,
            "salt": salt,
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
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username, password, salt, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("robot", password_hash, salt, dumps_json(profile), utc_now(), utc_now()),
            )
        self.store = UserStore(self.db_path, seed_path=str(self.tmpdir / "missing.json"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_save_sanitized_profile_preserves_credentials(self):
        record = self.store.get_profile_with_revision("robot")
        sanitized = record["profile"]
        sanitized.pop("password", None)
        sanitized.pop("salt", None)
        sanitized["level"] = 2

        self.store.save_profile_guarded(
            sanitized,
            expected_revision=record["profile_revision"],
            source="test.credentials.sanitized",
        )

        self.assertTrue(self.store.authenticate("robot", "secret-pass"))
        self.assertFalse(self.store.authenticate("robot", "wrong-pass"))
        restored = self.store.get_profile("robot")
        self.assertTrue(restored.get("password"))
        self.assertTrue(restored.get("salt"))
        self.assertEqual(restored["level"], 2)

    def test_late_profile_save_preserves_ghostnetwork_reward_history(self):
        stale_record = self.store.get_profile_with_revision("robot")
        rewarded = stale_record["profile"]
        rewarded["ghostnetwork_reward_history"] = [{
            "reward_key": "ghost-reward-1",
            "reward_type": "part_discovered",
            "rsp": 12,
            "source": "ghostnetwork",
        }]
        self.store.save_profile_guarded(
            rewarded,
            expected_revision=stale_record["profile_revision"],
            source="test.ghost_reward",
        )

        stale = stale_record["profile"]
        stale["level"] = 2
        with self.assertRaises(ProfileWriteConflict):
            self.store.save_profile_guarded(
                stale,
                expected_revision=stale_record["profile_revision"],
                source="test.stale_profile",
            )

        restored = self.store.get_profile("robot")
        self.assertEqual(
            [item["reward_key"] for item in restored["ghostnetwork_reward_history"]],
            ["ghost-reward-1"],
        )


class UserStoreVersionedSeedCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_versioned_user_seed_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        seed_path = Path(__file__).resolve().parents[1] / "static" / "users.json"
        self.store = UserStore(self.db_path, seed_path=str(seed_path))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_real_seed_creates_valid_lkg_and_canonical_wallet_without_template_merge(self):
        profiles = self.store.list_profiles()
        self.assertEqual(9, len(profiles))
        wallet = WalletBalanceStore(self.db_path)

        for profile in profiles:
            username = profile["username"]
            record = self.store.get_profile_with_revision(username)
            lkg = self.store.get_last_known_good(username)
            self.assertEqual("valid", record["state"], username)
            self.assertTrue(record["checksum_valid"], username)
            self.assertGreaterEqual(record["profile_revision"], 1, username)
            self.assertTrue(lkg["checksum_valid"], username)
            self.assertEqual(
                int(record["profile"].get("hackcoins") or 0),
                wallet.get_balance(username),
                username,
            )

        self.assertTrue(self.store.authenticate("admin", "1234"))


if __name__ == "__main__":
    unittest.main()
