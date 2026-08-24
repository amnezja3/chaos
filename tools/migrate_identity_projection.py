"""Operator tool for the Sprint 130.12 identity projection migration."""

import argparse
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from database import (
    DB_PATH,
    IDENTITY_PROJECTION_VERSION,
    PROFILE_INTEGRITY_VALID,
    UserIdentityProjectionStore,
    _identity_projection_payload,
    _validate_persisted_profile_row,
)


@contextmanager
def readonly_connection(db_path):
    resolved = Path(db_path).resolve()
    conn = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def table_exists(conn):
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' "
        "AND name = 'user_identity_projection'"
    ).fetchone())


def status(db_path):
    with readonly_connection(db_path) as conn:
        users = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        if not table_exists(conn):
            return {
                "status": "not_applied", "users": users, "projected": 0,
                "missing": users, "stale": 0,
            }
        projected = int(conn.execute(
            "SELECT COUNT(*) FROM user_identity_projection"
        ).fetchone()[0])
        stale = int(conn.execute(
            """
            SELECT COUNT(*)
            FROM user_identity_projection AS p
            LEFT JOIN users AS u ON u.username = p.username
            WHERE u.username IS NULL
               OR p.source_profile_revision != u.profile_revision
               OR p.source_profile_checksum != u.profile_checksum
               OR u.profile_integrity_status != ?
               OR p.projection_version != ?
            """,
            (PROFILE_INTEGRITY_VALID, IDENTITY_PROJECTION_VERSION),
        ).fetchone()[0])
        missing = int(conn.execute(
            """
            SELECT COUNT(*)
            FROM users AS u
            LEFT JOIN user_identity_projection AS p ON p.username = u.username
            WHERE p.username IS NULL
            """
        ).fetchone()[0])
    return {
        "status": "ready" if missing == 0 and stale == 0 else "incomplete",
        "users": users, "projected": projected,
        "missing": missing, "stale": stale,
    }


def dry_run(db_path, *, after_username="", limit=100):
    limit = max(1, min(500, int(limit)))
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT username, profile_json, profile_revision,
                   profile_checksum, profile_integrity_status
            FROM users
            WHERE username > ?
            ORDER BY username
            LIMIT ?
            """,
            (str(after_username or ""), limit),
        ).fetchall()
    valid = []
    skipped = []
    for row in rows:
        profile, errors = _validate_persisted_profile_row(row, row["username"])
        if errors:
            skipped.append({"username": row["username"], "errors": list(errors)})
            continue
        projection = _identity_projection_payload(profile)
        valid.append({
            "username": projection["username"],
            "source_profile_revision": int(row["profile_revision"] or 0),
            "projection_version": IDENTITY_PROJECTION_VERSION,
        })
    return {
        "mode": "dry-run", "after_username": str(after_username or ""),
        "next_cursor": rows[-1]["username"] if rows else "",
        "scanned": len(rows), "valid": valid, "skipped": skipped,
        "done": len(rows) < limit, "database_mutated": False,
    }


def apply(db_path, *, after_username="", batch_size=100, single_page=False):
    store = UserIdentityProjectionStore(db_path)
    cursor = after_username
    totals = {"scanned": 0, "projected": 0, "skipped": 0}
    while True:
        result = store.backfill_page(after_username=cursor, limit=batch_size)
        totals["scanned"] += result["scanned"]
        totals["projected"] += len(result["projected"])
        totals["skipped"] += len(result["skipped"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        cursor = result["next_cursor"]
        if single_page or result["done"]:
            break
    return {"totals": totals, "next_cursor": cursor}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("status", "audit", "dry-run", "apply", "verify")
    )
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--after-username", default="")
    parser.add_argument("--single-page", action="store_true")
    parser.add_argument("--confirm-apply", action="store_true")
    args = parser.parse_args()

    if args.command in {"status", "audit", "verify"}:
        result = status(args.db)
        result["command"] = args.command
        print(json.dumps(result, sort_keys=True))
        if args.command == "verify" and result["status"] != "ready":
            raise SystemExit(2)
        return
    if args.command == "dry-run":
        print(json.dumps(dry_run(
            args.db, after_username=args.after_username, limit=args.batch_size
        ), ensure_ascii=False, sort_keys=True))
        return
    if not args.confirm_apply:
        parser.error("apply requires --confirm-apply")
    result = apply(
        args.db,
        after_username=args.after_username,
        batch_size=args.batch_size,
        single_page=args.single_page,
    )
    print(json.dumps(result, sort_keys=True))
    if result["totals"]["skipped"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
