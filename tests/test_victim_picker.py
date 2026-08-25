import unittest
from unittest.mock import patch

import run


class VictimPickerTest(unittest.TestCase):
    def test_zero_zero_target_is_fail_closed_without_focus_or_teleport(self):
        profile = {
            "username": "main",
            "curently_possition": {"lat": 52.263, "lng": 21.0},
            "aimed_target": {},
        }
        candidate = run.build_victim_picker_candidate(
            profile,
            {"target_id": "map:0.0:0.0:target", "lat": 0.0, "lng": 0.0,
             "label": "target"},
            "profile.targets",
            origin=run.victim_picker_position(profile),
            action_range=1000,
        )

        self.assertFalse(candidate["can_aim"])
        self.assertEqual("missing_position", candidate["disabled_reason"])
        self.assertIsNone(candidate["focus"])
        self.assertEqual({}, candidate["teleport"])

    def test_active_zero_zero_profile_projection_is_not_a_candidate(self):
        profile = {
            "username": "main",
            "curently_possition": {"lat": 52.263, "lng": 21.0},
            "aimed_target": {
                "target_id": "map:0.0:0.0:target", "lat": 0.0, "lng": 0.0,
                "label": "target",
            },
        }

        self.assertIsNone(run.build_victim_picker_active_target_candidate(
            profile, run.victim_picker_position(profile), 1000
        ))

    def test_active_map_target_is_included_in_candidates(self):
        profile = {
            "username": "main",
            "curently_possition": {"lat": 52.263, "lng": 21.0},
            "apps": [{"id": "victimPicker", "type": "pro-system-tool"}],
            "targets": [],
            "aimed_target": {
                "target_id": "POI-175F8C",
                "label": "POI-175F8C",
                "name": "POI-175F8C",
                "icon": "\U0001F4CD",
                "lat": 52.565,
                "lng": 19.7,
                "source_type": "scan",
                "target_mode": "standard",
                "security": {"scan_ports": True},
                "actions_allowed": {"scan_ports": True},
            },
        }

        with patch.object(run.mail_store, "list_accepted_contacts", return_value=[]), \
                patch.object(run.territory_store, "list_recent_area_intruders", return_value=[]), \
                patch.object(run.vulnerability_store, "list_active", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[]):
            candidates = run.build_victim_picker_candidates("main", profile)

        by_id = {candidate["target_id"]: candidate for candidate in candidates}
        self.assertIn("POI-175F8C", by_id)
        active = by_id["POI-175F8C"]
        self.assertTrue(active["is_aimed"])
        self.assertTrue(active["is_active_target"])
        self.assertEqual(active["candidate_source"], "profile.targets")
        self.assertEqual(active["source_type"], "scan")


if __name__ == "__main__":
    unittest.main()
