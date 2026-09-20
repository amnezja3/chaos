"""Explicit legacy Judgment archive/import. Read-only by default, never on a request."""
import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def migrate(path, *, apply=False, after='', limit=25):
    mode = 'rw' if apply else 'ro'
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=' + mode, uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout=10000')
        conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='response_legacy_judgment'").fetchone()
        if apply:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_legacy_judgment (
                actor_id TEXT PRIMARY KEY, points INTEGER NOT NULL, source_revision INTEGER NOT NULL,
                judgment_json TEXT NOT NULL, history_json TEXT NOT NULL, imported_at TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_judgment (
                actor_id TEXT PRIMARY KEY, points INTEGER NOT NULL, updated_at TEXT NOT NULL)''')
        rows = conn.execute('''SELECT username,profile_revision,
            CASE WHEN json_valid(profile_json) THEN json_extract(profile_json,'$.judgment.points') END AS points,
            CASE WHEN json_valid(profile_json) THEN json_type(profile_json,'$.judgment.points') END AS points_type,
            CASE WHEN json_valid(profile_json) THEN json_extract(profile_json,'$.judgment') END AS judgment_json,
            CASE WHEN json_valid(profile_json) THEN json_extract(profile_json,'$.judgment_history') END AS history_json
            FROM users WHERE username>? ORDER BY username LIMIT ?''',
            (after, min(50,max(1,limit)))).fetchall()
        report = {'applied':apply, 'scanned':len(rows), 'next_after':rows[-1]['username'] if rows else after,
                  'imported':[], 'eligible':[], 'skipped':[]}
        for row in rows:
            name = row['username']
            if row['points'] is None:
                continue
            if row['points_type'] != 'integer' or row['points'] < 0:
                report['skipped'].append({'actor':name, 'reason':'invalid_points'})
                continue
            if (exists or apply) and conn.execute('SELECT 1 FROM response_legacy_judgment WHERE actor_id=?', (name,)).fetchone():
                continue
            report['eligible'].append(name)
            if apply:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute('INSERT INTO response_legacy_judgment VALUES (?,?,?,?,?,?)',
                    (name,row['points'],row['profile_revision'],row['judgment_json'] or '{}',row['history_json'] or '[]',now))
                conn.execute('''INSERT INTO response_judgment VALUES (?,?,?) ON CONFLICT(actor_id)
                    DO UPDATE SET points=points+excluded.points,updated_at=excluded.updated_at''', (name,row['points'],now))
                report['imported'].append(name)
        if apply:
            conn.commit()
        else:
            conn.rollback()
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--after', default='')
    parser.add_argument('--limit', type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(migrate(args.db, apply=args.apply, after=args.after, limit=args.limit), ensure_ascii=False, indent=2))
