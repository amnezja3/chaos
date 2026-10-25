// Explicit opt-in only. Loading this file does not authorize scopes or budgets.
module.exports = { apps: [{
  name: 'chaos-world-discovery-worker',
  cwd: '/home/johndoe/app/chaos',
  script: '/home/johndoe/app/chaos/.venv/bin/python',
  // Serve is bounded by the permit file; expiry exits normally, no automatic renewal.
  args: 'tools/world_discovery_worker.py --execute --serve --interval 30',
  interpreter: 'none', instances: 1, autorestart: false,
  kill_timeout: 40000,
  env: {
    CHAOS_POI_DISCOVERY_WORKER_ENABLED: '0',
    CHAOS_POI_PRIORITY_ENABLED: '1',
    CHAOS_POI_ROUTING_ENABLED: '0',
    CHAOS_MAPLARK_ACCEPT_VARIABLE_COST: '1',
    CHAOS_POI_CACHE_PATH: '/home/johndoe/app/chaos/data/poi_cache.sqlite3',
    CHAOS_POI_DISCOVERY_PERMIT_PATH: '/home/johndoe/app/chaos/data/discovery-permit.json'
  },
  env_bounded: {
    CHAOS_POI_DISCOVERY_WORKER_ENABLED: '1',
    CHAOS_POI_PRIORITY_ENABLED: '1',
    CHAOS_POI_ROUTING_ENABLED: '1',
    CHAOS_MAPLARK_ACCEPT_VARIABLE_COST: '1',
    CHAOS_POI_DISCOVERY_PERMIT_PATH: '/home/johndoe/app/chaos/data/collection-daemon-2036-5153-v1/permit.json'
  },
  env_regions: {
    CHAOS_POI_DISCOVERY_WORKER_ENABLED: '1',
    CHAOS_POI_PRIORITY_ENABLED: '1',
    CHAOS_POI_ROUTING_ENABLED: '1',
    CHAOS_MAPLARK_ACCEPT_VARIABLE_COST: '1',
    CHAOS_POI_DISCOVERY_PERMIT_PATH: '/home/johndoe/app/chaos/data/collection-regions-v1/permit.json'
  },
  env_baseline: { CHAOS_POI_DISCOVERY_WORKER_ENABLED: '0', CHAOS_POI_ROUTING_ENABLED: '0' }
}] };
