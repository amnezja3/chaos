"""Private, at-most-once live presentation. Claims never execute a consequence."""
import json
from datetime import datetime, timezone

from database import db_connect


def ensure_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS response_consequence_show_claims (
        encounter_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, claimed_at TEXT NOT NULL)''')


def claim(db_path, actor, encounter_id, *, now=None):
    now = now or datetime.now(timezone.utc)
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT execution_json FROM response_encounters
            WHERE encounter_id=? AND actor_id=? AND execution_status='executed' ''',
            (encounter_id, actor)).fetchone()
        if not row:
            return None
        result = json.loads(row['execution_json'])
        stamp = datetime.fromisoformat(result['executed_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if not 0 <= (now - stamp).total_seconds() <= 60:
            return None
        inserted = conn.execute('''INSERT OR IGNORE INTO response_consequence_show_claims
            VALUES (?,?,?)''', (encounter_id, actor, now.isoformat()))
        if not inserted.rowcount:
            return None
        return {'encounter_id': encounter_id, 'stage': result['plan']['stage'],
                'effects': result['effects']}
