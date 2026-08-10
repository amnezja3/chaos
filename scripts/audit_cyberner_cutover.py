#!/usr/bin/env python3
"""Read-only audit of Cyberner shared-channel cutover readiness."""

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path


def load_migration(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def audit(db_path):
    migration_dir = Path(__file__).with_name("db_migrations")
    migration_005 = load_migration(migration_dir / "005_cyberner_channel_stores.py")
    migration_006 = load_migration(migration_dir / "006_cyberner_channel_cutover.py")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        tables = {
            name: table_exists(conn, name)
            for name in (
                "chat_messages", "cyberner_world_messages",
                "cyberner_clan_messages", "cyberner_channel_cursors",
            )
        }
        if not all(tables.values()):
            return {"ok": False, "tables": tables, "error": "shared_schema_incomplete"}

        world_expected_ids = {
            migration_005._legacy_message_id(row)
            for row in migration_005._legacy_candidates(conn)
        }
        clan_expected_ids = {
            migration_006._legacy_message_id(row)
            for row in migration_006._legacy_clan_candidates(conn)
        }
        world_actual_ids = {
            row[0] for row in conn.execute(
                "SELECT message_id FROM cyberner_world_messages "
                "WHERE message_id LIKE 'cyberner_world_legacy_%'"
            ).fetchall()
        }
        clan_actual_ids = {
            row[0] for row in conn.execute(
                "SELECT message_id FROM cyberner_clan_messages "
                "WHERE message_id LIKE 'cyberner_clan_legacy_%'"
            ).fetchall()
        }
        missing_world_messages = sorted(world_expected_ids - world_actual_ids)
        missing_clan_messages = sorted(clan_expected_ids - clan_actual_ids)
        users = conn.execute("SELECT username, profile_json FROM users").fetchall()
        missing_world_cursors = []
        missing_clan_cursors = []
        for user in users:
            username = str(user["username"] or "")
            if not conn.execute(
                "SELECT 1 FROM cyberner_channel_cursors "
                "WHERE username=? AND channel_type='world' AND channel_key='global'",
                (username,),
            ).fetchone():
                missing_world_cursors.append(username)
            clan = migration_006._profile_clan(user["profile_json"])
            if clan and not conn.execute(
                "SELECT 1 FROM cyberner_channel_cursors "
                "WHERE username=? AND channel_type='clan' AND channel_key=?",
                (username, clan),
            ).fetchone():
                missing_clan_cursors.append(username)

    ok = (
        not missing_world_messages
        and not missing_clan_messages
        and not missing_world_cursors
        and not missing_clan_cursors
    )
    return {
        "ok": ok,
        "tables": tables,
        "world": {
            "legacy_canonical": len(world_expected_ids),
            "shared_migrated": len(world_actual_ids),
            "missing_message_ids": missing_world_messages,
        },
        "clan": {
            "legacy_canonical": len(clan_expected_ids),
            "shared_migrated": len(clan_actual_ids),
            "missing_message_ids": missing_clan_messages,
        },
        "cursors": {
            "users": len(users),
            "missing_world": missing_world_cursors,
            "missing_clan": missing_clan_cursors,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/game.sqlite3")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = audit(Path(args.db))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
