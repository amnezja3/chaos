"""144.3 operator-only security cutover; dry-run by default, backup before apply."""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_security_store import PlayerSecurityStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = Path(args.db).resolve()
    if not path.is_file():
        parser.error('Database does not exist')
    store = PlayerSecurityStore(str(path))
    report = store.migrate()
    if args.apply and any(row['status'] == 'invalid_projection' for row in report):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if args.apply:
        directory = path.parent.parent / 'backups'
        directory.mkdir(exist_ok=True)
        backup = directory / ('security1443-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        print('Backup: ' + str(backup))
        report = store.migrate(apply=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(any(row['status'] == 'invalid_projection' for row in report))


if __name__ == '__main__':
    raise SystemExit(main())
