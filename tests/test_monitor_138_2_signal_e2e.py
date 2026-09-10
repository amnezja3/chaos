import json
from pathlib import Path
import tempfile
import unittest

from scripts.monitor_138_2_signal_e2e import (
    atomic_json,
    canonical_hash,
    changed_sections,
    milestone_flags,
)


class SignalE2EMonitorTest(unittest.TestCase):
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
