"""143.4 atomic prison transport, online clock recovery and bail.

Only this service writes detention positions. Destinations come from the saved
sentence, never HTTP coordinates or a source-string bypass of the movement gate.
"""
import json
import logging
import os
import secrets
from datetime import datetime, timezone

from database import db_connect, dumps_json, PlayerPositionStore
from session_generation_store import username_digest
from .prison_catalog import list_prisons
from .sanctions import SanctionStore, milliseconds


def detention_enabled():
    return os.environ.get('CHAOS_RESPONSE_DETENTION_ENABLED', 'false').lower() == 'true'


class DetentionService:
    def __init__(self, db_path, wallet, messages, deltas):
        self.db_path, self.wallet, self.messages, self.deltas = db_path, wallet, messages, deltas
        if any(os.path.abspath(s.db_path) != os.path.abspath(db_path) for s in (wallet, messages, deltas)):
            raise ValueError('detention_stores_must_share_database')
        self.sanctions = SanctionStore(db_path)
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_detention_transport (
                sanction_id TEXT PRIMARY KEY, prison_json TEXT NOT NULL,
                return_lat REAL NOT NULL, return_lng REAL NOT NULL,
                checked_ms INTEGER NOT NULL DEFAULT 0, pending INTEGER NOT NULL DEFAULT 1,
                bail_payer TEXT, bail_paid_hc INTEGER NOT NULL DEFAULT 0)''')
            fields = {r[1] for r in conn.execute('PRAGMA table_info(response_detention_transport)')}
            if 'pending' not in fields:
                conn.execute('ALTER TABLE response_detention_transport ADD COLUMN pending INTEGER NOT NULL DEFAULT 1')
                conn.execute("UPDATE response_detention_transport SET pending=0 WHERE sanction_id IN (SELECT sanction_id FROM response_sanctions WHERE status='released')")
            conn.execute('''CREATE INDEX IF NOT EXISTS response_detention_pending_tick
                ON response_detention_transport(checked_ms,sanction_id) WHERE pending=1''')

    @staticmethod
    def _online_revision(conn, actor, now):
        row = conn.execute('''SELECT s.status,s.active_revision,s.updated_at,p.last_seen_at
            FROM account_login_ownership s JOIN mail_presence p ON p.username=?
            WHERE s.username_hash=?''', (actor, username_digest(actor))).fetchone()
        if not row or row['status'] != 'active' or not row['active_revision']:
            return None
        def parse(stamp):
            date = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            return date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        heartbeat, login = parse(row['last_seen_at']), parse(row['updated_at'])
        if heartbeat < login or not 0 <= (now - heartbeat).total_seconds() <= 90:
            return None
        return str(row['active_revision'])

    def impose(self, conn, *, actor, encounter_id, incident_id, plan, now):
        self.sanctions._transaction(conn)
        if not detention_enabled():
            raise ValueError('detention_disabled')
        revision = self._online_revision(conn, actor, now)
        if not revision:
            raise ValueError('detention_requires_online')
        origin = conn.execute('SELECT lat,lng FROM player_positions WHERE username=?', (actor,)).fetchone()
        if not origin or not PlayerPositionStore._normalize(dict(origin)):
            raise ValueError('detention_position_missing')
        row, created = self.sanctions.impose(conn, encounter_id=encounter_id, actor_id=actor,
            incident_id=incident_id, plan=plan, now=now)
        if not created:
            return row
        prison = secrets.choice(list_prisons())
        conn.execute('INSERT INTO response_detention_transport(sanction_id,prison_json,return_lat,return_lng) VALUES (?,?,?,?)',
                     (row['sanction_id'], dumps_json(prison), origin['lat'], origin['lng']))
        conn.execute('UPDATE response_sanctions SET sample_ms=?,session_revision=? WHERE sanction_id=?',
                     (milliseconds(now), revision, row['sanction_id']))
        self._move(conn, row, returning=False, now=now)
        self.messages.add_message(actor, {'id': row['sanction_id'], 'dedupe_key': row['sanction_id'],
            'title': 'Areszt', 'text': f"Areszt: {plan['detention_minutes']} min online. "
                f"Wiezienie: {prison['name']}. Kaucja: {plan['bail_hc']} HC.",
            'type': 'warning', 'sanction_id': row['sanction_id'], 'created_at': now.isoformat()},
            source='response_network', conn=conn)
        return self.sanctions.get(conn, row['sanction_id'])

    def _move(self, conn, row, *, returning, now):
        self.sanctions._transaction(conn)
        transport = conn.execute('SELECT * FROM response_detention_transport WHERE sanction_id=?',
                                  (row['sanction_id'],)).fetchone()
        if not transport or row['status'] != ('released' if returning else 'active'):
            raise ValueError('invalid_detention_transport')
        destination = ({'lat': transport['return_lat'], 'lng': transport['return_lng']} if returning
                       else json.loads(transport['prison_json']))
        point = PlayerPositionStore._normalize(destination)
        if not point:
            raise ValueError('invalid_detention_destination')
        source = 'detention_release' if returning else 'detention_imposed'
        changed = conn.execute('''UPDATE player_positions SET lat=?,lng=?,source=?,
            version=version+1,updated_at=? WHERE username=?''',
            (point['lat'], point['lng'], source, now.isoformat(), row['actor_id']))
        if changed.rowcount != 1:
            raise ValueError('detention_position_missing')
        version = conn.execute('SELECT version FROM player_positions WHERE username=?', (row['actor_id'],)).fetchone()[0]
        self.deltas.record_change(row['actor_id'], 'map', 'map.player_forced_position',
            {'username': row['actor_id'], **point, 'position_version': version,
             'position_updated_at': now.isoformat(), 'reason': source, 'sanction_id': row['sanction_id']},
            entity_id=row['actor_id'], dedupe_key=row['sanction_id'] + ':' + source, conn=conn)

    def _release(self, conn, row, *, reason, now):
        released, changed = self.sanctions.release(conn, row['sanction_id'], reason=reason, now=now)
        if changed:
            self._move(conn, released, returning=True, now=now)
            conn.execute('UPDATE response_detention_transport SET pending=0 WHERE sanction_id=?', (row['sanction_id'],))
            self.messages.add_message(row['actor_id'], {'id': row['sanction_id'] + ':released',
                'dedupe_key': row['sanction_id'] + ':released', 'title': 'Zwolnienie z aresztu',
                'text': 'Kaucja oplacona. Powrot do pozycji sprzed aresztu.' if reason == 'bail'
                        else 'Wyrok odbyty. Powrot do pozycji sprzed aresztu.',
                'type': 'success', 'sanction_id': row['sanction_id'], 'created_at': now.isoformat()},
                source='response_network', conn=conn)
        return released

    def _advance(self, conn, row, now):
        row = self.sanctions.observe_presence(conn, row['sanction_id'], now=now)
        if row['status'] == 'release_pending':
            row = self._release(conn, row, reason='served', now=now)
        return row

    def advance_actor(self, actor, *, now=None):
        now = now or datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            if not self.sanctions.active_for(conn, actor):
                return None  # Ordinary polling must not acquire the SQLite writer.
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = self.sanctions.active_for(conn, actor)
            if row:
                row = self._advance(conn, row, now)
            return self._public(row) if row else None

    def tick(self, *, now=None, limit=16):
        # Recovery/clock/release are deliberately independent of the activation flag.
        now = now or datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT t.sanction_id FROM response_detention_transport t
                JOIN response_sanctions s ON s.sanction_id=t.sanction_id
                WHERE t.pending=1 AND s.status IN ('active','release_pending')
                ORDER BY t.checked_ms,t.sanction_id LIMIT ?''', (max(1, min(32, int(limit))),)).fetchall()
        released = 0
        errors = 0
        for item in rows:
            with db_connect(self.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                row = self.sanctions.get(conn, item['sanction_id'])
                if row['status'] not in ('active', 'release_pending'):
                    continue
                conn.execute('SAVEPOINT detention_tick')
                try:
                    row = self._advance(conn, row, now)
                except Exception:
                    conn.execute('ROLLBACK TO detention_tick')
                    errors += 1
                    logging.getLogger(__name__).exception('Detention recovery failed: %s', row['sanction_id'])
                else:
                    released += row['status'] == 'released'
                finally:
                    conn.execute('RELEASE detention_tick')
                conn.execute('UPDATE response_detention_transport SET checked_ms=? WHERE sanction_id=?',
                             (milliseconds(now), row['sanction_id']))
        return {'checked': len(rows), 'released': released, 'errors': errors}

    @staticmethod
    def _public(row):
        plan = json.loads(row['plan_json'])
        return {'sanction_id': row['sanction_id'], 'status': row['status'], 'stage': plan['stage'],
                'remaining_seconds': (row['remaining_ms'] + 999) // 1000,
                'bail_hc': plan['bail_hc'], 'release_reason': row['release_reason']}

    def quote(self, actor):
        # Minimum data needed by a third-party payer; no prison/return coordinates.
        with db_connect(self.db_path) as conn:
            row = self.sanctions.active_for(conn, actor)
            return self._public(row) if row else None

    def pay_bail(self, payer, sanction_id, *, now=None):
        now = now or datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = self.sanctions.get(conn, sanction_id)
            if not row:
                raise ValueError('sanction_not_found')
            if row['status'] == 'released':
                return {'paid': False, 'reason': 'already_released'}
            row = self._advance(conn, row, now)
            if row['status'] == 'released':
                return {'paid': False, 'reason': 'sentence_served'}
            amount = int(json.loads(row['plan_json'])['bail_hc'])
            debit = self.wallet.debit(payer, amount, 'detention_bail:' + sanction_id,
                                      reason='response.bail', source='response_network', conn=conn)
            self.deltas.record_change(payer, 'wallet', 'wallet.balance_changed',
                {'balance': debit['balance'], 'currency': 'HC'}, entity_id='wallet',
                dedupe_key=sanction_id + ':bail', conn=conn)
            conn.execute('UPDATE response_detention_transport SET bail_payer=?,bail_paid_hc=? WHERE sanction_id=?',
                         (payer, amount, sanction_id))
            self._release(conn, row, reason='bail', now=now)
            return {'paid': True, 'amount_hc': amount, 'balance': debit['balance'], 'sanction_id': sanction_id}
