import unittest
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import run
from database import DevBugReportStore, JsonResourceStore, MailStore
from run import (
    active_operations_from_operations,
    apply_operation_quality_to_files,
    build_generated_app,
    build_player_actor,
    cancel_profile_operation,
    collect_ghost_exchange_files,
    create_operations_for_app_action,
    display_target_label,
    ensure_files_inventory,
    filter_targets_by_position,
    get_apps_for_map_action,
    googleplex_catalog_payload,
    normalize_app_contract,
    normalize_profile_storage,
    operation_history_from_operations,
    refresh_operation_runtime,
    refresh_operations_runtime,
    resolve_player_actor_relation,
    target_position_key,
    targets_share_position,
)


class TargetDisplayLabelTest(unittest.TestCase):
    def test_unnamed_poi_gets_deterministic_node_label(self):
        target = {
            "name": "",
            "label": "Brak nazwy",
            "source_type": "shop",
            "target_type": "poi",
            "osm_id": 123456,
            "lat": 52.2297,
            "lng": 21.0122,
        }

        label = display_target_label(target)

        self.assertTrue(label.startswith("NODE-"))
        self.assertNotEqual(label, "Brak nazwy")
        self.assertEqual(label, display_target_label(dict(target)))

    def test_named_target_keeps_real_name(self):
        target = {
            "name": "Zabka",
            "label": "",
            "source_type": "shop",
            "lat": 52.1,
            "lng": 21.2,
        }

        self.assertEqual(display_target_label(target), "Zabka")

    def test_vehicle_and_person_prefixes_are_readable(self):
        vehicle = {"source_type": "car", "name": "", "lat": 52.1, "lng": 21.2}
        person = {"source_type": "person", "name": "", "lat": 52.1, "lng": 21.2}

        self.assertTrue(display_target_label(vehicle).startswith("ECU-"))
        self.assertTrue(display_target_label(person).startswith("SUBJECT-"))


class DevBugReportStoreTest(unittest.TestCase):
    def test_dev_mode_gate_uses_environment(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "CHAOS_DEV_MODE": ""}, clear=False):
            self.assertFalse(run.is_dev_mode_enabled())

        with patch.dict(os.environ, {"APP_ENV": "staging", "CHAOS_DEV_MODE": ""}, clear=False):
            self.assertTrue(run.is_dev_mode_enabled())

        with patch.dict(os.environ, {"APP_ENV": "production", "CHAOS_DEV_MODE": "true"}, clear=False):
            self.assertTrue(run.is_dev_mode_enabled())

    def test_dev_bug_report_store_creates_lists_and_updates_status(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = DevBugReportStore(db_path=path)
            report = store.create_report(
                {
                    "title": "Camera cards overlap",
                    "description": "Long cards break UI",
                    "category": "UI",
                    "severity": "high",
                    "current_url": "/desktop",
                    "context": {
                        "client_timestamp": "2026-06-29T12:00:00",
                        "active_window": {"title": "Mapa"},
                    },
                },
                created_by="tester",
                app_version="test-build",
            )

            self.assertEqual(report["status"], "new")
            self.assertEqual(report["category"], "UI")
            self.assertEqual(report["context"]["active_window"]["title"], "Mapa")
            self.assertEqual(len(store.list_reports(search="camera")), 1)
            self.assertEqual(len(store.find_similar("Camera overlap")), 1)

            updated = store.update_report(report["id"], {"status": "confirmed"})
            self.assertEqual(updated["status"], "confirmed")
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass

    def test_dev_bug_server_context_uses_trusted_profile_username(self):
        fake_profile = {
            "username": "admin",
            "nick": "Admin",
            "level": 6,
            "hackcoins": 123,
            "respect": 7,
            "aimed_target": {"label": "Target A", "target_mode": "standard"},
            "operations": [
                {
                    "operation_id": "op1",
                    "operation_type": "camera_stream",
                    "status": "running",
                    "target": {"label": "Camera"},
                    "expires_at": "2999-06-29T12:30:00+00:00",
                    "remaining_seconds": 1800,
                }
            ],
        }

        with patch.object(run.user_store, "get_profile", return_value=fake_profile):
            context = run.build_dev_bug_server_context(
                "admin",
                client_context={"profile": {"username": "spoofed"}, "current_url": "/desktop"},
            )

        self.assertEqual(context["session"]["username"], "admin")
        self.assertEqual(context["profile_snapshot"]["level"], 6)
        self.assertEqual(context["aimed_target"]["label"], "Target A")
        self.assertEqual(context["active_operations_summary"][0]["operation_type"], "camera_stream")
        self.assertIn("server_timestamp", context)


class JsonResourceStoreSeedTest(unittest.TestCase):
    def test_static_seed_uses_resource_whitelist(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            JsonResourceStore(db_path=path)
            conn = sqlite3.connect(path)
            try:
                keys = {
                    row[0]
                    for row in conn.execute("SELECT key FROM json_resources").fetchall()
                }
            finally:
                conn.close()

            self.assertIn("app_config", keys)
            self.assertIn("user_template", keys)
            self.assertIn("user_security", keys)
            self.assertIn("terminal_command", keys)
            self.assertNotIn("targets", keys)
            self.assertNotIn("resources", keys)
            self.assertNotIn("system_status", keys)
            self.assertNotIn("system_messages", keys)
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass


class MailStoreFriendshipStatusTest(unittest.TestCase):
    def test_pending_contact_is_not_accepted_friendship(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = MailStore(db_path=path)
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(path) as conn:
                conn.execute(
                    "INSERT INTO users (username, password, salt, profile_json, created_at, updated_at) VALUES (?, '', '', '{}', ?, ?)",
                    ("alice", now, now),
                )
                conn.execute(
                    "INSERT INTO users (username, password, salt, profile_json, created_at, updated_at) VALUES (?, '', '', '{}', ?, ?)",
                    ("bob", now, now),
                )
                conn.commit()

            store.add_contact("alice", "bob")

            self.assertTrue(store.is_contact("alice", "bob"))
            self.assertFalse(store.is_accepted_contact("alice", "bob"))
            self.assertEqual(store.list_accepted_contacts("alice"), [])
            self.assertTrue(store.has_pending_contact_request("alice", "bob"))

            store.add_contact("bob", "alice")

            self.assertTrue(store.is_accepted_contact("alice", "bob"))
            self.assertEqual(store.list_accepted_contacts("alice")[0]["name"], "bob")
            self.assertFalse(store.has_pending_contact_request("alice", "bob"))
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass


class LightweightPollingEndpointTest(unittest.TestCase):
    def test_empty_launch_queue_does_not_write_profile(self):
        profile = {"username": "tester", "launch_queue": [], "system_messages": []}
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            response = client.get("/launch-queue")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_system_messages_without_new_messages_does_not_write_profile(self):
        profile = {
            "username": "tester",
            "launch_queue": [],
            "system_messages": [
                {"title": "Old", "text": "Read already", "status": "read"}
            ],
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            response = client.get("/system-messages")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])


class MissingProfileAndSessionSafetyTest(unittest.TestCase):
    def test_map_without_profile_redirects_to_login_instead_of_500(self):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "ghost"

        with patch.object(run, "sync_session_profile", return_value=None):
            response = client.get("/map")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

        follow = client.get("/")
        self.assertEqual(follow.status_code, 200)
        self.assertIn("Brak danych profilu".encode("utf-8"), follow.data)

    def test_root_username_profile_loads_even_when_nick_is_rut(self):
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [],
            "files": {},
            "own_places": None,
            "captured_targets": None,
            "territory": None,
            "areas": None,
        }

        with patch.object(run.user_store, "get_profile", return_value=profile):
            loaded = run.load_profile_readonly("root", normalize_apps=False, normalize_files=False)

        self.assertEqual(loaded["username"], "root")
        self.assertEqual(loaded["nick"], "Rut")
        self.assertEqual(loaded["own_places"], [])
        self.assertEqual(loaded["captured_targets"], [])
        self.assertEqual(loaded["territory"], [])
        self.assertEqual(loaded["areas"], [])

    def test_territory_hack_does_not_replace_session_user_with_owner(self):
        class FakeProfileManager:
            created_for = []

            def __init__(self, username):
                self.username = username
                self.__class__.created_for.append(username)

            def update_profile(self, updates):
                self.updates = updates

        critical_security = {
            key: True
            for key in [
                "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
                "browser_protection", "os_hardening", "log_guardian", "process_monitor",
                "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
                "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
                "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
                "background_injection", "memory_guard", "vpn_blocker",
            ]
        }
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "noop_tool",
                "name": "Noop Tool",
                "requires_off": [],
                "interferes_with": [],
                "levels": [{"options": []}],
            }],
            "aimed_target": {
                "target_mode": "territory_contest",
                "contest_owner_username": "owner_a",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Foreign pillar",
                "security": critical_security,
                "actions_allowed": {"scan_ports": True},
            },
            "system_messages": [],
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "find_captured_target_for_owner", return_value=None), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "noop_tool"})

        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as sess:
            self.assertEqual(sess["user"], "root")
        self.assertIn("root", FakeProfileManager.created_for)
        self.assertNotIn("owner_a", FakeProfileManager.created_for)


