import os
import tempfile
import unittest
from unittest.mock import patch

import run
from response_network.detection_candidate_store import DetectionCandidateStore
from response_network.detection_validator import DetectionValidator
from response_network.incident_store import IncidentStore
from response_network.npc_capsule_factory import NPCCapsuleFactory, position_at
from response_network.npc_capsule_store import NPCCapsuleStore


def temp_db_path(prefix):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return path


class FakeTerritoryReader:
    def __init__(self, own=False):
        self.own = own

    def for_point(self, lat, lng, actor_username=None, include_inactive=False):
        return {
            "inside_any_territory": self.own,
            "inside_own_territory": self.own,
            "inside_foreign_territory": False,
            "owner_ids": [actor_username] if self.own and actor_username else [],
        }


def make_operation(operation_id, incident_id, position, status="running"):
    return {
        "operation_id": operation_id,
        "status": status,
        "operation_risk_meter": {
            "incident_id": incident_id,
            "active_contribution": 80 if status == "running" else 0,
            "position": position,
        },
    }


class DetectionFeedbackShadowTest(unittest.TestCase):
    def setUp(self):
        self.paths = [
            temp_db_path("chaos_detection_incident_"),
            temp_db_path("chaos_detection_capsule_"),
            temp_db_path("chaos_detection_candidate_"),
        ]
        self.incident_store = IncidentStore(db_path=self.paths[0])
        self.capsule_store = NPCCapsuleStore(db_path=self.paths[1])
        self.candidate_store = DetectionCandidateStore(db_path=self.paths[2])
        self.reader = FakeTerritoryReader()
        self.validator = DetectionValidator(
            self.incident_store,
            self.capsule_store,
            self.reader,
            self.candidate_store,
        )

    def tearDown(self):
        for path in self.paths:
            if os.path.exists(path):
                os.remove(path)

    def _seed_active_scene(self):
        incident = self.incident_store.upsert({
            "incident_id": "incident_detection",
            "status": "active",
            "level": 2,
            "heat": 90,
            "center": {"lat": 52.23, "lng": 21.01},
            "search_radius_m": 180,
            "operation_ids": ["op-detect"],
            "expires_at": "2026-07-14T10:30:00+00:00",
            "seed": "incident-detection-seed",
        }, now="2026-07-14T10:00:00+00:00")
        capsule = NPCCapsuleFactory().build_for_incident(
            incident,
            now="2026-07-14T10:00:00+00:00",
        )[0]
        self.capsule_store.upsert(capsule, now="2026-07-14T10:00:00+00:00")
        detected_at = "2026-07-14T10:01:00+00:00"
        npc_position = position_at(capsule, detected_at)
        actor_position = {"lat": npc_position["lat"], "lng": npc_position["lng"]}
        profile = {
            "username": "main",
            "operations": [make_operation("op-detect", incident["incident_id"], actor_position)],
        }
        candidate = {
            "candidate_id": "candidate-valid",
            "incident_id": incident["incident_id"],
            "capsule_id": capsule["capsule_id"],
            "npc_id": capsule["npc_id"],
            "actor_id": "main",
            "operation_id": "op-detect",
            "tracking_token": capsule["tracking_tokens"][0],
            "detected_at": detected_at,
            "npc_position": npc_position,
            "actor_position": actor_position,
            "behavior_version": capsule["behavior_version"],
            "trajectory_seed": capsule["trajectory_seed"],
            "trajectory_phase_deg": capsule["trajectory_phase_deg"],
            "mode": "shadow",
        }
        return incident, capsule, profile, candidate

    def test_valid_candidate_is_shadow_only_and_audited(self):
        incident, capsule, profile, candidate = self._seed_active_scene()

        decision = self.validator.validate(
            candidate,
            profile_loader=lambda username, **kwargs: profile,
        )

        self.assertEqual(decision["status"], "shadow_only")
        self.assertEqual(decision["reason"], "valid_shadow_detection")
        self.assertTrue(decision["shadow_only"])
        recent = self.candidate_store.recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["status"], "shadow_only")

    def test_duplicate_candidate_is_deduplicated(self):
        incident, capsule, profile, candidate = self._seed_active_scene()

        first = self.validator.validate(candidate, profile_loader=lambda username, **kwargs: profile)
        second = self.validator.validate({**candidate, "candidate_id": "candidate-valid-copy"}, profile_loader=lambda username, **kwargs: profile)

        self.assertEqual(first["status"], "shadow_only")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(len(self.candidate_store.recent()), 1)

    def test_invalid_token_is_rejected_without_consequence(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        candidate["candidate_id"] = "candidate-invalid-token"
        candidate["tracking_token"] = "wrong-token"

        decision = self.validator.validate(candidate, profile_loader=lambda username, **kwargs: profile)

        self.assertEqual(decision["status"], "rejected")
        self.assertEqual(decision["reason"], "invalid_tracking_token")

    def test_cancelled_operation_expires_later_feedback(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        profile["operations"] = [make_operation("op-detect", incident["incident_id"], candidate["actor_position"], status="cancelled")]
        candidate["candidate_id"] = "candidate-cancelled"

        decision = self.validator.validate(candidate, profile_loader=lambda username, **kwargs: profile)

        self.assertEqual(decision["status"], "expired")
        self.assertEqual(decision["reason"], "operation_not_active")

    def test_passive_offline_player_on_own_territory_is_protected(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        self.validator.territory_context_reader = FakeTerritoryReader(own=True)
        candidate["candidate_id"] = "candidate-protected"
        candidate["operation_id"] = None
        profile = {"username": "main", "operations": []}

        decision = self.validator.validate(candidate, profile_loader=lambda username, **kwargs: profile)

        self.assertEqual(decision["status"], "rejected")
        self.assertEqual(decision["reason"], "passive_or_offline_territory_protected")

    def test_detection_candidate_endpoint_returns_full_response_decision(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "observer"

        with patch.object(run, "detection_validator", self.validator), \
                patch.object(run, "load_profile_readonly", return_value=profile), \
                patch.object(run.user_store, "get_profile", return_value=None):
            response = client.post("/api/map/incidents/detection-candidates", json=candidate)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["mode"], "full")
        self.assertEqual(payload["status"], "accepted")
        self.assertFalse(payload["penalty_executed"])
        self.assertFalse(payload["consequence_executed"])
        self.assertEqual(payload["consequence"]["status"], "rejected")
        self.assertEqual(payload["consequence"]["reason"], "profile_not_found")

    def test_visible_safe_candidate_is_accepted_without_penalty(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        candidate["candidate_id"] = "candidate-visible-safe"
        candidate["mode"] = "visible_safe"

        decision = self.validator.validate(
            candidate,
            profile_loader=lambda username, **kwargs: profile,
        )

        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["mode"], "visible_safe")
        self.assertFalse(decision["shadow_only"])
        self.assertTrue(decision["visible_safe"])
        self.assertFalse(decision["penalty_executed"])

    def test_limited_enforcement_candidate_is_accepted_without_penalty_at_validation(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        candidate["candidate_id"] = "candidate-limited-enforcement"
        candidate["mode"] = "limited_enforcement"

        decision = self.validator.validate(
            candidate,
            profile_loader=lambda username, **kwargs: profile,
        )

        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["mode"], "limited_enforcement")
        self.assertFalse(decision["shadow_only"])
        self.assertTrue(decision["limited_enforcement"])
        self.assertFalse(decision["penalty_executed"])
        self.assertFalse(decision["consequence_executed"])

    def test_full_candidate_is_accepted_without_penalty_at_validation(self):
        incident, capsule, profile, candidate = self._seed_active_scene()
        candidate["candidate_id"] = "candidate-full-response"
        candidate["mode"] = "full"

        decision = self.validator.validate(
            candidate,
            profile_loader=lambda username, **kwargs: profile,
        )

        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["mode"], "full")
        self.assertFalse(decision["shadow_only"])
        self.assertTrue(decision["full"])
        self.assertFalse(decision["penalty_executed"])
        self.assertFalse(decision["consequence_executed"])


if __name__ == "__main__":
    unittest.main()
