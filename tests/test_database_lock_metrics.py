import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import db_connect
from tools.analyze_db_lock_metrics import LINE, percentile


class DatabaseLockMetricsTests(unittest.TestCase):
    def test_log_analyzer_contract(self):
        match = LINE.search(
            "[DB_LOCK] origin=claim_rebuild_job outcome=commit "
            "wait_ms=12 hold_ms=34 commit_ms=2 statements=3"
        )
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group("wait")), 12)
        self.assertEqual(percentile([1, 5, 9], .95), 9)

    def test_opt_in_metric_reports_writer_wait_and_hold(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3")
        handle.close()
        path = Path(handle.name)
        output = io.StringIO()
        try:
            with patch.dict(os.environ, {
                "CHAOS_DB_LOCK_METRICS": "1",
                "CHAOS_DB_LOCK_METRICS_MIN_MS": "0",
            }), contextlib.redirect_stdout(output):
                with db_connect(str(path)) as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS metric_probe (id INTEGER)")
                    conn.commit()
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("INSERT INTO metric_probe (id) VALUES (1)")
            line = output.getvalue()
            self.assertIn("[DB_LOCK]", line)
            self.assertIn("wait_ms=", line)
            self.assertIn("hold_ms=", line)
            self.assertIn("statements=1", line)
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(f"{path}{suffix}")
                if candidate.exists():
                    try:
                        candidate.unlink()
                    except PermissionError:
                        pass


if __name__ == "__main__":
    unittest.main()
