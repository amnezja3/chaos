import copy
import unittest
from unittest.mock import Mock, call, patch

import run
from database import ProfileWriteConflict


def profile_record(revision, **updates):
    profile = {
        "username": "alice",
        "level": 3,
        "respect": 7,
        "hacked": [],
        "aimed_target": {},
        "system_messages": [],
    }
    profile.update(copy.deepcopy(updates))
    return {"profile": profile, "profile_revision": revision}


class TerritoryProfileProjectionCasTest(unittest.TestCase):
    def test_capture_owner_loss_does_not_write_profile(self):
        target = dict(target_id='pillar-1', lat=52., lng=21.)
        with patch.object(run.player_target_runtime_store, 'clear_if_matches', return_value=True) as clear, \
             patch.object(run, 'load_profile_write_record', side_effect=AssertionError('heavy read')), \
             patch.object(run.user_store, 'patch_profile_guarded', side_effect=AssertionError('heavy write')):
            result = run.project_lost_territory_after_capture('alice', target)
        self.assertTrue(result['applied'])
        self.assertTrue(result['runtime_cleared'])
        clear.assert_called_once_with('alice', target, source='territory_capture_owner_loss')

    def test_capture_owner_loss_store_failure_is_retryable(self):
        with patch.object(run.player_target_runtime_store, 'clear_if_matches', side_effect=RuntimeError('busy')):
            with self.assertRaises(RuntimeError):
                run.project_lost_territory_after_capture('alice', dict(target_id='pillar-1'))

    def test_controlled_recovery_conflict_consolidation_has_no_reward_or_profile_side_effect(self):
        conflict = {
            "conflict_id": "conflict-recovery",
            "participants": ["pies1", "trolu2"],
            "last_actor_username": "trolu2",
            "source_event": "sprint_130_11_rollback",
            "conflict_version": 2,
        }
        published = {
            "ok": True,
            "changed": True,
            "pending_newer": False,
            "snapshot": {"conflict": {**conflict, "status": "resolved"}},
        }
        with patch.object(
            run.territory_conflict_store, "claim_rebuild",
            return_value={"conflict": conflict, "processing_version": 2},
        ), patch.object(
            run.user_store, "get_profile",
            side_effect=AssertionError("controlled conflict must not read participant profiles"),
        ) as profile_read, patch.object(
            run.territory_conflict_store, "reconcile_rebuild_pillars"
        ), patch.object(
            run.territory_conflict_store, "publish_rebuild", return_value=published
        ), patch.object(
            run, "record_territory_conflict_delta"
        ), patch.object(
            run, "settle_conflict_resolution_reward",
            side_effect=AssertionError("controlled rollback must not create a reward"),
        ) as reward, patch.object(
            run, "resolve_territory_encirclements_after_change",
            side_effect=AssertionError("controlled rollback must not resolve encirclements"),
        ) as encirclement:
            result = run.consolidate_conflict_rebuild(
                "conflict-recovery",
                prebuilt_areas=[],
                prebuilt_detection_plans=[],
                rebuild_participants=True,
                run_encirclement=True,
            )

        self.assertTrue(result["ok"])
        profile_read.assert_not_called()
        reward.assert_not_called()
        encirclement.assert_not_called()

    def test_controlled_recovery_resolution_is_never_rewarded(self):
        snapshot = {
            "conflict": {
                "conflict_id": "conflict-recovery",
                "participants": ["pies1", "trolu2"],
                "last_actor_username": "trolu2",
                "source_event": "sprint_130_11_rollback",
                "status": "resolved",
            }
        }
        store = Mock()

        result = run.settle_conflict_resolution_reward(
            snapshot, progression_store=store
        )

        self.assertEqual("controlled_recovery_no_reward", result["reason"])
        store.ensure.assert_not_called()
        store.settle_strategic.assert_not_called()

    def test_controlled_recovery_conflict_skips_every_profile_projection(self):
        conflict = {
            "participants": ["pies1", "trolu2"],
            "last_actor_username": "trolu2",
            "source_event": "sprint_130_11_recovery",
        }
        with patch.object(
            run.territory_conflict_store, "get_by_key", return_value=conflict
        ), patch.object(
            run.territory_store, "list_player_areas", return_value=[]
        ) as area_read, patch.object(
            run, "load_profile_write_record",
            side_effect=AssertionError("controlled recovery conflict must be profile-neutral"),
        ) as profile_read, patch.object(
            run.user_store, "patch_profile_guarded",
            side_effect=AssertionError("controlled recovery conflict must not write profiles"),
        ) as profile_write:
            summaries = run.finalize_conflict_rebuild_profiles("conflict-recovery")

        self.assertEqual(["pies1", "trolu2"], [item["username"] for item in summaries])
        self.assertTrue(all(item["profile_projection_skipped"] for item in summaries))
        self.assertEqual(2, area_read.call_count)
        profile_read.assert_not_called()
        profile_write.assert_not_called()

    def test_controlled_recovery_rebuild_skips_heavy_profile_and_lkg_projection(self):
        claim = {
            "job_id": "recovery-job-1",
            "owner_username": "trolu2",
            "reason": "sprint_130_11_recovery",
            "target": {
                "recovery_contract": "sprint_130_11",
                "recovery_plan_id": "trollu2_recovery_test",
                "recovery_subject": "trolu2",
                "recovery_level": 50,
                "target_ids": ["pillar-1"],
            },
        }
        with patch.object(
            run.territory_store, "claim_rebuild_job", return_value=claim
        ), patch.object(
            run, "load_profile_write_record",
            side_effect=AssertionError("heavy profile read must not run"),
        ) as profile_read, patch.object(
            run, "rebuild_player_areas_with_territory_delta", return_value=[]
        ) as rebuild, patch.object(
            run.territory_store, "list_player_areas", return_value=[]
        ), patch.object(
            run, "detect_territory_conflicts", return_value=[]
        ), patch.object(
            run.territory_store, "list_captured_targets",
            side_effect=AssertionError("profile projection must not run"),
        ) as captured_read, patch.object(
            run.user_store, "patch_profile_guarded",
            side_effect=AssertionError("LKG/profile write must not run"),
        ) as profile_write, patch.object(
            run.player_target_runtime_store, "clear_if_matches",
            side_effect=AssertionError("recovery job is not an abandon action"),
        ) as target_clear, patch.object(
            run.territory_store, "finish_rebuild_job", return_value=True
        ) as finish:
            result = run.process_territory_rebuild_job("worker")

        self.assertTrue(result["ok"])
        self.assertTrue(result["controlled_recovery"])
        rebuild.assert_called_once_with(
            "trolu2", 50, reason="sprint_130_11_recovery"
        )
        profile_read.assert_not_called()
        captured_read.assert_not_called()
        profile_write.assert_not_called()
        target_clear.assert_not_called()
        finish.assert_called_once_with("recovery-job-1", "worker", ok=True)

    def test_rebuild_worker_uses_only_canonical_context(self):
        with patch.object(run.territory_store, 'claim_rebuild_job', return_value=dict(job_id='job-1', owner_username='alice', target={})), \
             patch.object(run.territory_progression_receipt_store.progression, 'get', return_value=dict(level=3)), \
             patch.object(run.player_target_runtime_store, 'clear_if_matches', return_value=True), \
             patch.object(run, 'rebuild_player_areas_with_territory_delta', return_value=[]), \
             patch.object(run.territory_store, 'list_player_areas', return_value=[]), \
             patch.object(run, 'detect_territory_conflicts', return_value=[]), \
             patch.object(run, 'load_profile_write_record', side_effect=AssertionError('heavy read')), \
             patch.object(run.user_store, 'patch_profile_guarded', side_effect=AssertionError('heavy write')), \
             patch.object(run.territory_store, 'finish_rebuild_job') as finish:
            result = run.process_territory_rebuild_job('worker')
        self.assertTrue(result['ok'], result)
        finish.assert_called_once_with('job-1', 'worker', ok=True)

    def test_conflict_finalize_refreshes_only_scoped_stats(self):
        with patch.object(run.territory_conflict_store, 'get_by_key', return_value=dict(participants=['alice'])), \
             patch.object(run.territory_progression_receipt_store.progression, 'get', return_value=dict(level=3)), \
             patch.object(run.territory_store, 'list_player_areas', return_value=[]), \
             patch.object(run, 'refresh_canonical_territory_stats', return_value=dict(level=3)) as refresh, \
             patch.object(run, 'load_profile_write_record', side_effect=AssertionError('heavy read')), \
             patch.object(run, 'notify_encircled_area_owners'):
            result = run.finalize_conflict_rebuild_profiles('conflict-1')
        refresh.assert_called_once_with('alice', [])
        self.assertEqual(result, [dict(username='alice', areas=0, levels_gained=0)])

    def test_clear_aimed_uses_canonical_selection_only(self):
        target = dict(target_id='pillar-1')
        with patch.object(run.player_target_runtime_store, 'clear_if_matches', return_value=True) as clear, \
             patch.object(run, 'load_profile_write_record', side_effect=AssertionError('heavy read')):
            self.assertTrue(run.clear_aimed_target_if_matches('alice', target))
        clear.assert_called_once_with('alice', target, source='clear_aimed_target')


if __name__ == "__main__":
    unittest.main()
