"""Explicit retention of existing observations; never renews scan freshness."""
from contextlib import closing
import hashlib
import json
import re
import time

from .providers import Registry
from .world_storage import FORMAT


def retain_saved(repo, snapshots, *, apply=False):
    if (type(apply) is not bool or not isinstance(snapshots, (list, tuple))
            or not 1 <= len(snapshots) <= 10 or len(set(snapshots)) != len(snapshots)
            or any(not isinstance(s, str) or not re.fullmatch('[0-9a-f]{64}', s) for s in snapshots)):
        raise ValueError('retention_snapshot_list_invalid')
    now = time.time()
    reference = 'operator:maplark-seven-day-archive-20261025'
    context = repo.transaction() if apply else closing(repo.connect())
    with context as c:
        provider = Registry(repo)._load(c, 'maplark')
        if not provider or not all(Registry.approved(provider, scope) for scope in ('storage', 'world_storage')):
            raise ValueError('retention_storage_approval_required')
        items = []
        for snapshot in snapshots:
            row = c.execute('SELECT * FROM world_snapshot WHERE id=?', (snapshot,)).fetchone()
            if row is None:
                raise ValueError('snapshot_missing_no_automatic_refetch')
            if row['provider'] != 'maplark' or row['profile'] != FORMAT or len(row['payload']) > 8*1024*1024:
                raise ValueError('retention_source_invalid')
            if hashlib.sha256(row['payload']).hexdigest() != row['digest']:
                raise ValueError('retention_digest_invalid')
            raw = json.loads(row['payload'])
            if raw.get('revision') != provider['revision']:
                raise ValueError('retention_provider_revision_changed')
            until = row['fetched'] + 7*86400
            if not row['fetched'] <= now < until or provider['review_due_at'] < until:
                raise ValueError('retention_deadline_not_allowed')
            old = c.execute('SELECT * FROM world_retention WHERE snapshot_id=?', (snapshot,)).fetchone()
            if old and (old['retain_until'] != until or old['decision_reference'] != reference):
                raise ValueError('retention_existing_decision_conflict')
            items.append(dict(snapshot=snapshot, retain_until=until, already_retained=bool(old),
                              fetched=row['fetched'], fresh_until=row['fresh_until'], usable_until=row['usable_until']))
        # All snapshots must pass before any insert; transaction fences pruning/revision changes.
        if apply:
            c.executemany('INSERT OR IGNORE INTO world_retention VALUES (?,?,?)',
                          [(i['snapshot'], i['retain_until'], reference) for i in items])
    return dict(status='retained' if apply else 'plan', network_calls=0,
                retention_seconds=604800, items=items, freshness_changed=False,
                ledger_changed=False, payload_changed=False, refetch=False)
