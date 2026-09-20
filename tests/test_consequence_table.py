import tempfile
import unittest
from pathlib import Path
from database import db_connect
from response_network.consequence_table import plan_consequence, fine_amount
from response_network.criminal_record import CriminalRecordStore


class ConsequenceTableTest(unittest.TestCase):
    def test_levels_and_recidivism_share_one_counter(self):
        self.assertEqual([plan_consequence(2, n)['stage'] for n in range(10)],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 9])
        self.assertEqual([plan_consequence(level, 0)['stage'] for level in (2, 3, 4, 5)],
                         [1, 3, 5, 6])
        self.assertEqual(plan_consequence(3, 2)['stage'], 5)
        self.assertIsNone(plan_consequence(1, 100))
        for level, count in ((0, 0), (6, 0), (2, -1)):
            with self.assertRaises(ValueError):
                plan_consequence(level, count)

    def test_effects_and_online_only_detention(self):
        plans = [plan_consequence(2, n) for n in range(9)]
        self.assertEqual([p['fine_multiplier'] for p in plans], [1,2,0,0,3,0,0,0,0])
        self.assertEqual([p['tools'] for p in plans], [0,0,1,2,3,0,0,0,0])
        self.assertEqual([p['detention_minutes'] for p in plans], [0,0,0,0,0,5,10,15,20])
        self.assertTrue(plans[-1]['detention_rules']['pause_offline'])
        self.assertTrue(plans[-1]['detention_rules']['requires_online'])
        plans[-1]['detention_rules']['pause_offline'] = False
        self.assertTrue(plan_consequence(5, 0)['detention_rules']['pause_offline'])

    def test_fine_multipliers_keep_mvp_wallet_protections(self):
        self.assertEqual([fine_amount(10000, 60, n) for n in (1,2,3)], [30,60,90])
        self.assertEqual(fine_amount(100, 100, 3), 18)
        self.assertEqual(fine_amount(0, 100, 3), 0)
        self.assertEqual(fine_amount(100, 100, 0), 0)

    def test_record_counts_execution_once_and_rolls_back_with_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'record.db')
            store = CriminalRecordStore(path)
            with db_connect(path) as conn:
                conn.execute('''CREATE TABLE response_encounters(encounter_id TEXT PRIMARY KEY,
                    actor_id TEXT,incident_id TEXT,outcome TEXT,execution_status TEXT)''')
                conn.executemany('INSERT INTO response_encounters VALUES (?,?,?,?,?)', [
                    ('one','player','incident-a','selected','executed'),
                    ('two','player','incident-b','selected','executed'),
                    ('avoided','player','incident-c','avoided','not_enabled'),
                    ('pending','player','incident-d','selected','not_enabled')])
            with db_connect(path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                plan = store.prepare(conn, 'player', 2)
                for receipt in ('avoided', 'pending'):
                    with self.assertRaisesRegex(ValueError, 'encounter_not_executed'):
                        store.record_executed(conn, receipt, plan, {'fine_hc': 10}, 'now')
                with self.assertRaisesRegex(ValueError, 'no_executed_effect'):
                    store.record_executed(conn, 'one', plan, {}, 'now')
                self.assertTrue(store.record_executed(conn, 'one', plan, {'fine_hc':10}, 'now')['created'])
                self.assertFalse(store.record_executed(conn, 'one', plan, {'fine_hc':10}, 'now')['created'])
                with self.assertRaisesRegex(ValueError, 'stale_consequence_plan'):
                    store.record_executed(conn, 'two', plan, {'fine_hc':10}, 'now')
            with self.assertRaises(RuntimeError):
                with db_connect(path) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    plan = store.prepare(conn, 'player', 3)
                    self.assertEqual(plan['stage'], 4)
                    store.record_executed(conn, 'two', plan, {'tool_ids':['tool-a']}, 'now')
                    raise RuntimeError('crash before commit')
            restored = CriminalRecordStore(path)
            with db_connect(path) as conn:
                self.assertEqual(restored.prepare(conn, 'player', 3)['stage'], 4)
                self.assertEqual(conn.execute('SELECT count(*) FROM response_penalty_history').fetchone()[0], 1)
