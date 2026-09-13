import os
import tempfile
import unittest
from unittest.mock import patch

import run
from database import DevBugReportStore, db_connect


class AdminBugReportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = DevBugReportStore(os.path.join(self.tmp.name, "bugs.sqlite3"))
        self.report = self.store.create_report({"title": "Błąd <script>", "description": "opis", "context": {"scene": "map"}}, "alice")
        self.patcher = patch.object(run, "dev_bug_report_store", self.store)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_player_cannot_list_search_patch_or_export(self):
        routes = [("/api/dev/bug-reports", "GET", run.api_dev_bug_reports),
                  ("/api/dev/bug-reports/similar", "GET", run.api_dev_bug_report_similar),
                  ("/api/dev/bug-reports/1", "PATCH", lambda: run.api_dev_bug_report_update(1)),
                  ("/api/admin/bug-reports/dump", "GET", run.api_admin_bug_reports_dump)]
        for user in (None, "alice"):
            for path, method, handler in routes:
                with run.app.test_request_context(path, method=method, json={"status": "fixed"}):
                    if user:
                        run.session["user"] = user
                    self.assertEqual(run.app.make_response(handler()).status_code, 403)
        self.assertEqual(self.store.list_reports()[0]["status"], "new")

    def test_create_forces_new_and_does_not_disclose_other_reports(self):
        with run.app.test_request_context("/api/dev/bug-reports", method="POST", json={"title": "Błąd", "status": "fixed"}), \
             patch.object(run, "require_dev_mode", return_value=None), \
             patch.object(run, "build_dev_bug_server_context", return_value={}):
            run.session["user"] = "bob"
            response = run.api_dev_bug_report_create().get_json()
            self.assertEqual(response["report"]["status"], "new")
            self.assertEqual(response["report"]["created_by"], "bob")
            self.assertNotIn("similar", response)

    def test_admin_status_and_complete_export(self):
        with run.app.test_request_context("/api/dev/bug-reports/1", method="PATCH", json={"status": "fixed"}):
            run.session["user"] = "admin"
            self.assertEqual(run.api_dev_bug_report_update(self.report["id"]).get_json()["report"]["status"], "fixed")
        with db_connect(self.store.db_path) as conn:
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(dev_bug_reports)") if row["name"] != "id"]
            names = ",".join(columns)
            for _ in range(9):
                conn.execute("INSERT INTO dev_bug_reports (" + names + ") SELECT " + names + " FROM dev_bug_reports")
        self.assertEqual(len(self.store.list_reports()), 200)
        with run.app.test_request_context("/api/admin/bug-reports/dump"):
            run.session["user"] = "admin"
            response = run.api_admin_bug_reports_dump()
            body = response.get_data(as_text=True)
            self.assertEqual(body.count('"title":'), 512)
            self.assertIn('"scene": "map"', body)
            self.assertIn("attachment", response.headers["Content-Disposition"])
            self.assertIn("Błąd", body)


if __name__ == "__main__":
    unittest.main()
