"""System acceptance: real GN activation, canonical camera clock and grants."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import run
from camera_visual import CameraVisual, PilotError
from database import (PlayerMarkedTargetStore, PlayerScanSnapshotStore,
                      db_connect, reset_hot_path_metrics, restore_hot_path_metrics,
                      get_hot_path_metrics)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from response_network.camera_contract import camera_marker
import test_camera_visual_gameplay as fixture


class CameraSystemPowersTest(unittest.TestCase):
    setUp = fixture.CameraVisualGameplayTest.setUp
    seed = fixture.CameraVisualGameplayTest.seed
    prepare = fixture.CameraVisualGameplayTest.prepare

    def system(self, big=False, profession='broker', part_code='V1'):
        self.prepare(big=big)
        self.stack.enter_context(patch.dict(os.environ, CHAOS_CAMERA_STREET_VIEW='1',
            CHAOS_CAMERA_VISUAL_PILOT='0', CHAOS_CAMERA_SOURCE='fixture',
            CHAOS_CAMERA_WORKER='1', CHAOS_CAMERA_ARCHIVE_DIR=self.tmp.name + '/archive'))
        self.users.patch_profile_guarded('attacker', dict(level=60, ghost_profession=profession),
                                         source='test.camera.system.setup')
        self.now = datetime.now(timezone.utc)
        self.repo = GhostNetworkRepository(db_path=self.path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()['cycle']
        part = next(p for p in self.repo.list_parts(cycle['cycle_id']) if p['part_code'] == part_code)
        self.repo.update_part(part['part_id'], status='active', target_id='power-node',
            latitude=50, longitude=20, discovered_by='attacker', discovered_clan='virex',
            conflict_state='none', frozen_status='', conflict_id='', territory_id='power-area',
            territory_owner_id='attacker', territory_clan='virex')
        self.gn = GhostNetworkService(repository=self.repo)
        self.stack.enter_context(patch.object(run, 'GHOSTNETWORK_ABILITIES_ENABLED', True))
        self.stack.enter_context(patch.object(run, 'get_ghostnetwork_service', return_value=self.gn))
        self.marker = camera_marker(dict(lat=50, lng=20, osm_id='system-shop', name='System shop'))
        for user in ('attacker', 'victim'):
            if not self.inventory.has_app(user, self.app['id']):
                self.inventory.install_app(user, self.app, purchase_key='system-camera')
            self.positions.upsert(user, dict(lat=50, lng=20))
            scan = PlayerScanSnapshotStore(self.path).record(user, [self.marker], 50, 20)
            PlayerMarkedTargetStore(self.path).upsert(user, {**self.marker, 'scan_id':scan['scan_id']})
            with db_connect(self.path) as conn:
                conn.execute('UPDATE player_storage SET capacity=1024,used=0 WHERE username=?', (user,))
                conn.execute('DELETE FROM response_camera_observations WHERE username=?', (user,))
                conn.execute('DELETE FROM player_scan_snapshots WHERE username=?', (user,))
        token = reset_hot_path_metrics()
        self.addCleanup(restore_hot_path_metrics, token)
        self.stack.enter_context(patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')))
        self.stack.enter_context(patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')))

    def start(self, user, flow, source='launch_queue'):
        self.generation.authenticate(self.client, user)
        launch = self.client.post('/hack-action', json={**self.marker, 'action':'camera_stream',
            'selected_app_id':self.app['id'], '_client_action_key':'same-target-key', '_flow_id':flow})
        self.assertEqual(launch.status_code, 200, launch.json)
        payload = {**self.payload, 'expected_target':launch.json['target'],
                   'launch_source':source, 'launch_receipt':launch.json['added_apps'][0]['receipt']}
        result = self.client.post('/gonna-win', json=payload)
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(result.json['success'], result.json)
        replay = self.client.post('/gonna-win', json=payload)
        self.assertTrue(replay.json['duplicate'])
        return result.json

    def activate(self, key):
        self.generation.authenticate(self.client, 'attacker')
        response = self.client.post('/api/ghostnetwork/ability', json={'request_id':key})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(response.json['ok'], response.json)
        return response.json

    def finish(self, user, result):
        state = result['camera_visual']
        op = self.operations.list_active_operations(user, limit=20)[0]
        end = run.parse_operation_timestamp(op['expires_at'])
        data = dict(receipt=state['reference_id'], owner='system-test-owner-' + user)
        # Even an early terminal operation cannot grant early access.
        op['status'] = 'timeout'
        self.operations.upsert_operations(user, [op])
        with patch('camera_visual.time.time', return_value=end - 1):
            self.service.finalize(user, op)
            self.assertEqual(self.inventory.list_data_files(user, operation_id=op['operation_id']), [])
            with self.assertRaises(PilotError):
                self.service.window(user, data)
        with patch('camera_visual.time.time', return_value=end):
            self.service.finalize(user, op)
            self.assertEqual(len(self.inventory.list_data_files(user, operation_id=op['operation_id'])), 1)
            from camera_visual_archive import ArchiveStore
            ArchiveStore(self.path).process_one()
            opened = self.service.window(user, data)['camera_visual']
            self.assertEqual(opened['state'], 'ready')
            self.assertEqual(opened['ready_at'], end)
            self.assertTrue(opened['material'])
            # Recreate service and lease: persisted photo, path and FX survive recovery.
            self.service.window(user, {**data, 'action':'release'})
            restored = CameraVisual(run).window(user, data)['camera_visual']
            self.assertEqual(opened['feed'], restored['feed'])
            self.service.window(user, {**data, 'action':'close'})
            self.assertFalse(self.service.window(user, data)['granted'])
        return opened

    def assert_light(self):
        metrics = get_hot_path_metrics()
        for key in ('profile_full_read', 'profile_full_write', 'profile_bytes'):
            self.assertEqual(metrics[key], 0, (key, metrics))

    def test_active_power_real_http_hook_cross_account_and_repeat(self):
        self.system(big=True)
        self.activate('before-download')
        powered = self.start('attacker', 'first')
        normal = self.start('victim', 'first')
        with self.assertRaises(PilotError):
            self.service.window('victim', dict(receipt=powered['camera_visual']['reference_id'],
                                               owner='foreign-owner-system-test'))
        self.assertEqual(powered['camera_visual']['ready_at'] - powered['camera_visual']['download_at'], 300)
        self.assertEqual(normal['camera_visual']['ready_at'] - normal['camera_visual']['download_at'], 1800)
        first = self.finish('attacker', powered)
        other = self.finish('victim', normal)
        self.assertNotEqual(first['instance_id'], other['instance_id'])
        self.assertNotEqual(first['motion'], other['motion'])
        # Desktop and terminal contracts use independent invocations on the same mark.
        for source in ('desktop_menu', 'terminal'):
            new = self.start('attacker', source, source)
            view = self.finish('attacker', new)
            self.assertNotEqual(view['instance_id'], first['instance_id'])
            self.assertNotEqual(view['motion'], first['motion'])
        self.assert_light()

    def test_mid_download_activation_replay_and_canonical_clock(self):
        self.system()
        with patch.dict(run.DEFAULT_OPERATION_DURATIONS_SECONDS, camera_stream=300):
            result = self.start('attacker', 'mid-download')
        original = result['camera_visual']
        self.now = datetime.fromtimestamp(original['download_at'] + 60, timezone.utc)
        self.activate('during-download')
        op = self.operations.list_active_operations('attacker', limit=20)[0]
        end = run.parse_operation_timestamp(op['expires_at'])
        self.assertAlmostEqual(end - self.now.timestamp(), 40, places=4)
        self.activate('during-download')
        self.assertEqual(self.operations.list_active_operations('attacker', limit=20)[0]['expires_at'], op['expires_at'])
        with patch('camera_visual.time.time', return_value=end - 1):
            snapshot = self.client.get('/api/camera-visual/state').json['sessions'][0]
            self.assertEqual(snapshot['ready_at'], end)
            self.assertEqual(snapshot['state'], 'downloading')
        self.finish('attacker', result)
        self.assert_light()

    def test_operational_prediction_generated_app_and_expired_window(self):
        self.system(profession='algorithm_curator', part_code='V5')
        self.app = {**self.app, 'id':'generated-camera-system', 'name':'Independent camera app'}
        self.inventory.install_app('attacker', self.app, purchase_key='generated-power-camera')
        self.payload['app_id'] = self.app['id']
        self.activate('prediction-camera')
        result = self.start('attacker', 'prediction', 'terminal')
        self.assertEqual(result['camera_visual']['ready_at'] - result['camera_visual']['download_at'], 300)
        self.assertEqual(result['created_operations'][0]['ability_provenance']['ability_code'], 'operational_prediction')
        self.finish('attacker', result)
        # Expiry affects new operations, never reverses a duration already granted.
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        ordinary = dict(operation_id='after-window', started_at=future.isoformat(),
                        expires_at=(future + timedelta(seconds=1800)).isoformat(), duration_seconds=1800)
        self.assertFalse(run.apply_active_ghostnetwork_ability_to_new_operation('attacker', ordinary, now=future))
        self.assertEqual(ordinary['duration_seconds'], 1800)
        self.assert_light()
