import unittest
from pathlib import Path


class PoiFetcherLatencyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("poiFetchClass.py").read_text(encoding="utf-8")

    def test_scan_has_bounded_remote_budget_and_cache(self):
        self.assertIn("endpoint_limit: int = 2", self.source)
        self.assertIn('CHAOS_OVERPASS_TIMEOUT_SECONDS", "8"', self.source)
        self.assertIn("self._cache_lock", self.source)
        self.assertIn("Overpass cache hit", self.source)
        self.assertIn("Overpass stale cache fallback", self.source)


if __name__ == "__main__":
    unittest.main()
