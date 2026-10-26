"""Enable the tested VK endpoint for background geometry only; no HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.regular_discovery import load

PID = 'overpass-vk'
URL = 'https://maps.mail.ru/osm/tools/overpass/api/interpreter'
LAYERS = ('roads', 'waterways', 'inland_water', 'coastline')
SCOPES = ['small_probe', 'storage', 'world_storage', 'background_refresh']


def configure(repo, policy_path, backup=None):
    policy = load(policy_path)[0]
    if policy['review_until'] <= time.time():
        raise ValueError('regular_policy_expired')
    registry = Registry(repo)
    p = next((p for p in registry.list() if p['id'] == PID), None)
    if not p or p['url'] != URL or p['operator_group'] != 'maps.mail.ru':
        raise ValueError('vk_endpoint_mismatch')
    if p['technical_status'] != 'tested_ok':
        raise ValueError('successful_probe_required')
    if 'normal_scan' in p['scopes']:
        raise ValueError('existing_live_approval_requires_separate_review')
    routing = Routing(repo)
    routes = {layer: routing.get(layer, 'background') for layer in LAYERS}
    chains = {layer: [PID] + [x for x in r['chain'] if x != PID][:2]
              for layer, r in routes.items()}
    result = dict(status='plan', network_calls=0, gameplay_changed=False,
                  provider=PID, daily_attempt_limit=120, rolling_31_day_attempt_limit=3720,
                  chains=chains, review_until=policy['review_until'], retention_days=7)
    if backup is None:
        return result
    backup = Path(backup)
    backup.parent.mkdir(parents=True, exist_ok=True)
    with backup.open('xb'):
        pass
    with closing(sqlite3.connect(Path(repo.path).resolve().as_uri()+'?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(backup)) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('backup_integrity_failed')
    actor = 'operator:vk-background-collection'
    # Budget first: enabling never creates an unbudgeted acquisition path.
    CreditBudget(repo).configure_recurring(PID, 120, 3720)
    review = policy['review_until'] + 7*86400 + 60
    if not (p['policy_status'] == 'approved_for_defined_use'
            and set(p['scopes']) == set(SCOPES) and p['review_due_at'] >= review):
        p = registry.decision(PID, p['revision'], 'approved_for_defined_use', SCOPES,
            dict(source_url='https://wiki.openstreetmap.org/wiki/Overpass_API',
                 reference='VK public usage declaration in OSM instance directory; operator rollout 2026-10-26',
                 notes='Public declaration, not individual provider confirmation. Background geometry observations only; '
                       '120 attempts/day, one request/cycle, 7-day retention. No normal_scan approval.'),
            review, actor)
    if not p['enabled']:
        p = registry.enable(PID, p['revision'], True, actor)
    for layer, current in routes.items():
        if current['chain'] != chains[layer]:
            routing.save(layer, 'background', current['revision'], chains[layer], actor)
    return dict(result, status='configured', revision=p['revision'], backup=str(backup))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/poi_cache.sqlite3')
    parser.add_argument('--policy', default='data/world-collection-policy.json')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    args = parser.parse_args()
    try:
        if args.apply != bool(args.backup):
            raise ValueError('apply_requires_backup')
        if not Path(args.db).is_file() or Path(args.db).name == 'game.sqlite3':
            raise ValueError('poi_database_required')
        print(json.dumps(configure(Repository(args.db), args.policy, args.backup)))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped', error=str(exc), network_calls=0)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
