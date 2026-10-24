"""Prepare routing tables after SQLite backup; no network or runtime activation."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def prepare(path, backup_directory=None):
    from poi_infrastructure.repository import Repository
    from poi_infrastructure.providers import Registry
    from poi_infrastructure.routing import Routing
    source=Path(path).resolve()
    if not source.is_file():
        raise ValueError('database_missing')
    if backup_directory is None:
        with tempfile.TemporaryDirectory(prefix='chaos-routing-') as directory:
            target=Path(directory)/'poi.sqlite3'
            backup(source,target)
            repo=Repository(target);Registry(repo).initialize();Routing(repo).initialize()
            check(target)
        return dict(status='dry_run',network_calls=0,original_data_unchanged=True)
    directory=Path(backup_directory).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/'poi_cache.sqlite3'
    if target.exists():
        raise ValueError('backup_already_exists')
    backup(source,target);check(target)
    repo=Repository(source);Registry(repo).initialize();Routing(repo).initialize();check(source)
    return dict(status='prepared',backup=str(target),network_calls=0,environment_changed=False)


def backup(source,target):
    c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    out=sqlite3.connect(target)
    try:
        c.backup(out)
    finally:
        out.close();c.close()


def check(path):
    c=sqlite3.connect(path)
    try:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('database_integrity_failed')
    finally:
        c.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--backup-dir',help='Apply only after creating this new backup')
    args=parser.parse_args()
    print(json.dumps(prepare(args.db,args.backup_dir)))


if __name__=='__main__':main()
