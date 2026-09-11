"""Operator schema migration for 140.2; default read-only, no historical backfill."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def migrate(path, apply=False):
    uri = Path(path).resolve().as_uri()
    with closing(sqlite3.connect(uri + "?mode=ro", uri=True)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(ghost_signal_shows)")}
        if not columns:
            raise ValueError("ghost_signal_shows missing")
    missing = "scene_snapshot_json" not in columns
    changed = False
    if apply:
        with closing(sqlite3.connect(uri + "?mode=rw", uri=True)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ghost_signal_shows)")}
            if "scene_snapshot_json" not in columns:
                conn.execute("ALTER TABLE ghost_signal_shows ADD COLUMN scene_snapshot_json TEXT NOT NULL DEFAULT '{}'")
                changed = True
            conn.commit()
    return {"ok": True, "apply": apply, "schema_change": missing,
            "changed": changed, "historical_backfill": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(migrate(args.db, args.apply)))
