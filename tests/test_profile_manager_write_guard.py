import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from database import (
    ProfileRecoveryRequired,
    ProfileWriteConflict,
    UserStore,
    db_connect,
    dumps_json,
    init_db,
    utc_now,
)
from profileManagment import UserProfileManager


class FakeResources:
    def __init__(self, template):
        self.template = copy.deepcopy(template)

    def get(self, _key, seed_path=None, default=None):
        return copy.deepcopy(self.template)


def complete_profile(username="alice"):
    return {
        "username": username,
        "password": "secret",
        "salt": "seed",
        "nick": "Alice",
        "email": "alice@example.test",
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


class ProfileManagerWriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_profile_manager_guard_"))
        self.store = UserStore(
            str(self.tmpdir / "game.sqlite3"),
            seed_path=str(self.tmpdir / "missing.json"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_recovery_required_profile_never_reaches_template_sync(self):
        partial = {"username": "alice", "level": 7}
        with db_connect(self.store.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username,password,salt,profile_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                ("alice", "", "", dumps_json(partial), utc_now(), utc_now()),
            )
        init_db(self.store.db_path)
        resources = FakeResources(complete_profile())

        with self.assertRaises(ProfileRecoveryRequired):
            UserProfileManager(
                "alice",
                store=self.store,
                resource_store=resources,
            )

        stored = self.store.get_profile_with_revision("alice")
        self.assertEqual("invalid_schema", stored["state"])
        self.assertEqual(partial, stored["profile"])
        self.assertIsNone(self.store.get_last_known_good("alice"))

    def test_template_sync_uses_guarded_revision(self):
        profile = complete_profile()
        self.store.save_profile_guarded(
            profile,
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )
        template = complete_profile()
        template["new_safe_field"] = []

        manager = UserProfileManager(
            "alice",
            store=self.store,
            resource_store=FakeResources(template),
        )

        record = self.store.get_profile_with_revision("alice")
        self.assertEqual(2, record["profile_revision"])
        self.assertEqual([], record["profile"]["new_safe_field"])
        self.assertEqual(2, manager.profile_revision)

    def test_two_managers_cannot_overwrite_each_other(self):
        profile = complete_profile()
        self.store.save_profile_guarded(
            profile,
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )
        resources = FakeResources(profile)
        first = UserProfileManager(
            "alice", store=self.store, resource_store=resources
        )
        stale = UserProfileManager(
            "alice", store=self.store, resource_store=resources
        )

        first.update_profile({"respect": 5})
        with self.assertRaises(ProfileWriteConflict):
            stale.update_profile({"respect": 9})

        current = self.store.get_profile_with_revision("alice")
        self.assertEqual(5, current["profile"]["respect"])
        self.assertEqual(2, current["profile_revision"])

    def test_manager_forwards_precommit_guard_on_update(self):
        profile = complete_profile()
        self.store.save_profile_guarded(
            profile,
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )
        observed = []

        def guard(*, conn, username, current_revision):
            observed.append((username, current_revision))
            self.assertIsNotNone(conn.execute("SELECT 1").fetchone())

        manager = UserProfileManager(
            "alice",
            store=self.store,
            resource_store=FakeResources(profile),
            precommit_guard=guard,
        )
        manager.update_profile({"respect": 3})

        self.assertEqual([("alice", 1)], observed)

    def test_nullable_current_city_accepts_canonical_travel_city_only(self):
        profile = complete_profile()
        profile["current_city"] = None
        self.store.save_profile_guarded(
            profile,
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )
        resources = FakeResources(profile)

        manager = UserProfileManager(
            "alice", store=self.store, resource_store=resources
        )
        manager.update_profile({"current_city": "Tokio"})

        current = self.store.get_profile_with_revision("alice")
        self.assertEqual("Tokio", current["profile"]["current_city"])
        with self.assertRaises(TypeError):
            UserProfileManager(
                "alice", store=self.store, resource_store=resources
            ).update_profile({"current_city": {"invalid": True}})


if __name__ == "__main__":
    unittest.main()
