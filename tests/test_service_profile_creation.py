import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import ProfileValidationError, UserStore


def complete_template():
    return {
        "username": "template",
        "password": "template-secret",
        "salt": "template-salt",
        "nick": "Template",
        "email": "template@example.test",
        "avatar": "/static/images/default_avatar.png",
        "level": 1,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "clan": "",
        "fraction": {},
        "inventory": [],
        "files": {
            "tools": [],
            "download": [],
            "pictures": [],
            "social-media": [],
            "projects": [],
        },
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "operations": [],
        "targets": [],
    }


class FakeResources:
    def __init__(self, template):
        self.template = copy.deepcopy(template)

    def get(self, key, seed_path=None, default=None):
        if key == "user_template":
            return copy.deepcopy(self.template)
        return copy.deepcopy(default)


class ServiceProfileCreationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_service_profiles_"))
        self.store = UserStore(
            str(self.tmpdir / "game.sqlite3"),
            seed_path=str(self.tmpdir / "missing-users.json"),
        )
        self.resources = FakeResources(complete_template())
        self.original_store = run.user_store
        self.original_resources = run.resources_store
        self.original_testing = run.app.config.get("TESTING")
        run.user_store = self.store
        run.resources_store = self.resources
        run.app.config.update(TESTING=True)

    def tearDown(self):
        run.user_store = self.original_store
        run.resources_store = self.original_resources
        run.app.config["TESTING"] = self.original_testing
        shutil.rmtree(self.tmpdir)

    def test_dev_admin_is_created_from_full_template_and_can_log_in(self):
        with patch.object(
            run,
            "authenticate_user",
            side_effect=self.store.authenticate,
        ), patch.object(run, "begin_authenticated_session") as begin_session:
            response = run.app.test_client().post(
                "/",
                data={"username": "admin", "password": "1234"},
            )

        self.assertEqual(302, response.status_code)
        begin_session.assert_called_once_with("admin")
        record = self.store.get_profile_with_revision("admin")
        self.assertEqual("valid", record["state"])
        self.assertEqual(1, record["profile_revision"])
        self.assertTrue(record["profile"]["dev_account"])
        self.assertGreaterEqual(record["profile"]["level"], 50)
        self.assertTrue(self.store.authenticate("admin", "1234"))

    def test_existing_dev_admin_uses_guarded_revision_update(self):
        original = complete_template()
        original.update({"username": "admin", "password": "old-password"})
        self.store.save_profile_guarded(
            original,
            expected_revision=0,
            source="test.admin_seed",
            allow_create=True,
        )

        run.ensure_dev_admin_account()

        record = self.store.get_profile_with_revision("admin")
        self.assertEqual(2, record["profile_revision"])
        self.assertTrue(record["profile"]["dev_account"])
        self.assertTrue(self.store.authenticate("admin", "1234"))

    def test_purchase_account_is_full_guarded_create_and_idempotent(self):
        profile = run.ensure_purchase_account_profile("service-payee")
        first = self.store.get_profile_with_revision("service-payee")
        repeated = run.ensure_purchase_account_profile("service-payee")
        second = self.store.get_profile_with_revision("service-payee")

        self.assertEqual("valid", first["state"])
        self.assertEqual(1, first["profile_revision"])
        self.assertEqual(1, second["profile_revision"])
        self.assertEqual("service-payee", profile["username"])
        self.assertEqual("service-payee", repeated["username"])
        self.assertTrue(profile["service_account"])
        self.assertTrue(profile["purchase_account"])
        self.assertEqual(0, profile["hackcoins"])

    def test_service_profile_rejects_partial_template_without_creating_identity(self):
        run.resources_store = FakeResources({"username": "partial"})

        with self.assertRaises(ProfileValidationError):
            run.ensure_purchase_account_profile("broken-payee")

        self.assertFalse(self.store.has_user("broken-payee"))


if __name__ == "__main__":
    unittest.main()
