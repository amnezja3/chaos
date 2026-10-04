import unittest
from unittest.mock import patch
from flask import make_response
import run
from database import db_connect, WalletBalanceStore, GameStateDeltaBus, atomic_runtime_transaction
from creator_store import CreatorStore
from creator_payments import execute
from tests import test_capture_scoped_runtime as capture


class CreatorPaymentsTest(unittest.TestCase):
    setUp = capture.CaptureScopedRuntimeTest.setUp
    no_heavy = capture.CaptureScopedRuntimeTest.no_heavy

    def prepare(self, author='victim'):
        self.users.save_profile(capture.read_tests.valid_profile('victim'))
        self.users.save_profile(capture.read_tests.valid_profile('admin'))
        CreatorStore(self.path)
        self.wallet = WalletBalanceStore(self.path)
        self.bus = GameStateDeltaBus(self.path)
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', self.wallet))
        app = dict(id='paid-creator', name='Paid', creator_username=author, version=1,
            creator_contract_version=1, creator_contract=dict(interface='button_choices', options=[dict(price=10)], operation_types=[]))
        self.inventory.install_app('attacker', app, purchase_key='paid-install')
        with db_connect(self.path) as conn:
            conn.execute('CREATE TABLE test_effect (id TEXT PRIMARY KEY)')
        self.data = dict(app_id=app['id'], choice_id=0, launch_receipt='test-launch-0001', expected_target={'target_id':'test'})

    def operation(self):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("INSERT INTO test_effect VALUES('effect')")
            conn.commit()  # A nested store cannot commit the encompassing operation.
        return {'success': True}, 200

    def pay(self, operation=None):
        with run.app.app_context(), self.no_heavy():
            return execute('attacker', self.data, self.inventory, self.wallet, self.bus,
                           operation or self.operation, make_response)

    def test_success_retry_and_fallback_admin(self):
        self.prepare(author='deleted-author')
        before = self.wallet.get_balance('attacker'), self.wallet.get_balance('admin')
        first = self.pay()
        self.assertEqual(first.json['option_payment'], dict(amount=10, recipient='admin', success_only=True, reserved=0))
        self.assertEqual(self.pay().json, first.json)
        self.assertEqual(self.wallet.get_balance('attacker'), before[0] - 10)
        self.assertEqual(self.wallet.get_balance('admin'), before[1] + 10)

    def test_wallet_failure_rolls_back_effect_and_retry_can_execute(self):
        self.prepare()
        with patch.object(self.wallet, 'transfer', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError): self.pay()
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM test_effect').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT count(*) FROM creator_option_receipts').fetchone()[0], 0)
        self.assertEqual(self.pay().json['option_payment']['amount'], 10)

    def test_failure_does_not_charge(self):
        self.prepare()
        before = self.wallet.get_balance('attacker')
        response = self.pay(lambda: ({'success': False}, 400))
        self.assertEqual(response.json['option_payment']['amount'], 0)
        self.assertEqual(self.wallet.get_balance('attacker'), before)

    def test_own_option_uses_free_path(self):
        self.prepare(author='attacker')
        before = self.wallet.get_balance('attacker')
        self.assertIsNone(self.pay())
        self.assertEqual(self.wallet.get_balance('attacker'), before)

    def prepare_async(self):
        import json
        self.prepare()
        with db_connect(self.path) as conn:
            app = json.loads(conn.execute("SELECT app_json FROM player_apps WHERE username='attacker' AND app_id='paid-creator'").fetchone()[0])
            app['creator_contract']['operation_types'] = ['generic_trace']
            conn.execute("UPDATE player_apps SET app_json=? WHERE username='attacker' AND app_id='paid-creator'", (json.dumps(app),))
        def start():
            operation = dict(operation_id='async-test', owner_username='attacker', status='running', operation_type='generic_trace')
            with db_connect(self.path) as conn:
                conn.execute('''INSERT INTO player_operations(operation_id,username,status,operation_json,created_at,updated_at)
                    VALUES(?,?,?,?,?,?)''', ('async-test','attacker','running',json.dumps(operation),'2026-10-02','2026-10-02'))
            return {'success':True, 'created_operations':[operation]}, 200
        return self.pay(start)

    def test_async_reservation_recovery_and_success_only_payment(self):
        from creator_payments import settle_pending
        from database import wallet_reserved, WalletInsufficientFunds
        response = self.prepare_async()
        before = self.wallet.get_balance('attacker')
        self.assertEqual(response.json['option_payment']['amount'], 0)
        self.assertEqual(response.json['option_payment']['reserved'], 10)
        with db_connect(self.path) as conn:
            self.assertEqual(wallet_reserved(conn, 'attacker'), 10)
        with self.assertRaises(WalletInsufficientFunds):
            self.wallet.transfer('attacker','victim',before,transaction_key='competing-spend')
        self.assertEqual(settle_pending(self.inventory,self.wallet,self.bus,lambda *args: self.fail('running operation')),0)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_operations SET status='completed' WHERE operation_id='async-test'")
        def finalize(actor, operation):
            with db_connect(self.path) as conn:
                conn.execute("INSERT INTO test_effect VALUES('file')")
        with patch.object(self.wallet,'transfer',side_effect=RuntimeError('restart')):
            with self.assertRaises(RuntimeError):settle_pending(self.inventory,self.wallet,self.bus,finalize)
        with db_connect(self.path) as conn:
            self.assertEqual(wallet_reserved(conn,'attacker'),10)
        with self.no_heavy():
            self.assertEqual(settle_pending(self.inventory,self.wallet,self.bus,finalize),1)
            self.assertEqual(settle_pending(self.inventory,self.wallet,self.bus,finalize),0)
        self.assertEqual(self.wallet.get_balance('attacker'),before-10)
        with db_connect(self.path) as conn:
            self.assertEqual(wallet_reserved(conn,'attacker'),0)
            self.assertEqual(conn.execute('SELECT count(*) FROM test_effect').fetchone()[0],1)

    def test_async_cancel_releases_reservation_without_transfer(self):
        from creator_payments import settle_pending
        from database import wallet_reserved
        self.prepare_async()
        before=self.wallet.get_balance('attacker')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_operations SET status='cancelled' WHERE operation_id='async-test'")
        self.assertEqual(settle_pending(self.inventory,self.wallet,self.bus,lambda *args:self.fail('cancelled result')),1)
        self.assertEqual(self.wallet.get_balance('attacker'),before)
        with db_connect(self.path) as conn:self.assertEqual(wallet_reserved(conn,'attacker'),0)

    def test_worker_isolates_failed_receipt_and_preserves_it_for_retry(self):
        from creator_payments import settle_pending
        from database import wallet_reserved
        self.prepare_async()
        before = self.wallet.get_balance('attacker')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_operations SET status='timeout' WHERE operation_id='async-test'")
            conn.execute('''INSERT INTO player_operations(operation_id,username,status,operation_json,created_at,updated_at)
                SELECT 'second-operation',username,'cancelled',
                    json_set(operation_json,'$.operation_id','second-operation'),created_at,updated_at
                FROM player_operations WHERE operation_id='async-test' ''')
            conn.execute('''INSERT INTO creator_option_pending
                SELECT 'second-receipt',username,recipient,amount,'["second-operation"]' FROM creator_option_pending''')
            conn.execute("INSERT INTO wallet_holds SELECT 'second-receipt',username,amount FROM wallet_holds")
            conn.execute("INSERT INTO creator_option_receipts SELECT 'second-receipt',request_hash,response_json,status_code FROM creator_option_receipts")
        failures = []
        def broken_file(*args):
            raise RuntimeError('file finalization failed')
        with self.no_heavy():
            self.assertEqual(settle_pending(self.inventory, self.wallet, self.bus, broken_file,
                on_error=lambda key, error: failures.append((key, type(error)))), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(self.wallet.get_balance('attacker'), before)
        with db_connect(self.path) as conn:
            self.assertEqual(wallet_reserved(conn, 'attacker'), 10)
            self.assertEqual(conn.execute('SELECT count(*) FROM creator_option_pending').fetchone()[0], 1)
        self.assertEqual(settle_pending(self.inventory, self.wallet, self.bus, lambda *args: None), 1)
        self.assertEqual(self.wallet.get_balance('attacker'), before-10)

    def test_creator_no_file_bypasses_all_legacy_finalizers(self):
        operation = dict(status='completed', creator_creates_file=False)
        for name in ('finalize_vehicle_tracking_file', 'finalize_device_tracking_file',
                     'finalize_atm_log_extraction_files', 'finalize_persistent_sniffer_files',
                     'finalize_camera_stream_file', 'finalize_wifi_scanner_files',
                     'finalize_audio_interference_files', 'finalize_vehicle_ecu_files',
                     'finalize_generic_trace_file'):
            with self.subTest(finalizer=name):
                self.assertFalse(getattr(run, name)({}, operation))
        self.assertEqual(run.operation_declared_resources(operation, ['wifi_networks'], ['wifi_networks']), [])
        self.assertEqual(run.operation_declared_resources({}, ['wifi_networks'], ['wifi_networks']), ['wifi_networks'])

    def test_no_file_finalization_is_recorded_without_inventory_hydration(self):
        self.prepare()
        operation = dict(operation_id='no-file', operation_type='wifi_scanner', status='completed',
                         creator_creates_file=False)
        with self.no_heavy(), patch.object(self.inventory, 'snapshot', side_effect=AssertionError('unneeded inventory read')), \
                patch.object(self.inventory, 'append_data_files', return_value=[]) as append:
            self.assertEqual(run.finalize_operation_files_bounded('attacker', operation), [])
            self.assertEqual(run.finalize_operation_files_bounded('attacker', operation), [])
            append.assert_called_once()
            self.assertEqual(append.call_args.args, ('attacker', []))

    def test_empty_file_finalization_persists_to_real_operation(self):
        import json
        self.prepare_async()
        with db_connect(self.path) as conn:
            op=json.loads(conn.execute("SELECT operation_json FROM player_operations WHERE operation_id='async-test'").fetchone()[0])
            op.pop('creator_payment_pending',None)
            op.update(status='completed',creator_creates_file=False)
            conn.execute("UPDATE player_operations SET status='completed',operation_json=? WHERE operation_id='async-test'",(json.dumps(op),))
        with self.no_heavy():
            run.finalize_operation_files_bounded('attacker',op)
        with db_connect(self.path) as conn:
            saved=json.loads(conn.execute("SELECT operation_json FROM player_operations WHERE operation_id='async-test'").fetchone()[0])
            self.assertEqual(saved['artifact_state']['file_count'],0)
            self.assertTrue(saved['artifact_state']['finalized_at'])

    def test_http_scan_ports_creates_one_recon_file_on_retry(self):
        from creator_policy import generate_contract
        self.prepare()
        contract=generate_contract(dict(name='Recon',icon='X',interface='terminal',action='scan_ports',creates_file=True),40)
        product=run.build_creator_edition(dict(contract=contract,presentation=dict(name='Recon',icon='X'),
            id='recon-project',app_id='creator_recon',owner='victim'),1)
        self.inventory.install_app('attacker',product,purchase_key='recon-install')
        target=dict(target_id='poi:recon',target_mode='standard',label='Recon target',lat=52.,lng=21.,source_type='poi',
                    security={'firewall':True},actions_allowed={'scan_ports':False})
        run.player_target_runtime_store.upsert_aimed('attacker',target)
        run.player_marked_target_store.ensure_seeded('attacker')
        data=dict(app_id=product['id'],target=target,expected_target=target,launch_receipt='recon-launch-1')
        with self.no_heavy():
            response=self.client.post('/gonna-win',json=data)
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(len(response.json['created_files']),1)
            repeated=self.client.post('/gonna-win',json=data)
            self.assertEqual(repeated.status_code,200,repeated.json)
            self.assertEqual(response.json['created_files'],repeated.json['created_files'])

    def test_concurrent_spending_and_retry(self):
        from concurrent.futures import ThreadPoolExecutor
        from ghostlab_store import GhostLabError
        self.prepare()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE wallet_balances SET balance=10 WHERE username='attacker'")
        def attempt(index):
            data = dict(self.data, launch_receipt='concurrent-' + str(index))
            def operation():
                with db_connect(self.path) as conn:
                    conn.execute('INSERT INTO test_effect VALUES(?)', (str(index),))
                return {'success': True}, 200
            with run.app.app_context():
                try:
                    return execute('attacker', data, self.inventory, self.wallet, self.bus, operation, make_response).status_code
                except GhostLabError as error:
                    return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [1, 2]))
        self.assertEqual(sorted(results), [200, 409])
        self.assertEqual(self.wallet.get_balance('attacker'), 0)
        with db_connect(self.path) as conn:
            winner = int(conn.execute('SELECT id FROM test_effect').fetchone()[0])
            self.assertEqual(conn.execute('SELECT count(*) FROM test_effect').fetchone()[0], 1)
        self.assertEqual(attempt(winner), 200)

    def test_nested_exception_rolls_back_only_savepoint(self):
        self.prepare()
        with atomic_runtime_transaction(self.path) as conn:
            conn.execute("INSERT INTO test_effect VALUES('outer')")
            try:
                with db_connect(self.path) as nested:
                    nested.execute("INSERT INTO test_effect VALUES('inner')")
                    raise ValueError('failed optional unit')
            except ValueError:
                pass
        with db_connect(self.path) as conn:
            self.assertEqual([row[0] for row in conn.execute('SELECT id FROM test_effect')], ['outer'])

    def test_http_real_effect_payment_and_capture_share_transaction(self):
        from creator_policy import generate_contract, configure_draft, SECURITY_KEYS
        self.prepare()
        self.stack.enter_context(patch.object(run, 'delta_bus', self.bus))
        from session_generation_store import SessionGenerationStore
        self.generation.store = SessionGenerationStore(self.path)
        self.stack.enter_context(patch.object(run, 'session_generation_store', self.generation.store))
        self.generation.authenticate(self.client, 'attacker')
        self.stack.enter_context(patch.object(run, 'ghostnetwork_territory_job_store',
            type(run.ghostnetwork_territory_job_store)(self.path)))
        contract = generate_contract(dict(name='Paid capture', icon='X', interface='button_choices',
            action='exploit', creates_file=False), 100)
        contract = configure_draft(contract, {'options': [{'effect': 'security.clear', 'price': 10}]}, 100)
        product = run.build_creator_edition(dict(contract=contract, presentation=dict(name='Paid capture', icon='X'),
            id='project-paid', app_id='paid-real', owner='victim'), 1)
        self.inventory.install_app('attacker', product, purchase_key='install-paid-real')
        target = dict(target_id='poi:paid', target_mode='standard', label='Paid target', lat=52., lng=21., source_type='poi',
            security={key: True for key in SECURITY_KEYS},
            actions_allowed=dict(scan_ports=True, sniff=True, trace=True, exploit=False))
        run.player_target_runtime_store.upsert_aimed('attacker', target)
        run.player_marked_target_store.ensure_seeded('attacker')
        request = dict(app_id=product['id'], choice_id=0, target=target, expected_target=target,
                       launch_receipt='real-paid-launch')
        before = self.wallet.get_balance('attacker')
        with self.no_heavy():
            with patch.object(self.wallet, 'transfer', side_effect=ValueError('Simulated transfer failure')):
                failed = self.client.post('/gonna-win', json=request)
                self.assertEqual(failed.status_code, 400, failed.json)
            self.assertEqual(run.territory_store.list_captured_targets('attacker'), [])
            self.assertTrue(run.player_target_runtime_store.get_active_target('attacker')['security']['firewall'])
            response = self.client.post('/gonna-win', json=request)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertTrue(response.json['success'], response.json)
            self.assertEqual(response.json['option_payment']['amount'], 10)
            self.assertEqual(len(run.territory_store.list_captured_targets('attacker')), 1)
            self.assertEqual(self.client.post('/gonna-win', json=request).json, response.json)
        self.assertEqual(self.wallet.get_balance('attacker'), before - 10)

    def test_http_async_trace_finalizes_real_file_and_payment(self):
        from creator_policy import generate_contract, configure_draft
        from creator_payments import settle_pending
        from session_generation_store import SessionGenerationStore
        self.prepare()
        self.stack.enter_context(patch.object(run, 'delta_bus', self.bus))
        self.generation.store = SessionGenerationStore(self.path)
        self.stack.enter_context(patch.object(run, 'session_generation_store', self.generation.store))
        self.generation.authenticate(self.client, 'attacker')
        contract=generate_contract(dict(name='Paid trace',icon='X',interface='button_choices',action='trace',creates_file=True),100)
        contract=configure_draft(contract,{'options':[{'price':10}]},100)
        product=run.build_creator_edition(dict(contract=contract,presentation=dict(name='Paid trace',icon='X'),
            id='trace-project',app_id='creator_trace',owner='victim'),1)
        self.inventory.install_app('attacker',product,purchase_key='trace-install')
        target=dict(target_id='poi:trace',target_mode='standard',label='Trace target',lat=52.,lng=21.,source_type='poi',
                    security={'firewall':True},actions_allowed={'trace':False})
        run.player_target_runtime_store.upsert_aimed('attacker',target)
        run.player_marked_target_store.ensure_seeded('attacker')
        before=self.wallet.get_balance('attacker')
        with self.no_heavy():
            picker=self.client.post('/hack-action',json=dict(target,action='trace'))
            self.assertEqual(picker.status_code,200,picker.json)
            self.assertTrue(picker.json['tool_selection_required'])
            launch=self.client.post('/hack-action',json=dict(target, action='trace',
                selected_app_id=product['id'], _client_action_key='trace-picker'))
            self.assertEqual(launch.status_code,200,launch.json)
            self.assertEqual(launch.json['created_operations'],[])
            self.assertFalse(launch.json['target']['actions_allowed'].get('trace',False))
            self.assertEqual(run.player_operation_store.list_operations('attacker'),[])
            response=self.client.post('/gonna-win',json=dict(app_id=product['id'],choice_id=0,target=target,
                expected_target=target,launch_receipt='trace-paid-launch'))
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['option_payment']['reserved'],10)
            self.assertEqual(self.wallet.get_balance('attacker'),before)
            opid=response.json['created_operations'][0]['operation_id']
            with db_connect(self.path) as conn:
                conn.execute("UPDATE player_operations SET status='timeout' WHERE operation_id=?",(opid,))
            self.assertEqual(settle_pending(self.inventory,self.wallet,self.bus,run.finalize_operation_files_bounded),1)
            self.assertTrue(self.inventory.list_data_files('attacker',operation_id=opid))
            self.assertEqual(self.wallet.get_balance('attacker'),before-10)

    def test_camera_picker_waits_for_choice_and_shutdown_charges_once(self):
        from creator_policy import generate_contract, configure_draft
        from database import PlayerScanSnapshotStore
        from response_network.camera_contract import camera_marker
        from session_generation_store import SessionGenerationStore
        self.prepare()
        self.generation.store = SessionGenerationStore(self.path)
        self.stack.enter_context(patch.object(run, 'session_generation_store', self.generation.store))
        self.generation.authenticate(self.client, 'attacker')
        self.stack.enter_context(patch.object(run, 'delta_bus', self.bus))
        scans = PlayerScanSnapshotStore(self.path)
        self.stack.enter_context(patch.object(run, 'player_scan_snapshot_store', scans))
        self.stack.enter_context(patch.object(run, 'foreign_territory_action_block', return_value=None))
        camera = camera_marker(dict(lat=52.1, lng=21.2, osm_id='node:123'))
        scan = scans.record('attacker', [camera], 52.1, 21.2)
        run.player_position_store.upsert('attacker', dict(lat=52.1, lng=21.2))
        contract = generate_contract(dict(name='Camera', icon='X', interface='button_choices',
            action='camera_shutdown', creates_file=False), 100)
        contract = configure_draft(contract, {'options': [
            {'price': 10, 'effect': 'firewall=false'}, {'price': 20, 'effect': 'firewall=true'}]}, 100)
        product = run.build_creator_edition(dict(contract=contract, presentation=dict(name='Camera', icon='X',
            option_labels=['Disable firewall', 'Enable firewall']),
            id='camera-project', app_id='creator_camera', owner='victim'), 1)
        self.inventory.install_app('attacker', product, purchase_key='camera-install')
        before = self.wallet.get_balance('attacker')
        payload = dict(action='camera_shutdown', selected_app_id=product['id'],
            camera_id=camera['camera_id'], scan_id=scan['scan_id'])
        with self.no_heavy():
            launch = self.client.post('/hack-action', json=payload)
            self.assertEqual(launch.status_code, 200, launch.json)
            self.assertEqual(launch.json['created_operations'], [])
            self.assertEqual(run.player_operation_store.list_operations('attacker'), [])
            self.assertEqual(self.wallet.get_balance('attacker'), before)
            data = dict(app_id=product['id'], expected_target=launch.json['target'],
                launch_receipt=launch.json['added_apps'][0]['receipt'])
            invalid = self.client.post('/gonna-win', json=dict(data, choice_id=99))
            self.assertEqual(invalid.status_code, 400, invalid.json)
            self.assertEqual(run.player_operation_store.list_operations('attacker'), [])
            with patch.object(self.wallet, 'transfer', side_effect=ValueError('payment failure')):
                failed = self.client.post('/gonna-win', json=dict(data, choice_id=0))
                self.assertEqual(failed.status_code, 400, failed.json)
            self.assertEqual(run.player_operation_store.list_operations('attacker'), [])
            result = self.client.post('/gonna-win', json=dict(data, choice_id=0))
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual(result.json['option_payment']['amount'], 10)
            self.assertFalse(result.json['target']['security']['firewall'])
            retry = self.client.post('/gonna-win', json=dict(data, choice_id=0))
            self.assertEqual(retry.json, result.json)
            self.assertEqual(self.wallet.get_balance('attacker'), before-10)
            self.assertEqual(len(run.player_operation_store.list_operations('attacker')), 1)
            duplicate = self.client.post('/gonna-win', json=dict(data, choice_id=1, launch_receipt='different-camera-choice'))
            self.assertEqual(duplicate.status_code, 200, duplicate.json)
            self.assertTrue(duplicate.json['duplicate'])
            self.assertEqual(duplicate.json['option_payment']['amount'], 0)
            self.assertFalse(run.player_target_runtime_store.get_active_target('attacker')['security']['firewall'])

    def test_map_launcher_recipe_interface_matrix_defers_execution(self):
        from creator_policy import generate_contract, RECIPES, INTERFACES
        self.prepare()
        run.player_marked_target_store.ensure_seeded('attacker')
        for action, recipe in RECIPES.items():
            if action == 'camera_shutdown':
                continue  # Its observed-camera contract is tested separately.
            for interface in sorted(INTERFACES):
                with self.subTest(action=action, interface=interface):
                    key = action + '-' + interface
                    contract = generate_contract(dict(name=key, icon='X', interface=interface,
                        action=action, creates_file=False), 100)
                    if interface == 'button_choices':
                        contract['options'] = [{'price': 0, 'effect': {}}]
                    product = run.build_creator_edition(dict(contract=contract,
                        presentation=dict(name=key, icon='X'), id=key,
                        app_id='creator_' + key, owner='victim'), 1)
                    self.inventory.install_app('attacker', product, purchase_key=key)
                    target = dict(target_id='map:' + key, target_mode='standard', label=key,
                        lat=52., lng=21., source_type=recipe['target_types'][0],
                        target_type=recipe['target_types'][0], security={'firewall': True},
                        actions_allowed={action: False})
                    run.player_target_runtime_store.upsert_aimed('attacker', target)
                    with self.no_heavy():
                        response = self.client.post('/hack-action', json=dict(target,
                            action=action, selected_app_id=product['id'], _client_action_key=key))
                        self.assertEqual(response.status_code, 200, response.json)
                        self.assertEqual(response.json['applicationEffect']['id'], product['id'])
                        self.assertEqual(response.json['applicationEffect']['levels'], product['levels'])
                        self.assertEqual(response.json['created_operations'], [])
                        self.assertFalse(response.json['target']['actions_allowed'].get(action, False))
                        self.assertTrue(response.json['target']['security']['firewall'])
                        self.assertEqual(run.player_operation_store.list_operations('attacker'), [])
                        if action == 'atm_logs':
                            executed = self.client.post('/gonna-win', json=dict(app_id=product['id'],
                                expected_target=target, launch_receipt='fileless-' + key,
                                **({'choice_id': 0} if interface == 'button_choices' else {})))
                            self.assertEqual(executed.status_code, 400, executed.json)
                            self.assertIn('wyłączone tworzenie pliku', executed.json['message'])
                            self.assertEqual(run.player_operation_store.list_operations('attacker'), [])

    def test_recipe_executors_produce_declared_files_without_heavy_profile(self):
        from creator_policy import generate_contract, RECIPES
        self.prepare()
        run.player_marked_target_store.ensure_seeded('attacker')
        for index, (action, recipe) in enumerate(RECIPES.items()):
            if action in {'exploit', 'camera_shutdown'}:
                continue  # Dedicated capture and observed-camera HTTP tests.
            with self.subTest(action=action):
                creates_file = bool(recipe['resource_types'])
                contract = generate_contract(dict(name=action, icon='X', interface='window',
                    action=action, creates_file=creates_file), 100)
                product = run.build_creator_edition(dict(contract=contract,
                    presentation=dict(name=action, icon='X'), id=action,
                    app_id='creator_' + action, owner='victim'), 1)
                self.inventory.install_app('attacker', product, purchase_key=action)
                target = dict(target_id='map:' + action, target_mode='standard', label=action,
                    lat=52. + index / 1000, lng=21., source_type=recipe['target_types'][0],
                    target_type=recipe['target_types'][0], security={'firewall': True},
                    actions_allowed={action: False})
                run.player_target_runtime_store.upsert_aimed('attacker', target)
                with self.no_heavy():
                    data = dict(app_id=product['id'], target=target, expected_target=target,
                        launch_receipt='executor-' + action)
                    response = self.client.post('/gonna-win', json=data)
                    self.assertEqual(response.status_code, 200, response.json)
                    self.assertTrue(response.json['success'], response.json)
                    if action == 'scan_ports':
                        self.assertTrue(response.json['created_files'])
                        continue
                    operations = response.json['created_operations']
                    self.assertEqual(len(operations), 1)
                    operation = dict(operations[0], status='timeout')
                    with patch.object(self.inventory, 'snapshot', side_effect=AssertionError('unbounded inventory read')):
                        files = run.finalize_operation_files_bounded('attacker', operation)
                    if creates_file:
                        self.assertTrue(files, action)
                        resources = {resource for item in files for resource in item.get('resource_types', [])}
                        self.assertTrue(resources.intersection(recipe['resource_types']), (action, resources))
                        if action == 'atm_logs':
                            response = self.client.get('/api/ghostlab/file-manager/folders/atm')
                            self.assertEqual(response.status_code, 200, response.json)
                            self.assertTrue(response.json['files'])
                            self.assertTrue(any(item.get('operation_id') == operation['operation_id']
                                or item.get('source_operation_id') == operation['operation_id']
                                for item in response.json['files']))
                    else:
                        self.assertEqual(files, [])
                    self.assertEqual(run.finalize_operation_files_bounded('attacker', operation), files)
