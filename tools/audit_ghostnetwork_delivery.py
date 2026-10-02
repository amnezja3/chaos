"""Read-only, bounded audit of canonical events versus durable delivery jobs.

Missing delivery is a candidate for review, not proof that a gameplay reward
was lost. This command never runs a migration or replays an old cycle.
"""
import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def utc_timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Use an explicit timezone, for example +02:00 or Z')
    return parsed.astimezone(timezone.utc).isoformat()


def audit(db_path, since, until, limit=100):
    since, until = utc_timestamp(since), utc_timestamp(until)
    if since >= until or not 1 <= limit <= 500:
        raise ValueError('Expected since < until and limit between 1 and 500')
    path = Path(db_path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        rows = conn.execute('''SELECT e.event_id, e.event_type, e.cycle_id,
            e.part_id, e.player_id, e.created_at, d.status AS delivery_status
            FROM ghost_part_events e LEFT JOIN ghostnetwork_delta_delivery_jobs d
            ON d.event_id=e.event_id
            WHERE julianday(e.created_at)>=julianday(?) AND julianday(e.created_at)<julianday(?)
            ORDER BY e.created_at,e.event_id LIMIT ?''', (since, until, limit + 1)).fetchall()
    return {'read_only': True, 'since': since, 'until': until,
            'truncated': len(rows) > limit,
            'events': [dict(row) for row in rows[:limit]],
            'missing_delivery_ids': [row['event_id'] for row in rows[:limit] if row['delivery_status'] is None]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--since', required=True)
    parser.add_argument('--until', required=True)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(audit(args.db, args.since, args.until, args.limit), ensure_ascii=False, indent=2))
