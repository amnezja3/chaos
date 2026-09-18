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
        CHAOS_RESPONSE_QUALIFICATION_MODE: "observe",
        CHAOS_NARRATIVE_TTL_URGENT_SECONDS: "1800",
        CHAOS_NARRATIVE_TTL_NORMAL_SECONDS: "7200",
        CHAOS_NARRATIVE_TTL_EDITORIAL_SECONDS: "21600",
        CHAOS_NARRATIVE_PRIORITY_URGENT: "300",
        CHAOS_NARRATIVE_PRIORITY_NORMAL: "200",
        CHAOS_NARRATIVE_PRIORITY_EDITORIAL: "100",
        PYTHONUNBUFFERED: "1",
        CHAOS_NARRATIVE_PUBLISHER_ENABLED: "true",
        CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED: "false",
        CHAOS_NARRATIVE_PUBLISHER_POLL_SECONDS: "1.5",
        CHAOS_NARRATIVE_PUBLISHER_LEASE_SECONDS: "60"
      }
    }
  ]
};
