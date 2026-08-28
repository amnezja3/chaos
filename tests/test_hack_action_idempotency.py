import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from database import AppActionReceiptStore, GameStateDeltaBus, PlayerInventoryStore, PlayerOperationStore, PlayerPositionStore, PlayerTargetRuntimeStore, ProfileWriteConflict, SystemMessageStore, UserStore, WalletBalanceStore, WalletIdempotencyConflict
from session_generation_store import SessionGenerationStore
import run


def complete_test_profile(username="main", balance=0, launch_queue=None):
    return {
        "username": username,
        "password": "pw",
        "salt": "",
        "level": 1,
        "hackcoins": balance,
        "respect": 0,
        "exp": "0 / 1000",
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "system_messages": [],
        "launch_queue": list(launch_queue or []),
    }


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
        self.original_session_generation_store = run.session_generation_store
        run.app_action_receipt_store = AppActionReceiptStore(db_path=self.db_path)
        run.player_target_runtime_store = PlayerTargetRuntimeStore(db_path=self.db_path)
        run.player_position_store = PlayerPositionStore(db_path=self.db_path)
        run.player_operation_store = PlayerOperationStore(db_path=self.db_path)
        run.system_message_store = SystemMessageStore(db_path=self.db_path)
        run.player_inventory_store = PlayerInventoryStore(db_path=self.db_path)
        run.wallet_balance_store = WalletBalanceStore(db_path=self.db_path)
        run.delta_bus = GameStateDeltaBus(db_path=self.db_path)
        run.session_generation_store = SessionGenerationStore(self.db_path)
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
        run.session_generation_store = self.original_session_generation_store
        self.tmpdir.cleanup()

    def _create_wallet_user(self, balance=0):
        return UserStore(
            db_path=self.db_path,
            seed_path=str(Path(self.tmpdir.name) / "missing_users.json"),
        ).save_profile_guarded(
            complete_test_profile(balance=balance),
            expected_revision=0,
            source="test.registration",
            allow_create=True,
        )

    def _authenticate_client(self, client, username="main"):
        lineage = f"lineage-{username}-{id(client)}"
        generation = f"generation-{username}-{id(client)}"
        run.session_generation_store.activate(
            lineage,
            generation,
            username,
            reason="test_seed",
        )
        with client.session_transaction() as sess:
            sess["user"] = username
            sess[run.SESSION_LINEAGE_KEY] = lineage
            sess[run.SESSION_GENERATION_KEY] = generation
        return {run.SESSION_GENERATION_HEADER: generation}

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

    def test_gonna_win_accepts_late_snapshot_from_same_rebuilt_conflict_pillar(self):
        previous = {
            "target_id": "territory:pillar:revision-4",
            "target_mode": "territory_contest",
            "stable_conflict_id": "conflict-stable-9",
            "foreign_area_id": 41,
            "expected_owner_username": "owner",
            "contest_owner_username": "owner",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Conflict Pillar",
            "security": {"trace_guard": True},
            "actions_allowed": {"trace": False},
        }
        rebuilt = {
            **previous,
            "target_id": "territory:pillar:revision-5",
            "ownership_version": 5,
        }
        profile = complete_test_profile()
        profile["apps"] = [{
            "id": "trace_tool",
            "name": "Trace Tool",
            "map_actions": ["trace"],
            "operation_types": [],
            "requires_off": [],
            "interferes_with": [],
            "levels": [{"options": []}],
        }]
        profile["aimed_target"] = rebuilt
        run.player_target_runtime_store.upsert_aimed("main", rebuilt)
        client = run.app.test_client()
        headers = self._authenticate_client(client)

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "create_missing_operations_for_app_target", return_value=[]):
            response = client.post(
                "/gonna-win",
                headers=headers,
                json={
                    "app_id": "trace_tool",
                    "operation_only": True,
                    "expected_target": previous,
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertNotEqual("target_selection_changed", payload.get("reason"))
        stored = run.player_target_runtime_store.get_active_target("main")
        self.assertEqual("territory:pillar:revision-5", stored["target_id"])
        self.assertTrue(stored["actions_allowed"]["trace"])

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

    def test_player_operation_store_unchanged_sync_does_not_bump_version_or_event(self):
        operation = {
            "operation_id": "op_unchanged_sync",
            "target_id": "target-sync",
            "map_action_id": "trace",
            "operation_type": "generic_trace",
            "source_app_id": "trace_1",
            "status": "timeout",
        }
        run.player_operation_store.upsert_operations(
            "main", [operation], event_type="operation.started"
        )
        stored_before = run.player_operation_store.list_operations("main")[0]
        conn = sqlite3.connect(self.db_path)
        try:
            events_before = conn.execute("SELECT COUNT(*) FROM operation_events").fetchone()[0]
        finally:
            conn.close()

        accepted = run.player_operation_store.upsert_operations(
            "main",
            [operation],
            event_type="operation.runtime_sync",
            source="refresh_and_persist_operations",
        )

        stored_after = run.player_operation_store.list_operations("main")[0]
        conn = sqlite3.connect(self.db_path)
        try:
            events_after = conn.execute("SELECT COUNT(*) FROM operation_events").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual([item["operation_id"] for item in accepted], ["op_unchanged_sync"])
        self.assertEqual(stored_after["_runtime_version"], stored_before["_runtime_version"])
        self.assertEqual(events_after, events_before)

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
        headers = self._authenticate_client(client)

        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            first = client.get("/system-messages", headers=headers)
            second = client.get("/system-messages", headers=headers)

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
        self._create_wallet_user(0)
        first = run.wallet_balance_store.credit(
            "main", 100, transaction_key="tx-1", reason="test"
        )
        second = run.wallet_balance_store.credit(
            "main", 100, transaction_key="tx-1", reason="test"
        )

        self.assertTrue(first["applied"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["balance"], 100)
        self.assertEqual(second["balance"], 100)
        self.assertEqual(run.wallet_balance_store.get_balance("main"), 100)
        with self.assertRaises(WalletIdempotencyConflict):
            run.wallet_balance_store.credit(
                "main", 999, transaction_key="tx-1", reason="conflict"
            )

    def test_record_wallet_balance_delta_publishes_committed_canonical_balance(self):
        self._create_wallet_user(0)
        run.wallet_balance_store.credit(
            "main", 321, transaction_key="wallet:test:credit", reason="test"
        )
        run.record_wallet_balance_delta(
            "main", 999999, reason="test", dedupe_key="wallet:test:main"
        )

        self.assertEqual(run.wallet_balance_store.get_balance("main"), 321)
        changes = run.delta_bus.get_changes_since("main", 0)["changes"]
        self.assertEqual(1, len(changes))
        self.assertEqual(321, changes[0]["payload"]["balance"])

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
        headers = self._authenticate_client(client)

        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=AssertionError("summary should not refresh full profile")):
            response = client.get("/api/operations?summary=1", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["source"], "player_operations")
        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["active_operations"][0]["operation_id"], "op_summary")

    def test_map_operation_cancel_uses_canonical_store_and_is_idempotent(self):
        operation = {
            "operation_id": "op_map_cancel",
            "target_id": "target-cancel",
            "map_action_id": "trace",
            "operation_type": "vehicle_tracking",
            "source_app_id": "trace_1",
            "status": "running",
            "operation_risk_meter": {
                "current_heat": 55,
                "active_contribution": 55,
                "warning_crossed": True,
                "warning_dedupe_key": "operation-risk:op_map_cancel:warning",
            },
        }
        run.player_operation_store.upsert_operations(
            "main", [operation], event_type="operation.started"
        )
        client = run.app.test_client()
        headers = self._authenticate_client(client)

        with patch.object(
            run,
            "sync_session_profile",
            side_effect=AssertionError("canonical cancel must not hydrate a full profile"),
        ), patch.object(run.incident_initializer, "sync_operations", return_value={"actions": []}), \
                patch.object(run, "sync_response_warnings", return_value=[]):
            first = client.post(
                "/api/operations/cancel",
                headers=headers,
                json={"operation_id": "op_map_cancel"},
            )
            replay = client.post(
                "/api/operations/cancel",
                headers=headers,
                json={"operation_id": "op_map_cancel"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        first_payload = first.get_json()
        replay_payload = replay.get_json()
        self.assertEqual(first_payload["result"], "cancelled")
        self.assertFalse(first_payload["idempotent"])
        self.assertEqual(replay_payload["result"], "already_cancelled")
        self.assertTrue(replay_payload["idempotent"])
        self.assertEqual(first_payload["receipt"], replay_payload["receipt"])
        self.assertEqual(first_payload["active_operations"], [])
        stored = run.player_operation_store.list_operations("main")[0]
        self.assertEqual(stored["status"], "cancelled")
        self.assertFalse(stored["cleanup_state"]["marker_visible"])
        self.assertEqual(stored["operation_risk_meter"]["active_contribution"], 0)
        self.assertTrue(stored["operation_risk_meter"]["warning_cancelled"])
        conn = sqlite3.connect(self.db_path)
        try:
            cancel_events = conn.execute(
                "SELECT COUNT(*) FROM operation_events WHERE event_type = 'operation.cancelled'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(cancel_events, 1)

    def test_map_operation_cancel_missing_identity_is_domain_conflict_not_404(self):
        client = run.app.test_client()
        headers = self._authenticate_client(client)

        response = client.post(
            "/api/operations/cancel",
            headers=headers,
            json={"operation_id": "missing-operation"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["reason_code"], "operation_not_available")

    def test_stale_profile_sync_cannot_resurrect_cancelled_operation(self):
        operation = {
            "operation_id": "op_no_resurrection",
            "target_id": "target-1",
            "map_action_id": "trace",
            "operation_type": "generic_trace",
            "source_app_id": "trace_1",
            "status": "running",
        }
        run.player_operation_store.upsert_operations("main", [operation])
        run.player_operation_store.cancel_operation("main", "op_no_resurrection")

        accepted = run.player_operation_store.upsert_operations(
            "main", [operation], event_type="operation.profile_mirror_sync"
        )

        self.assertEqual(accepted[0]["status"], "cancelled")
        stored = run.player_operation_store.list_operations("main")[0]
        self.assertEqual(stored["status"], "cancelled")

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
            store.save_profile_guarded(
                complete_test_profile(),
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )
            created = store.get_profile_with_revision("main")
            store.patch_profile_guarded(
                "main",
                {"launch_queue": ["Snfx"]},
                expected_revision=created["profile_revision"],
                source="test.launch_queue.append",
            )

            stale = store.get_profile_with_revision("main")
            self.assertEqual(store.consume_launch_queue("main"), ["Snfx"])

            with self.assertRaises(ProfileWriteConflict):
                store.patch_profile_guarded(
                    "main",
                    {"system_messages": [{"id": 1, "title": "Late writer"}]},
                    expected_revision=stale["profile_revision"],
                    source="test.stale_writer",
                )

            self.assertEqual(store.get_profile("main")["launch_queue"], [])

    def test_user_store_consume_launch_queue_is_one_shot(self):
        with TemporaryDirectory() as tmpdir:
            store = UserStore(
                db_path=str(Path(tmpdir) / "game.sqlite3"),
                seed_path=str(Path(tmpdir) / "missing_users.json"),
            )
            store.save_profile_guarded(
                complete_test_profile(
                    launch_queue=["Snfx", "Snfx", "Trace Compass"]
                ),
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )

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
            patch.object(
                run,
                "load_profile_write_record",
                return_value={"profile": complete_test_profile(), "profile_revision": 7},
            ), \
            patch.object(
                run.user_store, "patch_profile_guarded", autospec=True
            ) as guarded_patch, \
            patch.object(run, "safe_ghostnetwork_on_target_aimed") as ghost_hook:
            result = run.set_player_aimed_target(
                "main",
                profile,
                {"lat": 52.3082685, "lng": 21.0628002, "label": "POI-7C133E"},
                update_fields={"launch_queue": ["V-MAP"]},
            )

        self.assertEqual(result, {})
        self.assertEqual(profile["aimed_target"], {})
        guarded_patch.assert_called_once()
        self.assertEqual(guarded_patch.call_args.args[0], "main")
        saved_fields = guarded_patch.call_args.args[1]
        self.assertEqual(saved_fields["aimed_target"], {})
        self.assertEqual(saved_fields["launch_queue"], ["V-MAP"])
        self.assertEqual(guarded_patch.call_args.kwargs["expected_revision"], 7)
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
