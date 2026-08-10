import importlib.util
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from database import (
    CybernerChannelCursorStore,
    CybernerClanStore,
    CybernerWorldStore,
    MailStore,
)


def load_channel_migration():
    path = Path("scripts/db_migrations/005_cyberner_channel_stores.py")
    spec = importlib.util.spec_from_file_location("cyberner_channel_migration_005", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cutover_migration():
    path = Path("scripts/db_migrations/006_cyberner_channel_cutover.py")
    spec = importlib.util.spec_from_file_location("cyberner_channel_migration_006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CybernerChannelStoreTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        self.world = CybernerWorldStore(self.db_path)
        self.clan = CybernerClanStore(self.db_path)
        self.cursors = CybernerChannelCursorStore(self.db_path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{self.db_path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def test_additive_schema_and_legacy_indexes_exist(self):
        with sqlite3.connect(self.db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            indexes = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
            }

        self.assertIn("cyberner_world_messages", tables)
        self.assertIn("cyberner_clan_messages", tables)
        self.assertIn("cyberner_channel_cursors", tables)
        self.assertIn("idx_cyberner_world_messages_client", indexes)
        self.assertIn("idx_cyberner_clan_messages_channel", indexes)
        self.assertIn("idx_chat_messages_thread", indexes)
        self.assertIn("idx_chat_messages_unread", indexes)

    def test_world_idempotency_is_scoped_to_sender(self):
        first, first_created = self.world.add_message(
            "alice", "pierwsza", client_message_id="client-1"
        )
        duplicate, duplicate_created = self.world.add_message(
            "alice", "zmieniona", client_message_id="client-1"
        )
        other_sender, other_created = self.world.add_message(
            "bob", "od boba", client_message_id="client-1"
        )

        self.assertTrue(first_created)
        self.assertFalse(duplicate_created)
        self.assertTrue(other_created)
        self.assertEqual(duplicate["message_id"], first["message_id"])
        self.assertEqual(duplicate["body"], "pierwsza")
        self.assertNotEqual(other_sender["message_id"], first["message_id"])
        self.assertEqual(len(self.world.list_messages()), 2)

    def test_world_pagination_is_stable_and_chronological(self):
        messages = [
            self.world.add_message("alice", f"m-{index}", client_message_id=f"c-{index}")[0]
            for index in range(1, 5)
        ]

        latest = self.world.list_messages(limit=2)
        after = self.world.list_messages(after_id=messages[0]["id"], limit=2)
        before = self.world.list_messages(before_id=messages[3]["id"], limit=2)

        self.assertEqual([item["body"] for item in latest], ["m-3", "m-4"])
        self.assertEqual([item["body"] for item in after], ["m-2", "m-3"])
        self.assertEqual([item["body"] for item in before], ["m-2", "m-3"])
        self.assertEqual(self.world.latest_message_id(), messages[-1]["id"])
        self.assertEqual(self.world.count_after(messages[1]["id"]), 2)

    def test_clan_streams_and_idempotency_are_isolated(self):
        red, red_created = self.clan.add_message(
            "red", "alice", "red message", client_message_id="same-client"
        )
        blue, blue_created = self.clan.add_message(
            "blue", "alice", "blue message", client_message_id="same-client"
        )
        duplicate, duplicate_created = self.clan.add_message(
            "red", "alice", "ignored", client_message_id="same-client"
        )

        self.assertTrue(red_created)
        self.assertTrue(blue_created)
        self.assertFalse(duplicate_created)
        self.assertEqual(duplicate["message_id"], red["message_id"])
        self.assertEqual([item["body"] for item in self.clan.list_messages("red")], ["red message"])
        self.assertEqual([item["body"] for item in self.clan.list_messages("blue")], ["blue message"])
        self.assertNotEqual(red["message_id"], blue["message_id"])

    def test_channel_cursor_is_per_user_channel_and_monotonic(self):
        self.assertEqual(
            self.cursors.get("alice", "world", "global")["last_read_message_id"],
            0,
        )
        advanced = self.cursors.advance("alice", "world", "global", 12)
        stale = self.cursors.advance("alice", "world", "global", 4)
        clan = self.cursors.advance("alice", "clan", "red", 7)
        other_user = self.cursors.advance("bob", "world", "global", 3)

        self.assertEqual(advanced["last_read_message_id"], 12)
        self.assertEqual(stale["last_read_message_id"], 12)
        self.assertEqual(clan["last_read_message_id"], 7)
        self.assertEqual(other_user["last_read_message_id"], 3)

    def test_concurrent_world_writes_keep_unique_messages_and_idempotent_retry(self):
        def write(index):
            client_id = "shared-retry" if index < 8 else f"unique-{index}"
            sender = "alice" if index < 8 else f"player-{index % 6}"
            return CybernerWorldStore(self.db_path).add_message(
                sender, f"body-{index}", client_message_id=client_id
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write, range(24)))

        messages = self.world.list_messages(limit=100)
        shared = [item for item in messages if item.get("client_message_id") == "shared-retry"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(len(messages), 17)
        self.assertEqual(sum(1 for _, created in results if created), 17)


class CybernerLegacyWorldMigrationTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        MailStore(self.db_path)
        self.migration = load_channel_migration()

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{self.db_path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def seed_legacy_world(self):
        rows = [
            ("alice", "alice", "hello", "2026-08-10T10:00:00"),
            ("bob", "alice", "hello", "2026-08-10T10:00:00"),
            ("alice", "alice", "hello", "2026-08-10T10:00:00"),
            ("bob", "system", "alert", "2026-08-10T10:01:00"),
            ("carol", "system", "alert", "2026-08-10T10:01:00"),
        ]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, 'group', 'global', ?, '', ?, ?, NULL)
                """,
                rows,
            )

    def test_migration_deduplicates_fanout_and_is_repeatable(self):
        self.seed_legacy_world()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            dry_run = self.migration.migrate(conn, apply=False)
            count_after_dry_run = conn.execute(
                "SELECT COUNT(*) FROM cyberner_world_messages"
            ).fetchone()[0]
            applied = self.migration.migrate(conn, apply=True)
            repeated = self.migration.migrate(conn, apply=True)
            migrated = conn.execute(
                "SELECT sender_username, body FROM cyberner_world_messages ORDER BY id"
            ).fetchall()

        self.assertEqual(dry_run["legacy_rows_scanned"], 5)
        self.assertEqual(dry_run["canonical_messages"], 3)
        self.assertEqual(dry_run["messages_to_insert"], 3)
        self.assertEqual(count_after_dry_run, 0)
        self.assertEqual(applied["messages_to_insert"], 3)
        self.assertEqual(repeated["messages_to_insert"], 0)
        self.assertEqual(
            [(row["sender_username"], row["body"]) for row in migrated],
            [("alice", "hello"), ("alice", "hello"), ("system", "alert")],
        )


class CybernerCutoverMigrationTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        MailStore(self.db_path)
        self.migration_005 = load_channel_migration()
        self.migration_006 = load_cutover_migration()

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{self.db_path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def test_clan_fanout_is_deduplicated_and_cursors_start_at_cutover_baseline(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.executemany(
                """
                INSERT INTO users (username, password, salt, profile_json, created_at, updated_at)
                VALUES (?, '', '', ?, 'now', 'now')
                """,
                [
                    ("alice", '{"username":"alice","clan":"red"}'),
                    ("carol", '{"username":"carol","clan":"red"}'),
                    ("bob", '{"username":"bob","clan":"blue"}'),
                ],
            )
            conn.executemany(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, 'channel', 'clan:red', 'alice', '', 'red signal', '2026-08-10T10:00:00', NULL)
                """,
                [("alice",), ("carol",)],
            )
            self.migration_005.migrate(conn, apply=True)
            result = self.migration_006.migrate(conn, apply=True)
            repeated = self.migration_006.migrate(conn, apply=True)
            clan_count = conn.execute("SELECT COUNT(*) FROM cyberner_clan_messages").fetchone()[0]
            cursors = conn.execute(
                "SELECT username, channel_type, channel_key, last_read_message_id "
                "FROM cyberner_channel_cursors ORDER BY username, channel_type"
            ).fetchall()

        self.assertEqual(result["canonical_clan_messages"], 1)
        self.assertEqual(result["clan_messages_to_insert"], 1)
        self.assertEqual(repeated["clan_messages_to_insert"], 0)
        self.assertEqual(clan_count, 1)
        self.assertIn(("alice", "clan", "red", 1), [tuple(row) for row in cursors])
        self.assertIn(("carol", "clan", "red", 1), [tuple(row) for row in cursors])
        self.assertIn(("bob", "clan", "blue", 0), [tuple(row) for row in cursors])


if __name__ == "__main__":
    unittest.main()
