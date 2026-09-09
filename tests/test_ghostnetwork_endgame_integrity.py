import os
import tempfile
import unittest
from unittest.mock import patch

from config import GHOSTNETWORK_ENDGAME_FLAGS
from database import TerritoryStore, db_connect, dumps_json, init_db
from ghostnetwork import (
    GhostCycleService,
    GhostNetworkClosureService,
    GhostNetworkRepository,
    GhostNetworkService,
    GhostTransmissionService,
)
from ghostnetwork.closure import resolve_endgame_conflict_gate
from ghostnetwork.endgame import build_territory_consumption_plan
from scripts.audit_ghostnetwork_signal import audit as audit_signal


def square(south, west, north, east):
    return [
        {"lat": south, "lng": west},
        {"lat": south, "lng": east},
        {"lat": north, "lng": east},
        {"lat": north, "lng": west},
    ]


class GhostNetworkEndgameIntegrityTest(unittest.TestCase):
    def test_server_preflight_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "signal-audit.sqlite3")
            init_db(db_path)
            repo = GhostNetworkRepository(db_path=db_path)
            GhostCycleService(repository=repo).ensure_active_cycle()
            report = audit_signal(db_path)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["mode"], "read_only")
            self.assertEqual(report["mutations"], {})
            self.assertFalse(report["production_signal_triggered_by_audit"])

    def test_conflict_gate_is_fail_closed_and_allows_verified_orphan(self):
        part = {"part_id": "part-a", "part_code": "A1", "conflict_state": "none"}
        unresolved = {
            "conflict_id": "conflict-a",
            "part_id": "part-a",
            "status": "active",
            "snapshot": {},
        }
        blocked = resolve_endgame_conflict_gate([part], [unresolved])
        self.assertTrue(blocked["blocked"])
        self.assertEqual(blocked["blockers"][0]["reason"], "unresolved_strategic_conflict")

        unresolved["snapshot"] = {"endgame_orphan_verified": True}
        verified = resolve_endgame_conflict_gate([part], [unresolved])
        self.assertFalse(verified["blocked"])
        self.assertEqual(verified["warnings"][0]["reason"], "verified_orphaned_strategic_conflict")

        part["conflict_state"] = "contested"
        live = resolve_endgame_conflict_gate([part], [])
        self.assertTrue(live["blocked"])
        self.assertEqual(live["blockers"][0]["reason"], "part_conflict_without_strategic_record")

    def test_territory_plan_is_deduplicated_and_only_expands_one_hop(self):
        territories = [
            {"territory_id": "a", "owner_id": "alice", "clan_code": "echo", "vertices": square(0, 0, 2, 2)},
            {"territory_id": "b", "owner_id": "bob", "clan_code": "echo", "vertices": square(1, 1, 3, 3)},
            {"territory_id": "c", "owner_id": "cara", "clan_code": "echo", "vertices": square(2.5, 2.5, 4, 4)},
            {"territory_id": "d", "owner_id": "dan", "clan_code": "virex", "vertices": square(10, 10, 11, 11)},
        ]
        plan = build_territory_consumption_plan(
            [{"territory_id": "a", "territory_clan": "echo"}],
            [{"conflict_id": "resolved-1", "territory_id": "d", "status": "resolved"}],
            territories,
            [{"conflict_id": "resolved-1", "status": "resolved", "territory_ids": ["a", "d"]}],
        )
        entries = {item["territory_id"]: item for item in plan["entries"]}
        self.assertEqual(set(entries), {"a", "b", "d"})
        self.assertEqual(entries["a"]["role"], "primary")
        self.assertEqual(entries["b"]["role"], "allied_overlap")
        self.assertEqual(entries["d"]["role"], "conflict")
        self.assertNotIn("c", entries, "one-hop expansion must not recurse through b")

    def test_territory_consumption_is_archived_hidden_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "territory-consumption.sqlite3")
            init_db(db_path)
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            now = repo.now()
            vertices = square(52.0, 21.0, 52.01, 21.01)
            with db_connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO player_areas (
                        id, owner_username, vertices_json, centroid_lat, centroid_lng,
                        area_size, max_edge_distance, status, created_at, updated_at
                    ) VALUES (101, 'alice', ?, 52.005, 21.005, 1000, 100, 'active', ?, ?)
                    """,
                    (dumps_json(vertices), now, now),
                )
                conn.execute(
                    """
                    INSERT INTO territory_area_publications (
                        owner_username, publication_version, geometry_hash, updated_at
                    ) VALUES ('alice', 7, 'hash', ?)
                    """,
                    (now,),
                )
                target = {"target_id": "target-a", "lat": 52.005, "lng": 21.005}
                cursor = conn.execute(
                    """
                    INSERT INTO captured_targets (
                        owner_username, lat, lng, label, target_json, captured_at, updated_at
                    ) VALUES ('alice', 52.005, 21.005, 'A', ?, ?, ?)
                    """,
                    (dumps_json(target), now, now),
                )
                conn.execute(
                    """
                    INSERT INTO territory_target_ownership (
                        target_id, owner_username, lat, lng, label, target_json, updated_at
                    ) VALUES ('target-a', 'alice', 52.005, 21.005, 'A', ?, ?)
                    """,
                    (dumps_json(target), now),
                )
                capture_id = cursor.lastrowid
            plan = {
                "schema": 1,
                "entries": [{
                    "territory_id": "101",
                    "owner_id": "alice",
                    "clan_code": "echo",
                    "role": "primary",
                    "reason": "ghostnetwork_part_territory",
                    "area_size": 1000,
                    "publication_version": 7,
                    "vertices": vertices,
                    "targets": [{
                        "capture_record_id": capture_id,
                        "target_id": "target-a",
                        "lat": 52.005,
                        "lng": 21.005,
                        "target": target,
                    }],
                }],
            }
            first = repo.consume_signal_territories("signal-a", cycle["cycle_id"], plan)
            second = repo.consume_signal_territories("signal-a", cycle["cycle_id"], plan)
            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertEqual(len(repo.list_signal_territory_consumptions("signal-a")), 1)
            self.assertEqual(TerritoryStore(db_path).list_player_areas(), [])
            with db_connect(db_path) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM captured_targets").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM territory_target_ownership").fetchone()[0], 0)
                status = conn.execute("SELECT status FROM player_areas WHERE id = 101").fetchone()[0]
            self.assertEqual(status, "consumed")

    def test_canonical_territory_reward_projects_profile_and_clan_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "territory-reward.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            service = GhostNetworkService(repository=repo)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            reward = repo.insert_reward({
                "reward_key": "signal:territory:alice:101",
                "cycle_id": cycle["cycle_id"],
                "signal_id": "signal-a",
                "player_id": "alice",
                "clan_code": "echo",
                "reward_type": "ghost_signal_territory_consumed",
                "final_rsp": 8,
            })
            profile = {"username": "alice", "respect": 10, "ghostnetwork_stats": {}}
            applied = service.apply_pending_reward(profile, reward_id=reward["reward_id"])
            self.assertTrue(applied["ok"], applied)
            self.assertEqual(profile["respect"], 18)
            self.assertEqual(profile["ghostnetwork_stats"]["signal_territories_consumed"], 1)
            reputation = repo.get_clan_reputation("echo")
            self.assertEqual(reputation["signal_territories_consumed"], 1)
            self.assertGreater(reputation["total_reputation"], 0)

    def test_enabled_plan_is_consumed_and_rewarded_once_by_transmission(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "endgame-enabled.sqlite3")
            init_db(db_path)
            repo = GhostNetworkRepository(db_path=db_path)
            cycle_service = GhostCycleService(repository=repo)
            cycle = cycle_service.create_cycle()["cycle"]
            now = repo.now()
            vertices = square(52.0, 21.0, 52.01, 21.01)
            with db_connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO player_areas (
                        id, owner_username, vertices_json, centroid_lat, centroid_lng,
                        area_size, max_edge_distance, status, created_at, updated_at
                    ) VALUES (101, 'alice', ?, 52.005, 21.005, 1000, 100, 'active', ?, ?)
                    """,
                    (dumps_json(vertices), now, now),
                )
                conn.execute(
                    """
                    INSERT INTO territory_area_publications (
                        owner_username, publication_version, geometry_hash, updated_at
                    ) VALUES ('alice', 7, 'hash', ?)
                    """,
                    (now,),
                )
                target = {"target_id": "target-a", "lat": 52.005, "lng": 21.005}
                conn.execute(
                    """
                    INSERT INTO captured_targets (
                        owner_username, lat, lng, label, target_json, captured_at, updated_at
                    ) VALUES ('alice', 52.005, 21.005, 'A', ?, ?, ?)
                    """,
                    (dumps_json(target), now, now),
                )
                conn.execute(
                    """
                    INSERT INTO territory_target_ownership (
                        target_id, owner_username, lat, lng, label, target_json, updated_at
                    ) VALUES ('target-a', 'alice', 52.005, 21.005, 'A', ?, ?)
                    """,
                    (dumps_json(target), now),
                )
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                repo.update_part(
                    part["part_id"],
                    status="active",
                    target_id=f"POI-{part['part_code']}",
                    latitude=52.001 + index * 0.0001,
                    longitude=21.001 + index * 0.0001,
                    discovered_by="alice",
                    discovered_clan=part["clan_code"],
                    discovered_at=now,
                    anchor_snapshot_json=dumps_json({
                        "target_id": f"POI-{part['part_code']}",
                        "lat": 52.001 + index * 0.0001,
                        "lng": 21.001 + index * 0.0001,
                    }),
                    territory_id="101",
                    territory_owner_id="alice",
                    territory_clan=part["clan_code"],
                    territory_state_version=7,
                    activated_at=now,
                    last_activated_at=now,
                    conflict_state="none",
                    conflict_id="",
                )
            closing_part = repo.list_parts(cycle["cycle_id"])[-1]
            closing_event = repo.append_event(
                "ghost.part_activated",
                cycle_id=cycle["cycle_id"],
                part_id=closing_part["part_id"],
                entity_id=closing_part["part_id"],
                player_id="alice",
                clan_code=closing_part["clan_code"],
                territory_id="101",
                dedupe_key="test:enabled:closing",
            )
            closure = GhostNetworkClosureService(repository=repo)
            transmission = GhostTransmissionService(repository=repo, closure_service=closure)
            with patch.dict(GHOSTNETWORK_ENDGAME_FLAGS, {"territory_consumption_enabled": True}):
                locked = closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
            self.assertTrue(locked["locked"], locked)
            plan = locked["snapshot"]["snapshot"]["territory_consumption_plan"]
            self.assertTrue(plan["execution_required"])
            self.assertEqual(plan["counts"]["primary"], 1)

            first = transmission.start_transmission(cycle["cycle_id"])
            second = transmission.start_transmission(cycle["cycle_id"])
            self.assertTrue(first["ok"], first)
            self.assertEqual(first["territories"]["count"], 1)
            self.assertTrue(second["idempotent"])
            self.assertEqual(second["territories"]["count"], 1)
            self.assertEqual(len(repo.list_signal_territory_consumptions(first["signal"]["signal_id"])), 1)
            rewards = repo.list_rewards(signal_id=first["signal"]["signal_id"], limit=100)
            self.assertEqual(len(rewards), 22)
            self.assertEqual(
                sum(item["reward_type"] == "ghost_signal_territory_consumed" for item in rewards),
                1,
            )
            self.assertEqual(TerritoryStore(db_path).list_player_areas(), [])


if __name__ == "__main__":
    unittest.main()
