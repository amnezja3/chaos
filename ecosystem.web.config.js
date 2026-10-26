module.exports = {
  apps: [
    {
      name: "chaos",
      cwd: "/home/johndoe/app/chaos",
      script: "/home/johndoe/app/chaos/.venv/bin/gunicorn",
      args: "run:app --bind 127.0.0.1:6666 --workers 4 --timeout 120 --access-logfile - --error-logfile -",
      interpreter: "none",
      env: {
        // Sprint 161: production scanner; budgets live in the POI database.
        // API credentials remain in the private server environment, never Git.
        CHAOS_POI_INFRASTRUCTURE_ENABLED: "1",
        CHAOS_POI_MAPLARK_ENABLED: "1",
        CHAOS_POI_ROUTING_ENABLED: "0", // Enable only after controlled routing acceptance.
        CHAOS_POI_MAPLARK_PILOT_ENABLED: "0",
        CHAOS_MAPLARK_ACCEPT_VARIABLE_COST: "1",
        CHAOS_MAPLARK_CREDIT_RESERVATION: "20",
        // Sprint 162: persistence pilot passed; disable scope for rollback acceptance.
        // Normal MapLark scans and the credit ledger remain active.
        CHAOS_POI_WORLD_INGEST_ENABLED: "0",
        CHAOS_POI_WORLD_REPOSITORY_ENABLED: "0",
        CHAOS_POI_WORLD_ACCESS_MODE: "pilot",
        CHAOS_POI_WORLD_REGIONAL_READ_ENABLED: "0",
        CHAOS_POI_WORLD_VISITS_ENABLED: "0",
        CHAOS_POI_WIDE_FETCH_ENABLED: "0",
        CHAOS_POI_SCAN_NETWORK_PAUSED: "0",
        CHAOS_POI_WORLD_PILOT_USER: "",
        CHAOS_POI_WORLD_PILOT_CENTER: "",
        CHAOS_POI_WORLD_PILOT_UNTIL: "0",
        // Schema v2 and gameplay verified on VPS; collect demand without background HTTP.
        CHAOS_POI_DISCOVERY_MODE: "passive",
        // Sprint 163: live scans take admission priority over the bounded roads pilot.
        CHAOS_POI_PRIORITY_ENABLED: "1",
        // Apply tools/poi_world.py --metrics before enabling aggregate writes.
        CHAOS_POI_METRICS_ENABLED: "1",
        // Enable explicitly after the offline 148 project migration.
        CHAOS_CREATORS_V2_ENABLED: process.env.CHAOS_CREATORS_V2_ENABLED || "false",
        CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_TRAVEL_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_MAINTENANCE_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_FIRMWARE_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_SCANNER_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_PTK_ENABLED: "true",
        CHAOS_GHOSTLAB_FINANCIAL_SNIFFER_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_FRIEND_KICKER_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_SECURITY_PANEL_PROXY_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_ARSENAL_CLEANER_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_INTRUDER_KICKER_RUNTIME_ENABLED: "true",
        CHAOS_GHOSTLAB_RUNTIME_ACTORS: "*",
        CHAOS_RESPONSE_QUALIFICATION_MODE: "observe",
        CHAOS_RESPONSE_ENCOUNTERS_ENABLED: "true",
        CHAOS_RESPONSE_EXECUTION_MODE: "enforce",
        CHAOS_RESPONSE_EXECUTION_ACTORS: "*",
        CHAOS_RESPONSE_DETENTION_ENABLED: "true", // 143.5 gates installed; applies only to new eligible encounters.
        CHAOS_NARRATIVE_TTL_URGENT_SECONDS: "1800",
        CHAOS_NARRATIVE_TTL_NORMAL_SECONDS: "7200",
        CHAOS_NARRATIVE_TTL_EDITORIAL_SECONDS: "21600",
        CHAOS_NARRATIVE_PRIORITY_URGENT: "300",
        CHAOS_NARRATIVE_PRIORITY_NORMAL: "200",
        CHAOS_NARRATIVE_PRIORITY_EDITORIAL: "100",
        APP_ENV: "staging",
        PORT: "6666",
        CHAOS_OPERATION_FEEDBACK_ENABLED: "1",
        CHAOS_OPERATION_FEEDBACK_ACTIONS: "scan_ports,exploit,sniff,trace,trace_gps,trace_device,mic_sniff,atm_logs,install_sniffer,camera_stream,camera_shutdown,car_hack",
        CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED: "1",
        CHAOS_CYBERNER_CHANNEL_STORE_ENABLED: "1",
        CHAOS_CYBERNER_WORLD_STORE_ENABLED: "1",
        CHAOS_CYBERNER_CLAN_STORE_ENABLED: "1",
        CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED: "1",
        CHAOS_PROFILE_WRITE_METRICS: "1",
        CHAOS_GHOSTNETWORK_RUNTIME_MODE: "development",
        CHAOS_GHOSTNETWORK_DROPS_ENABLED: "true",
        CHAOS_GHOSTNETWORK_DROP_CHANCE: "0.04",
        CHAOS_GHOSTNETWORK_MIN_PART_DISTANCE_KM: "50",
        CHAOS_GHOSTNETWORK_ABILITIES_ENABLED: "true",
        CHAOS_GHOSTNETWORK_ABILITY_ALLOWED_CODES: "insider_feed,service_entrance,false_image,hostile_takeover,operational_prediction,expose,narrative_takeover,full_disclosure,resistance_signal,domino_effect,phantom_node,glitch_injection,false_tracking,network_fracture,reflection,integrity_scan,bastion,rollback,trust_corridor,quarantine",
        CHAOS_GHOSTNETWORK_ABILITY_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS: "3600",
        CHAOS_GHOSTNETWORK_SIGNAL_NODE_HOLDER_RSP: "800",
        CHAOS_GHOSTNETWORK_SIGNAL_CLOSER_RSP: "2000",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_RSP: "800",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_PRIMARY_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONFLICT_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_OVERLAP_MULTIPLIER: "1.0",
        CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONSUMPTION_ENABLED: "1",
        CHAOS_GHOSTNETWORK_SIGNAL_SHOW_DURATION_SECONDS: "900",
        CHAOS_GHOSTNETWORK_RANK_NODE_POOL: "400",
        CHAOS_GHOSTNETWORK_RANK_TERRITORY_POOL: "300",
        CHAOS_GHOSTNETWORK_RANK_CONFLICT_POOL: "200",
        CHAOS_GHOSTNETWORK_RANK_CLOSER_POOL: "100"
      },
      // Explicit rollout/rollback profiles; normal reload retains the parked baseline.
      env_routing: { CHAOS_POI_ROUTING_ENABLED: "1" },
      env_baseline: { CHAOS_POI_ROUTING_ENABLED: "0" }
    }
  ]
};
