import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from database import db_connect, init_db
from session_generation_store import SessionGenerationStore, username_digest
from response_network.incident_store import IncidentStore
from response_network.npc_capsule_store import NPCCapsuleStore
from response_network.npc_capsule_factory import NPCCapsuleFactory, position_at
from response_network.encounters import EncounterStore


class ResponseEncountersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'encounters.sqlite3')
        init_db(self.path)
        self.now = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        self.incidents = IncidentStore(self.path)
        self.capsules = NPCCapsuleStore(self.path)
        SessionGenerationStore(self.path)
        self.incident = self.incidents.upsert({'incident_id': 'incident-one', 'status': 'escalated',
            'level': 4, 'center': {'lat': 52, 'lng': 21}, 'search_radius_m': 200,
            'suspect_refs': [{'actor_id': 'alice'}],
            'expires_at': (self.now + timedelta(minutes=30)).isoformat()}, now=self.now)
        self.capsule = NPCCapsuleFactory().build_for_incident(self.incident, now=self.now)[0]
        self.capsules.upsert(self.capsule, now=self.now)
        self.now += timedelta(seconds=30)
        self.point = position_at(self.capsule, self.now)
        self.roll = Mock(return_value=30)
        self.store = EncounterStore(self.incidents, self.capsules, self.path, self.roll)
        self.env = patch.dict('os.environ', {'CHAOS_RESPONSE_ENCOUNTERS_ENABLED': 'true', 'CHAOS_RESPONSE_QUALIFICATION_MODE': 'observe'})
        self.env.start(); self.addCleanup(self.env.stop)
        for actor in ('alice', 'bob'):
            self.seed_actor(actor)

    def seed_actor(self, actor):
        with db_connect(self.path) as conn:
            conn.execute('''INSERT INTO account_login_ownership
                (username_hash,status,created_at,updated_at) VALUES (?,?,?,?)''',
                (username_digest(actor), 'active', self.now.isoformat(), self.now.isoformat()))
            conn.execute('INSERT INTO mail_presence(username,last_seen_at) VALUES (?,?)', (actor, self.now.isoformat()))
            conn.execute('''INSERT INTO player_positions(username,lat,lng,source,version,updated_at)
                VALUES (?,?,?,'test',1,?)''', (actor, self.point['lat'], self.point['lng'], self.now.isoformat()))

    def candidate(self, actor='alice', capsule=None):
        capsule = capsule or self.capsule
        return {'actor_id': actor, 'incident_id': self.incident['incident_id'],
            'capsule_id': capsule['capsule_id'], 'detected_at': self.now.isoformat(),
            'actor_position': self.point, 'position_version': 1,
            'npc_position': position_at(capsule, self.now), 'tracking_token': capsule['tracking_tokens'][0],
            'behavior_version': capsule['behavior_version'], 'trajectory_seed': capsule['trajectory_seed']}

    def rows(self):
        with db_connect(self.path) as conn:
            return [dict(row) for row in conn.execute('SELECT * FROM response_encounters')]

    def test_thresholds_and_avoided_outcome_are_persisted(self):
        self.roll.return_value = 80
        a = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertTrue(a.get('qualified'), a)
        self.assertEqual(a['encounter']['chance'], 80)
        self.assertEqual(a['encounter']['outcome'], 'selected')
        self.roll.return_value = 31
        b = self.store.encounter(self.candidate('bob'), 'observer', now=self.now)
        self.assertEqual(b['encounter']['chance'], 30)
        self.assertEqual(b['encounter']['outcome'], 'avoided')
        self.assertEqual(len(self.rows()), 2)
        self.assertTrue(all(r['execution_status'] == 'not_enabled' for r in self.rows()))

    def test_concurrent_observers_draw_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda n: self.store.encounter(self.candidate(), str(n), now=self.now), range(4)))
        self.assertEqual(self.roll.call_count, 1)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(sum(not r['duplicate_encounter'] for r in results), 1)

    def test_restart_reconnect_and_other_patrol_do_not_reroll(self):
        first = self.store.encounter(self.candidate(), 'observer-one', now=self.now)
        other = {**self.capsule, 'capsule_id': 'another-patrol', 'npc_id': 'another-patrol'}
        self.capsules.upsert(other, now=self.now)
        with db_connect(self.path) as conn:
            conn.execute('UPDATE account_login_ownership SET active_revision=active_revision+1')
        restored = EncounterStore(self.incidents, self.capsules, self.path, Mock(side_effect=AssertionError('reroll')))
        replay = restored.encounter(self.candidate(capsule=other), 'observer-two', now=self.now)
        self.assertEqual(first['encounter'], replay['encounter'])
        self.assertTrue(replay['duplicate_encounter'])

    def test_offline_or_stale_position_never_consumes_draw(self):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE account_login_ownership SET status='logged_out'")
        self.assertFalse(self.store.encounter(self.candidate(), 'observer', now=self.now)['qualified'])
        self.roll.assert_not_called()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE account_login_ownership SET status='active'")
            conn.execute('UPDATE player_positions SET version=2')
        self.assertEqual(self.store.encounter(self.candidate(), 'observer', now=self.now)['reason'], 'stale_position_version')
        self.assertEqual(self.rows(), [])

    def test_closed_source_and_disabled_gate_never_draw(self):
        with patch.dict('os.environ', {'CHAOS_RESPONSE_ENCOUNTERS_ENABLED': 'false'}):
            self.assertEqual(self.store.encounter({}, '', now=self.now)['status'], 'disabled')
        self.incidents.upsert({**self.incident, 'status': 'resolved'}, now=self.now)
        self.assertFalse(self.store.encounter(self.candidate(), 'observer', now=self.now)['qualified'])
        self.roll.assert_not_called()

    def test_invalid_roll_rolls_back_then_retry_commits_once(self):
        self.roll.return_value = 101
        with self.assertRaises(ValueError):
            self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(self.rows(), [])
        self.roll.return_value = 81
        result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['encounter']['outcome'], 'avoided')

    def test_worker_finds_online_players_without_map_and_pages_dense_area(self):
        first = self.store.scan(now=self.now, patrol_limit=1, actor_limit=1)
        second = self.store.scan(now=self.now, patrol_limit=1, actor_limit=1)
        self.assertEqual(first['created'], 1)
        self.assertEqual(second['created'], 1)
        self.assertEqual({r['actor_id'] for r in self.rows()}, {'alice', 'bob'})
        self.assertEqual(self.roll.call_count, 2)
        self.store.scan(now=self.now, patrol_limit=1, actor_limit=1)
        self.store.scan(now=self.now, patrol_limit=1, actor_limit=1)
        self.assertEqual(self.roll.call_count, 2)

    def test_offline_return_uses_current_position_without_replaying_detection(self):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE account_login_ownership SET status='logged_out'")
        self.assertEqual(self.store.scan(now=self.now)['created'], 0)
        self.roll.assert_not_called()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE account_login_ownership SET status='active'")
            conn.execute('UPDATE player_positions SET lat=0,lng=0,version=2')
        self.assertEqual(self.store.scan(now=self.now)['created'], 0)
        with db_connect(self.path) as conn:
            conn.execute('UPDATE player_positions SET lat=?,lng=?,version=3',
                (self.point['lat'], self.point['lng']))
        self.assertEqual(self.store.scan(now=self.now)['created'], 2)

    def test_malformed_patrol_does_not_starve_next_patrol(self):
        other = {**self.capsule, 'capsule_id': 'zzz-healthy'}
        self.capsules.upsert(other, now=self.now)
        self.capsules.upsert({**self.capsule, 'detection_radius_m': 0}, now=self.now)
        self.assertEqual(self.store.scan(now=self.now, patrol_limit=1)['created'], 0)
        self.assertEqual(self.store.scan(now=self.now, patrol_limit=1)['created'], 2)

    def test_bystander_boundary_and_distinct_incident_have_separate_receipts(self):
        result = self.store.encounter(self.candidate('bob'), 'bob', now=self.now)
        self.assertEqual(result['encounter']['outcome'], 'selected')
        other = self.incidents.upsert({**self.incident, 'incident_id': 'incident-two'}, now=self.now)
        capsule = {**self.capsule, 'capsule_id': 'patrol-two', 'incident_id': other['incident_id']}
        self.capsules.upsert(capsule, now=self.now)
        candidate = {**self.candidate('bob', capsule), 'incident_id': other['incident_id'], 'occurrence': 999}
        self.store.encounter(candidate, 'observer', now=self.now)
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual({row['occurrence'] for row in self.rows()}, {1})
        self.assertEqual(self.roll.call_count, 2)
