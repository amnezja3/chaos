"""Read-only production evidence; no secrets, player identifiers or API calls."""
import ast
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = ['run.py', 'ghostnetwork/llm/router.py', 'ghostnetwork/llm/mistral_provider.py']
    tree = ast.parse((ROOT / 'run.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_start_location_by_ip')
    body = [n for n in node.body if not isinstance(n, ast.Expr)]
    random_only = len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call) and isinstance(body[0].value.func, ast.Name) and body[0].value.func.id == 'fallback_start_city'
    result = {'disk_start_city_random_only': random_only,
              'disk_mistral_guard_present': all('mistral_data_review_required' in (ROOT / p).read_text(encoding='utf-8') for p in paths[1:]),
              'processes': []}
    latest = max((ROOT / p).stat().st_mtime for p in paths)
    processes = json.loads(subprocess.check_output(['pm2', 'jlist'], text=True))
    for proc in processes:
        if proc.get('name') not in {'chaos', 'chaos-ollama-worker', 'chaos-narrative-publisher', 'chaos-territory-worker'}:
            continue
        meta = proc.get('pm2_env', {})
        item = {'name': proc['name'], 'status': meta.get('status'),
                'started_after_files': meta.get('pm_uptime', 0) / 1000 > latest}
        try:
            raw = Path(f"/proc/{int(proc['pid'])}/environ").read_bytes()
            env = dict(part.split(b'=', 1) for part in raw.split(b'\0') if b'=' in part)
            item['mistral_release_enabled'] = env.get(b'CHAOS_MISTRAL_DATA_REVIEW_APPROVED', b'').strip() == b'1'
            item['age_flag'] = env.get(b'CHAOS_ADULT_POLICY_ENABLED', b'(unset)').decode('ascii', errors='replace')
            item['cwd_matches'] = Path(f"/proc/{int(proc['pid'])}/cwd").resolve() == ROOT
        except (OSError, KeyError, ValueError):
            item['environment_readable'] = False
        result['processes'].append(item)
    db = sqlite3.connect((ROOT / 'data/game.sqlite3').as_uri() + '?mode=ro', uri=True)
    try:
        cols = {r[1] for r in db.execute('PRAGMA table_info(identity_consents)')}
        if 'terms_version' in cols:
            result['accepted_terms_counts'] = [dict(version=r[0], count=r[1]) for r in db.execute('SELECT terms_version,count(*) FROM identity_consents GROUP BY terms_version')]
        if 'age_statement_version' in cols:
            result['age_statement_counts'] = [dict(version=r[0], confirmed=r[1], count=r[2]) for r in db.execute('SELECT age_statement_version,age_confirmed,count(*) FROM identity_consents GROUP BY age_statement_version,age_confirmed')]
    finally:
        db.close()
    result['scope'] = 'Disk code, process startup/environment and aggregate acceptance records; not live network tracing or proof of historical notice delivery.'
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
