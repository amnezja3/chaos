module.exports = {
  apps: [
    {
      name: "chaos-ollama-worker",
      cwd: "/home/johndoe/app/chaos",
      script: "/home/johndoe/app/chaos/scripts/ollama_narrative_worker.py",
      args: ["run"],
      interpreter: "/home/johndoe/app/chaos/.venv/bin/python",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      // SIGTERM only stops the outer claim loop. Let the in-flight bounded
      // model call (240 s read timeout) finish before PM2 escalates to SIGKILL.
      kill_timeout: 300000,
      env: {
        CHAOS_RESPONSE_QUALIFICATION_MODE: "observe",
        CHAOS_RESPONSE_ENCOUNTERS_ENABLED: "true",
        CHAOS_RESPONSE_EXECUTION_MODE: "enforce",
        CHAOS_RESPONSE_EXECUTION_ACTORS: "*",
        CHAOS_NARRATIVE_TTL_URGENT_SECONDS: "1800",
        CHAOS_NARRATIVE_TTL_NORMAL_SECONDS: "7200",
        CHAOS_NARRATIVE_TTL_EDITORIAL_SECONDS: "21600",
        CHAOS_NARRATIVE_PRIORITY_URGENT: "300",
        CHAOS_NARRATIVE_PRIORITY_NORMAL: "200",
        CHAOS_NARRATIVE_PRIORITY_EDITORIAL: "100",
        PYTHONUNBUFFERED: "1",
        CHAOS_OLLAMA_WORKER_ENABLED: "true",
        CHAOS_OLLAMA_SOURCE_EVENT_ID: "",
        CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED: "false",
        CHAOS_OLLAMA_BASE_URL: "http://127.0.0.1:11434",
        CHAOS_OLLAMA_MODEL: "llama3.1:8b",
        CHAOS_OLLAMA_MODEL_DIGEST: "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
        CHAOS_OLLAMA_RUNTIME_VERSION: "0.15.4",
        CHAOS_OLLAMA_QUANTIZATION: "Q4_K_M",
        CHAOS_OLLAMA_NUM_CTX: "4096",
        CHAOS_OLLAMA_NUM_PREDICT: "192",
        CHAOS_OLLAMA_TEMPERATURE: "0",
        CHAOS_OLLAMA_KEEP_ALIVE: "5m",
        CHAOS_OLLAMA_CONNECT_TIMEOUT_SEC: "2",
        CHAOS_OLLAMA_READ_TIMEOUT_SEC: "240",
        CHAOS_OLLAMA_MAX_HTTP_RESPONSE_BYTES: "65536",
        CHAOS_OLLAMA_POLL_SECONDS: "1.5",
        CHAOS_OLLAMA_POLL_JITTER_SECONDS: "0.25",
        CHAOS_OLLAMA_LEASE_SECONDS: "180",
        CHAOS_OLLAMA_HEARTBEAT_SECONDS: "30",
        CHAOS_OLLAMA_PREFLIGHT_INTERVAL_SECONDS: "300",
        CHAOS_OLLAMA_PREFLIGHT_RETRY_SECONDS: "30"
      }
    }
  ]
};
