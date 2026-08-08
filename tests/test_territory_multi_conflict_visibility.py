import unittest
from unittest.mock import patch

import run


GEOMETRY = [[
    {"lat": 52.0, "lng": 21.0},
    {"lat": 52.0, "lng": 21.02},
    {"lat": 52.02, "lng": 21.02},
    {"lat": 52.02, "lng": 21.0},
]]


def context(owner_clan="blue", friends=None):
    return {
        "viewer_username": "a",
        "profile_cache": {
            "a": {"username": "a", "clan": "red"},
            "b": {"username": "b", "clan": owner_clan},
            "d": {"username": "d", "clan": "green"},
        },
        "accepted_contacts": set(friends or []),
        "member_conflict_ids": {"a-d", "b-d"},
        "engagements": [{
            "engagement_id": "eng-1",
            "status": "active",
            "member_conflict_ids": ["a-d", "b-d"],
            "participant_usernames": ["a", "b", "d"],
            "geometry": GEOMETRY,
        }],
    }


class TerritoryMultiConflictVisibilityTests(unittest.TestCase):
    def test_friend_different_clan_is_social_friend_and_hostile_target(self):
        result = run.project_territory_target_visibility(
            "a", "b", {"lat": 52.01, "lng": 21.01},
            source_conflict_ids=["b-d"], context=context(friends={"b"}),
        )
        self.assertEqual(result["viewer_relation"], "friend")
        self.assertEqual(result["combat_relation"], "hostile")
        self.assertTrue(result["visible"])
        self.assertTrue(result["attackable"])
        self.assertEqual(result["engagement_ids"], ["eng-1"])

    def test_same_clan_is_never_visible_or_attackable_as_target(self):
        result = run.project_territory_target_visibility(
            "a", "b", {"lat": 52.01, "lng": 21.01},
            source_conflict_ids=["b-d"], context=context(owner_clan="red"),
        )
        self.assertEqual(result["viewer_relation"], "crew")
        self.assertEqual(result["combat_relation"], "protected_same_clan")
        self.assertFalse(result["visible"])
        self.assertFalse(result["attackable"])
        self.assertEqual(result["visibility_reason"], "same_clan_immunity")

    def test_clanless_players_are_separate_hostile_groups(self):
        clanless = context(owner_clan="")
        clanless["profile_cache"]["a"]["clan"] = ""
        result = run.project_territory_target_visibility(
            "a", "b", {"lat": 52.01, "lng": 21.01},
            source_conflict_ids=["b-d"], context=clanless,
        )
        self.assertEqual(result["combat_relation"], "hostile")
        self.assertTrue(result["attackable"])

    def test_target_outside_shared_geometry_stays_hidden(self):
        result = run.project_territory_target_visibility(
            "a", "b", {"lat": 52.5, "lng": 21.5},
            source_conflict_ids=["b-d"], context=context(),
        )
        self.assertFalse(result["visible"])
        self.assertEqual(result["visibility_reason"], "outside_viewer_conflict_and_engagement")

    def test_direct_bilateral_conflict_remains_visible_without_engagement(self):
        result = run.project_territory_target_visibility(
            "a", "d", {"lat": 52.5, "lng": 21.5},
            source_conflict_ids=["a-d"], direct_conflict=True, context=context(),
        )
        self.assertTrue(result["visible"])
        self.assertEqual(result["visibility_reason"], "direct_conflict")

    def test_actor_projection_uses_same_social_and_combat_relations(self):
        result = run.project_territory_actor_visibility(
            "a", "b", {"lat": 52.01, "lng": 21.01}, context=context(friends={"b"})
        )
        self.assertEqual(result["viewer_relation"], "friend")
        self.assertEqual(result["combat_relation"], "hostile")
        self.assertTrue(result["visible"])
        self.assertTrue(result["attackable"])
        actor = run.build_player_actor(
            "a", {"username": "b", "lat": 52.01, "lng": 21.01},
            relation="friend", context=result,
        )
        self.assertEqual(actor["viewer_relation"], "friend")
        self.assertTrue(actor["actions"]["mark_target"]["enabled"])

    def test_indirect_engagement_target_enters_shared_contested_projection(self):
        direct = {
            "conflict_id": "a-d", "participants": ["a", "d"],
            "status": "active", "targets": [], "intersections": GEOMETRY,
        }
        indirect = {
            "conflict_id": "b-d", "participants": ["b", "d"],
            "status": "active", "intersections": GEOMETRY,
            "targets": [{
                "target_id": "pillar-b", "owner_username": "b",
                "status": "contested", "captured": False,
                "target": {"target_id": "pillar-b", "label": "B pillar",
                           "lat": 52.01, "lng": 21.01},
            }],
        }
        profiles = {
            "a": {"username": "a", "clan": "red"},
            "b": {"username": "b", "clan": "blue", "nick": "Bee"},
            "d": {"username": "d", "clan": "green"},
        }
        engagement = {
            "engagement_id": "eng-1", "status": "active",
            "member_conflict_ids": ["a-d", "b-d"],
            "participant_usernames": ["a", "b", "d"], "geometry": GEOMETRY,
        }
        with patch.object(run.territory_conflict_engagement_store, "list_active", return_value=[engagement]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[direct, indirect]), \
                patch.object(run.mail_store, "list_accepted_contacts", return_value=[{"name": "b"}]), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})):
            targets = run.contested_targets_from_active_conflicts("a", conflicts=[direct], areas=[])

        self.assertEqual(len(targets), 1)
        target = targets[0]
        self.assertEqual(target["conflict_id"], "b-d")
        self.assertEqual(target["viewer_relation"], "friend")
        self.assertEqual(target["combat_relation"], "hostile")
        self.assertEqual(target["engagement_ids"], ["eng-1"])

        picker = run.build_victim_picker_candidate(
            {"username": "a"}, target, "territory_conflict",
            origin={"lat": 52.01, "lng": 21.01}, action_range=100,
        )
        serialized = run.serialize_victim_picker_candidate(picker)
        self.assertEqual(serialized["viewer_relation"], "friend")
        self.assertEqual(serialized["engagement_ids"], ["eng-1"])
        self.assertTrue(serialized["attackable"])

        threat = run.territory_control_area_threat(
            "a", {"id": 1, "vertices": GEOMETRY[0]}, [direct], visible_targets=targets
        )
        self.assertEqual(threat["visible_targets"][0]["target_id"], "pillar-b")


if __name__ == "__main__":
    unittest.main()
