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
      kill_timeout: 10000,
      env: {
        PYTHONUNBUFFERED: "1",
        CHAOS_OLLAMA_WORKER_ENABLED: "false",
        CHAOS_OLLAMA_BASE_URL: "http://127.0.0.1:11434",
        CHAOS_OLLAMA_MODEL: "llama3.1:8b",
        CHAOS_OLLAMA_MODEL_DIGEST: "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
        CHAOS_OLLAMA_RUNTIME_VERSION: "0.15.4",
        CHAOS_OLLAMA_QUANTIZATION: "Q4_K_M",
        CHAOS_OLLAMA_NUM_CTX: "4096",
        CHAOS_OLLAMA_NUM_PREDICT: "512",
        CHAOS_OLLAMA_TEMPERATURE: "0",
        CHAOS_OLLAMA_KEEP_ALIVE: "5m",
        CHAOS_OLLAMA_CONNECT_TIMEOUT_SEC: "2",
        CHAOS_OLLAMA_READ_TIMEOUT_SEC: "120",
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
