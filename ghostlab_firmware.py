"""Paid single attempts, permanent effects and account-scoped crash recovery."""
import json
import secrets
import time

from flask import g, jsonify, request, session
from database import db_connect, utc_now, ProfileWriteError
from ghostlab_store import GhostLabError, digest
from ghostlab_products import published_product, resolve, runtime_artifact_ready
from ghostlab_registry import template_available, runtime_actor_allowed
from response_network.capabilities import require_targeting_allowed

DISK_LIMIT_MB = 2 * 1024 * 1024
SCAN_LIMIT_M = 30000
COOLDOWN_SECONDS = 24 * 3600
RESTART_SECONDS = 8


class FirmwareCrashed(ProfileWriteError):
    pass


def state(conn, actor):
    row = conn.execute('SELECT * FROM ghostlab_firmware_state WHERE username=?', (actor,)).fetchone()
    return dict(row) if row else dict(username=actor, scan_bonus=0, cooldown_until=0, crash_id='', restart_after=0)


def scan_range(conn, actor, base):
    # Add firmware only to scans, never to the shared targeting/action radius.
    return max(base, min(SCAN_LIMIT_M, base + state(conn, actor)['scan_bonus']))


def require_ready(conn, actor):
    current = state(conn, actor)
    if current['crash_id']:
        raise FirmwareCrashed('Firmware crash: wymagany restart systemu.')
    if current['cooldown_until'] > time.time():
        raise GhostLabError('firmware_cooldown', 'Firmware: kolejna próba po upływie 24 godzin od poprzedniej.', 409)


def remaining(conn, actor, policy, services):
    storage = conn.execute('SELECT capacity,used,unit FROM player_storage WHERE username=?', (actor,)).fetchone()
    caps = services['capability_projection_store'].get_capabilities(actor, conn=conn)
    if not storage or storage['unit'] != 'MB' or not caps:
        raise GhostLabError('firmware_state_unavailable', 'Brak kanonicznych parametrów systemu.', 409)
    radius = scan_range(conn, actor, caps['action_range'])
    return dict(disk_mb=max(0, min(policy['disk_mb'], DISK_LIMIT_MB - storage['capacity'])),
                scan_m=max(0, min(policy['scan_m'], SCAN_LIMIT_M - radius)),
                storage=dict(storage), scan_range_m=radius)


def offer(conn, app_id):
    product = published_product(conn, app_id)
    if not product or product.get('template_id') != 'firmware_update' or product.get('published') is False:
        raise GhostLabError('publication_withdrawn', 'Firmware niedostępny w sprzedaży.', 409)
    row = conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE artifact_id=?', (product['artifact_id'],)).fetchone()
    artifact = json.loads(row[0]) if row else {}
    if not runtime_artifact_ready(artifact):
        raise GhostLabError('firmware_build_unavailable', 'Firmware wymaga aktualnego buildu.', 409)
    return dict(product, policy=artifact['blueprint_snapshot'], policy_version=artifact['policy_version'])


def enabled(actor):
    if not template_available('firmware_update', 'runtime') or not runtime_actor_allowed(actor):
        raise GhostLabError('runtime_disabled', 'Runtime firmware jest wyłączony.', 403)


def purchase_result(conn, actor, receipt, inventory, duplicate=False):
    snapshot = inventory.snapshot(actor, conn=conn)
    balance = conn.execute('SELECT balance FROM wallet_balances WHERE username=?', (actor,)).fetchone()
    return dict(status='success', success=True, receipt=receipt, duplicate=duplicate,
                hackcoins=balance[0] if balance else 0, apps=snapshot['apps'], files=snapshot['files'],
                storage=snapshot['storage'], message='Próba firmware jest opłacona. Uruchom aplikację z pulpitu.')


