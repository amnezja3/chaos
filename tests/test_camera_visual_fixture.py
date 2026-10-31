"""164.0 persistent lifecycle acceptance, isolated DB and controllable clock."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from database import db_connect, UserStore
from tools.camera_visual_fixture_store import FixtureStore


class CameraActivationFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fixture.sqlite3'
        self.time=1000000.
        self.store=FixtureStore(self.path,clock=lambda:self.time)
        self.user='cvn-alice'

    def success(self):
        return self.store.result(self.user,True)

    def finish(self):
        self.success();self.time+=1805;self.store.tick(self.user)

    def test_success_exact_order_and_commit_gate(self):
        r=self.success()
        self.assertEqual(self.store.snapshot(self.user)['operations'],[])
        with self.assertRaises(PermissionError):self.store.claim(self.user,'document')
        self.time+=4.999
        self.assertEqual(self.store.snapshot(self.user)['operations'],[])
        self.time+=.001
        snap=self.store.snapshot(self.user)
        self.assertEqual(len(snap['operations']),1)
        self.assertEqual(snap['receipt']['progress'],0)
        self.time+=900
        self.assertEqual(self.store.snapshot(self.user)['receipt']['progress'],50)
        self.time+=899.999
        self.assertFalse(self.store.snapshot(self.user)['receipt']['file_verified'])
        self.time+=.001
        snap=self.store.snapshot(self.user)
        self.assertEqual(snap['receipt']['progress'],100)
        self.assertTrue(snap['receipt']['file_verified'])
        self.assertEqual(len(snap['files']),1)
        self.assertEqual(self.store.claim(self.user,'document')['instance_id'],r['instance_id'])

    def test_failure_never_downloads_and_cannot_be_upgraded_by_retry(self):
        self.store.result(self.user,False)
        self.store.result(self.user,True)
        self.time+=5000
        snap=self.store.snapshot(self.user)
        self.assertEqual(snap['receipt']['state'],'FAILED')
        self.assertEqual(snap['operations'],[])
        self.assertEqual(snap['files'],[])
        with self.assertRaises(PermissionError):self.store.claim(self.user,'document',explicit=True)

    def test_restart_login_and_offline_completion(self):
        first=self.success()
        self.store.login(self.user)
        self.time+=100
        old=self.store.snapshot(self.user)
        self.store=FixtureStore(self.path,clock=lambda:self.time)
        self.assertEqual(old['receipt']['start_at'],self.store.snapshot(self.user)['receipt']['start_at'])
        token=self.store.login(self.user);self.store.logout(token)
        self.time+=1800
        self.store=FixtureStore(self.path,clock=lambda:self.time)
        self.store.login(self.user)
        new=self.store.snapshot(self.user)
        self.assertTrue(new['receipt']['file_verified'])
        self.assertEqual(new['receipt']['instance_id'],first['instance_id'])

    def test_parallel_receipts_ticks_and_claims_are_unique(self):
        with ThreadPoolExecutor(4) as pool:
            receipts=list(pool.map(lambda _:self.success(),range(8)))
        self.assertEqual(len({r['id'] for r in receipts}),1)
        self.time+=1805
        with ThreadPoolExecutor(4) as pool:list(pool.map(lambda _:self.store.tick(self.user),range(8)))
        with ThreadPoolExecutor(4) as pool:
            claims=list(pool.map(lambda i:self.store.claim(self.user,str(i)),range(8)))
        self.assertEqual(sum(bool(c) for c in claims),1)
        snap=self.store.snapshot(self.user)
        self.assertEqual(len(snap['operations']),1)
        self.assertEqual(len(snap['files']),1)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT used FROM player_storage WHERE username=?',(self.user,)).fetchone()[0],1)

    def test_disk_full_does_not_publish_or_launch(self):
        self.success()
        with db_connect(self.path) as conn:conn.execute('UPDATE player_storage SET capacity=0 WHERE username=?',(self.user,))
        self.time+=1805
        snap=self.store.snapshot(self.user)
        self.assertEqual(snap['receipt']['state'],'WRITE_FAILED')
        self.assertFalse(snap['receipt']['file_verified'])
        self.assertEqual(snap['files'],[])
        with self.assertRaises(PermissionError):self.store.claim(self.user,'doc')

    def test_transaction_error_rolls_back_file_and_ready_then_recovers(self):
        self.success();self.time+=1805
        with db_connect(self.path) as conn:
            conn.execute("CREATE TRIGGER fail_activation BEFORE UPDATE ON cvn_fixture_accounts WHEN NEW.receipt LIKE '%READY%' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(Exception):self.store.tick(self.user)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_data_files').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT used FROM player_storage WHERE username=?',(self.user,)).fetchone()[0],0)
            conn.execute('DROP TRIGGER fail_activation')
        self.assertTrue(self.store.snapshot(self.user)['receipt']['file_verified'])

    def test_close_lease_and_corrupt_file(self):
        self.finish()
        a=self.store.claim(self.user,'a')
        self.assertIsNone(self.store.claim(self.user,'b'))
        self.time+=9
        self.assertEqual(self.store.claim(self.user,'b')['instance_id'],a['instance_id'])
        self.store.release(self.user,'a',closed=True) # old document cannot close new owner
        self.assertIsNone(self.store.claim(self.user,'c'))
        self.store.release(self.user,'b',closed=True)
        self.assertIsNone(self.store.claim(self.user,'b'))
        self.assertIsNotNone(self.store.claim(self.user,'b',explicit=True))
        with db_connect(self.path) as conn:conn.execute("UPDATE player_data_files SET file_json='{}'")
        self.assertFalse(self.store.snapshot(self.user)['receipt']['file_verified'])
        with self.assertRaises(PermissionError):self.store.claim(self.user,'b')

    def test_accounts_and_sessions_are_isolated(self):
        token=self.store.login(self.user)
        newer=self.store.login(self.user)
        with self.assertRaises(PermissionError):self.store.user(token)
        self.assertEqual(self.store.user(newer),self.user)
        self.finish()
        self.assertEqual(self.store.snapshot('cvn-bob')['receipt'],{})
        with self.assertRaises(PermissionError):self.store.claim('cvn-bob','b')

    def test_no_profile_dependency_even_with_35mb_profile(self):
        with db_connect(self.path) as conn:
            conn.execute('INSERT INTO users(username,profile_json,created_at,updated_at) VALUES(?,?,?,?)',
                         (self.user,'{"padding":"'+'x'*(35*1024*1024)+'"}','fixture','fixture'))
        with (patch.object(UserStore,'get_profile',side_effect=AssertionError('heavy read')),
              patch.object(UserStore,'get_profile_with_revision',side_effect=AssertionError('heavy read'))):
            self.finish()
            self.assertTrue(self.store.snapshot(self.user)['receipt']['file_verified'])

    def test_refuses_unmarked_database(self):
        other=Path(self.temp.name)/'game.sqlite3'
        import sqlite3
        conn=sqlite3.connect(other)
        conn.execute('CREATE TABLE example(id)')
        conn.commit();conn.close()
        with self.assertRaises(ValueError):FixtureStore(other)


if __name__=='__main__':unittest.main()
