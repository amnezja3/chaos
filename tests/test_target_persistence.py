import unittest
from unittest.mock import patch

import run
from run import (
    build_player_actor,
    filter_targets_by_position,
    resolve_player_actor_relation,
    target_position_key,
    targets_share_position,
)


class FakeTerritoryStore:
    def __init__(self, targets):
        self.targets = targets
        self.synced = False

    def list_captured_targets(self, username, stationary=None):
        return list(self.targets)

    def sync_profile_hacked_targets(self, username, profile):
        self.synced = True
        return []


class TargetPersistenceHelpersTest(unittest.TestCase):
    def test_position_key_uses_lng_or_lon(self):
        left = {"lat": 52.1234567, "lng": 21.1234567}
        right = {"lat": 52.12345671, "lon": 21.12345671}

        self.assertEqual(target_position_key(left), target_position_key(right))
        self.assertTrue(targets_share_position(left, right))

    def test_filter_removes_by_position_without_label_match(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [
            {"lat": 52.1, "lng": 21.2, "label": "Punkt kolizyjny: AE Woman"},
            {"lat": 52.2, "lng": 21.3, "label": "Other"},
        ]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=False)

        self.assertEqual(removed, 1)
        self.assertEqual(filtered, [{"lat": 52.2, "lng": 21.3, "label": "Other"}])

    def test_filter_can_require_label_when_needed(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [{"lat": 52.1, "lng": 21.2, "label": "Other label"}]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=True)

        self.assertEqual(removed, 0)
        self.assertEqual(filtered, targets)

    def test_sqlite_captured_targets_replace_stale_profile_hacked(self):
        profile = {
            "hacked": [{"lat": 52.1, "lng": 21.2, "label": "Lost pillar"}],
            "captured_targets_source": "sqlite",
        }
        fake_store = FakeTerritoryStore([])

        with patch.object(run, "territory_store", fake_store):
            changed = run.merge_captured_targets_into_profile("defender", profile)

        self.assertTrue(changed)
        self.assertEqual(profile["hacked"], [])
        self.assertEqual(profile["captured_targets_source"], "sqlite")
        self.assertFalse(fake_store.synced)

    def test_player_actor_relation_prefers_friend_context(self):
        viewer = {"username": "neo", "clan": "VIREX"}
        actor = {"username": "trinity", "clan": "VIREX"}

        relation = resolve_player_actor_relation(viewer, actor, {"is_friend": True})

        self.assertEqual(relation, "friend")

    def test_player_actor_actions_disable_friend_targeting(self):
        actor = build_player_actor(
            "neo",
            {"username": "trinity", "nick": "Trinity", "lat": 52.1, "lng": 21.2},
            relation="friend",
            context={"source": "friend", "sources": ["friend"], "is_friend": True},
        )

        self.assertTrue(actor["actions"]["chat"]["enabled"])
        self.assertFalse(actor["actions"]["add_friend"]["enabled"])
        self.assertFalse(actor["actions"]["mark_target"]["enabled"])
        self.assertTrue(actor["actions"]["transfer_hc"]["enabled"])


if __name__ == "__main__":
    unittest.main()
