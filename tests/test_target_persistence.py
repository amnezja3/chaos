import unittest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import run
from database import DevBugReportStore
from run import (
    active_operations_from_operations,
    build_player_actor,
    cancel_profile_operation,
    collect_ghost_exchange_files,
    create_operations_for_app_action,
    ensure_files_inventory,
    filter_targets_by_position,
    get_apps_for_map_action,
    googleplex_catalog_payload,
    normalize_app_contract,
    operation_history_from_operations,
    refresh_operation_runtime,
    refresh_operations_runtime,
    resolve_player_actor_relation,
    target_position_key,
    targets_share_position,
)


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
                },
                created_by="tester",
                app_version="test-build",
            )

            self.assertEqual(report["status"], "new")
            self.assertEqual(report["category"], "UI")
            self.assertEqual(len(store.list_reports(search="camera")), 1)
            self.assertEqual(len(store.find_similar("Camera overlap")), 1)

            updated = store.update_report(report["id"], {"status": "confirmed"})
            self.assertEqual(updated["status"], "confirmed")
        finally:
            if os.path.exists(path):
                os.remove(path)


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
