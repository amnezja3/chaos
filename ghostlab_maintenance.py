"""Own-system executors: signed previews, canonical transactions, immutable receipts."""
import json
import math
import uuid

from flask import jsonify, request, session
from itsdangerous import URLSafeTimedSerializer, BadData
from database import db_connect, utc_now, ProfileWriteConflict
from ghostlab_products import resolve
from player_security_store import PlayerSecurityStore
from response_network.capabilities import require_targeting_allowed

TERMINAL = {'cancelled', 'canceled', 'done', 'completed', 'failed', 'expired', 'timeout', 'resolved', 'detected'}
OBJECT_FOLDERS = {'gps', 'device', 'personal', 'atm', 'financial', 'credentials', 'network', 'vehicle', 'audio'}


def cleanup_category(file, folder):
    # No tool/project/core directories; unknown data is protected by default.
    if folder == 'camera':
        return 'camera'
    if folder in OBJECT_FOLDERS:
        return 'objects'
    resources = file.get('resource_types') or []
    if folder == 'system' and resources == ['internal_recon_state']:
        return 'recon'
    if folder == 'system' and file.get('disposable') is True:
        return 'system'
    if folder == 'installers' and file.get('disposable') is True:
        return 'installers'
    return None


def candidates(conn, actor, blueprint, sellable):
    rows = conn.execute('''SELECT d.file_id,d.folder,d.operation_id,d.file_json,d.market_status,d.version,
        o.status AS operation_status FROM player_data_files d LEFT JOIN player_operations o
        ON o.operation_id=d.operation_id AND o.username=d.username
        WHERE d.username=? ORDER BY d.file_id LIMIT 5001''', (actor,)).fetchall()
    if len(rows) > 5000:
        raise ValueError('Przekroczono limit 5000 plików podglądu. Czyszczenie nie zostało wykonane.')
    result = []
    for row in rows:
        file = json.loads(row['file_json'])
        if not isinstance(file, dict):
            continue
        metadata = file.get('metadata') if isinstance(file.get('metadata'), dict) else {}
        category = cleanup_category(file, row['folder'])
        if not category or not blueprint.get(category):
            continue
        # Explicit unsellability AND market rules; not_listed alone grants nothing.
        if file.get('sellable') is not False or sellable(dict(file, market_status='not_listed')):
            continue
        if row['market_status'] not in {'not_listed', 'created'}:
            continue
        if any(file.get(key) or metadata.get(key) for key in ('protected', 'core', 'required', 'gameplay_required', 'app_id',
                                        'source_app_id', 'installed', 'purchased', 'googleplex_sellable',
                                        'ghost_exchange_sellable', 'generated', 'project_id', 'artifact_id')):
            continue
        if any(str(value) != row['operation_id'] for value in
               (file.get('operation_id'), file.get('source_operation_id'), metadata.get('operation_id')) if value):
            continue
        if row['operation_id'] and row['operation_status'] not in TERMINAL:
            continue
        size = file.get('file_size', 0)
        if type(size) not in (int, float) or not math.isfinite(size) or size < 0:
            continue
        result.append(dict(id=row['file_id'], version=row['version'], name=str(file.get('name') or row['file_id'])[:180],
                           size=int(round(size)), category=category))
        if len(result) == 250:
            break
    return result


def restore_preset(security, preset, builder, conflicts):
    updated = builder(security, preset)
    # Only existing keys, and the same conflict rules as manual switches.
    for key in updated:
        if updated[key] is True:
            for other in conflicts.get(key, []):
                if other in updated and updated[other] is True:
                    updated[other] = False
    return updated


