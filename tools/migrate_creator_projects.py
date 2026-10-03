"""Offline adoption of legacy creator projects. Defaults to read-only dry-run."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creator_legacy import adopt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--owner', required=True, action='append')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = Path(args.db).resolve(strict=True)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
        row = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
        apps = {x['id']: x for x in json.loads(row[0]) if isinstance(x, dict) and x.get('id')}
        for row in conn.execute('SELECT app_id,app_json FROM creator_publications'):
            apps[row[0]] = json.loads(row[1])
    store = SimpleNamespace(db_path=str(path))
    if args.apply:
        from creator_store import CreatorStore
        store = CreatorStore(str(path))
    results = adopt(store, list(apps.values()), args.owner, apply=args.apply)
    print(json.dumps(dict(apply=args.apply, results=results), ensure_ascii=False, indent=2))
    return 2 if any(x['status'] == 'review' for x in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
