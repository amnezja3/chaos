import unittest
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from database import db_connect
from tests import test_canonical_consequences as fixture
from response_network.criminal_record import CriminalRecordStore, DECAY_MS, reduction_message


class ReductionMessageTest(unittest.TestCase):
    def test_institution_tracks_remaining_burden_and_zero_ends_supervision(self):
        for level, authority in [(14, 'Prokuratura cyberbezpieczeństwa'),
                                 (10, 'Prokuratura cyberbezpieczeństwa'),
                                 (9, 'Centrum cyberbezpieczeństwa'),
                                 (5, 'Centrum cyberbezpieczeństwa'),
                                 (4, 'Policja'), (1, 'Policja')]:
            message = reduction_message(level)
            self.assertEqual(message['title'], authority)
            self.assertIn(f'poziomu {level}', message['text'])
        self.assertIn('dozór zakończony', reduction_message(0)['text'])


class CriminalRecordDecayTest(unittest.TestCase):
    seed_actor = fixture.CanonicalConsequencesTest.seed_actor
    candidate = fixture.CanonicalConsequencesTest.candidate
    rows = fixture.CanonicalConsequencesTest.rows

    def setUp(self):
        fixture.CanonicalConsequencesTest.setUp(self)
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO response_criminal_records VALUES ('alice',3,?)", (self.now.isoformat(),))
            conn.execute('UPDATE account_login_ownership SET active_revision=1')

    def pulse(self, seconds=60):
        self.now += timedelta(seconds=seconds)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE mail_presence SET last_seen_at=? WHERE username='alice'", (self.now.isoformat(),))
        return self.records.observe('alice', now=self.now, messages=self.messages)

    def test_hour_reduces_burden_preserves_history_and_entry_floor(self):
        self.records.observe('alice', now=self.now)
        for _ in range(59):
            result = self.pulse()
        self.assertEqual(result['active_burden'], 3)
        result = self.pulse()
        self.assertEqual(result['active_burden'], 2)
        self.assertEqual(result['executed_count'], 3)
        with db_connect(self.path) as conn:
            self.assertEqual(self.records.prepare(conn, 'alice', 2)['stage'], 3)
            self.assertIsNone(self.records.prepare(conn, 'alice', 1))
        self.assertEqual(CriminalRecordStore(self.path).observe('alice', now=self.now)['remaining_seconds'], 3600)

    def test_offline_session_change_and_duplicate_do_not_credit(self):
        self.records.observe('alice', now=self.now)
        self.assertEqual(self.pulse()['remaining_seconds'], 3540)
        self.assertEqual(self.pulse(7200)['remaining_seconds'], 3540)
        with db_connect(self.path) as conn:
            conn.execute('UPDATE account_login_ownership SET active_revision=2')
        self.assertEqual(self.pulse()['remaining_seconds'], 3540)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.records.observe('alice', now=self.now), range(2)))
        self.assertTrue(all(r['remaining_seconds'] == 3540 for r in results))

    def test_executed_penalty_resets_progress_and_ordinal_is_historical(self):
        self.records.observe('alice', now=self.now)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_record_decay SET forgiven=2,progress_ms=? WHERE actor_id='alice'", (DECAY_MS-1,))
        result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['execution']['status'], 'executed', result)
        with db_connect(self.path) as conn:
            state = self.records.state(conn, 'alice')
            self.assertEqual(state, {'executed_count': 4, 'active_burden': 2, 'remaining_seconds': 3600})
            self.assertEqual(conn.execute('SELECT ordinal FROM response_penalty_history').fetchone()[0], 4)

    def test_detention_pauses_and_bail_does_not_clear_burden(self):
        self.records.observe('alice', now=self.now)
        self.pulse()
        with db_connect(self.path) as conn:
            conn.execute('''INSERT INTO response_sanctions(sanction_id,encounter_id,actor_id,incident_id,
                plan_json,duration_ms,remaining_ms,status,created_ms,updated_ms)
                VALUES ('s','e','alice','i','{}',60000,60000,'active',0,0)''')
        self.assertTrue(self.pulse()['paused'])
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_sanctions SET status='released',released_ms=?,release_reason='bail'", (int(self.now.timestamp()*1000),))
        result = self.pulse()
        self.assertEqual(result['remaining_seconds'], 3540)
        self.assertEqual(result['active_burden'], 3)
