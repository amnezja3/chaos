import unittest
from datetime import datetime, timezone

import run
from response_network.operation_risk_meter import (
    calculate_operation_risk,
    update_operation_risk_meter,
)


def ts(hour, minute=0):
    return datetime(2026, 7, 14, hour, minute, tzinfo=timezone.utc).timestamp()


class OperationRiskMeterTest(unittest.TestCase):
    def _operation(self, **overrides):
        operation = {
            "operation_id": "op-risk-1",
            "operation_type": "persistent_sniffer",
            "owner_username": "neo",
            "target_id": "map:52.1:21.2:test",
            "target": {
                "lat": 52.1,
                "lng": 21.2,
                "label": "Test target",
                "security": {
                    "firewall": True,
                    "camera": True,
                },
            },
            "target_mode": "territory_contest",
            "status": "running",
            "started_at": "2026-07-14T10:00:00+00:00",
            "expires_at": "2026-07-14T11:00:00+00:00",
            "source_app_quality": {
                "creator_power": 90,
                "quality_score": 40,
                "reliability": 30,
            },
        }
        operation.update(overrides)
        return operation

    def test_calculates_observe_meter_from_operation_inputs(self):
        operation = self._operation()

        meter = calculate_operation_risk(operation, now_ts=ts(10, 30))

        self.assertEqual(meter["mode"], "observe")
        self.assertEqual(meter["operation_id"], "op-risk-1")
        self.assertEqual(meter["base_heat"], 20)
        self.assertGreater(meter["time_heat"], 0)
        self.assertGreater(meter["tool_modifier"], 0)
        self.assertGreater(meter["security_modifier"], 0)
        self.assertEqual(meter["conflict_modifier"], 25)
        self.assertGreaterEqual(meter["current_heat"], meter["incident_threshold"])
        self.assertTrue(meter["warning_crossed"])
        self.assertTrue(meter["incident_crossed"])
        self.assertIsNone(meter["warning_issued_at"])
        self.assertIsNone(meter["incident_id"])

    def test_threshold_crossing_is_idempotent_for_same_state(self):
        operation = self._operation()

        changed_first = update_operation_risk_meter(operation, now_ts=ts(10, 30))
        first = dict(operation["operation_risk_meter"])
        changed_second = update_operation_risk_meter(operation, now_ts=ts(10, 30))
        second = dict(operation["operation_risk_meter"])

        self.assertTrue(changed_first)
        self.assertFalse(changed_second)
        self.assertEqual(first["risk_version"], second["risk_version"])
        self.assertEqual(first["warning_dedupe_key"], second["warning_dedupe_key"])
        self.assertEqual(first["incident_dedupe_key"], second["incident_dedupe_key"])
        self.assertEqual(first["warning_crossed_at"], second["warning_crossed_at"])
        self.assertEqual(first["incident_crossed_at"], second["incident_crossed_at"])

    def test_cancelled_operation_zeros_active_contribution_and_cancels_threshold_state(self):
        operation = self._operation()
        update_operation_risk_meter(operation, now_ts=ts(10, 30))
        operation["status"] = "cancelled"

        changed = update_operation_risk_meter(operation, now_ts=ts(10, 35))
        meter = operation["operation_risk_meter"]

        self.assertTrue(changed)
        self.assertTrue(meter["cancelled"])
        self.assertEqual(meter["current_heat"], 0)
        self.assertEqual(meter["active_contribution"], 0)
        self.assertFalse(meter["warning_crossed"])
        self.assertFalse(meter["incident_crossed"])
        self.assertTrue(meter["warning_cancelled"])
        self.assertTrue(meter["incident_cancelled"])

    def test_created_operations_get_risk_meter_without_publishing_incidents(self):
        profile = {"operations": [], "risk_events": [], "system_messages": []}
        app = {
            "id": "snfx",
            "name": "Snfx",
            "operation_types": ["persistent_sniffer"],
            "creator_power": 90,
            "quality_score": 40,
            "reliability": 30,
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Test target",
            "target_mode": "territory_contest",
            "security": {"firewall": True},
        }

        created = run.create_operations_for_app_action(profile, "neo", app, "sniff", target)

        self.assertEqual(len(created), 1)
        meter = created[0]["operation_risk_meter"]
        self.assertEqual(meter["mode"], "observe")
        self.assertEqual(meter["risk_version"], 1)
        self.assertEqual(profile["risk_events"], [])
        self.assertEqual(profile["system_messages"], [])


if __name__ == "__main__":
    unittest.main()
