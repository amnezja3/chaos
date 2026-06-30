#!/usr/bin/env python3
"""Compare/sync approved static JSON seed files into SQLite json_resources.

This tool never touches users, profiles, profile.apps, operations or player
runtime data. It only reads static JSON files and optionally updates
json_resources rows.
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_RESOURCE_KEYS = {
    "app_config",
    "user_template",
    "user_security",
    "terminal_command",
    "messages",
    "friends",
    "fractions",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stored_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_json_resources_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS json_resources (
            key TEXT PRIMARY KEY,
            source_path TEXT,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def selected_keys(static_dir, key):
    if key:
        if key not in ALLOWED_RESOURCE_KEYS:
            raise SystemExit(
                f"Key '{key}' is not an approved static JSON resource. "
                f"Allowed: {', '.join(sorted(ALLOWED_RESOURCE_KEYS))}"
            )
        return [key]

    return sorted(ALLOWED_RESOURCE_KEYS)


def read_db_resources(conn):
    return {
        row[0]: {
            "source_path": row[1] or "",
            "value_json": row[2],
            "updated_at": row[3] or "",
        }
        for row in conn.execute(
            "SELECT key, source_path, value_json, updated_at FROM json_resources"
        ).fetchall()
    }


def compare_key(key, static_dir, db_resources):
    path = Path(static_dir) / f"{key}.json"
    db_row = db_resources.get(key)
    if not path.exists():
        return {
            "key": key,
            "status": "missing_static",
            "path": str(path),
            "db_updated_at": (db_row or {}).get("updated_at", ""),
        }

    static_value = load_json(path)
    static_canonical = canonical_json(static_value)

    if not db_row:
        return {
            "key": key,
            "status": "missing_in_db",
            "path": str(path),
            "static_value": static_value,
            "static_json": stored_json(static_value),
            "db_updated_at": "",
        }

    try:
        db_value = json.loads(db_row["value_json"])
    except json.JSONDecodeError:
        db_value = None

    status = "unchanged" if canonical_json(db_value) == static_canonical else "changed"
    return {
        "key": key,
        "status": status,
        "path": str(path),
        "static_value": static_value,
        "static_json": stored_json(static_value),
        "db_updated_at": db_row.get("updated_at", ""),
        "db_json": db_row.get("value_json", ""),
    }


def backup_db_value(backup_dir, item):
    if not item.get("db_json"):
        return ""

    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{item['key']}.json"
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(item["db_json"])
    return str(target)


def apply_item(conn, item, backup_dir):
    if item["status"] not in {"missing_in_db", "changed"}:
        return ""

    backup_path = backup_db_value(backup_dir, item)
    conn.execute(
        """
        INSERT INTO json_resources (key, source_path, value_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            source_path = excluded.source_path,
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        (item["key"], item["path"], item["static_json"], utc_now()),
    )
    return backup_path


def format_report_line(item):
    suffix = ""
    if item.get("db_updated_at"):
        suffix = f" db_updated_at={item['db_updated_at']}"
    return f"{item['status']:>13}  {item['key']:<18} {item.get('path', '')}{suffix}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/game.sqlite3", help="SQLite database path.")
    parser.add_argument("--static-dir", default="static", help="Directory with seed JSON files.")
    parser.add_argument("--key", help="Sync only one approved resource key.")
    parser.add_argument("--apply", action="store_true", help="Write changes to json_resources.")
    args = parser.parse_args()

    db_path = Path(args.db)
    static_dir = Path(args.static_dir)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    if not static_dir.is_dir():
        raise SystemExit(f"Static directory not found: {static_dir}")

    keys = selected_keys(static_dir, args.key)
    backup_dir = Path("data/backups") / f"json_resources_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with sqlite3.connect(db_path) as conn:
        ensure_json_resources_table(conn)
        db_resources = read_db_resources(conn)
        items = [compare_key(key, static_dir, db_resources) for key in keys]

        for db_key in sorted(set(db_resources) - ALLOWED_RESOURCE_KEYS):
            items.append({
                "key": db_key,
                "status": "extra_in_db",
                "path": "",
                "db_updated_at": db_resources[db_key].get("updated_at", ""),
            })

        backups = {}
        if args.apply:
            for item in items:
                backup_path = apply_item(conn, item, backup_dir)
                if backup_path:
                    backups[item["key"]] = backup_path
            conn.commit()

    print("Static JSON resource sync")
    print(f"mode: {'apply' if args.apply else 'dry-run'}")
    print(f"db: {db_path}")
    print(f"static_dir: {static_dir}")
    if args.key:
        print(f"key: {args.key}")
    print("")

    counts = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        print(format_report_line(item))
        if item["key"] in backups:
            print(f"{'backup':>13}  {item['key']:<18} {backups[item['key']]}")

    print("")
    print("summary:", ", ".join(f"{key}={counts[key]}" for key in sorted(counts)) or "none")
    if not args.apply:
        print("No writes performed. Use --apply to update SQLite json_resources.")


if __name__ == "__main__":
    main()
