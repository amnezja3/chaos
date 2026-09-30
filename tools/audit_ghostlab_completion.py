"""146.5 read-only pre-deploy report. Never imports the application or mutates data."""
import argparse
import collections
import json
from pathlib import Path
import sqlite3


def report(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'ghostlab_projects' not in tables:
            return {'ready':False, 'reason':'Canonical GhostLab migration required'}
        projects = conn.execute('SELECT count(*) FROM ghostlab_projects WHERE deleted=0').fetchone()[0]
        by_owner = collections.defaultdict(lambda: collections.defaultdict(list))
        if 'player_apps' in tables:
            for owner, app_id, name in conn.execute("SELECT username, app_id, json_extract(app_json,'$.name') FROM player_apps WHERE status!='uninstalled'"):
                by_owner[owner][str(name).strip().casefold()].append(app_id)
        duplicates = [dict(owner=owner, name=name, launch_ids=ids) for owner, names in by_owner.items()
                      for name, ids in names.items() if len(ids)>1]
        legacy_zero = [dict(app_id=r[0], current_price=r[1]) for r in conn.execute('''
            SELECT app_id, json_extract(app_json,'$.price') FROM ghostlab_publications
            WHERE json_extract(app_json,'$.metadata.artifact.branding_snapshot.suggested_price')=0
            AND coalesce(json_extract(app_json,'$.glab_price_policy'),0)!=1''')]
        pending = [dict(owner=r[0],status=r[1]) for r in conn.execute("SELECT owner,status FROM ghostlab_migrations WHERE status!='complete'")]
        return dict(ready=not pending, mode='read-only / no migration writes', lab_files=projects,
                    name_conflicts=duplicates, migration_required=pending,
                    historical_zero_prices_preserved=legacy_zero,
                    price_policy='New published builds only; no historical repricing',
                    document_schema='Created automatically at startup; purchased editions remain immutable')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/game.sqlite3')
    args=parser.parse_args()
    print(json.dumps(report(args.db),ensure_ascii=False,indent=2))
