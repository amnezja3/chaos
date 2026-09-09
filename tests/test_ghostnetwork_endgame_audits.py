import os
import tempfile
import unittest

from ghostnetwork import GhostCycleService, GhostNetworkRepository
from scripts.audit_ghostnetwork_endgame import audit as postflight_audit
from scripts.audit_ghostnetwork_endgame_preflight import (
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


if __name__ == "__main__":
    unittest.main()
