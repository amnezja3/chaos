import os
import tempfile
import unittest

import run
from response_network.consequence_executor import ConsequenceExecutor
from response_network.consequence_policy import CONSEQUENCE_MODE_FULL, ConsequencePolicy


def temp_db_path(prefix):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


def make_profile(extra_app=True):
    apps = [
        {
            "id": "sniffer",
            "name": "Sniffer",
            "operation_types": ["persistent_sniffer"],
            "category": "tool",
        }
    ]
    if extra_app:
        apps.append({
            "id": "xmapper",
            "name": "xmapper",
            "operation_types": ["scan"],
            "category": "tool",
        })
    return {
        "username": "main",
        "wallet": 1000,
        "hackcoins": 1000,
        "apps": apps,
        "files": {
            "tools": [
                {"id": "sniffer", "app_id": "sniffer", "name": "Sniffer", "size": 12},
                {"id": "xmapper", "app_id": "xmapper", "name": "xmapper", "size": 8},
            ]
        },
        "operations": [
            {
                "operation_id": "op-detect",
                "status": "running",
                "source_app_id": "sniffer",
                "source_app_name": "Sniffer",
                "resource_buffer": {
                    "files": [{"name": "packet.log", "size": 3}],
                    "items": [{"name": "trace"}],
                    "data_file_created": True,
                },
                "operation_risk_meter": {
                    "incident_id": "incident-detect",
                    "active_contribution": 92,
                    "current_heat": 92,
                    "position": {"lat": 52.23, "lng": 21.01},
                },
            }
        ],
    }


def make_decision():
    return {
        "status": "accepted",
        "mode": "full",
        "validation_key": "detection:full:key",
        "actor_id": "main",
        "operation_id": "op-detect",
        "incident_id": "incident-detect",
        "capsule_id": "capsule-detect",
        "candidate_id": "candidate-detect",
    }


class ConsequenceFullResponseTest(unittest.TestCase):
    def setUp(self):
        self.path = temp_db_path("chaos_consequence_full_")
        self.policy = ConsequencePolicy(
            mode=CONSEQUENCE_MODE_FULL,
            feature_flags={
                "tool_confiscation": True,
                "hc_confiscation": True,
                "judgment": True,
                "radio_hooks": True,
                "cyberner_hooks": True,
                "incident_history": True,
            },
        )
        self.executor = ConsequenceExecutor(db_path=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def execute(self, profile, intent):
        return self.executor.execute(
            intent,
            profile,
            cancel_operation=lambda profile_arg, operation_id: run.cancel_profile_operation(
                profile_arg,
                operation_id,
                cancelled_by="response_network",
            ),
            refresh_operations=lambda profile_arg: profile_arg.get("operations", []),
        )

    def test_full_response_cancels_operation_confiscates_and_records_hooks_once(self):
        profile = make_profile()
        intent = self.policy.prepare_intent(make_decision())

        first = self.execute(profile, intent)
        second = self.execute(profile, intent)

        self.assertEqual(first["status"], "executed")
        self.assertTrue(first["consequence_executed"])
        self.assertTrue(first["penalty_executed"])
        self.assertTrue(first["confiscated_tools"])
        self.assertTrue(first["confiscated_hc"])
        self.assertTrue(first["judgment"])
        self.assertTrue(first["cyberner_hook"])
        self.assertTrue(first["radio_hook"])
        self.assertTrue(first["incident_history_recorded"])
        self.assertEqual(profile["operations"][0]["status"], "cancelled")
        self.assertTrue(profile["operations"][0]["reward_blocked"])
        self.assertEqual(profile["operations"][0]["resource_buffer"]["files"], [])
        self.assertEqual([app["id"] for app in profile["apps"]], ["xmapper"])
        self.assertEqual([tool["id"] for tool in profile["files"]["tools"]], ["xmapper"])
        self.assertLess(profile["hackcoins"], 1000)
        self.assertEqual(profile["wallet"], profile["hackcoins"])
        self.assertEqual(profile["judgment"]["status"], "active")
        response_messages = [
            item for item in profile["system_messages"]
            if isinstance(item, dict) and item.get("source") == "response_network"
        ]
        self.assertEqual(len(response_messages), 1)
        self.assertEqual(len(profile["radio_events"]), 1)
        self.assertEqual(len(profile["incident_history"]), 1)
        self.assertTrue(second["duplicate"])
        response_messages = [
            item for item in profile["system_messages"]
            if isinstance(item, dict) and item.get("source") == "response_network"
        ]
        self.assertEqual(len(response_messages), 1)
        self.assertEqual(len(profile["radio_events"]), 1)
        self.assertEqual(len(profile["incident_history"]), 1)

    def test_softlock_protection_keeps_last_operation_tool(self):
        profile = make_profile(extra_app=False)
        intent = self.policy.prepare_intent(make_decision())

        result = self.execute(profile, intent)

        self.assertEqual(result["status"], "executed")
        self.assertFalse(result["confiscated_tools"])
        self.assertEqual(result["confiscated_tool"]["reason"], "softlock_protection")
        self.assertEqual(profile["apps"][0]["id"], "sniffer")
        self.assertTrue(result["confiscated_hc"])
        self.assertTrue(result["judgment"])

    def test_feature_switches_can_disable_individual_penalties(self):
        profile = make_profile()
        self.policy.set_feature_enabled("tool_confiscation", False)
        self.policy.set_feature_enabled("hc_confiscation", False)
        self.policy.set_feature_enabled("judgment", False)
        intent = self.policy.prepare_intent(make_decision())

        result = self.execute(profile, intent)

        self.assertEqual(result["status"], "executed")
        self.assertFalse(result["penalty_executed"])
        self.assertFalse(result["confiscated_tools"])
        self.assertFalse(result["confiscated_hc"])
        self.assertFalse(result["judgment"])
        self.assertEqual(profile["apps"][0]["id"], "sniffer")
        self.assertEqual(profile["hackcoins"], 1000)
        self.assertNotIn("judgment", profile)


if __name__ == "__main__":
    unittest.main()
