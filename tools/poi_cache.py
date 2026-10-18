"""POI cache status, explicit initialization/maintenance and log summary; no HTTP."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import Config


def summarize(path):
    counts = Counter()
    durations = []
    attempts = 0
    with Path(path).open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            for event in ('poi_scan', 'poi_fetch', 'poi_http', 'poi_cache'):
                marker = event + ' '
                if marker not in line:
                    continue
                try:
                    item = json.loads(line.split(marker, 1)[1])
                except (ValueError, TypeError):
                    continue
                if event == 'poi_scan':
                    counts['scan:' + str(item.get('result'))] += 1
                    durations.append(float(item['seconds']))
                elif event == 'poi_fetch':
                    counts['source:' + str(item.get('source'))] += 1
                    attempts += item.get('attempts', 0)
                elif event == 'poi_http':
                    counts['http:' + str(item.get('status'))] += 1
                else:
                    counts['evictions'] += item.get('evictions', 0)
    durations.sort()
    return dict(counts=counts, scans=len(durations), attempts=attempts,
                seconds={f'p{p}': durations[min(len(durations)-1, int((len(durations)-1)*p/100))] if durations else None for p in (50,95,99)},
                note='Legacy scans have duration/outcome but no poi_fetch attempt counts. Compare identical observation windows.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=os.environ.get('CHAOS_POI_CACHE_PATH') or str(ROOT / 'data/poi_cache.sqlite3'))
    parser.add_argument('--initialize', action='store_true')
    parser.add_argument('--maintenance', action='store_true', help='Expired entries and passive checkpoint; never VACUUM')
    parser.add_argument('--log')
    args = parser.parse_args()
    if args.log:
        print(json.dumps(summarize(args.log), indent=2))
        return
    config = Config.environment()
    path = Path(args.db).resolve()
    if path.name == 'game.sqlite3':
        parser.error('Refusing player database')
    if args.initialize:
        Repository(path, config.max_cache, config.max_entries).initialize()
    conn = sqlite3.connect(path.as_uri() + ('?mode=rw' if args.maintenance else '?mode=ro'), uri=True, timeout=.2)
    try:
        if args.maintenance:
            now = time.time()
            conn.execute('DELETE FROM leases WHERE until_at<=?', (now,))
            # Never remove useful stale if operator configured a longer TTL.
            stale = max(float(os.getenv('CHAOS_POI_STALE_CACHE_TTL_SECONDS','1800')), float(os.getenv('CHAOS_POI_CACHE_TTL_SECONDS','300')))
            conn.execute('DELETE FROM cache WHERE fetched<? AND key NOT IN (SELECT key FROM leases)', (now-stale,))
            conn.commit()
            checkpoint = list(conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone())
        else:
            checkpoint = None
        count, size = conn.execute('SELECT count(*),coalesce(sum(bytes),0) FROM cache').fetchone()
        print(json.dumps(dict(entries=count, payload_bytes=size,
            file_bytes=path.stat().st_size, wal_bytes=Path(str(path)+'-wal').stat().st_size if Path(str(path)+'-wal').exists() else 0,
            active_leases=conn.execute('SELECT count(*) FROM leases WHERE until_at>?',(time.time(),)).fetchone()[0],
            providers=[dict(zip(('group','failure_streak','open_until'), row)) for row in conn.execute('SELECT * FROM providers')],
            integrity=conn.execute('PRAGMA quick_check').fetchone()[0], checkpoint=checkpoint), indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
