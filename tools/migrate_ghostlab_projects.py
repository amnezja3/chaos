"""Offline, explicit-account migration. Dry-run by default; never imports run.py."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ghostlab_policy import validate_ghostlab_blueprint
from ghostlab_store import GhostLabStore, digest, encoded, now
from database import db_connect


def migrate_account(conn, owner, apply=False):
    row = conn.execute("""SELECT profile_revision, profile_checksum,
        json_extract(profile_json,'$.files.pro_system_projects') AS projects
        FROM users WHERE username=?""", (owner,)).fetchone()
    if not row:
        return dict(owner=owner, status='blocked', errors=['account_missing'])
    raw = row['projects']
    projects = json.loads(raw) if raw else []
    signature = digest(projects)
    result = dict(owner=owner, status='would_migrate', source_hash=signature,
                  source_revision=row['profile_revision'], projects=[], errors=[])
    if not isinstance(projects, list) or len(projects) > GhostLabStore.MAX_PROJECTS:
        return dict(result, status='blocked', errors=['invalid_or_oversized_project_list'])
    resource = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
    catalog = json.loads(resource['value_json']) if resource else []
    seen_ids, seen_apps, planned = set(), set(), []
    for legacy in projects:
        if not isinstance(legacy, dict) or not legacy.get('id'):
            result['errors'].append('invalid_legacy_project')
            continue
        legacy_id = str(legacy['id'])
        project_id = 'glp_' + uuid.uuid5(uuid.NAMESPACE_URL, f'chaos:ghostlab:{owner}:{legacy_id}').hex
        app_id = legacy.get('googleplex_app_id') or 'ghostlab_' + uuid.uuid5(uuid.NAMESPACE_URL, project_id).hex
        validation = validate_ghostlab_blueprint(legacy.get('template_id') or '', legacy.get('blueprint', {}))
        # Empty custom notes are valid saved sketches, not executable builds.
        empty_sketch = not legacy.get('template_id') and legacy.get('blueprint') == {'notes': ''}
        if not validation['valid'] and not empty_sketch:
            result['errors'].append(f'{legacy_id}: invalid_blueprint: {validation["errors"]}')
        if legacy_id in seen_ids or app_id in seen_apps:
            result['errors'].append(f'{legacy_id}: duplicate_identity')
        seen_ids.add(legacy_id); seen_apps.add(app_id)
        matching = [a for a in catalog if a.get('id') == app_id]
        if legacy.get('googleplex_app_id') and (len(matching) != 1 or
                matching[0].get('creator_username') != owner or
                matching[0].get('source_project_id') != legacy_id or
                not matching[0].get('ghostlab_generated')):
            result['errors'].append(f'{legacy_id}: publication_owner_or_source_conflict')
        project = dict(legacy, id=project_id, owner=owner, revision=1, schema_version=1,
                       googleplex_app_id=app_id, artifact={}, builds=[], status='draft', updated_at=now())
        # Preserve evidence, never promote unvalidated legacy builds to executable artifacts.
        project['legacy_id'] = legacy_id
        evidence = {'builds': legacy.get('builds', []), 'artifact': legacy.get('artifact', {})}
        result['projects'].append(dict(legacy_id=legacy_id, project_id=project_id, app_id=app_id,
                                       old_builds=len(evidence['builds']), requires_compile=True))
        planned.append((project, evidence))
    tables = conn.execute("SELECT 1 FROM sqlite_master WHERE name='ghostlab_migrations'").fetchone()
    if tables:
        previous = conn.execute('SELECT * FROM ghostlab_migrations WHERE owner=?', (owner,)).fetchone()
        if previous and previous['status'] == 'complete':
            return dict(result, status='already_migrated' if previous['source_hash'] == signature else 'blocked',
                        errors=[] if previous['source_hash'] == signature else ['legacy_changed_after_migration'])
        for project, _ in planned:
            claimed = conn.execute('SELECT owner FROM ghostlab_projects WHERE app_id=? OR id=?',
                                   (project['googleplex_app_id'], project['id'])).fetchone()
            if claimed:
                result['errors'].append(f'{project["legacy_id"]}: identity_already_claimed')
    if result['errors']:
        return dict(result, status='blocked')
    if apply:
        for project, evidence in planned:
            conn.execute('INSERT INTO ghostlab_projects(id,owner,app_id,revision,project_json,updated_at) VALUES(?,?,?,?,?,?)',
                         (project['id'],owner,project['googleplex_app_id'],1,encoded(project),now()))
            conn.execute('INSERT INTO ghostlab_legacy_ids VALUES(?,?,?)', (owner,project['legacy_id'],project['id']))
            conn.execute('INSERT INTO ghostlab_meta(key,value) VALUES(?,?)',
                         ('legacy-builds:' + project['id'], encoded(evidence)))
        conn.execute('''INSERT INTO ghostlab_migrations(owner,status,source_hash,updated_at) VALUES(?,'complete',?,?)
            ON CONFLICT(owner) DO UPDATE SET status='complete',source_hash=excluded.source_hash,updated_at=excluded.updated_at''',
                     (owner,signature,now()))
        result['status'] = 'migrated'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--user', action='append', required=True, help='Explicit account; repeat for up to 100 accounts')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    owners = list(dict.fromkeys(args.user))
    if len(owners) > 100:
        parser.error('Maximum 100 explicit accounts per invocation')
    if not Path(args.db).is_file():
        parser.error('Database must already exist')
    if args.apply:
        GhostLabStore(args.db)
        results = []
        for owner in owners:
            with db_connect(args.db) as conn:
                conn.execute('BEGIN IMMEDIATE')
                results.append(migrate_account(conn, owner, apply=True))
    else:
        conn = sqlite3.connect(Path(args.db).resolve().as_uri() + '?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        try:
            results = [migrate_account(conn, owner) for owner in owners]
        finally:
            conn.close()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if any(r['status'] == 'blocked' for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
