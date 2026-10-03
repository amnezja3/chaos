"""Free, explicit edition replacement; an active installation is required."""
import json
from database import db_connect
from ghostlab_store import GhostLabError


def state(conn, actor, app_id):
    row = conn.execute("SELECT app_json FROM player_apps WHERE username=? AND app_id=? AND status='installed'",
                       (actor, app_id)).fetchone()
    if not row:
        raise GhostLabError('not_installed', 'Najpierw kup i zainstaluj aplikację.', 409)
    installed = json.loads(row[0])
    row = conn.execute('SELECT app_json FROM creator_publications WHERE app_id=?', (app_id,)).fetchone()
    available = json.loads(row[0]) if row else None
    if not installed.get('creator_contract_version'):
        if not (available and available.get('creator_legacy_project')) and not installed.get('creator_legacy_project'):
            raise GhostLabError('legacy_edition', 'Ta aplikacja nie ma wersjonowanego projektu.', 409)
        installed['version'] = installed.get('version') or 1
    if available and not available.get('published'):
        available = None
    return installed, available


def view(conn, actor, app_id):
    installed, available = state(conn, actor, app_id)
    return dict(installed_version=installed['version'], available_version=available['version'] if available else None,
                update_available=bool(available and available['version'] > installed['version']), update_price_hc=0)


def update(actor, app_id, expected, desired, inventory, delta_bus):
    from response_network.capabilities import require_targeting_allowed
    if type(expected) is not int or type(desired) is not int or desired < 1:
        raise ValueError('Wymagane numery zainstalowanej i docelowej wersji.')
    with db_connect(inventory.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        require_targeting_allowed(conn, actor)
        installed, available = state(conn, actor, app_id)
        if installed['version'] == desired:
            return dict(duplicate=True, **view(conn, actor, app_id))
        if installed['version'] != expected or not available or available['version'] != desired or desired <= expected:
            raise GhostLabError('edition_changed', 'Wersja zmieniła się. Odśwież ofertę.', 409)
        if available.get('creator_legacy_project'):
            from creator_legacy import validate_update
            validate_update(conn, installed, available)
        elif installed.get('creator_project_id') != available.get('creator_project_id'):
            raise GhostLabError('project_changed', 'Niezgodna tożsamość projektu.', 409)
        if not available.get('creator_legacy_project') and installed['creator_contract'] != available.get('creator_contract'):
            raise GhostLabError('mechanics_changed', 'Wydanie zmienia zamrożoną mechanikę.', 409)
        storage = conn.execute('SELECT capacity,used FROM player_storage WHERE username=?', (actor,)).fetchone()
        added = inventory._inventory_storage_size(available, app=True) - inventory._inventory_storage_size(installed, app=True)
        if not storage or (added > 0 and storage['used'] + added > storage['capacity']):
            raise ValueError('Brak miejsca na aktualizację.')
        removed = []
        inventory.uninstall_app(actor, app_id=app_id, conn=conn, removed_tools=removed)
        result = inventory.install_app_with_conn(conn, actor, dict(available, bounded_install=False),
                    purchase_key=installed.get('wallet_transaction_key') or f'creator:update:{app_id}:{desired}')
        tools = [json.loads(row[0]) for row in conn.execute(
            'SELECT tool_json FROM player_tool_files WHERE username=? AND app_id=?', (actor, app_id))]
        delta_bus.record_change(actor, 'apps', 'apps.app_installed',
            dict(app=result['app'], app_id=app_id, reason='creator_update',
                 removed_tool_ids=[item['tool_id'] for item in removed], updated_tools=tools),
            entity_id=app_id, dedupe_key=f'creator:update:{actor}:{app_id}:{desired}', conn=conn)
        delta_bus.record_change(actor, 'storage', 'storage.used_changed',
            dict(conn.execute('SELECT used,capacity,unit FROM player_storage WHERE username=?', (actor,)).fetchone()),
            entity_id=actor, dedupe_key=f'creator:update:storage:{actor}:{app_id}:{desired}', conn=conn)
        return dict(duplicate=False, **view(conn, actor, app_id))
