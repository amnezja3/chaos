import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import run
from database import (
    UserStore,
    db_connect,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from profileManagment import UserProfileManager


def complete_profile(username="alice", padding=""):
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
        "hot_path_padding": padding,
    }


class FakeResources:
    def __init__(self, profile):
        self.profile = copy.deepcopy(profile)

    def get(self, *_args, **_kwargs):
        return copy.deepcopy(self.profile)


class UserStoreHotPathTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_hot_path_"))
        self.store = UserStore(
            str(self.tmpdir / "game.sqlite3"),
            seed_path=str(self.tmpdir / "missing.json"),
        )
        self.profile = complete_profile(padding="x" * 100_000)
        self.store.save_profile_guarded(
            self.profile,
            expected_revision=0,
            source="test.hot_path.create",
            allow_create=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_runtime_get_profile_does_not_enter_heavy_revision_path(self):
        token = reset_hot_path_metrics()
        try:
            with patch.object(
                self.store,
                "get_profile_with_revision",
                side_effect=AssertionError("runtime read entered heavy integrity path"),
            ):
                profile = self.store.get_profile("alice")
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)

        self.assertEqual("alice", profile["username"])
        self.assertEqual(0, metrics["profile_full_read"])
        self.assertGreater(metrics["profile_bytes"], 100_000)

    def test_guarded_patch_prepares_lkg_before_writer_lock(self):
        original = database._prepare_profile_lkg
        observed = []

        def probe(profile):
            with db_connect(self.store.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                observed.append(True)
                conn.rollback()
            return original(profile)

        with patch.object(database, "_prepare_profile_lkg", side_effect=probe):
            self.store.patch_profile_guarded(
                "alice", {"respect": 7}, source="test.hot_path.patch"
            )

        self.assertEqual([True], observed)
        self.assertEqual(7, self.store.get_profile_with_revision("alice")["profile"]["respect"])

    def test_profile_manager_does_not_scan_all_profiles(self):
        with patch.object(
            self.store,
            "list_profiles",
            side_effect=AssertionError("profile manager scanned all users"),
        ):
            manager = UserProfileManager(
                "alice",
                store=self.store,
                resource_store=FakeResources(self.profile),
            )
        self.assertEqual("alice", manager.get_profile()["username"])


class EndpointHotPathTests(unittest.TestCase):
    def test_aim_target_uses_only_runtime_target_store(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"

        identity = {"username": "alice", "clan": "A"}

        class FakeGhostService:
            def get_active_cycle(self):
                return None

            def on_target_aimed(self, *_args, **_kwargs):
                return {"ok": True, "status": "no_active_cycle"}

        def runtime_upsert(_username, target, **_kwargs):
            return {"changed": True, "target": dict(target), "status": "aimed", "version": 1}

        with patch.dict(run.app.config, {"TESTING": True}), \
                patch.object(run.identity_projection_store, "get_identity", return_value=identity), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run.user_store, "patch_profile_guarded", side_effect=AssertionError("full profile write")), \
                patch.object(run, "load_profile_write_record", side_effect=AssertionError("heavy write read")), \
                patch.object(run, "find_contested_target", return_value=None), \
                patch.object(run, "foreign_territory_action_block", return_value=None), \
                patch.object(run, "find_owned_captured_target_for_runtime_target", return_value=None), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value={}), \
                patch.object(run.player_target_runtime_store, "upsert_aimed", side_effect=runtime_upsert), \
                patch.object(run.resources_store, "get", return_value={"firewall": True}), \
                patch.object(run, "get_ghostnetwork_service", return_value=FakeGhostService()), \
                patch.object(run, "record_map_target_delta"):
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1,
                "lng": 21.2,
                "label": "Hot target",
                "target_id": "map:hot-target",
            })

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["target"]["target_id"].startswith("map:"))

    def test_operation_only_gonna_win_does_not_create_profile_manager(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "root"

        profile = {
            "username": "root",
            "apps": [{
                "id": "hot_tool",
                "name": "Hot Tool",
                "map_actions": ["scan_ports"],
                "operation_types": ["scan"],
                "requires_off": [],
                "interferes_with": [],
                "levels": [{"options": []}],
            }],
            "aimed_target": {
                "target_id": "map:hot-target",
                "target_mode": "standard",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Hot target",
                "security": {"firewall": True},
                "actions_allowed": {},
            },
            "operations": [],
            "system_messages": [],
        }

        with patch.dict(run.app.config, {"TESTING": True}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("profile manager in hot path")), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("extra profile read")), \
                patch.object(run, "apply_app_map_actions_to_aimed_target", return_value=(False, [])), \
                patch.object(run, "merge_latest_aimed_target_runtime_state", return_value=profile["aimed_target"]), \
                patch.object(run, "create_missing_operations_for_app_target", return_value=[]):
            response = client.post("/gonna-win", json={
                "app_id": "hot_tool",
                "operation_only": True,
            })

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["operation_only"])

    def test_ghostnetwork_service_is_initialized_once_per_process(self):
        service = object()
        with patch.object(run, "_ghostnetwork_service", None), \
                patch.object(run, "GhostNetworkService", return_value=service) as service_class:
            self.assertIs(service, run.get_ghostnetwork_service())
            self.assertIs(service, run.get_ghostnetwork_service())
        service_class.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
