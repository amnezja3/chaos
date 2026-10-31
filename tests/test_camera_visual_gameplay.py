import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
import test_player_hack_read_paths as fixtures
from camera_visual import CameraVisual, LAT, LNG, PilotError, generate_motion
from database import (PlayerPositionStore, PlayerOperationStore, PlayerTargetRuntimeStore,
                      db_connect, reset_hot_path_metrics, restore_hot_path_metrics, get_hot_path_metrics)


class CameraVisualGameplayTest(unittest.TestCase):
    setUp = fixtures.PlayerHackReadPathsTest.setUp
    seed = fixtures.PlayerHackReadPathsTest.seed

    def prepare(self, big=False):
        self.seed(big_attacker=big)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_storage SET capacity=1024,used=0 WHERE username='attacker'")
        self.stack.enter_context(patch.dict(os.environ, CHAOS_CAMERA_VISUAL_PILOT='1', CHAOS_CAMERA_VISUAL_PILOT_USER='attacker'))
        self.operations = PlayerOperationStore(self.path)
        self.targets = PlayerTargetRuntimeStore(self.path)
        self.positions = PlayerPositionStore(self.path)
        for name, value in [('player_operation_store', self.operations), ('player_target_runtime_store', self.targets), ('player_position_store', self.positions)]:
            self.stack.enter_context(patch.object(run, name, value))
        self.stack.enter_context(patch.object(run, 'foreign_territory_action_block', return_value=None))
        self.target = dict(lat=LAT, lng=LNG, label='Kamera sklepu', source_type='camera', target_mode='standard',
                           target_id=f'map:{LAT}:{LNG}:Kamera sklepu', security={'firewall': False}, actions_allowed={'camera_stream': True})
        self.targets.upsert_aimed('attacker', self.target)
        self.positions.upsert('attacker', dict(lat=LAT, lng=LNG))
        self.app = dict(id='glass-eye', name='Glass Eye', interface='progressbar_random',
                        map_actions=['camera_stream'], operation_types=['camera_stream'], target_types=['camera'],
                        resource_types=['camera_dump'], requires_off=['firewall'])
        self.inventory.install_app('attacker', self.app, purchase_key='cvn-test')
        self.service = CameraVisual(run)
        self.payload = dict(app_id='glass-eye', expected_target=self.target, launch_receipt='desktop-test-receipt', launch_source='desktop_menu')

    def complete(self, response):
        state = response['camera_visual']
        op = response['created_operations'][0]
        op['status'] = 'timeout'
        self.operations.upsert_operations('attacker', [op])
        with patch('camera_visual.time.time', return_value=state['ready_at']):
            self.service.finalize('attacker', op)
            return self.service.snapshot('attacker')[0]

    def test_real_routes_success_no_heavy_and_canonical_file(self):
        self.prepare(big=True)
        token = reset_hot_path_metrics()
        self.addCleanup(restore_hot_path_metrics, token)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), patch.object(run, 'sync_session_profile', side_effect=AssertionError('heavy hydrate')):
            launch = self.client.post('/hack-action', json={**self.target, 'action': 'camera_stream', 'selected_app_id': self.app['id'], '_client_action_key': 'real-map-launch'})
            self.assertEqual(launch.status_code, 200, launch.json)
            self.assertEqual(launch.json['created_operations'], [])
            payload = {**self.payload, 'launch_receipt': launch.json['added_apps'][0]['receipt'], 'launch_source': 'launch_queue'}
            result = self.client.post('/gonna-win', json=payload)
            self.assertEqual(result.status_code, 200, result.json)
            self.assertTrue(result.json['success'], result.json)
            state = result.json['camera_visual']
            self.assertEqual(state['ready_at']-state['download_at'], 1800)
            self.assertEqual(state['state'], 'session_close')
            self.assertEqual(self.client.get(f"/api/camera-visual/media/{state['reference_id']}/0").status_code, 403)
            with patch('camera_visual.time.time', return_value=state['download_at']+900):
                self.assertEqual(self.service.snapshot('attacker')[0]['progress'], 50)
            ready = self.complete(result.json)
            self.assertEqual(ready['state'], 'ready')
        self.assertEqual(get_hot_path_metrics()['profile_full_read'], 0)
        self.assertEqual(get_hot_path_metrics()['profile_full_write'], 0)
        self.assertEqual(get_hot_path_metrics()['profile_bytes'], 0)
        files = self.inventory.list_data_files('attacker', operation_id=state['operation_id'])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['resource_type'], 'camera_activation')

    def test_failure_durable_no_operation_even_after_security_changes(self):
        self.prepare()
        self.target['security']['firewall'] = True
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_target_runtime SET security_json=? WHERE username='attacker'", (json.dumps(self.target['security']),))
        first = self.client.post('/gonna-win', json=self.payload)
        self.assertEqual(first.status_code, 200, first.json)
        self.assertFalse(first.json['success'])
        self.target['security']['firewall'] = False
        self.targets.upsert_aimed('attacker', self.target)
        retry = self.client.post('/gonna-win', json=self.payload)
        self.assertFalse(retry.json['success'])
        self.assertTrue(retry.json['duplicate'])
        self.assertEqual(self.operations.list_operations('attacker'), [])

    def test_parallel_results_one_operation_and_one_session(self):
        self.prepare()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.service.result('attacker', self.payload), range(4)))
        self.assertEqual(len({r['camera_visual']['instance_id'] for r in results}), 1)
        self.assertEqual(len(self.operations.list_operations('attacker')), 1)
        self.assertEqual(len(self.service.snapshot('attacker')), 1)

    def test_disk_full_retry_and_corruption_fail_closed(self):
        self.prepare()
        result = self.service.result('attacker', self.payload)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_storage SET used=capacity WHERE username='attacker'")
        self.assertEqual(self.complete(result)['state'], 'save_pending')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_storage SET used=0 WHERE username='attacker'")
        self.assertEqual(self.complete(result)['state'], 'ready')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_data_files SET file_json='{}' WHERE username='attacker'")
        with patch('camera_visual.time.time', return_value=result['camera_visual']['ready_at']):
            self.assertEqual(self.service.snapshot('attacker')[0]['state'], 'save_pending')
            with self.assertRaises(PilotError):
                self.service.window('attacker', dict(owner='a'*32, receipt=self.payload['launch_receipt']))

    def test_two_tabs_close_reopen_and_foreign_account(self):
        self.prepare()
        result = self.service.result('attacker', self.payload)
        self.complete(result)
        data = dict(owner='a'*32, receipt=self.payload['launch_receipt'])
        with patch('camera_visual.time.time', return_value=result['camera_visual']['ready_at']):
            self.assertTrue(self.service.window('attacker', data)['granted'])
            self.assertFalse(self.service.window('attacker', {**data, 'owner':'b'*32})['granted'])
            self.service.window('attacker', {**data, 'action':'close'})
            self.assertFalse(self.service.window('attacker', data)['granted'])
            with self.assertRaisesRegex(PilotError, 'camera_new_hack_required'):
                self.service.window('attacker', {**data, 'action':'reopen'})
            self.assertEqual(self.service.snapshot('attacker')[0]['state'], 'consumed')
            self.assertEqual(self.client.get('/api/camera-visual/media/desktop-test-receipt/0').status_code, 403)
            fresh = self.service.result('attacker', {**self.payload, 'launch_receipt':'fresh-hack'})
            self.assertNotEqual(fresh['camera_visual']['instance_id'], result['camera_visual']['instance_id'])
            self.assertNotEqual(fresh['camera_visual']['motion'], result['camera_visual']['motion'])
            self.assertEqual(fresh['camera_visual']['state'], 'session_close')
            with self.assertRaises(PilotError):
                self.service.window('victim', data)

    def test_uninstalled_app_and_changed_target_rejected(self):
        self.prepare()
        response = self.client.post('/gonna-win', json={**self.payload, 'launch_source':'launch_queue'})
        self.assertEqual(response.status_code, 409, response.json)
        self.positions.upsert('attacker', dict(lat=0, lng=0))
        response = self.client.post('/gonna-win', json=self.payload)
        self.assertEqual(response.json['reason'], 'camera_out_of_range')

    def test_alias_cannot_get_independent_window_and_cancel_blocks_media(self):
        self.prepare()
        first = self.service.result('attacker', self.payload)
        second = self.service.result('attacker', {**self.payload, 'launch_receipt':'second-desktop-receipt'})
        self.assertTrue(second['duplicate'])
        self.assertEqual(len(self.service.snapshot('attacker')), 1)
        self.complete(first)
        with patch('camera_visual.time.time', return_value=first['camera_visual']['ready_at']):
            with self.assertRaises(PilotError):
                self.service.window('attacker', dict(owner='x'*32, receipt='second-desktop-receipt'))
            response = self.client.get('/api/camera-visual/media/desktop-test-receipt/0')
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response.headers['Cache-Control'])
            response.close()
            with db_connect(self.path) as conn:
                conn.execute("UPDATE player_operations SET status='cancelled' WHERE username='attacker'")
            self.assertEqual(self.client.get('/api/camera-visual/media/desktop-test-receipt/0').status_code, 403)

    def test_parent_transaction_rollback_leaves_no_result_or_operation(self):
        from database import atomic_runtime_transaction
        self.prepare()
        with self.assertRaisesRegex(RuntimeError, 'rollback'):
            with atomic_runtime_transaction(self.path):
                self.service.result('attacker', self.payload)
                raise RuntimeError('rollback')
        self.assertEqual(self.service.snapshot('attacker'), [])
        self.assertEqual(self.operations.list_operations('attacker'), [])

    def test_csrf_and_replay_target_guard(self):
        self.prepare()
        denied = self.client.post('/gonna-win', json=self.payload, headers={'X-Chaos-CSRF':'wrong'})
        self.assertEqual(denied.status_code, 403)
        self.service.result('attacker', self.payload)
        with self.assertRaises(PilotError):
            self.service.result('attacker', {**self.payload, 'expected_target':{'lat':0, 'lng':0}})

    def test_generated_app_joins_by_contract_without_name_or_id_allowlist(self):
        from creator_policy import generate_contract
        self.prepare()
        contract = generate_contract(dict(action='camera_stream', interface='window', creates_file=True, price=0), 40)
        generated = run.build_creator_edition(dict(id='cvn-project', app_id='arbitrary-camera-app',
            owner='attacker', contract=contract, presentation={'name':'Unrelated name','icon':'X'}), 1)
        self.inventory.install_app('attacker', generated, purchase_key='generated-cvn')
        result = self.client.post('/gonna-win', json={**self.payload, 'app_id':generated['id']})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(result.json['success'], result.json)
        self.assertEqual(result.json['camera_visual']['app_id'], generated['id'])

    def test_motion_is_persisted_and_legacy_upgrade_is_once(self):
        self.prepare()
        result = self.service.result('attacker', self.payload)
        motion = result['camera_visual']['motion']
        self.assertEqual(self.service.result('attacker', self.payload)['camera_visual']['motion'], motion)
        self.assertEqual(self.service.snapshot('attacker')[0]['motion'], motion)
        self.assertNotEqual(motion, generate_motion())
        self.assertEqual(motion['version'], 2)
        self.assertIn(motion['image'], range(3))
        self.assertTrue(all(0 <= v <= 50 for v in motion['start'] + motion['control'] + motion['end']))
        self.assertNotEqual(motion['start'], motion['end'])
        self.assertTrue(180 <= motion['seconds'] <= 300)
        self.complete(result)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE camera_visual_sessions SET payload_json=json_set(payload_json,'$.motion',json(?))", (json.dumps({'version':1,'tracks':[]}),))
        data = dict(owner='a'*32, receipt=self.payload['launch_receipt'])
        with patch('camera_visual.time.time', return_value=result['camera_visual']['ready_at']):
            upgraded = self.service.window('attacker', data)['camera_visual']['motion']
            self.assertEqual(self.service.window('attacker', data)['camera_visual']['motion'], upgraded)
            self.assertEqual(self.service.snapshot('attacker')[0]['motion'], upgraded)

    def test_heartbeat_read_only_under_writer_lock_and_lease_expiry(self):
        import sqlite3
        self.prepare()
        result = self.service.result('attacker', self.payload)
        self.complete(result)
        data = dict(owner='a'*32, receipt=self.payload['launch_receipt'])
        now = result['camera_visual']['ready_at']
        with patch('camera_visual.time.time', return_value=now):
            lease = self.service.window('attacker', data)['lease_until']
            blocker = sqlite3.connect(self.path)
            try:
                blocker.execute('BEGIN IMMEDIATE')
                # This used to BEGIN IMMEDIATE and fail after 15 seconds.
                response = self.service.window('attacker', data)
                self.assertEqual(response['lease_until'], lease)
            finally:
                blocker.rollback(); blocker.close()
        with patch('camera_visual.time.time', return_value=now+41):
            renewed = self.service.window('attacker', data)['lease_until']
            self.assertGreater(renewed, lease)
            self.assertFalse(self.service.window('attacker', {**data, 'owner':'b'*32})['granted'])
        with patch('camera_visual.time.time', return_value=renewed+1):
            self.assertTrue(self.service.window('attacker', {**data, 'owner':'b'*32})['granted'])

    def test_busy_window_returns_retryable_response(self):
        import sqlite3
        self.prepare()
        with patch.object(CameraVisual, 'window', side_effect=sqlite3.OperationalError('database is locked')):
            response = self.client.post('/api/camera-visual/window', json={})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json['reason'], 'camera_storage_busy')
        self.assertEqual(response.headers['Retry-After'], '5')

    def test_release_keeps_grant_and_foreign_owner_cannot_release(self):
        self.prepare()
        result = self.service.result('attacker', self.payload)
        self.complete(result)
        data = dict(owner='a'*32, receipt=self.payload['launch_receipt'])
        with patch('camera_visual.time.time', return_value=result['camera_visual']['ready_at']):
            self.service.window('attacker', data)
            self.service.window('attacker', {**data, 'owner':'b'*32, 'action':'release'})
            self.assertFalse(self.service.window('attacker', {**data, 'owner':'b'*32})['granted'])
            self.service.window('attacker', {**data, 'action':'release'})
            self.assertTrue(self.service.window('attacker', {**data, 'owner':'b'*32})['granted'])
            self.assertFalse(self.service.snapshot('attacker')[0]['viewer_closed'])

    def test_same_camera_different_player_gets_own_motion(self):
        self.prepare()
        first = self.service.result('attacker', self.payload)['camera_visual']['motion']
        self.inventory.install_app('victim', self.app, purchase_key='victim-camera')
        self.targets.upsert_aimed('victim', self.target)
        with patch.object(self.service, 'guard'):
            other = self.service.result('victim', self.payload)['camera_visual']['motion']
            retry = self.service.result('victim', self.payload)['camera_visual']['motion']
        self.assertNotEqual(first, other)
        self.assertEqual(other, retry)

    def test_gameplay_duration_and_later_acceleration_are_authoritative(self):
        self.prepare()
        with patch.dict(run.DEFAULT_OPERATION_DURATIONS_SECONDS, camera_stream=300):
            response = self.service.result('attacker', self.payload)
        state = response['camera_visual']
        self.assertEqual(state['ready_at'] - state['download_at'], 300)
        op = response['created_operations'][0]
        from ghostnetwork.ability_realizers import _operation_speed
        from camera_visual import iso
        now = state['download_at'] + 60
        _operation_speed({'operations':[op]}, dict(window_id='test-speed', activated_at=iso(now),
            ability_code='insider_feed', level_snapshot=60))
        self.operations.upsert_operations('attacker', [op])
        end = run.parse_operation_timestamp(op['expires_at'])
        self.assertLess(end, state['ready_at'])
        with patch('camera_visual.time.time', return_value=end-1):
            self.assertEqual(self.service.snapshot('attacker')[0]['state'], 'downloading')
            self.assertEqual(self.service.snapshot('attacker')[0]['ready_at'], end)
        op['status'] = 'timeout'
        self.operations.upsert_operations('attacker', [op])
        with patch('camera_visual.time.time', return_value=end):
            self.service.finalize('attacker', op)
            self.assertEqual(self.service.snapshot('attacker')[0]['state'], 'ready')

    def test_observed_world_camera_uses_canonical_identity(self):
        from database import PlayerScanSnapshotStore
        from response_network.camera_contract import camera_marker
        self.prepare()
        self.stack.enter_context(patch.dict(os.environ, CHAOS_CAMERA_STREET_VIEW='1'))
        marker = camera_marker(dict(lat=50.0, lng=20.0, osm_id='test-shop'))
        scans = PlayerScanSnapshotStore(self.path)
        snapshot = scans.record('attacker', [marker], 50, 20)
        self.positions.upsert('attacker', dict(lat=50, lng=20))
        data = dict(marker, scan_id=snapshot['scan_id'], action='camera_stream',
                    selected_app_id=self.app['id'], _client_action_key='world-camera')
        launch = self.client.post('/hack-action', json=data)
        self.assertEqual(launch.status_code, 200, launch.json)
        target = launch.json['target']
        self.assertEqual(target['camera_id'], marker['camera_id'])
        payload = {**self.payload, 'expected_target':target,
                   'launch_receipt':launch.json['added_apps'][0]['receipt'], 'launch_source':'launch_queue'}
        result = self.client.post('/gonna-win', json=payload)
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(result.json['success'], result.json)
        self.assertEqual(result.json['camera_visual']['target']['camera_id'], marker['camera_id'])
        forged = self.client.post('/hack-action', json={**data, 'camera_id':'invented'})
        self.assertEqual(forged.status_code, 409)
        for kind in ('atm','commercial'):
            with self.subTest(parent=kind):
                other=camera_marker(dict(lat=50,lng=20,osm_id='test-'+kind,source_type=kind))
                scan=scans.record('attacker',[other],50,20)
                launch=self.client.post('/hack-action',json={**data,**other,'scan_id':scan['scan_id'],'_client_action_key':kind})
                self.assertEqual(launch.status_code,200,launch.json)
                result=self.client.post('/gonna-win',json={**payload,'expected_target':launch.json['target'],
                    'launch_receipt':launch.json['added_apps'][0]['receipt']})
                self.assertTrue(result.json['success'],result.json)
                self.assertEqual(result.json['camera_visual']['target']['parent_target_id'],'test-'+kind)

    def test_archive_binding_is_not_authorization_and_is_revocable(self):
        import tempfile
        from camera_visual_archive import ArchiveStore
        self.prepare()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,
                CHAOS_CAMERA_SOURCE='fixture',CHAOS_CAMERA_WORKER='1',CHAOS_CAMERA_ARCHIVE_DIR=directory):
            result=self.service.result('attacker',self.payload)
            archive=ArchiveStore(self.path)
            self.assertEqual(archive.process_one()['status'],'READY')
            self.assertEqual(self.client.get('/api/camera-visual/media/desktop-test-receipt/0').status_code,403)
            self.complete(result)
            now=result['camera_visual']['ready_at']
            data=dict(owner='a'*32,receipt=self.payload['launch_receipt'])
            with patch('camera_visual.time.time',return_value=now):
                state=self.service.window('attacker',data)['camera_visual']
                self.assertTrue(state['material'])
                response=self.client.get('/api/camera-visual/media/desktop-test-receipt/'+str(state['motion']['image']))
                self.assertEqual(response.status_code,200);response.close()
                archive.withdraw(state['material']['source'],state['image_id'],'test')
                response=self.client.get('/api/camera-visual/media/desktop-test-receipt/'+str(state['motion']['image']))
                self.assertEqual(response.status_code,404)
                self.assertIsNone(self.service.snapshot('attacker')[0]['material'])

    def test_active_super_power_at_creation_and_long_lived_instance(self):
        from ghostnetwork.ability_realizers import apply_operation_speed_to_new_operation
        from datetime import timedelta
        self.prepare()
        def realize(username,operation,now=None):
            return apply_operation_speed_to_new_operation(operation,dict(window_id='active-test',
                ability_code='insider_feed',level_snapshot=60,
                activated_at=(now-timedelta(seconds=10)).isoformat(),expires_at=(now+timedelta(hours=1)).isoformat()))
        with patch.object(run,'apply_active_ghostnetwork_ability_to_new_operation',side_effect=realize):
            result=self.service.result('attacker',self.payload)
        state=result['camera_visual']
        self.assertEqual(state['ready_at']-state['download_at'],300)
        self.complete(result)
        data=dict(owner='a'*32,receipt=self.payload['launch_receipt'])
        with patch('camera_visual.time.time',return_value=state['ready_at']):
            original=self.service.window('attacker',data)['camera_visual']
        with patch('camera_visual.time.time',return_value=state['ready_at']+7*86400):
            restored=self.service.window('attacker',data)['camera_visual']
            self.assertEqual(restored['instance_id'],original['instance_id'])
            self.assertEqual(restored['motion'],original['motion'])
            self.assertFalse(restored['viewer_closed'])

    def test_admin_is_restricted_and_sources_are_public(self):
        self.prepare(big=True)
        public=run.app.test_client().get('/camera-sources?locale=en')
        self.assertEqual(public.status_code,200)
        self.assertIn(b'Data sources',public.data)
        denied=self.client.get('/dev?tab=camera')
        self.assertEqual(denied.status_code,403)
        with patch.object(run,'require_dev_admin',return_value=True), patch.object(self.users,'get_profile',side_effect=AssertionError('heavy read')):
            rendered=self.client.get('/dev?tab=camera')
            self.assertEqual(rendered.status_code,200,rendered.data[:200])
            self.assertIn(b'Camera Street View',rendered.data)
            self.assertNotIn(os.environ.get('MAPILLARY_ACCESS_TOKEN','not-a-secret').encode(),rendered.data)

    def test_late_archive_keeps_same_grant_and_concurrent_close_is_final(self):
        import tempfile
        from camera_visual_archive import ArchiveStore
        self.prepare()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,
                CHAOS_CAMERA_SOURCE='fixture',CHAOS_CAMERA_WORKER='1',CHAOS_CAMERA_ARCHIVE_DIR=directory):
            with patch.dict(run.DEFAULT_OPERATION_DURATIONS_SECONDS,camera_stream=300):
                result=self.service.result('attacker',self.payload)
            self.complete(result)
            data=dict(owner='a'*32,receipt=self.payload['launch_receipt'])
            with patch('camera_visual.time.time',return_value=result['camera_visual']['ready_at']):
                first=self.service.window('attacker',data)['camera_visual']
                self.assertEqual(first['state'],'ready')
                self.assertIsNone(first['material'])
            ArchiveStore(self.path).process_one()
            with patch('camera_visual.time.time',return_value=result['camera_visual']['ready_at']):
                second=self.service.window('attacker',data)['camera_visual']
                self.assertEqual(first['instance_id'],second['instance_id'])
                self.assertTrue(second['material'])
                with ThreadPoolExecutor(max_workers=3) as pool:
                    closed=list(pool.map(lambda _:self.service.window('attacker',{**data,'action':'close'}),range(3)))
                self.assertTrue(all(r['closed'] for r in closed))
                self.assertFalse(self.service.window('attacker',data)['granted'])

    def test_same_photo_still_gets_new_motion_vector(self):
        with patch('camera_visual.IMAGES',('one-photo',)):
            first=generate_motion();second=generate_motion(first)
        self.assertEqual(first['image'],second['image'])
        self.assertNotEqual([b-a for a,b in zip(first['start'],first['end'])],
                            [b-a for a,b in zip(second['start'],second['end'])])


if __name__ == '__main__':
    unittest.main()
