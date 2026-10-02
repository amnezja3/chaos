"""Explicit offline seeding for the territory reward ledger. Dry-run by default."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from database import _validate_persisted_profile_row
from player_progression import SCHEMA, seed
from ghost_reward_projection import SCHEMAS


def migrate(path, owners, apply=False):
    owners = list(dict.fromkeys(owners))
    if not owners or len(owners) > 100 or any(not isinstance(x, str) or not x.strip() for x in owners):
        raise ValueError('Specify 1 to 100 explicit account names')
    path = Path(path).resolve()
    prepared, report = [], []
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_progression'").fetchone()
        ghost_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_ghost_reward_state'").fetchone()
        for owner in owners:
            if ghost_exists and conn.execute('SELECT 1 FROM player_ghost_reward_state WHERE username=?',(owner,)).fetchone() and exists and conn.execute('SELECT 1 FROM player_progression WHERE username=?',(owner,)).fetchone():
                report.append(dict(username=owner,status='already_seeded'))
                continue
            row = conn.execute('SELECT username,password,salt,profile_json,profile_revision,profile_checksum,profile_integrity_status FROM users WHERE username=?',
                               (owner,)).fetchone()
            profile, errors = _validate_persisted_profile_row(row, owner)
            if errors:
                report.append(dict(username=owner,status='review',errors=list(errors)))
                continue
            prepared.append((profile,row['profile_revision'],row['profile_checksum']))
            report.append(dict(username=owner,status='ready'))
    if apply:
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute(SCHEMA)
            for statement in SCHEMAS:
                conn.execute(statement)
            for profile, revision, checksum in prepared:
                row = conn.execute('SELECT profile_revision,profile_checksum FROM users WHERE username=?',
                                   (profile['username'],)).fetchone()
                if row != (revision,checksum):
                    raise ValueError('Profile changed during migration: '+profile['username'])
                seed(conn,profile)
            for item in report:
                if item['status']=='ready':item['status']='seeded'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--owner',action='append',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    result=migrate(args.db,args.owner,args.apply)
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(2 if any(row['status']=='review' for row in result) else 0)
