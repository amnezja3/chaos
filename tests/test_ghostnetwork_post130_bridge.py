import os
import copy
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import run
from database import (
    GhostNetworkDeltaDeliveryJobStore,
    GhostNetworkTerritoryJobStore,
    ProfileWriteConflict,
)
from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService


class GhostNetworkPost130BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghost-bridge.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=self.repo).ensure_active_cycle()
        self.service = GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
        )
        self.job_store = GhostNetworkTerritoryJobStore(db_path=self.db_path)
        self.delivery_store = GhostNetworkDeltaDeliveryJobStore(db_path=self.db_path)
        self.player = {"player_id": "alice", "username": "alice", "clan_code": "virex"}
        self.target = {
            "target_id": "map:52.1:21.1:bridge", "lat": 52.1, "lng": 21.1,
            "label": "Bridge", "source_type": "shop", "target_mode": "standard", "hackable": True,
        }
        self.service.on_target_aimed(self.player, self.target)
        discovered = self.service.on_target_hacked(self.player, self.target, result={"target_captured": True})
        self.assertEqual(discovered["status"], "discovered")
        self.part = self.repo.find_part_by_target(self.repo.get_active_cycle()["cycle_id"], self.target["target_id"])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def area(owner, version=1):
        return {
            "id": "post130-area", "owner_username": owner, "status": "active",
            "updated_at": f"2026-08-19T00:00:0{version}Z",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.2, "lng": 21.0},
                {"lat": 52.2, "lng": 21.2},
                {"lat": 52.0, "lng": 21.2},
            ],
        }

    def test_canonical_area_publication_drives_contained_active_and_release(self):
        areas = [self.area("foreign-owner", 1)]
        profiles = {
            "foreign-owner": {"username": "foreign-owner", "clan": "sentinel_order"},
            "part-owner": {"username": "part-owner", "clan": self.part["clan_code"]},
        }
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run.user_store, "list_profile_identities", side_effect=lambda: list(profiles.items())), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("foreign-owner", areas, reason="post130_publication")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "contained")

            areas[:] = [self.area("part-owner", 2)]
            run.record_territory_areas_delta("part-owner", areas, reason="post130_owner_changed")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")
            progress = self.service.modules.resolve_machine_progress(
                self.repo.get_active_cycle()["cycle_id"], self.part["machine_code"]
            )
            self.assertEqual(progress["parts_active"], 1)

            areas[:] = []
            run.record_territory_areas_delta("part-owner", areas, reason="post130_release")
            run.process_ghostnetwork_territory_job("test-worker")
            released = self.repo.get_part(self.part["part_id"])
            self.assertEqual(released["status"], "public")
            self.assertEqual(released["territory_id"], "")

    def test_area_publication_carries_live_lifecycle_event_to_delta_bridge(self):
        areas = [self.area("foreign-owner", 1)]
        profiles = {
            "foreign-owner": {"username": "foreign-owner", "clan": "sentinel_order"},
        }
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run.user_store, "list_profile_identities", side_effect=lambda: list(profiles.items())), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta(
                "foreign-owner",
                areas,
                reason="post130_live_containment",
            )
            run.process_ghostnetwork_territory_job("test-worker")

        event_types = []
        while True:
            claim = self.delivery_store.claim("test-delivery-worker")
            if not claim:
                break
            event_types.append(claim["event"].get("event_type"))
            self.delivery_store.advance(
                claim["job_id"], "test-delivery-worker", len(claim["viewers"]), 0,
                len(claim["viewers"]), complete=True,
            )
        self.assertIn("ghost.part_contained", event_types)

    def test_canonical_ghost_clan_profile_is_included_in_territory_publication(self):
        areas = [self.area("foreign-owner", 1)]
        profile = {"ghost_clan_code": "sentinel_order"}
        with patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run.user_store, "list_profile_identities", return_value=[("foreign-owner", profile)]), \
                patch.object(run.user_store, "get_profile", return_value=profile):
            publication = run.build_ghostnetwork_territory_publication()

        self.assertEqual(len(publication), 1)
        self.assertEqual(publication[0]["owner_username"], "foreign-owner")
        self.assertEqual(publication[0]["owner_clan"], "sentinel_order")

    def test_public_reward_event_loads_full_record_before_guarded_save(self):
        identity_projection = {
            "username": "alice",
            "clan": "virex",
            "profession": "broker",
        }
        persisted_profile = {
            "username": "alice",
            "clan": "virex",
            "profession": "broker",
            "level": 37,
            "hackcoins": 84512,
            "respect": 900,
            "apps": [{"id": "established-app"}],
            "tools": [{"id": "established-tool"}],
            "custom_profile_state": {"must": "survive"},
        }
        event = {
            "event_id": "activation:alice:full-profile-regression",
            "event_type": "ghost.part_activated",
            "cycle_id": self.repo.get_active_cycle()["cycle_id"],
            "part_id": self.part["part_id"],
            "player_id": "alice",
            "audience_scope": "public",
            "payload": {"player_id": "alice"},
        }
        service = MagicMock()
        received_profiles = []
        saved_profiles = []
        persisted_record = {
            "profile": dict(persisted_profile),
            "profile_revision": 42,
            "checksum": "profile-checksum",
        }

        def handle_reward(_event, profile, apply):
            self.assertFalse(apply)
            received_profiles.append(profile)
            return {
                "ok": True,
                "created": {"reward": {"reward_id": "reward-full-profile"}},
                "applied": None,
            }

        def project_reward(profile, reward_id):
            self.assertEqual(reward_id, "reward-full-profile")
            profile["respect"] += 5
            return {
                "ok": True,
                "status": "projected",
                "profile_changed": True,
                "requires_finalize": True,
            }

        service.handle_reward_event.side_effect = handle_reward
        service.project_reward_to_profile.side_effect = project_reward
        service.finalize_projected_reward.return_value = {
            "ok": True,
            "status": "applied",
        }
        def capture_guarded_save(record, profile, source):
            saved_profiles.append({
                "record": record,
                "profile": dict(profile),
                "source": source,
            })
            return {"applied": True, "profile_revision": 43}

        with patch.object(
            run.user_store,
            "list_profile_identities",
            return_value=[("alice", identity_projection)],
        ), patch.object(
            run.user_store,
            "get_profile",
            side_effect=AssertionError("identity projection must not load reward profile"),
        ), patch.object(
            run.user_store,
            "save_profile",
            side_effect=AssertionError("legacy full save must not run"),
        ), patch.object(
            run,
            "load_profile_write_record",
            return_value=persisted_record,
        ) as load_record, patch.object(
            run,
            "save_profile_write_record",
            side_effect=capture_guarded_save,
        ) as guarded_save, patch.object(
            run,
            "enqueue_ghostnetwork_event_delta",
            return_value={"ok": True},
        ):
            run.apply_ghostnetwork_runtime_result(service, event)

        load_record.assert_called_once_with("alice")
        guarded_save.assert_called_once()
        self.assertEqual(received_profiles[0]["level"], 37)
        self.assertIs(saved_profiles[0]["record"], persisted_record)
        self.assertEqual(saved_profiles[0]["source"], "ghostnetwork.runtime_reward")
        saved_profile = saved_profiles[0]["profile"]
        self.assertEqual(saved_profile["hackcoins"], 84512)
        self.assertEqual(saved_profile["apps"], [{"id": "established-app"}])
        self.assertEqual(saved_profile["tools"], [{"id": "established-tool"}])
        self.assertEqual(saved_profile["custom_profile_state"], {"must": "survive"})
        self.assertEqual(saved_profile["respect"], 905)
        self.assertNotIn("level", identity_projection)
        service.finalize_projected_reward.assert_called_once_with(
            received_profiles[0],
            reward_id="reward-full-profile",
        )

    def test_reward_cas_failure_stays_pending_and_retry_applies_once(self):
        event = {
            "event_id": "activation:alice:cas-retry",
            "event_type": "ghost.part_activated",
            "cycle_id": self.repo.get_active_cycle()["cycle_id"],
            "part_id": "part-cas-retry",
            "player_id": "alice",
            "clan_code": "virex",
            "audience_scope": "player",
            "payload": {"player_id": "alice", "score": 10},
        }
        durable = {
            "record": {
                "profile": {"username": "alice", "respect": 100},
                "profile_revision": 7,
            },
            "fail_once": True,
        }

        def load_record(_username):
            return {
                **durable["record"],
                "profile": copy.deepcopy(durable["record"]["profile"]),
            }

        def guarded_save(record, profile, _source):
            if durable["fail_once"]:
                durable["fail_once"] = False
                raise ProfileWriteConflict("fault-injected CAS loss")
            durable["record"] = {
                "profile": copy.deepcopy(profile),
                "profile_revision": int(record["profile_revision"]) + 1,
            }
            return {"applied": True, **durable["record"]}

        patches = (
            patch.object(run, "load_profile_write_record", side_effect=load_record),
            patch.object(run, "save_profile_write_record", side_effect=guarded_save),
            patch.object(run, "enqueue_ghostnetwork_event_delta", return_value={"ok": True}),
        )
        with patches[0], patches[1], patches[2]:
            with self.assertRaises(ProfileWriteConflict):
                run.apply_ghostnetwork_runtime_result(self.service, event)
            reward = self.repo.list_rewards(player_id="alice", limit=10)[0]
            self.assertEqual(reward["status"], "pending")
            self.assertEqual(durable["record"]["profile"]["respect"], 100)

            run.apply_ghostnetwork_runtime_result(self.service, event)
            after_retry = copy.deepcopy(durable["record"]["profile"])
            run.apply_ghostnetwork_runtime_result(self.service, event)

        reward = self.repo.get_reward(reward["reward_id"])
        self.assertEqual(reward["status"], "applied")
        self.assertGreater(after_retry["respect"], 100)
        self.assertEqual(durable["record"]["profile"]["respect"], after_retry["respect"])
        self.assertEqual(len(after_retry["ghostnetwork_reward_history"]), 1)
        reputation = self.repo.get_clan_reputation("virex")
        self.assertEqual(reputation["parts_activated"], 1)

    def test_reward_crash_after_profile_save_retries_without_double_rsp(self):
        event = {
            "event_id": "activation:alice:post-save-crash",
            "event_type": "ghost.part_activated",
            "cycle_id": self.repo.get_active_cycle()["cycle_id"],
            "part_id": "part-post-save-crash",
            "player_id": "alice",
            "clan_code": "virex",
            "audience_scope": "player",
            "payload": {"player_id": "alice", "score": 10},
        }
        durable = {
            "profile": {"username": "alice", "respect": 200},
            "revision": 11,
        }

        def load_record(_username):
            return {
                "profile": copy.deepcopy(durable["profile"]),
                "profile_revision": durable["revision"],
            }

        def guarded_save(record, profile, _source):
            durable["profile"] = copy.deepcopy(profile)
            durable["revision"] = int(record["profile_revision"]) + 1
            return {
                "applied": True,
                "profile": copy.deepcopy(profile),
                "profile_revision": durable["revision"],
            }

        with patch.object(run, "load_profile_write_record", side_effect=load_record), \
                patch.object(run, "save_profile_write_record", side_effect=guarded_save), \
                patch.object(run, "enqueue_ghostnetwork_event_delta", return_value={"ok": True}), \
                patch.object(
                    self.service,
                    "finalize_projected_reward",
                    side_effect=RuntimeError("fault-injected post-save crash"),
                ):
            with self.assertRaises(RuntimeError):
                run.apply_ghostnetwork_runtime_result(self.service, event)

        saved_once = copy.deepcopy(durable["profile"])
        reward = self.repo.list_rewards(player_id="alice", limit=10)[0]
        self.assertEqual(reward["status"], "pending")
        self.assertGreater(saved_once["respect"], 200)
        self.assertEqual(len(saved_once["ghostnetwork_reward_history"]), 1)

        with patch.object(run, "load_profile_write_record", side_effect=load_record), \
                patch.object(run, "save_profile_write_record", side_effect=guarded_save) as save_mock, \
                patch.object(run, "enqueue_ghostnetwork_event_delta", return_value={"ok": True}):
            run.apply_ghostnetwork_runtime_result(self.service, event)

        self.assertEqual(save_mock.call_count, 0)
        self.assertEqual(durable["profile"]["respect"], saved_once["respect"])
        self.assertEqual(len(durable["profile"]["ghostnetwork_reward_history"]), 1)
        self.assertEqual(self.repo.get_reward(reward["reward_id"])["status"], "applied")
        reputation = self.repo.get_clan_reputation("virex")
        self.assertEqual(reputation["parts_activated"], 1)

    def test_territory_publication_does_not_require_username_inside_profile_json(self):
        areas = [self.area("foreign-owner", 1)]
        profile_without_username = {"ghost_clan_code": "sentinel_order"}
        with patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(
                    run.user_store,
                    "list_profile_identities",
                    return_value=[("foreign-owner", profile_without_username)],
                ):
            publication = run.build_ghostnetwork_territory_publication()

        self.assertEqual(len(publication), 1)
        self.assertEqual(publication[0]["owner_username"], "foreign-owner")
        self.assertEqual(publication[0]["owner_clan"], "sentinel_order")

    def test_canonical_conflict_publication_freezes_and_resolution_reconciles(self):
        areas = [self.area("part-owner", 1)]
        profiles = {"part-owner": {"username": "part-owner", "clan": self.part["clan_code"]}}
        active_snapshot = {
            "conflict": {"conflict_id": "post130-conflict", "status": "active", "conflict_version": 3},
            "fronts": [{"front_id": "post130-front", "geometry": areas[0]["vertices"]}],
        }
        resolved_snapshot = {
            "conflict": {"conflict_id": "post130-conflict", "status": "resolved", "conflict_version": 4},
            "fronts": active_snapshot["fronts"],
        }
        latest = {"value": active_snapshot}
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_delta_publisher, "record_conflict_changed", return_value=[]), \
                patch.object(run.territory_conflict_store, "latest_snapshot_state", side_effect=lambda *_: latest["value"]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run.user_store, "list_profile_identities", side_effect=lambda: list(profiles.items())), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("part-owner", areas, reason="post130_stable")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")

            run.record_territory_conflict_delta(active_snapshot["conflict"], reason="post130_conflict_started")
            run.process_ghostnetwork_territory_job("test-worker")
            contested = self.repo.get_part(self.part["part_id"])
            self.assertEqual(contested["conflict_state"], "contested")

            latest["value"] = resolved_snapshot
            run.record_territory_conflict_delta(resolved_snapshot["conflict"], reason="post130_conflict_resolved")
            run.process_ghostnetwork_territory_job("test-worker")
            resolved = self.repo.get_part(self.part["part_id"])
            self.assertEqual(resolved["conflict_state"], "none")
            self.assertEqual(resolved["status"], "active")


if __name__ == "__main__":
    unittest.main()
