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
    providers = [p for p in Registry(repo).list() if p['id'] == 'maplark']
    if not providers or not worker.candidate(dict(provider='maplark', revision=providers[0]['revision'])):
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
                    AND NOT EXISTS (SELECT 1 FROM world_discovery_job j WHERE j.demand_key=d.key
                        AND j.provider='maplark' AND j.revision=? AND j.profile=d.layer)
                    ORDER BY d.key LIMIT 1''',
                    (x, y, profile, SCHEMA_VERSION, time.time(), revision)).fetchall())
    finally:
        c.close()
    jobs = []
    for row in rows[:limit]:
        if apply:
            permit.validate()
            permit.validate_budgets(repo)
            if not worker.candidate(dict(provider='maplark', revision=revision, profile=row['layer'])):
                continue
            key = worker.jobs.enqueue(row['key'], 'maplark', revision, row['layer'])
            if key:
                jobs.append(key)
        else:
            if worker.candidate(dict(provider='maplark', revision=revision, profile=row['layer'])):
                jobs.append(dict(demand_key=row['key'], profile=row['layer'], revision=revision))
    return dict(status='prepared' if apply else 'plan', jobs=jobs, network_calls=0)
