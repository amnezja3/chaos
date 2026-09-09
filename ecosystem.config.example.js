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
        GIT_COMMIT: "",
        CHAOS_CYBERNER_CHANNEL_STORE_ENABLED: "0",
        CHAOS_CYBERNER_WORLD_STORE_ENABLED: "0",
        CHAOS_CYBERNER_CLAN_STORE_ENABLED: "0",
        CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED: "0",
        CHAOS_GHOSTNETWORK_RUNTIME_MODE: "development",
        CHAOS_GHOSTNETWORK_DROPS_ENABLED: "true",
        CHAOS_GHOSTNETWORK_DROP_CHANCE: "0.04",
        CHAOS_GHOSTNETWORK_MIN_PART_DISTANCE_KM: "50",
        CHAOS_GHOSTNETWORK_ABILITIES_ENABLED: "true",
        CHAOS_GHOSTNETWORK_ABILITY_ALLOWED_CODES: "insider_feed,service_entrance,false_image,hostile_takeover,operational_prediction,expose,narrative_takeover,full_disclosure,resistance_signal,domino_effect,phantom_node,glitch_injection,false_tracking,network_fracture,reflection,integrity_scan,bastion,rollback,trust_corridor,quarantine",
        CHAOS_GHOSTNETWORK_ABILITY_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS: "3600",
        CHAOS_GHOSTNETWORK_SIGNAL_NODE_HOLDER_RSP: "8",
        CHAOS_GHOSTNETWORK_SIGNAL_CLOSER_RSP: "20",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_RSP: "8",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_PRIMARY_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONFLICT_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_OVERLAP_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONSUMPTION_ENABLED: "1",
        CHAOS_GHOSTNETWORK_SIGNAL_SHOW_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_RANK_NODE_POOL: "400",
        CHAOS_GHOSTNETWORK_RANK_TERRITORY_POOL: "300",
        CHAOS_GHOSTNETWORK_RANK_CONFLICT_POOL: "200",
        CHAOS_GHOSTNETWORK_RANK_CLOSER_POOL: "100"
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
      restart_delay: 2000,
      env: {
        PYTHONUNBUFFERED: "1",
        CHAOS_GHOSTNETWORK_RUNTIME_MODE: "development",
        CHAOS_GHOSTNETWORK_DROPS_ENABLED: "true",
        CHAOS_GHOSTNETWORK_DROP_CHANCE: "0.04",
        CHAOS_GHOSTNETWORK_MIN_PART_DISTANCE_KM: "50",
        CHAOS_GHOSTNETWORK_ABILITIES_ENABLED: "true",
        CHAOS_GHOSTNETWORK_ABILITY_ALLOWED_CODES: "insider_feed,service_entrance,false_image,hostile_takeover,operational_prediction,expose,narrative_takeover,full_disclosure,resistance_signal,domino_effect,phantom_node,glitch_injection,false_tracking,network_fracture,reflection,integrity_scan,bastion,rollback,trust_corridor,quarantine",
        CHAOS_GHOSTNETWORK_ABILITY_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS: "3600",
        CHAOS_GHOSTNETWORK_SIGNAL_NODE_HOLDER_RSP: "8",
        CHAOS_GHOSTNETWORK_SIGNAL_CLOSER_RSP: "20",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_RSP: "8",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_PRIMARY_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONFLICT_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_OVERLAP_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONSUMPTION_ENABLED: "1",
        CHAOS_GHOSTNETWORK_SIGNAL_SHOW_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_RANK_NODE_POOL: "400",
        CHAOS_GHOSTNETWORK_RANK_TERRITORY_POOL: "300",
        CHAOS_GHOSTNETWORK_RANK_CONFLICT_POOL: "200",
        CHAOS_GHOSTNETWORK_RANK_CLOSER_POOL: "100"
      }
    }
  ]
};
