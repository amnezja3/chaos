"""Read-only by default. Add TTL columns or remove expired filesystem sessions offline."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from persistent_session_schema import ensure_persistence_schema
from tools.ghost_content_155_migrate import integrity, snapshot


def migrate(path, apply=False):
    path = Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + ('?mode=rw' if apply else '?mode=ro'), uri=True)) as conn:
        conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        integrity(conn)
        if not apply:
            with closing(sqlite3.connect(':memory:')) as preview:
                sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='session_generation_lineages'").fetchone()
                if not sql:
                    raise ValueError('session_lineage_table_missing')
                preview.execute(sql[0])
                added = ensure_persistence_schema(preview)
        else:
            before = snapshot(conn)
            added = ensure_persistence_schema(conn)
            integrity(conn)
            if snapshot(conn, before) != before:
                raise ValueError('original_data_changed')
            conn.commit()
        return dict(ok=True, status='applied' if apply else 'dry_run', added_columns=added,
                    original_data_unchanged=True, integrity='ok', foreign_keys='ok')


def cleanup(directory, *, apply=False, writers_stopped=False, limit=1000, now=None):
    if apply and not writers_stopped:
        raise ValueError('stop_all_session_writers_before_cleanup')
    source = Path(directory)
    if source.is_symlink():
        raise ValueError('symlink_directory_rejected')
    root = source.resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError('invalid_session_directory')
    if not 1 <= limit <= 10000:
        raise ValueError('invalid_scan_limit')
    now = time.time() if now is None else now
    checked = expired = removed = skipped = 0
    # Do not deserialize pickle, recurse into folders, follow symlinks, or touch
    # the management entry (expiry 0). Apply requires writers stopped to avoid
    # racing the cache's atomic replacement of renewed files.
    with os.scandir(root) as entries:
        for entry in entries:
            if checked >= limit:
                break
            checked += 1
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False) or not re.fullmatch('[a-f0-9]{32}', entry.name):
                skipped += 1
                continue
            path = Path(entry.path)
            if path.resolve().parent != root:
                raise ValueError('session_path_outside_root')
            try:
                with path.open('rb') as stream:
                    expiry = struct.unpack('I', stream.read(4))[0]
                if 0 < expiry <= now:
                    expired += 1
                    if apply:
                        path.unlink()
                        removed += 1
            except (FileNotFoundError, struct.error):
                skipped += 1
    return dict(ok=True, status='applied' if apply else 'dry_run', checked=checked,
                expired=expired, removed=removed, skipped=skipped, scan_limit=limit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    migration = commands.add_parser('migrate')
    migration.add_argument('--db', required=True)
    migration.add_argument('--apply', action='store_true')
    clean = commands.add_parser('cleanup')
    clean.add_argument('--session-dir', required=True)
    clean.add_argument('--apply', action='store_true')
    clean.add_argument('--writers-stopped', action='store_true')
    clean.add_argument('--limit', type=int, default=1000)
    args = parser.parse_args()
    try:
        result = (migrate(args.db, args.apply) if args.command == 'migrate' else
                  cleanup(args.session_dir, apply=args.apply, writers_stopped=args.writers_stopped, limit=args.limit))
        print(json.dumps(result))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps(dict(ok=False, error=str(error))))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
