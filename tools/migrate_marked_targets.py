#!/usr/bin/env python
"""One-way migration of legacy ``profile_json.targets`` to its runtime store.

The default command is read-only.  ``--apply`` bootstraps the schema and writes
one idempotency receipt per account, so the large profile JSON is never parsed
again by the marked-target hot path.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "game.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument("--username", default="", help="Limit migration to one account")
    parser.add_argument("--apply", action="store_true", help="Write canonical rows and receipts")
    return parser.parse_args()


def read_status(db_path, username=""):
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        state_available = "player_marked_target_state" in tables
        sql = "SELECT username, profile_revision FROM users"
        params = ()
        if username:
            sql += " WHERE username = ?"
            params = (username,)
        sql += " ORDER BY username"
        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            seeded = False
            if state_available:
                seeded = conn.execute(
                    "SELECT 1 FROM player_marked_target_state WHERE username = ?",
                    (row["username"],),
                ).fetchone() is not None
            result.append({
                "username": row["username"],
                "profile_revision": int(row["profile_revision"] or 0),
                "seeded": seeded,
            })
        return result
    finally:
        conn.close()


def main():
    args = parse_args()
    before = read_status(args.db, args.username)
    if args.username and not before:
        print(json.dumps({"ok": False, "error": "user_not_found", "username": args.username}))
        return 2

    report = {
        "ok": True,
        "mode": "apply" if args.apply else "dry-run",
        "db": str(Path(args.db).resolve()),
        "users": len(before),
        "already_seeded": sum(1 for item in before if item["seeded"]),
        "pending": sum(1 for item in before if not item["seeded"]),
        "results": [],
    }
    if not args.apply:
        report["results"] = before
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from database import PlayerMarkedTargetStore  # noqa: E402

    store = PlayerMarkedTargetStore(str(Path(args.db).resolve()))
    failures = 0
    for item in before:
        try:
            result = store.ensure_seeded(item["username"])
            report["results"].append({"username": item["username"], **result})
        except Exception as exc:  # keep migrating independent accounts
            failures += 1
            report["results"].append({
                "username": item["username"],
                "error": exc.__class__.__name__,
                "message": str(exc),
            })
    report["ok"] = failures == 0
    report["failures"] = failures
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
