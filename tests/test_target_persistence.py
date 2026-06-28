import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import run
from run import (
    build_player_actor,
    create_operations_for_app_action,
    ensure_files_inventory,
    filter_targets_by_position,
    get_apps_for_map_action,
    normalize_app_contract,
    refresh_operation_runtime,
    refresh_operations_runtime,
    resolve_player_actor_relation,
    target_position_key,
    targets_share_position,
)


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
        self.assertFalse(gps_file["sellable"])
        self.assertEqual(gps_file["market_status"], "not_listed")


if __name__ == "__main__":
    unittest.main()
