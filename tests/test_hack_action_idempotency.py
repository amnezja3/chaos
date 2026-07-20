import unittest
from unittest.mock import patch

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

    def test_normalize_profile_position_update_writes_legacy_and_canonical_fields(self):
        result = run.normalize_profile_position_update({"lat": "52.1", "lon": "21.2"})

        self.assertEqual(result["curently_possition"], {"lat": 52.1, "lng": 21.2})
        self.assertEqual(result["current_position"], {"lat": 52.1, "lng": 21.2})
        self.assertIsNot(result["curently_possition"], result["current_position"])


if __name__ == "__main__":
    unittest.main()