def register(app, services):
    def signer():
        return URLSafeTimedSerializer(app.secret_key, salt='ghostlab-maintenance-v1')

    @app.route('/api/ghostlab/installed/<app_id>/maintenance', methods=['GET', 'POST'])
    def maintenance(app_id):
        actor = session.get('user')
        if not actor:
            return jsonify(success=False, error='Nie jesteś zalogowany.'), 401
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify(success=False, error='Nieprawidłowe żądanie.'), 400
        try:
            with db_connect(services['player_inventory_store'].db_path) as conn:
                conn.execute('BEGIN IMMEDIATE' if request.method == 'POST' else 'BEGIN')
                require_targeting_allowed(conn, actor)
                product = resolve(conn, actor, app_id, [], launch_modes=('own_system',))
                if not product or not product['runtime_enabled']:
                    return jsonify(success=False, error='Narzędzie niezainstalowane lub runtime wyłączony.'), 403
                kind, blueprint = product['template_id'], product['blueprint']
                security = PlayerSecurityStore(services['player_inventory_store'].db_path)
                if request.method == 'GET':
                    plan = dict(actor=actor, app=app_id, artifact=product['artifact_id'], action_id=uuid.uuid4().hex)
                    preview = dict(kind=kind)
                    if kind == 'file_cleanup':
                        files = candidates(conn, actor, blueprint, services['is_ghost_exchange_sellable'])
                        plan['files'] = [[f['id'], f['version']] for f in files]
                        preview.update(files=files, count=len(files), size=sum(f['size'] for f in files))
                    elif kind == 'security_restore':
                        state = security.get(actor, conn=conn)
                        plan['security_version'] = state['security_version']
                        preview['preset'] = blueprint['preset']
                    else:
                        preview['logs'] = [blueprint[f'log_{i}'] for i in range(1, 5)]
                    return jsonify(success=True, preview=preview, token=signer().dumps(plan))
                token = body.get('token')
                if not isinstance(token, str) or len(token) > 100000:
                    raise ValueError('Najpierw odśwież podgląd operacji.')
                plan = signer().loads(token, max_age=600)
                if (plan['actor'], plan['app'], plan['artifact']) != (actor, app_id, product['artifact_id']):
                    raise ValueError('Wersja aplikacji zmieniła się. Odśwież podgląd.')
                saved = conn.execute('SELECT result_json FROM ghostlab_maintenance_receipts WHERE username=? AND action_id=?',
                                     (actor, plan['action_id'])).fetchone()
                if saved:
                    return jsonify(**dict(json.loads(saved[0]), duplicate=True))
                result = dict(success=True, kind=kind, action_id=plan['action_id'], duplicate=False)
                if kind == 'file_cleanup':
                    approved = {key: version for key, version in plan['files']}
                    files = [f for f in candidates(conn, actor, blueprint, services['is_ghost_exchange_sellable'])
                             if approved.get(f['id']) == f['version']]
                    storage = conn.execute('SELECT used,capacity,unit FROM player_storage WHERE username=?', (actor,)).fetchone()
                    if not storage:
                        raise ValueError('Brak kanonicznego stanu dysku.')
                    size = sum(f['size'] for f in files)
                    if size > storage['used']:
                        raise ValueError('Niespójna zajętość dysku. Czyszczenie przerwane.')
                    for file in files:
                        conn.execute('DELETE FROM player_data_files WHERE username=? AND file_id=? AND version=?',
                                     (actor, file['id'], file['version']))
                        conn.execute('INSERT INTO player_data_file_tombstones VALUES (?,?,?)', (actor, file['id'], utc_now()))
                    if files:
                        conn.execute('UPDATE player_storage SET used=used-?,version=version+1,updated_at=? WHERE username=?',
                                     (size, utc_now(), actor))
                    result.update(removed_file_ids=[f['id'] for f in files], count=len(files), freed_mb=size,
                        storage=dict(storage, used=storage['used'] - size),
                        message=f'Usunięto {len(files)} plików. Zwolniono {size} MB.' if files else
                        ('Zakres zmienił się — odśwież podgląd.' if approved else 'System jest już czysty — nie ma czego usuwać.'))
                elif kind == 'security_restore':
                    before = security.get(actor, conn=conn)['security']
                    state = security.update(actor, lambda s: restore_preset(s, blueprint['preset'],
                        services['build_security_preset'], services['SECURITY_CONFLICTS']),
                        expected_version=plan['security_version'], conn=conn)
                    changed = [key for key in before if before[key] != state['security'][key]]
                    result.update(**state, changed=changed, preset=blueprint['preset'],
                        message=f'Zestaw {blueprint["preset"].upper()}: zmieniono {len(changed)} ustawień.' if changed else
                        'Zabezpieczenia są już zgodne z wybranym zestawem.')
                else:
                    result['message'] = 'Prezentacja aktualizacji zakończona. Parametry systemu pozostają bez zmian.'
                require_targeting_allowed(conn, actor)
                conn.execute('INSERT INTO ghostlab_maintenance_receipts VALUES (?,?,?,?,?)',
                             (actor, plan['action_id'], app_id, json.dumps(result, ensure_ascii=False), utc_now()))
                services['delta_bus'].record_change(actor, 'maintenance', 'maintenance.completed', result,
                    entity_id=app_id, dedupe_key='maintenance:' + plan['action_id'], conn=conn)
                return jsonify(**result)
        except BadData:
            return jsonify(success=False, error='Podgląd wygasł lub jest nieprawidłowy. Odśwież panel.'), 409
        except ProfileWriteConflict:
            return jsonify(success=False, error='Zabezpieczenia zostały zmienione. Odśwież podgląd i spróbuj ponownie.'), 409
        except ValueError as exc:
            return jsonify(success=False, error=str(exc)), 400
