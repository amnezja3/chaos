import sqlite3
import unittest
import communication_safety as safety


class SafetyStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE)')
        self.conn.execute('CREATE TABLE contacts(owner_username TEXT,contact_name TEXT,status TEXT,created_at TEXT,UNIQUE(owner_username,contact_name))')
        self.conn.executemany('INSERT INTO users VALUES (?,?)',[(1,'alice'),(2,'bob'),(3,'admin')])
        safety.initialize(self.conn)

    def connect_players(self):
        safety.invite(self.conn,'alice','bob')
        safety.answer_invite(self.conn,2,'alice',True)

    def test_contact_requires_explicit_acceptance_and_block_removes_permission(self):
        route={'channel':'direct','peer':'bob'}
        with self.assertRaisesRegex(ValueError,'contact_unavailable'):
            safety.require_send(self.conn,'alice',route)
        safety.invite(self.conn,'alice','bob')
        with self.assertRaisesRegex(ValueError,'contact_unavailable'):
            safety.require_send(self.conn,'alice',route)
        safety.answer_invite(self.conn,2,'alice',True)
        safety.require_send(self.conn,'alice',route)
        safety.set_block(self.conn,2,'alice',True)
        with self.assertRaisesRegex(ValueError,'contact_unavailable'):
            safety.require_send(self.conn,'alice',route)
        safety.set_block(self.conn,2,'alice',False)
        self.assertFalse(safety.friends(self.conn,'alice','bob'))

    def test_invitation_decline_and_limits(self):
        safety.invite(self.conn,'alice','bob')
        self.assertEqual(safety.invite(self.conn,'alice','bob'),'already_pending')
        safety.answer_invite(self.conn,2,'alice',False)
        with self.assertRaisesRegex(ValueError,'safety_rate_limited'):
            safety.invite(self.conn,'alice','bob')

    def test_hidden_content_and_system_events(self):
        safety.set_block(self.conn,2,'alice',True)
        route={'channel':'world'}
        rows=[dict(sender='alice',body='hello',message_id='w1'),dict(sender='alice',source='domain_event',body='battle',message_id='w2')]
        result=safety.visible_messages(self.conn,'bob',route,rows)
        self.assertEqual([r['message_id'] for r in result],['w2'])
        self.assertEqual(len(safety.visible_messages(self.conn,'bob',{'channel':'direct'},rows)),2)

    def test_report_dedup_moderation_restore_and_sanction(self):
        report=safety.report(self.conn,2,'message','w1','harassment','context',{'body':'text'},1)
        self.assertEqual(report,safety.report(self.conn,2,'message','w1','harassment','duplicate',{},1))
        safety.decide(self.conn,3,report,'hide','Confirmed report')
        self.assertFalse(safety.visible_messages(self.conn,'bob',{'channel':'world'},[dict(message_id='w1',sender='alice')]))
        safety.decide(self.conn,3,report,'restrict','Repeated harassment',1)
        with self.assertRaisesRegex(ValueError,'communication_restricted'):
            safety.require_sender(self.conn,1)
        safety.decide(self.conn,3,report,'release','Appeal accepted')
        safety.require_sender(self.conn,1)
        safety.decide(self.conn,3,report,'restore','Restore after appeal')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM safety_actions').fetchone()[0],4)

    def test_initialization_idempotent_and_fk_integrity(self):
        self.connect_players()
        safety.initialize(self.conn)
        self.assertTrue(safety.friends(self.conn,'alice','bob'))
        self.assertEqual(self.conn.execute('PRAGMA foreign_key_check').fetchall(),[])
