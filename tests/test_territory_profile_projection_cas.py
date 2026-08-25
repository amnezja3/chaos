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
    def test_capture_owner_loss_projection_rebases_instead_of_false_409(self):
        target = {
            "target_id": "pillar-1", "lat": 52.1, "lng": 21.2,
            "label": "Conflict Pillar",
        }
        fresh_hacked = [{"target_id": "pillar-2", "lat": 52.2, "lng": 21.3}]
        records = [
            profile_record(30, aimed_target=target, hacked=[target], nick="before"),
            profile_record(31, aimed_target=target, hacked=[target], nick="concurrent"),
        ]
        applied_profile = copy.deepcopy(records[-1]["profile"])
        applied_profile.update({
            "aimed_target": {},
            "hacked": fresh_hacked,
            "captured_targets_source": "sqlite",
        })

        with patch.object(
            run.player_target_runtime_store, "clear_if_matches", return_value=True
        ), patch.object(
            run.territory_store, "list_captured_targets", return_value=fresh_hacked
        ), patch.object(
            run, "load_profile_write_record", side_effect=records
        ), patch.object(
            run.user_store, "patch_profile_guarded",
            side_effect=[
                ProfileWriteConflict("concurrent writer"),
                {"applied": True, "profile": applied_profile, "profile_revision": 32},
            ],
        ) as guarded_patch:
            result = run.project_lost_territory_after_capture("alice", target)

        self.assertTrue(result["applied"])
        self.assertFalse(result["deferred"])
        self.assertTrue(result["runtime_cleared"])
        self.assertEqual(2, guarded_patch.call_count)
        self.assertEqual(
            [item.kwargs["expected_revision"] for item in guarded_patch.call_args_list],
            [30, 31],
        )
        for item in guarded_patch.call_args_list:
            self.assertEqual(
                set(item.args[1]),
                {"aimed_target", "hacked", "captured_targets_source"},
            )
            self.assertNotIn("nick", item.args[1])

    def test_capture_owner_loss_projection_defers_exhausted_cas_after_canonical_commit(self):
        target = {
            "target_id": "pillar-1", "lat": 52.1, "lng": 21.2,
            "label": "Conflict Pillar",
        }
        records = [profile_record(revision, aimed_target=target, hacked=[target])
                   for revision in (40, 41, 42)]

        with patch.object(
            run.player_target_runtime_store, "clear_if_matches", return_value=True
        ), patch.object(
            run.territory_store, "list_captured_targets", return_value=[]
        ), patch.object(
            run, "load_profile_write_record", side_effect=records
        ), patch.object(
            run.user_store, "patch_profile_guarded",
            side_effect=ProfileWriteConflict("busy profile writer"),
        ) as guarded_patch:
            result = run.project_lost_territory_after_capture("alice", target)

        self.assertFalse(result["applied"])
        self.assertTrue(result["deferred"])
        self.assertEqual(3, guarded_patch.call_count)

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

    def test_rebuild_projection_reloads_and_retries_normal_cas_conflict(self):
        abandoned = {"target_id": "target-a", "lat": 52.0, "lng": 21.0}
        fresh = [{"target_id": "target-b", "lat": 52.1, "lng": 21.1}]
        records = [
            profile_record(4, aimed_target=abandoned),
            profile_record(5, aimed_target=abandoned, nick="concurrent-one"),
            profile_record(6, aimed_target=abandoned, nick="concurrent-two"),
        ]
        applied_profile = copy.deepcopy(records[-1]["profile"])
        applied_profile.update({
            "aimed_target": {},
            "hacked": fresh,
            "captured_targets_source": "sqlite",
        })

        with patch.object(
            run.territory_store, "claim_rebuild_job",
            return_value={
                "job_id": "job-1", "owner_username": "alice",
                "target": abandoned, "reason": "abandon",
            },
        ), patch.object(
            run, "load_profile_write_record", side_effect=records
        ), patch.object(
            run.player_target_runtime_store, "clear_if_matches", return_value=True
        ), patch.object(
            run, "rebuild_player_areas_with_territory_delta", return_value=[]
        ), patch.object(
            run.territory_store, "list_player_areas", return_value=[]
        ), patch.object(
            run, "detect_territory_conflicts", return_value=[]
        ), patch.object(
            run.territory_store, "list_captured_targets", return_value=fresh
        ), patch.object(
            run.user_store,
            "patch_profile_guarded",
            side_effect=[
                ProfileWriteConflict("concurrent writer"),
                {"applied": True, "profile": applied_profile, "profile_revision": 7},
            ],
        ) as guarded_patch, patch.object(
            run.territory_store, "finish_rebuild_job", return_value=True
        ) as finish:
            result = run.process_territory_rebuild_job("worker")

        self.assertTrue(result["ok"])
        self.assertEqual(guarded_patch.call_count, 2)
        self.assertEqual(
            [item.kwargs["expected_revision"] for item in guarded_patch.call_args_list],
            [5, 6],
        )
        for item in guarded_patch.call_args_list:
            self.assertEqual(
                set(item.args[1]),
                {"aimed_target", "hacked", "captured_targets_source"},
            )
            self.assertNotIn("nick", item.args[1])
        finish.assert_called_once_with("job-1", "worker", ok=True)

    def test_conflict_finalize_projection_retries_without_full_profile_save(self):
        areas = [{"id": 1, "owner_username": "alice", "vertices": []}]
        fresh = [{"target_id": "target-c"}]
        records = [
            profile_record(10, nick="before"),
            profile_record(11, nick="concurrent-one"),
            profile_record(12, nick="concurrent-two"),
        ]
        applied_profile = copy.deepcopy(records[-1]["profile"])
        applied_profile.update({
            "hacked": fresh,
            "captured_targets_source": "sqlite",
            "territory_stats": {"effective_area": 12.0},
            "exp": "12 m2",
        })

        def refresh(profile, _areas):
            profile["territory_stats"] = {"effective_area": 12.0}
            profile["exp"] = "12 m2"
            return profile

        with patch.object(
            run.territory_conflict_store, "get_by_key",
            return_value={"participants": ["alice"], "last_actor_username": ""},
        ), patch.object(
            run, "load_profile_write_record", side_effect=records
        ), patch.object(
            run.territory_store, "list_player_areas", return_value=areas
        ), patch.object(
            run.territory_store, "list_captured_targets", return_value=fresh
        ), patch.object(
            run, "refresh_territory_stats_snapshot", side_effect=refresh
        ), patch.object(
            run.user_store,
            "patch_profile_guarded",
            side_effect=[
                ProfileWriteConflict("concurrent writer"),
                {"applied": True, "profile": applied_profile, "profile_revision": 13},
            ],
        ) as guarded_patch, patch.object(
            run, "notify_encircled_area_owners"
        ):
            summaries = run.finalize_conflict_rebuild_profiles("conflict-1")

        self.assertEqual(summaries, [{"username": "alice", "areas": 1, "levels_gained": 0}])
        self.assertEqual(guarded_patch.call_count, 2)
        self.assertEqual(
            [item.kwargs["expected_revision"] for item in guarded_patch.call_args_list],
            [11, 12],
        )
        for item in guarded_patch.call_args_list:
            self.assertEqual(
                set(item.args[1]),
                {"hacked", "captured_targets_source", "territory_stats", "exp"},
            )
            self.assertNotIn("nick", item.args[1])

    def test_clear_aimed_projection_has_no_undefined_revision_and_retries(self):
        target = {"target_id": "target-a", "lat": 52.0, "lng": 21.0}
        records = [
            profile_record(20, aimed_target=target),
            profile_record(21, aimed_target=target),
        ]
        with patch.object(
            run.player_target_runtime_store, "clear_if_matches", return_value=False
        ), patch.object(
            run, "load_profile_write_record", side_effect=records
        ), patch.object(
            run.user_store,
            "patch_profile_guarded",
            side_effect=[
                ProfileWriteConflict("concurrent writer"),
                {"applied": True, "profile": profile_record(22)["profile"], "profile_revision": 22},
            ],
        ) as guarded_patch:
            cleared = run.clear_aimed_target_if_matches("alice", target)

        self.assertTrue(cleared)
        self.assertEqual(guarded_patch.call_count, 2)
        self.assertEqual(
            [item.kwargs["expected_revision"] for item in guarded_patch.call_args_list],
            [20, 21],
        )


if __name__ == "__main__":
    unittest.main()
