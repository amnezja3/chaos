"""144.3 catalog audit; optional backed-up download baseline repair. No heavy profiles."""
import argparse
import ast
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ghostlab_registry import PRO_TOOL_GLAB, get_template, validate_pro_tool_assignments, pro_tool_classification


def audit(conn, tools):
    validate_pro_tool_assignments(tools)
    row = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
    catalog = json.loads(row[0]) if row else []
    publications = {r[0]: json.loads(r[1]) for r in conn.execute('SELECT app_id,app_json FROM ghostlab_publications')}
    anomalies, baselines = [], []
    for item in catalog:
        if item.get('ghostlab_generated') and item.get('id') not in publications:
            anomalies.append({'app_id': item.get('id'), 'reason': 'no_canonical_publication'})
        elif item.get('type') == 'pro-system-tool' and item.get('id') not in PRO_TOOL_GLAB and item.get('id') not in publications:
            anomalies.append({'app_id': item.get('id'), 'reason': 'unclassified_legacy_pro_tool'})
        if item.get('id') in publications:
            canonical = publications[item['id']]
            if int(item.get('downloads') or 0) > int(canonical.get('downloads') or 0):
                baselines.append({'app_id': item['id'], 'downloads': int(item['downloads'])})
            for field in ('source_project_id', 'creator_username', 'artifact_id', 'template_id'):
                if canonical.get(field) != item.get(field):
                    anomalies.append({'app_id': item['id'], 'reason': 'mismatch:' + field})
    return {'system_tools': [dict(id=t['id'], **pro_tool_classification(t['id'])) for t in tools],
            'publications': len(publications), 'anomalies': anomalies, 'download_baseline_updates': baselines,
            'note': 'Built-in classification is projected from code; no profile/catalog rewrite required.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--apply-download-baselines', action='store_true', help='Only copy existing download totals into canonical publication metadata; backup first.')
    args = parser.parse_args()
    tree = ast.parse((ROOT/'run.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='PRO_SYSTEM_TOOLS' for t in n.targets))
    tools = ast.literal_eval(node.value)
    path = Path(args.db).resolve()
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:
        report = audit(conn, tools)
    if args.apply_download_baselines and not report['anomalies'] and report['download_baseline_updates']:
        backup_dir = path.parent.parent/'backups'
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir/('glab1443-downloads-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        print('Backup: '+str(backup))
        with sqlite3.connect(path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            report = audit(conn, tools)
            if report['anomalies']:
                raise ValueError('Catalog changed; review audit before applying')
            for item in report['download_baseline_updates']:
                canonical=json.loads(conn.execute('SELECT app_json FROM ghostlab_publications WHERE app_id=?',(item['app_id'],)).fetchone()[0])
                canonical['downloads']=item['downloads']
                conn.execute('UPDATE ghostlab_publications SET app_json=? WHERE app_id=?',(json.dumps(canonical,ensure_ascii=False),item['app_id']))
            report = audit(conn, tools)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(bool(report['anomalies']))


if __name__ == '__main__':
    raise SystemExit(main())
