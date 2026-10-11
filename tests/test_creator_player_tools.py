"""Generated ordinary PvP tools use the canonical player executor, not GhostLab."""
import unittest
from unittest.mock import patch, Mock
import run
import test_player_launcher_hot_path as launcher
from creator_policy import generate_contract, PLAYER_ACTIONS, INTERFACES, SECURITY_KEYS


class CreatorPlayerToolsTest(unittest.TestCase):
    setUp = launcher.PlayerLauncherHotPathTest.setUp
    seed = launcher.PlayerLauncherHotPathTest.seed
    prepare = launcher.PlayerLauncherHotPathTest.prepare
    setup_selection = launcher.PlayerLauncherHotPathTest.setup_selection
    mark = launcher.PlayerLauncherHotPathTest.mark
    setup_launcher = launcher.PlayerLauncherHotPathTest.setup_launcher

    def product(self, purpose, interface='window', creates_file=False):
        contract = generate_contract(dict(action=purpose, interface=interface, creates_file=creates_file),
                                     40, Mock(random=lambda: 0))
        return run.build_creator_edition(dict(id=purpose + interface, app_id=purpose + interface,
            owner='attacker', contract=contract, presentation_locale='en',
            presentation={'name': purpose + interface, 'icon': 'X'}), 1)

    def test_all_interfaces_match_only_their_player_step(self):
        for interface in INTERFACES:
            products = [self.product(purpose, interface) for purpose in PLAYER_ACTIONS]
            for purpose, step in PLAYER_ACTIONS.items():
                with self.subTest(interface=interface, purpose=purpose):
                    matched, _ = run.get_apps_for_target_action(products, step, {'target_mode': 'player'})
                    self.assertEqual([p['id'] for p in matched], [purpose + interface])
                    for source in ('poi', 'camera', 'vehicle', 'person', 'atm'):
                        self.assertEqual(run.get_apps_for_target_action(products, step, {'source_type': source})[0], [])

    def test_generated_chain_picker_launch_execution_and_replay(self):
        self.setup_launcher()
        target = self.targets.get_active_target('attacker')
        target['security'] = dict.fromkeys(SECURITY_KEYS, True)
        self.targets.upsert_aimed('attacker', target)
        for purpose, step in PLAYER_ACTIONS.items():
            product = self.product(purpose, creates_file=purpose == 'scan_player')
            self.inventory.install_app('attacker', product, purchase_key=purpose)
            payload = dict(self.payload, action=step, selected_app_id='', _client_action_key=purpose)
            with patch.object(run, 'PROVISIONAL_APP_LAUNCH_ENABLED', True):
                picker = self.client.post('/hack-action', json=payload)
            self.assertEqual(picker.status_code, 200, picker.json)
            self.assertIn(product['id'], [item['id'] for item in picker.json['matching_apps']])
            launched = self.client.post('/hack-action', json=dict(payload, selected_app_id=product['id']))
            self.assertEqual(launched.status_code, 200, launched.json)
            queue = self.inventory.consume_launches('attacker')
            self.assertEqual(len(queue), 1)
            target = self.targets.get_active_target('attacker')
            self.assertFalse(target['actions_allowed'].get(step), 'Launch must not complete generated tools')
            execution = {'app_id': product['id'], 'expected_target': target,
                         'launch_receipt': queue[0]['receipt']}
            result = self.client.post('/gonna-win', json=execution)
            self.assertEqual(result.status_code, 200, result.json)
            self.assertTrue(result.json['success'], result.json)
            if purpose == 'scan_player':
                self.assertTrue(result.json.get('created_files'), result.json)
            if purpose in {'sniff_player', 'trace_player'}:
                operations = result.json['created_operations']
                self.assertEqual(len(operations), 1)
                self.assertEqual(operations[0]['target_id'], 'player:victim')
                self.assertEqual(operations[0]['operation_type'],
                                 'persistent_sniffer' if purpose == 'sniff_player' else 'generic_trace')
                self.assertTrue(operations[0]['creator_creates_file'])
            repeat = self.client.post('/gonna-win', json=execution)
            self.assertEqual(repeat.status_code, 200, repeat.json)
            if purpose != 'trace_player':
                self.assertTrue(self.targets.get_active_target('attacker')['actions_allowed'][step])
            else:
                self.assertTrue(result.json.get('player_hack_access'), result.json)

    def test_map_tool_and_wrong_player_purpose_rejected(self):
        self.setup_launcher()
        for purpose in ('scan_ports', 'exploit_player'):
            product = self.product(purpose)
            self.inventory.install_app('attacker', product, purchase_key=purpose)
            result = self.client.post('/hack-action', json=dict(self.payload,
                selected_app_id=product['id'], _client_action_key=purpose))
            self.assertGreaterEqual(result.status_code, 400, result.json)
            self.assertEqual(self.inventory.consume_launches('attacker'), [])

    def test_exploit_keeps_rolled_power_and_interface_choice_validation(self):
        from creator_policy import runtime_effect
        for interface in INTERFACES:
            product = self.product('exploit_player', interface)
            product['creator_contract']['power'] = 40
            choice = 0 if interface == 'button_choices' else None
            effect = runtime_effect(product, dict.fromkeys(SECURITY_KEYS, True), choice)
            self.assertEqual(len(effect), len(SECURITY_KEYS) * 40 // 100)
            self.assertTrue(all(value is False for value in effect.values()))
            if interface == 'button_choices':
                with self.assertRaises(ValueError):
                    runtime_effect(product, dict.fromkeys(SECURITY_KEYS, True))
