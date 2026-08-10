import hashlib
import json
from datetime import datetime, timezone


MIGRATION_ID = "006"
NAME = "Cyberner CLAN history and shared cursor cutover baseline"


def _table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _signature(row):
    return (
        str(row["peer_name"] or ""),
        str(row["sender"] or ""),
        str(row["subject"] or ""),
        str(row["body"] or ""),
        str(row["created_at"] or ""),
    )


def _legacy_clan_candidates(conn):
    if not _table_exists(conn, "chat_messages"):
        return []
    rows = conn.execute(
        """
        SELECT id, owner_username, peer_name, sender, subject, body, created_at
        FROM chat_messages
        WHERE scope = 'channel' AND peer_name LIKE 'clan:%'
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
        candidates.append((authoritative or copies[:1])[0])
    return sorted(candidates, key=lambda row: int(row["id"]))


def _legacy_message_id(row):
    material = "|".join(str(value or "") for value in (
        row["peer_name"], row["id"], row["sender"], row["created_at"], row["body"],
    ))
    digest = hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()[:24]
    return f"cyberner_clan_legacy_{digest}"


def _profile_clan(profile_json):
    try:
        profile = json.loads(profile_json or "{}")
    except (TypeError, ValueError):
        return ""
    clan = profile.get("clan")
    if isinstance(clan, dict):
        clan = clan.get("name") or clan.get("id")
    return str(clan or "").strip()


def migrate(conn, apply=False):
    required = {
        "cyberner_world_messages", "cyberner_clan_messages",
        "cyberner_channel_cursors",
    }
    missing_tables = sorted(name for name in required if not _table_exists(conn, name))
    if missing_tables:
        if not apply:
            # In a full dry-run migration 005 is inspected immediately before
            # this migration, but it intentionally performs no schema writes.
            # Report the dependency instead of making the read-only plan fail.
            return {
                "prerequisite": "005",
                "prerequisite_tables_missing": missing_tables,
                "legacy_clan_rows_scanned": len(conn.execute(
                    "SELECT id FROM chat_messages "
                    "WHERE scope='channel' AND peer_name LIKE 'clan:%'"
                ).fetchall()) if _table_exists(conn, "chat_messages") else 0,
                "canonical_clan_messages": None,
                "clan_messages_to_insert": None,
                "cursor_users": None,
                "cursor_policy": "migrated_history_read",
                "write_mode": False,
                "status": "ready_after_005",
            }
        raise RuntimeError(f"Migration 005 must run first; missing: {', '.join(missing_tables)}")

    candidates = _legacy_clan_candidates(conn)
    existing = {
        row[0] for row in conn.execute(
            "SELECT message_id FROM cyberner_clan_messages "
            "WHERE message_id LIKE 'cyberner_clan_legacy_%'"
        ).fetchall()
    }
    planned = [row for row in candidates if _legacy_message_id(row) not in existing]

    users = []
    if _table_exists(conn, "users"):
        users = conn.execute("SELECT username, profile_json FROM users ORDER BY username").fetchall()
    latest_world = int(conn.execute(
        "SELECT COALESCE(MAX(id), 0) FROM cyberner_world_messages"
    ).fetchone()[0] or 0)
    clan_latest = {
        str(row[0]): int(row[1] or 0)
        for row in conn.execute(
            "SELECT clan_key, COALESCE(MAX(id), 0) FROM cyberner_clan_messages GROUP BY clan_key"
        ).fetchall()
    }

    if apply:
        for row in planned:
            clan_key = str(row["peer_name"] or "").split(":", 1)[-1].strip()
            conn.execute(
                """
                INSERT OR IGNORE INTO cyberner_clan_messages
                    (message_id, clan_key, sender_username, subject, body, created_at, client_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _legacy_message_id(row), clan_key,
                    str(row["sender"] or row["owner_username"] or "legacy"),
                    str(row["subject"] or ""), str(row["body"] or ""),
                    str(row["created_at"] or ""), f"legacy-clan:{int(row['id'])}",
                ),
            )

        # Re-read after inserts: the cutover baseline deliberately treats all
        # migrated history as read. New messages remain independently unread.
        clan_latest = {
            str(row[0]): int(row[1] or 0)
            for row in conn.execute(
                "SELECT clan_key, COALESCE(MAX(id), 0) FROM cyberner_clan_messages GROUP BY clan_key"
            ).fetchall()
        }
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for user in users:
            username = str(user["username"] or "").strip()
            if not username:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO cyberner_channel_cursors
                    (username, channel_type, channel_key, last_read_message_id, updated_at)
                VALUES (?, 'world', 'global', ?, ?)
                """,
                (username, latest_world, now),
            )
            clan_key = _profile_clan(user["profile_json"])
            if clan_key:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cyberner_channel_cursors
                        (username, channel_type, channel_key, last_read_message_id, updated_at)
                    VALUES (?, 'clan', ?, ?, ?)
                    """,
                    (username, clan_key, clan_latest.get(clan_key, 0), now),
                )

    return {
        "legacy_clan_rows_scanned": len(conn.execute(
            "SELECT id FROM chat_messages WHERE scope='channel' AND peer_name LIKE 'clan:%'"
        ).fetchall()) if _table_exists(conn, "chat_messages") else 0,
        "canonical_clan_messages": len(candidates),
        "clan_messages_to_insert": len(planned),
        "cursor_users": len(users),
        "cursor_policy": "migrated_history_read",
        "write_mode": bool(apply),
    }
