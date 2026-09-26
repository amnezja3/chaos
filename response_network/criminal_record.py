"""Small canonical record, to be committed with actual effects by 142.6."""
from database import DB_PATH, db_connect, dumps_json
from .consequence_table import plan_consequence
from datetime import datetime, timezone
from session_generation_store import username_digest

DECAY_MS = 60 * 60 * 1000


class CriminalRecordStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_criminal_records (
                actor_id TEXT PRIMARY KEY, executed_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_penalty_history (
                encounter_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                incident_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
                policy_version TEXT NOT NULL, stage INTEGER NOT NULL,
                plan_json TEXT NOT NULL, effects_json TEXT NOT NULL,
                executed_at TEXT NOT NULL, UNIQUE(actor_id,ordinal))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_record_decay (
                actor_id TEXT PRIMARY KEY, forgiven INTEGER NOT NULL DEFAULT 0,
                progress_ms INTEGER NOT NULL DEFAULT 0, sample_ms INTEGER,
                session_revision TEXT)''')

    @staticmethod
    def state(conn, actor):
        row = conn.execute('''SELECT r.executed_count,COALESCE(d.forgiven,0) forgiven,
            COALESCE(d.progress_ms,0) progress_ms FROM response_criminal_records r
            LEFT JOIN response_record_decay d ON d.actor_id=r.actor_id WHERE r.actor_id=?''', (actor,)).fetchone()
        count = row['executed_count'] if row else 0
        burden = max(0, count - (row['forgiven'] if row else 0))
        return {'executed_count': count, 'active_burden': burden,
                'remaining_seconds': (DECAY_MS - row['progress_ms'] + 999) // 1000 if burden else 0}

    def observe(self, actor, *, now=None, messages=None):
        """Only consecutive canonical authenticated heartbeats earn time; no profile reads."""
        now = now or datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            if not self.state(conn, actor)['active_burden']:
                return self.state(conn, actor)
            conn.execute('BEGIN IMMEDIATE')
            state = self.state(conn, actor)
            if not state['active_burden']:
                return state
            session = conn.execute('''SELECT s.status,s.active_revision,s.updated_at,p.last_seen_at
                FROM account_login_ownership s JOIN mail_presence p ON p.username=?
                WHERE s.username_hash=?''', (actor, username_digest(actor))).fetchone()
            def stamp(value):
                date = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return int((date if date.tzinfo else date.replace(tzinfo=timezone.utc)).timestamp()*1000)
            at = int(now.timestamp()*1000)
            try:
                heartbeat, login = stamp(session['last_seen_at']), stamp(session['updated_at'])
                live = session['status'] == 'active' and session['active_revision'] and heartbeat >= login and 0 <= at-heartbeat <= 90000
            except (TypeError, ValueError, KeyError):
                live = False
            conn.execute('INSERT OR IGNORE INTO response_record_decay(actor_id) VALUES (?)', (actor,))
            row = conn.execute('SELECT * FROM response_record_decay WHERE actor_id=?', (actor,)).fetchone()
            detained = conn.execute("SELECT 1 FROM response_sanctions WHERE actor_id=? AND status IN ('active','release_pending')", (actor,)).fetchone()
            # A completed sentence between samples must not earn peaceful time either.
            released = conn.execute('SELECT 1 FROM response_sanctions WHERE actor_id=? AND released_ms>? LIMIT 1',
                (actor, row['sample_ms'] if row['sample_ms'] is not None else at)).fetchone()
            if not live or detained:
                if row['sample_ms'] is not None:
                    conn.execute('UPDATE response_record_decay SET sample_ms=NULL,session_revision=NULL WHERE actor_id=?', (actor,))
                return {**state, 'paused': True}
            if row['sample_ms'] is not None and heartbeat <= row['sample_ms']:
                return {**state, 'paused': False}
            gap = heartbeat - row['sample_ms'] if row['sample_ms'] is not None else 0
            credit = gap if not released and row['session_revision'] == str(session['active_revision']) and 0 < gap <= 90000 else 0
            progress = row['progress_ms'] + credit
            drops = min(state['active_burden'], progress // DECAY_MS)
            progress = progress % DECAY_MS if state['active_burden'] > drops else 0
            conn.execute('''UPDATE response_record_decay SET forgiven=forgiven+?,progress_ms=?,sample_ms=?,session_revision=? WHERE actor_id=?''',
                (drops, progress, heartbeat, str(session['active_revision']), actor))
            if drops and messages:
                messages.add_message(actor, {'dedupe_key': f"record-decay:{actor}:{state['executed_count']}:{row['forgiven']+drops}",
                    'title': 'Kartoteka wygasa', 'text': 'Służby obniżyły priorytet obserwacji. Obciążenie kartoteki spadło o jeden stopień.',
                    'type': 'success', 'created_at': now.isoformat()}, source='response_network', conn=conn)
            return {**self.state(conn, actor), 'paused': False}

    def prepare(self, conn, actor_id, incident_level):
        return plan_consequence(incident_level, self.state(conn, actor_id)['active_burden'])

    def record_executed(self, conn, encounter_id, plan, effects, executed_at):
        """Caller holds BEGIN IMMEDIATE and has committed effects in this transaction.

        No inner commit/schema init/profile write. Failure rolls back with effects.
        Never call for avoided, prepared, unsupported detention or zero effects.
        """
        if not conn.in_transaction:
            raise ValueError('penalty_transaction_required')
        existing = conn.execute('SELECT ordinal FROM response_penalty_history WHERE encounter_id=?',
                                (encounter_id,)).fetchone()
        if existing:
            return {'created': False, 'ordinal': existing['ordinal']}
        receipt = conn.execute('SELECT * FROM response_encounters WHERE encounter_id=?',
                               (encounter_id,)).fetchone()
        if not receipt or receipt['outcome'] != 'selected' or receipt['execution_status'] != 'executed':
            raise ValueError('encounter_not_executed')
        if not effects or not (effects.get('fine_hc', 0) > 0 or effects.get('tool_ids')
                               or effects.get('detention_seconds', 0) > 0):
            raise ValueError('no_executed_effect')
        actor = receipt['actor_id']
        expected = self.prepare(conn, actor, plan['incident_level'])
        if not expected or plan != expected:
            raise ValueError('stale_consequence_plan')
        ordinal = self.state(conn, actor)['executed_count'] + 1
        conn.execute('''INSERT INTO response_penalty_history
            (encounter_id,actor_id,incident_id,ordinal,policy_version,stage,plan_json,effects_json,executed_at)
            VALUES (?,?,?,?,?,?,?,?,?)''', (encounter_id,actor,receipt['incident_id'],ordinal,
                plan['policy_version'],plan['stage'],dumps_json(plan),dumps_json(effects),executed_at))
        conn.execute('''INSERT INTO response_criminal_records(actor_id,executed_count,updated_at) VALUES (?,?,?)
            ON CONFLICT(actor_id) DO UPDATE SET executed_count=excluded.executed_count,
                updated_at=excluded.updated_at''', (actor,ordinal,executed_at))
        conn.execute('''INSERT INTO response_record_decay(actor_id) VALUES (?) ON CONFLICT(actor_id)
            DO UPDATE SET progress_ms=0,sample_ms=NULL,session_revision=NULL''', (actor,))
        return {'created': True, 'ordinal': ordinal}
