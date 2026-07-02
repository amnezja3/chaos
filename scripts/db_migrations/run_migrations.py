#!/usr/bin/env python3
"""Run CHAOS SQLite migrations.

Default mode is dry-run. Use --apply to write changes. Each migration must be
idempotent and expose MIGRATION_ID, NAME and migrate(conn, apply=False).
"""

import argparse
import hashlib
import importlib.util
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema_migrations(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            script_hash TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'applied',
            notes TEXT NOT NULL DEFAULT ''
        )
        """
    )


def script_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def applied_migrations(conn):
    ensure_schema_migrations(conn)
    return {
        row[0]: {
            "name": row[1],
            "script_hash": row[2],
            "status": row[3],
        }
        for row in conn.execute(
            "SELECT id, name, script_hash, status FROM schema_migrations"
        ).fetchall()
    }


def migration_files(migrations_dir):
    return sorted(
        path for path in Path(migrations_dir).glob("*.py")
        if path.name[0:3].isdigit() and path.name != Path(__file__).name
    )


def load_migration(path):
    migrations_dir = str(Path(path).parent.resolve())
    if migrations_dir not in sys.path:
        sys.path.insert(0, migrations_dir)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for attr in ("MIGRATION_ID", "NAME", "migrate"):
        if not hasattr(module, attr):
            raise RuntimeError(f"Migration {path} missing {attr}")
    return module


def record_migration(conn, module, path, notes=""):
    conn.execute(
        """
        INSERT INTO schema_migrations (id, name, applied_at, script_hash, status, notes)
        VALUES (?, ?, ?, ?, 'applied', ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            applied_at = excluded.applied_at,
            script_hash = excluded.script_hash,
            status = excluded.status,
            notes = excluded.notes
        """,
        (
            module.MIGRATION_ID,
            module.NAME,
            utc_now(),
            script_hash(path),
            notes,
        ),
    )


def run(db_path, migrations_dir, apply=False):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_schema_migrations(conn)
        applied = applied_migrations(conn)
        results = []
        for path in migration_files(migrations_dir):
            module = load_migration(path)
            already = module.MIGRATION_ID in applied
            result = {
                "id": module.MIGRATION_ID,
                "name": module.NAME,
                "path": str(path),
                "already_applied": already,
                "status": "skipped" if already else "pending",
                "details": {},
            }
            if not already:
                details = module.migrate(conn, apply=apply)
                result["details"] = details or {}
                result["status"] = "applied" if apply else "dry-run"
                if apply:
                    record_migration(conn, module, path, notes=str(details or {}))
            results.append(result)
        if apply:
            conn.commit()
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/game.sqlite3", help="SQLite database path.")
    parser.add_argument("--migrations-dir", default="scripts/db_migrations")
    parser.add_argument("--apply", action="store_true", help="Write migration changes.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    results = run(db_path, args.migrations_dir, apply=args.apply)
    print(f"CHAOS migration runner mode={'apply' if args.apply else 'dry-run'}")
    for item in results:
        print(f"{item['status']:>8} {item['id']} {item['name']}")
        if item["details"]:
            print(f"         {item['details']}")
    if not args.apply:
        print("No writes performed. Use --apply to update SQLite.")


if __name__ == "__main__":
    main()
