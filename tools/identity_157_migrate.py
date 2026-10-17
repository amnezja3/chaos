"""Additive identity migration, never starts CHAOS. Default: read-only dry-run."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_gateway.store import initialize
from tools.ghost_content_155_migrate import connect, integrity, snapshot


def apply_transaction(conn):
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('BEGIN IMMEDIATE')
    try:
        integrity(conn)
        before = snapshot(conn)
        previous = conn.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        initialize(conn)
        integrity(conn)
        if snapshot(conn, before) != before:
            raise ValueError('original_data_changed')
        changed = previous != conn.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        conn.commit()
        return dict(ok=True, status='migrated' if changed else 'already_migrated',
                    schema_changes=changed, original_data_unchanged=True,
                    integrity='ok', foreign_keys='ok')
    except Exception:
        conn.rollback()
        raise


def migrate(path, apply=False):
    with closing(connect(path, writable=apply)) as source:
        if apply:
            return apply_transaction(source)
        # Snapshot via SQLite backup includes committed WAL data. Only this
        # transient in-memory database receives DDL; no second game instance.
        with closing(sqlite3.connect(':memory:')) as preview:
            source.backup(preview)
            result = apply_transaction(preview)
            result['status'] = 'dry_run'
            return result


def check(path, baseline=None):
    with closing(connect(path)) as conn:
        conn.execute('BEGIN')
        integrity(conn)
        required={'user_identities','identity_account_security','identity_consents','identity_intents',
                  'identity_flow_data','identity_tickets','identity_grants','identity_mail_challenges',
                  'identity_rate_limits','identity_retired_subjects','identity_security_events','identity_mail_settings'}
        present={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(present):
            raise ValueError('identity_schema_missing')
        for table, names in {'identity_consents': {'age_confirmed','age_statement_version'},
                             'identity_account_security': {'age_restricted'}}.items():
            if not names.issubset({r[1] for r in conn.execute('PRAGMA table_info('+table+')')}):
                raise ValueError('adult_schema_missing')
        result=dict(ok=True,status='checked',integrity='ok',foreign_keys='ok')
        if baseline:
            before=json.loads(Path(baseline).read_text(encoding='utf-8'))
            if snapshot(conn,before)!=before:
                raise ValueError('baseline_mismatch')
            result['baseline_matches']=True
        return result


def backup(path, target):
    destination=Path(target).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation: never overwrite an earlier backup.
    with destination.open('xb'):
        pass
    try:
        with closing(connect(path)) as source, closing(sqlite3.connect(destination)) as copy:
            source.backup(copy)
            integrity(copy)
            before=snapshot(copy)
        baseline=destination.with_suffix('.baseline.json')
        with baseline.open('x',encoding='utf-8') as output:
            json.dump(before,output)
        return dict(ok=True,status='backed_up',backup=str(destination),baseline=str(baseline),integrity='ok',foreign_keys='ok')
    except Exception:
        # Keep failed artifact for inspection, never call it a successful backup.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--backup', metavar='DESTINATION')
    parser.add_argument('--baseline',help='Original-data snapshot, only with --check while writers remain paused')
    args = parser.parse_args()
    try:
        if args.baseline and not args.check:
            parser.error('--baseline requires --check')
        result=backup(args.db,args.backup) if args.backup else check(args.db,args.baseline) if args.check else migrate(args.db,args.apply)
        print(json.dumps(result))
        return 0
    except (OSError, sqlite3.Error, ValueError):
        print(json.dumps(dict(ok=False, error='identity_migration_failed')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