class FakeTerritoryStore:
    def __init__(self, targets):
        self.targets = targets
        self.synced = False

    def list_captured_targets(self, username, stationary=None):
        return list(self.targets)

    def sync_profile_hacked_targets(self, username, profile):
        self.synced = True
        return []


class TargetPersistenceHelpersTest(unittest.TestCase):
    def test_position_key_uses_lng_or_lon(self):
        left = {"lat": 52.1234567, "lng": 21.1234567}
        right = {"lat": 52.12345671, "lon": 21.12345671}

        self.assertEqual(target_position_key(left), target_position_key(right))
        self.assertTrue(targets_share_position(left, right))

    def test_filter_removes_by_position_without_label_match(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [
            {"lat": 52.1, "lng": 21.2, "label": "Punkt kolizyjny: AE Woman"},
            {"lat": 52.2, "lng": 21.3, "label": "Other"},
        ]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=False)

        self.assertEqual(removed, 1)
        self.assertEqual(filtered, [{"lat": 52.2, "lng": 21.3, "label": "Other"}])

    def test_filter_can_require_label_when_needed(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [{"lat": 52.1, "lng": 21.2, "label": "Other label"}]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=True)

        self.assertEqual(removed, 0)
        self.assertEqual(filtered, targets)

    def test_sqlite_captured_targets_replace_stale_profile_hacked(self):
        profile = {
            "hacked": [{"lat": 52.1, "lng": 21.2, "label": "Lost pillar"}],
            "captured_targets_source": "sqlite",
        }
        fake_store = FakeTerritoryStore([])

        with patch.object(run, "territory_store", fake_store):
            changed = run.merge_captured_targets_into_profile("defender", profile)

        self.assertTrue(changed)
        self.assertEqual(profile["hacked"], [])
        self.assertEqual(profile["captured_targets_source"], "sqlite")
        self.assertFalse(fake_store.synced)

    def test_player_actor_relation_prefers_friend_context(self):
        viewer = {"username": "neo", "clan": "VIREX"}
        actor = {"username": "trinity", "clan": "VIREX"}

        relation = resolve_player_actor_relation(viewer, actor, {"is_friend": True})

        self.assertEqual(relation, "friend")

    def test_player_actor_actions_disable_friend_targeting(self):
        actor = build_player_actor(
            "neo",
            {"username": "trinity", "nick": "Trinity", "lat": 52.1, "lng": 21.2},
            relation="friend",
            context={"source": "friend", "sources": ["friend"], "is_friend": True},
        )

        self.assertTrue(actor["actions"]["chat"]["enabled"])
        self.assertFalse(actor["actions"]["add_friend"]["enabled"])
        self.assertFalse(actor["actions"]["mark_target"]["enabled"])
        self.assertTrue(actor["actions"]["transfer_hc"]["enabled"])

    def test_map_action_router_prefers_app_map_actions(self):
        apps = [
            {"id": "legacy_scanner", "name": "Legacy", "type": "scanner", "detects": ["open_ports"]},
            {"id": "gps_tracker", "name": "GPS Tracker", "map_actions": ["trace_gps"], "type": "scanner"},
        ]

        matched, source = get_apps_for_map_action(apps, "trace_gps")

        self.assertEqual(source, "map_actions")
        self.assertEqual([app["id"] for app in matched], ["gps_tracker"])

    def test_legacy_app_contract_gets_runtime_map_actions(self):
        app = normalize_app_contract({
            "id": "scan_probe_v1",
            "name": "ScanProbe",
            "type": "scanner",
            "detects": ["open_ports", "user_location"],
        })

        self.assertIn("scan_ports", app["map_actions"])
        self.assertIn("trace", app["map_actions"])
        self.assertEqual(app["map_actions_source"], "legacy_inferred")

    def test_map_action_router_returns_no_match_for_missing_app(self):
        matched, source = get_apps_for_map_action([], "scan_ports")

        self.assertEqual(matched, [])
        self.assertEqual(source, "none")

    def test_legacy_trace_gps_app_gets_operation_type(self):
        app = normalize_app_contract({
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "type": "scanner",
            "detects": ["gps_location", "movement_data"],
        })

        self.assertIn("trace_gps", app["map_actions"])
        self.assertIn("vehicle_tracking", app["operation_types"])
        self.assertEqual(app["operation_types_source"], "legacy_inferred")

    def test_exploit_suite_legacy_inference_does_not_add_scan_ports(self):
        app = normalize_app_contract({
            "id": "pencombo_v1",
            "name": "PenCombo",
            "type": "exploit_suite",
            "detects": ["open_ports", "weak_configs", "inject_points"],
        })

        self.assertIn("exploit", app["map_actions"])
        self.assertNotIn("scan_ports", app["map_actions"])
        self.assertEqual(app["map_actions_source"], "legacy_inferred")

    def test_migration_inferred_pencombo_does_not_match_scan_ports(self):
        pencombo = {
            "id": "pencombo_v1",
            "name": "PenCombo",
            "type": "exploit_suite",
            "map_actions": ["exploit", "scan_ports"],
            "map_actions_source": "migration_inferred",
        }
        scanner = {
            "id": "scan_probe_v1",
            "name": "ScanProbe",
            "type": "scanner",
            "map_actions": ["scan_ports"],
            "map_actions_source": "migration_inferred",
        }

        scan_matches, scan_source = get_apps_for_map_action([pencombo, scanner], "scan_ports")
        exploit_matches, exploit_source = get_apps_for_map_action([pencombo, scanner], "exploit")

        scan_ids = [app["id"] for app in scan_matches]
        self.assertEqual(scan_source, "map_actions")
        self.assertEqual(scan_ids, ["scan_probe_v1"])
        self.assertEqual(exploit_source, "map_actions")
        self.assertEqual([app["id"] for app in exploit_matches], ["pencombo_v1"])

    def test_explicit_exploit_suite_map_actions_still_win(self):
        explicit_hybrid = normalize_app_contract({
            "id": "explicit_hybrid",
            "name": "Explicit Hybrid",
            "type": "exploit_suite",
            "map_actions": ["exploit", "scan_ports"],
        })

        self.assertIn("scan_ports", explicit_hybrid["map_actions"])
        self.assertIn("exploit", explicit_hybrid["map_actions"])

    def test_sniff_action_matches_sniffer_not_exploit_suite(self):
        apps = [
            {
                "id": "deep_sniff_r2",
                "name": "DeepSniff",
                "type": "scanner",
                "map_actions": ["sniff"],
                "map_actions_source": "migration_inferred",
            },
            {
                "id": "pencombo_v1",
                "name": "PenCombo",
                "type": "exploit_suite",
                "map_actions": ["exploit"],
                "map_actions_source": "migration_inferred",
            },
        ]

        matched, source = get_apps_for_map_action(apps, "sniff")

        self.assertEqual(source, "map_actions")
        self.assertEqual([app["id"] for app in matched], ["deep_sniff_r2"])

    def test_legacy_fallback_can_be_disabled_for_dev_tests(self):
        apps = [{
            "id": "legacy_scanner",
            "name": "Legacy Scanner",
            "type": "scanner",
            "detects": ["open_ports"],
        }]

        with patch.dict(os.environ, {"CHAOS_LEGACY_MAP_ACTION_FALLBACK": "false"}):
            matched, source = get_apps_for_map_action(apps, "scan_ports", allow_legacy_fallback=True)

        self.assertEqual(matched, [])
        self.assertEqual(source, "none")

    def test_googleplex_catalog_payload_exposes_runtime_contract(self):
        app = normalize_app_contract({
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "price": 50,
            "map_actions": ["trace_gps"],
            "operation_types": ["vehicle_tracking"],
            "resource_types": ["gps_logs", "location_history"],
            "target_types": ["vehicle"],
        })
        profile = {"hackcoins": 120, "apps": []}

        payload = googleplex_catalog_payload(app, profile)

        self.assertFalse(payload["installed"])
        self.assertTrue(payload["can_afford"])
        self.assertEqual(payload["install_blocked_reason"], "")
        self.assertEqual(payload["map_actions"], ["trace_gps"])
        self.assertEqual(payload["operation_types"], ["vehicle_tracking"])
        self.assertEqual(payload["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(payload["app_level"], "Advanced")
        self.assertGreater(payload["file_size"], 0)
        self.assertGreater(payload["disk_usage"], 0)
        self.assertEqual(payload["install_size"], payload["disk_usage"])
        self.assertGreater(payload["power_score"], 0)
        self.assertGreater(payload["price_hint"], 0)
        self.assertIn(payload["balance_tier"], {"Basic", "Advanced", "Pro"})

    def test_app_contract_adds_default_storage_fields(self):
        app = normalize_app_contract({
            "id": "camera_tool_v1",
            "name": "Camera Tool",
            "interface": "window",
            "type": "camera_tool",
            "map_actions": ["camera_stream"],
            "operation_types": ["camera_stream"],
            "resource_types": ["camera_dump", "video_material"],
        })

        self.assertGreaterEqual(app["file_size"], 1)
        self.assertGreaterEqual(app["disk_usage"], app["file_size"])
        self.assertEqual(app["install_size"], app["disk_usage"])
        self.assertGreaterEqual(app["quality_score"], 0)
        self.assertGreaterEqual(app["reliability"], 0)
        self.assertGreaterEqual(app["creator_power"], 0)
        self.assertGreater(app["power_score"], 0)
        self.assertGreater(app["price_hint"], 0)
        self.assertIn(app["balance_tier"], {"Basic", "Advanced", "Pro"})

    def test_legacy_app_keeps_explicit_price_but_gets_balance_hint(self):
        app = normalize_app_contract({
            "id": "admin_test_scan_ports_1",
            "name": "Admin Test Scanner",
            "type": "scanner",
            "price": 10,
            "map_actions": ["scan_ports"],
            "map_actions_source": "admin_test_seed",
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })

        self.assertEqual(app["price"], 10)
        self.assertGreater(app["price_hint"], app["price"])
        self.assertGreater(app["power_score"], 0)

    def assert_generated_app_install_and_command_preserve_levels(self, payload, assert_levels):
        with patch.object(run.user_store, "get_profile", return_value={"level": 18, "respect": 180, "hackcoins": 5000}):
            app = build_generated_app(payload, "creator", "Creator")

        assert_levels(app["levels"])

        profile = {
            "username": "creator",
            "nick": "Creator",
            "hackcoins": 10000,
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
            "system_messages": [],
        }
        store = [dict(app)]

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "creator"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.resources_store, "get", return_value=store), \
                patch.object(run.resources_store, "set", return_value=None), \
                patch.object(run, "get_app_catalog", return_value=store):
            install_response = client.post("/install-app", json={"app_id": app["id"]})
            self.assertEqual(install_response.status_code, 200)
            self.assertEqual(install_response.get_json()["status"], "success")

            installed = next(item for item in profile["apps"] if item["id"] == app["id"])
            assert_levels(installed["levels"])
            self.assertIn(f"{app['name']}.sh", profile["files"]["tools"])

            command_response = client.post("/command", json={"input": app["name"].lower()})
            command_data = command_response.get_json()
            self.assertTrue(command_data["runApp"])
            self.assertEqual(command_data["applicationId"], app["id"])
            assert_levels(command_data["applicationEffect"]["levels"])

    def test_button_maker_generated_app_keeps_button_choices_runtime_content(self):
        payload = {
            "name": "Choice Panel",
            "interface": "button_choices",
            "type": "custom",
            "level_title": "Wybierz tryb",
            "button_text": "Wybierz wariant działania.",
            "button_options": "Recon|risk_level=10|90\nShield|firewall=false|120",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Wybierz tryb")
            self.assertEqual(levels[0]["text"], "Wybierz wariant działania.")
            self.assertEqual(len(levels[0]["options"]), 2)
            self.assertEqual(levels[0]["options"][0]["label"], "Recon")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_term_creator_generated_app_keeps_terminal_runtime_content(self):
        payload = {
            "name": "Log Runner",
            "interface": "terminal",
            "type": "custom",
            "terminal_levels": [{
                "command": "./log-runner.sh --target current",
                "logs": "Start\nAnaliza\nRaport zapisany",
            }],
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["command"], "./log-runner.sh --target current")
            self.assertEqual(levels[0]["logs"], ["Start", "Analiza", "Raport zapisany"])

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_window_maker_generated_app_keeps_window_runtime_content(self):
        payload = {
            "name": "Status Window",
            "interface": "window",
            "type": "custom",
            "level_title": "Panel statusu",
            "window_list": "Sygnał stabilny\nKanał gotowy",
            "window_buttons": "Uruchom|run_generated\nZamknij|close",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Panel statusu")
            self.assertEqual(levels[0]["list"], ["Sygnał stabilny", "Kanał gotowy"])
            self.assertEqual(levels[0]["buttons"][0]["label"], "Uruchom")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_appforge_generated_app_keeps_progress_runtime_content(self):
        payload = {
            "name": "Progress Tool",
            "interface": "progressbar_random",
            "type": "custom",
            "level_title": "Wykonanie",
            "progress_steps": ["Kalibracja", "Pomiar", "Zapis stanu"],
            "result_success": "Operacja zakończona.",
            "result_failure": "Operacja przerwana.",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Wykonanie")
            self.assertEqual(levels[0]["steps"], ["Kalibracja", "Pomiar", "Zapis stanu"])
            self.assertEqual(levels[0]["result_success"], "Operacja zakończona.")
            self.assertEqual(levels[0]["result_failure"], "Operacja przerwana.")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_pro_system_tool_has_higher_balance_than_basic_tool(self):
        basic = normalize_app_contract({
            "id": "basic_ping",
            "name": "Basic Ping",
            "type": "scanner",
            "price": 80,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        pro = normalize_app_contract({
            "id": "ghostlab_financial",
            "name": "GhostLab Financial",
            "type": "pro-system-tool",
            "category": "pro-system-tools",
            "price": 3000,
            "required_level": 12,
            "required_respect": 180,
            "tool_family": "sniffer",
            "tool_mode": "desktop",
            "operation_types": [],
            "resource_types": ["financial_records", "internal_recon_state"],
            "ghostlab_generated": True,
        }, infer_legacy=False)

        self.assertGreater(pro["disk_usage"], basic["disk_usage"])
        self.assertGreater(pro["power_score"], basic["power_score"])
        self.assertGreater(pro["price_hint"], basic["price_hint"])

    def test_generated_app_quality_depends_on_creator_power(self):
        payload = {
            "name": "Creator Scanner",
            "interface": "progressbar_random",
            "type": "scanner",
            "detects": "open_ports,user_location",
            "price": 10,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 1, "respect": 0, "hackcoins": 0}):
            low_app = build_generated_app(payload, "low_creator", "Low")
        with patch.object(run.user_store, "get_profile", return_value={"level": 50, "respect": 1000, "hackcoins": 100000}):
            high_app = build_generated_app(payload, "high_creator", "High")

        self.assertGreater(high_app["creator_power"], low_app["creator_power"])
        self.assertGreater(high_app["quality_score"], low_app["quality_score"])
        self.assertGreater(high_app["reliability"], low_app["reliability"])
        self.assertGreater(high_app["price_hint"], low_app["price_hint"])

    def test_generated_app_price_uses_balance_floor(self):
        payload = {
            "name": "Cheap Creator Tool",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "map",
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks"],
            "target_types": ["router"],
            "price": 1,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 5, "respect": 10, "hackcoins": 100}):
            app = build_generated_app(payload, "cheap_creator", "Cheap")

        self.assertGreater(app["price_hint"], 1)
        self.assertEqual(app["price"], app["price_hint"])

    def test_generated_app_preserves_explicit_gameplay_contract(self):
        payload = {
            "name": "Wizard Scanner",
            "interface": "progressbar_random",
            "type": "scanner",
            "map_actions": ["scan_ports"],
            "target_types": ["router", "server"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks"],
            "price": 25,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 120, "hackcoins": 1000}):
            app = build_generated_app(payload, "wizard_creator", "Wizard")

        self.assertEqual(app["map_actions"], ["scan_ports"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "server"])
        self.assertEqual(app["operation_types"], ["wifi_scanner"])
        self.assertEqual(app["resource_types"], ["wifi_networks"])

    def test_map_scanner_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Recon",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "map",
            "map_actions": ["scan_ports", "scan_hotspots"],
            "target_types": ["router", "venue"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks", "internal_recon_state"],
            "detects": ["open_ports"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 10, "respect": 100, "hackcoins": 500}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["scanner_mode"], "map")
        self.assertEqual(app["map_actions"], ["scan_ports", "scan_hotspots"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "venue"])
        self.assertEqual(app["operation_types"], ["wifi_scanner"])
        self.assertEqual(app["resource_types"], ["wifi_networks", "internal_recon_state"])

    def test_desktop_scanner_creator_can_omit_map_actions(self):
        payload = {
            "name": "Desktop Recon",
            "interface": "terminal",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "desktop",
            "target_types": ["router", "server"],
            "operation_types": ["generic_trace"],
            "resource_types": ["internal_recon_state"],
            "detects": ["open_ports"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 8, "respect": 40, "hackcoins": 200}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["scanner_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "server"])
        self.assertEqual(app["operation_types"], ["generic_trace"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_hybrid_scanner_creator_can_use_map_and_aimed_target_contract(self):
        payload = {
            "name": "Hybrid Recon",
            "interface": "window",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "hybrid",
            "map_actions": ["trace", "scan_ports"],
            "target_types": ["poi", "player"],
            "operation_types": ["generic_trace"],
            "resource_types": ["location_history", "internal_recon_state"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 20, "respect": 250, "hackcoins": 5000}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "hybrid")
        self.assertEqual(app["scanner_mode"], "hybrid")
        self.assertEqual(app["map_actions"], ["trace", "scan_ports"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["generic_trace"])
        self.assertEqual(app["resource_types"], ["location_history", "internal_recon_state"])

    def test_map_exploit_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Exploit",
            "interface": "button_choices",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "map",
            "map_actions": ["exploit", "camera_shutdown"],
            "target_types": ["camera", "router"],
            "operation_types": ["camera_shutdown"],
            "resource_types": ["internal_recon_state"],
            "detects": ["weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 18, "respect": 220, "hackcoins": 2000}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["tool_family"], "exploit")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["map_actions"], ["exploit", "camera_shutdown"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["camera", "router"])
        self.assertEqual(app["operation_types"], ["camera_shutdown"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_desktop_exploit_creator_can_omit_map_actions(self):
        payload = {
            "name": "Desktop Exploit",
            "interface": "terminal",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["audio_interference"],
            "resource_types": ["internal_recon_state"],
            "detects": ["weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 80, "hackcoins": 300}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["tool_family"], "exploit")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["server"])
        self.assertEqual(app["operation_types"], ["audio_interference"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_map_sniffer_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Sniffer",
            "interface": "progressbar_random",
            "type": "sniffer",
            "tool_family": "sniffer",
            "tool_mode": "map",
            "map_actions": ["sniff", "atm_logs"],
            "target_types": ["atm", "router"],
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump", "financial_records"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 16, "respect": 140, "hackcoins": 1200}):
            app = build_generated_app(payload, "sniffer_creator", "Sniffer")

        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["map_actions"], ["sniff", "atm_logs"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["atm_log_extraction"])
        self.assertEqual(app["resource_types"], ["atm_dump", "financial_records"])

    def test_hybrid_sniffer_creator_can_use_map_and_aimed_target_contract(self):
        payload = {
            "name": "Hybrid Sniffer",
            "interface": "window",
            "type": "sniffer",
            "tool_family": "sniffer",
            "tool_mode": "hybrid",
            "map_actions": ["install_sniffer", "camera_stream"],
            "target_types": ["camera", "server"],
            "operation_types": ["persistent_sniffer", "camera_stream"],
            "resource_types": ["credentials", "camera_dump", "internal_recon_state"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 24, "respect": 300, "hackcoins": 7000}):
            app = build_generated_app(payload, "sniffer_creator", "Sniffer")

        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(app["tool_mode"], "hybrid")
        self.assertEqual(app["map_actions"], ["install_sniffer", "camera_stream"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["persistent_sniffer", "camera_stream"])
        self.assertEqual(app["resource_types"], ["credentials", "camera_dump", "internal_recon_state"])

    def test_creator_tool_family_disables_legacy_map_action_inference(self):
        payload = {
            "name": "Desktop Family Tool",
            "interface": "terminal",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["audio_interference"],
            "resource_types": ["internal_recon_state"],
            "detects": ["open_ports", "weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 10, "respect": 80, "hackcoins": 300}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")

    def test_ghostlab_published_tool_has_app_contract(self):
        project = {
            "id": "glp_logs",
            "name": "Log Reader Pro",
            "slug": "log_reader_pro",
            "icon": "GL",
            "template_id": "system_log_reader",
            "template_name": "System Log Reader",
            "tool_category": "intel",
            "blueprint": run.default_ghostlab_blueprint("system_log_reader"),
        }
        project["artifact"] = run.build_ghostlab_artifact(project, project["blueprint"], 1)
        owner_profile = {"nick": "Builder", "level": 30, "respect": 450, "hackcoins": 12000}

        app = run.build_ghostlab_googleplex_app(project, "builder", owner_profile)

        self.assertEqual(app["type"], "pro-system-tool")
        self.assertEqual(app["category"], "pro-system-tools")
        self.assertEqual(app["source"], "ghostlab")
        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "ghostlab_contract")
        self.assertEqual(app["target_types"], ["player"])
        self.assertEqual(app["operation_types"], [])
        self.assertEqual(app["resource_types"], ["device_logs", "internal_recon_state"])
        self.assertGreater(app["file_size"], 0)
        self.assertGreaterEqual(app["disk_usage"], app["file_size"])
        self.assertEqual(app["install_size"], app["disk_usage"])
        self.assertGreater(app["quality_score"], 0)
        self.assertGreater(app["reliability"], 0)

    def test_ghostlab_published_tool_preserves_requirements_and_googleplex_shape(self):
        project = {
            "id": "glp_fin",
            "name": "Financial Lab Tool",
            "slug": "financial_lab_tool",
            "template_id": "financial_sniffer",
            "template_name": "Financial Sniffer",
            "tool_category": "finance",
            "blueprint": run.default_ghostlab_blueprint("financial_sniffer"),
        }
        project["artifact"] = run.build_ghostlab_artifact(project, project["blueprint"], 2)
        owner_profile = {"nick": "Builder", "level": 40, "respect": 700, "hackcoins": 20000}

        app = run.build_ghostlab_googleplex_app(project, "builder", owner_profile)
        payload = googleplex_catalog_payload(app, {"hackcoins": 99999, "apps": []})

        self.assertEqual(app["required_level"], 12)
        self.assertEqual(app["required_respect"], 180)
        self.assertEqual(app["purchase_account"], "builder")
        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(payload["id"], app["id"])
        self.assertEqual(payload["type"], "pro-system-tool")
        self.assertEqual(payload["map_actions"], [])
        self.assertEqual(payload["operation_types"], [])
        self.assertEqual(payload["resource_types"], ["financial_records", "internal_recon_state"])

    def test_operation_quality_can_raise_generated_file_quality(self):
        profile = {
            "files": {
                "gps": [{
                    "name": "quality_demo.log",
                    "source_operation_id": "op_quality",
                    "resource_types": ["gps_logs"],
                    "metadata": {"checkpoint_count": 1, "quality_score": 35},
                }]
            }
        }
        ensure_files_inventory(profile)
        operation = {
            "operation_id": "op_quality",
            "source_app_quality": {
                "creator_power": 90,
                "quality_score": 82,
                "reliability": 88,
            },
        }

        changed = apply_operation_quality_to_files(profile, operation)
        ensure_files_inventory(profile)
        file_entry = profile["files"]["gps"][0]

        self.assertTrue(changed)
        self.assertEqual(file_entry["quality_score"], 82)
        self.assertEqual(file_entry["metadata"]["source_app_quality_score"], 82)
        self.assertEqual(file_entry["metadata"]["source_app_reliability"], 88)

    def test_runtime_files_and_profile_get_soft_storage_usage(self):
        profile = {
            "apps": [
                normalize_app_contract({
                    "id": "gps_tracker_v1",
                    "name": "GPS Tracker",
                    "map_actions": ["trace_gps"],
                    "operation_types": ["vehicle_tracking"],
                    "resource_types": ["gps_logs"],
                    "disk_usage": 20,
                })
            ],
            "files": {
                "gps": [{
                    "name": "gps_demo.log",
                    "resource_types": ["gps_logs", "location_history"],
                    "metadata": {"checkpoint_count": 3},
                }]
            },
        }

        files = ensure_files_inventory(profile)
        normalize_profile_storage(profile)

        self.assertGreater(files["gps"][0]["file_size"], 0)
        self.assertEqual(profile["storage_capacity"], 512)
        self.assertEqual(profile["storage_unit"], "MB")
        self.assertTrue(profile["storage_soft_limit"])
        self.assertGreaterEqual(profile["storage_used"], 20 + files["gps"][0]["file_size"])

    def test_googleplex_catalog_payload_blocks_installed_and_missing_hc(self):
        app = normalize_app_contract({
            "id": "atm_reader_v1",
            "name": "ATM Reader",
            "price": 500,
            "map_actions": ["atm_logs"],
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump"],
        })

        installed_payload = googleplex_catalog_payload(app, {
            "hackcoins": 1000,
            "apps": [{"id": "atm_reader_v1"}],
        })
        poor_payload = googleplex_catalog_payload(app, {
            "hackcoins": 10,
            "apps": [],
        })

        self.assertTrue(installed_payload["installed"])
        self.assertEqual(installed_payload["install_blocked_reason"], "Aplikacja juz kupiona.")
        self.assertFalse(poor_payload["can_afford"])
        self.assertIn("Brak HC", poor_payload["install_blocked_reason"])

    def test_uninstall_app_removes_profile_app_tool_and_recalculates_storage(self):
        app = normalize_app_contract({
            "id": "lifecycle_tool",
            "name": "Lifecycle Tool",
            "type": "scanner",
            "price": 100,
            "disk_usage": 30,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        profile = {
            "username": "tester",
            "apps": [app],
            "files": {
                "tools": ["Lifecycle Tool.sh"],
                "projects": ["Lifecycle Tool.sh"],
            },
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager):
            response = client.post("/api/apps/uninstall", json={
                "app_id": "lifecycle_tool",
                "tool_file": "Lifecycle Tool.sh",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["removed_app"])
        self.assertTrue(data["removed_tool"])
        self.assertEqual(data["apps"], [])
        self.assertNotIn("Lifecycle Tool.sh", data["files"]["tools"])
        self.assertIn("Lifecycle Tool.sh", data["files"]["projects"])
        self.assertEqual(updates["apps"], [])
        self.assertNotIn("Lifecycle Tool.sh", updates["files"]["tools"])
        self.assertLess(data["storage"]["used"], 30 + run.FILE_CATEGORY_SIZE_HINTS_MB["projects"])

    def test_uninstall_app_is_idempotent_for_missing_app(self):
        profile = {
            "username": "tester",
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager):
            response = client.post("/api/apps/uninstall", json={
                "app_id": "missing_tool",
                "tool_file": "Missing Tool.sh",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "noop")
        self.assertTrue(data["success"])
        self.assertFalse(data["removed_app"])
        self.assertFalse(data["removed_tool"])
        self.assertEqual(data["apps"], [])
        self.assertEqual(data["files"]["tools"], [])
        self.assertEqual(updates["apps"], [])

    def test_uninstall_seed_and_ghostlab_apps_only_changes_profile(self):
        seed_app = normalize_app_contract({
            "id": "seed_scan",
            "name": "Seed Scan",
            "type": "scanner",
            "price": 120,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        ghostlab_app = normalize_app_contract({
            "id": "ghostlab_tool",
            "name": "GhostLab Tool",
            "type": "pro-system-tool",
            "category": "pro-system-tools",
            "ghostlab_generated": True,
            "price": 3000,
            "project_file": "GhostLab Tool.sh",
            "resource_types": ["internal_recon_state"],
        }, infer_legacy=False)
        profile = {
            "username": "tester",
            "apps": [seed_app, ghostlab_app],
            "files": {
                "tools": ["Seed Scan.sh", "GhostLab Tool.sh"],
                "projects": ["GhostLab Tool.glab"],
            },
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.resources_store, "set", side_effect=AssertionError("catalog should not change")):
            ghost_response = client.post("/api/apps/uninstall", json={
                "app_id": "ghostlab_tool",
                "tool_file": "GhostLab Tool.sh",
            })
            seed_response = client.post("/api/apps/uninstall", json={
                "app_id": "seed_scan",
                "tool_file": "Seed Scan.sh",
            })

        self.assertEqual(ghost_response.status_code, 200)
        self.assertEqual(seed_response.status_code, 200)
        self.assertEqual(seed_response.get_json()["apps"], [])
        self.assertEqual(updates["files"]["tools"], [])
        self.assertEqual(updates["files"]["projects"], ["GhostLab Tool.glab"])

    def test_generated_app_install_tools_uninstall_lifecycle(self):
        payload = {
            "name": "Lifecycle Generated",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "map",
            "map_actions": ["scan_ports"],
            "target_types": ["router"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
            "price": 1,
        }
        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 100, "hackcoins": 1000}):
            app = build_generated_app(payload, "tester", "Tester")
        profile = {
            "username": "tester",
            "nick": "Tester",
            "hackcoins": 10000,
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
            "system_messages": [],
        }
        store = [dict(app)]

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.resources_store, "get", return_value=store), \
                patch.object(run.resources_store, "set", side_effect=lambda key, value: store[:] == value), \
                patch.object(run, "get_app_catalog", return_value=store):
            install_response = client.post("/install-app", json={"app_id": app["id"]})
            install_data = install_response.get_json()
            self.assertEqual(install_response.status_code, 200)
            self.assertEqual(install_data["status"], "success")
            self.assertTrue(any(item.get("id") == app["id"] for item in profile["apps"]))
            self.assertIn(f"{app['name']}.sh", profile["files"]["tools"])
            uninstall_response = client.post("/api/apps/uninstall", json={
                "app_id": app["id"],
                "tool_file": f"{app['name']}.sh",
            })

        uninstall_data = uninstall_response.get_json()
        self.assertEqual(uninstall_response.status_code, 200)
        self.assertEqual(uninstall_data["status"], "success")
        self.assertFalse(any(item.get("id") == app["id"] for item in uninstall_data["apps"]))
        self.assertNotIn(f"{app['name']}.sh", uninstall_data["files"]["tools"])

    def test_create_operation_for_app_action_adds_runtime_operation(self):
        profile = {"operations": []}
        app = {
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "operation_types": ["vehicle_tracking"],
            "resource_types": ["gps_logs", "location_history"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Tracked car",
            "source_type": "car",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "trace_gps", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(profile["operations"], created)
        self.assertEqual(operation["operation_type"], "vehicle_tracking")
        self.assertEqual(operation["owner_username"], "neo")
        self.assertEqual(operation["source_app_id"], "gps_tracker_v1")
        self.assertEqual(operation["map_action_id"], "trace_gps")
        self.assertEqual(operation["target_type"], "vehicle")
        self.assertEqual(operation["target_mode"], "standard")
        self.assertEqual(operation["status"], "running")
        self.assertIn("operation_id", operation)
        self.assertIn("expires_at", operation)
        self.assertEqual(operation["resource_buffer"]["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(operation["resource_buffer"]["items"], [])
        self.assertEqual(operation["risk_state"]["level"], "none")
        self.assertEqual(operation["movement_model"], "road_movement")
        self.assertIn("procedural_seed", operation)

    def test_operation_expiry_uses_timezone_aware_utc_durations(self):
        cases = [
            ("trace_gps", "vehicle_tracking", "car", 2 * 60 * 60),
            ("camera_stream", "camera_stream", "camera", 30 * 60),
            ("install_sniffer", "persistent_sniffer", "router", 3 * 60 * 60),
        ]

        for map_action_id, operation_type, source_type, expected_duration in cases:
            with self.subTest(operation_type=operation_type):
                operation = run.build_operation_instance(
                    "neo",
                    {
                        "id": f"{operation_type}_app",
                        "name": operation_type,
                        "resource_types": [],
                    },
                    map_action_id,
                    operation_type,
                    {
                        "lat": 52.1,
                        "lng": 21.2,
                        "label": operation_type,
                        "source_type": source_type,
                        "target_mode": "standard",
                    },
                )
                started_ts = run.parse_operation_timestamp(operation["started_at"])
                expires_ts = run.parse_operation_timestamp(operation["expires_at"])

                self.assertIsNotNone(started_ts)
                self.assertIsNotNone(expires_ts)
                self.assertAlmostEqual(expires_ts - started_ts, expected_duration, delta=1)

                refreshed = refresh_operation_runtime(operation, now_ts=started_ts + 1)
                self.assertEqual(refreshed["status"], "running")
                self.assertGreater(refreshed["remaining_seconds"], 0)
                self.assertTrue(run.operation_is_active(refreshed, now_ts=started_ts + 1))

    def test_refresh_operation_runtime_marks_expired_operation_timeout(self):
        profile = {
            "operations": [{
                "operation_id": "op_expired",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Camera"},
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(profile["operations"][0]["status"], "timeout")
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(refreshed[0]["remaining_seconds"], 0)

    def test_vehicle_tracking_current_position_changes_over_time(self):
        operation = {
            "operation_id": "op_vehicle",
            "operation_type": "vehicle_tracking",
            "owner_username": "neo",
            "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
            "target_type": "vehicle",
            "status": "running",
            "started_at": "2026-06-27T10:00:00Z",
            "expires_at": "2026-06-27T12:00:00Z",
            "duration_seconds": 7200,
            "movement_model": "road_movement",
            "procedural_seed": 12345,
        }

        early = refresh_operation_runtime(
            operation,
            now_ts=datetime(2026, 6, 27, 10, 10, tzinfo=timezone.utc).timestamp(),
        )
        later = refresh_operation_runtime(
            operation,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertNotEqual(early["current_position"], later["current_position"])
        self.assertEqual(early["movement_model"], "road_movement")

    def test_vehicle_tracking_timeout_creates_single_gps_file(self):
        profile = {
            "files": {"gps": []},
            "operations": [{
                "operation_id": "op_vehicle_done",
                "operation_type": "vehicle_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
                "target_id": "map:52.1:21.2:Tracked car",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T12:00:00Z",
                "duration_seconds": 7200,
                "movement_model": "road_movement",
                "procedural_seed": 12345,
                "resource_buffer": {"resource_types": ["gps_logs", "location_history"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["operations"][0]["checkpoints"]), 8)
        self.assertEqual(len(profile["files"]["gps"]), 1)

        gps_file = profile["files"]["gps"][0]
        self.assertEqual(gps_file["file_category"], "gps")
        self.assertEqual(gps_file["directory"], "/data/gps")
        self.assertEqual(gps_file["preview_mode"], "table")
        self.assertEqual(gps_file["metadata"]["operation_id"], "op_vehicle_done")
        self.assertEqual(gps_file["metadata"]["checkpoint_count"], 8)
        self.assertEqual(gps_file["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(len(gps_file["checkpoints"]), 8)

    def test_device_tracking_basic_app_creates_small_device_package(self):
        profile = {
            "files": {"device": [], "personal": []},
            "operations": [{
                "operation_id": "op_device_basic",
                "operation_type": "device_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Klient"},
                "target_id": "map:52.1:21.2:Klient",
                "target_type": "person",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "procedural_seed": 555,
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["device"]), 1)
        self.assertEqual(len(profile["files"]["personal"]), 0)

        device_file = profile["files"]["device"][0]
        self.assertEqual(device_file["resource_types"], ["location_history", "device_logs"])
        self.assertEqual(device_file["metadata"]["completeness"]["tier"], "basic")
        self.assertEqual(device_file["metadata"]["completeness"]["percent"], 33)

    def test_device_tracking_better_app_creates_richer_personal_package(self):
        profile = {
            "files": {"device": [], "personal": []},
            "operations": [{
                "operation_id": "op_device_rich",
                "operation_type": "device_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Smartfon"},
                "target_id": "map:52.1:21.2:Smartfon",
                "target_type": "phone",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "procedural_seed": 777,
                "resource_buffer": {
                    "resource_types": [
                        "location_history",
                        "device_logs",
                        "personal_records",
                        "call_history",
                        "messenger_data",
                    ],
                    "items": [],
                },
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["device"]), 0)
        self.assertEqual(len(profile["files"]["personal"]), 1)

        personal_file = profile["files"]["personal"][0]
        self.assertEqual(personal_file["file_category"], "personal")
        self.assertEqual(personal_file["directory"], "/data/personal")
        self.assertEqual(personal_file["metadata"]["completeness"]["tier"], "rich")
        self.assertEqual(personal_file["metadata"]["completeness"]["percent"], 83)
        self.assertIn("messenger_data", personal_file["resource_types"])

    def test_camera_stream_creates_fragments_without_duplicates(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_stream",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                "target_id": "map:52.1:21.2:Kamera sklepu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:30:00Z",
                "duration_seconds": 1800,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 12, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 12, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "running")
        self.assertEqual(refreshed[0]["remaining_seconds"], 1080)
        self.assertEqual(len(profile["files"]["camera"]), 2)
        self.assertEqual(len(profile["operations"][0]["fragments"]), 2)

        camera_file = profile["files"]["camera"][0]
        self.assertEqual(camera_file["file_category"], "camera")
        self.assertEqual(camera_file["directory"], "/data/camera")
        self.assertEqual(camera_file["preview_mode"], "media_placeholder")
        self.assertEqual(camera_file["resource_types"], ["camera_dump"])
        self.assertEqual(camera_file["metadata"]["operation_id"], "op_camera_stream")
        self.assertEqual(camera_file["metadata"]["duration_seconds"], 300)
        self.assertEqual(len(profile["files"]["camera"]), len(refreshed_again[0]["fragments"]))

    def test_camera_stream_honors_video_material_resource(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_video",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera parkingu"},
                "target_id": "map:52.1:21.2:Kamera parkingu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:15:00Z",
                "duration_seconds": 900,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["video_material"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["camera"]), 3)
        self.assertTrue(profile["files"]["camera"][0]["name"].endswith(".vid"))
        self.assertEqual(profile["files"]["camera"][0]["metadata"]["resource_primary"], "video_material")
        self.assertEqual(profile["files"]["camera"][0]["resource_types"], ["camera_dump", "video_material"])

    def test_camera_shutdown_sets_timed_support_state(self):
        profile = {
            "files": {},
            "operations": [{
                "operation_id": "op_camera_shutdown",
                "operation_type": "camera_shutdown",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                "target_id": "map:52.1:21.2:Kamera sklepu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_late, changed_late = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 11, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["support_state"]["camera_state"], "offline")
        self.assertEqual(refreshed[0]["support_state"]["remaining_seconds"], 300)
        self.assertEqual(refreshed[0]["support_state"]["risk_modifier"], "camera_shutdown")
        self.assertTrue(changed_late)
        self.assertEqual(refreshed_late[0]["status"], "timeout")
        self.assertEqual(profile["operations"][0]["support_state"]["camera_state"], "recovering")

    def test_atm_logs_app_creates_high_risk_operation(self):
        profile = {"operations": []}
        app = {
            "id": "atm_reader_v1",
            "name": "ATM Reader",
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "ATM",
            "source_type": "atm",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "atm_logs", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(operation["operation_type"], "atm_log_extraction")
        self.assertEqual(operation["target_type"], "atm")
        self.assertEqual(operation["risk_state"]["level"], "high")
        self.assertIn("atm_alarm", operation["risk_state"]["events"])
        self.assertFalse(operation["risk_state"]["consequences_enabled"])

    def test_atm_log_extraction_creates_single_atm_dump(self):
        profile = {
            "files": {"atm": [], "financial": []},
            "operations": [{
                "operation_id": "op_atm_dump",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Rynek"},
                "target_id": "map:52.1:21.2:ATM Rynek",
                "target_type": "atm",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 0)

        atm_file = profile["files"]["atm"][0]
        self.assertEqual(atm_file["file_category"], "atm")
        self.assertEqual(atm_file["directory"], "/data/atm")
        self.assertEqual(atm_file["preview_mode"], "table")
        self.assertEqual(atm_file["resource_types"], ["atm_dump"])
        self.assertEqual(atm_file["metadata"]["operation_id"], "op_atm_dump")
        self.assertEqual(atm_file["metadata"]["record_count"], 5)
        self.assertEqual(len(atm_file["records"]), 5)
        self.assertEqual(profile["operations"][0]["risk_state"]["level"], "high")

    def test_richer_atm_log_extraction_creates_financial_records_file(self):
        profile = {
            "files": {"atm": [], "financial": []},
            "operations": [{
                "operation_id": "op_atm_financial",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Bank"},
                "target_id": "map:52.1:21.2:ATM Bank",
                "target_type": "atm",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": ["financial_records"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 1)

        financial_file = profile["files"]["financial"][0]
        self.assertEqual(financial_file["file_category"], "financial")
        self.assertEqual(financial_file["directory"], "/data/financial")
        self.assertEqual(financial_file["preview_mode"], "table")
        self.assertEqual(financial_file["resource_types"], ["financial_records"])
        self.assertEqual(financial_file["metadata"]["record_count"], 8)
        self.assertEqual(len(financial_file["records"]), 8)

    def test_install_sniffer_creates_persistent_sniffer_operation(self):
        profile = {"operations": []}
        app = {
            "id": "persistent_sniffer_v1",
            "name": "PersistentSniffer",
            "operation_types": ["persistent_sniffer"],
            "resource_types": ["credentials"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Router",
            "source_type": "generated",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "install_sniffer", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(operation["operation_type"], "persistent_sniffer")
        self.assertEqual(operation["movement_model"], "implant_timer")
        self.assertEqual(operation["risk_state"]["level"], "medium")
        self.assertIn("long_operation_detected", operation["risk_state"]["events"])
        self.assertIn("sniffer_detected", operation["risk_state"]["events"])
        self.assertFalse(operation["risk_state"]["consequences_enabled"])

    def test_persistent_sniffer_creates_encrypted_credentials_without_duplicates(self):
        profile = {
            "files": {"credentials": [], "financial": [], "device": [], "system": []},
            "operations": [{
                "operation_id": "op_sniffer_credentials",
                "operation_type": "persistent_sniffer",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Router"},
                "target_id": "map:52.1:21.2:Router",
                "target_type": "router",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T13:00:00Z",
                "duration_seconds": 10800,
                "movement_model": "implant_timer",
                "resource_buffer": {"resource_types": ["credentials"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["credentials"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 0)

        credentials_file = profile["files"]["credentials"][0]
        self.assertEqual(credentials_file["file_category"], "credentials")
        self.assertEqual(credentials_file["directory"], "/data/credentials")
        self.assertEqual(credentials_file["preview_mode"], "encrypted_blob")
        self.assertEqual(credentials_file["resource_types"], ["credentials"])
        self.assertFalse(credentials_file["summary"]["plain_text_visible"])
        self.assertEqual(credentials_file["metadata"]["operation_id"], "op_sniffer_credentials")
        self.assertIn("sniffer_detected", profile["operations"][0]["risk_state"]["events"])

    def test_persistent_sniffer_rich_app_creates_multiple_resource_files(self):
        profile = {
            "files": {"credentials": [], "financial": [], "device": [], "system": []},
            "operations": [{
                "operation_id": "op_sniffer_rich",
                "operation_type": "persistent_sniffer",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Router"},
                "target_id": "map:52.1:21.2:ATM Router",
                "target_type": "router",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T13:00:00Z",
                "duration_seconds": 10800,
                "movement_model": "implant_timer",
                "resource_buffer": {
                    "resource_types": [
                        "financial_records",
                        "credentials",
                        "device_logs",
                        "internal_recon_state",
                    ],
                    "items": [],
                },
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 5, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["financial"]), 1)
        self.assertEqual(len(profile["files"]["credentials"]), 1)
        self.assertEqual(len(profile["files"]["device"]), 1)
        self.assertEqual(len(profile["files"]["system"]), 1)

        self.assertEqual(profile["files"]["financial"][0]["resource_types"], ["financial_records"])
        self.assertEqual(profile["files"]["credentials"][0]["preview_mode"], "encrypted_blob")
        self.assertEqual(profile["files"]["device"][0]["resource_types"], ["device_logs"])
        self.assertEqual(profile["files"]["system"][0]["resource_types"], ["internal_recon_state"])
        self.assertEqual(profile["operations"][0]["risk_state"]["level"], "high")
        self.assertIn("high_value", profile["operations"][0]["risk_state"]["events"])

    def test_wifi_scanner_timeout_creates_network_file_without_duplicates(self):
        profile = {
            "files": {"network": []},
            "operations": [{
                "operation_id": "op_wifi_scan",
                "operation_type": "wifi_scanner",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Cafe"},
                "target_id": "map:52.1:21.2:Cafe",
                "target_type": "venue",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": ["wifi_networks", "hotspot_database"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["network"]), 1)
        network_file = profile["files"]["network"][0]
        self.assertEqual(network_file["file_category"], "network")
        self.assertEqual(network_file["directory"], "/data/network")
        self.assertEqual(network_file["preview_mode"], "table")
        self.assertEqual(network_file["resource_types"], ["wifi_networks", "hotspot_database"])
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_audio_interference_timeout_creates_audio_transcript_without_duplicates(self):
        profile = {
            "files": {"audio": []},
            "operations": [{
                "operation_id": "op_audio_hack",
                "operation_type": "audio_interference",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Bar"},
                "target_id": "map:52.1:21.2:Bar",
                "target_type": "venue",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:20:00Z",
                "duration_seconds": 1200,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["audio_transcript"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 25, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 30, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["audio"]), 1)
        audio_file = profile["files"]["audio"][0]
        self.assertEqual(audio_file["file_category"], "audio")
        self.assertEqual(audio_file["directory"], "/data/audio")
        self.assertEqual(audio_file["preview_mode"], "transcript")
        self.assertEqual(audio_file["resource_types"], ["audio_transcript"])
        self.assertGreaterEqual(len(audio_file["transcript"]), 3)
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_vehicle_ecu_timeout_creates_vehicle_diagnostics_without_duplicates(self):
        profile = {
            "files": {"vehicle": []},
            "operations": [{
                "operation_id": "op_vehicle_ecu",
                "operation_type": "vehicle_ecu",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Auto"},
                "target_id": "map:52.1:21.2:Auto",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "road_movement",
                "resource_buffer": {"resource_types": ["vehicle_diagnostics"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["vehicle"]), 1)
        vehicle_file = profile["files"]["vehicle"][0]
        self.assertEqual(vehicle_file["file_category"], "vehicle")
        self.assertEqual(vehicle_file["directory"], "/data/vehicle")
        self.assertEqual(vehicle_file["preview_mode"], "table")
        self.assertEqual(vehicle_file["resource_types"], ["vehicle_diagnostics"])
        self.assertTrue(vehicle_file["records"])
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_generic_trace_timeout_creates_location_history_without_duplicates(self):
        profile = {
            "files": {"gps": [], "system": []},
            "operations": [{
                "operation_id": "op_generic_trace",
                "operation_type": "generic_trace",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Cel"},
                "target_id": "map:52.1:21.2:Cel",
                "target_type": "poi",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "resource_buffer": {"resource_types": ["location_history", "internal_recon_state"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["gps"]), 1)
        self.assertEqual(len(profile["files"]["system"]), 1)
        trace_file = profile["files"]["gps"][0]
        self.assertEqual(trace_file["file_category"], "gps")
        self.assertEqual(trace_file["directory"], "/data/gps")
        self.assertEqual(trace_file["preview_mode"], "table")
        self.assertEqual(trace_file["resource_types"], ["location_history"])
        self.assertTrue(trace_file["checkpoints"])
        listings = collect_ghost_exchange_files(profile)
        self.assertEqual(len([item for item in listings if item["file_category"] == "gps"]), 1)

    def test_camera_stream_timeout_creates_minimal_dump_without_prior_fragments(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_minimal",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera"},
                "target_id": "map:52.1:21.2:Kamera",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:02:00Z",
                "duration_seconds": 120,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["camera_dump"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 3, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 4, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["camera"]), 1)
        camera_file = profile["files"]["camera"][0]
        self.assertEqual(camera_file["file_category"], "camera")
        self.assertEqual(camera_file["resource_types"], ["camera_dump"])
        self.assertEqual(camera_file["metadata"]["duration_seconds"], 120)
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_file_inventory_normalizes_runtime_data_files_and_keeps_tools_compatible(self):
        profile = {
            "files": {
                "tools": ["TraceBike.sh"],
                "gps": [{
                    "name": "old_gps.log",
                    "operation_id": "op_old_gps",
                    "metadata": {
                        "target": {"label": "Old Vehicle"},
                        "ended_at": "2026-06-28T10:00:00Z",
                    },
                }],
            }
        }

        files = ensure_files_inventory(profile)

        for folder in [
            "tools",
            "gps",
            "device",
            "audio",
            "camera",
            "atm",
            "credentials",
            "financial",
            "personal",
            "network",
            "vehicle",
            "system",
            "market",
            "projects",
        ]:
            self.assertIn(folder, files)
            self.assertIsInstance(files[folder], list)

        self.assertEqual(files["tools"], ["TraceBike.sh"])
        gps_file = files["gps"][0]
        self.assertEqual(gps_file["id"], "file_gps_op_old_gps_old_gps_log")
        self.assertEqual(gps_file["file_category"], "gps")
        self.assertEqual(gps_file["directory"], "/data/gps")
        self.assertEqual(gps_file["preview_mode"], "table")
        self.assertEqual(gps_file["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(gps_file["source_operation_id"], "op_old_gps")
        self.assertEqual(gps_file["created_at"], "2026-06-28T10:00:00Z")
        self.assertEqual(gps_file["target_snapshot"]["label"], "Old Vehicle")
        self.assertTrue(gps_file["sellable"])
        self.assertEqual(gps_file["market_status"], "not_listed")
        self.assertIn("completeness_percent", gps_file)
        self.assertIn("completeness_tier", gps_file)
        self.assertIn("missing_fields", gps_file)
        self.assertIn("quality_score", gps_file)

    def test_file_inventory_sellable_matches_ghost_exchange_eligibility(self):
        profile = {
            "files": {
                "gps": [{
                    "name": "trace_client.log",
                    "operation_id": "op_trace_client",
                    "resource_types": ["location_history"],
                }],
                "system": [{
                    "name": "recon_state.sys",
                    "operation_id": "op_recon",
                    "resource_types": ["internal_recon_state"],
                }],
            }
        }

        files = ensure_files_inventory(profile)
        listings = collect_ghost_exchange_files(profile)

        self.assertTrue(files["gps"][0]["sellable"])
        self.assertFalse(files["system"][0]["sellable"])
        self.assertEqual([item["id"] for item in listings], [files["gps"][0]["id"]])

    def test_ghost_exchange_prices_richer_device_package_higher(self):
        profile = {
            "files": {
                "device": [{
                    "id": "basic_device",
                    "name": "basic_device.pkg",
                    "file_category": "device",
                    "directory": "/data/device",
                    "preview_mode": "card",
                    "resource_types": ["location_history", "device_logs"],
                    "metadata": {
                        "operation_id": "op_basic",
                        "completeness_percent": 33,
                        "completeness_tier": "fragment",
                        "quality_score": 48,
                        "collected_count": 2,
                    },
                }],
                "personal": [{
                    "id": "rich_device",
                    "name": "rich_device.pkg",
                    "file_category": "personal",
                    "directory": "/data/personal",
                    "preview_mode": "card",
                    "resource_types": [
                        "location_history",
                        "device_logs",
                        "personal_records",
                        "call_history",
                        "messenger_data",
                    ],
                    "metadata": {
                        "operation_id": "op_rich",
                        "completeness_percent": 83,
                        "completeness_tier": "rich",
                        "quality_score": 85,
                        "collected_count": 8,
                    },
                }],
            }
        }

        listings = collect_ghost_exchange_files(profile)
        by_id = {item["id"]: item for item in listings}

        self.assertGreater(by_id["rich_device"]["price_preview"], by_id["basic_device"]["price_preview"])
        self.assertEqual(by_id["basic_device"]["completeness_percent"], 33)
        self.assertEqual(by_id["rich_device"]["completeness_tier"], "rich")
        self.assertEqual(by_id["rich_device"]["quality_score"], 85)

    def test_cancelled_operation_moves_to_history_without_final_file(self):
        profile = {
            "files": {"gps": []},
            "operations": [{
                "operation_id": "op_cancel_vehicle",
                "operation_type": "vehicle_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
                "target_id": "map:52.1:21.2:Tracked car",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T12:00:00Z",
                "duration_seconds": 7200,
                "movement_model": "road_movement",
                "resource_buffer": {"resource_types": ["gps_logs", "location_history"], "items": []},
            }],
            "risk_events": [],
            "system_messages": [],
        }

        operation, result = cancel_profile_operation(
            profile,
            "op_cancel_vehicle",
            cancelled_by="neo",
            now_ts=datetime(2026, 6, 27, 10, 30, tzinfo=timezone.utc).timestamp(),
        )
        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 30, tzinfo=timezone.utc).timestamp(),
        )

        self.assertEqual(result, "cancelled")
        self.assertEqual(operation["status"], "cancelled")
        self.assertEqual(refreshed[0]["status"], "cancelled")
        self.assertEqual(active_operations_from_operations(refreshed), [])
        self.assertEqual(len(operation_history_from_operations(refreshed)), 1)
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(profile["operations"][0]["cleanup_state"]["active_object_active"], False)
        self.assertEqual(profile["operations"][0]["cleanup_state"]["marker_visible"], False)
        self.assertEqual(profile["risk_events"][0]["event_type"], "abandoned_operation")
        self.assertFalse(changed)

    def test_expired_camera_shutdown_no_longer_reduces_camera_risk(self):
        profile = {
            "operations": [
                {
                    "operation_id": "op_shutdown_expired",
                    "operation_type": "camera_shutdown",
                    "owner_username": "neo",
                    "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                    "target_id": "map:52.1:21.2:Kamera sklepu",
                    "target_type": "camera",
                    "status": "timeout",
                    "started_at": "2026-06-27T10:00:00Z",
                    "expires_at": "2026-06-27T10:05:00Z",
                    "ended_at": "2026-06-27T10:05:00Z",
                    "duration_seconds": 300,
                    "support_state": {"active": False, "risk_modifier": "camera_shutdown"},
                },
                {
                    "operation_id": "op_camera_stream_risk",
                    "operation_type": "camera_stream",
                    "owner_username": "neo",
                    "target": {"lat": 52.1001, "lng": 21.2001, "label": "Kamera sklepu"},
                    "target_id": "map:52.1001:21.2001:Kamera sklepu",
                    "target_type": "camera",
                    "status": "timeout",
                    "started_at": "2026-06-27T10:01:00Z",
                    "expires_at": "2026-06-27T10:06:00Z",
                    "ended_at": "2026-06-27T10:06:00Z",
                    "duration_seconds": 300,
                    "risk_state": {"level": "none", "events": ["camera_detected"], "score": 0},
                },
            ],
            "risk_events": [],
            "system_messages": [],
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        risk_event = next(event for event in profile["risk_events"] if event["event_type"] == "camera_detected")
        self.assertEqual(risk_event["risk_score"], 46)
        self.assertEqual(risk_event["modifiers"], [])
        self.assertEqual(active_operations_from_operations(refreshed), [])

    def test_finalizer_recreates_missing_atm_file_when_created_flag_is_stale(self):
        profile = {
            "files": {
                "atm": [],
                "financial": [],
                "market": [],
            },
            "market_history": [],
            "operations": [{
                "operation_id": "op_atm_missing_file",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "source_app_id": "atm_reader",
                "map_action_id": "atm_logs",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM"},
                "target_id": "map:52.1:21.2:ATM",
                "target_type": "atm",
                "target_mode": "standard",
                "status": "timeout",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:05:00Z",
                "ended_at": "2026-06-27T10:05:00Z",
                "duration_seconds": 300,
                "resource_buffer": {
                    "resource_types": ["atm_dump"],
                    "atm_files_created": True,
                    "files": [{"name": "lost_atm_dump.dump", "file_category": "atm"}],
                },
            }],
            "risk_events": [],
            "system_messages": [],
        }

        _, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 6, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(profile["files"]["atm"][0]["source_operation_id"], "op_atm_missing_file")
        self.assertTrue(profile["operations"][0]["resource_buffer"]["atm_files_created"])


if __name__ == "__main__":
    unittest.main()
