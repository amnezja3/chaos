"""Additive BlackNet language ledger; does not rewrite player content or publish."""
import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ghostnetwork.signal_language import SCHEMA


def run(path, action, apply=False):
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + ('?mode=rw' if apply else '?mode=ro'), uri=True)) as conn:
        conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        exists = bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='blacknet_signal_languages'").fetchone())
        count = conn.execute('SELECT count(*) FROM blacknet_signal_languages').fetchone()[0] if exists else 0
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        foreign = conn.execute('PRAGMA foreign_key_check').fetchall()
        if integrity != 'ok' or foreign:
            raise ValueError('database_integrity_failed')
        inventory = {}
        # Bounded rows, no full player profiles, no content or secrets in reports.
        for table, column, location in (
            ('creator_projects', 'project_json', '$.presentation.signal_language'),
            ('creator_publications', 'app_json', '$.signal_language'),
            ('creator_editions', 'app_json', '$.signal_language'),
            ('ghostlab_projects', 'project_json', '$.signal_language'),
            ('player_apps', 'app_json', '$.signal_language')):
            if conn.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?', ('table', table)).fetchone():
                rows = conn.execute(f"SELECT COALESCE(json_extract({column}, ?), 'unknown'), count(*) FROM {table} GROUP BY 1", (location,)).fetchall()
                inventory[table] = {str(locale): count for locale, count in rows}
        if action == 'migrate' and apply:
            conn.execute(SCHEMA)
        if action == 'rollback' and apply and exists:
            if count:
                raise ValueError('ledger_in_use_keep_for_existing_signals')
            conn.execute('DROP TABLE blacknet_signal_languages')
        result = dict(ok=True, action=action, applied=apply, ledger_exists=exists,
                      pinned_signals=count, integrity=integrity, foreign_keys='ok',
                      original_data_unchanged=True, published=False)
        result['declarations'] = inventory
        result['legacy_policy'] = 'retain_original_unknown_no_republish'
        if apply:
            conn.commit()
        else:
            conn.rollback()
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inventory', 'migrate', 'check', 'rollback'])
    parser.add_argument('--db', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.apply and args.action not in ('migrate', 'rollback'):
        parser.error('--apply is only valid for migrate/rollback')
    print(json.dumps(run(args.db, args.action, args.apply)))
