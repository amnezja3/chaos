import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.app_catalog_cleanup import (
    IMPORTANT_MAP_ACTIONS,
    cleanup_database,
    read_app_config,
)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class AppCatalogCleanupTests(unittest.TestCase):
    def make_db(self):
        tmp = tempfile.TemporaryDirectory()
        db_path = Path(tmp.name) / "game.sqlite3"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE json_resources (
                key TEXT PRIMARY KEY,
                source_path TEXT NOT NULL DEFAULT '',
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        apps = [
            {
                "id": "admin_test_scan_ports_1",
                "name": "Admin Scan Test",
                "map_actions_source": "admin_test_seed",
                "map_actions": ["scan_ports"],
                "price": 10,
            },
            {
                "id": "pencombo_v1",
                "name": "PenCombo",
                "map_actions_source": "migration_inferred",
                "map_actions": ["scan_ports", "exploit"],
                "price": 100,
            },
            {
                "id": "stable_seed_tool",
                "name": "Stable Seed Tool",
                "map_actions_source": "explicit_seed",
                "map_actions": ["trace"],
                "target_types": ["person"],
                "operation_types": ["generic_trace"],
                "resource_types": ["location_history"],
                "price": 200,
            },
            {
                "id": "user_alice_custom",
                "name": "Alice Custom",
                "generated": True,
                "source": "creator",
                "creator_username": "alice",
                "map_actions_source": "creator_explicit",
                "map_actions": ["scan_ports"],
                "target_types": ["router"],
                "operation_types": ["wifi_scanner"],
                "resource_types": ["internal_recon_state"],
                "price": 25,
            },
            {
                "id": "ghostlab_alice_1",
                "name": "Alice GhostLab",
                "ghostlab_generated": True,
                "source": "ghostlab",
                "type": "pro-system-tool",
                "category": "pro-system-tools",
                "price": 3000,
            },
        ]
        profile = {
            "nick": "CyberPhoenix",
            "apps": [
                apps[0],
                apps[3],
                apps[4],
            ],
            "files": {
                "tools": [
                    "Admin Scan Test.sh",
                    "Alice Custom.sh",
                    "Alice GhostLab.sh",
                    "Old Orphan.sh",
                ],
                "projects": ["Alice GhostLab.glab"],
            },
            "storage_capacity": 512,
            "storage_used": 999,
        }
        conn.execute(
            "INSERT INTO json_resources (key, source_path, value_json, updated_at) VALUES ('app_config', '', ?, 'now')",
            (dumps(apps),),
        )
        conn.execute(
            """
            INSERT INTO users (username, password, salt, profile_json, created_at, updated_at)
            VALUES ('admin', '', '', ?, 'now', 'now')
            """,
            (dumps(profile),),
        )
        conn.commit()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(conn.close)
        return tmp, db_path, conn

    def test_dry_run_does_not_change_database(self):
        tmp, _db_path, conn = self.make_db()
        before = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()[0]

        report = cleanup_database(conn, apply=False)
        after = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()[0]

        self.assertEqual(before, after)
        self.assertEqual(report["mode"], "dry-run")
        self.assertGreaterEqual(len(report["catalog_removed"]), 2)

    def test_apply_cleans_catalog_preserves_generated_and_ghostlab(self):
        tmp, _db_path, conn = self.make_db()

        report = cleanup_database(conn, apply=True)
        conn.commit()

        apps = read_app_config(conn)
        ids = {app["id"] for app in apps}
        self.assertNotIn("admin_test_scan_ports_1", ids)
        self.assertNotIn("pencombo_v1", ids)
        self.assertIn("user_alice_custom", ids)
        self.assertIn("ghostlab_alice_1", ids)
        self.assertIn("admin_seed_scan_ports_v1", ids)
        self.assertIn("admin_seed_audio_hack_v1", ids)

        stable = next(app for app in apps if app["id"] == "stable_seed_tool")
        self.assertEqual(stable["price"], 400)
        self.assertEqual(stable["price_adjustment"], "sprint31_x2")

        coverage = report["map_action_coverage"]
        missing = [action for action in IMPORTANT_MAP_ACTIONS if coverage.get(action, 0) < 1]
        self.assertEqual(missing, [])

    def test_apply_cleans_profiles_tools_and_recalculates_storage(self):
        tmp, _db_path, conn = self.make_db()

        cleanup_database(conn, apply=True)
        conn.commit()
        profile = json.loads(conn.execute(
            "SELECT profile_json FROM users WHERE username='admin'"
        ).fetchone()[0])

        app_ids = {app["id"] for app in profile["apps"]}
        self.assertNotIn("admin_test_scan_ports_1", app_ids)
        self.assertIn("user_alice_custom", app_ids)
        self.assertIn("ghostlab_alice_1", app_ids)
        self.assertNotIn("Admin Scan Test.sh", profile["files"]["tools"])
        self.assertNotIn("Old Orphan.sh", profile["files"]["tools"])
        self.assertIn("Alice Custom.sh", profile["files"]["tools"])
        self.assertIn("Alice GhostLab.glab", profile["files"]["projects"])
        self.assertNotEqual(profile["storage_used"], 999)


if __name__ == "__main__":
    unittest.main()
