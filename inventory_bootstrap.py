"""Inventory creation and explicit offline repair; never a runtime read fallback."""
import json


INVENTORY_TABLES = ('player_storage', 'player_apps', 'player_tool_files',
                    'player_data_files', 'player_data_file_tombstones')


def inventory_state(conn, username):
    return {table: bool(conn.execute(f'SELECT 1 FROM {table} WHERE username=? LIMIT 1',
                                    (username,)).fetchone()) for table in INVENTORY_TABLES}


def prepare_inventory(profile):
    from database import PlayerInventoryStore as Store, dumps_json, utc_now
    now = utc_now()
    apps, tools, data = {}, {}, {}
    for app in profile.get('apps') or []:
        if isinstance(app, dict):
            app_id = Store._app_id(app)
            apps[app_id] = (app_id, dumps_json(app), Store._clean_text(app.get('status'), 'installed'), now)
    files = profile.get('files') if isinstance(profile.get('files'), dict) else {}
    for tool in files.get('tools') or []:
        tool_id = Store._tool_id(tool)
        payload = tool if isinstance(tool, dict) else {'name': tool_id, 'file': tool_id}
        tools[tool_id] = (tool_id, Store._clean_text(payload.get('app_id') or payload.get('source_app_id')), dumps_json(payload), now)
    # Only gameplay folders consumed by the bounded FM endpoint. Static help,
    # creator projects and PTK documents have separate authoritative stores.
    for folder in ('gps', 'device', 'audio', 'camera', 'atm', 'credentials', 'financial', 'personal', 'network', 'vehicle'):
        for item in files.get(folder) or []:
            if not isinstance(item, dict):
                raise ValueError('unsupported_legacy_file')
            file_id = Store._data_file_id(item)
            if not file_id or file_id in data:
                raise ValueError('ambiguous_legacy_file')
            payload = dict(item, id=file_id, file_category=folder)
            operation = Store._clean_text(item.get('source_operation_id') or item.get('operation_id'))
            data[file_id] = (file_id, folder, operation, dumps_json(payload),
                            Store._clean_text(item.get('market_status'), 'not_listed'),
                            Store._clean_text(item.get('created_at'), now), now)
    storage = Store._storage_from_profile(profile)
    return {'apps': list(apps.values()), 'tools': list(tools.values()), 'data': list(data.values()),
            'storage': (storage['capacity'], storage['used'], storage['unit'], dumps_json(storage['modifiers']), now)}


def insert_inventory(conn, username, prepared):
    # No upsert: concurrent creation or partial canonical data must not be reset.
    if any(inventory_state(conn, username).values()):
        raise ValueError('inventory_already_or_partially_initialized')
    conn.executemany('''INSERT INTO player_apps
        (username,app_id,app_json,status,version,updated_at) VALUES (?,?,?,?,1,?)''',
        [(username, *row) for row in prepared['apps']])
    conn.executemany('''INSERT INTO player_tool_files
        (username,tool_id,app_id,tool_json,version,updated_at) VALUES (?,?,?,?,1,?)''',
        [(username, *row) for row in prepared['tools']])
    conn.executemany('''INSERT INTO player_data_files
        (username,file_id,folder,operation_id,file_json,market_status,version,created_at,updated_at)
        VALUES (?,?,?,?,?,?,1,?,?)''', [(username, *row) for row in prepared['data']])
    conn.execute('''INSERT INTO player_storage
        (username,capacity,used,unit,modifiers_json,version,updated_at) VALUES (?,?,?,?,?,1,?)''',
        (username, *prepared['storage']))


def repair_missing_inventory(db_path, username, *, apply=False):
    """Operator-only exact-account repair from integrity-verified evidence."""
    from database import db_connect, profile_payload_checksum
    with db_connect(db_path) as conn:
        state = inventory_state(conn, username)
        if state['player_storage']:
            return {'username': username, 'status': 'already_initialized'}
        if any(state.values()):
            return {'username': username, 'status': 'blocked', 'reason': 'partial_inventory_requires_review'}
        row = conn.execute('''SELECT profile_json,profile_revision,profile_checksum,profile_integrity_status
                              FROM users WHERE username=?''', (username,)).fetchone()
    if not row:
        return {'username': username, 'status': 'blocked', 'reason': 'unknown_account'}
    profile = json.loads(row['profile_json'])
    if row['profile_integrity_status'] != 'valid' or profile_payload_checksum(profile) != row['profile_checksum']:
        return {'username': username, 'status': 'blocked', 'reason': 'profile_integrity'}
    prepared = prepare_inventory(profile)
    result = {'username': username, 'status': 'ready', 'apps': len(prepared['apps']),
              'tools': len(prepared['tools']), 'data_files': len(prepared['data'])}
    if not apply:
        return result
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute('SELECT profile_revision,profile_checksum,profile_integrity_status FROM users WHERE username=?', (username,)).fetchone()
        if not current or tuple(current) != (row['profile_revision'], row['profile_checksum'], row['profile_integrity_status']):
            raise ValueError('profile_changed_retry_audit')
        insert_inventory(conn, username, prepared)
    return dict(result, status='applied')
