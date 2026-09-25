"""Installed PvP products resolved from inventory and immutable published builds."""
import json
from database import db_connect, ProfileRecoveryRequired
from ghostlab_registry import get_template, artifact_compatible, template_available, PRO_TOOL_GLAB, runtime_actor_allowed, validate_fields


def runtime_artifact_ready(artifact):
    return (artifact.get('template_id') == 'system_log_reader'
            and artifact.get('runtime_revision') == 1
            and artifact_compatible(artifact, 'system_log_reader')
            and not validate_fields('system_log_reader', artifact.get('blueprint_snapshot')))


def runtime_status(artifact):
    return 'player_hack_access' if runtime_artifact_ready(artifact) else 'pending_custom_runtime'


def published_product(conn, app_id):
    row = conn.execute('''SELECT g.app_json,g.owner,g.artifact_id,p.id,b.artifact_json FROM ghostlab_publications g
        JOIN ghostlab_projects p ON p.app_id=g.app_id AND p.owner=g.owner
        JOIN ghostlab_builds b ON b.project_id=p.id AND b.artifact_id=g.artifact_id AND b.published=1
        WHERE g.app_id=?''', (app_id,)).fetchone()
    if not row:
        return None
    app, artifact = json.loads(row['app_json']), json.loads(row['artifact_json'])
    if (app.get('creator_username') != row['owner'] or app.get('source_project_id') != row['id']
            or app.get('artifact_id') != row['artifact_id'] or not artifact_compatible(artifact, app.get('template_id'))):
        return None
    return app


def resolve(conn, username, app_id, builtins):
    row = conn.execute("SELECT app_json,version FROM player_apps WHERE username=? AND app_id=? AND status!='uninstalled'",
                       (username, app_id)).fetchone()
    if not row:
        return None
    installed = json.loads(row['app_json'])
    builtin = next((tool for tool in builtins if tool['id'] == app_id), None)
    if builtin:
        if not PRO_TOOL_GLAB.get(app_id):
            return None
        return dict(builtin, installed=True, enabled=True, runtime_enabled=True, family_id=app_id,
                    installed_version=row['version'], artifact_id=None)
    artifact_id = installed.get('artifact_id')
    if not artifact_id:
        return None
    # Published history is sufficient even when sale/creation is withdrawn. Never trust type/name/flags.
    source = conn.execute('''SELECT p.owner,p.app_id,p.id,b.artifact_json FROM ghostlab_projects p
        JOIN ghostlab_builds b ON b.project_id=p.id WHERE p.app_id=? AND b.artifact_id=? AND b.published=1''',
        (app_id, artifact_id)).fetchone()
    if not source or installed.get('creator_username') != source['owner'] or installed.get('source_project_id') != source['id']:
        return None
    artifact = json.loads(source['artifact_json'])
    definition = get_template(artifact.get('template_id'))
    if not definition or definition['launch_mode'] != 'player_hack_access':
        return None
    branding = artifact.get('branding_snapshot') or {}
    compatible = artifact_compatible(artifact, definition['id'])
    runtime = (runtime_artifact_ready(artifact) and template_available(definition['id'], 'runtime')
               and runtime_actor_allowed(username))
    reason = 'Runtime potomka jeszcze niedostępny.'
    if not compatible:
        reason = 'Wersja kontraktu niedostępna.'
    elif definition['id'] == 'system_log_reader':
        if not runtime_artifact_ready(artifact):
            reason = 'Build wymaga ponownej kompilacji, publikacji i aktualizacji do runtime.'
        elif not template_available(definition['id'], 'runtime'):
            reason = 'Runtime System Log Reader jest wyłączony na serwerze.'
        elif not runtime_actor_allowed(username):
            reason = 'Runtime jest dostępny tylko dla aktywowanych kont testowych.'
    return {'id': app_id, 'name': branding.get('name') or artifact.get('project_name') or app_id,
            'icon': branding.get('icon') or definition['icon'],
            'description': branding.get('description') or definition['description'],
            'installed': True, 'enabled': runtime, 'runtime_enabled': runtime,
            'family_id': definition.get('source_tool_id') or definition['id'], 'template_id': definition['id'],
            'artifact_id': artifact_id, 'installed_version': artifact['version'],
            'blueprint': artifact.get('blueprint_snapshot', {}), 'policy_version': artifact.get('policy_version'),
            'disabled_reason': '' if runtime else reason}


def installed_products(db_path, username, builtins):
    with db_connect(db_path) as conn:
        rows = conn.execute("SELECT app_id FROM player_apps WHERE username=? AND status!='uninstalled' ORDER BY app_id LIMIT 1001", (username,)).fetchall()
        if len(rows) > 1000:
            raise ProfileRecoveryRequired('Player application limit exceeded')
        return [product for row in rows if (product := resolve(conn, username, row['app_id'], builtins))]
