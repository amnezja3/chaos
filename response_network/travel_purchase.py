"""Atomic ticket payment and position commit; receipt replay never moves twice."""
import os

from database import db_connect
from .movement_guard import require_movement_allowed


def purchase_travel(wallet, positions, *, actor, payee, price, key, note, destination):
    if os.path.abspath(wallet.db_path) != os.path.abspath(positions.db_path):
        raise ValueError('travel_stores_must_share_database')
    position = {}

    def move(conn, transaction):
        if transaction.get('duplicate'):
            current = positions.get(actor, conn=conn) or {}
            position.update({'changed': False, 'position': {k: current[k] for k in ('lat', 'lng') if k in current},
                             'version': current.get('version'), 'updated_at': current.get('updated_at')})
            return
        require_movement_allowed(conn, actor)
        position.update(positions.upsert(actor, destination, source='googleplex_travel', conn=conn))
        if not position.get('position'):
            raise ValueError('invalid_travel_destination')

    if price > 0 and payee != actor:
        result = wallet.transfer(actor, payee, price, transaction_key=key, note=note,
                                 source='googleplex.travel', transaction_callback=move)
        payment = {'balance': result['source_balance'], 'recipient_balance': result['target_balance'],
                   'duplicate': bool(result.get('duplicate'))}
    else:
        # Free/self-paid tickets still need a durable replay key.
        with db_connect(positions.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('''CREATE TABLE IF NOT EXISTS player_free_travel_receipts (
                purchase_key TEXT PRIMARY KEY, actor_id TEXT NOT NULL, destination_json TEXT NOT NULL)''')
            import json
            encoded = json.dumps(destination, sort_keys=True)
            old = conn.execute('SELECT * FROM player_free_travel_receipts WHERE purchase_key=?', (key,)).fetchone()
            if old and (old['actor_id'] != actor or old['destination_json'] != encoded):
                raise ValueError('travel_receipt_conflict')
            move(conn, {'duplicate': bool(old)})
            if not old:
                conn.execute('INSERT INTO player_free_travel_receipts VALUES (?,?,?)', (key, actor, encoded))
            payment = {'duplicate': bool(old)}
    return payment, position
