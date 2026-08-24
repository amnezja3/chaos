import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools import repair_trollu2_identity as tool
from tools import repair_trollu2_profile as recovery


class Trollu2IdentityRepairTests(unittest.TestCase):
    def setUp(self):
        # Windows can retain an SQLite file handle briefly after connection
        # teardown; cleanup must not turn a passed DB-contract test into noise.
        self.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = str(Path(self.tempdir.name) / "game.sqlite3")
        self.profile = {
            "username": "trolu2",
            "nick": "NowyHaker",
            "avatar": "/static/images/default_avatar.png",
            "clan": "Echo Wolnosci",
            "fraction": {"id": "2", "name": "Echo Wolnosci", "role": "2"},
            "level": 50,
            "respect": 2560,
            "exp": "2217312.71 m² efektywne",
            "hackcoins": 250000,
            "inventory": [{"id": f"item-{i}"} for i in range(11)],
            "files": {"system": [], "personal": []},
            "apps": [{"id": f"app-{i}"} for i in range(11)],
            "hacked": [{"target_id": f"target-{i}"} for i in range(8)],
            "desktop_settings": {},
            "security": {},
            "territory_stats": {"effective_area": 2217312.71},
            "operations": [{"operation_id": "op-preserved"}],
        }
        self._create_database()

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_database(self):
        checksum = recovery.profile_checksum(self.profile)
        snapshot = recovery.lkg_snapshot_value(self.profile, top_level=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                f"""
                CREATE TABLE users (
                    username TEXT PRIMARY KEY, profile_json TEXT NOT NULL,
                    profile_revision INTEGER NOT NULL, profile_schema_version INTEGER NOT NULL,
                    profile_checksum TEXT NOT NULL, profile_integrity_status TEXT NOT NULL,
                    profile_validation_version INTEGER NOT NULL, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE profile_last_known_good (
                    username TEXT PRIMARY KEY, profile_revision INTEGER, schema_version INTEGER,
                    snapshot_json TEXT, checksum TEXT, source TEXT, created_at TEXT,
                    validation_version INTEGER
                );
                CREATE TABLE {recovery.RECOVERY_RECEIPTS_TABLE} (
                    plan_id TEXT PRIMARY KEY, canonical_username TEXT, plan_sha256 TEXT,
                    before_manifest_sha256 TEXT, status TEXT, expected_before_revision INTEGER,
                    expected_before_checksum TEXT, current_profile_revision INTEGER,
                    current_profile_checksum TEXT, current_wallet_version INTEGER,
                    result_json TEXT, created_at TEXT, updated_at TEXT, applied_at TEXT,
                    verified_at TEXT, promoted_at TEXT, rolled_back_at TEXT
                );
                CREATE TABLE profile_store_migrations (
                    migration_id TEXT, username TEXT, status TEXT, completed_at TEXT,
                    backup_json TEXT, PRIMARY KEY(migration_id, username)
                );
                CREATE TABLE wallet_balances (username TEXT PRIMARY KEY, balance INTEGER, version INTEGER);
                CREATE TABLE wallet_ledger (ledger_id TEXT PRIMARY KEY, username TEXT, amount_delta INTEGER);
                CREATE TABLE wallet_balance_events (event_id TEXT PRIMARY KEY, username TEXT, amount_delta INTEGER);
                CREATE TABLE player_apps (username TEXT, app_id TEXT, status TEXT);
                CREATE TABLE player_tool_files (username TEXT, tool_id TEXT);
                CREATE TABLE player_storage (username TEXT PRIMARY KEY, capacity INTEGER, used INTEGER, version INTEGER);
                CREATE TABLE captured_targets (id INTEGER PRIMARY KEY, owner_username TEXT, target_json TEXT);
                CREATE TABLE territory_target_ownership (target_id TEXT PRIMARY KEY, owner_username TEXT, ownership_version INTEGER);
                CREATE TABLE player_areas (id INTEGER PRIMARY KEY, owner_username TEXT, geometry_json TEXT);
                CREATE TABLE ghost_cycles (cycle_id TEXT PRIMARY KEY, status TEXT, state_version INTEGER);
                CREATE TABLE ghost_parts (part_id TEXT PRIMARY KEY, cycle_id TEXT, status TEXT);
                """
            )
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "trolu2", recovery.canonical_json(self.profile), 6, 1, checksum,
                    "valid", 1, "2026-06-28", "2026-08-24",
                ),
            )
            conn.execute(
                "INSERT INTO profile_last_known_good VALUES (?,?,?,?,?,?,?,?)",
                (
                    "trolu2", 6, 1, recovery.canonical_json(snapshot), recovery.digest(snapshot),
                    "sprint_130_11.verified_recovery", "2026-08-24", 1,
                ),
            )
            conn.execute(
                f"INSERT INTO {recovery.RECOVERY_RECEIPTS_TABLE} "
                "(plan_id,canonical_username,plan_sha256,status,current_profile_revision,"
                "current_profile_checksum,current_wallet_version,updated_at,promoted_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                ("recovery-final", "trolu2", "recovery-sha", "complete", 6, checksum, 121, "2026-08-24", "2026-08-24"),
            )
            historical = copy.deepcopy(self.profile)
            historical["nick"] = "Trolu 2"
            historical.pop("profession", None)
            conn.execute(
                "INSERT INTO profile_store_migrations VALUES (?,?,?,?,?)",
                (
                    "profile-store-v1", "trolu2", "verified", "2026-07-23",
                    recovery.canonical_json({"profile_json": recovery.canonical_json(historical)}),
                ),
            )
            conn.execute("INSERT INTO wallet_balances VALUES ('trolu2',250000,121)")
            conn.execute("INSERT INTO wallet_ledger VALUES ('ledger-1','trolu2',250000)")
            conn.execute("INSERT INTO wallet_balance_events VALUES ('event-1','trolu2',250000)")
            for index in range(11):
                conn.execute("INSERT INTO player_apps VALUES (?,?,?)", ("trolu2", f"app-{index}", "installed"))
                conn.execute("INSERT INTO player_tool_files VALUES (?,?)", ("trolu2", f"tool-{index}"))
            conn.execute("INSERT INTO player_storage VALUES ('trolu2',4352,273,533)")
            for index in range(8):
                conn.execute(
                    "INSERT INTO captured_targets VALUES (?,?,?)",
                    (index + 1, "trolu2", recovery.canonical_json({"target_id": f"recovery-{index}"})),
                )
                conn.execute(
                    "INSERT INTO territory_target_ownership VALUES (?,?,?)",
                    (f"recovery-{index}", "trolu2", 1),
                )
            conn.execute("INSERT INTO player_areas VALUES (1,'trolu2','tokio-area')")
            conn.execute("INSERT INTO ghost_cycles VALUES ('ghostnetwork_0001','active',200)")
            for index in range(20):
                conn.execute(
                    "INSERT INTO ghost_parts VALUES (?,?,?)",
                    (f"part-{index}", "ghostnetwork_0001", "pooled"),
                )

    def _plan(self):
        with recovery.readonly_connection(self.db_path) as conn:
            return tool.build_plan(conn)

    def _current_profile(self):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT profile_json, profile_revision, profile_checksum FROM users WHERE username='trolu2'"
            ).fetchone()
        return json.loads(row[0]), row[1], row[2]

    def test_audit_resolves_exact_avatar_and_historical_role_evidence(self):
        with recovery.readonly_connection(self.db_path) as conn:
            audit = tool.audit_identity(conn)
        self.assertEqual("/static/images/avatar-frakcja-2-player-2.png", audit["canonical_avatar_mapping"]["avatar"])
        self.assertTrue(audit["canonical_avatar_mapping"]["asset_exists"])
        self.assertTrue(audit["historical_evidence"]["nick_confirmed"])
        self.assertFalse(audit["historical_evidence"]["profession_explicitly_confirmed"])
        self.assertTrue(audit["historical_evidence"]["profession_correlated_by_fraction_role_2"])

    def test_field_level_apply_preserves_all_gameplay_state(self):
        plan = self._plan()
        before_profile, before_revision, _ = self._current_profile()
        before_external = plan["preconditions"]["external_invariants"]
        result = tool.apply_identity(self.db_path, plan, "test-operator")
        after_profile, after_revision, _ = self._current_profile()

        self.assertFalse(result["duplicate"])
        self.assertEqual("Trolu 2", after_profile["nick"])
        self.assertEqual("Socjotechnik", after_profile["profession"])
        self.assertEqual("/static/images/avatar-frakcja-2-player-2.png", after_profile["avatar"])
        self.assertEqual("Echo Wolnosci", after_profile["clan"])
        self.assertEqual(before_revision + 1, after_revision)
        self.assertEqual(tool.profile_invariant(before_profile), tool.profile_invariant(after_profile))
        with recovery.readonly_connection(self.db_path) as conn:
            self.assertEqual(before_external, tool.external_invariants(conn))
            verification = tool.verify_identity(conn, plan)
        self.assertTrue(verification["ok"], verification["blockers"])
        self.assertEqual(50, verification["profile"]["level"])
        self.assertEqual(2560, verification["profile"]["respect"])
        self.assertEqual(250000, verification["profile"]["hackcoins"])
        self.assertTrue(verification["inventory"]["expected_11_11"])

    def test_duplicate_apply_is_exactly_once(self):
        plan = self._plan()
        first = tool.apply_identity(self.db_path, plan, "test-operator")
        second = tool.apply_identity(self.db_path, plan, "test-operator")
        _, revision, checksum = self._current_profile()
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["profile_revision"], revision)
        self.assertEqual(first["profile_checksum"], checksum)
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(f"SELECT COUNT(*) FROM {tool.RECEIPTS_TABLE}").fetchone()[0]
        self.assertEqual(1, count)

    def test_profile_cas_drift_fails_closed(self):
        plan = self._plan()
        changed = copy.deepcopy(self.profile)
        changed["operations"].append({"operation_id": "new-gameplay"})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile_json=?, profile_revision=7, profile_checksum=? WHERE username='trolu2'",
                (recovery.canonical_json(changed), recovery.profile_checksum(changed)),
            )
        with self.assertRaisesRegex(tool.IdentityRepairError, "REPLAN_REQUIRED"):
            tool.apply_identity(self.db_path, plan, "test-operator")
        with sqlite3.connect(self.db_path) as conn:
            self.assertNotIn(tool.RECEIPTS_TABLE, {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            })

    def test_external_gameplay_drift_fails_closed(self):
        plan = self._plan()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE wallet_balances SET version=version+1 WHERE username='trolu2'")
        with self.assertRaisesRegex(tool.IdentityRepairError, "GAMEPLAY_STATE_CHANGED"):
            tool.apply_identity(self.db_path, plan, "test-operator")
        profile, revision, _ = self._current_profile()
        self.assertEqual(6, revision)
        self.assertEqual("NowyHaker", profile["nick"])

    def test_verified_identity_promotes_lkg_and_is_idempotent(self):
        plan = self._plan()
        applied = tool.apply_identity(self.db_path, plan, "test-operator")
        promoted = tool.promote_lkg(self.db_path, plan, applied["profile_checksum"])
        duplicate = tool.promote_lkg(self.db_path, plan, applied["profile_checksum"])
        self.assertFalse(promoted["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        with recovery.readonly_connection(self.db_path) as conn:
            verification = tool.verify_identity(conn, plan)
            lkg = conn.execute(
                "SELECT profile_revision, snapshot_json, source FROM profile_last_known_good WHERE username='trolu2'"
            ).fetchone()
        snapshot = json.loads(lkg["snapshot_json"])
        self.assertTrue(verification["ok"], verification["blockers"])
        self.assertTrue(verification["lkg_matches_identity_profile"])
        self.assertEqual("Trolu 2", snapshot["nick"])
        self.assertEqual("Socjotechnik", snapshot["profession"])
        self.assertEqual("/static/images/avatar-frakcja-2-player-2.png", snapshot["avatar"])
        self.assertEqual("sprint_130_11.identity_repair", lkg["source"])

    def test_runtime_does_not_import_identity_operator_tool(self):
        needle = "repair_trollu2_identity"
        runtime_paths = [
            Path(tool.ROOT) / "run.py",
            Path(tool.ROOT) / "scripts" / "territory_conflict_worker.py",
        ]
        for path in runtime_paths:
            self.assertNotIn(needle, path.read_text(encoding="utf-8"), str(path))


if __name__ == "__main__":
    unittest.main()
