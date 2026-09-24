import copy
import unittest
import tempfile
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from response_network.qualification import DetectionQualification, actor_snapshot
from session_generation_store import username_digest


class ResponseQualificationTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)
        self.actor = {'session': {'status': 'active', 'updated_at': (self.now-timedelta(hours=1)).isoformat(), 'active_revision': 3},
            'presence': {'last_seen_at': self.now.isoformat()},
            'position': {'lat': 52, 'lng': 21, 'version': 7, 'updated_at': self.now.isoformat()}}
        self.incident = {'incident_id': 'incident', 'status': 'escalated', 'version': 2,
            'suspect_refs': [{'actor_id': 'alice'}], 'operation_ids': [],
            'expires_at': (self.now-timedelta(hours=1)).isoformat()}
        self.capsule = {'incident_id': 'incident', 'status': 'active',
            'spawn_at': (self.now-timedelta(minutes=1)).isoformat(),
            'expires_at': (self.now+timedelta(minutes=5)).isoformat(),
            'behavior_version': 1, 'trajectory_seed': 'seed', 'tracking_tokens': ['public'],
            'detection_radius_m': 65}
        self.candidate = {'actor_id': 'alice', 'incident_id': 'incident', 'capsule_id': 'npc',
            'detected_at': self.now.isoformat(), 'position_version': 7,
            'actor_position': {'lat': 52, 'lng': 21}, 'npc_position': {'lat': 52, 'lng': 21},
            'tracking_token': 'public', 'behavior_version': 1, 'trajectory_seed': 'seed',
            'mode': 'full', 'operation_id': 'forged'}
        self.reader = Mock(side_effect=lambda username: copy.deepcopy(self.actor))
        self.incidents = Mock(); self.incidents.get.return_value = self.incident
        self.capsules = Mock(); self.capsules.get.return_value = self.capsule
        self.audit = Mock(); self.audit.record.side_effect = lambda c, d, now: ({'candidate_id': c['candidate_id']}, True)
        self.qualifier = DetectionQualification(self.incidents, self.capsules, self.audit, self.reader)
        self.env = patch.dict('os.environ', {'CHAOS_RESPONSE_QUALIFICATION_MODE': 'observe'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.movement = patch('response_network.qualification.position_at', return_value={'lat': 52, 'lng': 21})
        self.movement.start(); self.addCleanup(self.movement.stop)

    def result(self):
        return self.qualifier.qualify(self.candidate, 'observer', self.now)

    def test_treasury_is_not_a_player_candidate(self):
        self.candidate['actor_id'] = 'admin'
        self.assertEqual(self.result()['reason'], 'system_treasury_account')
        self.reader.assert_not_called()

    def test_initiator_without_active_operation_is_observed_never_executed(self):
        result = self.result()
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['actor_role'], 'initiator')
        self.assertFalse(result['consequence_executed'])
        self.assertEqual(self.audit.record.call_args.args[0]['operation_id'], '')

    def test_three_services_roles_presence_and_distance_matrix(self):
        from config import response_service_detection_radius
        from response_network.npc_capsule_factory import _project_point
        from response_network.detection_validator import _distance_m
        original = copy.deepcopy(self.actor)
        center = {'lat': 52, 'lng': 21}
        for family in ('police', 'cyberpolice', 'secretservice'):
            radius = response_service_detection_radius(2, 1)
            for role in ('initiator', 'bystander'):
                for state in ('online_active', 'online_inactive', 'offline', 'expired', 'heartbeat_timeout'):
                    for place, meters in (('inside', radius - 1), ('boundary', radius), ('outside', radius + 1)):
                        with self.subTest(family=family, role=role, state=state, place=place):
                            self.actor = copy.deepcopy(original)
                            self.capsule['visual_family'] = family
                            self.incident['suspect_refs'] = [{'actor_id':'alice'}] if role == 'initiator' else []
                            point = _project_point(center, meters, 90)
                            self.actor['position'].update(point)
                            self.candidate['actor_position'] = point
                            # Exact computed boundary avoids a floating-point metre discrepancy.
                            self.capsule['detection_radius_m'] = _distance_m(center, point) if place == 'boundary' else radius
                            if state == 'online_inactive':
                                self.actor['position']['updated_at'] = (self.now-timedelta(hours=3)).isoformat()
                            elif state in ('offline', 'expired'):
                                self.actor['session']['status'] = 'logged_out' if state == 'offline' else 'expired'
                            elif state == 'heartbeat_timeout':
                                self.actor['presence']['last_seen_at'] = (self.now-timedelta(seconds=91)).isoformat()
                            result = self.result()
                            expected = state.startswith('online_') and place != 'outside'
                            self.assertEqual(result['qualified'], expected, result)
                            if expected:
                                self.assertEqual(result['actor_role'], role)
                                self.assertEqual(result['presence_class'], state)

    def test_old_patrol_radius_cannot_be_used_as_radar(self):
        for radius in (300, 2000, 39000):
            with self.subTest(radius=radius):
                self.capsule['detection_radius_m'] = radius
                result = self.result()
                self.assertFalse(result['qualified'])
                self.assertEqual(result['reason'], 'capsule_recalibration_required')
        self.audit.record.assert_not_called()

    def test_bystander_and_stationary_online_are_classified(self):
        self.incident['suspect_refs'] = []
        self.actor['position']['updated_at'] = (self.now-timedelta(hours=3)).isoformat()
        result = self.result()
        self.assertEqual(result['actor_role'], 'bystander')
        self.assertEqual(result['presence_class'], 'online_inactive')
        self.assertTrue(result['qualified'])

    def test_global_gate_precedes_all_store_reads(self):
        for mode in ('disabled', 'full', 'bogus'):
            with patch.dict('os.environ', {'CHAOS_RESPONSE_QUALIFICATION_MODE': mode}):
                self.assertEqual(self.result()['status'], 'disabled')
        self.reader.assert_not_called(); self.incidents.get.assert_not_called()

    def test_stale_future_and_invalid_time_never_load_actor(self):
        for value in ((self.now-timedelta(seconds=16)).isoformat(), (self.now+timedelta(seconds=4)).isoformat(), 'bad', None):
            self.candidate['detected_at'] = value
            self.assertFalse(self.result()['qualified'])
        self.reader.assert_not_called()

    def test_offline_expired_and_missing_presence_block_even_with_public_token(self):
        for state, reason in (('logged_out', 'actor_offline'), ('expired', 'actor_session_expired'), ('unknown', 'session_projection_missing')):
            self.actor['session']['status'] = state
            self.assertEqual(self.result()['reason'], reason)
        self.actor['session']['status'] = 'active'
        self.actor['presence'] = None
        self.assertEqual(self.result()['reason'], 'presence_projection_missing')
        self.actor['presence'] = {'last_seen_at': (self.now-timedelta(seconds=91)).isoformat()}
        self.assertEqual(self.result()['reason'], 'actor_offline')
        self.audit.record.assert_not_called()

    def test_relogin_does_not_replay_old_detection(self):
        self.actor['session']['updated_at'] = self.now.isoformat()
        self.candidate['detected_at'] = (self.now-timedelta(seconds=1)).isoformat()
        self.assertEqual(self.result()['reason'], 'detection_before_current_login')

    def test_forged_position_and_old_revision_fail(self):
        self.candidate['position_version'] = 6
        self.assertEqual(self.result()['reason'], 'stale_position_version')
        self.candidate['position_version'] = 7
        self.actor['position']['lat'] = 53
        self.assertEqual(self.result()['reason'], 'actor_position_mismatch')
        self.candidate['actor_position']['lat'] = 53
        self.assertEqual(self.result()['reason'], 'actor_outside_detection_radius')

    def test_cooling_and_capsule_expiry_use_server_now(self):
        self.incident['status'] = 'cooling'
        self.assertEqual(self.result()['reason'], 'incident_cooling_expired')
        self.incident['status'] = 'escalated'
        self.capsule['expires_at'] = self.now.isoformat()
        self.assertEqual(self.result()['reason'], 'capsule_time_window_closed')

    def test_wrong_capsule_and_missing_projection_fail_closed(self):
        self.capsule['incident_id'] = 'other'
        self.assertEqual(self.result()['reason'], 'capsule_incident_mismatch')
        self.actor['position'] = None
        self.assertEqual(self.result()['reason'], 'position_projection_missing')

    def test_actor_snapshot_reads_canonical_rows_without_user_profile_table(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'actor.sqlite3')
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''
                    CREATE TABLE account_login_ownership(username_hash TEXT PRIMARY KEY,status TEXT,updated_at TEXT,active_revision INTEGER);
                    CREATE TABLE mail_presence(username TEXT PRIMARY KEY,last_seen_at TEXT);
                    CREATE TABLE player_positions(username TEXT PRIMARY KEY,lat REAL,lng REAL,version INTEGER,updated_at TEXT);
                ''')
                db.execute('INSERT INTO account_login_ownership VALUES (?,?,?,?)',
                    (username_digest('alice'), 'active', self.now.isoformat(), 3))
                db.execute('INSERT INTO mail_presence VALUES (?,?)', ('alice', self.now.isoformat()))
                db.execute('INSERT INTO player_positions VALUES (?,?,?,?,?)', ('alice', 52, 21, 7, self.now.isoformat()))
                db.commit()
            self.assertEqual(actor_snapshot(path, 'alice')['position']['version'], 7)
            self.assertEqual(actor_snapshot(path, 'missing'), {'session': None, 'presence': None, 'position': None})

    def test_public_tracking_token_does_not_override_offline_actor(self):
        self.actor['session']['status'] = 'logged_out'
        self.candidate['observer_username'] = 'alice'
        self.candidate['mode'] = 'full'
        self.assertEqual(self.result()['reason'], 'actor_offline')
        self.incidents.get.assert_not_called()
        self.audit.record.assert_not_called()
