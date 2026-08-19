import os
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from ghostnetwork import (
    GhostCycleService,
    GhostDropPolicy,
    GhostNetworkDeltaPublisher,
    GhostNetworkRepository,
    GhostNetworkService,
)
from tools import audit_ghostnetwork_runtime_state


class CountingDropPolicy(GhostDropPolicy):
    def __init__(self, *, enabled, chance):
        super().__init__(enabled=enabled, chance=chance, reservation_ttl_seconds=600)
        self.roll_calls = 0

    def should_attempt_reservation(self, player, target, cycle, context=None):
        self.roll_calls += 1
        return super().should_attempt_reservation(player, target, cycle, context=context)


class RecordingDeltaBus:
    def __init__(self):
        self.records = []

    def record_change(self, username, scope, change_type, **kwargs):
        record = {"username": username, "scope": scope, "type": change_type, **kwargs}
        self.records.append(record)
        return record


class GhostNetworkDropPipelineDiagnosticTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork-diagnostic.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=self.repo).ensure_active_cycle()
        self.player = {
            "player_id": "audit-player",
            "username": "audit-player",
            "clan_code": "virex",
            "ghost_profession": "broker",
        }
        self.target = {
            "target_id": "map:52.10000:21.10000:audit-target",
            "lat": 52.1,
            "lng": 21.1,
            "label": "Audit target",
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_distinguishes_roll_miss_from_roll_not_reached(self):
        policy = CountingDropPolicy(enabled=False, chance=0.0)
        service = GhostNetworkService(repository=self.repo, drop_policy=policy)

        result = service.on_target_aimed(self.player, self.target)

        self.assertEqual(result["status"], "roll_missed")
        self.assertEqual(policy.roll_calls, 1)
        self.assertEqual(self.repo.get_reservation_status()["active"], 0)

    def test_forced_positive_roll_reaches_persistence_snapshot_and_delta(self):
        policy = CountingDropPolicy(enabled=True, chance=1.0)
        service = GhostNetworkService(repository=self.repo, drop_policy=policy)

        reservation = service.on_target_aimed(self.player, self.target)
        self.assertEqual(reservation["status"], "reserved")
        self.assertEqual(policy.roll_calls, 1)
        attached = service.attach_reservation_to_operation(
            self.player["player_id"], self.target["target_id"], "audit-op-1"
        )
        self.assertEqual(attached["status"], "attached")

        discovered = service.on_target_hacked(
            self.player,
            self.target,
            operation={"operation_id": "audit-op-1"},
            result={"success": True, "target_captured": True},
            context={"capture_confirmed": True},
        )
        self.assertEqual(discovered["status"], "discovered")
        persisted = self.repo.get_part(discovered["part"]["part_id"])
        self.assertEqual(persisted["status"], "public")
        self.assertEqual(persisted["target_id"], self.target["target_id"])

        viewer = {
            "viewer_id": self.player["player_id"],
            "username": self.player["player_id"],
            "viewer_clan": "virex",
            "viewer_profession": "broker",
            "audience_scope": "player",
            "is_authenticated": True,
        }
        projection = service.get_snapshot_for_viewer(viewer)
        projected_ids = {item.get("part_id") for item in projection.get("parts", [])}
        self.assertIn(persisted["part_id"], projected_ids)

        delta_bus = RecordingDeltaBus()
        published = GhostNetworkDeltaPublisher(
            repository=self.repo,
            delta_bus=delta_bus,
        ).publish_event(discovered["event"], [viewer])
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["scope"], "ghostnetwork")
        self.assertEqual(published[0]["type"], "ghost.part_discovered")

    def test_runtime_audit_reads_part_summary_from_cycle_service(self):
        service = GhostNetworkService(repository=self.repo)
        output = io.StringIO()

        with patch.object(
            audit_ghostnetwork_runtime_state,
            "GhostNetworkService",
            return_value=service,
        ), redirect_stdout(output):
            audit_ghostnetwork_runtime_state.main()

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["cycle"]["cycle_id"], service.get_active_cycle()["cycle_id"])
        self.assertEqual(payload["parts_summary"]["parts_total"], 20)
        self.assertEqual(payload["parts_count"], 20)


if __name__ == "__main__":
    unittest.main()
