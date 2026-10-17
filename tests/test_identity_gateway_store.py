from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest

from identity_gateway.store import initialize, issue_intent, consume_intent, cleanup
from tools.identity_157_migrate import migrate,backup,check


class IdentityStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,password TEXT,profile_json TEXT)')
        self.conn.executemany('INSERT INTO users VALUES (?,?,?)', [(1,'legacy','{}'), (2,'','{}')])
        initialize(self.conn)
        self.conn.commit()

    def issue(self, **extra):
        self.conn.execute('BEGIN IMMEDIATE')
        token = issue_intent(self.conn, purpose='link', provider='google', client='browser',
                             ttl=300, user_id=1, generation='gen', now=100, **extra)
        self.conn.commit()
        return token

    def consume(self, token, **overrides):
        args = dict(purpose='link', provider='google', client='browser', user_id=1, generation='gen', now=101)
        args.update(overrides)
        consume_intent(self.conn, token, **args)

    def test_legacy_not_verified_and_absent_password_disabled(self):
        self.assertEqual(self.conn.execute('SELECT * FROM identity_account_security ORDER BY user_id').fetchall(),
                         [(1,1,None,None), (2,0,None,None)])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM identity_consents').fetchone()[0], 0)

    def test_bound_expiring_one_time_intent(self):
        token = self.issue()
        self.assertNotIn(token, str(self.conn.execute('SELECT * FROM identity_intents').fetchall()))
        for bad in ({'client':'other'}, {'generation':'old'}, {'user_id':2},
                    {'purpose':'login'}, {'provider':'github'}, {'now':400}, {'now':99}):
            self.conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError):
                self.consume(token, **bad)
            self.conn.rollback()
        self.conn.execute('BEGIN IMMEDIATE')
        self.consume(token)
        self.conn.commit()
        self.conn.execute('BEGIN IMMEDIATE')
        with self.assertRaises(ValueError):
            self.consume(token)
        self.conn.rollback()

    def test_failed_identity_write_rolls_back_consumption(self):
        token = self.issue()
        self.conn.execute('BEGIN IMMEDIATE')
        self.consume(token)
        self.conn.execute("INSERT INTO users VALUES (3,'','{\"nick\":\"new\"}')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO user_identities(user_id,provider,provider_user_id,linked_at) VALUES (999,'google','sub',1)")
        self.conn.rollback()
        self.assertIsNone(self.conn.execute('SELECT id FROM users WHERE id=3').fetchone())
        self.conn.execute('BEGIN IMMEDIATE')
        self.consume(token)
        self.conn.commit()

    def test_two_connections_cannot_consume_same_intent(self):
        token = self.issue()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'race.sqlite3'
            with closing(sqlite3.connect(path)) as disk:
                self.conn.backup(disk)
            barrier = threading.Barrier(2)
            def attempt():
                with closing(sqlite3.connect(path,timeout=5)) as conn:
                    conn.execute('PRAGMA foreign_keys=ON')
                    barrier.wait(timeout=5)
                    conn.execute('BEGIN IMMEDIATE')
                    try:
                        consume_intent(conn,token,purpose='link',provider='google',client='browser',
                                       user_id=1,generation='gen',now=101)
                        conn.commit()
                        return True
                    except ValueError:
                        conn.rollback()
                        return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: attempt(),range(2)))
            self.assertEqual(sorted(results),[False,True])

    def test_identity_unique_for_provider_subject_and_user(self):
        sql = 'INSERT INTO user_identities(user_id,provider,provider_user_id,linked_at) VALUES (?,?,?,1)'
        self.conn.execute(sql,(1,'google','subject'))
        for values in ((2,'google','subject'), (1,'google','another'), (1,'unknown','x')):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql,values)

    def test_cleanup_and_transaction_requirement(self):
        token = self.issue()
        with self.assertRaises(ValueError):
            self.consume(token)
        self.conn.execute('BEGIN IMMEDIATE')
        self.assertEqual(cleanup(self.conn,now=400),1)
        self.conn.commit()

    def test_migration_dry_run_repeat_and_original_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.sqlite3'
            with closing(sqlite3.connect(path)) as disk:
                self.conn.backup(disk)
                # Test a legacy schema, before any identity tables.
                for table in ('user_identities','identity_account_security','identity_consents','identity_intents'):
                    disk.execute('DROP TABLE '+table)
                disk.commit()
            before = hashlib.sha256(path.read_bytes()).digest()
            self.assertEqual(migrate(path)['status'],'dry_run')
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),before)
            self.assertEqual(migrate(path,True)['status'],'migrated')
            self.assertEqual(migrate(path,True)['status'],'already_migrated')
            with closing(sqlite3.connect(path)) as disk:
                self.assertEqual(disk.execute('SELECT * FROM users ORDER BY id').fetchall(),
                                 [(1,'legacy','{}'),(2,'','{}')])

    def test_backup_check_and_baseline_detects_changed_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'game.sqlite3'
            with closing(sqlite3.connect(path)) as disk:self.conn.backup(disk)
            target=Path(directory)/'backup.sqlite3'
            result=backup(path,target)
            self.assertTrue(check(path,result['baseline'])['baseline_matches'])
            with self.assertRaises(FileExistsError):backup(path,target)
            with closing(sqlite3.connect(path)) as disk:
                disk.execute("UPDATE users SET profile_json='changed' WHERE id=1")
                disk.commit()
            with self.assertRaises(ValueError):check(path,result['baseline'])
