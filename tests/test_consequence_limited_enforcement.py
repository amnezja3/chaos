import os
import tempfile
import unittest

import run
from response_network.consequence_executor import ConsequenceExecutor
from response_network.consequence_policy import ConsequencePolicy


def temp_db_path(prefix):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


def make_profile():
    return {
        "username": "main",
        "wallet": 777,
        "hackcoins": 777,
        "apps": [{"id": "sniffer", "name": "Sniffer"}],
        "operations": [
            {
                "operation_id": "op-detect",
                "status": "running",
                "resource_buffer": {
                    "files": [{"name": "packet.log", "size": 3}],
                    "items": [{"name": "trace"}],
                    "data_file_created": True,
                },
                "operation_risk_meter": {
                    "incident_id": "incident-detect",
                    "active_contribution": 80,
                    "position": {"lat": 52.23, "lng": 21.01},
                },
            },
            {
                "operation_id": "op-other",
                "status": "running",
                "resource_buffer": {
                    "files": [{"name": "other.log", "size": 1}],
                },
                "operation_risk_meter": {
                    "incident_id": "incident-other",
                    "active_contribution": 30,
                    "position": {"lat": 52.24, "lng": 21.02},
                },
            },
        ],
    }


def make_decision():
    return {
        "status": "accepted",
        "mode": "limited_enforcement",
        "validation_key": "detection:key",
        "actor_id": "main",
        "operation_id": "op-detect",
        "incident_id": "incident-detect",
        "capsule_id": "capsule-detect",
        "candidate_id": "candidate-detect",
    }


class ConsequenceLimitedEnforcementTest(unittest.TestCase):
    def setUp(self):
        self.path = temp_db_path("chaos_consequence_")
        self.policy = ConsequencePolicy()
        self.executor = ConsequenceExecutor(db_path=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_policy_prepares_cancel_operation_intent_without_penalty(self):
        intent = self.policy.prepare_intent(make_decision(), now="2026-07-15T10:00:00+00:00")

        self.assertEqual(intent["status"], "prepared")
        self.assertEqual(intent["mode"], "limited_enforcement")
        self.assertEqual(intent["action"], "cancel_operation")
        self.assertEqual(intent["operation_id"], "op-detect")
        self.assertFalse(intent["confiscate_tools"])
        self.assertFalse(intent["confiscate_hc"])
        self.assertFalse(intent["judgment"])
        self.assertTrue(intent["cancel_related_operation_only"])

    def test_executor_cancels_only_related_operation_and_removes_progress_once(self):
        profile = make_profile()
        intent = self.policy.prepare_intent(make_decision())

        def refresh_operations(profile_arg):
            return profile_arg.get("operations", [])

        first = self.executor.execute(
            intent,
            profile,
            cancel_operation=lambda profile_arg, operation_id: run.cancel_profile_operation(
                profile_arg,
                operation_id,
                cancelled_by="response_network",
            ),
            refresh_operations=refresh_operations,
        )
        second = self.executor.execute(
            intent,
            profile,
            cancel_operation=lambda profile_arg, operation_id: run.cancel_profile_operation(
                profile_arg,
                operation_id,
                cancelled_by="response_network",
            ),
            refresh_operations=refresh_operations,
        )

        cancelled = profile["operations"][0]
        untouched = profile["operations"][1]
        self.assertEqual(first["status"], "executed")
        self.assertTrue(first["consequence_executed"])
        self.assertFalse(first["penalty_executed"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["cancelled_by"], "response_network")
        self.assertTrue(cancelled["reward_blocked"])
        self.assertEqual(cancelled["resource_buffer"]["files"], [])
        self.assertEqual(cancelled["resource_buffer"]["items"], [])
        self.assertTrue(cancelled["resource_buffer"]["progress_removed"])
        self.assertEqual(untouched["status"], "running")
        self.assertEqual(untouched["resource_buffer"]["files"][0]["name"], "other.log")
        self.assertEqual(profile["wallet"], 777)
        self.assertEqual(profile["apps"][0]["id"], "sniffer")
        self.assertNotIn("judgment", profile)
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["status"], "executed")

    def test_executor_kill_switch_blocks_prepared_intent_without_cancel(self):
        profile = make_profile()
        intent = self.policy.prepare_intent(make_decision())

        result = self.executor.execute(
            intent,
            profile,
            cancel_operation=lambda profile_arg, operation_id: run.cancel_profile_operation(
                profile_arg,
                operation_id,
                cancelled_by="response_network",
            ),
            refresh_operations=lambda profile_arg: profile_arg.get("operations", []),
            kill_switch_active=lambda: True,
        )

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["reason"], "consequence_kill_switch")
        self.assertFalse(result["consequence_executed"])
        self.assertEqual(profile["operations"][0]["status"], "running")

    def test_executor_supersedes_race_after_player_cancel(self):
        profile = make_profile()
        profile["operations"][0]["status"] = "cancelled"
        intent = self.policy.prepare_intent(make_decision())

        result = self.executor.execute(
            intent,
            profile,
            cancel_operation=lambda profile_arg, operation_id: run.cancel_profile_operation(
                profile_arg,
                operation_id,
                cancelled_by="response_network",
            ),
            refresh_operations=lambda profile_arg: profile_arg.get("operations", []),
        )

        self.assertEqual(result["status"], "superseded")
        self.assertEqual(result["reason"], "already_terminal")
        self.assertFalse(result["consequence_executed"])


if __name__ == "__main__":
    unittest.main()
