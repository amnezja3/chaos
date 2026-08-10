import shutil
import tempfile
import unittest
from pathlib import Path

from database import UserStore, db_connect, dumps_json, hash_password, init_db, utc_now


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
        sanitized = self.store.get_profile("robot")
        sanitized.pop("password", None)
        sanitized.pop("salt", None)
        sanitized["level"] = 2

        self.store.save_profile(sanitized)

        self.assertTrue(self.store.authenticate("robot", "secret-pass"))
        self.assertFalse(self.store.authenticate("robot", "wrong-pass"))
        restored = self.store.get_profile("robot")
        self.assertTrue(restored.get("password"))
        self.assertTrue(restored.get("salt"))
        self.assertEqual(restored["level"], 2)


if __name__ == "__main__":
    unittest.main()
