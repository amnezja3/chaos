import os
import tempfile
import unittest
from unittest.mock import patch

import run
from database import (
    CybernerChannelCursorStore,
    CybernerClanStore,
    CybernerWorldStore,
    GameStateDeltaBus,
    MailStore,
    SystemMessageStore,
    UserStore,
)


class CybernerChannelRoutingTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "cyberner-routing.sqlite3")
        self.user_store = UserStore(db_path=self.db_path, seed_path=os.path.join(self.temp_dir.name, "missing.json"))
        self.mail_store = MailStore(db_path=self.db_path)
        self.world_store = CybernerWorldStore(db_path=self.db_path)
        self.clan_store = CybernerClanStore(db_path=self.db_path)
        self.cursor_store = CybernerChannelCursorStore(db_path=self.db_path)
        self.system_store = SystemMessageStore(db_path=self.db_path)
        self.delta_bus = GameStateDeltaBus(db_path=self.db_path)
        for username, clan in (("alice", "red"), ("bob", "blue"), ("carol", "red")):
            self.user_store.save_profile({
                "username": username,
                "nick": username.title(),
                "clan": clan,
                "friends": [],
            })

        self.stack = patch.multiple(
            run,
            user_store=self.user_store,
            mail_store=self.mail_store,
            cyberner_world_store=self.world_store,
            cyberner_clan_store=self.clan_store,
            cyberner_channel_cursor_store=self.cursor_store,
            system_message_store=self.system_store,
            delta_bus=self.delta_bus,
        )
        self.stack.start()
        self.flags = patch.dict(run.CYBERNER_CHANNEL_STORE_FLAGS, {
            "enabled": True,
            "world": True,
            "clan": True,
            "live_delivery": False,
        }, clear=True)
        self.flags.start()
        run.app.config.update(TESTING=True, SECRET_KEY="cyberner-routing-test")

    def tearDown(self):
        self.flags.stop()
        self.stack.stop()
        self.temp_dir.cleanup()

    def client_for(self, username):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = username
        return client

    def test_world_is_one_atomic_record_and_retry_is_idempotent(self):
        client = self.client_for("alice")
        payload = {
            "scope": "group",
            "peer": "global",
            "body": "hello world",
            "client_message_id": "alice-world-1",
        }
        first = client.post("/api/chats/messages", json=payload)
        replay = client.post("/api/chats/messages", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        first_data = first.get_json()
        replay_data = replay.get_json()
        self.assertEqual(first_data["channel"]["scope"], "world")
        self.assertEqual(first_data["channel"]["channel_key"], "global")
        self.assertFalse(first_data["idempotent_replay"])
        self.assertTrue(replay_data["idempotent_replay"])
        self.assertEqual(first_data["message_id"], replay_data["message_id"])
        self.assertEqual(len(self.world_store.list_messages()), 1)
        self.assertNotIn(
            "hello world",
            [item["body"] for item in self.mail_store.list_messages("alice", "group", "global")],
        )
        self.assertEqual(len(self.system_store.consume_pending("bob")), 1)
        self.assertEqual(len(self.system_store.consume_pending("carol")), 1)

    def test_world_read_advances_only_viewers_cursor(self):
        self.world_store.add_message("alice", "one", client_message_id="one")
        self.world_store.add_message("alice", "two", client_message_id="two")

        response = self.client_for("bob").get("/api/chats/messages?scope=world&peer=global")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["messages"]), 2)
        self.assertEqual(self.cursor_store.get("bob", "world", "global")["last_read_message_id"], 2)
        self.assertEqual(self.cursor_store.get("carol", "world", "global")["last_read_message_id"], 0)

    def test_clan_channel_is_authorized_and_isolated(self):
        alice = self.client_for("alice")
        sent = alice.post("/api/chats/messages", json={
            "scope": "channel",
            "peer": "clan:red",
            "body": "red only",
            "client_message_id": "red-1",
        })
        denied = self.client_for("bob").get(
            "/api/chats/messages?scope=channel&peer=clan:red"
        )
        carol = self.client_for("carol").get(
            "/api/chats/messages?scope=clan&peer=clan:red"
        )

        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.get_json()["channel"]["channel_key"], "clan:red")
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(carol.status_code, 200)
        self.assertEqual([item["body"] for item in carol.get_json()["messages"]], ["red only"])
        self.assertEqual(self.clan_store.list_messages("blue"), [])

    def test_friends_channel_stays_on_local_legacy_fanout(self):
        self.mail_store.add_contact_pair("alice", "carol")
        response = self.client_for("alice").post("/api/chats/messages", json={
            "scope": "channel", "peer": "friends", "body": "friends only",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["channel"]["channel"], "friends")
        self.assertEqual(len(self.mail_store.list_messages("alice", "channel", "friends")), 1)
        self.assertEqual(len(self.mail_store.list_messages("carol", "channel", "friends")), 1)
        self.assertEqual(self.world_store.list_messages(), [])
        self.assertEqual(self.clan_store.list_messages("red"), [])

    def test_notification_failure_does_not_change_committed_success(self):
        client = self.client_for("alice")
        with patch.object(run, "add_cyberner_notification_to_user", side_effect=RuntimeError("offline")):
            response = client.post("/api/chats/messages", json={
                "scope": "world", "peer": "global", "body": "committed",
                "client_message_id": "notify-fails",
            })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual([item["body"] for item in self.world_store.list_messages()], ["committed"])

    def test_disabled_store_flag_preserves_legacy_world_path(self):
        self.mail_store.add_contact_pair("alice", "carol")
        with patch.dict(run.CYBERNER_CHANNEL_STORE_FLAGS, {
            "enabled": False, "world": True, "clan": True, "live_delivery": False,
        }, clear=True):
            response = self.client_for("alice").post("/api/chats/messages", json={
                "scope": "group", "peer": "global", "body": "legacy world",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["recovery"]["store"], "legacy")
        self.assertEqual(self.world_store.list_messages(), [])
        self.assertIn(
            "legacy world",
            [item["body"] for item in self.mail_store.list_messages("carol", "group", "global")],
        )
        self.assertEqual(self.system_store.consume_pending("bob"), [])

    def test_live_delivery_publishes_full_stable_message_to_world_audience(self):
        with patch.dict(run.CYBERNER_CHANNEL_STORE_FLAGS, {
            "enabled": True, "world": True, "clan": True, "live_delivery": True,
        }, clear=True):
            response = self.client_for("alice").post("/api/chats/messages", json={
                "scope": "world", "peer": "global", "body": "live world",
                "client_message_id": "live-world-1",
            })

        self.assertEqual(response.status_code, 200)
        message_id = response.get_json()["message_id"]
        for username in ("alice", "bob", "carol"):
            changes = self.delta_bus.get_changes_since(username, 0, 100)["changes"]
            live = [item for item in changes if item["type"] == "cyberner.message_created"]
            self.assertEqual(len(live), 1)
            self.assertEqual(live[0]["entity_id"], message_id)
            self.assertEqual(live[0]["payload"]["message"]["body"], "live world")
            self.assertEqual(live[0]["payload"]["channel_key"], "global")

    def test_clan_live_delivery_never_reaches_foreign_clan(self):
        with patch.dict(run.CYBERNER_CHANNEL_STORE_FLAGS, {
            "enabled": True, "world": True, "clan": True, "live_delivery": True,
        }, clear=True):
            response = self.client_for("alice").post("/api/chats/messages", json={
                "scope": "clan", "peer": "clan:red", "body": "red live",
                "client_message_id": "red-live-1",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len([item for item in self.delta_bus.get_changes_since("carol", 0, 100)["changes"]
                 if item["type"] == "cyberner.message_created"]),
            1,
        )
        self.assertEqual(
            [item for item in self.delta_bus.get_changes_since("bob", 0, 100)["changes"]
             if item["type"] == "cyberner.message_created"],
            [],
        )

    def test_world_read_failure_does_not_break_bootstrap_or_other_channels(self):
        client = self.client_for("alice")
        with patch.object(self.world_store, "list_messages", side_effect=RuntimeError("world offline")), \
                patch.object(self.world_store, "count_after", side_effect=RuntimeError("world offline")):
            response = client.get("/api/mail/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["group_messages"], [])
        self.assertFalse(payload["channel_states"]["world"]["available"])
        self.assertTrue(payload["channel_states"]["friends"]["available"])
        self.assertTrue(payload["channel_states"]["clan"]["available"])


if __name__ == "__main__":
    unittest.main()
