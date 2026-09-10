import re
from pathlib import Path
import unittest


class OllamaEcosystemShutdownContractTest(unittest.TestCase):
    def test_pm2_kill_timeout_exceeds_bounded_model_read_timeout(self):
        source = Path("ecosystem.ollama-worker.config.js").read_text(encoding="utf-8")
        kill_match = re.search(r"kill_timeout:\s*(\d+)", source)
        read_match = re.search(r'CHAOS_OLLAMA_READ_TIMEOUT_SEC:\s*"(\d+)"', source)
        self.assertIsNotNone(kill_match)
        self.assertIsNotNone(read_match)

        kill_timeout_ms = int(kill_match.group(1))
        read_timeout_ms = int(read_match.group(1)) * 1000
        self.assertGreaterEqual(kill_timeout_ms, read_timeout_ms + 30_000)

    def test_worker_remains_single_instance_with_explicit_opt_in(self):
        source = Path("ecosystem.ollama-worker.config.js").read_text(encoding="utf-8")
        self.assertIn("instances: 1", source)
        self.assertIn(
            'CHAOS_OLLAMA_WORKER_ENABLED: process.env.CHAOS_OLLAMA_WORKER_ENABLED || "false"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
