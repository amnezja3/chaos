"""Read-only PM2/POI audit. Prints allowlisted settings; no HTTP or player data."""
import json
from pathlib import Path
import sqlite3
import subprocess
import time


DEFAULTS = {
    'CHAOS_POI_INFRASTRUCTURE_ENABLED':'0', 'CHAOS_POI_MASA_UX_ENABLED':'0',
    'CHAOS_POI_PROVIDER_ADMIN_ENABLED':'0', 'CHAOS_POI_PROVIDER_REGISTRY_ENABLED':'0',
    'CHAOS_POI_WORLD_INGEST_ENABLED':'0', 'CHAOS_POI_WORLD_REPOSITORY_ENABLED':'0',
    'CHAOS_POI_WIDE_FETCH_ENABLED':'0', 'CHAOS_POI_PROVIDER_MONITOR_ENABLED':'0',
    'CHAOS_ADULT_POLICY_ENABLED':'0', 'CHAOS_OVERPASS_TIMEOUT_SECONDS':'8',
    'CHAOS_POI_DEADLINE':'110', 'CHAOS_POI_CONNECT_TIMEOUT':'3',
    'CHAOS_POI_JOIN_WAIT':'2', 'CHAOS_POI_CACHE_TTL_SECONDS':'300',
    'CHAOS_POI_STALE_CACHE_TTL_SECONDS':'1800',
}


def main():
    raw = subprocess.run(['pm2','jlist'], capture_output=True, text=True, check=True, timeout=15)
    processes = json.loads(raw.stdout)
    web = next(p for p in processes if p.get('name') == 'chaos')
    env = web['pm2_env']
    settings = {key:str(env.get(key,default)) for key,default in DEFAULTS.items()}
    cwd = Path(env['pm_cwd'])
    path = Path(env.get('CHAOS_POI_CACHE_PATH') or 'data/poi_cache.sqlite3')
    if not path.is_absolute():
        path = cwd / path
    report = dict(scope='PM2 environment snapshot and read-only POI state; not worker memory or network trace',
                  process_status=env.get('status'), cwd=str(cwd), db_path=str(path),
                  settings=settings, db_exists=path.is_file())
    if path.is_file():
        conn = sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            now = time.time()
            if 'users' in tables:
                raise ValueError('Refusing player database')
            if 'providers' in tables:
                report['circuits'] = [dict(operator=r['name'], failures=r['failures'],
                    remaining_seconds=round(max(0,r['until_at']-now),2))
                    for r in conn.execute('SELECT name,failures,until_at FROM providers')]
            if 'leases' in tables:
                report['active_leases'] = [dict(kind=r['key'].split(':')[0] if r['key'].startswith('@') else 'query_or_world',
                    remaining_seconds=round(r['until_at']-now,2))
                    for r in conn.execute('SELECT key,until_at FROM leases WHERE until_at>?',(now,))]
            if 'poi_provider_config' in tables:
                providers = [json.loads(r[0]) for r in conn.execute('SELECT config FROM poi_provider_config')]
                report['registry'] = [dict(id=p['id'], enabled=p['enabled'], technical=p['technical_status'],
                    policy=p['policy_status'], scopes=p['scopes'], review_current=p['review_due_at']>now)
                    for p in providers]
                report['eligible_normal_scan'] = [p['id'] for p in providers if p['enabled'] and
                    p['technical_status']=='tested_ok' and p['policy_status']=='approved_for_defined_use' and
                    p['review_due_at']>now and 'normal_scan' in p['scopes']]
        finally:
            conn.close()
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
