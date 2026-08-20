import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import TerritoryStore, TerritoryTargetOwnershipStore


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

    def test_recaptured_ordinary_target_gets_a_new_rebuild_job(self):
        first_capture = self.store.save_captured_target("alice", target())
        first = self.store.abandon_captured_target(
            "alice", first_capture, first_capture["target_id"]
        )
        self.store.finish_rebuild_job(
            first["job_id"],
            "test-worker",
            ok=True,
        ) if self.store.claim_rebuild_job("test-worker") else None

        second_capture = self.store.save_captured_target("alice", target())
        second = self.store.abandon_captured_target(
            "alice", second_capture, second_capture["target_id"]
        )

        self.assertTrue(second["ok"])
        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertNotEqual(first["capture_record_id"], second["capture_record_id"])
        claimed = self.store.claim_rebuild_job("second-worker")
        self.assertEqual(claimed["job_id"], second["job_id"])

    def test_operator_can_enqueue_recovery_for_already_removed_target(self):
        queued = self.store.enqueue_rebuild_job("alice", reason="operator_visibility_recovery")
        claimed = self.store.claim_rebuild_job("test-worker")
        self.assertEqual(claimed["job_id"], queued["job_id"])
        self.assertEqual(claimed["reason"], "operator_visibility_recovery")

    def test_capture_batch_is_all_or_nothing_when_one_cas_mismatches(self):
        ownership = TerritoryTargetOwnershipStore(str(self.path))
        first = self.store.save_captured_target("bob", target("First", 52.1, 21.1))
        second = self.store.save_captured_target("bob", target("Second", 52.2, 21.2))
        ownership.capture("seed:first", first["target_id"], "bob", "bob", first)
        ownership.capture("seed:second", second["target_id"], "bob", "bob", second)

        result = ownership.capture_batch("cluster:atomic", "alice", [
            {"target_id": first["target_id"], "expected_owner_username": "bob", "target": first},
            {"target_id": second["target_id"], "expected_owner_username": "mallory", "target": second},
        ])

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "batch_cas_mismatch")
        self.assertEqual(ownership.get(first["target_id"])["owner_username"], "bob")
        self.assertEqual(ownership.get(second["target_id"])["owner_username"], "bob")
        self.assertEqual({item["label"] for item in self.store.list_captured_targets("alice")}, set())
        self.assertEqual(
            {item["label"] for item in self.store.list_captured_targets("bob")},
            {"First", "Second"},
        )


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

    def test_territory_control_abandon_uses_the_same_canonical_queue(self):
        item = target()
        result = {"ok": True, "job_id": "territory_rebuild_tc", "target": item}
        installed = {
            "username": "alice",
            "apps": [{"id": "territoryControl", "type": "pro-system-tool"}],
        }
        with patch.object(run, "territory_control_load_profile", return_value=installed), \
                patch.object(run.territory_store, "get_captured_target", return_value=item), \
                patch.object(run.territory_store, "abandon_captured_target", return_value=result) as abandon, \
                patch.object(run.territory_store, "remove_captured_target") as legacy_remove, \
                patch.object(run, "record_map_target_delta"), \
                patch.object(run, "rebuild_player_areas_with_territory_delta") as rebuild:
            response = self._client().post("/api/ghost-control/territory/abandon", json={
                "target_id": item["target_id"],
                "lat": item["lat"],
                "lng": item["lng"],
                "label": item["label"],
                "confirm": True,
            })
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.get_json()["queued"])
        abandon.assert_called_once()
        legacy_remove.assert_not_called()
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

    def test_abandon_uses_ghost_confirmation_and_removes_local_marker(self):
        self.assertIn("window.parent.blacknetDecisionDialog", self.source)
        self.assertNotIn("window.confirm(`Porzuci", self.source)
        self.assertIn("removeAbandonedCapturedObject(menuObj, sourceMarker)", self.source)
        self.assertIn("removeMapLayerSafe(sourceMarker)", self.source)

    def test_worker_completion_delta_recovers_abandoned_territory_geometry(self):
        self.assertIn("territory_publication:${territoryReason}", self.source)
        self.assertIn("window.requestTerritorySnapshotRecovery", self.source)


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

    def test_final_capture_refreshes_stale_version_from_active_conflict(self):
        stale = {
            **target(), "target_mode": "territory_contest",
            "target_id": "pillar:1", "conflict_id": "conflict:1",
            "contest_owner_username": "bob", "ownership_version": 2,
            "security": {"firewall": True},
        }
        current = {
            **stale, "expected_owner_username": "bob", "ownership_version": 4,
            "node_role": "pillar",
        }
        with patch.object(run, "find_contested_target", return_value=current), \
                patch.object(
                    run.territory_target_ownership_store, "get",
                    return_value={"owner_username": "bob", "ownership_version": 4},
                ):
            refreshed = run.refresh_active_contested_capture_identity("alice", stale)
        self.assertEqual(refreshed["ownership_version"], 4)
        self.assertEqual(refreshed["expected_owner_username"], "bob")
        self.assertTrue(refreshed["security"]["firewall"])

    def test_final_capture_does_not_refresh_owner_mismatch(self):
        stale = {
            **target(), "target_mode": "territory_contest",
            "target_id": "pillar:1", "conflict_id": "conflict:1",
            "contest_owner_username": "bob", "ownership_version": 2,
        }
        current = {**stale, "expected_owner_username": "bob", "ownership_version": 4}
        with patch.object(run, "find_contested_target", return_value=current), \
                patch.object(
                    run.territory_target_ownership_store, "get",
                    return_value={"owner_username": "charlie", "ownership_version": 4},
                ):
            refreshed = run.refresh_active_contested_capture_identity("alice", stale)
        self.assertEqual(refreshed["ownership_version"], 2)

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
