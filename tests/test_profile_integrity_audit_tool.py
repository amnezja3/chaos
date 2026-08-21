import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools import audit_profile_integrity as audit


class ProfileIntegrityAuditToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_profile_audit_"))
        self.db_path = self.tmpdir / "game.sqlite3"
        self.username = "forensic-user"
        self.profile = {
            "username": self.username,
            "password": "secret-password-hash",
            "salt": "secret-salt",
            "level": 12,
            "hackcoins": 4200,
            "respect": 77,
            "exp": "123 m2",
            "apps": [{"id": "app-one"}],
            "files": {"tools": [{"id": "tool-one", "app_id": "app-one"}]},
            "hacked": [],
            "desktop_settings": {},
            "security": {},
            "territory_stats": {},
            "operations": [],
            "launch_queue": [],
            "googleplex_products": [],
            "product_purchases": [],
            "market_history": [],
        }
        self._create_fixture()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_fixture(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE wallet_balances (
                username TEXT PRIMARY KEY,
                balance INTEGER NOT NULL,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE wallet_balance_events (
                event_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                transaction_key TEXT NOT NULL,
                amount_delta INTEGER NOT NULL,
                balance INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE wallet_ledger (
                ledger_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount_delta INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                peer_username TEXT NOT NULL,
                note TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_username TEXT NOT NULL,
                to_username TEXT NOT NULL,
                amount INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE player_apps (
                username TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_json TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, app_id)
            );
            CREATE TABLE player_tool_files (
                username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                tool_json TEXT NOT NULL,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, tool_id)
            );
            CREATE TABLE player_storage (
                username TEXT PRIMARY KEY,
                capacity INTEGER NOT NULL,
                used INTEGER NOT NULL,
                unit TEXT NOT NULL,
                modifiers_json TEXT NOT NULL,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        now = "2026-08-21T12:00:00"
        conn.execute(
            """
            INSERT INTO users(username, password, salt, profile_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self.username,
                self.profile["password"],
                self.profile["salt"],
                json.dumps(self.profile),
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO wallet_balances VALUES (?, 4200, 1, ?)",
            (self.username, now),
        )
        conn.execute(
            "INSERT INTO wallet_balance_events VALUES ('event-1', ?, 'seed', 4200, 4200, 'seed', ?)",
            (self.username, now),
        )
        conn.execute(
            """
            INSERT INTO wallet_ledger VALUES
            ('ledger-1', ?, 'wallet.seed', 4200, 4200, 'test', 'seed', '', '',
             'wallet:test:seed', '{}', ?)
            """,
            (self.username, now),
        )
        conn.execute(
            "INSERT INTO player_apps VALUES (?, 'app-one', '{}', 'installed', 1, ?)",
            (self.username, now),
        )
        conn.execute(
            "INSERT INTO player_tool_files VALUES (?, 'tool-one', 'app-one', '{}', 1, ?)",
            (self.username, now),
        )
        conn.execute(
            "INSERT INTO player_storage VALUES (?, 0, 0, 'MB', '{}', 1, ?)",
            (self.username, now),
        )
        conn.commit()
        conn.close()

    def _database_checksum(self):
        return hashlib.sha256(self.db_path.read_bytes()).hexdigest()

    def _replace_profile_json(self, raw):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE users SET profile_json = ? WHERE username = ?",
            (raw, self.username),
        )
        conn.commit()
        conn.close()

    def test_connection_is_query_only_and_database_bytes_do_not_change(self):
        before = self._database_checksum()
        with audit.open_read_only_database(self.db_path) as (conn, _path):
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("CREATE TABLE forbidden_write(id INTEGER)")
        self.assertEqual(self._database_checksum(), before)

    def test_audit_is_redacted_and_reports_consistent_stores(self):
        report = audit.audit_report(str(self.db_path), self.username)

        self.assertTrue(report["exact_match"])
        self.assertEqual(report["profile"]["state"], "valid")
        self.assertEqual(report["wallet"]["profile_balance"], 4200)
        self.assertEqual(report["wallet"]["balance_store"]["balance"], 4200)
        self.assertEqual(report["wallet"]["ledger"]["latest_balance_after"], 4200)
        self.assertEqual(report["inventory"]["differences"]["profile_only_apps"], 0)
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(self.username, serialized)
        self.assertNotIn("secret-password-hash", serialized)
        self.assertNotIn("secret-salt", serialized)
        self.assertNotIn("app-one", serialized)
        self.assertNotIn("tool-one", serialized)

    def test_invalid_json_is_not_converted_to_empty_profile(self):
        self._replace_profile_json('{"username":"forensic-user"')

        report = audit.audit_report(str(self.db_path), self.username)

        self.assertEqual(report["profile"]["state"], "invalid_json")
        self.assertIn("profile_json_decode_failed", report["profile"]["issues"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["probe_status"], "complete")
        self.assertEqual(report["account_integrity_status"], "blocked")
        self.assertGreater(report["blocking_findings"], 0)

    def test_partial_profile_requires_recovery_without_template_sync(self):
        partial = json.dumps({"username": self.username, "level": 12})
        self._replace_profile_json(partial)
        before = self._database_checksum()

        report = audit.audit_report(str(self.db_path), self.username)

        self.assertEqual(report["profile"]["state"], "recovery_required")
        self.assertIn("missing:hackcoins", report["profile"]["issues"])
        self.assertEqual(self._database_checksum(), before)

    def test_status_aggregates_states_without_names(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO users(username, password, salt, profile_json, created_at, updated_at)
            VALUES ('broken-user', '', '', '{', '2026-08-21', '2026-08-21')
            """
        )
        conn.commit()
        conn.close()

        default_report = audit.status_report(str(self.db_path))
        report = audit.status_report(str(self.db_path), scan_all_profiles=True)

        self.assertFalse(default_report["profile_scan"]["performed"])
        self.assertEqual(default_report["profile_states"], {})
        self.assertEqual(default_report["total_users"], 2)
        self.assertTrue(report["profile_scan"]["performed"])
        self.assertEqual(report["profile_states"]["valid"], 1)
        self.assertEqual(report["profile_states"]["invalid_json"], 1)
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("broken-user", serialized)
        self.assertNotIn(self.username, serialized)

    def test_parser_accepts_database_before_or_after_command(self):
        parser = audit.build_parser()
        before = parser.parse_args(["--db", "before.sqlite3", "status"])
        after = parser.parse_args(["status", "--db", "after.sqlite3", "--scan-all-profiles"])
        self.assertEqual(before.db, "before.sqlite3")
        self.assertEqual(after.db, "after.sqlite3")
        self.assertTrue(after.scan_all_profiles)

    def test_inventory_accepts_string_tool_and_ignores_uninstalled_app(self):
        profile = dict(self.profile)
        profile["files"] = {"tools": ["tool-one"]}
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE users SET profile_json = ? WHERE username = ?",
            (json.dumps(profile), self.username),
        )
        conn.execute(
            "INSERT INTO player_apps VALUES (?, 'old-app', '{}', 'uninstalled', 2, ?)",
            (self.username, "2026-08-21T12:01:00"),
        )
        conn.commit()
        conn.close()

        report = audit.audit_report(str(self.db_path), self.username)

        self.assertEqual(report["inventory"]["differences"]["profile_only_tools"], 0)
        self.assertEqual(report["inventory"]["differences"]["store_only_tools"], 0)
        self.assertEqual(report["inventory"]["differences"]["store_only_apps"], 0)
        self.assertEqual(report["inventory"]["canonical_store"]["uninstalled_apps_count"], 1)

    def test_wallet_uses_delta_sum_and_marks_same_timestamp_tail_ambiguous(self):
        profile = dict(self.profile)
        profile["hackcoins"] = 4300
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE users SET profile_json = ? WHERE username = ?",
            (json.dumps(profile), self.username),
        )
        conn.execute(
            "UPDATE wallet_balances SET balance = 4300, version = 2 WHERE username = ?",
            (self.username,),
        )
        conn.execute(
            """
            INSERT INTO wallet_ledger VALUES
            ('ledger-2', ?, 'wallet.credit', 100, 4300, 'test', 'credit', '', '',
             'wallet:test:credit', '{}', '2026-08-21T12:00:00')
            """,
            (self.username,),
        )
        conn.commit()
        conn.close()

        report = audit.audit_report(str(self.db_path), self.username)

        self.assertEqual(report["wallet"]["ledger"]["delta_sum"], 4300)
        self.assertTrue(report["wallet"]["ledger"]["tail_order_ambiguous"])
        self.assertNotIn(
            "wallet_store_ledger_sum_mismatch",
            {item["code"] for item in report["findings"]},
        )

    def test_optional_schema_drift_is_reported_without_crashing(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE player_areas(owner_username TEXT)")
        conn.commit()
        conn.close()

        report = audit.audit_report(str(self.db_path), self.username)

        self.assertFalse(report["territory"]["schema"]["areas"]["schema_supported"])
        self.assertIn("created_at", report["territory"]["schema"]["areas"]["missing_columns"])
        self.assertEqual(report["territory"]["scope_status"], "unknown")

    def test_ghostnetwork_reward_history_is_compared_with_applied_ledger(self):
        profile = dict(self.profile)
        profile["ghostnetwork_reward_history"] = [{"reward_key": "reward-one"}]
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE users SET profile_json = ? WHERE username = ?",
            (json.dumps(profile), self.username),
        )
        conn.execute(
            """
            CREATE TABLE ghost_reward_ledger (
                player_id TEXT NOT NULL,
                reward_key TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                applied_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO ghost_reward_ledger VALUES (?, 'reward-one', 'part_discovered', 'event-one', 'applied', ?, ?)",
            (self.username, "2026-08-21T12:00:00", "2026-08-21T12:00:01"),
        )
        conn.commit()
        conn.close()

        matching = audit.audit_report(str(self.db_path), self.username)
        self.assertEqual(
            matching["ghostnetwork"]["user"]["reward_history_projection"]["ledger_only_count"],
            0,
        )
        self.assertEqual(
            matching["ghostnetwork"]["user"]["reward_timelines_by_type"]["part_discovered"]["count"],
            1,
        )

        profile["ghostnetwork_reward_history"] = []
        self._replace_profile_json(json.dumps(profile))
        mismatching = audit.audit_report(str(self.db_path), self.username)
        self.assertIn(
            "ghostnetwork_reward_history_projection_mismatch",
            {item["code"] for item in mismatching["account_findings"]},
        )
        self.assertEqual(mismatching["account_integrity_status"], "blocked")

    def test_sparse_activation_overwrite_signature_is_account_blocker(self):
        profile = dict(self.profile)
        profile.update({
            "level": 1,
            "hackcoins": 1000,
            "respect": 5,
            "ghostnetwork_reward_history": [{"reward_key": "activation-reward"}],
        })
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
            (json.dumps(profile), "2026-08-21T12:00:02", self.username),
        )
        conn.execute(
            """
            CREATE TABLE captured_targets (
                owner_username TEXT NOT NULL,
                stationary INTEGER NOT NULL,
                generated INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO captured_targets VALUES (?, 1, 0, '2026-08-21T12:00:00')",
            (self.username,),
        )
        conn.execute(
            """
            CREATE TABLE ghost_part_events (
                event_id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                audience_scope TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO ghost_part_events VALUES ('activation-event', ?, 'ghost.part_activated', 'clan', '2026-08-21T12:00:00')",
            (self.username,),
        )
        conn.execute(
            """
            CREATE TABLE ghost_reward_ledger (
                player_id TEXT NOT NULL,
                reward_key TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                applied_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ghost_reward_ledger VALUES
            (?, 'activation-reward', 'part_first_activated', 'activation-event',
             'applied', '2026-08-21T12:00:01', '2026-08-21T12:00:01')
            """,
            (self.username,),
        )
        conn.commit()
        conn.close()

        report = audit.audit_report(str(self.db_path), self.username)

        signal = report["ghostnetwork"]["user"]["sparse_activation_overwrite_signal"]
        self.assertTrue(signal["strong_signature"])
        self.assertEqual(signal["matched_activation_reward_count"], 1)
        self.assertEqual(signal["nearest_profile_update_distance_seconds"], 1.0)
        self.assertIn(
            "ghostnetwork_sparse_activation_overwrite_signature",
            {item["code"] for item in report["account_findings"]},
        )
        self.assertEqual(report["account_integrity_status"], "blocked")

    def test_missing_database_is_not_created(self):
        missing = self.tmpdir / "missing.sqlite3"
        with self.assertRaises(FileNotFoundError):
            audit.status_report(str(missing))
        self.assertFalse(missing.exists())

    def test_verify_exit_one_means_account_blocker_not_probe_failure(self):
        self._replace_profile_json("{")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = audit.main([
                "verify", "--db", str(self.db_path), "--username", self.username,
            ])

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertTrue(report["ok"])
        self.assertEqual(report["probe_status"], "complete")
        self.assertEqual(report["account_integrity_status"], "blocked")

    def test_verify_partial_evidence_without_account_blocker_exits_zero_but_stays_unknown(self):
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = audit.main([
                "verify", "--db", str(self.db_path), "--username", self.username,
            ])

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["evidence_status"], "partial")
        self.assertEqual(report["account_integrity_status"], "unknown")
        self.assertEqual(report["blocking_findings"], 0)

    def test_verify_exit_two_for_unsupported_users_schema(self):
        drifted = self.tmpdir / "drifted.sqlite3"
        conn = sqlite3.connect(drifted)
        conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO users VALUES (?)", (self.username,))
        conn.commit()
        conn.close()
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = audit.main([
                "verify", "--db", str(drifted), "--username", self.username,
            ])

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(report["evidence_status"], "unavailable")
        self.assertTrue(report["tool_schema_blocked"])


if __name__ == "__main__":
    unittest.main()
