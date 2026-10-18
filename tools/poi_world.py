"""Offline world/registry schema preparation and consistent SQLite backup.

Defaults to dry run on an in-memory copy. Never contacts an upstream provider.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poi_infrastructure.repository import Repository
from poi_infrastructure.world import WorldRepository
from poi_infrastructure.providers import Registry


def initialize(path):
    repo=Repository(path)
    WorldRepository(repo).initialize()
    Registry(repo).initialize()
    c=repo.connect()
    try:
        return dict(world=WorldRepository(repo).status(),providers=len(Registry(repo).list()),
                    integrity=c.execute('PRAGMA integrity_check').fetchone()[0],
                    foreign_keys='ok' if not c.execute('PRAGMA foreign_key_check').fetchall() else 'failed')
    finally:
        c.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=str(ROOT/'data/poi_cache.sqlite3'))
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--backup',help='New backup file; required for apply to an existing database')
    args=parser.parse_args()
    source=Path(args.db).resolve()
    if source.name=='game.sqlite3':
        parser.error('Refusing player database')
    if args.apply and source.exists() and not args.backup:
        parser.error('--backup is required before modifying an existing database')
    # A consistent API backup includes committed WAL data, unlike file copy.
    def copy_to(target):
        if target.exists():
            parser.error('Refusing to overwrite backup')
        if source.exists():
            src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
            dest=sqlite3.connect(target)
            try:
                # Do not mutate an unrelated file supplied under another name.
                names={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if names and (not {'cache','leases','providers'}<=names or 'users' in names):
                    raise ValueError('not_a_poi_database')
                src.backup(dest)
            finally:
                src.close();dest.close()
    if args.apply:
        if args.backup:
            copy_to(Path(args.backup).resolve())
        result=initialize(source)
        result['status']='schema_ready'
    else:
        with tempfile.TemporaryDirectory(prefix='poi-world-check-') as directory:
            target=Path(directory)/'poi.sqlite3'
            copy_to(target)
            result=initialize(target)
            result.update(status='dry_run',original_data_unchanged=True)
    print(json.dumps(result))


if __name__=='__main__':main()
