import copy
import unittest
from unittest.mock import patch

import run
from ghost_i18n import translator


class CatalogLocaleTest(unittest.TestCase):
    def test_legacy_system_fields_are_projected_without_reinstall_or_translating_forks(self):
        import json
        from pathlib import Path
        from catalog_presentation import legacy_presentation, legacy_sources
        seeds = json.loads((Path(run.__file__).parent / 'static/app_config.json').read_text(encoding='utf8'))
        for seed in [p for p in seeds if p['id'] in legacy_sources()]:
            before = copy.deepcopy(seed)
            projected = legacy_presentation(seed)
            self.assertEqual(seed, before)
            for i, level in enumerate(projected['levels']):
                self.assertEqual({k: v for k, v in level.items() if k != '_system_i18n'}, before['levels'][i])
                for entry in level['_system_i18n'].values():
                    self.assertNotEqual(translator().t(entry['key'], locale='en'), entry['key'])
            fork = legacy_presentation(dict(seed, generated=True, creator_username='player'))
            self.assertNotIn('presentation_i18n', fork)
            self.assertTrue(all('_system_i18n' not in level for level in fork['levels']))
        seed = seeds[0]
        edited = legacy_presentation(dict(seed, description='Opis gracza <PL>'))
        self.assertNotIn('description', edited['presentation_i18n'])
        self.assertEqual(edited['description'], 'Opis gracza <PL>')
        forged = legacy_presentation(dict(seed, generated=True, levels=projected['levels']))
        self.assertTrue(all('_system_i18n' not in level for level in forged['levels']))

    def test_pvp_result_presentation_preserves_authored_messages_and_receipts(self):
        for artifact in (None, 'immutable-author-build'):
            payload = dict(success=True, result_type='financial_sniffer', stolen_amount=17,
                           message='lab.pvp.result.financial', receipt='unchanged', duplicate=True,
                           tool={'id': 'tool', 'artifact_id': artifact})
            with run.app.test_request_context('/api/player-hack/tool/use', method='POST'):
                result = run.player_hack_tool_message_presentation(run.jsonify(payload)).get_json()
            self.assertEqual({k: v for k, v in result.items() if k != 'message_i18n'}, payload)
            if artifact:
                self.assertNotIn('message_i18n', result)
            else:
                self.assertEqual(result['message_i18n']['params'], {'amount': 17})
                self.assertIn('17', translator().t(result['message_i18n']['key'], {'amount': 17}, 'en'))

    def test_code_owned_products_have_complete_presentation_without_mutating_contracts(self):
        originals = copy.deepcopy(run.PRO_SYSTEM_TOOLS + run.CREATOR_SYSTEM_APPS + run.GOOGLEPLEX_EFFECT_PRODUCTS)
        products = run.pro_system_tools_catalog() + run.creator_system_apps_catalog() + run.googleplex_product_catalog()
        self.assertEqual(len(products), 38)
        for item in products:
            self.assertEqual(item['presentation_owner'], 'system')
            for field, message in item['presentation_i18n'].items():
                for locale in ('pl', 'en'):
                    translated = translator().t(message['key'], message['params'], locale)
                    self.assertTrue(translated)
                    self.assertNotEqual(translated, message['key'])
                if field == 'description':
                    self.assertIn(translator().t(message['key'], locale='en'), item['search_aliases'])
        self.assertEqual(originals, run.PRO_SYSTEM_TOOLS + run.CREATOR_SYSTEM_APPS + run.GOOGLEPLEX_EFFECT_PRODUCTS)

    def test_player_catalog_cannot_inherit_builtin_presentation(self):
        authored = {'id': 'creator_test', 'name': 'Bilet: Londyn', 'description': 'catalog.system.ticket_londyn.description',
                    'presentation_owner': 'system', 'presentation_i18n': {'name': {'key': 'catalog.system.ticket_londyn.name'}},
                    'search_aliases': ['injected'], 'price': 10}
        with patch.object(run.resources_store, 'get', return_value=[authored]), \
             patch.object(run.creator_store, 'catalog', return_value=[]), \
             patch.object(run.player_inventory_store, 'catalog_download_counts', return_value={}):
            product = next(item for item in run.get_app_catalog() if item['id'] == authored['id'])
        self.assertEqual(product['name'], authored['name'])
        self.assertEqual(product['description'], authored['description'])
        self.assertNotIn('presentation_i18n', product)
        self.assertNotIn('search_aliases', product)

    def test_ticket_public_projection_retains_keys_without_exposing_coordinates(self):
        from ghostlab_ticket_policy import public_ticket
        ticket = next(item for item in run.googleplex_product_catalog() if item['id'] == 'ticket_londyn')
        projected = public_ticket(dict(ticket, destination={'lat': 51, 'lon': 0, 'city': 'Londyn'}))
        self.assertEqual(projected['presentation_i18n'], ticket['presentation_i18n'])
        self.assertNotIn('lat', projected['destination'])
        self.assertEqual(projected['travel_city'], 'Londyn')

    def test_exchange_presentation_preserves_sale_and_duplicate_receipt(self):
        for duplicate in (False, True):
            payload = {'success': True, 'duplicate': duplicate, 'sale': {'price': 73, 'file_id': 'author-file'},
                       'balance': 123, 'message': 'legacy', 'files': []}
            with run.app.test_request_context('/api/ghost-exchange/sell', method='POST'):
                result = run.ghost_exchange_message_presentation(run.jsonify(payload)).get_json()
            self.assertEqual({k: v for k, v in result.items() if k != 'message_i18n'}, payload)
            message = result['message_i18n']
            self.assertEqual(message['params'], {'amount': 73})
            self.assertEqual(message['key'], 'apps.exchange.sale_duplicate' if duplicate else 'apps.exchange.sale_completed')
            for locale in ('pl', 'en'):
                self.assertIn('73', translator().t(message['key'], message['params'], locale))

    def test_historical_builtin_installs_project_only_unedited_fields(self):
        from catalog_presentation import installed_presentation
        originals = run.PRO_SYSTEM_TOOLS + run.CREATOR_SYSTEM_APPS + run.GOOGLEPLEX_EFFECT_PRODUCTS
        builtins = {item['id']: item for item in run.pro_system_tools_catalog() + run.creator_system_apps_catalog() + run.googleplex_product_catalog()}
        for original in originals:
            installed = copy.deepcopy(original)
            projected = installed_presentation(installed, builtins)
            self.assertIn('presentation_i18n', projected, original['id'])
            self.assertEqual(projected['presentation_i18n']['name']['key'], 'catalog.system.'+original['id']+'.name')
            self.assertEqual(installed, original)
            installed['description'] = 'Opis mojego wariantu'
            projected = installed_presentation(installed, builtins)
            self.assertNotIn('description', projected['presentation_i18n'])
            self.assertEqual(projected['description'], 'Opis mojego wariantu')

    def test_hack_action_presentation_keeps_ids_and_cooldown(self):
        cases = [({'success':False,'blocked':True,'reason':'invalid_tool'}, 'invalid_tool'),
                 ({'success':False,'blocked':True,'cooldown_seconds_left':30}, 'cooldown'),
                 ({'success':True,'matching_apps':[{'id':'stable'}],'pending_action':{'action':'car_hack'}}, 'choose'),
                 ({'success':True,'duplicate':True,'captured_target':{'id':'car:stable'}}, 'already_captured')]
        for payload, key in cases:
            with run.app.test_request_context('/hack-action', method='POST'):
                result = run.hack_action_message_presentation(run.jsonify(payload)).get_json()
            self.assertEqual({k:v for k,v in result.items() if k!='message_i18n'}, payload)
            self.assertEqual(result['message_i18n']['key'], 'map.launch.'+key)

    def test_install_envelope_keeps_receipt_amount_and_legacy_response(self):
        payload = {'status': 'success', 'duplicate': True, 'hackcoins': 80, 'price': 20, 'receipt': 'stable',
                   'message': 'Oryginalny komunikat', 'app_id': 'unchanged'}
        with run.app.test_request_context('/install-app', method='POST'):
            result = run.install_app_message_presentation(run.jsonify(payload)).get_json()
        self.assertEqual({key: value for key, value in result.items() if key != 'message_i18n'}, payload)
        self.assertEqual(result['message_i18n']['key'], 'shop.installed')
        with run.app.test_request_context('/install-app', method='POST'):
            response = run.jsonify(status='error', reason='offer_changed', message='legacy')
            response.status_code = 409
            result = run.install_app_message_presentation(response)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json['reason'], 'offer_changed')
        self.assertEqual(result.json['message_i18n']['key'], 'shop.offer_changed')
