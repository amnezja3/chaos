"""Inspect stored approvals, routes and archive deadlines without activation or HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing, LAYERS, reason
from poi_infrastructure.world_dashboard import budget_projection


def inspect(db, retention_seconds=7 * 86400):
    if type(retention_seconds) is not int or not 1800 <= retention_seconds <= 31 * 86400:
        raise ValueError('invalid_retention')
    source = Path(db).resolve()
    if not source.is_file():
        raise ValueError('existing_poi_database_required')
    with tempfile.TemporaryDirectory(prefix='chaos-activation-readiness-') as directory:
        target = Path(directory) / 'poi.sqlite3'
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'cache', 'leases', 'providers', 'poi_provider_config', 'world_retention'} <= tables or 'users' in tables:
                raise ValueError('prepared_poi_database_required')
            with closing(sqlite3.connect(target)) as dest:
                src.backup(dest)
        repo = Repository(target)
        providers = Registry(repo).list()
        by_id = {p['id']: p for p in providers}
        now = time.time()
        accounts = budget_projection(repo)
        routes = []
        for layer, lane in [('poi', 'live')] + [(layer, 'background') for layer in LAYERS]:
            route = Routing(repo).get(layer, lane)
            route['candidates'] = [dict(id=pid, blocked_by=reason(by_id[pid], layer, lane)
                if pid in by_id else 'provider_missing') for pid in route['chain']]
            routes.append(route)
        collection = []
        for pid, layer in [('maplark', 'roads'), ('geoapify', 'poi')]:
            provider = by_id.get(pid)
            blockers = []
            if provider is None:
                blockers.append('provider_missing')
            else:
                if not provider.get('enabled'):
                    blockers.append('provider_disabled')
                if provider.get('technical_status') != 'tested_ok':
                    blockers.append('technical_test_required')
                if provider.get('policy_status') != 'approved_for_defined_use':
                    blockers.append('policy_decision_required')
                if provider.get('review_due_at', 0) <= now:
                    blockers.append('policy_review_expired')
                for scope in ('background_refresh', 'storage', 'world_storage'):
                    if scope not in provider.get('scopes', []):
                        blockers.append('scope_required:' + scope)
                if provider.get('review_due_at', 0) < now + retention_seconds:
                    blockers.append('review_shorter_than_requested_retention')
                if not (provider.get('evidence') or {}).get('reference'):
                    blockers.append('storage_reference_required')
            budget = next((a for a in accounts if a['account'] == pid), None)
            windows = budget['windows'] if budget else []
            reservation = 5 if pid == 'geoapify' else 20
            if not windows:
                blockers.append('active_account_budget_required')
            elif any(w['remaining'] < reservation for w in windows):
                blockers.append('account_budget_insufficient')
            with closing(repo.connect()) as c:
                hold = c.execute('SELECT reason FROM world_credit_hold WHERE account=?', (pid,)).fetchone()
                recurring = c.execute('SELECT 1 FROM world_credit_policy WHERE account=?', (pid,)).fetchone()
                old_uncertain = c.execute('''SELECT 1 FROM world_credit_entry e
                    JOIN world_credit_operation o USING(account,operation)
                    JOIN world_credit_window w USING(account,period)
                    WHERE e.account=? AND o.state IN ('reserved','uncertain') AND w.ends<=?
                    AND NOT EXISTS (SELECT 1 FROM world_credit_entry carried
                        JOIN world_credit_window active USING(account,period)
                        WHERE carried.account=o.account AND carried.operation=o.operation
                          AND active.starts<=? AND active.ends>?
                          AND active.period LIKE 'carry:%'
                          AND carried.amount>=coalesce(o.charged,o.reserved)) LIMIT 1''',
                    (pid, now, now, now)).fetchone()
            if hold:
                blockers.append('account_hold')
            if old_uncertain and not recurring:
                blockers.append('previous_period_unresolved_requires_explicit_carry_forward')
            collection.append(dict(provider=pid, layer=layer,
                revision=provider.get('revision') if provider else None,
                blockers=blockers, reservation=reservation,
                execution_authorized=False,
                still_required=['bounded_permit', 'scoped_budget', 'runtime_admission_checks']))
        with closing(repo.connect()) as c:
            retention = dict(c.execute('''SELECT count(*) AS records,
                coalesce(sum(retain_until > ?),0) AS retained_now,
                max(retain_until) AS latest_deadline FROM world_retention''', (now,)).fetchone())
        return dict(status='read_only', network_calls=0, production_writes=0,
            requested_retention_seconds=retention_seconds, retention=retention,
            collection=collection, routes=routes, budgets=accounts,
            scope='Consistent temporary SQLite copy; no secrets, PM2 inspection or provider requests',
            limitation='Stored eligibility is not endpoint health, completeness or permission to execute. '
                       'An empty route is preserved. Uncertain costs remain reserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/poi_cache.sqlite3')
    parser.add_argument('--retention-seconds', type=int, default=7 * 86400)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.db, args.retention_seconds), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped', error_type=type(exc).__name__, network_calls=0)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
