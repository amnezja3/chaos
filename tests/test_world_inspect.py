import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('world_inspect', ROOT / 'tools/world_discovery_inspect.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InspectTests(unittest.TestCase):
    def test_synthetic_manifest_does_not_grant_gameplay_or_network(self):
        body, digest = module.read_json(ROOT / 'tests/fixtures/poi/world_maplark_synthetic.json')
        headers, _ = module.read_json(ROOT / 'tests/fixtures/poi/world_maplark_headers_synthetic.json')
        with patch('socket.socket', side_effect=AssertionError('unexpected network')):
            result = module.inspect('maplark', body, headers)
        self.assertEqual(result['objects'], 3)
        self.assertEqual(result['layers'], {'poi': 1, 'roads': 1, 'inland_water': 1})
        self.assertFalse(result['gameplay_approved'])
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(len(digest), 64)
        self.assertNotIn('coordinates', json.dumps(result))
