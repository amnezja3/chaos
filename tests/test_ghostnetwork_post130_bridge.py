import os
import tempfile
import unittest
from unittest.mock import patch

import run
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
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("foreign-owner", areas, reason="post130_publication")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "contained")

            areas[:] = [self.area("part-owner", 2)]
            run.record_territory_areas_delta("part-owner", areas, reason="post130_owner_changed")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")
            progress = self.service.modules.resolve_machine_progress(
                self.repo.get_active_cycle()["cycle_id"], self.part["machine_code"]
            )
            self.assertEqual(progress["parts_active"], 1)

            areas[:] = []
            run.record_territory_areas_delta("part-owner", areas, reason="post130_release")
            released = self.repo.get_part(self.part["part_id"])
            self.assertEqual(released["status"], "public")
            self.assertEqual(released["territory_id"], "")

    def test_area_publication_carries_live_lifecycle_event_to_delta_bridge(self):
        areas = [self.area("foreign-owner", 1)]
        profiles = {
            "foreign-owner": {"username": "foreign-owner", "clan": "sentinel_order"},
        }
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"), \
                patch.object(run, "publish_ghostnetwork_event_delta", return_value=[]) as publish:
            run.record_territory_areas_delta(
                "foreign-owner",
                areas,
                reason="post130_live_containment",
            )

        event_types = [call.args[0]["event_type"] for call in publish.call_args_list]
        self.assertIn("ghost.part_contained", event_types)

    def test_canonical_ghost_clan_profile_is_included_in_territory_publication(self):
        areas = [self.area("foreign-owner", 1)]
        profile = {"ghost_clan_code": "sentinel_order"}
        with patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run.user_store, "get_profile", return_value=profile):
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
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_delta_publisher, "record_conflict_changed", return_value=[]), \
                patch.object(run.territory_conflict_store, "latest_snapshot_state", side_effect=lambda *_: latest["value"]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("part-owner", areas, reason="post130_stable")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")

            run.record_territory_conflict_delta(active_snapshot["conflict"], reason="post130_conflict_started")
            contested = self.repo.get_part(self.part["part_id"])
            self.assertEqual(contested["conflict_state"], "contested")

            latest["value"] = resolved_snapshot
            run.record_territory_conflict_delta(resolved_snapshot["conflict"], reason="post130_conflict_resolved")
            resolved = self.repo.get_part(self.part["part_id"])
            self.assertEqual(resolved["conflict_state"], "none")
            self.assertEqual(resolved["status"], "active")


if __name__ == "__main__":
    unittest.main()
