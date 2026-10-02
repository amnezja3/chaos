"""Offline, explicit-owner migration of historical creator publications.

Never reads player profiles or changes installed copies. The source is an export
of the canonical app_config resource. Ambiguous records require operator review.
"""
import argparse
import copy
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ghostlab_store import digest, encoded


def plan(catalog, owners):
    if not isinstance(catalog, list):
        raise ValueError('Catalog must be a JSON array.')
    owners = set(owners)
    if not owners or any(not isinstance(owner, str) or not owner.strip() for owner in owners):
        raise ValueError('An explicit, nonempty owner list is required.')
    ids, names = {}, {}
    for item in catalog:
        if isinstance(item, dict):
            ids.setdefault(item.get('id'), []).append(item)
            names.setdefault(str(item.get('name', '')).strip().casefold(), []).append(item)
    entries = []
    for item in catalog:
        if not isinstance(item, dict) or item.get('creator_username') not in owners:
            continue
        if not item.get('generated') or item.get('ghostlab_generated'):
            continue
        errors = []
        for key in ('id', 'name', 'creator_username', 'project_file'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append('missing_' + key)
        if len(ids.get(item.get('id'), [])) != 1:
            errors.append('duplicate_id')
        if len(names.get(str(item.get('name', '')).strip().casefold(), [])) != 1:
            errors.append('duplicate_name')
        if type(item.get('price')) is not int or item['price'] < 0:
            errors.append('invalid_price')
        if item.get('creator_contract_version'):
            errors.append('already_versioned')
        entries.append(dict(id=item.get('id'), owner=item.get('creator_username'),
            source_hash=digest(item), status='review' if errors else 'ready', errors=errors,
            # Exact snapshot: no normalizer, power roll, ID or price substitution.
            snapshot=copy.deepcopy(item)))
    return entries


def apply(store, entries):
    from database import db_connect
    results = []
    with db_connect(store.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('''CREATE TABLE IF NOT EXISTS creator_migration_receipts (
            app_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL)''')
        for entry in entries:
            if entry['status'] != 'ready':
                results.append(dict(id=entry['id'], status='review', errors=entry['errors']))
                continue
            previous = conn.execute('SELECT source_hash FROM creator_migration_receipts WHERE app_id=?',
                                    (entry['id'],)).fetchone()
            if previous:
                if previous['source_hash'] != entry['source_hash']:
                    raise ValueError('Migration source changed for ' + entry['id'])
                results.append(dict(id=entry['id'], status='already_migrated'))
                continue
            publication = conn.execute('SELECT app_json FROM creator_publications WHERE app_id=?',
                                       (entry['id'],)).fetchone()
            if publication and digest(json.loads(publication['app_json'])) != entry['source_hash']:
                raise ValueError('Existing publication differs: ' + entry['id'])
            store._publish(conn, entry['owner'], entry['snapshot'])
            conn.execute('INSERT INTO creator_migration_receipts VALUES(?,?)',
                         (entry['id'], entry['source_hash']))
            results.append(dict(id=entry['id'], status='migrated'))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--owner', action='append', required=True)
    parser.add_argument('--apply', action='store_true', help='Default is read-only dry-run')
    args = parser.parse_args()
    path = Path(args.db).resolve()
    # Dry-run must not initialize or seed a database.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
        row = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
    if row is None:
        raise ValueError('Canonical app_config resource is missing.')
    entries = plan(json.loads(row[0]), args.owner)
    if args.apply:
        from creator_store import CreatorStore
        results = apply(CreatorStore(str(path)), entries)
    else:
        results = [{key: value for key, value in item.items() if key != 'snapshot'} for item in entries]
    print(encoded(dict(mode='apply' if args.apply else 'dry-run', entries=results)))
    return 2 if any(item['status'] == 'review' for item in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
