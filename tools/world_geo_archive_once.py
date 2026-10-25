"""Operator-approved single Geoapify capture and seven-day observation archive."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.world_acquisition import acquire_features
from poi_infrastructure.world_adapters import plan_geoapify
from poi_infrastructure.world_storage import CanonicalWorldRepository

IDENTITY = 'geo-archive-7d-20261025-v1'
ACTOR = 'operator:geo-archive-once'


def run(db, output, *, execute=False, transport=None):
    plan = dict(status='plan', network_calls=0, max_network_calls=1, reservation=5,
                retention_seconds=604800, latitude=52.2319, longitude=21.0067,
                radius=300, categories=['commercial'], limit=100,
                gameplay_changed=False, environment_changed=False,
                recurring_collection_enabled=False, provider_price_cap=False)
    if not execute:
        return plan
    db, output = Path(db).resolve(), Path(output).resolve()
    if not db.is_file() or db.name == 'game.sqlite3':
        raise ValueError('existing_poi_database_required')
    if output.exists():
        # Never turn an interrupted or completed operation into another request.
        return dict(plan, status='already_attempted_inspect_saved_report', output=str(output))
    repo = Repository(db)
    registry = Registry(repo)
    provider = next((p for p in registry.list() if p['id'] == 'geoapify'), None)
    if (not provider or provider['revision'] != 2 or provider.get('enabled')
            or provider['url'] != 'https://api.geoapify.com/v2/places'
            or provider['operator_group'] != 'api.geoapify.com'
            or provider.get('policy_status') != 'approved_for_defined_use'
            or set(provider.get('scopes', [])) != {'small_probe'}
            or provider.get('review_due_at', 0) <= time.time()):
        raise ValueError('provider_baseline_changed')
    query = plan_geoapify(52.2319, 21.0067, 300, categories=('commercial',), limit=100)
    query.authenticated_wire()  # Fail before any write when secret is missing.
    with closing(repo.connect()) as c:
        c.execute('SELECT snapshot_id FROM world_retention LIMIT 1').fetchall()
        if c.execute('SELECT 1 FROM world_credit_window WHERE account=? AND period=?',
                     ('geoapify', 'carry:'+IDENTITY)).fetchone():
            raise ValueError('operation_already_prepared_do_not_reset')
    output.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro', uri=True)) as src, \
            closing(sqlite3.connect(output/'poi_cache.sqlite3')) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or dst.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('backup_integrity')
    ledger = CreditBudget(repo)
    started = time.time()
    carried = ledger.carry_forward('geoapify', IDENTITY, started, started+3600, 5)
    report = dict(plan, status='prepared', carry_forward=carried, output=str(output))
    def save():
        temporary = output/'report.tmp'
        temporary.write_text(json.dumps(report, indent=2), encoding='utf8')
        temporary.replace(output/'report.json')
    save()
    def active():
        return time.time() < started+3600 and any(
            p['id']=='geoapify' and p['revision']==provider['revision']
            and p.get('probe_allowed') and p.get('review_due_at',0)>time.time()
            for p in registry.list())
    try:
        batch, bill = acquire_features(repo, query, IDENTITY, 5, account='geoapify',
            accept_variable_cost=True, transport=transport, still_active=active, lane='background')
        report.update(status='captured', network_calls=1, billing=bill, objects=len(batch.objects))
        save()
        # Technical status is earned by this actual validated response, not by a CLI assertion.
        tested = registry.tested('geoapify', provider['revision'], True, ACTOR)
        decision = registry.decision('geoapify', tested['revision'], 'approved_for_defined_use',
            ['small_probe', 'storage', 'world_storage'],
            dict(source_url='https://www.geoapify.com/terms-and-conditions/', reference=IDENTITY,
                 notes='Operator accepted one commercial POI capture and seven-day archive. '
                       'No normal_scan or background_refresh authorization; unknown costs stay reserved.'),
            started+604800+3600, ACTOR)
        # Storage-only enable: Registry.enable intentionally requires normal_scan, which is NOT granted.
        with repo.transaction() as c:
            current = registry._load(c, 'geoapify')
            if current['revision'] != decision['revision']:
                raise ValueError('provider_revision_conflict')
            stored = registry._write(c, dict(current, enabled=True), current, ACTOR, 'archive_only_enable')
        owner = repo.acquire(IDENTITY, 120)
        if owner is None:
            raise ValueError('archive_lease_busy')
        try:
            now = time.time()
            snapshot = CanonicalWorldRepository(repo).publish_batch(IDENTITY, owner, batch,
                provider='geoapify', revision=stored['revision'], storage_reference=IDENTITY,
                fresh_until=now+300, usable_until=now+1800, retain_until=now+604800)
            if not snapshot:
                raise ValueError('archive_publication_lost')
        finally:
            repo.release(IDENTITY, owner)
        restored = CanonicalWorldRepository(Repository(db)).read_batch(snapshot)
        if restored != batch:
            raise ValueError('archive_readback_failed')
        with closing(repo.connect()) as c:
            retention = c.execute('SELECT retain_until FROM world_retention WHERE snapshot_id=?',
                                  (snapshot,)).fetchone()
            if retention is None or c.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('archive_integrity_failed')
        report.update(status='archived_observations', snapshot=snapshot, coverage='UNKNOWN',
                      provider_revision=stored['revision'], normal_scan_allowed=False,
                      background_refresh_allowed=False, local_readback_pass=True,
                      retain_until=retention[0])
        save()
        return report
    except Exception as exc:
        report.update(status='stopped_no_automatic_retry', error_type=type(exc).__name__)
        # A failed transport may have sent a request: never report a definite zero.
        if not report.get('billing'):
            report['network_calls'] = 'unknown_after_acquisition_attempt'
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/poi_cache.sqlite3')
    parser.add_argument('--output', default='data/'+IDENTITY)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.db, args.output, execute=args.execute)))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped', error_type=type(exc).__name__,
                              automatic_retry=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
