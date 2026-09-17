import copy
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
import test_player_hack_read_paths as fixtures
from database import (PlayerScanSnapshotStore, PlayerPositionStore, PlayerOperationStore, PlayerMarkedTargetStore, PlayerTargetRuntimeStore,
                      GameStateDeltaBus, db_connect, reset_hot_path_metrics,
                      get_hot_path_metrics, restore_hot_path_metrics)
from response_network.camera_contract import camera_marker, CameraContractStore, CameraContractError


class CameraShutdownContractTest(unittest.TestCase):
    setUp = fixtures.PlayerHackReadPathsTest.setUp
    seed = fixtures.PlayerHackReadPathsTest.seed

    def test_map_desktop_terminal_and_new_scan_share_one_operation(self):
        self.prepare()
        runtime = PlayerTargetRuntimeStore(self.path)
        target = {**self.camera, 'lng': self.camera['lon'], 'scan_id': self.scan['scan_id']}
        runtime.upsert_aimed('attacker', target)
        with patch.object(run, 'player_target_runtime_store', runtime), \
                patch.object(run, 'sync_session_profile', side_effect=AssertionError('heavy path')):
            first = self.client.post('/gonna-win', json={'app_id': 'cam-off', 'launch_source': 'desktop'})
            self.assertEqual(first.status_code, 200, first.json)
            original = first.json['created_operations'][0]
            second = self.client.post('/hack-action', json=self.payload)
            self.assertEqual(second.status_code, 200, second.json)
            self.assertEqual(second.json['created_operations'][0], original)
            newer = self.scans.record('attacker', [self.camera], 52.1, 21.2)
            third = self.client.post('/hack-action', json={**self.payload, 'scan_id': newer['scan_id']})
            self.assertEqual(third.json['created_operations'][0], original)
            fourth = self.client.post('/gonna-win', json={'app_id': 'cam-off', 'launch_source': 'terminal'})
            self.assertTrue(fourth.json['duplicate'], fourth.json)
            self.assertEqual(fourth.json['created_operations'][0]['expires_at'], original['expires_at'])
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_operations').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT count(*) FROM player_launch_entries').fetchone()[0], 0)

    def test_legacy_operation_at_same_camera_prevents_second_operation(self):
        self.prepare()
        old = run.build_operation_instance('attacker', {'id': 'cam-off'}, 'exploit', 'camera_shutdown',
                                            {**self.camera, 'lng': self.camera['lon']})
        old['target'].pop('camera_id', None)
        self.operations.upsert_operations('attacker', [old])
        response = self.client.post('/hack-action', json=self.payload)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(response.json['duplicate'])
        self.assertEqual(response.json['created_operations'][0]['operation_id'], old['operation_id'])

    def test_map_then_other_desktop_app_keeps_original_timer(self):
        self.prepare()
        runtime = PlayerTargetRuntimeStore(self.path)
        runtime.upsert_aimed('attacker', {**self.camera, 'lng': self.camera['lon'], 'scan_id': self.scan['scan_id']})
        self.inventory.install_app('attacker', {'id': 'cam-other', 'map_actions': ['camera_shutdown'],
                                              'target_types': ['camera']}, purchase_key='other-camera')
        first = self.client.post('/hack-action', json=self.payload).json['created_operations'][0]
        with patch.object(run, 'player_target_runtime_store', runtime), \
                patch.object(run, 'sync_session_profile', side_effect=AssertionError('heavy path')):
            response = self.client.post('/gonna-win', json={'app_id': 'cam-other', 'launch_source': 'desktop'})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(response.json['duplicate'])
        self.assertEqual(response.json['created_operations'][0], first)

    def test_old_scan_rejected_with_actionable_message_on_desktop(self):
        self.prepare()
        runtime = PlayerTargetRuntimeStore(self.path)
        target = {**self.camera, 'lng': self.camera['lon']}
        target.pop('camera_id')
        runtime.upsert_aimed('attacker', target)
        with patch.object(run, 'player_target_runtime_store', runtime):
            response = self.client.post('/gonna-win', json={'app_id': 'cam-off'})
        self.assertEqual(response.status_code, 409, response.json)
        self.assertIn('nowy scan', response.json['message'])

    def prepare(self, big=False):
        self.seed(big_attacker=big)
        self.scans = PlayerScanSnapshotStore(self.path)
        self.positions = PlayerPositionStore(self.path)
        self.operations = PlayerOperationStore(self.path)
        self.delta = GameStateDeltaBus(self.path)
        for key, store in [('player_scan_snapshot_store', self.scans), ('player_position_store', self.positions),
                           ('player_operation_store', self.operations), ('delta_bus', self.delta)]:
            self.stack.enter_context(patch.object(run, key, store))
        self.stack.enter_context(patch.object(run, 'foreign_territory_action_block', return_value=None))
        self.camera = camera_marker({'lat': 52.1, 'lng': 21.2, 'osm_id': 'node:123'})
        self.scan = self.scans.record('attacker', [self.camera], 52.1, 21.2)
        self.positions.upsert('attacker', {'lat': 52.1, 'lng': 21.2})
        self.inventory.install_app('attacker', {'id': 'cam-off', 'name': 'Camera Off',
            'map_actions': ['camera_shutdown'], 'operation_types': ['camera_shutdown'],
            'target_types': ['camera']}, purchase_key='camera-test')
        self.payload = {'action': 'camera_shutdown', 'camera_id': self.camera['camera_id'],
                        'scan_id': self.scan['scan_id'], 'selected_app_id': 'cam-off'}

    def test_shutdown_replay_and_launcher_confirmation_no_full_profile(self):
        self.prepare(big=True)
        token = reset_hot_path_metrics()
        self.addCleanup(restore_hot_path_metrics, token)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(run, 'sync_session_profile', side_effect=AssertionError('hydrate')):
            response = self.client.post('/hack-action', json=self.payload)
            self.assertEqual(response.status_code, 200, response.json)
            op = response.json['created_operations'][0]
            self.assertEqual(op['target']['camera_id'], self.camera['camera_id'])
            replay = self.client.post('/hack-action', json=self.payload)
            self.assertTrue(replay.json['duplicate'], replay.json)
            confirmed = self.client.post('/gonna-win', json={'app_id': 'cam-off', 'launch_receipt': op['operation_id']})
            self.assertEqual(confirmed.status_code, 200, confirmed.json)
        metrics = get_hot_path_metrics()
        for key in ('profile_full_read', 'profile_full_write', 'profile_bytes'):
            self.assertEqual(metrics.get(key, 0), 0, metrics)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM player_operations WHERE operation_type='camera_shutdown'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM player_launch_entries WHERE username='attacker'").fetchone()[0], 1)

    def test_unknown_camera_other_scan_and_wrong_app_cannot_mutate(self):
        self.prepare()
        for changes in ({'camera_id': 'invented'}, {'scan_id': 'invented'}, {'selected_app_id': 'systemLogReader'}):
            response = self.client.post('/hack-action', json={**self.payload, **changes})
            self.assertEqual(response.status_code, 409, response.json)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_operations').fetchone()[0], 0)

    def test_mark_refresh_then_shutdown_keeps_camera_evidence(self):
        self.prepare()
        marked = PlayerMarkedTargetStore(self.path)
        marked.ensure_seeded('attacker')
        target = {**self.camera, 'lng': self.camera['lon'], 'scan_id': self.scan['scan_id']}
        with patch.object(run, 'player_marked_target_store', marked), \
                patch.object(run.territory_store, 'list_captured_targets', return_value=[]), \
                patch.object(run, 'sync_session_profile', side_effect=AssertionError('heavy path')):
            response = self.client.post('/map-action', json={**target, 'action': 'mark_target'})
            self.assertEqual(response.status_code, 200, response.json)
            refreshed = self.client.get('/api/map/target-snapshot')
            self.assertEqual(refreshed.status_code, 200, refreshed.json)
            for restored in (response.json['target'], refreshed.json['targets'][0]):
                self.assertEqual(restored['camera_id'], target['camera_id'])
                self.assertEqual(restored['scan_id'], target['scan_id'])
                result = self.client.post('/hack-action', json={**restored, 'action': 'camera_shutdown',
                                                               'selected_app_id': 'cam-off'})
                self.assertEqual(result.status_code, 200, result.json)
            self.assertTrue(result.json['duplicate'])

    def test_selection_uses_canonical_coordinates_and_preserves_evidence(self):
        self.prepare()
        payload = {**self.payload, 'selected_app_id': '', 'lat': 0, 'lng': 0, 'name': 'Forged'}
        response = self.client.post('/hack-action', json=payload)
        self.assertTrue(response.json['tool_selection_required'], response.json)
        self.assertEqual(response.json['pending_action']['lat'], self.camera['lat'])
        self.scans.record('attacker', [], 0, 0)
        response = self.client.post('/hack-action', json=self.payload)
        self.assertEqual(response.status_code, 200, response.json)

    def test_atomic_rollback_when_launch_write_fails(self):
        self.prepare()
        with patch.object(self.inventory, 'commit_launch', side_effect=RuntimeError('failure')):
            with run.app.test_request_context('/hack-action', json=self.payload):
                run.session['user'] = 'attacker'
                with self.assertRaises(RuntimeError):
                    run.camera_shutdown_action(self.payload)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_operations').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT count(*) FROM operation_events').fetchone()[0], 0)

    def test_range_and_expired_scan_fail_closed(self):
        self.prepare()
        self.positions.upsert('attacker', {'lat': 0, 'lng': 0})
        response = self.client.post('/hack-action', json=self.payload)
        self.assertEqual(response.json['reason'], 'camera_out_of_range')
        with db_connect(self.path) as conn:
            conn.execute('UPDATE response_camera_observations SET expires_at=0')
        response = self.client.post('/hack-action', json=self.payload)
        self.assertEqual(response.json['reason'], 'camera_scan_expired_or_unknown')

    def test_generated_identity_and_position_are_stable(self):
        parent = {'lat': 52.1, 'lng': 21.2, 'osm_id': 'node:123'}
        self.assertEqual(camera_marker(parent), camera_marker(copy.deepcopy(parent)))
        self.assertNotEqual(camera_marker(parent)['camera_id'], camera_marker(parent, 1)['camera_id'])

    def test_new_scan_does_not_reset_active_shutdown_and_cancel_removes_support(self):
        self.prepare()
        first = self.client.post('/hack-action', json=self.payload).json
        newer = self.scans.record('attacker', [self.camera, self.camera], 52.1, 21.2)
        second = self.client.post('/hack-action', json={**self.payload, 'scan_id': newer['scan_id']}).json
        self.assertTrue(second['duplicate'], second)
        self.assertEqual(first['created_operations'], second['created_operations'])
        operation_id = first['created_operations'][0]['operation_id']
        cancelled, _ = self.operations.cancel_operation('attacker', operation_id)
        self.assertFalse(cancelled['support_state']['active'])
        replay = self.client.post('/hack-action', json=self.payload).json
        self.assertEqual(replay['created_operations'][0]['status'], 'cancelled')

    def test_commit_rechecks_position_app_and_territory(self):
        self.prepare()
        original = CameraContractStore.shutdown
        for mutation in ('position', 'app', 'territory'):
            def raced(store, *args, **kwargs):
                if mutation == 'position':
                    self.positions.upsert('attacker', {'lat': 0, 'lng': 0})
                if mutation == 'app':
                    with db_connect(self.path) as conn:
                        conn.execute("UPDATE player_apps SET status='uninstalled' WHERE app_id='cam-off'")
                if mutation == 'territory':
                    with patch.object(run, 'foreign_territory_action_block', return_value={'id': 1}):
                        return original(store, *args, **kwargs)
                return original(store, *args, **kwargs)
            with patch.object(CameraContractStore, 'shutdown', raced):
                response = self.client.post('/hack-action', json=self.payload)
                self.assertEqual(response.status_code, 409, response.json)
            self.positions.upsert('attacker', {'lat': 52.1, 'lng': 21.2})
            with db_connect(self.path) as conn:
                conn.execute("UPDATE player_apps SET status='installed' WHERE app_id='cam-off'")
                self.assertEqual(conn.execute('SELECT count(*) FROM player_operations').fetchone()[0], 0)

    def test_other_player_cannot_use_observation_or_confirm_receipt(self):
        self.prepare()
        operation = self.client.post('/hack-action', json=self.payload).json['created_operations'][0]
        with self.assertRaises(CameraContractError):
            CameraContractStore(self.path).observed('victim', self.scan['scan_id'], self.camera['camera_id'])
        response = self.client.post('/gonna-win', json={'app_id': 'other', 'launch_receipt': operation['operation_id']})
        self.assertEqual(response.status_code, 409)

    def test_parallel_retries_commit_once_and_restart_reads_same_receipt(self):
        self.prepare()
        def shutdown(_):
            store = CameraContractStore(self.path)
            return store.shutdown('attacker', self.scan['scan_id'], self.camera['camera_id'],
                                  'cam-off', guard=lambda conn, target: None,
                                  inventory=self.inventory, messages=self.messages, deltas=self.delta)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(shutdown, range(2)))
        self.assertEqual(sorted(duplicate for _, duplicate in results), [False, True])
        self.assertEqual(results[0][0], results[1][0])
        self.assertTrue(shutdown(2)[1])
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_operations').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT count(*) FROM operation_events').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT count(*) FROM player_launch_entries').fetchone()[0], 1)
