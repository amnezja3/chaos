"""Grouped offline regressions for the final 163.5 deployment; isolated test DBs."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    'test_world_regular_collection.py', 'test_world_discovery*.py',
    'test_world_routing*.py', 'test_world_read.py', 'test_world_maplark_region.py',
    'test_world_land_water*.py', 'test_world_natural_earth.py',
    'test_world_dashboard.py', 'test_world_viewport.py',
    'test_world_archive_retention.py', 'test_world_collection_retention.py',
    'test_world_worker_heartbeat.py', 'test_world_credit_budget.py',
    'test_world_recurring_budget.py', 'test_poi_providers.py',
)


def main():
    sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for pattern in PATTERNS:
        part = loader.discover(str(ROOT / 'tests'), pattern=pattern)
        if not part.countTestCases():
            raise RuntimeError('Missing regression suite: ' + pattern)
        suite.addTests(part)
    return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
