"""Exercise the actual account deletion and operator redaction on an isolated DB."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest

from database import atomic_runtime_transaction, db_connect
from identity_gateway import service
from tools.privacy_redact import redact, digest, inventory
import test_identity_gateway_web as gateway


class ManualErasureTests(unittest.TestCase):
    setUp = gateway.GatewayWebTests.setUp
    authenticate = gateway.GatewayWebTests.authenticate
    post = gateway.GatewayWebTests.post
    grant = gateway.GatewayWebTests.grant

    def seed_case(self):
        self.authenticate()
        self.peer_before = self.users.get_profile('bob')
        with atomic_runtime_transaction(self.path, foreign_keys=True) as conn:
            user_id = service.account(conn, 'alice')[0]
            service.link(conn, user_id, dict(provider='google',subject='case-subject',email='alice@example.test'))
            message = conn.execute("""INSERT INTO chat_messages
                (owner_username,scope,peer_name,sender,body,created_at)
                VALUES ('bob','private','alice','alice','Contact alice@example.test','2026-10-18')""").lastrowid
            event = conn.execute("""INSERT INTO area_events
                (owner_username,actor_username,event_type,payload_json,created_at)
                VALUES ('bob','alice','test','{"note":"alice@example.test"}','2026-10-18')""").lastrowid
        self.case = {'case_id':'TEST-ERASURE-1','username':'alice',
                     'reason':'Verified request; remove email from reviewed copies, retain world actor references',
                     'redactions':[
            {'table':'chat_messages','id':message,'column':'body',
             'expected_sha256':digest('Contact alice@example.test'),'replacement':'[personal data removed]'},
            {'table':'area_events','id':event,'column':'payload_json',
             'expected_sha256':digest('{"note":"alice@example.test"}'),'replacement':'{"note":"[removed]"}'},
        ]}
        return user_id

    def delete(self):
        result = self.post('/api/account/delete', {'username':'alice','confirm':'alice','grant':self.grant('delete')})
        self.assertEqual(result.status_code,200,result.json)

    def test_manual_case_and_restore_replay_preserve_world_and_peer(self):
        uid = self.seed_case()
        backup = str(Path(self.tmp.name)/'before-erasure.sqlite3')
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
        with self.assertRaisesRegex(ValueError,'delete_account_through_identity_first'):
            redact(self.path,self.case,apply=True)
        self.delete()
        self.assertTrue(inventory(self.path,['alice@example.test']))
        with db_connect(self.path) as conn:
            for table in ('user_identities','identity_account_security','identity_consents','identity_mail_challenges'):
                self.assertEqual(conn.execute(f'SELECT count(*) FROM {table} WHERE user_id=?',(uid,)).fetchone()[0],0)
            self.assertIsNotNone(conn.execute('SELECT 1 FROM identity_retired_subjects').fetchone())
            self.assertEqual(conn.execute('SELECT actor_username FROM area_events').fetchone()[0],'alice')
        self.assertEqual(redact(self.path,self.case)['changed_fields'],2)
        with db_connect(self.path) as conn:
            self.assertIn('alice@example.test',conn.execute('SELECT body FROM chat_messages').fetchone()[0])
        bad = copy.deepcopy(self.case)
        bad['redactions'][1]['expected_sha256']='outdated'
        with self.assertRaisesRegex(ValueError,'content_changed'):
            redact(self.path,bad,apply=True)
        with db_connect(self.path) as conn:
            self.assertIn('alice@example.test',conn.execute('SELECT body FROM chat_messages').fetchone()[0])
        self.assertEqual(redact(self.path,self.case,apply=True)['changed_fields'],2)
        self.assertEqual(redact(self.path,self.case,apply=True)['already_redacted'],2)
        self.assertEqual(inventory(self.path,['alice@example.test']),[])
        self.assertEqual(self.users.get_profile('bob'),self.peer_before)
        self.assertFalse(self.users.has_user('alice'))
        # Backups are retained, not silently rewritten. A restored copy is kept
        # offline until deletion and the same reviewed content plan are replayed.
        restored = str(Path(self.tmp.name)/'restore.sqlite3')
        with closing(sqlite3.connect(backup)) as source, closing(sqlite3.connect(restored)) as target:
            self.assertIsNotNone(source.execute("SELECT 1 FROM users WHERE username='alice'").fetchone())
            source.backup(target)
        from database import UserStore
        store = UserStore(restored,seed_path=str(Path(self.tmp.name)/'no-seed'))
        self.assertTrue(store.delete_user('alice',preserve_peer_history=True))
        redact(restored,self.case,apply=True)
        with db_connect(restored) as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM users WHERE username='alice'").fetchone())
            self.assertEqual(conn.execute('SELECT body FROM chat_messages').fetchone()[0],'[personal data removed]')
            self.assertEqual(conn.execute('SELECT actor_username FROM area_events').fetchone()[0],'alice')
            self.assertIsNone(conn.execute('PRAGMA foreign_key_check').fetchone())
        # Existing session must not regain account access after deletion.
        self.assertNotEqual(self.client.get('/account/identity').status_code,200)

    def test_operator_cannot_change_structural_gameplay_fields(self):
        self.seed_case()
        self.delete()
        self.case['redactions'][0]['column']='sender'
        with self.assertRaisesRegex(ValueError,'unsupported_content_field'):
            redact(self.path,self.case,apply=True)


if __name__=='__main__':
    unittest.main()
