import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import run
from database import db_connect, get_hot_path_metrics, reset_hot_path_metrics, restore_hot_path_metrics
import test_camera_shutdown_contract as camera_fixtures
from response_network.camera_contract import camera_marker
from response_network.camera_exposure import capture_exposure, shutdown_windows, bind_windows
from response_network.operation_risk_meter import update_operation_risk_meter
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore


class CameraExposureTest(unittest.TestCase):
    setUp = camera_fixtures.CameraShutdownContractTest.setUp
    seed = camera_fixtures.CameraShutdownContractTest.seed
    prepare = camera_fixtures.CameraShutdownContractTest.prepare

    def scene(self, big=False):
        self.prepare(big=big)
        self.parent = {'lat': 52.1, 'lng': 21.2, 'osm_id': 'shop-1',
                       'source_type': 'shop', 'label': 'Shop'}
        self.cameras = [camera_marker(self.parent, i) for i in range(2)]
        self.scan = self.scans.record('attacker', [self.parent, *self.cameras], 52.1, 21.2)
        self.now = datetime.now(timezone.utc)

    def operation(self):
        with patch.object(run, 'apply_active_ghostnetwork_ability_to_new_operation'):
            op = run.build_operation_instance('attacker', {'id': 'test', 'quality_score': 100,
                 'reliability': 100, 'creator_power': 0}, 'sniff', 'persistent_sniffer',
                 {**self.parent, 'scan_id': self.scan['scan_id'], 'security': {'camera': True}})
        # 20 base + 13 time + 25 conflict = 58; cameras alone cross 60.
        op.update(started_at=(self.now - timedelta(seconds=130)).isoformat(),
                  expires_at=(self.now + timedelta(seconds=170)).isoformat(),
                  target_mode='territory_contest')
        update_operation_risk_meter(op, now_ts=self.now)
        return op

    def shutdown(self, index=0):
        response = self.client.post('/hack-action', json={**self.payload,
            'camera_id': self.cameras[index]['camera_id'], 'scan_id': self.scan['scan_id']})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['created_operations'][0]

    def refresh(self, op, now=None):
        bind_windows(op, shutdown_windows(self.path, op['owner_username']))
        update_operation_risk_meter(op, now_ts=now or self.now)
        return op['operation_risk_meter']

    def test_real_shutdown_changes_threshold_without_stacking_or_other_risk(self):
        self.scene()
        op = self.operation()
        initial = op['operation_risk_meter']
        self.assertEqual(initial['current_heat'], 62)
        self.shutdown()
        one = self.refresh(op)
        self.assertEqual(one['current_heat'], 58)
        self.assertFalse(one['incident_crossed'])
        self.assertEqual(one['camera_state']['disabled'], 1)
        for key in ('base_heat', 'time_heat', 'tool_modifier', 'security_modifier', 'conflict_modifier'):
            self.assertEqual(one[key], initial[key])
        self.shutdown(1)
        two = self.refresh(op)
        self.assertEqual(two['current_heat'], 58)
        self.assertEqual(two['camera_state']['disabled'], 2)

    def test_existing_incident_survives_reduction_and_partial_actor_batch(self):
        self.scene()
        op = self.operation()
        other = copy.deepcopy(op)
        other.update(operation_id='other-player', owner_username='victim')
        store = IncidentStore(self.path)
        initializer = IncidentInitializer(store)
        initializer.sync_operations([op, other], now=self.now)
        incident_id = op['operation_risk_meter']['incident_id']
        self.shutdown()
        self.refresh(op)
        initializer.sync_operations([op], now=self.now)
        saved = store.get(incident_id)
        self.assertNotEqual(saved['status'], 'cancelled')
        self.assertEqual(set(saved['operation_ids']), {op['operation_id'], 'other-player'})
        self.assertEqual(next(r['heat'] for r in saved['operation_refs']
                             if r['operation_id'] == op['operation_id']), 58)
        # A separate scene with only this operation also stays alive below 60.
        other['status'] = 'cancelled'
        update_operation_risk_meter(other, now_ts=self.now)
        initializer.sync_operations([op, other], now=self.now)
        self.assertEqual(store.get(incident_id)['heat'], 58)
        self.assertEqual(op['operation_risk_meter']['incident_id'], incident_id)

    def test_rescan_ttl_restart_and_expiry_do_not_erase_frozen_evidence(self):
        self.scene()
        op = self.operation()
        shutdown = self.shutdown()
        self.refresh(op)
        self.operations.upsert_operations('attacker', [op])
        self.scans.record('attacker', [], 0, 0)
        with db_connect(self.path) as conn:
            conn.execute('DELETE FROM response_camera_observations')
        restored = next(o for o in self.operations.list_operations('attacker')
                        if o['operation_id'] == op['operation_id'])
        self.assertEqual(self.refresh(restored)['camera_modifier'], 0)
        end = datetime.fromisoformat(shutdown['expires_at'])
        self.assertEqual(self.refresh(restored, end)['camera_modifier'], 4)
        self.assertEqual(restored['camera_exposure']['camera_ids'], op['camera_exposure']['camera_ids'])

    def test_scope_owner_cancel_and_unverified_shutdown(self):
        self.scene()
        op = self.operation()
        shutdown = self.shutdown()
        foreign = copy.deepcopy(op)
        foreign['owner_username'] = 'victim'
        foreign['camera_exposure']['owner_username'] = 'victim'
        self.assertEqual(self.refresh(foreign)['camera_modifier'], 4)
        remote = copy.deepcopy(op)
        remote['camera_exposure']['scope'] = 'other-shop'
        self.assertEqual(self.refresh(remote)['camera_modifier'], 4)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_operations SET status='cancelled' WHERE operation_id=?",
                         (shutdown['operation_id'],))
        self.assertEqual(self.refresh(op)['camera_modifier'], 4)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_operations SET status='running', operation_json=json_remove(operation_json, '$.camera_evidence') WHERE operation_id=?", (shutdown['operation_id'],))
        self.assertEqual(self.refresh(op)['camera_modifier'], 4)

    def test_no_cameras_unknown_snapshot_and_forged_client_flags(self):
        self.scene()
        forged = {**self.parent, 'camera_disabled': True, 'parent_target_id': 'forged',
                  'camera_exposure': {'known': True, 'camera_ids': []}}
        captured = capture_exposure(self.path, 'attacker', forged)
        self.assertEqual(len(captured['camera_ids']), 2)
        self.assertEqual(captured['scope'], 'shop-1')
        self.assertFalse(capture_exposure(self.path, 'victim', forged)['known'])
        self.assertFalse(capture_exposure(self.path, 'attacker', {**forged, 'scan_id': 'fake'})['known'])
        self.scans.record('attacker', [self.parent], 52.1, 21.2)
        op = self.operation()
        op['camera_exposure'] = capture_exposure(self.path, 'attacker', self.parent)
        self.assertEqual(self.refresh(op)['current_heat'], 58)
        self.assertEqual(op['operation_risk_meter']['camera_state']['detected'], 0)

    def test_large_profile_worker_uses_canonical_state_and_live_delta(self):
        self.scene(big=True)
        op = self.operation()
        self.operations.upsert_operations('attacker', [op])
        self.shutdown()
        token = reset_hot_path_metrics()
        self.addCleanup(restore_hot_path_metrics, token)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(run, 'active_ghostnetwork_operation_risk_rules', return_value={}), \
             patch.object(run, 'incident_initializer', IncidentInitializer(IncidentStore(self.path))), \
             patch.object(run, 'publish_incident_actions'), \
             patch.object(run, 'sync_response_warnings', return_value=[]), \
             patch.object(self.delta, 'record_change', wraps=self.delta.record_change) as delta:
            run.process_operation_runtime_tick(min_age_seconds=0, now_ts=self.now.timestamp() + 1)
        restored = next(o for o in self.operations.list_operations('attacker')
                        if o['operation_id'] == op['operation_id'])
        self.assertEqual(restored['operation_risk_meter']['camera_modifier'], 0)
        self.assertTrue(any(c.args[2] == 'map.operations_changed' for c in delta.call_args_list))
        metrics = get_hot_path_metrics()
        for key in ('profile_full_read', 'profile_full_write', 'profile_bytes'):
            self.assertEqual(metrics.get(key, 0), 0, metrics)

    def test_delta_failure_rolls_back_risk_and_next_tick_recovers(self):
        self.scene()
        op = self.operation()
        self.operations.upsert_operations('attacker', [op])
        self.shutdown()
        with patch.object(run, 'active_ghostnetwork_operation_risk_rules', return_value={}), \
             patch.object(self.delta, 'record_change', side_effect=RuntimeError('outbox failed')):
            with self.assertRaisesRegex(RuntimeError, 'outbox failed'):
                run.process_operation_runtime_tick(min_age_seconds=0, now_ts=self.now.timestamp() + 1)
        restored = next(o for o in self.operations.list_operations('attacker')
                        if o['operation_id'] == op['operation_id'])
        self.assertEqual(restored['operation_risk_meter']['camera_modifier'], 4)
        with patch.object(run, 'active_ghostnetwork_operation_risk_rules', return_value={}), \
             patch.object(run, 'incident_initializer', IncidentInitializer(IncidentStore(self.path))), \
             patch.object(run, 'publish_incident_actions'), \
             patch.object(run, 'sync_response_warnings', return_value=[]):
            run.process_operation_runtime_tick(min_age_seconds=0, now_ts=self.now.timestamp() + 2)
        restored = next(o for o in self.operations.list_operations('attacker')
                        if o['operation_id'] == op['operation_id'])
        self.assertEqual(restored['operation_risk_meter']['camera_modifier'], 0)