def purchase(actor, app_id, body, services):
    enabled(actor)
    key = body.get('client_action_key')
    if not isinstance(key, str) or not 1 <= len(key) <= 180:
        raise GhostLabError('purchase_key_required', 'Brak identyfikatora zakupu.', 400)
    receipt = 'firmware:' + digest([actor, key])
    inventory = services['player_inventory_store']
    with db_connect(inventory.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        old = conn.execute('SELECT * FROM ghostlab_firmware_attempts WHERE receipt=?', (receipt,)).fetchone()
        if old:
            if (old['username'], old['app_id'], old['artifact_id'], old['price']) != (actor, app_id, body.get('expected_artifact_id'), body.get('expected_price')):
                raise GhostLabError('purchase_key_conflict', 'Identyfikator dotyczy innego zakupu.', 409)
        else:
            require_ready(conn, actor)
            require_targeting_allowed(conn, actor)
            pending = conn.execute('SELECT * FROM ghostlab_firmware_attempts WHERE username=? AND result_json IS NULL', (actor,)).fetchone()
            if pending:
                if pending['app_id'] == app_id and not inventory.has_app(actor, app_id, conn=conn):
                    restored = json.loads(pending['offer_json'])
                    inventory.install_app_with_conn(conn, actor, restored, purchase_key=pending['receipt'])
                    services['delta_bus'].record_change(actor, 'apps', 'apps.app_installed',
                        dict(app=restored, app_id=app_id), conn=conn)
                    return purchase_result(conn, actor, pending['receipt'], inventory, duplicate=True)
                raise GhostLabError('firmware_pending', 'Masz już zakupioną próbę. Wykorzystaj ją przed kolejnym zakupem.', 409)
            product = offer(conn, app_id)
            if product['artifact_id'] != body.get('expected_artifact_id') or product['price'] != body.get('expected_price'):
                raise GhostLabError('offer_changed', 'Oferta się zmieniła. Odśwież przed zakupem.', 409)
            gains = remaining(conn, actor, product['policy'], services)
            if not gains['disk_mb'] and not gains['scan_m']:
                raise GhostLabError('firmware_limits', 'Osiągnięto oba limity firmware: 2 TB i 30 km.', 409)
            identity = services['identity_projection_store'].get_creator_identity(actor, conn=conn)
            caps = services['capability_projection_store'].get_capabilities(actor, conn=conn)
            error = services['validate_app_install_requirements'](product, {**(identity or {}), **(caps or {})})
            if error:
                raise GhostLabError('requirements_not_met', error, 400)
            payee = product['creator_username']
            if product['price'] and payee != actor:
                services['wallet_balance_store'].transfer(actor, payee, product['price'], transaction_key=receipt,
                    note='googleplex:' + app_id, source='googleplex.firmware', conn=conn)
            if not inventory.has_app(actor, app_id, conn=conn):
                inventory.install_app_with_conn(conn, actor, product, purchase_key=receipt)
            conn.execute('INSERT INTO ghostlab_firmware_attempts VALUES (?,?,?,?,?,?,NULL,?)',
                         (receipt, actor, app_id, product['artifact_id'], product['price'], json.dumps(product), utc_now()))
            inventory.record_catalog_download(app_id, receipt, conn=conn)
            for who in {actor, payee}:
                balance = conn.execute('SELECT balance FROM wallet_balances WHERE username=?', (who,)).fetchone()
                if balance:
                    services['delta_bus'].record_change(who, 'wallet', 'wallet.balance_changed',
                        dict(balance=balance[0], currency='HC'), dedupe_key=receipt + ':' + who, conn=conn)
            services['delta_bus'].record_change(actor, 'apps', 'apps.app_installed',
                dict(app=product, app_id=app_id), dedupe_key=receipt + ':app', conn=conn)
        return purchase_result(conn, actor, receipt, inventory, duplicate=bool(old))


def execute(actor, app_id, receipt, services):
    with db_connect(services['player_inventory_store'].db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        attempt = conn.execute('SELECT * FROM ghostlab_firmware_attempts WHERE receipt=? AND username=? AND app_id=?',
                               (receipt, actor, app_id)).fetchone()
        if not attempt:
            raise GhostLabError('firmware_purchase_required', 'Najpierw kup próbę firmware.', 409)
        if attempt['result_json']:
            return dict(json.loads(attempt['result_json']), duplicate=True)
        enabled(actor)
        require_ready(conn, actor)
        require_targeting_allowed(conn, actor)
        installed = resolve(conn, actor, app_id, [], launch_modes=('own_system',))
        if not installed or not installed['runtime_enabled'] or installed['template_id'] != 'firmware_update':
            raise GhostLabError('firmware_not_installed', 'Zainstaluj firmware przed uruchomieniem.', 409)
        purchased = json.loads(attempt['offer_json'])
        policy = purchased['policy']  # Purchase pins the version; free updates never change a paid attempt.
        gains = remaining(conn, actor, policy, services)
        if not gains['disk_mb'] and not gains['scan_m']:
            raise GhostLabError('firmware_limits', 'Osiągnięto oba limity. Nie zużyto próby.', 409)
        roll = secrets.randbelow(10000)
        succeeded = roll < policy['success_percent'] * 100
        now = time.time()
        current = state(conn, actor)
        disk = gains['disk_mb'] if succeeded else 0
        scan = gains['scan_m'] if succeeded else 0
        crash_id = '' if succeeded else receipt
        if crash_id:
            conn.execute('DELETE FROM ghostlab_scanner_leases WHERE username=?', (actor,))
        conn.execute('''INSERT INTO ghostlab_firmware_state VALUES (?,?,?,?,?)
            ON CONFLICT(username) DO UPDATE SET scan_bonus=excluded.scan_bonus,
            cooldown_until=excluded.cooldown_until, crash_id=excluded.crash_id, restart_after=excluded.restart_after''',
            (actor, current['scan_bonus'] + scan, now + COOLDOWN_SECONDS, crash_id, now + RESTART_SECONDS if crash_id else 0))
        if disk:
            conn.execute('UPDATE player_storage SET capacity=capacity+?,version=version+1,updated_at=? WHERE username=?',
                         (disk, utc_now(), actor))
        result = dict(success=True, succeeded=succeeded, receipt=receipt, artifact_id=attempt['artifact_id'],
            policy_version=purchased['policy_version'], chance=policy['success_percent'], roll=roll,
            disk_mb=disk, scan_m=scan, scan_range_m=gains['scan_range_m'] + scan,
            storage=dict(gains['storage'], capacity=gains['storage']['capacity'] + disk),
            cooldown_until=now + COOLDOWN_SECONDS, crash_id=crash_id, duplicate=False,
            message='Firmware zainstalowany — trwałe bonusy zapisane.' if succeeded else 'Flashowanie nieudane. Crash systemu — wymagany restart.')
        conn.execute('UPDATE ghostlab_firmware_attempts SET result_json=? WHERE receipt=?', (json.dumps(result), receipt))
        services['delta_bus'].record_change(actor, 'firmware', 'firmware.result', result, dedupe_key=receipt + ':result', conn=conn)
        services['system_message_store'].add_message(actor, dict(title='Aktualizacja firmware', text=result['message'],
            type='success' if succeeded else 'warning', dedupe_key=receipt + ':message'), source='ghostlab.firmware', conn=conn)
        return result


def exempt():
    if not session.get('user') or request.method == 'OPTIONS' or request.endpoint == 'static':
        return True
    if request.path in {'/', '/desktop', '/logout', '/session/recover', '/api/state/changes', '/api/ghostnetwork/show',
                        '/api/firmware/state', '/api/firmware/restart'}:
        return True
    return request.path.startswith('/api/ghostlab/firmware/')


def guard(conn, actor):
    if exempt() or not actor:
        return
    # Shared transaction hook may run on other databases too.
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='ghostlab_firmware_state'").fetchone():
        return
    if state(conn, actor)['crash_id']:
        g.firmware_commit_denied = True
        raise FirmwareCrashed('Firmware crash: wymagany restart systemu.')


def register(app, services):
    def actor():
        if not session.get('user'):
            raise GhostLabError('authentication_required', 'Zaloguj się.', 401)
        return session['user']

    def crashed_response():
        from ghostlab_messages import message
        return jsonify(success=False, error='firmware_restart_required', message='Crash firmware — uruchom ponownie system.',
                       message_i18n=message('lab.service.firmware_failure')), 423

    @app.errorhandler(FirmwareCrashed)
    def crashed(_error):
        return crashed_response()

    @app.after_request
    def preserve_firmware_rejection(response):
        if request.path.startswith(('/api/firmware/', '/api/ghostlab/firmware/')):
            response.headers['Cache-Control'] = 'private, no-store'
        return app.make_response(crashed_response()) if getattr(g, 'firmware_commit_denied', False) else response

    @app.before_request
    def crash_guard():
        if not exempt():
            with db_connect(services['player_inventory_store'].db_path) as conn:
                guard(conn, session.get('user'))

    @app.get('/api/firmware/state')
    def firmware_state():
        with db_connect(services['player_inventory_store'].db_path) as conn:
            current = state(conn, actor())
        response = jsonify(success=True, **current, server_time=time.time())
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    @app.post('/api/firmware/restart')
    def firmware_restart():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise GhostLabError('invalid_request', 'Nieprawidłowe żądanie.', 400)
        with db_connect(services['player_inventory_store'].db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current = state(conn, actor())
            if current['crash_id'] and (body.get('crash_id') != current['crash_id'] or time.time() < current['restart_after']):
                raise GhostLabError('restart_pending', 'Trwa odzyskiwanie systemu. Spróbuj za chwilę.', 409)
            conn.execute("UPDATE ghostlab_firmware_state SET crash_id='',restart_after=0 WHERE username=?", (actor(),))
        return jsonify(success=True)

    @app.route('/api/ghostlab/firmware/<app_id>', methods=['GET', 'POST'])
    def firmware(app_id):
        username = actor()
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise GhostLabError('invalid_request', 'Nieprawidłowe żądanie.', 400)
        if request.method == 'POST':
            receipt = body.get('receipt')
            if not isinstance(receipt, str) or len(receipt) > 180:
                raise GhostLabError('invalid_receipt', 'Nieprawidłowa próba.', 400)
            return jsonify(execute(username, app_id, receipt, services))
        enabled(username)
        with db_connect(services['player_inventory_store'].db_path) as conn:
            conn.execute('BEGIN')
            current = state(conn, username)
            pending = conn.execute('SELECT receipt,offer_json FROM ghostlab_firmware_attempts WHERE username=? AND app_id=? AND result_json IS NULL', (username, app_id)).fetchone()
            latest = conn.execute('SELECT result_json FROM ghostlab_firmware_attempts WHERE username=? AND app_id=? AND result_json IS NOT NULL ORDER BY created_at DESC LIMIT 1', (username, app_id)).fetchone()
            available = None
            try:
                available = offer(conn, app_id)
            except GhostLabError:
                if not pending and not latest:
                    raise
            product = json.loads(pending['offer_json']) if pending else available
            gains = remaining(conn, username, product['policy'], services) if product else None
            any_pending = conn.execute('SELECT 1 FROM ghostlab_firmware_attempts WHERE username=? AND result_json IS NULL', (username,)).fetchone()
            return jsonify(success=True, state=current, server_time=time.time(),
                pending=pending['receipt'] if pending else None, policy=product['policy'] if product else None,
                pending_offer=json.loads(pending['offer_json']) if pending else None,
                gains=gains, available=available, has_pending=bool(any_pending),
                last_result=json.loads(latest[0]) if latest else None)

    @app.post('/api/ghostlab/firmware/<app_id>/purchase')
    def firmware_purchase(app_id):
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise GhostLabError('invalid_request', 'Nieprawidłowe żądanie.', 400)
        return jsonify(purchase(actor(), app_id, body, services))
