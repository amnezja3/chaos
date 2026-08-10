import json
from datetime import datetime, timezone


MIGRATION_ID = "007"
NAME = "Remove Cyberner prototype chat messages"


PROTOTYPE_MESSAGES = (
    ("System", "Aktualizacja patcha 1.03"),
    ("H4x0rKira", "Widziałeś to?"),
    ("AI Central", "Zadanie moralne #7"),
)


def _table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


def _count_legacy(conn):
    if not _table_exists(conn, "chat_messages"):
        return 0
    return sum(
        conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE sender=? AND subject=?",
            item,
        ).fetchone()[0]
        for item in PROTOTYPE_MESSAGES
    )


def _count_shared(conn):
    if not _table_exists(conn, "cyberner_world_messages"):
        return 0
    return sum(
        conn.execute(
            "SELECT COUNT(*) FROM cyberner_world_messages "
            "WHERE sender_username=? AND subject=?",
            item,
        ).fetchone()[0]
        for item in PROTOTYPE_MESSAGES
    )


def migrate(conn, apply=False):
    legacy_rows = _count_legacy(conn)
    shared_rows = _count_shared(conn)
    if apply:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if _table_exists(conn, "chat_messages"):
            for sender, subject in PROTOTYPE_MESSAGES:
                conn.execute(
                    "DELETE FROM chat_messages WHERE sender=? AND subject=?",
                    (sender, subject),
                )
        if _table_exists(conn, "cyberner_world_messages"):
            for sender, subject in PROTOTYPE_MESSAGES:
                conn.execute(
                    "DELETE FROM cyberner_world_messages "
                    "WHERE sender_username=? AND subject=?",
                    (sender, subject),
                )
        if _table_exists(conn, "json_resources"):
            conn.execute(
                """
                INSERT INTO json_resources (key, source_path, value_json, updated_at)
                VALUES ('messages', 'static/messages.json', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (json.dumps([], ensure_ascii=False), now),
            )
        if _table_exists(conn, "kv_store"):
            conn.execute(
                """
                INSERT INTO kv_store (key, value_json, updated_at)
                VALUES ('messages', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (json.dumps([], ensure_ascii=False), now),
            )
    return {
        "legacy_rows_to_delete": int(legacy_rows),
        "shared_rows_to_delete": int(shared_rows),
        "prototype_definitions_to_clear": len(PROTOTYPE_MESSAGES),
        "write_mode": bool(apply),
    }
