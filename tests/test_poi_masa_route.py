"""Real map-action on fixture accounts; no production world or upstream HTTP."""
import os
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

import run
import test_ghostlab_scanner as fixtures
from database import WalletBalanceStore
from poiFetchClass import POIFetcher
from poi_infrastructure.service import Service


class MasaRouteTest(unittest.TestCase):
    def test_endpoint_contract_costs_and_non_masa_denials(self):
        fixture = fixtures.ScannerTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        stack = fixture.stack
        stack.enter_context(patch.dict(os.environ, CHAOS_POI_INFRASTRUCTURE_ENABLED='1', CHAOS_POI_MASA_UX_ENABLED='1'))
        fetcher = POIFetcher()
        fetcher.endpoints = ['https://fixture.invalid']
        transport = Mock(return_value=(200, None, {'elements': [
            {'type': 'node', 'id': 1, 'lat': 52, 'lon': 21,
             'tags': {'office': 'company', 'name': 'Fixture office'}}]}))
        service = Service(Path(fixture.tmp.name)/'poi.sqlite3', transport=transport)
        fetcher._poi_service = service
        stack.enter_context(patch.object(run, 'fetcher', fetcher))
        stack.enter_context(patch.object(run, 'GHOSTNETWORK_ABILITIES_ENABLED', False))
        stack.enter_context(patch.object(run.player_position_store, 'get_position', return_value={'lat':52, 'lng':21}))
        distance = stack.enter_context(patch.object(run.Haversine, 'haversine_distance', return_value=1))
        stack.enter_context(patch.object(run, 'foreign_territory_action_block', return_value=None))
        stack.enter_context(patch.object(run.player_marked_target_store, 'list_targets', return_value=[]))
        snapshot = stack.enter_context(patch.object(run.player_scan_snapshot_store, 'record', return_value={'scan_id':'fixture'}))
        wallet = WalletBalanceStore(fixture.path)
        stack.enter_context(patch.object(run, 'wallet_balance_store', wallet))
        balance = wallet.get_balance('attacker')
        body = {'action':'scan', 'lat':52, 'lng':21}
        with fixture.no_heavy():
            first = fixture.client.post('/map-action', json=body).json
            self.assertEqual(first['interference']['state'], 'ready')
            self.assertEqual(first['scan_outcome'], 'success')
            with service.repo.transaction() as c:
                c.execute('UPDATE cache SET fetched=?', (time.time()-400,))
            transport.return_value = (503, '60', None)
            stale = fixture.client.post('/map-action', json=body).json
            self.assertEqual(stale['interference']['state'], 'degraded')
            self.assertEqual(stale['markers'], first['markers'])
            with service.repo.transaction() as c: c.execute('DELETE FROM cache')
            snapshot.reset_mock()
            calls = transport.call_count
            blocked = fixture.client.post('/map-action', json=body).json
            self.assertEqual(blocked['interference']['state'], 'blocked')
            self.assertEqual(blocked['scan_outcome'], 'api_error')
            self.assertEqual(transport.call_count, calls)
            snapshot.assert_not_called()
            self.assertEqual(wallet.get_balance('attacker'), balance)
            distance.return_value = 999999
            denied = fixture.client.post('/map-action', json=body).json
            self.assertEqual(denied['scan_outcome'], 'denied')
            self.assertNotIn('interference', denied)
            distance.return_value = 1
            inactive = fixture.client.post('/map-action', json=dict(body, deep_scanner_token='invalid'))
            self.assertEqual(inactive.status_code, 409)
            self.assertNotIn('interference', inactive.json)
            with patch.dict(os.environ, CHAOS_POI_MASA_UX_ENABLED='0'):
                self.assertNotIn('interference', fixture.client.post('/map-action', json=body).json)
            with patch.object(fetcher, 'get_all', side_effect=RuntimeError('SECRET PROVIDER URL')):
                error = fixture.client.post('/map-action', json=body).json
                self.assertNotIn('interference', error)
                self.assertNotIn('SECRET', str(error))
        with fixture.client.session_transaction() as session: session.clear()
        unauthenticated = fixture.client.post('/map-action', json=body)
        self.assertNotIn('interference', unauthenticated.json or {})


if __name__ == '__main__': unittest.main()
