import unittest

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


if __name__ == "__main__":
    unittest.main()
