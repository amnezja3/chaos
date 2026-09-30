"""Real wallet/inventory regression for a purchase after canonical confiscation."""
import copy
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

import run
from tests import test_agi2108_console as fixtures


class GoogleplexRepurchaseTest(unittest.TestCase):
    setUp = fixtures.Agi2108BoundedInstallTest.setUp
    tearDown = fixtures.Agi2108BoundedInstallTest.tearDown
    def check_repurchase(self, bounded):
        offer = dict(self.app, id='creator_nmap', name='nmap', price=100,
                     type='scanner', bounded_install=bounded, purchase_account='admin')
        profile = self.users.get_profile('alice')
        inventory = self.inventory

        def sync(**kwargs):
            return inventory.mirror_profile('alice', copy.deepcopy(profile))

        class Manager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                updated = sync()
                updated.update(updates)
                inventory.write_from_profile(self.username, updated)

        def transfer(source, target, amount, **kwargs):
            result = self.wallet.transfer(source, target, amount, **kwargs)
            return dict(result, balance=result['source_balance'])

        with ExitStack() as stack:
            patches = {
                'wallet_balance_store': self.wallet,
                'player_inventory_store': self.inventory,
                'system_message_store': Mock(),
                'get_app_catalog': Mock(return_value=[offer]),
                'sync_session_profile': Mock(side_effect=sync),
                'canonical_wallet_balance': self.wallet.get_balance,
                'UserProfileManager': Manager,
                'ensure_purchase_account_profile': Mock(return_value={'username': 'admin'}),
                'record_storage_delta': Mock(),
                'record_apps_delta': Mock(),
                'record_wallet_balance_delta': Mock(),
                'add_cyberner_direct_notification': Mock(),
            }
            for name, value in patches.items():
                stack.enter_context(patch.object(run, name, value))
            stack.enter_context(patch.object(run.resources_store, 'get', return_value=[]))
            stack.enter_context(patch.object(run.resources_store, 'set'))
            stack.enter_context(patch.object(run.user_store, 'get_profile', return_value={'username': 'admin'}))
            stack.enter_context(patch.object(run.wallet_store, 'transfer', side_effect=transfer))

            def purchase(expected_status=200):
                with run.app.test_request_context('/install-app', method='POST', json={'app_id': offer['id']}):
                    run.session['user'] = 'alice'
                    response = run.app.make_response(run.install_app())
                    if expected_status == 200:
                        self.assertEqual(response.status_code, 200, response.json)
                    else:
                        self.assertGreaterEqual(response.status_code, 400, response.json)
                    return response.json

            first = purchase()
            self.assertTrue(purchase()['duplicate'])
            self.assertEqual(self.wallet.get_balance('alice'), 24900)
            # The canonical consequence executor uses this same atomic removal.
            self.assertTrue(self.inventory.uninstall_app('alice', app_id=offer['id']))
            if bounded:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=2) as pool:
                    responses = list(pool.map(lambda _: purchase(), range(2)))
                self.assertEqual(sum(not r['duplicate'] for r in responses), 1)
                second = next(r for r in responses if not r['duplicate'])
            else:
                second = purchase()
            self.assertFalse(second.get('duplicate', False))
            self.assertTrue(purchase()['duplicate'])
            self.assertEqual(self.wallet.get_balance('alice'), 24800)
            self.assertEqual(self.wallet.get_balance('admin'), 200)
            self.assertNotEqual(first['app']['wallet_transaction_key'], second['app']['wallet_transaction_key'])
            self.assertEqual(patches['add_cyberner_direct_notification'].call_count, 2)
            self.assertTrue(self.inventory.has_app('alice', offer['id']))
            if bounded:
                self.assertEqual(self.inventory.catalog_download_counts([offer['id']])[offer['id']], 2)
            # Another confiscation with an empty wallet must not restore the tool.
            self.inventory.uninstall_app('alice', app_id=offer['id'])
            self.wallet.debit('alice', 24800, transaction_key='test:empty-wallet')
            purchase(expected_status=400)
            self.assertFalse(self.inventory.has_app('alice', offer['id']))
            self.assertEqual(self.wallet.get_balance('admin'), 200)
            self.assertEqual(patches['add_cyberner_direct_notification'].call_count, 2)

    def test_bounded_repurchase_after_confiscation(self):
        self.check_repurchase(True)

    def test_legacy_repurchase_after_confiscation(self):
        self.check_repurchase(False)
