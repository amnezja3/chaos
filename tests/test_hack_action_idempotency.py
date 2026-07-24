import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from database import AppActionReceiptStore, GameStateDeltaBus, PlayerInventoryStore, PlayerOperationStore, PlayerPositionStore, PlayerTargetRuntimeStore, SystemMessageStore, UserStore, WalletBalanceStore
import run


class HackActionIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "game.sqlite3")
        self.original_receipt_store = run.app_action_receipt_store
        self.original_target_store = run.player_target_runtime_store
        self.original_position_store = run.player_position_store
        self.original_operation_store = run.player_operation_store
        self.original_system_message_store = run.system_message_store
        self.original_inventory_store = run.player_inventory_store
        self.original_wallet_balance_store = run.wallet_balance_store
        self.original_delta_bus = run.delta_bus
        run.app_action_receipt_store = AppActionReceiptStore(db_path=self.db_path)
        run.player_target_runtime_store = PlayerTargetRuntimeStore(db_path=self.db_path)
        run.player_position_store = PlayerPositionStore(db_path=self.db_path)
        run.player_operation_store = PlayerOperationStore(db_path=self.db_path)
        run.system_message_store = SystemMessageStore(db_path=self.db_path)
        run.player_inventory_store = PlayerInventoryStore(db_path=self.db_path)
        run.wallet_balance_store = WalletBalanceStore(db_path=self.db_path)
        run.delta_bus = GameStateDeltaBus(db_path=self.db_path)
        with run._hack_action_idempotency_lock:
            run._hack_action_idempotency_cache.clear()

    def tearDown(self):
        run.app_action_receipt_store = self.original_receipt_store
        run.player_target_runtime_store = self.original_target_store
        run.player_position_store = self.original_position_store
        run.player_operation_store = self.original_operation_store
        run.system_message_store = self.original_system_message_store
        run.player_inventory_store = self.original_inventory_store
        run.wallet_balance_store = self.original_wallet_balance_store
        run.delta_bus = self.original_delta_bus
        self.tmpdir.cleanup()

    def test_in_flight_flow_blocks_duplicate_execution(self):
        key = run.build_hack_action_idempotency_key(
            "main",
            "hf-test",
            "scan_ports",
            {"id": "port_scanner", "name": "Port Scanner"},
        )

        state, receipt = run.begin_hack_action_idempotency(key)
        duplicate_state, duplicate_receipt = run.begin_hack_action_idempotency(key)

        self.assertEqual(state, "new")
        self.assertIsNone(receipt)
        self.assertEqual(duplicate_state, "in_flight")
        self.assertEqual(duplicate_receipt["state"], "in_flight")

    def test_completed_flow_returns_replay_payload(self):
        key = run.build_hack_action_idempotency_key(
            "main",
            "hf-test",
            "scan_ports",
            {"id": "port_scanner", "name": "Port Scanner"},
        )
        payload = {"status": "done", "created_operations": [{"operation_id": "op_1"}]}

        run.begin_hack_action_idempotency(key)
        run.finish_hack_action_idempotency(key, payload, 200)
        state, receipt = run.begin_hack_action_idempotency(key)

        self.assertEqual(state, "completed")
        self.assertEqual(receipt["payload"], payload)
        self.assertEqual(receipt["status_code"], 200)

    def test_completed_flow_survives_memory_cache_clear(self):
        key = run.build_hack_action_idempotency_key(
            "main",
            "hf-test",
            "scan_ports",
            {"id": "port_scanner", "name": "Port Scanner"},
        )
        payload = {"status": "done", "created_operations": [{"operation_id": "op_1"}]}

        run.begin_hack_action_idempotency(key, {
            "username": "main",
            "app_id": "port_scanner",
            "action": "scan_ports",
            "target_key": "poi-1",
            "source": "map",
        })
        run.finish_hack_action_idempotency(key, payload, 200)
        with run._hack_action_idempotency_lock:
            run._hack_action_idempotency_cache.clear()
        state, receipt = run.begin_hack_action_idempotency(key)

        self.assertEqual(state, "completed")
        self.assertEqual(receipt["payload"], payload)
        self.assertEqual(receipt["store"], "sqlite")

    def test_client_action_key_wins_over_flow_id_for_map_retries(self):
        first = run.build_hack_action_idempotency_key(
            "main",
            "hf-first",
            "scan_ports",
            {"id": "port_scanner", "name": "Port Scanner"},
            "scan_ports|52.308268|21.062800|parcel_locker||territory_contest||POI-7C133E",
        )
        retry = run.build_hack_action_idempotency_key(
            "main",
            "hf-retry",
            "scan_ports",
            {"id": "port_scanner", "name": "Port Scanner"},
            "scan_ports|52.308268|21.062800|parcel_locker||territory_contest||POI-7C133E",
        )

        self.assertEqual(first, retry)

    def test_create_operations_for_app_action_skips_active_duplicate(self):
        run.player_operation_store.clear_all()
        profile = {"operations": []}
        app = {
            "id": "scanner_1",
            "name": "Port Scanner",
            "operation_types": ["wifi_scanner"],
        }
        target = {"lat": 52.1, "lng": 21.1, "label": "POI-1"}

        first = run.create_operations_for_app_action(profile, "main", app, "scan_ports", target)
        second = run.create_operations_for_app_action(profile, "main", app, "scan_ports", target)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(len(profile["operations"]), 1)

    def test_player_operation_store_skips_cross_worker_active_duplicate(self):
        first = {
            "operation_id": "op_first",
            "target_id": "target-1",
            "map_action_id": "scan_ports",
            "operation_type": "wifi_scanner",
            "source_app_id": "scanner_1",
            "status": "running",
            "started_at": "2026-07-22T10:00:00+00:00",
        }
        duplicate = {
            **first,
            "operation_id": "op_duplicate",
        }

        accepted_first = run.player_operation_store.upsert_operations("main", [first], event_type="operation.started")
        accepted_duplicate = run.player_operation_store.upsert_operations("main", [duplicate], event_type="operation.started")

        self.assertEqual([item["operation_id"] for item in accepted_first], ["op_first"])
        self.assertEqual(accepted_duplicate, [])
        self.assertEqual(
            [item["operation_id"] for item in run.player_operation_store.list_operations("main")],
            ["op_first"],
        )

    def test_player_operation_store_cancel_is_idempotent(self):
        operation = {
            "operation_id": "op_cancel",
            "target_id": "target-1",
            "map_action_id": "trace",
            "operation_type": "generic_trace",
            "source_app_id": "trace_1",
            "status": "running",
        }
        run.player_operation_store.upsert_operations("main", [operation], event_type="operation.started")

        cancelled, result = run.player_operation_store.cancel_operation("main", "op_cancel")
        second, second_result = run.player_operation_store.cancel_operation("main", "op_cancel")

        self.assertEqual(result, "cancelled")
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(second_result, "already_terminal")
        self.assertEqual(second["status"], "cancelled")

    def test_system_message_store_consumes_once_with_dedupe(self):
        message = {
            "type": "info",
            "title": "Efekt",
            "text": "Gotowe",
            "dedupe_key": "effect:op-1",
        }

        _, created_first = run.system_message_store.add_message("main", message)
        _, created_second = run.system_message_store.add_message("main", message)
        first = run.system_message_store.consume_pending("main")
        second = run.system_message_store.consume_pending("main")

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["title"], "Efekt")
        self.assertEqual(second, [])

    def test_system_messages_endpoint_consumes_store_without_profile_write(self):
        profile = {"username": "main", "system_messages": []}
        run.system_message_store.add_message("main", {
            "type": "info",
            "title": "Efekt",
            "text": "Gotowe",
            "dedupe_key": "effect:op-1",
        })
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "main"

        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            first = client.get("/system-messages")
            second = client.get("/system-messages")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(first.get_json()), 1)
        self.assertEqual(second.get_json(), [])

    def test_inventory_store_mirrors_apps_tools_and_storage(self):
        profile = {
            "apps": [{"id": "scanner_1", "name": "Port Scanner", "status": "installed"}],
            "files": {"tools": ["Port Scanner.sh"]},
            "storage_capacity": 512,
            "storage_used": 42,
            "storage_unit": "MB",
        }

        run.player_inventory_store.write_from_profile("main", profile)
        mirror = {"apps": [], "files": {"tools": []}, "storage_capacity": 0, "storage_used": 0}
        run.player_inventory_store.mirror_profile("main", mirror)

        self.assertEqual(mirror["apps"][0]["id"], "scanner_1")
        self.assertEqual(mirror["storage_capacity"], 512)
        self.assertEqual(mirror["storage_used"], 42)
        self.assertTrue(mirror["files"]["tools"])

    def test_record_apps_and_storage_delta_updates_inventory_store(self):
        profile = {
            "apps": [{"id": "snfx_1", "name": "Snfx", "status": "installed"}],
            "files": {"tools": ["Snfx.sh"]},
            "storage_capacity": 1024,
            "storage_used": 128,
            "storage_unit": "MB",
        }

        run.record_apps_delta("main", profile, "apps.app_installed", app=profile["apps"][0], app_id="snfx_1")
        run.record_storage_delta("main", profile, reason="test")
        snapshot = run.player_inventory_store.snapshot("main")

        self.assertEqual(snapshot["apps"][0]["id"], "snfx_1")
        self.assertEqual(snapshot["storage"]["used"], 128)

    def test_wallet_balance_store_idempotent_transaction_key(self):
        first = run.wallet_balance_store.set_balance("main", 100, transaction_key="tx-1", reason="test")
        second = run.wallet_balance_store.set_balance("main", 999, transaction_key="tx-1", reason="retry")

        self.assertEqual(first, 100)
        self.assertEqual(second, 100)
        self.assertEqual(run.wallet_balance_store.get_balance("main"), 100)

    def test_record_wallet_balance_delta_updates_balance_store(self):
        run.record_wallet_balance_delta("main", 321, reason="test", dedupe_key="wallet:test:main")

        self.assertEqual(run.wallet_balance_store.get_balance("main"), 321)

    def test_operations_summary_reads_store_without_profile_refresh(self):
        operation = {
            "operation_id": "op_summary",
            "target_id": "target-1",
            "map_action_id": "trace",
            "operation_type": "generic_trace",
            "source_app_id": "trace_1",
            "status": "running",
            "started_at": "2026-07-22T10:00:00+00:00",
            "expires_at": "2030-07-22T11:00:00+00:00",
        }
        run.player_operation_store.upsert_operations("main", [operation], event_type="operation.started")
        profile = {"username": "main", "operations": [operation], "system_messages": []}
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "main"

        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=AssertionError("summary should not refresh full profile")):
            response = client.get("/api/operations?summary=1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["source"], "player_operations")
        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["active_operations"][0]["operation_id"], "op_summary")

    def test_merge_operations_monotonic_preserves_latest_and_incoming_work(self):
        latest = [
            {
                "operation_id": "op_scan",
                "target_id": "target-1",
                "map_action_id": "scan_ports",
                "operation_type": "wifi_scanner",
                "source_app_id": "scanner_1",
                "status": "running",
            }
        ]
        incoming = [
            {
                "operation_id": "op_trace",
                "target_id": "target-1",
                "map_action_id": "trace",
                "operation_type": "generic_trace",
                "source_app_id": "trace_1",
                "status": "running",
            }
        ]

        merged = run.merge_operations_monotonic(latest, incoming)

        self.assertEqual({op["operation_id"] for op in merged}, {"op_scan", "op_trace"})

    def test_merge_operations_monotonic_skips_cross_worker_active_duplicate(self):
        latest = [
            {
                "operation_id": "op_first",
                "target_id": "target-1",
                "map_action_id": "scan_ports",
                "operation_type": "wifi_scanner",
                "source_app_id": "scanner_1",
                "status": "running",
            }
        ]
        incoming = [
            {
                "operation_id": "op_duplicate",
                "target_id": "target-1",
                "map_action_id": "scan_ports",
                "operation_type": "wifi_scanner",
                "source_app_id": "scanner_1",
                "status": "running",
            }
        ]

        merged = run.merge_operations_monotonic(latest, incoming)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["operation_id"], "op_first")

    def test_merge_latest_profile_runtime_fields_preserves_saved_runtime_fields(self):
        latest_profile = {
            "operations": [
                {
                    "operation_id": "op_scan",
                    "target_id": "target-1",
                    "map_action_id": "scan_ports",
                    "operation_type": "wifi_scanner",
                    "source_app_id": "scanner_1",
                    "status": "running",
                }
            ],
            "launch_queue": ["Port Scanner"],
        }
        fields = {
            "operations": [
                {
                    "operation_id": "op_trace",
                    "target_id": "target-1",
                    "map_action_id": "trace",
                    "operation_type": "generic_trace",
                    "source_app_id": "trace_1",
                    "status": "running",
                }
            ],
            "launch_queue": ["Trace Compass"],
        }

        with patch.object(run.user_store, "get_profile", return_value=latest_profile):
            merged = run.merge_latest_profile_runtime_fields("main", fields)

        self.assertEqual({op["operation_id"] for op in merged["operations"]}, {"op_scan", "op_trace"})
        self.assertEqual(merged["launch_queue"], ["Port Scanner", "Trace Compass"])

    def test_merge_latest_profile_runtime_fields_allows_launch_queue_consume_clear(self):
        latest_profile = {"launch_queue": ["V-MAP"]}

        with patch.object(run.user_store, "get_profile", return_value=latest_profile):
            merged = run.merge_latest_profile_runtime_fields("main", {"launch_queue": []})

        self.assertEqual(merged["launch_queue"], [])

    def test_user_store_does_not_resurrect_consumed_launch_queue_from_stale_save(self):
        with TemporaryDirectory() as tmpdir:
            store = UserStore(
                db_path=str(Path(tmpdir) / "game.sqlite3"),
                seed_path=str(Path(tmpdir) / "missing_users.json"),
            )
            store.save_profile({
                "username": "main",
                "password": "pw",
                "salt": "",
                "launch_queue": [],
            })

            pending = store.get_profile("main")
            pending["launch_queue"] = ["Snfx"]
            pending["_launch_queue_write_mode"] = "append"
            store.save_profile(pending)

            stale = store.get_profile("main")
            consumed = store.get_profile("main")
            consumed["launch_queue"] = []
            consumed["_launch_queue_write_mode"] = "clear"
            store.save_profile(consumed)

            stale["system_messages"] = [{"id": 1, "title": "Late writer"}]
            store.save_profile(stale)

            self.assertEqual(store.get_profile("main")["launch_queue"], [])

    def test_user_store_consume_launch_queue_is_one_shot(self):
        with TemporaryDirectory() as tmpdir:
            store = UserStore(
                db_path=str(Path(tmpdir) / "game.sqlite3"),
                seed_path=str(Path(tmpdir) / "missing_users.json"),
            )
            store.save_profile({
                "username": "main",
                "password": "pw",
                "salt": "",
                "launch_queue": ["Snfx", "Snfx", "Trace Compass"],
            })

            first = store.consume_launch_queue("main")
            second = store.consume_launch_queue("main")

            self.assertEqual(first, ["Snfx", "Trace Compass"])
            self.assertEqual(second, [])
            self.assertEqual(store.get_profile("main")["launch_queue"], [])

    def test_filter_accepted_created_operations_drops_rejected_cross_worker_duplicate(self):
        profile_after_merge = {
            "operations": [
                {
                    "operation_id": "op_first",
                    "target_id": "target-1",
                    "map_action_id": "scan_ports",
                    "operation_type": "wifi_scanner",
                    "source_app_id": "scanner_1",
                    "status": "running",
                }
            ]
        }
        locally_created = [
            {
                "operation_id": "op_duplicate",
                "target_id": "target-1",
                "map_action_id": "scan_ports",
                "operation_type": "wifi_scanner",
                "source_app_id": "scanner_1",
                "status": "running",
            }
        ]

        accepted = run.filter_accepted_created_operations(profile_after_merge, locally_created)

        self.assertEqual(accepted, [])

    def test_filter_accepted_created_operations_keeps_saved_operation(self):
        profile_after_merge = {
            "operations": [
                {
                    "operation_id": "op_scan",
                    "target_id": "target-1",
                    "map_action_id": "scan_ports",
                    "operation_type": "wifi_scanner",
                    "source_app_id": "scanner_1",
                    "status": "running",
                }
            ]
        }
        locally_created = [
            {
                "operation_id": "op_scan",
                "target_id": "target-1",
                "map_action_id": "scan_ports",
                "operation_type": "wifi_scanner",
                "source_app_id": "scanner_1",
                "status": "running",
            }
        ]

        accepted = run.filter_accepted_created_operations(profile_after_merge, locally_created)

        self.assertEqual(accepted, locally_created)

    def test_merge_latest_aimed_target_runtime_state_clears_already_captured_target(self):
        profile = {
            "aimed_target": {
                "lat": 52.3082685,
                "lng": 21.0628002,
                "label": "POI-7C133E",
                "actions_allowed": {"scan_ports": True, "exploit": True, "sniff": True},
            }
        }
        captured = {
            "lat": 52.3082685,
            "lng": 21.0628002,
            "label": "POI-7C133E",
            "owner_username": "main",
        }

        with patch.object(run.territory_store, "list_captured_targets", return_value=[captured]):
            result = run.merge_latest_aimed_target_runtime_state(profile, "main")

        self.assertEqual(result, {})
        self.assertEqual(profile["aimed_target"], {})

    def test_set_player_aimed_target_does_not_resurrect_already_captured_target(self):
        profile = {}
        captured = {
            "lat": 52.3082685,
            "lng": 21.0628002,
            "label": "POI-7C133E",
            "owner_username": "main",
        }

        with patch.object(run.territory_store, "list_captured_targets", return_value=[captured]), \
            patch.object(run, "merge_latest_profile_runtime_fields", side_effect=lambda _username, fields: fields), \
            patch.object(run, "UserProfileManager") as manager_class, \
            patch.object(run, "safe_ghostnetwork_on_target_aimed") as ghost_hook:
            result = run.set_player_aimed_target(
                "main",
                profile,
                {"lat": 52.3082685, "lng": 21.0628002, "label": "POI-7C133E"},
                update_fields={"launch_queue": ["V-MAP"]},
            )

        self.assertEqual(result, {})
        self.assertEqual(profile["aimed_target"], {})
        manager_class.return_value.update_profile.assert_called_once()
        saved_fields = manager_class.return_value.update_profile.call_args.args[0]
        self.assertEqual(saved_fields["aimed_target"], {})
        self.assertEqual(saved_fields["launch_queue"], ["V-MAP"])
        ghost_hook.assert_not_called()

    def test_normalize_profile_position_update_writes_legacy_and_canonical_fields(self):
        result = run.normalize_profile_position_update({"lat": "52.1", "lon": "21.2"})

        self.assertEqual(result["curently_possition"], {"lat": 52.1, "lng": 21.2})
        self.assertEqual(result["current_position"], {"lat": 52.1, "lng": 21.2})
        self.assertIsNot(result["curently_possition"], result["current_position"])

    def test_position_runtime_store_duplicate_position_keeps_version(self):
        first = run.player_position_store.upsert(
            "main",
            {"lat": 52.55, "lng": 19.67},
            source="travel",
        )
        second = run.player_position_store.upsert(
            "main",
            {"lat": 52.55, "lng": 19.67},
            source="travel_retry",
        )

        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(second["position"], {"lat": 52.55, "lng": 19.67})
        self.assertEqual(second["version"], first["version"])

    def test_target_runtime_store_merges_actions_and_security_monotonically(self):
        base = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "POI-1",
            "target_id": "map:poi-1",
            "actions_allowed": {"scan_ports": True, "exploit": False},
            "security": {"scan": False, "exploit": True},
        }
        later = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "POI-1",
            "target_id": "map:poi-1",
            "actions_allowed": {"scan_ports": False, "exploit": True},
            "security": {"scan": True, "exploit": False},
        }

        run.player_target_runtime_store.upsert_aimed("main", base, source="map")
        result = run.player_target_runtime_store.upsert_aimed("main", later, source="terminal")

        target = result["target"]
        self.assertIs(target["actions_allowed"]["scan_ports"], True)
        self.assertIs(target["actions_allowed"]["exploit"], True)
        self.assertIs(target["security"]["scan"], False)
        self.assertIs(target["security"]["exploit"], False)

    def test_target_runtime_store_keeps_existing_label_when_late_payload_is_missing_name(self):
        base = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "POI-1",
            "name": "POI-1",
            "target_id": "map:poi-1",
            "actions_allowed": {"scan_ports": True},
        }
        late = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "brak",
            "name": "",
            "target_id": "map:poi-1",
            "actions_allowed": {"exploit": True},
        }

        run.player_target_runtime_store.upsert_aimed("main", base, source="map")
        result = run.player_target_runtime_store.upsert_aimed("main", late, source="late_map")

        target = result["target"]
        self.assertEqual(target["label"], "POI-1")
        self.assertEqual(target["name"], "POI-1")
        self.assertIs(target["actions_allowed"]["scan_ports"], True)
        self.assertIs(target["actions_allowed"]["exploit"], True)

    def test_target_runtime_store_rejects_zero_coordinate_placeholder_target(self):
        placeholder = {
            "lat": 0.0,
            "lng": 0.0,
            "label": "target",
            "target_id": "map:0.0:0.0:target",
            "actions_allowed": {"scan_ports": True, "exploit": True, "sniff": True, "trace": True},
        }

        result = run.player_target_runtime_store.upsert_aimed("main", placeholder, source="late_placeholder")

        self.assertFalse(result["changed"])
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(run.player_target_runtime_store.get_active_target("main"), {})

    def test_target_runtime_store_rejects_stale_aimed_after_capture(self):
        target = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "POI-1",
            "target_id": "map:poi-1",
            "actions_allowed": {"scan_ports": True},
        }

        run.player_target_runtime_store.upsert_aimed("main", target, source="map")
        run.player_target_runtime_store.mark_captured("main", target, source="capture")
        result = run.player_target_runtime_store.upsert_aimed("main", target, source="late_map")

        self.assertFalse(result["changed"])
        self.assertEqual(result["status"], "captured")
        self.assertEqual(run.player_target_runtime_store.get_active_target("main"), {})

    def test_merge_latest_target_runtime_state_keeps_captured_store_terminal(self):
        target = {
            "lat": 52.3,
            "lng": 21.0,
            "label": "POI-1",
            "target_id": "map:poi-1",
            "actions_allowed": {"scan_ports": True, "exploit": True},
        }
        stale_profile = {"aimed_target": dict(target)}

        run.player_target_runtime_store.upsert_aimed("main", target, source="map")
        run.player_target_runtime_store.mark_captured("main", target, source="capture")
        result = run.merge_latest_aimed_target_runtime_state(stale_profile, "main")

        self.assertEqual(result, {})
        self.assertEqual(stale_profile["aimed_target"], {})

    def test_position_runtime_store_overlays_profile_position(self):
        run.normalize_profile_position_update(
            {"lat": "52.55", "lng": "19.67"},
            username="main",
            source="terminal",
        )
        stale_profile = {
            "curently_possition": {"lat": 52.1, "lng": 21.1},
            "current_position": {"lat": 52.1, "lng": 21.1},
        }

        run.apply_runtime_stores_to_profile("main", stale_profile)

        self.assertEqual(stale_profile["curently_possition"], {"lat": 52.55, "lng": 19.67})
        self.assertEqual(stale_profile["current_position"], {"lat": 52.55, "lng": 19.67})


if __name__ == "__main__":
    unittest.main()
