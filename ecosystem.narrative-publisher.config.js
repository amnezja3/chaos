module.exports = {
  apps: [
    {
      name: "chaos-narrative-publisher",
      cwd: "/home/johndoe/app/chaos",
      script: "/home/johndoe/app/chaos/scripts/narrative_publication_worker.py",
      args: ["run"],
      interpreter: "/home/johndoe/app/chaos/.venv/bin/python",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      kill_timeout: 10000,
      env: {
        PYTHONUNBUFFERED: "1",
        CHAOS_NARRATIVE_PUBLISHER_ENABLED: "false",
        CHAOS_NARRATIVE_PUBLISHER_POLL_SECONDS: "1.5",
        CHAOS_NARRATIVE_PUBLISHER_LEASE_SECONDS: "60"
      }
    }
  ]
};
