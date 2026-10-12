"""Additive 155 migration and SQLite backup/checks; never starts the game or publishes."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COLUMNS = {
    'chat_messages': ('system_copy_json', "TEXT NOT NULL DEFAULT '{}'"),
    'ghost_narrative_medium_records': ('output_locale', "TEXT NOT NULL DEFAULT ''"),
}


def connect(path, writable=False):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('database_must_exist')
    return sqlite3.connect(path.as_uri() + ('?mode=rw' if writable else '?mode=ro'),
                           uri=True, timeout=30)


def quote(value):
    return '"' + value.replace('"', '""') + '"'


def integrity(conn):
    if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('integrity_check_failed')
    if conn.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('foreign_key_check_failed')


def snapshot(conn, baseline=None):
    """Hash every original field, including IDs/receipts/read state; no text export."""
    tables = baseline or {row[0]: None for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    result = {}
    for name, previous in tables.items():
        columns = previous['columns'] if previous else [r[1] for r in conn.execute(
            'PRAGMA table_info(' + quote(name) + ')')]
        if not columns:
            raise ValueError('missing_table')
        fields = ','.join(map(quote, columns))
        digest = hashlib.sha256()
        count = 0
        for row in conn.execute(f'SELECT {fields} FROM {quote(name)} ORDER BY {fields}'):
            for value in row:
                encoded = (b'b' + value if isinstance(value, bytes) else
                           json.dumps(value, ensure_ascii=True, allow_nan=False).encode())
                digest.update(str(len(encoded)).encode() + b':' + encoded)
            digest.update(b'\n')
            count += 1
        result[name] = dict(columns=columns, count=count, sha256=digest.hexdigest())
    return result


def schema(conn):
    from ghostnetwork.news_locales import initialize
    from ghostnetwork.news_generation import initialize as jobs
    from ghostnetwork.narrative_locale_history import _schema as history
    for table, (column, definition) in COLUMNS.items():
        columns = {r[1] for r in conn.execute('PRAGMA table_info(' + quote(table) + ')')}
        if not columns:
            raise ValueError('required_table_missing:' + table)
        if column not in columns:
            conn.execute(f'ALTER TABLE {quote(table)} ADD COLUMN {quote(column)} {definition}')
    initialize(conn)
    jobs(conn)
    history(conn)


def migrate(path, apply=False):
    # Dry-run executes the real DDL only in memory, never against the live schema.
    with closing(connect(path, apply)) as source:
        if not apply:
            source.execute('BEGIN')
            integrity(source)
            with closing(sqlite3.connect(':memory:')) as preview:
                # Rehearse DDL on the schema alone: no second game database,
                # and memory use does not grow with production message history.
                for (sql,) in source.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','index') AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END,name"):
                    preview.execute(sql)
                result = _migrate(preview, False)
                result['original_data_unchanged'] = True
                return result
        return _migrate(source, True)


def _migrate(conn, apply):
    conn.execute('BEGIN IMMEDIATE')
    try:
        integrity(conn)
        before = snapshot(conn)
        old_schema = conn.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        schema(conn)
        integrity(conn)
        if snapshot(conn, before) != before:
            raise ValueError('original_data_changed')
        changed = old_schema != conn.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        conn.commit()
        return dict(ok=True, status=('migrated' if changed else 'already_migrated') if apply else 'dry_run',
                    schema_changes=changed, original_data_unchanged=True,
                    integrity='ok', foreign_keys='ok', tables_checked=len(before))
    except Exception:
        conn.rollback()
        raise


def backup(path, destination):
    destination = Path(destination).resolve()
    # Exclusive creation prevents overwriting either the source or an older backup.
    with destination.open('xb'):
        pass
    destination.chmod(0o600)
    with closing(connect(path)) as source, closing(sqlite3.connect(destination)) as target:
        source.backup(target)
        integrity(target)
    digest = hashlib.sha256()
    with destination.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return dict(ok=True, status='backed_up', path=str(destination), sha256=digest.hexdigest(),
                integrity='ok', foreign_keys='ok')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('backup', 'check', 'migrate'))
    parser.add_argument('--db', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'backup':
            if not args.output:
                parser.error('backup requires --output (new file)')
            result = backup(args.db, args.output)
        elif args.command == 'migrate':
            result = migrate(args.db, args.apply)
        else:
            with closing(connect(args.db)) as conn:
                conn.execute('BEGIN')
                integrity(conn)
                baseline = json.loads(args.baseline.read_text()) if args.baseline else None
                data = snapshot(conn, baseline)
                if baseline is not None and data != baseline:
                    raise ValueError('baseline_mismatch')
                if args.output:
                    with args.output.open('x', encoding='utf-8') as stream:
                        json.dump(data, stream, indent=2)
                    args.output.chmod(0o600)
            result = dict(ok=True, status='checked', integrity='ok', foreign_keys='ok',
                          tables_checked=len(data), baseline_matches=baseline is not None)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps(dict(ok=False, error=str(exc))))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
