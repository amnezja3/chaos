import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostNetworkRepository
from database import db_connect
from ghostnetwork.transmission import signal_payload_checksum
from scripts.audit_ghostnetwork_endgame import (
    _production_conflict_chronology,
    _signal_checksum,
    _transmission_chronology,
    _transmission_reward_times,
    audit as postflight_audit,
)
from scripts.audit_ghostnetwork_endgame_preflight import (
    _blocked_checkpoint_gate_holds,
    _compact_report,
    audit as preflight_audit,
)


class GhostNetworkEndgameAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "endgame-audit.sqlite3")
        self.repository = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repository).ensure_active_cycle()["cycle"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_preflight_is_read_only_and_strictly_rejects_unprepared_cycle(self):
        report = preflight_audit(
            self.db_path, strict=True, check_runtime=False, backup_path="",
        )

        self.assertFalse(report["ok"])
        self.assertEqual(report["mode"], "read_only")
        self.assertEqual(report["mutations"], {})
        self.assertIn("entry_state_19_of_20", report["errors"])
        self.assertIn("exactly_one_conflict_blocker", report["errors"])

    def test_postflight_reports_incomplete_lineage_without_writing(self):
        before = self.repository.get_state_version(self.cycle["cycle_id"])
        report = postflight_audit(self.cycle["cycle_id"], self.db_path, strict=True)
        after = self.repository.get_state_version(self.cycle["cycle_id"])

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(before, after)
        self.assertIn("one_lock", report["integrity_errors"])
        self.assertIn("one_signal", report["integrity_errors"])

    def test_preflight_console_report_does_not_dump_target_payloads(self):
        compact = _compact_report({
            "closing_part": {"part_id": "p1", "part_code": "P1", "anchor_snapshot": {"large": True}},
            "territory_plan": {"entries": [{
                "territory_id": "t1", "targets": [{"large": True}],
                "vertices": [{"lat": 1, "lng": 2}],
            }]},
        })

        self.assertNotIn("anchor_snapshot", compact["closing_part"])
        self.assertNotIn("targets", compact["territory_plan"]["entries"][0])
        self.assertEqual(compact["territory_plan"]["entries"][0]["target_count"], 1)
        self.assertEqual(compact["territory_plan"]["entries"][0]["geometry_vertices"], 1)

    def test_blocked_checkpoint_uses_conflict_gate_public_contract(self):
        parts = [{"part_id": f"part-{index}", "status": "active"} for index in range(20)]
        gate = {"blocked": True, "blockers": [{"conflict_id": "conflict-a"}]}

        self.assertTrue(_blocked_checkpoint_gate_holds(parts, gate))
        self.assertFalse(_blocked_checkpoint_gate_holds(parts[:-1], gate))
        self.assertFalse(_blocked_checkpoint_gate_holds(parts, {"blocked": False, "blockers": []}))

    def test_postflight_uses_canonical_signal_checksum(self):
        payload = {"unicode": "sygnał", "nested": {"b": 2, "a": 1}}
        self.assertEqual(_signal_checksum(payload), signal_payload_checksum(payload))

    def test_production_conflict_resolved_after_lock_is_an_integrity_violation(self):
        locked_at = datetime.now(timezone.utc)

        class RepositoryStub:
            @staticmethod
            def list_endgame_production_conflicts(*_args, **_kwargs):
                return [{
                    "conflict_id": "conflict-a",
                    "status": "resolved",
                    "territory_ids": ["territory-a"],
                    "resolved_at": (locked_at + timedelta(seconds=2)).isoformat(),
                    "closed_at": "",
                    "resolution_reason": "territory_consumed",
                }]

        result = _production_conflict_chronology(RepositoryStub(), {
            "locked_at": locked_at.isoformat(),
            "parts": [{"territory_id": "territory-a", "conflict_id": ""}],
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["violations"][0]["reason"], "resolved_after_cycle_lock")

    def test_integrity_event_query_is_not_truncated_by_timeline_limit(self):
        cycle_id = self.cycle["cycle_id"]
        now = self.repository.now()
        with db_connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO ghost_part_events (
                    event_id, cycle_id, part_id, event_type, player_id,
                    clan_code, territory_id, state_version, created_at,
                    payload_json, dedupe_key, audience_scope, audience_clan, entity_id
                ) VALUES (?, ?, '', ?, '', '', '', ?, ?, '{}', '', 'system', '', '')
                """,
                [(f"bulk-{index}", cycle_id, "ghost.audit.bulk", index + 1, now)
                 for index in range(1005)],
            )

        self.assertEqual(len(self.repository.list_events(cycle_id, limit=5000)), 1000)
        self.assertEqual(
            len(self.repository.list_events_by_types(cycle_id, ["ghost.audit.bulk"])),
            1005,
        )

    def timeline_fixture(self):
        start = "2026-09-10T10:00:00+00:00"
        end = "2026-09-10T10:15:00+00:00"
        effect = "2026-09-10T10:00:02+00:00"
        signal = {"cycle_id": "c", "signal_id": "s", "lock_snapshot_id": "l",
                  "sent_at": "2026-09-10T10:00:03+00:00"}
        show = {"cycle_id": "c", "signal_id": "s", "created_at": start,
                "show_started_at": start, "show_ends_at": end, "phase_policy_version": "v1"}
        events = [{"event_type": kind, "state_version": index + 1} for index, kind in enumerate([
            "ghost.transmission_started", "ghost.signal_show_started", "ghost.parts_consumed",
            "ghost.signal_sent", "ghost.stabilization_started"])]
        events[0]["payload"] = {"signal_id": "s", "lock_snapshot_id": "l", "started_at": start,
                                "ends_at": end, "phase_policy_version": "v1"}
        return show, signal, events, [effect]

    def test_timeline_checks_creation_time_not_backdated_show_start(self):
        show, signal, events, effects = self.timeline_fixture()
        self.assertTrue(_transmission_chronology(show, signal, events, effects)["ok"])
        show["created_at"] = "2026-09-10T10:00:05+00:00"
        report = _transmission_chronology(show, signal, events, effects)
        self.assertIn("show_not_created_before_effects", report["violations"])

    def test_timeline_excludes_cycle_rewards_but_rejects_early_signal_reward(self):
        show, signal, events, effects = self.timeline_fixture()
        old = "2026-08-19T09:18:22.763615+00:00"
        rewards = [
            {"signal_id": "", "created_at": old},
            {"signal_id": "other-signal", "created_at": old},
            {"signal_id": signal["signal_id"], "created_at": effects[0]},
        ]
        selected = _transmission_reward_times(rewards, signal)
        self.assertEqual(selected, effects)
        self.assertTrue(_transmission_chronology(show, signal, events, selected)["ok"])
        rewards.append({"signal_id": signal["signal_id"], "created_at": old})
        report = _transmission_chronology(
            show, signal, events, _transmission_reward_times(rewards, signal))
        self.assertIn("show_not_created_before_effects", report["violations"])
        self.assertEqual(_transmission_reward_times(rewards, None), [])

    def test_timeline_rejects_early_sent_and_changed_deadline(self):
        show, signal, events, effects = self.timeline_fixture()
        signal["sent_at"] = "2026-09-10T10:00:01+00:00"
        show["show_ends_at"] = "2026-09-10T10:16:00+00:00"
        events[2]["state_version"] = 6
        report = _transmission_chronology(show, signal, events, effects)
        self.assertIn("signal_sent_before_effects", report["violations"])
        self.assertIn("timeline_lineage_or_clock_changed", report["violations"])
        self.assertIn("effects_outside_show_to_sent_window", report["violations"])

    def test_legacy_timeline_is_not_certified_as_139(self):
        report = _transmission_chronology(None, None, [], [])
        self.assertFalse(report["enforced"])
        self.assertIsNone(report["ok"])
        strict = _transmission_chronology(None, None, [], [], required=True)
        self.assertTrue(strict["enforced"])
        self.assertFalse(strict["ok"])

    def test_postflight_can_require_139_without_mutating_old_schema(self):
        before = self.repository.get_state_version(self.cycle["cycle_id"])
        report = postflight_audit(self.cycle["cycle_id"], self.db_path,
                                 require_transmission_timeline=True)
        self.assertIn("transmission_timeline_valid", report["integrity_errors"])
        self.assertFalse(report["transmission_chronology"]["ok"])
        self.assertEqual(before, self.repository.get_state_version(self.cycle["cycle_id"]))


if __name__ == "__main__":
    unittest.main()
