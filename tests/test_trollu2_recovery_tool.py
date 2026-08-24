from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from tools import repair_trollu2_profile as tool


class Trollu2RecoveryToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = str(Path(self.temp.name) / "game.sqlite3")
        self._create_database()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _create_database(self):
        profile = {
            "username": tool.CANONICAL_USERNAME,
            "password": "secret-not-reported",
            "salt": "salt-not-reported",
            "level": 2,
            "respect": 25,
            "hackcoins": 1000,
            "inventory": [],
            "files": {"tools": []},
            "apps": [],
            "hacked": [],
            "desktop_settings": {},
            "security": {},
            "territory_stats": {},
            "exp": "0.0 m² efektywne",
        }
        checksum = tool.profile_checksum(profile)
        with self.connect() as conn:
            conn.executescript(
                """
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
                CREATE TABLE wallet_balances (username TEXT PRIMARY KEY, balance INTEGER, version INTEGER, updated_at TEXT);
                CREATE TABLE wallet_ledger (
                    ledger_id TEXT PRIMARY KEY, username TEXT, event_type TEXT,
                    amount_delta INTEGER, balance_after INTEGER, source TEXT, source_id TEXT,
                    peer_username TEXT, note TEXT, dedupe_key TEXT UNIQUE,
                    payload_json TEXT, created_at TEXT
                );
                CREATE TABLE wallet_balance_events (
                    event_id TEXT PRIMARY KEY, username TEXT, transaction_key TEXT,
                    amount_delta INTEGER, balance INTEGER, version INTEGER,
                    reason TEXT, created_at TEXT, UNIQUE(username, transaction_key)
                );
                CREATE TABLE player_apps (
                    username TEXT, app_id TEXT, installed INTEGER, app_json TEXT,
                    status TEXT, updated_at TEXT
                );
                CREATE TABLE player_tool_files (
                    username TEXT, tool_id TEXT, app_id TEXT, file_json TEXT,
                    tool_json TEXT, updated_at TEXT
                );
                CREATE TABLE player_storage (
                    username TEXT PRIMARY KEY, capacity INTEGER, used INTEGER, unit TEXT,
                    version INTEGER, updated_at TEXT, modifiers_json TEXT
                );
                CREATE TABLE system_messages (
                    message_id TEXT PRIMARY KEY, username TEXT, dedupe_key TEXT,
                    source TEXT, payload_json TEXT, created_at TEXT
                );
                CREATE TABLE captured_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT,
                    stationary INTEGER, updated_at TEXT, lat REAL, lng REAL,
                    label TEXT, name TEXT, icon TEXT, source_type TEXT,
                    generated INTEGER, target_json TEXT, captured_at TEXT
                );
                CREATE TABLE territory_target_ownership (
                    target_id TEXT PRIMARY KEY, owner_username TEXT, ownership_version INTEGER,
                    lat REAL, lng REAL, label TEXT, target_json TEXT, updated_at TEXT
                );
                CREATE TABLE player_areas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT,
                    vertices_json TEXT, area_size REAL,
                    status TEXT, updated_at TEXT
                );
                CREATE TABLE territory_area_publications (
                    owner_username TEXT PRIMARY KEY, payload_json TEXT, updated_at TEXT
                );
                CREATE TABLE territory_rebuild_jobs (
                    job_id TEXT PRIMARY KEY, owner_username TEXT, reason TEXT,
                    target_id TEXT, target_json TEXT, status TEXT, error TEXT DEFAULT '',
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE territory_progression_receipts (
                    receipt_id TEXT PRIMARY KEY, actor_username TEXT, status TEXT
                );
                CREATE TABLE territory_conflicts (
                    conflict_id TEXT PRIMARY KEY, participants_json TEXT DEFAULT '[]',
                    targets_json TEXT DEFAULT '[]', intersections_json TEXT,
                    intersection_json TEXT, status TEXT, conflict_version INTEGER DEFAULT 1,
                    geometry_status TEXT DEFAULT 'clean', resolution_reason TEXT DEFAULT '',
                    source_event TEXT DEFAULT '', last_actor_username TEXT DEFAULT '',
                    created_at TEXT, updated_at TEXT, resolved_at TEXT
                );
                CREATE TABLE territory_conflict_pillars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, conflict_id TEXT, target_id TEXT,
                    status TEXT, captured INTEGER, public_target_json TEXT
                );
                CREATE TABLE territory_conflict_events (
                    event_id TEXT PRIMARY KEY, conflict_id TEXT, event_type TEXT,
                    action_id TEXT, actor_username TEXT
                );
                CREATE TABLE territory_conflict_rebuilds (
                    conflict_id TEXT PRIMARY KEY, requested_version INTEGER,
                    status TEXT, reason TEXT, lease_owner TEXT DEFAULT '', lease_until TEXT,
                    requested_at TEXT, updated_at TEXT
                );
                CREATE TABLE territory_conflict_fronts (
                    front_id TEXT PRIMARY KEY, conflict_id TEXT, status TEXT
                );
                CREATE TABLE territory_conflict_engagements (
                    engagement_id TEXT PRIMARY KEY, status TEXT
                );
                CREATE TABLE territory_conflict_engagement_members (
                    engagement_id TEXT, conflict_id TEXT, front_id TEXT
                );
                CREATE TABLE ghost_cycles (
                    cycle_id TEXT PRIMARY KEY, status TEXT, state_version INTEGER, updated_at TEXT
                );
                CREATE TABLE ghost_parts (
                    part_id TEXT PRIMARY KEY, cycle_id TEXT, status TEXT, latitude REAL,
                    longitude REAL, target_id TEXT, territory_id TEXT,
                    territory_owner_id TEXT, conflict_id TEXT, updated_at TEXT
                );
                CREATE TABLE ghost_capture_effects (status TEXT);
                CREATE TABLE ghostnetwork_territory_jobs (status TEXT);
                CREATE TABLE ghostnetwork_delta_delivery_jobs (status TEXT);
                CREATE TABLE session_generation_lineages (username TEXT PRIMARY KEY);
                """
            )
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)",
                (tool.CANONICAL_USERNAME, tool.canonical_json(profile), 7, 1, checksum,
                 "valid", 1, "2026-01-01", "2026-01-02"),
            )
            lkg = {"username": tool.CANONICAL_USERNAME, "files": {"tools": []}}
            conn.execute(
                "INSERT INTO profile_last_known_good VALUES (?,?,?,?,?,?,?,?)",
                (tool.CANONICAL_USERNAME, 7, 1, tool.canonical_json(lkg),
                 tool.digest(lkg), "bootstrap", "2026-01-02", 1),
            )
            conn.execute("INSERT INTO wallet_balances VALUES (?,?,?,?)", (tool.CANONICAL_USERNAME, 1000, 4, "2026-01-02"))
            conn.execute(
                "INSERT INTO wallet_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("before-ledger", tool.CANONICAL_USERNAME, "bootstrap", 1000, 1000,
                 "bootstrap", "", "", "", "before-ledger", "{}", "2026-01-02"),
            )
            conn.execute(
                "INSERT INTO wallet_balance_events VALUES (?,?,?,?,?,?,?,?)",
                ("before-event", tool.CANONICAL_USERNAME, "before-event", 1000, 1000,
                 4, "bootstrap", "2026-01-02"),
            )
            for app_id, name in (("app_nmap", "Nmap"), ("app_metasploit", "Metasploit")):
                conn.execute(
                    "INSERT INTO player_apps VALUES (?,?,1,?,'installed','2026-01-02')",
                    (tool.CANONICAL_USERNAME, app_id, tool.canonical_json({"id": app_id, "name": name})),
                )
                conn.execute(
                    "INSERT INTO player_tool_files VALUES (?,?,?,?,?,'2026-01-02')",
                    (tool.CANONICAL_USERNAME, name + ".sh", app_id,
                     tool.canonical_json({"id": name + ".sh", "name": name + ".sh"}),
                     tool.canonical_json({"id": name + ".sh", "name": name + ".sh"})),
                )
            conn.execute(
                "INSERT INTO player_storage VALUES (?,?,?,?,?,?,?)",
                (tool.CANONICAL_USERNAME, 1024, 20, "MB", 2, "2026-01-02", "{}"),
            )
            for index, app_id in enumerate(("app_metasploit", "app_nmap")):
                dedupe = f"googleplex_app_install:{tool.CANONICAL_USERNAME}:{app_id}"
                payload = {"dedupe_key": dedupe}
                conn.execute(
                    "INSERT INTO system_messages VALUES (?,?,?,?,?,?)",
                    (f"install-{index}", tool.CANONICAL_USERNAME, dedupe,
                     "googleplex_install", tool.canonical_json(payload), f"2026-02-0{2-index}"),
                )
            travel = {
                "product_id": "ticket_tokio",
                "effects": [{"type": "travel_city", "city": "Tokio", "lat": 35.6762, "lng": 139.6503}],
            }
            conn.execute(
                "INSERT INTO system_messages VALUES (?,?,?,?,?,?)",
                ("travel-1", tool.CANONICAL_USERNAME, "ticket-tokio", "googleplex_product",
                 tool.canonical_json(travel), "2026-02-03"),
            )
            conn.execute("INSERT INTO ghost_cycles VALUES ('ghostnetwork_0001','active',3,'2026-02-03')")
            for index in range(20):
                conn.execute(
                    "INSERT INTO ghost_parts VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (f"part-{index}", "ghostnetwork_0001", "pooled", None, None, "", "", "", "", "2026-02-03"),
                )

    def build_plan(self):
        with tool.readonly_connection(self.db_path) as conn:
            return tool.build_plan(conn, self.db_path)

    def build_plan_and_manifest(self):
        plan = self.build_plan()
        with tool.readonly_connection(self.db_path) as conn:
            manifest = tool.build_before_manifest(conn, self.db_path, plan)
        return plan, manifest

    def start_recovery(self):
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        tool.apply_level_step(self.db_path, plan)
        for city in plan["territory_recovery"]["cities"]:
            tool.atomic_city_grant(self.db_path, plan, city)
        return plan, manifest

    def complete_recovery_jobs(self, plan):
        with self.connect() as conn:
            for city in plan["territory_recovery"]["cities"]:
                vertices = [
                    {"lat": target["lat"], "lng": target["lng"]}
                    for target in city["targets"]
                ]
                conn.execute(
                    "INSERT INTO player_areas "
                    "(owner_username, vertices_json, area_size, status, updated_at) "
                    "VALUES (?, ?, ?, 'active', '2026-02-04')",
                    (tool.CANONICAL_USERNAME, tool.canonical_json(vertices), 500000.0),
                )
                conn.execute(
                    "UPDATE territory_rebuild_jobs SET status='complete', updated_at='2026-02-04' "
                    "WHERE job_id=?",
                    (city["rebuild_job_id"],),
                )

    def test_status_audit_plan_and_dry_run_do_not_write_database(self):
        before = Path(self.db_path).read_bytes()
        with tool.readonly_connection(self.db_path) as conn:
            tool.require_schema(conn)
            tool.audit_snapshot(conn, self.db_path)
            plan = tool.build_plan(conn, self.db_path)
            self.assertEqual([], tool.validate_plan_against_current(conn, self.db_path, plan))
        self.assertEqual(before, Path(self.db_path).read_bytes())

    def test_audit_reads_only_exact_subject_profile(self):
        other = {"username": "other", "level": 99}
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)",
                ("other", "not-valid-json", 1, 1, tool.digest(other), "valid", 1, "", ""),
            )
        with tool.readonly_connection(self.db_path) as conn:
            report = tool.audit_snapshot(conn, self.db_path)
        self.assertTrue(report["ready_for_plan"])
        self.assertEqual(0, report["heavy_profile_audit"]["other_profile_full_reads"])
        self.assertEqual(0, report["heavy_profile_audit"]["all_profile_scans"])

    def test_wrong_case_only_account_is_rejected(self):
        with self.connect() as conn:
            conn.execute("UPDATE users SET username='Trollu2' WHERE username='trolu2'")
        with tool.readonly_connection(self.db_path) as conn:
            with self.assertRaises(tool.RecoveryGateError):
                tool.exact_user_row(conn)

    def test_plan_preserves_canonical_inventory_and_two_proven_installs(self):
        plan = self.build_plan()
        self.assertEqual(2, len(plan["preserve"]["apps"]))
        self.assertEqual(2, len(plan["preserve"]["tools"]))
        installs = plan["preserve"]["recent_googleplex_installs"]
        self.assertEqual({"app_nmap", "app_metasploit"}, {item["app_id"] for item in installs})
        self.assertTrue(all(item["canonical_inventory_match"] for item in installs))

    def test_missing_recent_install_evidence_blocks_plan(self):
        with self.connect() as conn:
            conn.execute("DELETE FROM system_messages WHERE message_id='install-0'")
        with tool.readonly_connection(self.db_path) as conn:
            with self.assertRaises(tool.RecoveryGateError):
                tool.build_plan(conn, self.db_path)

    def test_targets_are_stable_unique_and_stationary(self):
        first = self.build_plan()
        second = self.build_plan()
        first_targets = first["territory_recovery"]["cities"][0]["targets"]
        second_targets = second["territory_recovery"]["cities"][0]["targets"]
        self.assertEqual(
            [item["target_id"] for item in first_targets],
            [item["target_id"] for item in second_targets],
        )
        self.assertEqual(tool.PILLARS_PER_CITY, len({item["target_id"] for item in first_targets}))
        self.assertTrue(all(item["stationary"] for item in first_targets))

    def test_existing_territory_triggers_deterministic_relocation(self):
        polygon = [
            {"lat": 35.64, "lng": 139.61}, {"lat": 35.64, "lng": 139.69},
            {"lat": 35.71, "lng": 139.69}, {"lat": 35.71, "lng": 139.61},
        ]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO player_areas (owner_username, vertices_json, area_size, status, updated_at) VALUES (?,?,?,?,?)",
                ("foreign", tool.canonical_json(polygon), 1, "active", "2026-02-03"),
            )
        plan = self.build_plan()
        city = plan["territory_recovery"]["cities"][0]
        self.assertTrue(city["relocation"]["applied"])
        self.assertEqual([], city["collisions"])

    def test_collision_preview_uses_existing_subject_pillars_and_worker_geometry(self):
        center = {"city": "Tokio", "lat": 35.6762, "lng": 139.6503}
        targets = tool.recovery_targets("preview-plan", center)
        old_targets = [
            {
                "target_id": "old-tokio-pillar-a", "lat": 35.7200,
                "lng": 139.6400, "label": "old-a", "stationary": True,
            },
            {
                "target_id": "old-tokio-pillar-b", "lat": 35.7400,
                "lng": 139.6600, "label": "old-b", "stationary": True,
            },
            {
                "target_id": "old-tokio-pillar-c", "lat": 35.7700,
                "lng": 139.6400, "label": "old-c", "stationary": True,
            },
        ]
        foreign_polygon = [
            {"lat": 35.725, "lng": 139.645},
            {"lat": 35.725, "lng": 139.655},
            {"lat": 35.735, "lng": 139.655},
            {"lat": 35.735, "lng": 139.645},
        ]
        with self.connect() as conn:
            for old_target in old_targets:
                conn.execute(
                    "INSERT INTO captured_targets "
                    "(owner_username, stationary, updated_at, lat, lng, label, name, icon, "
                    "source_type, generated, target_json, captured_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        tool.CANONICAL_USERNAME, 1, "2026-02-03",
                        old_target["lat"], old_target["lng"],
                        old_target["label"], old_target["label"], "", "scan", 0,
                        tool.canonical_json(old_target), "2026-02-03",
                    ),
                )
            conn.execute(
                "INSERT INTO player_areas "
                "(owner_username, vertices_json, area_size, status, updated_at) "
                "VALUES (?,?,?,?,?)",
                ("pies1", tool.canonical_json(foreign_polygon), 1, "active", "2026-02-03"),
            )
        with tool.readonly_connection(self.db_path) as conn:
            preview = tool.canonical_subject_area_preview(conn, targets)
            findings = tool.collision_findings(conn, targets)
        self.assertTrue(preview)
        self.assertIn(
            "canonical_worker_area_conflict:pies1",
            {item["reason"] for item in findings},
        )
        plan = self.build_plan()
        self.assertFalse(plan["ready_for_dry_run"])
        self.assertIn("level_50_existing_geometry_conflict", plan["blockers"])
        self.assertEqual(
            "level_50_existing_geometry_conflict",
            plan["territory_recovery"]["cities"][0]["relocation"]["reason"],
        )

    def test_tampered_plan_signature_is_rejected(self):
        plan = self.build_plan()
        plan["final_state"]["wallet_balance"] += 1
        path = Path(self.temp.name) / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaises(tool.RecoveryGateError):
            tool.load_plan(str(path))

    def test_stale_profile_revision_blocks_dry_run(self):
        plan = self.build_plan()
        with self.connect() as conn:
            conn.execute("UPDATE users SET profile_revision=profile_revision+1 WHERE username=?", (tool.CANONICAL_USERNAME,))
        with tool.readonly_connection(self.db_path) as conn:
            blockers = tool.validate_plan_against_current(conn, self.db_path, plan)
        self.assertIn("profile_revision_changed", blockers)

    def test_ghostnetwork_must_have_twenty_parts(self):
        with self.connect() as conn:
            conn.execute("DELETE FROM ghost_parts WHERE part_id='part-19'")
        with tool.readonly_connection(self.db_path) as conn:
            report = tool.audit_snapshot(conn, self.db_path)
        self.assertIn("ghostnetwork_readiness_invalid", report["blockers"])

    def test_output_does_not_include_credentials_or_full_other_profiles(self):
        with tool.readonly_connection(self.db_path) as conn:
            report = tool.audit_snapshot(conn, self.db_path)
        rendered = tool.canonical_json(report)
        self.assertNotIn("secret-not-reported", rendered)
        self.assertNotIn("salt-not-reported", rendered)
        self.assertFalse(report["profile"]["credentials_included"])
        self.assertFalse(report["profile"]["full_profile_included"])

    def test_runtime_does_not_import_recovery_tool(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ("run.py", "database.py", "scripts/territory_conflict_worker.py"):
            source = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("repair_trollu2_profile", source)

    def test_tool_does_not_import_runtime_or_offer_all_profile_scan(self):
        source = Path(tool.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import run", source)
        self.assertNotIn("from database import", source)
        self.assertNotIn("list_profiles", source)

    def test_before_manifest_is_signed_and_contains_exact_restore_records(self):
        plan, manifest = self.build_plan_and_manifest()
        unsigned = dict(manifest)
        unsigned.pop("manifest_sha256")
        self.assertEqual(tool.digest(unsigned), manifest["manifest_sha256"])
        self.assertTrue(manifest["sensitive"])
        self.assertEqual(plan["plan_id"], manifest["plan_id"])
        self.assertEqual(1, len(manifest["records"]["users"]))
        self.assertEqual(1, len(manifest["records"]["wallet_balances"]))

    def test_city_grant_is_atomic_when_captured_insert_fails(self):
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        tool.apply_level_step(self.db_path, plan)
        city = plan["territory_recovery"]["cities"][0]
        with self.connect() as conn:
            conn.execute(
                "CREATE TRIGGER fail_recovery_capture BEFORE INSERT ON captured_targets "
                "WHEN NEW.source_type='sprint_130_11_recovery' "
                "BEGIN SELECT RAISE(ABORT, 'simulated crash'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            tool.atomic_city_grant(self.db_path, plan, city)
        with self.connect() as conn:
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM territory_target_ownership WHERE owner_username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM territory_rebuild_jobs WHERE job_id=?",
                (city["rebuild_job_id"],),
            ).fetchone()[0])
            self.assertIsNone(tool.recovery_step(
                conn, plan["plan_id"], "territory_city:" + city["city"].lower()
            ))

    def test_final_settlement_is_exactly_once_and_does_not_promote_lkg(self):
        plan, _manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        with self.connect() as conn:
            before_lkg = dict(conn.execute(
                "SELECT * FROM profile_last_known_good WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone())
        first = tool.final_settlement(self.db_path, plan)
        second = tool.final_settlement(self.db_path, plan)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        with self.connect() as conn:
            state = tool.profile_state(tool.exact_user_row(conn), include_profile=True)
            wallet = conn.execute(
                "SELECT balance FROM wallet_balances WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()
            self.assertEqual(50, state["profile"]["level"])
            self.assertEqual(2560, state["profile"]["respect"])
            self.assertEqual(250000, wallet["balance"])
            self.assertEqual(tool.PILLARS_PER_CITY, len(state["profile"]["hacked"]))
            self.assertEqual(1, conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events WHERE reason='sprint_130_11.recovery'"
            ).fetchone()[0])
            self.assertEqual(1, conn.execute(
                "SELECT COUNT(*) FROM wallet_ledger WHERE event_type='profile_recovery'"
            ).fetchone()[0])
            after_lkg = dict(conn.execute(
                "SELECT * FROM profile_last_known_good WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone())
        self.assertEqual(before_lkg, after_lkg)

    def test_verify_then_explicit_lkg_promotion_is_sanitized_and_idempotent(self):
        plan, _manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        settlement = tool.final_settlement(self.db_path, plan)
        with tool.readonly_connection(self.db_path) as conn:
            self.assertTrue(tool.verify_recovery(conn, plan)["ok"])
        first = tool.promote_lkg(self.db_path, plan, settlement["profile_checksum"])
        second = tool.promote_lkg(self.db_path, plan, settlement["profile_checksum"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        with self.connect() as conn:
            lkg = tool.lkg_state(conn)
            snapshot = json.loads(conn.execute(
                "SELECT snapshot_json FROM profile_last_known_good WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])
        self.assertTrue(lkg["usable_as_recovery_source"])
        self.assertFalse(set(snapshot) & {"apps", "files", "hackcoins", "hacked", "operations"})

    def test_rollback_restores_before_state_and_rejects_later_gameplay(self):
        plan, manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        tool.final_settlement(self.db_path, plan)
        second_db = str(Path(self.temp.name) / "later.sqlite3")
        Path(second_db).write_bytes(Path(self.db_path).read_bytes())
        conn = sqlite3.connect(second_db)
        try:
            conn.execute(
                "UPDATE users SET profile_revision=profile_revision+1 WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(tool.RecoveryGateError):
            tool.rollback_recovery(second_db, plan, manifest)

        rolled_back = tool.rollback_recovery(self.db_path, plan, manifest)
        self.assertFalse(rolled_back["duplicate"])
        with self.connect() as conn:
            state = tool.profile_state(tool.exact_user_row(conn), include_profile=True)
            wallet = conn.execute(
                "SELECT balance FROM wallet_balances WHERE username=?",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()
            self.assertEqual(2, state["profile"]["level"])
            self.assertEqual(25, state["profile"]["respect"])
            self.assertEqual(1000, wallet["balance"])
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM captured_targets WHERE source_type='sprint_130_11_recovery'"
            ).fetchone()[0])

    def test_exact_worker_projection_is_accepted_for_guarded_conflict_cleanup(self):
        plan, manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        with self.connect() as conn:
            receipt = tool.recovery_receipt(conn, plan["plan_id"])
            before_profile = json.loads(manifest["records"]["users"][0]["profile_json"])
            receipt_profile = tool.canonical_profile_overlay(
                conn, tool.CANONICAL_USERNAME, before_profile, 1000,
                exclude_recovery_plan_id=plan["plan_id"],
            )
            receipt_profile["level"] = tool.RECOVERY_LEVEL
            self.assertEqual(
                receipt["current_profile_checksum"],
                tool.profile_checksum(receipt_profile),
            )
            projected = copy.deepcopy(receipt_profile)
            projected["hacked"] = tool.runtime_captured_targets_projection(
                conn, tool.CANONICAL_USERNAME
            )
            self.assertTrue(projected["hacked"])
            self.assertTrue(all("lon" in item for item in projected["hacked"]))
            projected["captured_targets_source"] = "sqlite"
            stats, exp = tool.territory_stats_snapshot(
                conn, tool.RECOVERY_LEVEL, base_profile=projected
            )
            projected["territory_stats"] = stats
            projected["exp"] = exp
            conn.execute(
                "UPDATE users SET profile_json=?, profile_revision=?, profile_checksum=? "
                "WHERE username=?",
                (
                    tool.canonical_json(projected),
                    int(receipt["current_profile_revision"]) + 1,
                    tool.profile_checksum(projected),
                    tool.CANONICAL_USERNAME,
                ),
            )
            target = plan["territory_recovery"]["cities"][0]["targets"][0]
            conflict_id = "territory_conflict_recovery_test"
            conn.execute(
                "INSERT INTO territory_conflicts "
                "(conflict_id, participants_json, targets_json, intersections_json, "
                "intersection_json, status, conflict_version, geometry_status, "
                "source_event, last_actor_username, created_at, updated_at) "
                "VALUES (?,?,?,?,?,'active',1,'clean','sprint_130_11_recovery',?,?,?)",
                (
                    conflict_id, tool.canonical_json(["pies1", tool.CANONICAL_USERNAME]),
                    tool.canonical_json([{"target": target}]), "[]", "[]",
                    tool.CANONICAL_USERNAME, "9999-01-01", "9999-01-01",
                ),
            )
            conn.execute(
                "INSERT INTO territory_conflict_pillars "
                "(conflict_id,target_id,status,captured,public_target_json) "
                "VALUES (?,?, 'contested',0,?)",
                (conflict_id, "canonical-derived-id", tool.canonical_json({"target": target})),
            )
            conn.execute(
                "INSERT INTO territory_conflict_rebuilds "
                "(conflict_id,requested_version,status,reason,requested_at,updated_at) "
                "VALUES (?,1,'complete','recovery','9999-01-01','9999-01-01')",
                (conflict_id,),
            )
            conn.execute(
                "INSERT INTO territory_conflict_fronts VALUES (?,?, 'active')",
                ("front-recovery", conflict_id),
            )
            conn.execute(
                "INSERT INTO territory_conflicts "
                "(conflict_id, participants_json, targets_json, intersections_json, "
                "intersection_json, status, conflict_version, geometry_status, "
                "source_event, last_actor_username, created_at, updated_at) "
                "VALUES (?,?,?,?,?,'active',1,'clean','ordinary_gameplay',?,?,?)",
                (
                    "preexisting-unrelated-conflict",
                    tool.canonical_json(["old-opponent", tool.CANONICAL_USERNAME]),
                    "[]", "[]", "[]", "old-opponent", "0001-01-01", "0001-01-01",
                ),
            )
        with tool.readonly_connection(self.db_path) as conn:
            assessment = tool.recovery_worker_projection_assessment(
                conn, plan, manifest
            )
            verification = tool.verify_recovery(conn, plan, manifest)
        self.assertTrue(assessment["recognized"])
        self.assertTrue(verification["recognized_worker_projection"]["recognized"])
        self.assertIn(
            "recovery_created_conflict:" + conflict_id,
            verification["blockers"],
        )
        with self.assertRaisesRegex(
            tool.RecoveryGateError, "Recovery-created conflict blocks final settlement"
        ):
            tool.final_settlement(self.db_path, plan)

        rolled_back = tool.rollback_recovery(self.db_path, plan, manifest)
        self.assertTrue(rolled_back["recognized_worker_projection"]["recognized"])
        self.assertEqual([conflict_id], rolled_back["conflict_cleanup"]["conflict_ids"])
        with self.connect() as conn:
            conflict = conn.execute(
                "SELECT status, source_event FROM territory_conflicts WHERE conflict_id=?",
                (conflict_id,),
            ).fetchone()
            self.assertEqual("changing", conflict["status"])
            self.assertEqual("sprint_130_11_rollback", conflict["source_event"])
            self.assertEqual("pending", conn.execute(
                "SELECT status FROM territory_conflict_rebuilds WHERE conflict_id=?",
                (conflict_id,),
            ).fetchone()[0])
            self.assertIsNotNone(tool.recovery_step(
                conn, plan["plan_id"], "worker_profile_projection"
            ))
            conn.execute(
                "UPDATE territory_rebuild_jobs SET status='complete', error='' "
                "WHERE job_id=?",
                (rolled_back["territory_rebuild_job_id"],),
            )
            conn.execute(
                "UPDATE territory_conflicts SET status='resolved', "
                "geometry_status='clean' WHERE conflict_id=?",
                (conflict_id,),
            )
            conn.execute(
                "UPDATE territory_conflict_rebuilds SET status='complete' "
                "WHERE conflict_id=?",
                (conflict_id,),
            )
            conn.execute(
                "UPDATE territory_conflict_fronts SET status='closed' "
                "WHERE conflict_id=?",
                (conflict_id,),
            )
        with tool.readonly_connection(self.db_path) as conn:
            rollback_verification = tool.verify_rollback(conn, plan, manifest)
        self.assertTrue(rollback_verification["ok"])
        self.assertEqual("rolled_back", rollback_verification["receipt_status"])

    def test_unrelated_profile_change_is_not_accepted_as_worker_projection(self):
        plan, manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        with self.connect() as conn:
            row = tool.exact_user_row(conn)
            profile = json.loads(row["profile_json"])
            profile["nick"] = "later-gameplay"
            conn.execute(
                "UPDATE users SET profile_json=?, profile_revision=profile_revision+1, "
                "profile_checksum=? WHERE username=?",
                (
                    tool.canonical_json(profile), tool.profile_checksum(profile),
                    tool.CANONICAL_USERNAME,
                ),
            )
        with tool.readonly_connection(self.db_path) as conn:
            assessment = tool.recovery_worker_projection_assessment(
                conn, plan, manifest
            )
        self.assertFalse(assessment["recognized"])
        with self.assertRaises(tool.RecoveryGateError):
            tool.rollback_recovery(self.db_path, plan, manifest)



if __name__ == "__main__":
    unittest.main()
