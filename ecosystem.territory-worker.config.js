module.exports = {
  apps: [
    {
      name: "chaos-territory-worker",
      cwd: "/home/johndoe/app/chaos",
      script: "/home/johndoe/app/chaos/scripts/territory_conflict_worker.py",
      args: [],
      interpreter: "/home/johndoe/app/chaos/.venv/bin/python",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
        CHAOS_PROFILE_WRITE_METRICS: "1",
        CHAOS_GHOSTNETWORK_RUNTIME_MODE: "development",
        CHAOS_GHOSTNETWORK_DROPS_ENABLED: "true",
        CHAOS_GHOSTNETWORK_DROP_CHANCE: "0.04",
        CHAOS_GHOSTNETWORK_MIN_PART_DISTANCE_KM: "50"
      }
    }
  ]
};
