"""Join the one non-World allowance, fan-out and retry receipt in one write."""
import hashlib
import json
import secrets
from datetime import datetime, timezone

from database import db_connect, dumps_json
from .capabilities import snapshot, require_world, DetentionDenied
from .sanctions import SanctionStore


def deliver(db_path, actor, route, body, subject, client_id, writer):
    fingerprint = hashlib.sha256(dumps_json([route['channel'], route['channel_key'], body, subject]).encode()).hexdigest()
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        state = snapshot(conn, actor)
        if route['channel'] == 'world':
            require_world(conn, actor, sending=True)
        # Receipt also covers direct/group legacy delivery and retries after release.
        conn.execute('''CREATE TABLE IF NOT EXISTS response_chat_receipts (
            actor_id TEXT NOT NULL, client_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
            message_json TEXT NOT NULL, PRIMARY KEY(actor_id,client_id))''')
        key = str(client_id or secrets.token_hex(24))
        if len(key) > 200:
            raise ValueError('client_message_id_too_long')
        previous = conn.execute('SELECT * FROM response_chat_receipts WHERE actor_id=? AND client_id=?',
                                (actor, key)).fetchone()
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise ValueError('message_idempotency_conflict')
            return json.loads(previous['message_json']), False
        if state and route['channel'] != 'world':
            if not state['private_messages_remaining']:
                raise DetentionDenied('private_message_allowance_exhausted', state)
        message, created = writer(conn)
        if created and state and route['channel'] != 'world':
            SanctionStore.consume_private_message(conn, state['sanction_id'],
                message_id='chat_' + secrets.token_hex(24), now=datetime.now(timezone.utc))
        conn.execute('INSERT INTO response_chat_receipts VALUES (?,?,?,?)',
                     (actor, key, fingerprint, dumps_json(message)))
        return message, created
