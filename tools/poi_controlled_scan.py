"""One explicitly requested diagnostic scan; never enables gameplay or stores POI."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poiFetchClass import POIFetcher
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import Config, POIError, UpstreamUnavailable, bounded_http, validate, retry_delay


def scan(path, provider_id, execute=False, query_kind='full'):
    if query_kind not in ('full', 'simple'):
        raise POIError('invalid_query_kind')
    if not Path(path).is_file():
        raise POIError('existing_poi_database_required')
    repo = Repository(path)
    registry = Registry(repo)
    candidate = next((p for p in registry.list() if p['id'] == provider_id), None)
    if not candidate or not Registry.approved(candidate, 'small_probe'):
        raise POIError('successful_approved_probe_required')
    # Fixed public reference point in Warsaw, never a player's coordinates.
    fetcher = POIFetcher(radius=300, tag_filters=[
        'shop', 'amenity', 'office', 'healthcare', 'atm=yes', 'man_made=surveillance'])
    query = fetcher._build_query(52.2319, 21.0067).replace('[timeout:15]', '[timeout:25]')
    if query_kind == 'simple':
        query = '[out:json][timeout:25];node(around:300,52.2319,21.0067)["amenity"];out;'
    result = dict(provider=provider_id, status='dry_run', radius=300,
                  query_kind=query_kind,
                  latitude=52.2319, longitude=21.0067, read_timeout=25,
                  deadline=35, network_calls=0, gameplay_configuration_unchanged=True,
                  poi_storage=False)
    if not execute:
        return result
    # --execute authorizes this single manual diagnostic only. It does not
    # promote the registry's scope to normal_scan/storage or enable a provider.
    group = candidate['operator_group']
    if not repo.allowed(group):
        raise POIError('circuit_open')
    if not repo.acquire('@controlled-scan-rate:' + group, 900):
        raise POIError('controlled_scan_rate_limited')
    slot = repo.acquire('@upstream', 42, probe_group=group)
    if not slot:
        raise POIError('upstream_busy')
    started = time.monotonic()
    observation = 'error'
    try:
        current = next((p for p in registry.list() if p['id'] == provider_id), None)
        if current != candidate:
            raise POIError('provider_revision_conflict')
        if not repo.allowed(group):
            raise POIError('circuit_open')
        config = Config(deadline=35, diagnostic_errors=True)
        status, retry, data = bounded_http(config, candidate['url'], query, 25,
                                       started + 35, secure=True)
        observation = str(status)
        result.update(status='http_error', http_status=status, network_calls=1)
        if status != 200:
            result['diagnostic'] = data
        if status == 200:
            validate(data, config)
            repo.outcome(group, True)
            result.update(status='validated', elements=len(data['elements']),
                          types=dict(Counter(e['type'] for e in data['elements'])))
        elif status in (429, 500, 502, 503, 504):
            repo.outcome(group, False, retry_delay(retry) or (30 if status == 429 else 0))
        return dict(result, seconds=round(time.monotonic() - started, 3))
    except POIError as exc:
        observation = str(exc)
        if isinstance(exc, UpstreamUnavailable):
            repo.outcome(group, False)
        raise
    finally:
        try:
            registry.record_health(provider_id, candidate['revision'],
                                   'controlled_scan', observation, time.monotonic() - started)
        finally:
            try:
                repo.release('@probe:' + group, slot)
            finally:
                repo.release('@upstream', slot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT / 'data/poi_cache.sqlite3'))
    parser.add_argument('--provider', default='overpass-vk')
    parser.add_argument('--query', choices=('full', 'simple'), default='full')
    parser.add_argument('--execute', action='store_true',
                        help='Authorize one manual reference scan, without gameplay activation')
    args = parser.parse_args()
    try:
        result = scan(args.db, args.provider, args.execute, args.query)
    except POIError as exc:
        print(json.dumps(dict(ok=False, error=str(exc))))
        return 1
    print(json.dumps(result))
    return 0 if result['status'] in ('dry_run', 'validated') else 1


if __name__ == '__main__':
    raise SystemExit(main())
