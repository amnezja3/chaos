import copy
import unittest
from unittest.mock import call, patch

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
