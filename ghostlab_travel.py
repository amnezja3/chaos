"""Single-use travel purchases and verified-traveller reactions, without profiles."""
import json
import hashlib
import os
from database import db_connect
from ghostlab_store import GhostLabError, encoded, now, digest
from ghostlab_registry import template_available, runtime_actor_allowed, validate_fields
from ghostlab_products import published_product, runtime_artifact_ready
from response_network.movement_guard import require_movement_allowed


REACTIONS = ('bad', 'happy', 'very_happy')


class TravelStore:
    def __init__(self, db_path):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS travel_purchases (
                receipt TEXT PRIMARY KEY, actor TEXT NOT NULL, app_id TEXT NOT NULL,
                artifact_id TEXT, destination_revision TEXT NOT NULL, author TEXT NOT NULL,
                price INTEGER NOT NULL, offer_json TEXT NOT NULL, result_json TEXT NOT NULL,
                created_at TEXT NOT NULL)''')
            conn.execute('CREATE INDEX IF NOT EXISTS travel_actor_product ON travel_purchases(actor,app_id,created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS travel_actor_destination ON travel_purchases(actor,app_id,destination_revision,created_at)')
            conn.execute('''CREATE TABLE IF NOT EXISTS travel_reactions (
                actor TEXT NOT NULL, app_id TEXT NOT NULL, receipt TEXT NOT NULL,
                destination_revision TEXT NOT NULL, reaction TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY(actor,app_id))''')
            conn.execute('CREATE INDEX IF NOT EXISTS travel_reaction_counts ON travel_reactions(app_id,destination_revision,reaction)')

    def offer(self, conn, app_id, system_catalog, cities):
        if app_id.startswith('ghostlab_'):
            app = published_product(conn, app_id)
            if not app or app.get('template_id') != 'travel_ticket':
                raise GhostLabError('ticket_not_found', 'Brak biletu.', 404)
            row = conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE artifact_id=?', (app['artifact_id'],)).fetchone()
            artifact = json.loads(row[0]) if row else {}
            if not runtime_artifact_ready(artifact):
                raise GhostLabError('ticket_build_unavailable', 'Bilet wymaga zgodnego buildu.')
            destination = dict(artifact['blueprint_snapshot'])
        else:
            app = next((a for a in system_catalog if a['id'] == app_id and a.get('product_type') == 'travel_ticket'), None)
            if not app:
                raise GhostLabError('ticket_not_found', 'Brak biletu.', 404)
            city = cities.get(app.get('travel_city'))
            if not city:
                raise GhostLabError('destination_disabled', 'Miejsce jest niedostępne.')
            destination = dict(place_name=city['name'], city=city['name'], country=city['country'], lat=city['lat'], lng=city['lng'])
        if validate_fields('travel_ticket', destination):
            raise GhostLabError('invalid_destination', 'Nieprawidłowe dane miejsca.')
        return dict(app, destination=destination, destination_revision=digest(destination))

    def state(self, actor, app_id, system_catalog, cities):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN')
            offer = self.offer(conn, app_id, system_catalog, cities)
            return dict(offer=offer, **self.reactions(conn, actor, offer))

    @staticmethod
    def reactions(conn, actor, offer):
        counts = {key: 0 for key in REACTIONS}
        history = dict(counts)
        for row in conn.execute('''SELECT destination_revision=? AS current_place,reaction,count(*) AS n FROM travel_reactions
                WHERE app_id=? GROUP BY current_place,reaction''', (offer['destination_revision'],offer['id'])):
            target = counts if row['current_place'] else history
            target[row['reaction']] += row['n']
        mine = conn.execute('SELECT reaction,destination_revision FROM travel_reactions WHERE actor=? AND app_id=?', (actor,offer['id'])).fetchone()
        trip = conn.execute('''SELECT receipt FROM travel_purchases WHERE actor=? AND app_id=?
            AND destination_revision=? ORDER BY created_at DESC LIMIT 1''', (actor,offer['id'],offer['destination_revision'])).fetchone()
        return dict(counts=counts, historical_counts=history, mine=dict(mine) if mine else None,
                    reaction_receipt=trip['receipt'] if trip and actor != offer.get('creator_username') else None)

    def react(self, actor, app_id, receipt, reaction):
        if reaction not in REACTIONS or not isinstance(receipt, str) or len(receipt)>200:
            raise GhostLabError('invalid_reaction', 'Wybierz jedną z trzech reakcji.', 400)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            trip = conn.execute('SELECT * FROM travel_purchases WHERE receipt=? AND actor=? AND app_id=?', (receipt,actor,app_id)).fetchone()
            if not trip or trip['author'] == actor:
                raise GhostLabError('travel_required', 'Ocenę może dodać podróżujący, który nie jest autorem.', 403)
            conn.execute('''INSERT INTO travel_reactions VALUES(?,?,?,?,?,?) ON CONFLICT(actor,app_id)
                DO UPDATE SET receipt=excluded.receipt,destination_revision=excluded.destination_revision,
                reaction=excluded.reaction,updated_at=excluded.updated_at''',
                (actor,app_id,receipt,trip['destination_revision'],reaction,now()))

    def purchase(self, actor, app_id, action_key, expected_artifact, expected_price,
                 *, system_catalog, cities, wallet, positions, deltas, inventory, requirements):
        if not isinstance(action_key,str) or not 1 <= len(action_key) <= 180:
            raise GhostLabError('purchase_key_required', 'Brak identyfikatora zakupu.', 400)
        if any(os.path.abspath(s.db_path) != os.path.abspath(self.db_path) for s in (wallet,positions,deltas,inventory)):
            raise ValueError('travel_stores_must_share_database')
        receipt = 'travel:' + digest([actor, action_key])
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT * FROM travel_purchases WHERE receipt=?', (receipt,)).fetchone()
            if old:
                if old['actor'] != actor or old['app_id'] != app_id or old['artifact_id'] != expected_artifact or old['price'] != expected_price:
                    raise GhostLabError('purchase_key_conflict', 'Identyfikator dotyczy innego zakupu.')
                result = json.loads(old['result_json'])
                result.update(duplicate=True, hackcoins=wallet.get_balance(actor))
                result['travel'] = None  # A retry never rewinds the client to the old destination.
                return result
            # A browser may retry a purchase begun before the canonical-ticket cutover.
            # Recognize the old durable payment/free receipt without touching profile mirrors.
            if not app_id.startswith('ghostlab_'):
                legacy_key = f'googleplex:purchase:{actor}:{app_id}:' + hashlib.sha256(action_key.encode()).hexdigest()
                legacy = conn.execute('SELECT from_username,amount FROM wallet_transactions WHERE transaction_key=?', (legacy_key,)).fetchone()
                free = None
                if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_free_travel_receipts'").fetchone():
                    free = conn.execute('SELECT actor_id FROM player_free_travel_receipts WHERE purchase_key=?', (legacy_key,)).fetchone()
                if (legacy and legacy['from_username'] == actor) or (free and free['actor_id'] == actor):
                    return dict(status='success', duplicate=True, hackcoins=wallet.get_balance(actor), travel=None,
                        product={'id':app_id,'product_type':'travel_ticket'}, reaction_receipt=None,
                        message='Ten historyczny zakup został już rozliczony. Nie pobrano ponownie HC.')
            offer = self.offer(conn,app_id,system_catalog,cities)
            if offer.get('published') is False:
                raise GhostLabError('publication_withdrawn', 'Bilet wycofano ze sprzedaży.')
            if offer.get('artifact_id') != expected_artifact or type(expected_price) is not int or offer['price'] != expected_price:
                raise GhostLabError('offer_changed', 'Oferta zmieniła się. Odśwież i potwierdź zakup ponownie.')
            if offer.get('ghostlab_generated') and (not template_available('travel_ticket','runtime') or not runtime_actor_allowed(actor)):
                raise GhostLabError('ticket_runtime_disabled', 'Podróże twórców nie są aktywne dla tego konta.')
            require_movement_allowed(conn,actor)
            wallet._assert_migration_not_blocked_with_conn(conn,actor)
            requirements(offer,conn)
            payee = offer.get('creator_username') or 'admin'
            price = offer['price']
            if price and payee != actor:
                wallet.transfer(actor,payee,price,transaction_key=receipt,note='googleplex:'+app_id,
                                source='googleplex.travel',conn=conn)
            destination = offer['destination']
            moved = positions.upsert(actor,{'lat':destination['lat'],'lng':destination['lng']},source='googleplex_travel',conn=conn)
            if not moved.get('position'):
                raise GhostLabError('invalid_destination','Nie można wykonać podróży.')
            balance = conn.execute('SELECT balance FROM wallet_balances WHERE username=?',(actor,)).fetchone()
            if balance is None:
                raise GhostLabError('wallet_unavailable','Portfel niedostępny.')
            for username in {actor,payee}:
                row=conn.execute('SELECT balance FROM wallet_balances WHERE username=?',(username,)).fetchone()
                if row:
                    deltas.record_change(username,'wallet','wallet.balance_changed',{'balance':row['balance'],'currency':'HC'},
                        dedupe_key=receipt+':'+username,conn=conn)
            deltas.record_change(actor,'map','map.player_forced_position',
                dict(username=actor,**moved['position'],position_version=moved['version'],position_updated_at=moved['updated_at'],reason='googleplex_travel'),
                dedupe_key=receipt+':position',conn=conn)
            result=dict(status='success',duplicate=False,hackcoins=balance['balance'],price=price,
                product={'id':app_id,'name':offer['name'],'product_type':'travel_ticket'},
                travel=dict(receipt=receipt,position=moved['position'],position_version=moved['version'],position_updated_at=moved['updated_at']),
                message='Podróż zakończona.',reaction_receipt=receipt if actor != payee else None)
            conn.execute('INSERT INTO travel_purchases VALUES(?,?,?,?,?,?,?,?,?,?)',
                (receipt,actor,app_id,offer.get('artifact_id'),offer['destination_revision'],payee,price,encoded(offer),encoded(result),now()))
            return result


def register(app, services):
    from flask import request, session, jsonify
    def actor():
        if not session.get('user'):
            raise GhostLabError('authentication_required','Zaloguj się.',401)
        return session['user']
    @app.get('/api/travel-tickets/<app_id>')
    def travel_ticket_state(app_id):
        return jsonify(success=True,**services['travel_store'].state(actor(),app_id,services['googleplex_product_catalog'](),services['TRAVEL_CITIES']))
    @app.post('/api/travel-tickets/<app_id>/reaction')
    def travel_ticket_reaction(app_id):
        username=actor()
        if request.content_length and request.content_length>2048:
            raise GhostLabError('invalid_reaction','Zbyt duże żądanie.',413)
        data=request.get_json(silent=True)
        if not isinstance(data,dict):
            raise GhostLabError('invalid_reaction','Nieprawidłowa reakcja.',400)
        services['travel_store'].react(username,app_id,data.get('receipt'),data.get('reaction'))
        return jsonify(success=True)
