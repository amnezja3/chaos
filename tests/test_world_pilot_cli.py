import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from poi_infrastructure.repository import Repository
from poi_infrastructure.world_contract import ContractError
from tools.world_discovery_pilot import operate


class PilotCliTests(unittest.TestCase):
    def test_dry_run_neither_creates_database_nor_calls_api(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'absent.db'
            with patch('socket.socket',side_effect=AssertionError('network')):
                self.assertEqual(operate(path,'prepare')['status'],'plan')
            self.assertFalse(path.exists())

    def test_prepare_disabled_cannot_enable_untested_or_reset_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'poi.db'; Repository(path).initialize()
            result=operate(path,'prepare',apply=True)
            self.assertFalse(result['enabled'])
            from poi_infrastructure.service import POIError
            with self.assertRaisesRegex(POIError,'not_approved'):
                operate(path,'enable',apply=True)
            with self.assertRaisesRegex(ContractError,'already_prepared'):
                operate(path,'prepare',apply=True)
            status=operate(path,'status',apply=True)
            self.assertEqual(status['budget_windows'][0]['credit_limit'],100)
            self.assertEqual(status['budget_windows'][0]['committed'],0)
