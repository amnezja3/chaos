import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import TerritoryStore


def target(label="Node", lat=52.1, lng=21.1):
    return {
        "target_id": f"map:{lat}:{lng}:{label}",
        "label": label,
        "name": label,
        "lat": lat,
        "lng": lng,
        "lon": lng,
        "stationary": True,
        "security": {"firewall": False},
        "security_version": 0,
    }


class CapturedObjectStoreTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        handle.close()
        self.path = Path(handle.name)
        self.store = TerritoryStore(str(self.path))

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{self.path}{suffix}")
            if candidate.exists():
                try:
                    candidate.unlink()
                except PermissionError:
                    pass

    def test_security_update_is_versioned_and_does_not_rebuild(self):
        saved = self.store.save_captured_target("alice", target())
        first = self.store.update_captured_target_security(
            "alice", saved, {"firewall": True}, expected_version=0
        )
        stale = self.store.update_captured_target_security(
            "alice", saved, {"firewall": False}, expected_version=0
        )
        self.assertTrue(first["ok"])
        self.assertEqual(first["security_version"], 1)
        self.assertFalse(stale["ok"])
        self.assertEqual(stale["reason"], "stale_version")

    def test_abandon_is_atomic_and_queues_one_durable_job(self):
        saved = self.store.save_captured_target("alice", target())
        first = self.store.abandon_captured_target(
            "alice", saved, saved["target_id"]
        )
        second = self.store.abandon_captured_target(
            "alice", saved, saved["target_id"]
        )
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "not_found")
        claimed = self.store.claim_rebuild_job("test-worker")
        self.assertEqual(claimed["job_id"], first["job_id"])
        self.assertEqual(claimed["owner_username"], "alice")


class CapturedObjectEndpointTest(unittest.TestCase):
    def _client(self):
        client = run.app.test_client()
        with client.session_transaction() as session:
            session["user"] = "alice"
        return client

    def test_security_read_is_store_only(self):
        item = target()
        with patch.object(run.territory_store, "get_captured_target", return_value=item), \
                patch.object(run.territory_target_ownership_store, "get", return_value=None), \
                patch.object(run, "sync_session_profile") as sync, \
                patch.object(run, "rebuild_player_areas_with_territory_delta") as rebuild:
            response = self._client().post("/target-security-status", json={
                "target_id": item["target_id"], "lat": item["lat"], "lng": item["lng"]
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["security_version"], 0)
        sync.assert_not_called()
        rebuild.assert_not_called()

    def test_abandon_returns_queued_without_rebuild(self):
        item = target()
        result = {"ok": True, "job_id": "territory_rebuild_1", "target": item}
        with patch.object(run.territory_store, "get_captured_target", return_value=item), \
                patch.object(run.territory_store, "abandon_captured_target", return_value=result), \
                patch.object(run, "record_map_target_delta"), \
                patch.object(run.user_store, "get_profile") as profile_read, \
                patch.object(run.user_store, "save_profile") as profile_write, \
                patch.object(run, "rebuild_player_areas_with_territory_delta") as rebuild:
            response = self._client().post("/api/map/captured-object/abandon", json={
                "target_id": item["target_id"], "confirm": True
            })
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.get_json()["queued"])
        profile_read.assert_not_called()
        profile_write.assert_not_called()
        rebuild.assert_not_called()


class CapturedObjectFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_right_click_opens_local_two_action_menu(self):
        self.assertIn("showCapturedObjectMenu(e.containerPoint.x", self.source)
        self.assertIn("function showCapturedObjectMenu", self.source)
        self.assertIn("function abandonCapturedObject", self.source)

    def test_security_read_is_deduplicated_per_target(self):
        self.assertIn("capturedObjectSecurityRequests.get(targetId)", self.source)
        self.assertIn("capturedObjectSecurityRequests.set(targetId, requestPromise)", self.source)
        self.assertIn("context-menu-clean[data-target-id]", self.source)

    def test_legacy_hacked_dom_marker_uses_captured_object_menu(self):
        marker_binding = self.source[self.source.index("document.querySelectorAll('.marker-hacked')"):]
        marker_binding = marker_binding[:marker_binding.index("if (typeof window.bootMapInitialState")]
        self.assertIn("showCapturedObjectMenu", marker_binding)
        self.assertNotIn("showMenuForHacked(e.pageX", marker_binding)


class ConflictTargetIdentityTest(unittest.TestCase):
    def test_coordinate_identity_survives_display_label_change(self):
        conflict_target = target(label="Canonical pillar")
        with patch.object(run, "safe_player_areas", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", return_value=[]), \
                patch.object(
                    run,
                    "contested_targets_from_active_conflicts",
                    return_value=[conflict_target],
                ):
            found = run.find_contested_target(
                "alice", conflict_target["lat"], conflict_target["lng"], "POI-AB12"
            )
        self.assertEqual(found, conflict_target)

    def test_stable_target_id_wins_over_changed_marker_position_and_label(self):
        conflict_target = {
            **target(label="Canonical pillar", lat=52.1, lng=21.1),
            "target_id": "pillar:stable-1",
            "stable_conflict_id": "conflict-1",
        }
        with patch.object(run, "safe_player_areas", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", return_value=[]), \
                patch.object(
                    run,
                    "contested_targets_from_active_conflicts",
                    return_value=[conflict_target],
                ):
            found = run.find_contested_target(
                "alice", 52.1004, 21.1004, "POI-AB12",
                target_id="pillar:stable-1", conflict_id="conflict-1",
            )
        self.assertEqual(found, conflict_target)


if __name__ == "__main__":
    unittest.main()
