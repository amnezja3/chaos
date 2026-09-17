"""Current camera/incident audit observations; not production acceptance."""
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import run
from response_network.incident_initializer import IncidentInitializer
from response_network.incident_store import IncidentStore
from response_network.operation_risk_meter import calculate_operation_risk, update_operation_risk_meter


class CameraIncidentAuditTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.operation = {
            'operation_id': 'scan-camera-audit', 'operation_type': 'camera_stream',
            'owner_username': 'audit', 'status': 'running', 'target_id': 'camera-1',
            'target': {'lat': 52.1, 'lng': 21.2, 'security': {'firewall': True}},
            'target_mode': 'territory_contest',
            'started_at': (self.now - timedelta(minutes=10)).isoformat(),
            'expires_at': (self.now + timedelta(minutes=10)).isoformat(),
            'source_app_quality': {'creator_power': 90, 'quality_score': 20, 'reliability': 20},
        }
        self.shutdown = {
            **copy.deepcopy(self.operation), 'operation_id': 'shutdown-1',
            'operation_type': 'camera_shutdown', 'support_state': {'active': True},
        }

    def test_legacy_camera_event_reduces_by_18_and_expiry_removes_reduction(self):
        profile = {'operations': [self.operation, self.shutdown]}
        reduced, modifiers, _ = run.apply_risk_modifiers(profile, self.operation, 'camera_detected', 46)
        self.assertEqual(reduced, 28)
        self.assertEqual(len(modifiers), 1)
        self.shutdown.update(status='timeout', support_state={'active': False})
        self.assertEqual(run.apply_risk_modifiers(profile, self.operation, 'camera_detected', 46)[0], 46)

    def test_audit_legacy_reduction_does_not_change_public_incident_heat(self):
        baseline = calculate_operation_risk(self.operation, now_ts=self.now)
        run.apply_risk_modifiers({'operations': [self.operation, self.shutdown]},
                                 self.operation, 'camera_detected', 46)
        after = calculate_operation_risk(self.operation, now_ts=self.now)
        self.assertEqual(after['current_heat'], baseline['current_heat'])
        self.assertTrue(after['incident_crossed'])
        update_operation_risk_meter(self.operation, now_ts=self.now)
        with tempfile.TemporaryDirectory() as directory:
            store = IncidentStore(str(Path(directory) / 'incident.sqlite3'))
            IncidentInitializer(store, None).sync_operations([self.operation], now=self.now)
            self.assertEqual(len(store.list_active()), 1)

    def test_security_camera_boolean_is_generic_pressure_not_scan_coverage(self):
        active = copy.deepcopy(self.operation)
        inactive = copy.deepcopy(self.operation)
        active['target']['security']['camera'] = True
        inactive['target']['security']['camera'] = False
        on = calculate_operation_risk(active, now_ts=self.now)
        off = calculate_operation_risk(inactive, now_ts=self.now)
        self.assertEqual(on['security_modifier'] - off['security_modifier'], 4)
