module.exports = {
  apps: [
    {
      name: "chaos",
      cwd: "/home/johndoe/app/chaos",
      script: "/home/johndoe/app/chaos/.venv/bin/gunicorn",
      args: "run:app --bind 127.0.0.1:6666 --workers 4 --timeout 120 --access-logfile - --error-logfile -",
      interpreter: "none",
      env: {
        APP_ENV: "staging",
        PORT: "6666",
        CHAOS_OPERATION_FEEDBACK_ENABLED: "1",
        CHAOS_OPERATION_FEEDBACK_ACTIONS: "scan_ports,exploit,sniff,trace,trace_gps,trace_device,mic_sniff,atm_logs,install_sniffer,camera_stream,camera_shutdown,car_hack",
        CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED: "1",
        CHAOS_CYBERNER_CHANNEL_STORE_ENABLED: "1",
        CHAOS_CYBERNER_WORLD_STORE_ENABLED: "1",
        CHAOS_CYBERNER_CLAN_STORE_ENABLED: "1",
        CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED: "1",
        CHAOS_GHOSTNETWORK_RUNTIME_MODE: "development",
        CHAOS_GHOSTNETWORK_DROPS_ENABLED: "true",
        CHAOS_GHOSTNETWORK_DROP_CHANCE: "0.004"
      }
    }
  ]
};
