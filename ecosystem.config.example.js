/*
 * PM2 example configuration for CHAOS.
 *
 * Copy this file and adjust the copy locally:
 *
 *   cp ecosystem.config.example.js ecosystem.config.js
 *   pm2 start ecosystem.config.js
 *
 * Keep ecosystem.config.js out of Git. It belongs to the local server.
 */

module.exports = {
  apps: [
    {
      name: "chaos-dev",
      cwd: __dirname,
      script: "run.py",
      interpreter: "python",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        PORT: "5000",
        APP_ENV: "staging",
        CHAOS_DEV_MODE: "true",
        FLASK_ENV: "production",
        PYTHONUNBUFFERED: "1",
        APP_VERSION: "v0.3.4-stable",
        BUILD_TAG: "v0.3.4-stable",
        GIT_COMMIT: ""
      }
    },
    {
      name: "chaos-territory-worker",
      cwd: __dirname,
      script: ".venv/bin/python",
      args: "scripts/territory_conflict_worker.py",
      interpreter: "none",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 2000
    }
  ]
};
