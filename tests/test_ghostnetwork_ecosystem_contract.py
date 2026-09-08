import re
import unittest
from pathlib import Path

from ghostnetwork.ability_realizers import GhostAbilityProductionRealizer


class GhostNetworkEcosystemContractTest(unittest.TestCase):
    def test_web_worker_and_example_keep_the_complete_superpower_environment(self):
        expected_codes = set(GhostAbilityProductionRealizer.ABILITY_FAMILIES)
        files = {
            "ecosystem.web.config.js": 1,
            "ecosystem.territory-worker.config.js": 1,
            "ecosystem.config.example.js": 2,
        }
        for filename, expected_occurrences in files.items():
            with self.subTest(filename=filename):
                source = Path(filename).read_text(encoding="utf-8")
                allowlists = re.findall(
                    r'CHAOS_GHOSTNETWORK_ABILITY_ALLOWED_CODES:\s*"([^"]+)"',
                    source,
                )
                self.assertEqual(expected_occurrences, len(allowlists))
                for allowlist in allowlists:
                    self.assertEqual(expected_codes, set(allowlist.split(",")))
                self.assertEqual(
                    expected_occurrences,
                    source.count('CHAOS_GHOSTNETWORK_ABILITIES_ENABLED: "true"'),
                )
                self.assertEqual(
                    expected_occurrences,
                    source.count('CHAOS_GHOSTNETWORK_ABILITY_DURATION_SECONDS: "900"'),
                )
                self.assertEqual(
                    expected_occurrences,
                    source.count('CHAOS_GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS: "3600"'),
                )


if __name__ == "__main__":
    unittest.main()
