"""Bounded explicit demand-to-job preparation. No network, neighbors or daemon."""
import time

from .discovery_worker import DiscoveryWorker
from .world_contract import SCHEMA_VERSION


def prepare_jobs(repo, permit, *, apply=False, limit=40):
    """Default is read-only; schema/budgets/provider permissions must exist.

    At most ten approved cells x four layers. Existing job identities are kept,
    including uncertain and completed jobs: preparation never retries them.
    Execution rechecks permissions and atomically reserves actual credit scopes.
    """
    if type(apply) is not bool or type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError('discovery_producer_limits')
    permit.validate()
    permit.validate_budgets(repo)
    worker = DiscoveryWorker(repo, permit)
    from .providers import Registry
    account = permit.account
    providers = [p for p in Registry(repo).list() if p['id'] == account]
    if not providers or not worker.candidate(dict(provider=account, revision=providers[0]['revision'])):
        return dict(status='policy_blocked', jobs=[], network_calls=0)
    revision = providers[0]['revision']
    c = repo.connect()
    try:
        rows = []
        # Indexed demand key is not used here: queue is capped at 10,000 entries.
        # Explicit cell/layer predicates avoid reading player coordinates or IDs.
        for x, y in sorted(permit.cells):
            for profile in sorted(permit.profiles):
                rows.extend(c.execute('''SELECT d.key,d.layer FROM world_discovery_demand d
                    WHERE cell_x=? AND cell_y=? AND layer=? AND contract=? AND expires>?
                    AND (? OR NOT EXISTS (SELECT 1 FROM world_discovery_job j WHERE j.demand_key=d.key
                        AND j.provider=? AND j.revision=? AND j.profile=d.layer AND j.acquisition=?))
                    ORDER BY d.key LIMIT 1''',
                    (x, y, profile, SCHEMA_VERSION, time.time(), permit.refresh_seconds,
                     account, revision, permit.acquisition)).fetchall())
    finally:
        c.close()
    jobs = []
    for row in rows:
        if len(jobs)>=limit: break
        if permit.refresh_seconds and not worker.jobs.enqueue(row['key'],account,revision,row['layer'],
                acquisition=permit.acquisition,refresh_seconds=permit.refresh_seconds,plan_only=True):
            # Apply also records legacy completed/uncertain receipts before pruning.
            if apply:
                worker.jobs.enqueue(row['key'],account,revision,row['layer'],
                    acquisition=permit.acquisition,refresh_seconds=permit.refresh_seconds)
            continue
        if apply:
            permit.validate()
            permit.validate_budgets(repo)
            if not worker.candidate(dict(provider=account, revision=revision, profile=row['layer'])):
                continue
            key = worker.jobs.enqueue(row['key'], account, revision, row['layer'],
                acquisition=permit.acquisition,refresh_seconds=permit.refresh_seconds)
            if key:
                jobs.append(key)
        else:
            if worker.candidate(dict(provider=account, revision=revision, profile=row['layer'])):
                jobs.append(dict(demand_key=row['key'], profile=row['layer'], revision=revision,
                                 acquisition=permit.acquisition))
    return dict(status='prepared' if apply else 'plan', jobs=jobs, network_calls=0)
