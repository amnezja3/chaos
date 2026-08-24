import unittest
from unittest.mock import patch

import run


class FakeUserStore:
    def __init__(self):
        self.profiles = {
            "owner": {"username": "owner", "clan": "virex"},
            "ally": {"username": "ally", "clan": "virex"},
            "outsider": {"username": "outsider", "clan": "sentinel_order"},
        }

    def list_profiles(self):
        return list(self.profiles.values())

    def list_usernames(self):
        return list(self.profiles)

    def list_profile_entries(self):
        return list(self.profiles.items())

    def get_profile(self, username):
        return self.profiles.get(username)

    def get_identity(self, username):
        profile = self.profiles.get(username)
        return {"username": username, **profile} if profile else None

    def get_identities(self, usernames, max_items=500):
        if len(list(usernames)) > max_items:
            raise ValueError("identity batch exceeds bound")
        return [
            {"username": username, **self.profiles[username]}
            for username in usernames if username in self.profiles
        ]

    def list_recipient_ids(self, scope, *, clan_code=None, owner_ids=None, limit=500):
        if scope in {"owner", "owners"}:
            return [item for item in (owner_ids or []) if item in self.profiles][:limit]
        usernames = list(self.profiles)
        if scope == "clan":
            usernames = [
                username for username in usernames
                if self.profiles[username].get("clan") == clan_code
            ]
        return usernames[:limit]


class GhostNetworkDeltaAudienceBridgeTest(unittest.TestCase):
    def setUp(self):
        self.store = FakeUserStore()
        self.store_patch = patch.object(run, "user_store", self.store)
        self.identity_patch = patch.object(run, "identity_projection_store", self.store)
        self.store_patch.start()
        self.identity_patch.start()

    def tearDown(self):
        self.store_patch.stop()
        self.identity_patch.stop()

    @staticmethod
    def event(scope, event_type="ghost.part_contained", **values):
        payload = {
            "event_id": values.pop("event_id", f"event-{scope}"),
            "cycle_id": "ghostnetwork_0001",
            **values.pop("payload", {}),
        }
        return {
            "event_id": payload["event_id"],
            "event_type": event_type,
            "cycle_id": "ghostnetwork_0001",
            "audience_scope": scope,
            "payload": payload,
            **values,
        }

    def test_owner_clan_and_public_resolve_only_intended_profiles(self):
        owner = self.event("owner", payload={"territory_owner_id": "owner"})
        clan = self.event("clan", event_type="ghost.machine_progress_changed", audience_clan="virex")
        public = self.event("public", event_type="ghost.signal_sent")

        self.assertEqual(
            [name for name, _ in run.ghostnetwork_event_recipient_profiles(owner)],
            ["owner"],
        )
        self.assertEqual(
            {name for name, _ in run.ghostnetwork_event_recipient_profiles(clan)},
            {"owner", "ally"},
        )
        self.assertEqual(
            {name for name, _ in run.ghostnetwork_event_recipient_profiles(public)},
            {"owner", "ally", "outsider"},
        )

    def test_database_profiles_do_not_need_to_duplicate_username_column(self):
        self.store.profiles = {
            "owner": {"clan": "virex"},
            "ally": {"clan": "virex"},
        }

        owner = self.event("owner", payload={"territory_owner_id": "owner"})
        public = self.event("public", event_type="ghost.signal_sent")

        self.assertEqual(
            [name for name, _ in run.ghostnetwork_event_recipient_profiles(owner)],
            ["owner"],
        )
        self.assertEqual(
            {name for name, _ in run.ghostnetwork_event_recipient_profiles(public)},
            {"owner", "ally"},
        )

    def test_internal_and_system_never_reach_client_even_with_player_id(self):
        for scope in ("internal", "system"):
            event = self.event(scope, player_id="owner", payload={"player_id": "owner"})
            self.assertEqual(run.ghostnetwork_event_recipient_profiles(event), [])
            self.assertFalse(run.ghostnetwork_profile_is_event_recipient(
                event,
                "owner",
                self.store.get_profile("owner"),
            ))

    def test_publication_is_deduplicated_per_resolved_recipient(self):
        event = self.event(
            "clan",
            event_type="ghost.machine_progress_changed",
            audience_clan="virex",
            payload={"active_parts": 2, "previous_active_parts": 1},
        )
        with patch.object(
            run.GhostNetworkDeltaPublisher,
            "publish_event",
            return_value=[{"username": "owner"}, {"username": "ally"}],
        ) as publish:
            published = run.publish_ghostnetwork_event_delta(event)

        publish.assert_called_once()
        viewers = publish.call_args.args[1]
        self.assertEqual([viewer["username"] for viewer in viewers], ["owner", "ally"])
        self.assertEqual(len(published), 2)

    def test_required_live_event_types_resolve_to_expected_audiences(self):
        events = [
            self.event("owner", "ghost.part_contained", payload={"territory_owner_id": "owner"}),
            self.event("public", "ghost.part_contested"),
            self.event("clan", "ghost.machine_progress_changed", audience_clan="virex"),
            self.event("public", "ghost.signal_sent"),
        ]
        expected = {
            "ghost.part_contained": {"owner"},
            "ghost.part_contested": {"owner", "ally", "outsider"},
            "ghost.machine_progress_changed": {"owner", "ally"},
            "ghost.signal_sent": {"owner", "ally", "outsider"},
        }

        for event in events:
            recipients = {
                username for username, _ in run.ghostnetwork_event_recipient_profiles(event)
            }
            self.assertEqual(recipients, expected[event["event_type"]])


if __name__ == "__main__":
    unittest.main()
