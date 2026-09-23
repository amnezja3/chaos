import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import db_connect
from response_network.consequence_table import plan_consequence
from response_network.sanctions import SanctionStore
from session_generation_store import username_digest


class SanctionsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'sanctions.db')
        self.store = SanctionStore(self.path)
        self.start = datetime(2026, 9, 22, tzinfo=timezone.utc)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.row, _ = self.store.impose(conn, encounter_id='e1', actor_id='main',
                incident_id='i1', plan=plan_consequence(5, 0), now=self.start)
        self.sid = self.row['sanction_id']

    def tick(self, seconds, online=True, revision='session1'):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            return self.store.sample(conn, self.sid, now=self.start + timedelta(seconds=seconds),
                                     online=online, session_revision=revision)

    def test_clock_duplicates_outage_reconnect_and_restart(self):
        self.tick(1)
        self.assertEqual(self.tick(61)['remaining_ms'], 240000)
        self.assertEqual(self.tick(61)['remaining_ms'], 240000)
        self.assertEqual(self.tick(40)['remaining_ms'], 240000)
        self.tick(62, online=False)
        self.assertEqual(self.tick(10000, revision='session2')['remaining_ms'], 240000)
        self.store = SanctionStore(self.path)
        self.assertEqual(self.tick(10060, revision='session2')['remaining_ms'], 180000)
        self.assertEqual(self.tick(10100, revision='session3')['remaining_ms'], 180000)
        self.assertEqual(self.tick(20000, revision='session3')['remaining_ms'], 180000)

    def test_served_waits_for_atomic_release_and_blocks_second_sentence(self):
        self.tick(1)
        for seconds in (61, 121, 181, 241, 301):
            row = self.tick(seconds)
        self.assertEqual(row['remaining_ms'], 0)
        self.assertEqual(row['status'], 'release_pending')
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'already_detained'):
                self.store.impose(conn, encounter_id='e2', actor_id='main', incident_id='i2',
                    plan=plan_consequence(5, 0), now=self.start)
            with self.assertRaisesRegex(ValueError, 'already_served'):
                self.store.release(conn, self.sid, reason='bail', now=self.start + timedelta(seconds=302))
            _, created = self.store.release(conn, self.sid, reason='served',
                                            now=self.start + timedelta(seconds=302))
            self.assertTrue(created)
            self.assertFalse(self.store.release(conn, self.sid, reason='served',
                now=self.start + timedelta(seconds=303))[1])
            self.assertIsNone(self.store.active_for(conn, 'main'))

    def test_message_shared_limit_retry_restart_and_rollback(self):
        with self.assertRaises(RuntimeError):
            with db_connect(self.path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                self.store.consume_private_message(conn, self.sid, message_id='failed', now=self.start)
                raise RuntimeError('delivery failed')
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.assertTrue(self.store.consume_private_message(conn, self.sid,
                message_id='clan-message', now=self.start))
        self.store = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.assertFalse(self.store.consume_private_message(conn, self.sid,
                message_id='clan-message', now=self.start))
            with self.assertRaisesRegex(ValueError, 'allowance_exhausted'):
                self.store.consume_private_message(conn, self.sid, message_id='direct-message', now=self.start)

    def test_impose_idempotent_and_whole_transaction_rolls_back(self):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row, created = self.store.impose(conn, encounter_id='e1', actor_id='main',
                incident_id='i1', plan=plan_consequence(5, 0), now=self.start)
            self.assertFalse(created)
            self.assertEqual(row, self.row)
        with self.assertRaises(RuntimeError):
            with db_connect(self.path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                self.store.release(conn, self.sid, reason='bail', now=self.start)
                raise RuntimeError('transport failed')
        with db_connect(self.path) as conn:
            self.assertEqual(self.store.active_for(conn, 'main')['status'], 'active')
            self.assertEqual(conn.execute('SELECT count(*) FROM response_sanction_events').fetchone()[0], 1)
            with self.assertRaisesRegex(ValueError, 'transaction_required'):
                self.store.release(conn, self.sid, reason='bail', now=self.start)

    def test_naive_time_and_early_release_rejected(self):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'sentence_not_served'):
                self.store.release(conn, self.sid, reason='served', now=self.start)
            with self.assertRaisesRegex(ValueError, 'aware_server_time'):
                self.store.sample(conn, self.sid, now=datetime(2026, 9, 22), online=True,
                                  session_revision='s1')

    def test_canonical_heartbeat_is_not_recredited_by_worker_polling(self):
        with db_connect(self.path) as conn:
            conn.execute('CREATE TABLE account_login_ownership (username_hash TEXT PRIMARY KEY, status TEXT, updated_at TEXT, active_revision TEXT)')
            conn.execute('CREATE TABLE mail_presence (username TEXT PRIMARY KEY, last_seen_at TEXT)')
            conn.execute('INSERT INTO account_login_ownership VALUES (?,?,?,?)',
                (username_digest('main'), 'active', self.start.isoformat(), 's1'))
            conn.execute('INSERT INTO mail_presence VALUES (?,?)',
                ('main', (self.start + timedelta(seconds=1)).isoformat()))
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            def observe(seconds):
                return self.store.observe_presence(conn, self.sid,
                    now=self.start + timedelta(seconds=seconds))
            self.assertEqual(observe(1)['remaining_ms'], 300000)
            self.assertEqual(observe(50)['remaining_ms'], 300000)
            conn.execute('UPDATE mail_presence SET last_seen_at=?',
                ((self.start + timedelta(seconds=61)).isoformat(),))
            self.assertEqual(observe(65)['remaining_ms'], 240000)
            self.assertEqual(observe(100)['remaining_ms'], 240000)
            conn.execute("UPDATE account_login_ownership SET status='logged_out'")
            self.assertEqual(observe(110)['remaining_ms'], 240000)
            self.assertIsNone(observe(111)['session_revision'])

    def test_parallel_ticks_and_sends_have_one_effect(self):
        self.tick(1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.tick, [61, 61]))
        self.assertEqual([r['remaining_ms'] for r in results], [240000, 240000])

        def send(message):
            try:
                with db_connect(self.path) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    return self.store.consume_private_message(conn, self.sid,
                        message_id=message, now=self.start + timedelta(seconds=62))
            except ValueError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(send, ['direct', 'clan']))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count('private_message_allowance_exhausted'), 1)
