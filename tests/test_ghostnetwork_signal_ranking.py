import os
import tempfile
import unittest
from unittest.mock import patch
from ghostnetwork.show_manifest import prepare_settlement_scene

from database import dumps_json
from ghostnetwork import (
    GhostCycleService,
    GhostNetworkRepository,
    GhostSignalRankingService,
    GhostTransmissionService,
)
from ghostnetwork.closure import GhostNetworkClosureService


class GhostSignalRankingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ranking.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def transmit_cycle(self):
        cycle = GhostCycleService(repository=self.repo).create_cycle()["cycle"]
        now = self.repo.now()
        for index, part in enumerate(self.repo.list_parts(cycle["cycle_id"])):
            owner = "alpha" if index < 12 else "beta"
            clan = part["clan_code"]
            self.repo.update_part(
                part["part_id"], status="active", target_id=f"rank-{index}",
                latitude=52.0 + index * 0.001, longitude=21.0 + index * 0.001,
                discovered_by=owner, discovered_clan=clan, discovered_at=now,
                anchor_snapshot_json=dumps_json({"target_id": f"rank-{index}"}),
                territory_id=f"rank-territory-{index}", territory_owner_id=owner,
                territory_clan=clan, territory_state_version=index + 1,
                activated_at=now, last_activated_at=now, conflict_state="none",
            )
        closing = self.repo.list_parts(cycle["cycle_id"])[-1]
        event = self.repo.append_event(
            "ghost.part_activated", cycle_id=cycle["cycle_id"],
            part_id=closing["part_id"], entity_id=closing["part_id"],
            player_id="beta", clan_code=closing["clan_code"],
            territory_id=closing["territory_id"],
            event_id=f"ranking-close-{cycle['cycle_id']}",
            dedupe_key=f"ranking-close:{cycle['cycle_id']}",
            payload={"player_id": "beta"},
        )
        closure = GhostNetworkClosureService(repository=self.repo)
        locked = closure.attempt_cycle_lock(cycle["cycle_id"], event["event_id"])
        self.assertTrue(locked.get("locked"), locked)
        transmitted = GhostTransmissionService(
            repository=self.repo, closure_service=closure
        ).start_transmission(cycle["cycle_id"])
        self.assertTrue(transmitted["ok"], transmitted)
        return transmitted["signal"]

    def test_snapshot_is_immutable_idempotent_and_checksum_valid(self):
        signal = self.transmit_cycle()
        service = GhostSignalRankingService(self.repo)
        first = service.finalize(signal["signal_id"])
        second = service.finalize(signal["signal_id"])

        self.assertTrue(first["ok"], first)
        self.assertTrue(second["ok"], second)
        self.assertTrue(second["idempotent"])
        self.assertEqual(
            first["ranking"]["snapshot_checksum"],
            second["ranking"]["snapshot_checksum"],
        )
        self.assertEqual(len(self.repo.list_signal_rankings()), 1)
        snapshot = first["ranking"]["snapshot"]
        self.assertEqual(snapshot["snapshot_schema"], 2)
        self.assertEqual(len(snapshot["parts"]), 20)
        self.assertEqual(sum(row["nodes_held"] for row in snapshot["players"]), 20)
        self.assertEqual(sum(row["rsp_signal"] for row in snapshot["players"]), 180)
        self.assertEqual(sum(row["clan_ghost_score"] for row in snapshot["clans"]), 500)
        projection = self.repo.get_signal_show_for_signal(signal["signal_id"])["scene_snapshot"]["settlement"]
        self.assertEqual(projection["rsp_total"], 180)
        self.assertEqual(projection["players_total"], 2)
        self.assertNotIn("user_id", dumps_json(projection))
        self.repo.store_show_settlement_scene(signal["signal_id"], {"available": False})
        self.assertEqual(self.repo.get_signal_show_for_signal(signal["signal_id"])["scene_snapshot"]["settlement"], projection)

    def test_presentation_failure_does_not_block_ranking_and_retry_repairs(self):
        signal = self.transmit_cycle()
        service = GhostSignalRankingService(self.repo)
        with patch.object(self.repo, "store_show_settlement_scene", side_effect=RuntimeError("unavailable")):
            self.assertTrue(service.finalize(signal["signal_id"])["ok"])
        self.assertNotIn("settlement", self.repo.get_signal_show_for_signal(signal["signal_id"])["scene_snapshot"])
        self.assertTrue(service.finalize(signal["signal_id"])["ok"])
        self.assertTrue(self.repo.get_signal_show_for_signal(signal["signal_id"])["scene_snapshot"]["settlement"]["available"])

    def test_projection_bounds_and_signal_reward_lineage(self):
        ranking = {"signal_id": "current", "snapshot": {
            "rewards": [{"signal_id": "old", "final_rsp": 999},
                        {"signal_id": "current", "final_rsp": 7, "reward_type": "reward"}],
            "territories": [{"owner_id": "private", "targets": ["secret"], "vertices": [
                {"lat": 1, "lng": 1}, {"lat": 2, "lng": 1}, {"lat": 2, "lng": 2}]}] * 41,
            "players": [{"user_id": "private", "display_alias_snapshot": "Alias"}] * 21}}
        projection = prepare_settlement_scene(ranking)
        self.assertEqual(projection["rsp_total"], 7)
        self.assertEqual(len(projection["territories"]), 40)
        self.assertEqual(len(projection["players"]), 20)
        self.assertTrue(projection["territories_truncated"] and projection["players_truncated"])
        self.assertNotIn("private", dumps_json(projection))
        self.assertNotIn("secret", dumps_json(projection))
        self.assertLess(len(dumps_json(projection).encode()), 24576)
        for row in ranking["snapshot"]["territories"]:
            row["clan_code"] = "\U0001f30d" * 100
        ranking["snapshot"]["conflicts"] = [{"status": "\U0001f30d" * 100}] * 20
        projection = prepare_settlement_scene(ranking, production_conflicts=[{"status": "\U0001f30d" * 100}] * 20)
        self.assertLessEqual(len(__import__("json").dumps(projection, ensure_ascii=False).encode()), 24576)

    def test_publication_excerpts_exclude_other_cycles_private_and_unpublished(self):
        cycle = GhostCycleService(repository=self.repo).create_cycle()["cycle"]
        event = self.repo.append_event("ghost.part_activated", cycle_id=cycle["cycle_id"], dedupe_key="excerpt-source")
        now = self.repo.now()
        with self.repo._conn() as conn:
            def insert(table, fields):
                columns = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
                values = {c["name"]: "" for c in columns if c["notnull"] and c["dflt_value"] is None}
                values.update(fields)
                conn.execute("INSERT INTO " + table + " (" + ",".join(values) + ") VALUES ("
                             + ",".join("?" for _ in values) + ")", tuple(values.values()))
            for tag, scope, status, active in [("good", "public", "published", "active"),
                    ("private", "owner", "published", "active"), ("pending", "public", "ready", "active"),
                    ("invalid", "public", "published", "invalidated")]:
                insert("ghost_narrative_publication_receipts", {"publication_receipt_id": tag, "status": status,
                    "candidate_id": tag, "task_id": tag, "target_medium": "blacknet", "audience_scope": scope})
                insert("ghost_narrative_medium_records", {"medium_record_id": tag, "publication_receipt_id": tag,
                    "source_event_id": event["event_id"], "source_scope": "ghostnetwork", "title": tag,
                    "body": "excerpt", "target_medium": "blacknet", "audience_scope": scope,
                    "active_state": active, "published_at": now})
        self.assertEqual([r["title"] for r in self.repo.list_show_publication_excerpts(cycle["cycle_id"], now)], ["good"])
        self.assertEqual(self.repo.list_show_publication_excerpts("another-cycle", now), [])

    def test_production_conflicts_require_archive_reference_and_preexisting_resolution(self):
        ranking = {"signal_id": "s", "cycle_id": "c", "created_at": "2026-09-11T12:00:00Z",
                   "snapshot": {"parts": [{"conflict_id": "matching"}, {"conflict_id": "future"}]}}
        rows = [{"conflict_id": identity, "status": "resolved", "resolved_at": stamp}
                for identity, stamp in [("matching", "2026-09-11T11:00:00Z"),
                                        ("unrelated", "2026-09-11T11:00:00Z"),
                                        ("future", "2026-09-11T13:00:00Z")]]
        with patch.object(self.repo, "get_signal_show_for_signal", return_value={"scene_snapshot": {}}), \
                patch.object(self.repo, "list_show_publication_excerpts", return_value=[]), \
                patch.object(self.repo, "list_endgame_production_conflicts", return_value=rows), \
                patch.object(self.repo, "store_show_settlement_scene") as stored:
            GhostSignalRankingService(self.repo)._store_show_scene(ranking)
        projection = stored.call_args.args[1]
        self.assertEqual(len(projection["production_conflicts"]), 1)
        self.assertEqual(projection["production_conflicts"][0]["resolved_at"], "2026-09-11T11:00:00Z")
        self.assertNotIn("matching", dumps_json(projection))

    def test_all_time_is_rebuilt_from_snapshots(self):
        signal = self.transmit_cycle()
        service = GhostSignalRankingService(self.repo)
        service.finalize(signal["signal_id"])
        result = service.all_time()
        self.assertTrue(result["ok"])
        self.assertEqual(result["rebuilt_from_snapshots"], 1)
        self.assertEqual({row["user_id"] for row in result["players"]}, {"alpha", "beta"})
        self.assertGreaterEqual(len(result["clans"]), 1)
        self.assertEqual(sum(row["signals_participated"] for row in result["players"]), 2)

    def test_largest_remainder_is_deterministic(self):
        from ghostnetwork.ranking import allocate_pool

        self.assertEqual(allocate_pool(5, {"b": 1, "a": 1, "c": 1}), {"a": 2, "b": 2, "c": 1})


if __name__ == "__main__":
    unittest.main()
