import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from scripts.monitor_138_2_signal_e2e import (
    atomic_json,
    canonical_hash,
    changed_sections,
    milestone_flags,
    read_client_restart,
)


class SignalE2EMonitorTest(unittest.TestCase):
    def test_restart_evidence_is_cycle_scoped_and_excludes_boot_secrets(self):
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("CREATE TABLE ghost_part_events (event_id, created_at, payload_json, cycle_id, event_type, state_version)")
            conn.execute("CREATE TABLE session_restart_receipts (username_hash, lineage_hash, epoch, prepared_at, acknowledged_at, boot_token_hash)")
            conn.execute("INSERT INTO ghost_part_events VALUES ('e', 't1', ?, 'c1', 'ghost.client_restart_required', 1)",
                         (json.dumps({"epoch": "epoch1"}),))
            conn.executemany("INSERT INTO session_restart_receipts VALUES (?, ?, ?, 't2', ?, 'secret')", [
                ('u1', 'l1', 'epoch1', 't3'), ('u1', 'l2', 'epoch1', None),
                ('u2', 'l3', 'other-epoch', 't4')])
            evidence = read_client_restart(conn, 'c1')
            self.assertEqual(len(evidence['receipts']), 2)
            self.assertNotIn('secret', json.dumps(evidence))
            self.assertTrue(milestone_flags({'client_restart': evidence})['client_restart_acknowledged'])
            self.assertEqual(read_client_restart(conn, 'c2')['receipts'], [])
            conn.execute("INSERT INTO ghost_part_events SELECT 'duplicate', created_at, payload_json, cycle_id, event_type, 2 FROM ghost_part_events")
            duplicate = read_client_restart(conn, 'c1')
            self.assertFalse(milestone_flags({'client_restart': duplicate})['client_restart_requested'])

    def test_canonical_hash_ignores_dictionary_order(self):
        self.assertEqual(
            canonical_hash({"b": 2, "a": {"d": 4, "c": 3}}),
            canonical_hash({"a": {"c": 3, "d": 4}, "b": 2}),
        )

    def test_changed_sections_is_top_level_and_stable(self):
        previous = {"cycle": {"status": "active"}, "pm2": {"ok": True}}
        current = {"cycle": {"status": "stabilizing"}, "pm2": {"ok": True}}
        self.assertEqual(changed_sections(previous, current), ["cycle"])

    def test_signal_milestones_require_canonical_cardinality(self):
        snapshot = {
            "conflict": {"status": "closed"},
            "cycle": {"status": "stabilizing"},
            "locks": [{"lock_snapshot_id": "lock-1"}],
            "signals": [{"signal_id": "signal-1"}],
            "events": {"counts": {"ghost.signal_sent": 1}},
            "shows": [{"show_id": "show-1"}],
            "rankings": [{"ranking_id": "ranking-1"}],
            "narrative": {
                "signal_task_count": 3,
                "signal_attempt_count": 1,
                "signal_candidate_count": 4,
                "signal_accepted_candidate_count": 3,
                "signal_quarantined_candidate_count": 1,
                "signal_receipt_count": 1,
                "signal_record_count": 1,
            },
            "settlement": {"next_cycles": []},
        }
        flags = milestone_flags(snapshot)
        for name in (
            "conflict_resolved",
            "cycle_locked",
            "signal_sent",
            "signal_tasks_3_durable",
            "signal_attempt_started",
            "signal_candidate_created",
            "signal_candidates_3_accepted",
            "signal_receipt_created",
            "signal_record_published",
            "ranking_created",
            "show_created",
            "cycle_stabilizing",
        ):
            self.assertTrue(flags[name], name)
        self.assertFalse(flags["cycle_closed"])
        self.assertFalse(flags["next_cycle_active"])

        snapshot["narrative"]["signal_task_count"] = 4
        snapshot["events"]["counts"]["ghost.signal_sent"] = 2
        flags = milestone_flags(snapshot)
        self.assertFalse(flags["signal_tasks_3_durable"])
        self.assertFalse(flags["signal_sent"])

    def test_atomic_summary_is_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "summary.json"
            atomic_json(target, {"ok": True, "text": "sygnał"})
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"ok": True, "text": "sygnał"},
            )
            self.assertEqual(list(target.parent.glob("*.tmp-*")), [])


if __name__ == "__main__":
    unittest.main()
