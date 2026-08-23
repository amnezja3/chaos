import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import PlayerMarkedTargetStore, UserStore
from tests.session_generation_fixture import SessionGenerationFixture


def complete_profile(username="alice", targets=None):
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
        "targets": copy.deepcopy(targets or []),
        "market_history": [],
        "product_purchases": [],
        "storage_upgrades": [],
        "ghostnetwork_reward_history": [],
        "risk_events": [],
        "system_messages": [],
        "launch_queue": [],
    }


class PlayerMarkedTargetStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_marked_targets_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        self.user_store = UserStore(
            self.db_path,
            seed_path=str(self.tmpdir / "missing-users.json"),
        )
        self.legacy = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Legacy target",
            "name": "Legacy target",
            "icon": "L",
            "source_type": "shop",
        }
        self.user_store.save_profile_guarded(
            complete_profile(targets=[self.legacy]),
            expected_revision=0,
            source="test.marked_target.create",
            allow_create=True,
        )
        self.store = PlayerMarkedTargetStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_legacy_targets_are_seeded_once_and_store_becomes_authoritative(self):
        first = self.store.list_targets("alice")
        second_seed = self.store.ensure_seeded("alice")
        self.assertEqual(1, len(first))
        self.assertTrue(second_seed["already_seeded"])

        new_target = {
            "lat": 52.3,
            "lng": 21.4,
            "label": "New target",
            "icon": "N",
            "source_type": "office",
        }
        created = self.store.upsert("alice", new_target)
        duplicate = self.store.upsert("alice", new_target)
        self.assertTrue(created["changed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(2, len(self.store.list_targets("alice")))

        # Canonical write does not rewrite the 34 MB-compatible profile path.
        self.assertEqual(
            1,
            len(self.user_store.get_profile("alice")["targets"]),
        )
        # The next unrelated guarded profile write safely refreshes the mirror.
        self.user_store.patch_profile_guarded(
            "alice", {"respect": 1}, source="test.marked_target.overlay"
        )
        mirrored = self.user_store.get_profile("alice")
        self.assertEqual(2, len(mirrored["targets"]))

    def test_capture_removes_matching_mark_without_touching_other_rows(self):
        self.store.list_targets("alice")
        self.store.upsert("alice", {
            "lat": 52.3, "lng": 21.4, "label": "Other", "icon": "O",
        })
        removed = self.store.remove_matching(
            "alice", self.legacy, match_label=False,
        )
        remaining = self.store.list_targets("alice")
        self.assertEqual(1, removed)
        self.assertEqual(["Other"], [item["label"] for item in remaining])


class MarkTargetEndpointHotPathTests(unittest.TestCase):
    def setUp(self):
        self.session_generation = SessionGenerationFixture(
            "chaos_marked_target_session_"
        ).start()
        self.addCleanup(self.session_generation.stop)
        self.client = run.app.test_client()
        self.headers = self.session_generation.authenticate(self.client, "alice")

    def test_mark_target_never_enters_full_profile_or_profile_manager_path(self):
        stored_target = {
            "target_id": "map:52.1:21.2:Fast",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Fast",
            "name": "Fast",
            "icon": "F",
            "source_type": "shop",
            "generated": False,
        }
        with patch.object(run.user_store, "get_profile_identity", return_value={"username": "alice", "clan": "A"}), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("legacy profile sync")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("profile manager")), \
                patch.object(run, "foreign_territory_action_block", return_value=None), \
                patch.object(run.player_marked_target_store, "upsert", return_value={
                    "changed": True, "duplicate": False, "target": stored_target, "version": 1,
                }) as upsert, \
                patch.object(run, "record_map_target_delta") as delta:
            response = self.client.post("/map-action", headers=self.headers, json={
                "action": "mark_target",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Fast",
                "icon": "F",
                "source_type": "shop",
            })

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual("map:52.1:21.2:Fast", response.get_json()["target"]["target_id"])
        upsert.assert_called_once()
        delta.assert_called_once()

    def test_target_snapshot_reads_canonical_store_without_profile(self):
        target = {
            "target_id": "map:52.1:21.2:Fast",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Fast",
            "icon": "F",
        }
        with patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run.player_marked_target_store, "list_targets", return_value=[target]), \
                patch.object(run.territory_store, "list_captured_targets", return_value=[]):
            response = self.client.get("/api/map/target-snapshot", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.get_json()["targets"]))
        self.assertEqual("map:52.1:21.2:Fast", response.get_json()["targets"][0]["target_id"])
        self.assertFalse(response.get_json()["targets"][0]["captured"])

    def test_duplicate_mark_returns_success_without_duplicate_delta(self):
        stored_target = {
            "target_id": "map:52.1:21.2:Fast",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Fast",
            "icon": "F",
        }
        with patch.object(run.user_store, "get_profile_identity", return_value={"username": "alice"}), \
                patch.object(run, "foreign_territory_action_block", return_value=None), \
                patch.object(run.player_marked_target_store, "upsert", return_value={
                    "changed": False, "duplicate": True, "target": stored_target, "version": 1,
                }), \
                patch.object(run, "record_map_target_delta") as delta:
            response = self.client.post("/map-action", headers=self.headers, json={
                "action": "mark_target",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Fast",
                "icon": "F",
            })

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["duplicate"])
        delta.assert_not_called()

    def test_invalid_mark_coordinates_are_controlled_400(self):
        response = self.client.post("/map-action", headers=self.headers, json={
            "action": "mark_target",
            "lat": "not-a-number",
            "lng": 21.2,
            "label": "Fast",
            "icon": "F",
        })
        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_coordinates", response.get_json()["error"])


class MarkedTargetFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_pending_mark_is_independent_from_scan_layers(self):
        clear_start = self.source.index("function clearScanResultLayers()")
        clear_end = self.source.index("function rememberScanResultLayer", clear_start)
        clear_helper = self.source[clear_start:clear_end]
        self.assertIn("pendingMarkedTargetLayers", clear_helper)
        self.assertNotIn("pendingMarkedTargetLayers.clear", clear_helper)
        self.assertIn("unregisterTargetMarker(layer._scanTarget)", clear_helper)
        self.assertIn("showPendingMarkedTarget", clear_helper)
        self.assertIn("LINKING TARGET...", clear_helper)

    def test_mark_response_settles_pending_and_installs_interactive_marker(self):
        start = self.source.index("async function mapAction(")
        end = self.source.index("const bikeDirectionIcons", start)
        branch = self.source[start:end]
        self.assertIn("pendingMarkedTarget = showPendingMarkedTarget", branch)
        self.assertIn("addInteractiveTargetMarker(", branch)
        self.assertIn("settlePendingMarkedTarget(pendingMarkedTarget, 'success'", branch)
        self.assertIn("settlePendingMarkedTarget(", branch)
        self.assertNotIn("refreshParentToolbarProfile();", branch)
        self.assertNotIn("function mapAction_old", self.source)


if __name__ == "__main__":
    unittest.main()
