"""Short-lived, session-bound activation of an installed map-scanner overlay."""
import secrets
import time
from flask import g, jsonify, request, session
from database import db_connect
from ghostlab_store import GhostLabError
from ghostlab_products import resolve
from ghostlab_scanner_catalog import presentation
from response_network.capabilities import require_targeting_allowed

LEASE_SECONDS = 35


def generation():
    return str(getattr(g, 'session_generation', '') or session.get('session_generation') or '')


def active(conn, actor, gen, token):
    if not isinstance(token, str) or not 16 <= len(token) <= 100:
        return None
    row = conn.execute('SELECT * FROM ghostlab_scanner_leases WHERE username=? AND generation=? AND token=? AND expires>?',
                       (actor, gen, token, time.time())).fetchone()
    if not row:
        return None
    product = resolve(conn, actor, row['app_id'], [], launch_modes=('own_system',))
    if (not product or product['template_id'] != 'deep_scanner' or not product['runtime_enabled']
            or product['artifact_id'] != row['artifact_id']):
        return None
    return product


def scan_options(path, actor, gen, token):
    with db_connect(path) as conn:
        require_targeting_allowed(conn, actor)
        product = active(conn, actor, gen, token)
    if not product:
        raise GhostLabError('scanner_inactive', 'Nakładka skanera wygasła. Otwórz ją ponownie.', 409)
    def still_active():
        with db_connect(path) as conn:
            try:
                require_targeting_allowed(conn, actor)
                from ghostlab_firmware import state
                if state(conn, actor)['crash_id']:
                    return False
                return bool(active(conn, actor, gen, token))
            except Exception:
                return False
    return dict(extra_retries=int(product['blueprint']['extra_retries']), extra_timeout=int(product['blueprint']['extra_timeout']),
                still_active=still_active)


def register(app, services):
    @app.post('/api/ghostlab/scanner/<app_id>/activate')
    def activate_scanner(app_id):
        actor = session.get('user')
        if not actor:
            raise GhostLabError('authentication_required', 'Zaloguj się.', 401)
        body = request.get_json(silent=True)
        window = body.get('window_id') if isinstance(body, dict) else None
        if not isinstance(window, str) or not 8 <= len(window) <= 100 or not generation():
            raise GhostLabError('invalid_window', 'Brak identyfikatora okna/sesji.', 400)
        with db_connect(services['player_inventory_store'].db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            require_targeting_allowed(conn, actor)
            product = resolve(conn, actor, app_id, [], launch_modes=('own_system',))
            if not product or product['template_id'] != 'deep_scanner' or not product['runtime_enabled']:
                raise GhostLabError('scanner_unavailable', 'Skaner niezainstalowany lub runtime wyłączony.', 403)
            old = conn.execute('SELECT * FROM ghostlab_scanner_leases WHERE username=?', (actor,)).fetchone()
            if old and active(conn, actor, generation(), old['token']):
                if old['window_id'] != window or old['app_id'] != app_id:
                    previous = resolve(conn, actor, old['app_id'], [], launch_modes=('own_system',))
                    raise GhostLabError('scanner_busy', 'Najpierw zamknij aktywny skaner: ' + previous['name'], 409)
                token = old['token']
            else:
                token = secrets.token_urlsafe(24)
            conn.execute('INSERT OR REPLACE INTO ghostlab_scanner_leases VALUES (?,?,?,?,?,?,?)',
                         (actor, generation(), window, token, app_id, product['artifact_id'], time.time() + LEASE_SECONDS))
            return jsonify(success=True, token=token, ttl=LEASE_SECONDS, presentation=presentation(product))

    @app.post('/api/ghostlab/scanner/lease')
    def scanner_lease():
        actor = session.get('user')
        if not actor:
            raise GhostLabError('authentication_required', 'Zaloguj się.', 401)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get('token'), str) or len(body['token']) > 100:
            raise GhostLabError('invalid_lease', 'Nieprawidłowa aktywacja.', 400)
        with db_connect(services['player_inventory_store'].db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            if body.get('release') is True:
                conn.execute('DELETE FROM ghostlab_scanner_leases WHERE username=? AND generation=? AND token=?',
                             (actor, generation(), body['token']))
                return jsonify(success=True)
            require_targeting_allowed(conn, actor)
            product = active(conn, actor, generation(), body['token'])
            if not product:
                raise GhostLabError('scanner_inactive', 'Nakładka skanera wygasła.', 409)
            conn.execute('UPDATE ghostlab_scanner_leases SET expires=? WHERE username=? AND token=?',
                         (time.time() + LEASE_SECONDS, actor, body['token']))
            return jsonify(success=True, ttl=LEASE_SECONDS)
