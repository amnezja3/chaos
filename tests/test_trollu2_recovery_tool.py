from __future__ import annotations

import copy
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

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
                CREATE TABLE player_marked_targets (
                    username TEXT, target_key TEXT, target_json TEXT,
                    lat REAL, lng REAL, label TEXT, status TEXT, version INTEGER,
                    source TEXT, created_at TEXT, updated_at TEXT,
                    PRIMARY KEY(username, target_key)
                );
                CREATE TABLE player_marked_target_state (
                    username TEXT PRIMARY KEY, source_revision INTEGER,
                    migrated_count INTEGER, seeded_at TEXT
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
                    vertices_json TEXT, centroid_lat REAL, centroid_lng REAL,
                    area_size REAL, max_edge_distance REAL DEFAULT 0,
                    status TEXT, created_at TEXT, updated_at TEXT
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
            conn.execute(
                "INSERT INTO player_marked_target_state VALUES (?,?,?,?)",
                (tool.CANONICAL_USERNAME, 7, 2, "2026-01-02"),
            )
            marked_targets = [
                {
                    "target_id": "map:35.1:139.1:first", "lat": 35.1,
                    "lng": 139.1, "label": "first",
                },
                {
                    "target_id": "map:35.2:139.2:second", "lat": 35.2,
                    "lng": 139.2, "label": "second",
                },
            ]
            for index, target in enumerate(marked_targets):
                conn.execute(
                    "INSERT INTO player_marked_targets VALUES "
                    "(?,?,?,?,?,?,'active',1,'test',?,?)",
                    (
                        tool.CANONICAL_USERNAME, target["target_id"],
                        tool.canonical_json(target), target["lat"], target["lng"],
                        target["label"], f"2026-01-0{index + 2}",
                        f"2026-01-0{index + 2}",
                    ),
                )
            inventory_items = [
                ("app_nmap", "Nmap"),
                ("app_metasploit", "Metasploit"),
            ] + [
                (f"app_preserved_{index}", f"Preserved {index}")
                for index in range(1, 10)
            ]
            for app_id, name in inventory_items:
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
            historical_targets = [
                ("map:52.1486:20.90033:DPD", 52.1485961, 20.9003327, "DPD"),
                ("map:52.15753:20.8892:POI-9D7173", 52.1575251, 20.8891974, "POI-9D7173"),
                ("map:52.15806:20.90962:Cerber", 52.1580559, 20.9096169, "Cerber"),
                ("map:52.15876:20.9115:POI-67044F", 52.1587556, 20.9114969, "POI-67044F"),
                ("map:52.16796:20.89818:POI-166846", 52.1679612, 20.8981787, "POI-166846"),
                ("map:52.17101:20.90633:Arkazen", 52.1710090, 20.9063306, "Arkazen"),
                ("map:35.36472:139.46136:Lawson", 35.3647239, 139.4613615, "Lawson"),
                ("map:35.36583:139.44617:ユーミーClass", 35.3658278, 139.4461742, "ユーミーClass"),
                ("map:35.37252:139.45338:スーパー生鮮館TAIGA 藤沢石川店", 35.3725165, 139.4533766, "スーパー生鮮館TAIGA 藤沢石川店"),
            ]
            for target_id, lat, lng, label in historical_targets:
                payload = {
                    "target_id": target_id, "lat": lat, "lng": lng,
                    "label": label, "source_type": "scan",
                    "stationary": True, "generated": False,
                    "captured_at": "2026-08-20T12:00:00",
                }
                conn.execute(
                    "INSERT INTO captured_targets "
                    "(owner_username,stationary,updated_at,lat,lng,label,name,icon,"
                    "source_type,generated,target_json,captured_at) "
                    "VALUES (?,1,'2026-08-20',?,?,?,?, '', 'scan',0,?,?)",
                    (
                        tool.CANONICAL_USERNAME, lat, lng, label, label,
                        tool.canonical_json(payload), payload["captured_at"],
                    ),
                )
                conn.execute(
                    "INSERT INTO territory_target_ownership VALUES "
                    "(?,?,1,?,?,?,?, '2026-08-20')",
                    (
                        target_id, tool.CANONICAL_USERNAME, lat, lng, label,
                        tool.canonical_json(payload),
                    ),
                )
            unrelated_payload = {
                "target_id": "map:40.0:10.0:unrelated-ownership",
                "lat": 40.0, "lng": 10.0, "label": "unrelated-ownership",
            }
            conn.execute(
                "INSERT INTO territory_target_ownership VALUES "
                "(?,?,7,?,?,?,?, '2026-08-20')",
                (
                    unrelated_payload["target_id"], tool.CANONICAL_USERNAME,
                    unrelated_payload["lat"], unrelated_payload["lng"],
                    unrelated_payload["label"],
                    tool.canonical_json(unrelated_payload),
                ),
            )
            courier = {
                "target_id": "map:52.15872:20.90926:Kuriero-bot",
                "lat": 52.158725, "lng": 20.9092585,
                "label": "Kuriero-bot", "source_type": "parcel_locker",
                "stationary": False, "generated": True,
                "captured_at": "2026-08-21T13:25:41",
            }
            conn.execute(
                "INSERT INTO captured_targets "
                "(owner_username,stationary,updated_at,lat,lng,label,name,icon,"
                "source_type,generated,target_json,captured_at) "
                "VALUES (?,0,'2026-08-21',?,?,?,?, '', 'parcel_locker',1,?,?)",
                (
                    tool.CANONICAL_USERNAME, courier["lat"], courier["lng"],
                    courier["label"], courier["label"],
                    tool.canonical_json(courier), courier["captured_at"],
                ),
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

    def remove_historical_ownership(self):
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM territory_target_ownership WHERE target_id IN ({})".format(
                    ",".join("?" for _ in tool.HISTORICAL_GEOMETRY_TARGET_IDS)
                ),
                tool.HISTORICAL_GEOMETRY_TARGET_IDS,
            )

    def build_plan_and_manifest(self):
        plan = self.build_plan()
        with tool.readonly_connection(self.db_path) as conn:
            manifest = tool.build_before_manifest(conn, self.db_path, plan)
        return plan, manifest

    def apply_command_args(self, plan, manifest):
        plan_path = Path(self.temp.name) / "plan.json"
        manifest_path = Path(self.temp.name) / "before-manifest.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False), encoding="utf-8"
        )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        return SimpleNamespace(
            db=self.db_path,
            plan=str(plan_path),
            before_manifest=str(manifest_path),
            plan_sha256=plan["plan_sha256"],
            manifest_sha256=manifest["manifest_sha256"],
            write=True,
            authorized_by="test-operator",
        )

    def start_recovery(self):
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        tool.retire_historical_targets(self.db_path, plan, "test-operator")
        self.complete_retirement_job(plan)
        tool.mark_retirement_rebuild_verified(self.db_path, plan)
        tool.apply_level_step(self.db_path, plan)
        for city in plan["territory_recovery"]["cities"]:
            tool.atomic_city_grant(self.db_path, plan, city)
        return plan, manifest

    def complete_retirement_job(self, plan):
        job_id = plan["territory_recovery"]["historical_retirement"]["rebuild_job_id"]
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM player_areas WHERE owner_username=?",
                (tool.CANONICAL_USERNAME,),
            )
            conn.execute(
                "UPDATE territory_rebuild_jobs SET status='complete', "
                "updated_at='2026-02-04' WHERE job_id=?",
                (job_id,),
            )

    def complete_recovery_jobs(self, plan):
        with tool.readonly_connection(self.db_path) as conn:
            areas = tool.canonical_subject_area_preview(conn, [])
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM player_areas WHERE owner_username=?",
                (tool.CANONICAL_USERNAME,),
            )
            for area in areas:
                conn.execute(
                    "INSERT INTO player_areas "
                    "(owner_username,vertices_json,centroid_lat,centroid_lng,"
                    "area_size,max_edge_distance,status,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,'active','2026-02-04','2026-02-04')",
                    (
                        tool.CANONICAL_USERNAME,
                        tool.canonical_json(area["vertices"]),
                        area.get("centroid_lat"), area.get("centroid_lng"),
                        area.get("area_size"), area.get("max_edge_distance"),
                    ),
                )
            for city in plan["territory_recovery"]["cities"]:
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
        self.assertEqual(11, len(plan["preserve"]["apps"]))
        self.assertEqual(11, len(plan["preserve"]["tools"]))
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
        self.assertIn("combined_final_collision:Tokio", plan["blockers"])
        self.assertEqual(
            [], plan["territory_recovery"]["cities"][0]["collisions"]
        )

    def test_tampered_plan_signature_is_rejected(self):
        plan = self.build_plan()
        plan["final_state"]["wallet_balance"] += 1
        path = Path(self.temp.name) / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaises(tool.RecoveryGateError):
            tool.load_plan(str(path))

    def test_target_projection_diagnostics_are_structural_and_minimal(self):
        expected = [
            {"target_id": "target-a", "label": "secret-a", "version": 1},
            {"target_id": "target-b", "label": "secret-b"},
        ]
        current = [
            {"target_id": "target-b", "label": "secret-b"},
            {"target_id": "target-a", "label": "changed-secret", "version": 2},
            {"target_id": "target-c", "label": "secret-c"},
        ]

        diagnostics = tool.target_projection_diagnostics(expected, current)

        self.assertEqual(2, diagnostics["expected_count"])
        self.assertEqual(3, diagnostics["current_count"])
        self.assertFalse(diagnostics["order_matches"])
        self.assertEqual(["target-c"], diagnostics["added_stable_ids"])
        self.assertEqual([], diagnostics["removed_stable_ids"])
        changed = {item["stable_id"]: item for item in diagnostics["changed"]}
        self.assertEqual(
            {"label", "version"},
            {item["field"] for item in changed["target-a"]["fields"]},
        )
        rendered = tool.canonical_json(diagnostics)
        self.assertNotIn("secret-a", rendered)
        self.assertNotIn("changed-secret", rendered)

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
        tool.retire_historical_targets(self.db_path, plan, "test-operator")
        self.complete_retirement_job(plan)
        tool.mark_retirement_rebuild_verified(self.db_path, plan)
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
                "SELECT COUNT(*) FROM territory_target_ownership "
                "WHERE target_id LIKE 'recovery_%'",
            ).fetchone()[0])
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM territory_rebuild_jobs WHERE job_id=?",
                (city["rebuild_job_id"],),
            ).fetchone()[0])
            self.assertIsNone(tool.recovery_step(
                conn, plan["plan_id"], "territory_city:" + city["city"].lower()
            ))

    def test_retirement_is_exactly_nine_audited_and_preserves_kuriero_inventory_gn(self):
        plan, manifest = self.build_plan_and_manifest()
        with tool.readonly_connection(self.db_path) as conn:
            ghost_before = tool.ghostnetwork_evidence(conn)
            inventory_before = tool.inventory_evidence(conn)
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        first = tool.retire_historical_targets(
            self.db_path, plan, "test-operator"
        )
        second = tool.retire_historical_targets(
            self.db_path, plan, "test-operator"
        )
        self.assertEqual(9, first["retired_count"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        with tool.readonly_connection(self.db_path) as conn:
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM territory_target_ownership "
                "WHERE target_id IN ({})".format(
                    ",".join("?" for _ in tool.HISTORICAL_GEOMETRY_TARGET_IDS)
                ),
                tool.HISTORICAL_GEOMETRY_TARGET_IDS,
            ).fetchone()[0])
            courier = conn.execute(
                "SELECT stationary, generated FROM captured_targets "
                "WHERE owner_username=? AND label='Kuriero-bot'",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()
            self.assertIsNotNone(courier)
            self.assertEqual(0, int(courier["stationary"]))
            self.assertEqual(1, int(courier["generated"]))
            audit_rows = conn.execute(
                f"SELECT target_id, previous_owner_username, captured_row_id, "
                f"captured_sha256, ownership_state, recovery_plan_id, reason, "
                f"operator_username, previous_state_sha256, status "
                f"FROM {tool.RECOVERY_RETIREMENTS_TABLE} WHERE plan_id=?",
                (plan["plan_id"],),
            ).fetchall()
            self.assertEqual(9, len(audit_rows))
            self.assertEqual(
                set(tool.HISTORICAL_GEOMETRY_TARGET_IDS),
                {row["target_id"] for row in audit_rows},
            )
            self.assertTrue(all(
                row["previous_owner_username"] == tool.CANONICAL_USERNAME
                and int(row["captured_row_id"]) > 0
                and row["captured_sha256"]
                and row["ownership_state"] == "present"
                and row["recovery_plan_id"] == plan["plan_id"]
                and row["reason"] == tool.RECOVERY_REASON
                and row["operator_username"] == "test-operator"
                and row["previous_state_sha256"]
                and row["status"] == "retired"
                for row in audit_rows
            ))
            self.assertEqual(inventory_before, tool.inventory_evidence(conn))
            self.assertEqual(ghost_before, tool.ghostnetwork_evidence(conn))
            unrelated = conn.execute(
                "SELECT owner_username, ownership_version "
                "FROM territory_target_ownership "
                "WHERE target_id='map:40.0:10.0:unrelated-ownership'"
            ).fetchone()
            self.assertEqual(tool.CANONICAL_USERNAME, unrelated["owner_username"])
            self.assertEqual(7, int(unrelated["ownership_version"]))

    def test_current_world_change_before_bonus_grant_fails_closed(self):
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        tool.retire_historical_targets(self.db_path, plan, "test-operator")
        self.complete_retirement_job(plan)
        tool.mark_retirement_rebuild_verified(self.db_path, plan)
        tool.apply_level_step(self.db_path, plan)
        city = plan["territory_recovery"]["cities"][0]
        vertices = [
            {"lat": target["lat"], "lng": target["lng"]}
            for target in city["targets"]
        ]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO player_areas "
                "(owner_username,vertices_json,area_size,status,updated_at) "
                "VALUES ('foreign-player',?,1,'active','2026-02-05')",
                (tool.canonical_json(vertices),),
            )
        with self.assertRaisesRegex(
            tool.RecoveryGateError, "CURRENT_WORLD_CHANGED_REPLAN_REQUIRED"
        ):
            tool.atomic_city_grant(self.db_path, plan, city)
        with tool.readonly_connection(self.db_path) as conn:
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM captured_targets "
                "WHERE source_type='sprint_130_11_recovery'"
            ).fetchone()[0])
            self.assertIsNone(tool.recovery_step(
                conn, plan["plan_id"], "territory_city:" + city["city"].lower()
            ))

    def test_retirement_allows_explicit_absent_ownership_and_removes_worker_sources(self):
        self.remove_historical_ownership()
        plan, manifest = self.build_plan_and_manifest()
        retirement = plan["territory_recovery"]["historical_retirement"]
        states = retirement["targets"]
        self.assertEqual(9, len(states))
        self.assertEqual({"absent"}, {item["ownership_state"] for item in states})
        self.assertTrue(all("ownership_sha256" not in item for item in states))
        self.assertTrue(all("ownership_version" not in item for item in states))
        self.assertEqual(11, len(plan["preserve"]["apps"]))
        self.assertEqual(11, len(plan["preserve"]["tools"]))
        self.assertEqual(0, plan["ghostnetwork_isolation"]["writes"])
        city = plan["territory_recovery"]["cities"][0]
        self.assertEqual([], city["collisions"])
        self.assertEqual([], city["combined_final_collisions"])

        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        result = tool.retire_historical_targets(
            self.db_path, plan, "test-operator"
        )
        self.assertEqual(9, result["retired_count"])
        from database import TerritoryStore
        worker_store = TerritoryStore.__new__(TerritoryStore)
        worker_store.db_path = self.db_path
        actual_worker_areas = worker_store.build_player_areas(
            tool.CANONICAL_USERNAME, tool.RECOVERY_LEVEL
        )
        with tool.readonly_connection(self.db_path) as conn:
            audit_rows = conn.execute(
                f"SELECT target_id, captured_row_id, captured_sha256, "
                f"ownership_state, recovery_plan_id, previous_owner_username, "
                f"reason, operator_username, retired_at "
                f"FROM {tool.RECOVERY_RETIREMENTS_TABLE} WHERE plan_id=?",
                (plan["plan_id"],),
            ).fetchall()
            stationary_count = int(conn.execute(
                "SELECT COUNT(*) FROM captured_targets "
                "WHERE owner_username=? AND stationary=1",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])
            rebuilt_preview = tool.canonical_subject_area_preview(conn, [])
            courier = conn.execute(
                "SELECT id FROM captured_targets WHERE owner_username=? "
                "AND label='Kuriero-bot' AND stationary=0",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()
            unrelated = conn.execute(
                "SELECT ownership_version FROM territory_target_ownership "
                "WHERE target_id='map:40.0:10.0:unrelated-ownership'"
            ).fetchone()
        self.assertEqual(9, len(audit_rows))
        self.assertTrue(all(
            row["ownership_state"] == "absent"
            and int(row["captured_row_id"]) > 0
            and row["captured_sha256"]
            and row["recovery_plan_id"] == plan["plan_id"]
            and row["previous_owner_username"] == tool.CANONICAL_USERNAME
            and row["reason"] == tool.RECOVERY_REASON
            and row["operator_username"] == "test-operator"
            and row["retired_at"]
            for row in audit_rows
        ))
        self.assertEqual(0, stationary_count)
        self.assertEqual([], rebuilt_preview)
        self.assertEqual([], actual_worker_areas)
        self.assertIsNotNone(courier)
        self.assertEqual(7, int(unrelated["ownership_version"]))

    def test_ownership_appearing_after_absent_plan_fails_before_mutation(self):
        self.remove_historical_ownership()
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        target = plan["territory_recovery"]["historical_retirement"]["targets"][0]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO territory_target_ownership "
                "(target_id,owner_username,ownership_version,lat,lng,label,"
                "target_json,updated_at) VALUES (?,?,1,?,?,?,?,?)",
                (
                    target["target_id"], tool.CANONICAL_USERNAME,
                    target["lat"], target["lng"], "appeared",
                    tool.canonical_json({"target_id": target["target_id"]}),
                    "2026-08-24",
                ),
            )
        with self.assertRaisesRegex(
            tool.RecoveryGateError, "CURRENT_WORLD_CHANGED_REPLAN_REQUIRED"
        ):
            tool.retire_historical_targets(self.db_path, plan, "test-operator")
        with tool.readonly_connection(self.db_path) as conn:
            self.assertEqual(9, conn.execute(
                "SELECT COUNT(*) FROM captured_targets "
                "WHERE owner_username=? AND stationary=1",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])
            self.assertEqual(0, conn.execute(
                f"SELECT COUNT(*) FROM {tool.RECOVERY_RETIREMENTS_TABLE} "
                "WHERE plan_id=?",
                (plan["plan_id"],),
            ).fetchone()[0])

    def test_captured_row_change_after_plan_fails_before_mutation(self):
        self.remove_historical_ownership()
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        target = plan["territory_recovery"]["historical_retirement"]["targets"][0]
        with self.connect() as conn:
            conn.execute(
                "UPDATE captured_targets SET updated_at='2026-08-24T12:00:00Z' "
                "WHERE id=?",
                (target["captured_row_id"],),
            )
        with self.assertRaisesRegex(
            tool.RecoveryGateError, "CURRENT_WORLD_CHANGED_REPLAN_REQUIRED"
        ):
            tool.retire_historical_targets(self.db_path, plan, "test-operator")
        with tool.readonly_connection(self.db_path) as conn:
            self.assertEqual(9, conn.execute(
                "SELECT COUNT(*) FROM captured_targets "
                "WHERE owner_username=? AND stationary=1",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])
            self.assertEqual(0, conn.execute(
                f"SELECT COUNT(*) FROM {tool.RECOVERY_RETIREMENTS_TABLE} "
                "WHERE plan_id=?",
                (plan["plan_id"],),
            ).fetchone()[0])

    def test_rollback_from_retirement_phase_restores_current_state_and_keeps_audit(self):
        plan, manifest = self.build_plan_and_manifest()
        tool.initialize_recovery_receipt(self.db_path, plan, manifest)
        tool.retire_historical_targets(self.db_path, plan, "test-operator")
        rollback = tool.rollback_recovery(self.db_path, plan, manifest)
        with self.connect() as conn:
            conn.execute(
                "UPDATE territory_rebuild_jobs SET status='complete' WHERE job_id=?",
                (rollback["territory_rebuild_job_id"],),
            )
        with tool.readonly_connection(self.db_path) as conn:
            verification = tool.verify_rollback(conn, plan, manifest)
            statuses = [
                row["status"] for row in conn.execute(
                    f"SELECT status FROM {tool.RECOVERY_RETIREMENTS_TABLE} "
                    "WHERE plan_id=?",
                    (plan["plan_id"],),
                )
            ]
        self.assertTrue(verification["ok"], verification["blockers"])
        self.assertEqual(9, len(statuses))
        self.assertEqual({"rolled_back"}, set(statuses))

    def test_plan_separates_clean_bonus_from_historical_geometry(self):
        plan = self.build_plan()
        city = plan["territory_recovery"]["cities"][0]
        self.assertEqual([], city["collisions"])
        self.assertEqual([], city["combined_final_collisions"])
        self.assertEqual(1, city["bonus_only_worker_preview"]["area_count"])
        self.assertEqual(1, city["combined_final_worker_preview"]["area_count"])
        self.assertEqual(
            "retire_before_progression",
            plan["territory_recovery"]["existing_historical_geometry"]["disposition"],
        )

    def test_replan_reuses_only_the_old_bonus_center_and_requires_v2_for_apply(self):
        old_plan = self.build_plan()
        old_plan["plan_version"] = 1
        old_plan["plan_sha256"] = tool.digest({
            key: value for key, value in old_plan.items()
            if key != "plan_sha256"
        })
        with tool.readonly_connection(self.db_path) as conn:
            replanned = tool.build_plan(
                conn, self.db_path, bonus_source_plan=old_plan
            )
        old_city = old_plan["territory_recovery"]["cities"][0]
        new_city = replanned["territory_recovery"]["cities"][0]
        self.assertEqual(
            old_city["relocation"]["selected_center"],
            new_city["relocation"]["selected_center"],
        )
        self.assertEqual(old_plan["plan_id"], new_city["relocation"]["reused_from_plan_id"])
        self.assertNotEqual(old_plan["plan_id"], replanned["plan_id"])
        with self.assertRaisesRegex(tool.RecoveryGateError, "requires.*v2 plan"):
            tool.require_recovery_v2_plan(old_plan)

    def test_retirement_resolves_legacy_captured_row_by_canonical_ownership_coordinates(self):
        target_id = tool.HISTORICAL_GEOMETRY_TARGET_IDS[0]
        with self.connect() as conn:
            ownership = conn.execute(
                "SELECT lat, lng FROM territory_target_ownership WHERE target_id=?",
                (target_id,),
            ).fetchone()
            row = conn.execute(
                "SELECT id, target_json FROM captured_targets WHERE owner_username=? "
                "AND ROUND(lat,7)=ROUND(?,7) AND ROUND(lng,7)=ROUND(?,7)",
                (tool.CANONICAL_USERNAME, ownership["lat"], ownership["lng"]),
            ).fetchone()
            payload = json.loads(row["target_json"])
            payload.pop("target_id", None)
            conn.execute(
                "UPDATE captured_targets SET target_json=? WHERE id=?",
                (tool.canonical_json(payload), row["id"]),
            )
        with tool.readonly_connection(self.db_path) as conn:
            scope = tool.historical_retirement_scope(conn)
            preserved = tool.preserved_non_retired_captured_projection(conn)
            plan = tool.build_plan(conn, self.db_path)
        self.assertEqual([], scope["blockers"])
        self.assertEqual(9, scope["count"])
        self.assertEqual(1, preserved["count"])
        self.assertEqual(
            1,
            plan["territory_recovery"]["cities"][0]
            ["combined_final_worker_preview"]["area_count"],
        )

    def test_final_settlement_is_exactly_once_and_does_not_promote_lkg(self):
        plan, _manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        with tool.readonly_connection(self.db_path) as conn:
            self.assertEqual([], tool.final_phase_precondition_blockers(conn, plan))
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
            self.assertEqual(
                tool.PILLARS_PER_CITY + 1, len(state["profile"]["hacked"])
            )
            self.assertTrue(any(
                item.get("target_id") == "map:52.15872:20.90926:Kuriero-bot"
                for item in state["profile"]["hacked"]
            ))
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

    def test_three_apply_lifecycle_resumes_after_bonus_area_and_settles_once(self):
        plan, manifest = self.build_plan_and_manifest()
        args = self.apply_command_args(plan, manifest)
        output = io.StringIO()
        with redirect_stdout(output):
            first_rc = tool.command_apply(args)
        self.assertEqual(3, first_rc)
        self.assertEqual(
            "AWAITING_RETIREMENT_REBUILD",
            json.loads(output.getvalue())["phase"],
        )

        self.complete_retirement_job(plan)
        output = io.StringIO()
        with redirect_stdout(output):
            second_rc = tool.command_apply(args)
        self.assertEqual(3, second_rc)
        self.assertEqual(
            "AWAITING_FINAL_REBUILD",
            json.loads(output.getvalue())["phase"],
        )
        self.complete_recovery_jobs(plan)
        with tool.readonly_connection(self.db_path) as conn:
            scoped_retirement = tool.verify_retirement_rebuild(
                conn, plan, require_pre_bonus_empty_geometry=False
            )
            final_geometry = tool.final_geometry_verification(conn, plan)
        self.assertTrue(scoped_retirement["ok"], scoped_retirement["blockers"])
        self.assertEqual(8, scoped_retirement["canonical_worker_stationary_input_count"])
        self.assertEqual(1, scoped_retirement["canonical_worker_preview_area_count"])
        self.assertTrue(final_geometry["ok"], final_geometry["blockers"])
        self.assertEqual(8, final_geometry["captured_recovery_target_count"])
        self.assertEqual(1, final_geometry["actual_area_count"])

        output = io.StringIO()
        with redirect_stdout(output):
            third_rc = tool.command_apply(args)
        third = json.loads(output.getvalue())
        self.assertEqual(0, third_rc)
        self.assertEqual("APPLIED_READY_FOR_VERIFY", third["phase"])
        with tool.readonly_connection(self.db_path) as conn:
            receipt = tool.recovery_receipt(conn, plan["plan_id"])
            self.assertEqual("applied", receipt["status"])
            self.assertEqual(1, conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events "
                "WHERE reason='sprint_130_11.recovery'"
            ).fetchone()[0])
            self.assertEqual(8, conn.execute(
                "SELECT COUNT(*) FROM captured_targets "
                "WHERE owner_username=? AND source_type='sprint_130_11_recovery'",
                (tool.CANONICAL_USERNAME,),
            ).fetchone()[0])

    def test_historical_target_reactivation_blocks_scoped_retirement_after_bonus(self):
        plan, _manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        target = plan["territory_recovery"]["historical_retirement"]["targets"][0]
        payload = {
            "target_id": target["target_id"], "lat": target["lat"],
            "lng": target["lng"], "label": "DPD", "stationary": True,
        }
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO captured_targets "
                "(owner_username,stationary,updated_at,lat,lng,label,name,icon,"
                "source_type,generated,target_json,captured_at) "
                "VALUES (?,1,'2026-08-24',?,?,?,?, '', 'scan',0,?,'2026-08-24')",
                (
                    tool.CANONICAL_USERNAME, target["lat"], target["lng"],
                    "DPD", "DPD", tool.canonical_json(payload),
                ),
            )
        with tool.readonly_connection(self.db_path) as conn:
            verification = tool.verify_retirement_rebuild(
                conn, plan, require_pre_bonus_empty_geometry=False
            )
        self.assertFalse(verification["ok"])
        self.assertIn(
            "retired_capture_still_active:" + target["target_id"],
            verification["blockers"],
        )

    def test_new_gameplay_target_after_final_rebuild_blocks_resume_without_settlement(self):
        plan, manifest = self.start_recovery()
        self.complete_recovery_jobs(plan)
        args = self.apply_command_args(plan, manifest)
        payload = {
            "target_id": "map:0.0:0.0:later-gameplay", "lat": 0.0,
            "lng": 0.0, "label": "later-gameplay", "stationary": True,
        }
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO captured_targets "
                "(owner_username,stationary,updated_at,lat,lng,label,name,icon,"
                "source_type,generated,target_json,captured_at) "
                "VALUES (?,1,'2026-08-24',0,0,'later-gameplay','later-gameplay','',"
                "'scan',0,?,'2026-08-24')",
                (tool.CANONICAL_USERNAME, tool.canonical_json(payload)),
            )
        with self.assertRaisesRegex(
            tool.RecoveryGateError, "CURRENT_WORLD_CHANGED_REPLAN_REQUIRED"
        ):
            with redirect_stdout(io.StringIO()):
                tool.command_apply(args)
        with tool.readonly_connection(self.db_path) as conn:
            self.assertIsNone(tool.recovery_step(
                conn, plan["plan_id"], "final_settlement"
            ))
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events "
                "WHERE reason='sprint_130_11.recovery'"
            ).fetchone()[0])

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
            marked_overlaid, marked_targets = tool.runtime_marked_targets_projection(
                conn, tool.CANONICAL_USERNAME
            )
            self.assertTrue(marked_overlaid)
            projected["targets"] = marked_targets
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

    def test_unexpected_marked_target_is_not_accepted_as_worker_projection(self):
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
            projected = copy.deepcopy(receipt_profile)
            projected["hacked"] = tool.runtime_captured_targets_projection(
                conn, tool.CANONICAL_USERNAME
            )
            _overlaid, projected["targets"] = tool.runtime_marked_targets_projection(
                conn, tool.CANONICAL_USERNAME
            )
            projected["captured_targets_source"] = "sqlite"
            stats, exp = tool.territory_stats_snapshot(
                conn, tool.RECOVERY_LEVEL, base_profile=projected
            )
            projected["territory_stats"] = stats
            projected["exp"] = exp
            projected["targets"].append({
                "target_id": "later-gameplay-target", "lat": 1.0, "lng": 1.0,
            })
            conn.execute(
                "UPDATE users SET profile_json=?, profile_revision=?, profile_checksum=? "
                "WHERE username=?",
                (
                    tool.canonical_json(projected),
                    int(receipt["current_profile_revision"]) + 1,
                    tool.profile_checksum(projected), tool.CANONICAL_USERNAME,
                ),
            )

        with tool.readonly_connection(self.db_path) as conn:
            assessment = tool.recovery_worker_projection_assessment(
                conn, plan, manifest
            )

        self.assertFalse(assessment["recognized"])
        self.assertEqual(["targets"], assessment["differing_top_level_fields"])
        target_diff = assessment["projection_diagnostics"]["targets"]
        self.assertEqual(["later-gameplay-target"], target_diff["added_stable_ids"])



if __name__ == "__main__":
    unittest.main()
