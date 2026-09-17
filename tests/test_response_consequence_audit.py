"""Audit reproductions, not acceptance of production readiness (2026-09-16).

These observations must be replaced by safety regressions in sprint 142.
"""
import unittest
import test_detection_feedback_shadow as fixtures


class ResponseConsequenceAuditTest(unittest.TestCase):
    setUp = fixtures.DetectionFeedbackShadowTest.setUp
    tearDown = fixtures.DetectionFeedbackShadowTest.tearDown
    _seed_active_scene = fixtures.DetectionFeedbackShadowTest._seed_active_scene

    def test_audit_client_position_overrides_operation_position(self):
        _, _, profile, candidate = self._seed_active_scene()
        profile['operations'][0]['operation_risk_meter']['position'] = {'lat': 0, 'lng': 0}
        candidate['mode'] = 'full'
        result = self.validator.validate(candidate, profile_loader=lambda *a, **kw: profile)
        self.assertEqual(result['status'], 'accepted')

    def test_audit_historical_detection_time_is_not_bounded_by_server_now(self):
        _, _, profile, candidate = self._seed_active_scene()
        candidate['mode'] = 'full'
        result = self.validator.validate(candidate, profile_loader=lambda *a, **kw: profile,
                                         now='2026-09-16T12:00:00+00:00')
        self.assertEqual(result['status'], 'accepted')

    def test_audit_bystander_without_operation_cannot_reach_policy(self):
        _, _, profile, candidate = self._seed_active_scene()
        profile['operations'] = []
        candidate.update(mode='full', operation_id=None)
        result = self.validator.validate(candidate, profile_loader=lambda *a, **kw: profile)
        self.assertEqual(result['reason'], 'operation_not_active')
