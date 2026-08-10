import hashlib


MIGRATION_ID = "005"
NAME = "Cyberner shared channel stores and legacy WORLD history"


def _table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _ensure_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cyberner_world_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            sender_username TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            client_message_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cyberner_world_messages_created
        ON cyberner_world_messages(id, created_at)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cyberner_world_messages_client
        ON cyberner_world_messages(sender_username, client_message_id)
        WHERE client_message_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cyberner_clan_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            clan_key TEXT NOT NULL,
            sender_username TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            client_message_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cyberner_clan_messages_channel
        ON cyberner_clan_messages(clan_key, id)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cyberner_clan_messages_client
        ON cyberner_clan_messages(clan_key, sender_username, client_message_id)
        WHERE client_message_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cyberner_channel_cursors (
            username TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            channel_key TEXT NOT NULL,
            last_read_message_id INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(username, channel_type, channel_key)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cyberner_channel_cursors_channel
        ON cyberner_channel_cursors(channel_type, channel_key, username)
        """
    )
    if _table_exists(conn, "chat_messages"):
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        if "read_at" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN read_at TEXT")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
            ON chat_messages(owner_username, scope, peer_name, id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_unread
            ON chat_messages(owner_username, scope, peer_name, read_at)
            """
        )


def _signature(row):
    return (
        str(row["sender"] or ""),
        str(row["subject"] or ""),
        str(row["body"] or ""),
        str(row["created_at"] or ""),
    )


def _legacy_candidates(conn):
    if not _table_exists(conn, "chat_messages"):
        return []
    rows = conn.execute(
        """
        SELECT id, owner_username, sender, subject, body, created_at
        FROM chat_messages
        WHERE scope = 'group' AND peer_name = 'global'
        ORDER BY id ASC
        """
    ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(_signature(row), []).append(row)

    candidates = []
    for copies in grouped.values():
        authoritative = [
            row for row in copies
            if str(row["owner_username"] or "") == str(row["sender"] or "")
        ]
        candidates.extend(authoritative or copies[:1])
    candidates.sort(key=lambda row: int(row["id"]))
    return candidates


def _legacy_message_id(row):
    material = "|".join((
        str(row["id"]),
        str(row["sender"] or ""),
        str(row["created_at"] or ""),
        str(row["body"] or ""),
    ))
    digest = hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()[:24]
    return f"cyberner_world_legacy_{digest}"


def migrate(conn, apply=False):
    candidates = _legacy_candidates(conn)
    existing_ids = set()
    if _table_exists(conn, "cyberner_world_messages"):
        existing_ids = {
            row[0]
            for row in conn.execute(
                "SELECT message_id FROM cyberner_world_messages WHERE message_id LIKE 'cyberner_world_legacy_%'"
            ).fetchall()
        }

    planned = [row for row in candidates if _legacy_message_id(row) not in existing_ids]
    if apply:
        _ensure_schema(conn)
        for row in planned:
            legacy_id = int(row["id"])
            conn.execute(
                """
                INSERT OR IGNORE INTO cyberner_world_messages
                    (message_id, sender_username, subject, body, created_at, client_message_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    _legacy_message_id(row),
                    str(row["sender"] or row["owner_username"] or "legacy"),
                    str(row["subject"] or ""),
                    str(row["body"] or ""),
                    str(row["created_at"] or ""),
                    f"legacy:{legacy_id}",
                ),
            )

    return {
        "legacy_rows_scanned": sum(
            1 for _ in conn.execute(
                "SELECT 1 FROM chat_messages WHERE scope = 'group' AND peer_name = 'global'"
            )
        ) if _table_exists(conn, "chat_messages") else 0,
        "canonical_messages": len(candidates),
        "already_migrated": len(candidates) - len(planned),
        "messages_to_insert": len(planned),
        "write_mode": bool(apply),
    }
