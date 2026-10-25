"""Retain the three accepted MapLark sector snapshots; no fetch or TTL renewal."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.archive_retention import retain_saved

SNAPSHOTS = [
    '0349afbdd71c29f1341160b90cb7a6715bfeeeb99868706a50e4284df27f8584',
    'd181d0990cf052c1ed1c215f637b0fbce5c82ddfd2bcef4afc626c052b277161',
    '6c8282c90393965e1be92bed24d2e1d42997d0ddb5b407c413ae2f519163bd5a']


def run(db, backup=None):
    source = Path(db).resolve()
    if not source.is_file() or source.name == 'game.sqlite3':
        raise ValueError('existing_poi_database_required')
    with tempfile.TemporaryDirectory(prefix='chaos-retention-') as directory:
        copy = Path(directory)/'poi.sqlite3'
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src, \
                closing(sqlite3.connect(copy)) as dst:
            src.backup(dst)
        result = retain_saved(Repository(copy), SNAPSHOTS)
        if backup is None:
            return result
        backup = Path(backup).resolve()
        # Exclusive creation protects old backups. No deletion/replacement on error.
        with backup.open('xb'):
            pass
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src, \
                closing(sqlite3.connect(backup)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or dst.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('backup_integrity')
        result = retain_saved(Repository(source), SNAPSHOTS, apply=True)
        result['backup'] = str(backup)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/poi_cache.sqlite3')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    args = parser.parse_args()
    if args.apply != bool(args.backup):
        parser.error('--apply requires --backup; --backup requires --apply')
    try:
        print(json.dumps(run(args.db, args.backup)))
        return 0
    except ValueError as exc:
        # These are bounded local validation codes, never transport/secret errors.
        code = str(exc)
        if not code.replace('_','').isalnum(): code = 'invalid_local_state'
        print(json.dumps(dict(status='stopped', error=code, network_calls=0)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
