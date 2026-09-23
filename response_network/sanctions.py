"""143.2 durable sanctions. Internal transaction API; no client clock or activation.

Callers must hold BEGIN IMMEDIATE. Presence samples are server-owned observations,
never request fields. Transport and actual message delivery join this transaction
in subsequent stages; this module alone does not impose a gameplay penalty.
"""
import hashlib
import json
from datetime import datetime, timezone

from database import DB_PATH, db_connect, dumps_json
from session_generation_store import username_digest


def milliseconds(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError('aware_server_time_required')
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


class SanctionStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_sanctions (
                sanction_id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL UNIQUE,
                actor_id TEXT NOT NULL, incident_id TEXT NOT NULL,
                plan_json TEXT NOT NULL, duration_ms INTEGER NOT NULL,
                remaining_ms INTEGER NOT NULL CHECK(remaining_ms >= 0),
                status TEXT NOT NULL, created_ms INTEGER NOT NULL,
                updated_ms INTEGER NOT NULL, sample_ms INTEGER,
                session_revision TEXT, version INTEGER NOT NULL DEFAULT 1,
                release_reason TEXT, released_ms INTEGER)''')
            conn.execute('''CREATE UNIQUE INDEX IF NOT EXISTS response_one_open_sanction
                ON response_sanctions(actor_id) WHERE status IN ('active','release_pending')''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_sanction_events (
                sanction_id TEXT NOT NULL, version INTEGER NOT NULL,
                kind TEXT NOT NULL, at_ms INTEGER NOT NULL, data_json TEXT NOT NULL,
                PRIMARY KEY(sanction_id,version))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_sanction_messages (
                sanction_id TEXT PRIMARY KEY, message_id TEXT NOT NULL UNIQUE,
                consumed_ms INTEGER NOT NULL)''')

    @staticmethod
    def _transaction(conn):
        if not conn.in_transaction:
            raise ValueError('sanction_transaction_required')

    @staticmethod
    def get(conn, sanction_id):
        row = conn.execute('SELECT * FROM response_sanctions WHERE sanction_id=?',
                           (sanction_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def active_for(conn, actor_id):
        row = conn.execute("""SELECT * FROM response_sanctions WHERE actor_id=?
            AND status IN ('active','release_pending')""", (actor_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _event(conn, row, kind, at, data=None):
        conn.execute('INSERT INTO response_sanction_events VALUES (?,?,?,?,?)',
                     (row['sanction_id'], row['version'], kind, at, dumps_json(data or {})))

    def impose(self, conn, *, encounter_id, actor_id, incident_id, plan, now):
        self._transaction(conn)
        at = milliseconds(now)
        existing = conn.execute('SELECT * FROM response_sanctions WHERE encounter_id=?',
                                (encounter_id,)).fetchone()
        if existing:
            if existing['actor_id'] != actor_id or existing['incident_id'] != incident_id:
                raise ValueError('sanction_identity_mismatch')
            return dict(existing), False
        minutes = plan.get('detention_minutes')
        if type(minutes) is not int or not 0 < minutes <= 20:
            raise ValueError('invalid_detention_plan')
        if not all(isinstance(v, str) and v.strip() for v in (actor_id, incident_id, encounter_id)):
            raise ValueError('invalid_sanction_identity')
        if self.active_for(conn, actor_id):
            raise ValueError('actor_already_detained')
        sid = 'sanction_' + hashlib.sha256(encounter_id.encode()).hexdigest()[:32]
        conn.execute('''INSERT INTO response_sanctions
            (sanction_id,encounter_id,actor_id,incident_id,plan_json,duration_ms,
             remaining_ms,status,created_ms,updated_ms) VALUES (?,?,?,?,?,?,?,'active',?,?)''',
            (sid, encounter_id, actor_id, incident_id, dumps_json(plan),
             minutes * 60000, minutes * 60000, at, at))
        row = self.get(conn, sid)
        self._event(conn, row, 'imposed', at)
        return row, True

    def sample(self, conn, sanction_id, *, now, online, session_revision, max_gap_seconds=90):
        """Credit only consecutive online observations within the presence window.

        Duplicate/out-of-order samples are inert. Offline/logout, a session change
        or a long outage breaks the interval. Restart preserves already earned time.
        No speculative credit after the final heartbeat.
        """
        self._transaction(conn)
        at = milliseconds(now)
        if type(online) is not bool or type(max_gap_seconds) is not int or not 0 < max_gap_seconds <= 90:
            raise ValueError('invalid_presence_sample')
        if online and not session_revision:
            raise ValueError('session_revision_required')
        row = self.get(conn, sanction_id)
        if not row:
            raise ValueError('sanction_not_found')
        if row['status'] != 'active' or at <= row['updated_ms']:
            return row
        revision = str(session_revision) if online else None
        if not online and row['sample_ms'] is None and row['session_revision'] is None:
            return row  # Already paused; don't append an event on every worker tick.
        credit = 0
        if online and row['session_revision'] == revision and row['sample_ms'] is not None:
            gap = at - row['sample_ms']
            if 0 < gap <= max_gap_seconds * 1000:
                credit = min(gap, row['remaining_ms'])
        remaining = row['remaining_ms'] - credit
        status = 'active' if remaining else 'release_pending'
        conn.execute('''UPDATE response_sanctions SET remaining_ms=?,status=?,sample_ms=?,
            session_revision=?,updated_ms=?,version=version+1 WHERE sanction_id=?''',
            (remaining, status, at if online else None, revision, at, sanction_id))
        row = self.get(conn, sanction_id)
        self._event(conn, row, 'presence', at, {'credited_ms': credit, 'online': online})
        return row

    def observe_presence(self, conn, sanction_id, *, now):
        """Indexed canonical reads; only new authenticated heartbeat time earns credit.

        Worker integration must call this regularly and on explicit logout. A missed
        interval longer than 90 seconds is conservatively not credited. No profile
        read or client-provided actor/session/online timestamp is accepted here.
        """
        self._transaction(conn)
        at = milliseconds(now)
        row = self.get(conn, sanction_id)
        if not row:
            raise ValueError('sanction_not_found')
        if row['status'] != 'active':
            return row
        session = conn.execute('''SELECT status,updated_at,active_revision
            FROM account_login_ownership WHERE username_hash=?''',
            (username_digest(row['actor_id']),)).fetchone()
        presence = conn.execute('SELECT last_seen_at FROM mail_presence WHERE username=?',
                                (row['actor_id'],)).fetchone()
        try:
            heartbeat = datetime.fromisoformat(presence['last_seen_at'].replace('Z', '+00:00'))
            login = datetime.fromisoformat(session['updated_at'].replace('Z', '+00:00'))
            # Legacy canonical timestamps are UTC even where they omit an offset.
            heartbeat = heartbeat if heartbeat.tzinfo else heartbeat.replace(tzinfo=timezone.utc)
            login = login if login.tzinfo else login.replace(tzinfo=timezone.utc)
            live = (session['status'] == 'active' and bool(session['active_revision'])
                    and heartbeat >= login and 0 <= at - milliseconds(heartbeat) <= 90000)
        except (TypeError, ValueError, AttributeError, KeyError):
            live = False
        if not live:
            return self.sample(conn, sanction_id, now=now, online=False, session_revision=None)
        return self.sample(conn, sanction_id, now=heartbeat, online=True,
                           session_revision=session['active_revision'])

    @classmethod
    def consume_private_message(self, conn, sanction_id, *, message_id, now):
        """Reserve the single non-World send in the SAME transaction as delivery."""
        self._transaction(conn)
        row = self.get(conn, sanction_id)
        if not row or row['status'] not in ('active', 'release_pending'):
            raise ValueError('sanction_not_active')
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError('message_id_required')
        used = conn.execute('SELECT message_id FROM response_sanction_messages WHERE sanction_id=?',
                            (sanction_id,)).fetchone()
        if used:
            if used['message_id'] == message_id:
                return False
            raise ValueError('private_message_allowance_exhausted')
        if json.loads(row['plan_json'])['detention_rules']['private_message_allowance'] != 1:
            raise ValueError('unsupported_message_policy')
        conn.execute('INSERT INTO response_sanction_messages VALUES (?,?,?)',
                     (sanction_id, message_id, milliseconds(now)))
        return True

    def release(self, conn, sanction_id, *, reason, now):
        """Join return transport (and bail debit, if applicable) in caller transaction."""
        self._transaction(conn)
        row = self.get(conn, sanction_id)
        if not row:
            raise ValueError('sanction_not_found')
        if row['status'] == 'released':
            return row, False
        if reason not in ('served', 'bail'):
            raise ValueError('invalid_release_reason')
        if reason == 'served' and row['remaining_ms']:
            raise ValueError('sentence_not_served')
        if reason == 'bail' and not row['remaining_ms']:
            raise ValueError('sentence_already_served')
        at = milliseconds(now)
        if at < row['updated_ms']:
            raise ValueError('stale_release_time')
        conn.execute('''UPDATE response_sanctions SET status='released',release_reason=?,
            released_ms=?,updated_ms=?,sample_ms=NULL,session_revision=NULL,
            version=version+1 WHERE sanction_id=?''', (reason, at, at, sanction_id))
        row = self.get(conn, sanction_id)
        self._event(conn, row, 'released', at, {'reason': reason})
        return row, True
