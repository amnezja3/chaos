import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from database import UserStore
import run


class HackActionIdempotencyTests(unittest.TestCase):
    def setUp(self):
        with run._hack_action_idempotency_lock:
            run._hack_action_idempotency_cache.clear()

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


if __name__ == "__main__":
    unittest.main()
