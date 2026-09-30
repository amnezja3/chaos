"""Owned, immutable PTK editions. Purchases never hydrate player profiles."""
import json
from database import db_connect
from ghostlab_store import GhostLabError, now
from ghostlab_products import published_product, runtime_artifact_ready
from ghostlab_registry import template_available, runtime_actor_allowed
from ghostlab_pricing import apply_price


def visible(app, clan=''):
    return (app.get('template_id') != 'ptk_document' or app.get('visibility', 'global') == 'global'
            or bool(clan and clan == app.get('publication_clan')))


def public_document(app):
    fields = ('id', 'name', 'icon', 'description', 'system_description', 'type', 'category',
              'product_type', 'price', 'price_hint', 'open_source', 'creator_username', 'creator_nick',
              'published', 'generated', 'ghostlab_generated', 'template_id', 'template_name',
              'artifact_id', 'source_build_version', 'runtime_status', 'visibility', 'installed', 'can_afford',
              'install_blocked_reason', 'downloads')
    return {key: app[key] for key in fields if key in app}


class DocumentStore:
    def __init__(self, db_path):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_document_copies (
                owner TEXT NOT NULL, app_id TEXT NOT NULL, artifact_id TEXT NOT NULL,
                title TEXT NOT NULL, author TEXT NOT NULL, version INTEGER NOT NULL,
                price INTEGER NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(owner, artifact_id))''')
            conn.execute('CREATE INDEX IF NOT EXISTS glab_documents_owner_app ON ghostlab_document_copies(owner,app_id)')

    def files(self, owner):
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT artifact_id AS id, app_id, title, author, version
                FROM ghostlab_document_copies WHERE owner=? ORDER BY created_at DESC LIMIT 1001''', (owner,)).fetchall()
        return [dict(r, name=f"{r['title']} v{r['version']}.ptk") for r in rows]

    def read(self, owner, artifact_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute('''SELECT c.*, b.artifact_json FROM ghostlab_document_copies c
                JOIN ghostlab_builds b ON b.artifact_id=c.artifact_id
                WHERE c.owner=? AND c.artifact_id=?''', (owner, artifact_id)).fetchone()
        if not row:
            raise GhostLabError('document_not_owned', 'Dokument nie został pobrany na to konto.', 404)
        artifact = json.loads(row['artifact_json'])
        return dict(id=artifact_id, title=row['title'], author=row['author'], version=row['version'],
                    content=artifact['blueprint_snapshot']['content'])

    def purchase(self, owner, app_id, data, services):
        wallet = services['wallet_balance_store']
        deltas = services['delta_bus']
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            app = published_product(conn, app_id)
            if not app or app.get('template_id') != 'ptk_document':
                raise GhostLabError('document_not_found', 'Brak dokumentu.', 404)
            identity = conn.execute('SELECT clan_code FROM user_identity_projection WHERE username=?', (owner,)).fetchone()
            if not visible(app, identity[0] if identity else ''):
                raise GhostLabError('document_not_found', 'Brak dokumentu.', 404)
            if app.get('published') is False:
                raise GhostLabError('publication_withdrawn', 'Dokument wycofano ze sprzedaży.')
            if not template_available('ptk_document', 'runtime') or not runtime_actor_allowed(owner):
                raise GhostLabError('document_disabled', 'Pobieranie dokumentów jest wyłączone.')
            artifact = (app.get('metadata') or {}).get('artifact') or {}
            if not runtime_artifact_ready(artifact):
                raise GhostLabError('document_build_invalid', 'Dokument wymaga aktualnej kompilacji.')
            apply_price(app)
            if data.get('expected_artifact_id') != app['artifact_id'] or type(data.get('expected_price')) is not int or data['expected_price'] != app['price']:
                raise GhostLabError('offer_changed', 'Oferta zmieniła się. Odśwież i potwierdź pobranie.')
            previous = conn.execute('SELECT 1 FROM ghostlab_document_copies WHERE owner=? AND artifact_id=?',
                                    (owner, app['artifact_id'])).fetchone()
            receipt = 'ptk:' + owner + ':' + app['artifact_id']
            author, price = app['creator_username'], app['price']
            if not previous:
                if conn.execute('SELECT count(*) FROM ghostlab_document_copies WHERE owner=?', (owner,)).fetchone()[0] >= 1000:
                    raise GhostLabError('document_limit', 'Osiągnięto limit 1000 wydań dokumentów.')
                if price and author != owner:
                    wallet.transfer(owner, author, price, transaction_key=receipt,
                                    note='googleplex:' + app_id, source='googleplex.ptk', conn=conn)
                conn.execute('INSERT INTO ghostlab_document_copies VALUES(?,?,?,?,?,?,?,?)',
                             (owner, app_id, app['artifact_id'], app['name'], author,
                              app['source_build_version'], price, now()))
                services['player_inventory_store'].record_catalog_download(app_id, receipt, conn=conn)
                for username in {owner, author}:
                    balance = conn.execute('SELECT balance FROM wallet_balances WHERE username=?', (username,)).fetchone()
                    if balance:
                        deltas.record_change(username, 'wallet', 'wallet.balance_changed',
                            {'balance':balance[0], 'currency':'HC'}, dedupe_key=receipt+':'+username, conn=conn)
                services['system_message_store'].add_message(owner, {
                    'id':receipt, 'title':'Dokument PTK', 'text':'Pobrano dokument do Pliki → Dokumenty.',
                    'type':'success'}, conn=conn)
            balance = conn.execute('SELECT balance FROM wallet_balances WHERE username=?', (owner,)).fetchone()
        return dict(status='success', duplicate=bool(previous), hackcoins=balance[0] if balance else 0,
                    product={'id':app_id, 'product_type':'ptk_document'}, document_id=app['artifact_id'],
                    message='Dokument jest dostępny w Pliki → Dokumenty.')
