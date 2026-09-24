import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from contextlib import contextmanager
from datetime import timedelta
import time
import sqlite3

from database import (db_connect, dumps_json, PlayerInventoryStore, PlayerOperationStore,
    WalletBalanceStore, SystemMessageStore, GameStateDeltaBus,
    reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics)
from response_network.canonical_executor import CanonicalConsequenceExecutor
from response_network.criminal_record import CriminalRecordStore
import test_response_encounters as encounters_fixture
from ghostnetwork.repository import GhostNetworkRepository


class CanonicalConsequencesTest(unittest.TestCase):
    seed_actor = encounters_fixture.ResponseEncountersTest.seed_actor
    candidate = encounters_fixture.ResponseEncountersTest.candidate
    rows = encounters_fixture.ResponseEncountersTest.rows

    def setUp(self):
        encounters_fixture.ResponseEncountersTest.setUp(self)
        GhostNetworkRepository(db_path=self.path)
        self.records = CriminalRecordStore(self.path)
        self.inventory, self.ops = PlayerInventoryStore(self.path), PlayerOperationStore(self.path)
        self.wallet, self.messages = WalletBalanceStore(self.path), SystemMessageStore(self.path)
        self.deltas = GameStateDeltaBus(self.path)
        self.executor = CanonicalConsequenceExecutor(self.path, self.incidents, self.capsules,
            self.records, self.wallet, self.inventory, self.ops, self.messages, self.deltas)
        self.store.executor = self.executor
        env = patch.dict('os.environ', {'CHAOS_RESPONSE_EXECUTION_MODE':'enforce', 'CHAOS_RESPONSE_EXECUTION_ACTORS':'*'})
        env.start(); self.addCleanup(env.stop)
        self.incident = self.incidents.upsert({**self.incident, 'heat':60, 'level':2}, now=self.now)
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO users(username,profile_json,created_at,updated_at) VALUES ('admin','{}','now','now')")
            conn.execute("INSERT INTO wallet_balances(username,balance,version,updated_at) VALUES ('admin',0,1,'now')")
            for actor in ('alice','bob'):
                conn.execute("INSERT INTO users(username,profile_json,created_at,updated_at) VALUES (?,'{}','now','now')", (actor,))
                conn.execute("INSERT INTO wallet_balances(username,balance,version,updated_at) VALUES (?,10000,1,'now')", (actor,))
                conn.execute("INSERT INTO player_storage(username,capacity,used,updated_at) VALUES (?,512,40,'now')", (actor,))
            for i in range(4):
                app = {'id':f'tool-{i}','name':f'Tool {i}', 'operation_types':['port_scan'], 'disk_usage':8}
                conn.execute("INSERT INTO player_apps(username,app_id,app_json,updated_at) VALUES ('alice',?,?,'now')",
                    (app['id'], dumps_json(app)))
                conn.execute("INSERT INTO player_tool_files(username,tool_id,app_id,tool_json,updated_at) VALUES ('alice',?,?,?,'now')",
                    (f'file-{i}',app['id'],dumps_json({'name':f'Tool {i}.sh','file_size':2})))
        self.ops.upsert_operations('alice', [{'operation_id':'related', 'target_id':'map:one',
            'source_app_id':'tool-1', 'operation_type':'port_scan', 'status':'running'},
            {'operation_id':'unrelated','target_id':'map:other','operation_type':'port_scan','status':'running'}])
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO response_incident_members VALUES ('related',?)", (self.incident['incident_id'],))
        self.incident['operation_ids'] = ['related']

    def scalar(self, sql, params=()):
        with db_connect(self.path) as conn:
            return conn.execute(sql, params).fetchone()[0]

    def encounter(self, actor='alice'):
        return self.store.encounter(self.candidate(actor), 'observer', now=self.now)

    def test_fine_history_judgment_and_live_outbox_once_under_concurrency(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: self.encounter(), range(3)))
        self.assertTrue(all(r['execution']['status']=='executed' for r in results))
        self.assertEqual(self.roll.call_count, 1)
        self.assertEqual(self.scalar("SELECT balance FROM wallet_balances WHERE username='alice'"), 9970)
        self.assertEqual(self.scalar('SELECT count(*) FROM wallet_balance_events'), 2)
        self.assertEqual(self.wallet.get_balance('admin'), 30)
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 1)
        self.assertEqual(self.scalar('SELECT executed_count FROM response_criminal_records'), 1)
        self.assertEqual(self.scalar('SELECT points FROM response_judgment'), 2)
        self.assertEqual(self.scalar("SELECT status FROM player_operations WHERE operation_id='related'"), 'cancelled')
        self.assertEqual(self.scalar("SELECT status FROM player_operations WHERE operation_id='unrelated'"), 'running')
        self.assertEqual(self.scalar('SELECT count(*) FROM system_messages'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM game_state_deltas'), 6)
        with db_connect(self.path) as conn:
            events = [dict(row) for row in conn.execute(
                "SELECT type,payload_json FROM game_state_deltas WHERE username='alice' ORDER BY version")]
        self.assertEqual([event['type'] for event in events[:2]], ['incident.updated', 'npc.updated'])
        self.assertEqual(events[-1]['type'], 'response.consequence_executed')
        self.assertNotIn('suspect_refs', events[0]['payload_json'])

    def test_multitool_confiscation_keeps_last_tool_and_storage_consistent(self):
        self.incidents.upsert({**self.incident, 'level':4}, now=self.now)
        result = self.encounter()['execution']
        self.assertEqual(result['effects']['fine_hc'], 90)
        self.assertEqual(result['effects']['tool_ids'], ['tool-1','tool-0','tool-2'])
        self.assertEqual(self.scalar("SELECT count(*) FROM player_apps WHERE status='installed'"), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM player_tool_files'), 1)
        self.assertEqual(self.scalar("SELECT used FROM player_storage WHERE username='alice'"), 10)
        self.assertEqual(self.scalar("SELECT count(*) FROM game_state_deltas WHERE scope='apps'"), 1)

    def test_crash_rolls_back_all_effects_but_keeps_draw_for_fresh_retry(self):
        self.incidents.upsert({**self.incident, 'level':4}, now=self.now)
        with patch.object(self.messages, 'add_message', side_effect=RuntimeError('crash')):
            result = self.encounter()
        self.assertEqual(result['execution']['status'], 'deferred')
        self.assertEqual(self.rows()[0]['execution_status'], 'pending')
        self.assertEqual(self.scalar("SELECT balance FROM wallet_balances WHERE username='alice'"), 10000)
        self.assertEqual(self.scalar("SELECT count(*) FROM player_apps WHERE status='installed'"), 4)
        for table in ('response_penalty_history','response_criminal_records','response_judgment','game_state_deltas','wallet_balance_events'):
            self.assertEqual(self.scalar(f'SELECT count(*) FROM {table}'), 0, table)
        self.assertEqual(self.encounter()['execution']['status'], 'executed')
        self.assertEqual(self.roll.call_count, 1)

    def test_offline_between_draw_and_commit_prevents_execution(self):
        original = self.executor.execute
        def disconnect(*args, **kwargs):
            with db_connect(self.path) as conn:
                conn.execute("UPDATE account_login_ownership SET status='logged_out'")
            return original(*args, **kwargs)
        with patch.object(self.executor, 'execute', side_effect=disconnect):
            result = self.encounter()
        self.assertEqual(result['execution']['reason'], 'actor_offline')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE account_login_ownership SET status='active'")
            conn.execute('UPDATE player_positions SET lat=0,lng=0,version=2')
        self.store.scan(now=self.now)
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_avoided_and_pre_rollout_receipts_never_become_penalties(self):
        self.roll.return_value = 100
        self.assertEqual(self.encounter()['encounter']['outcome'], 'avoided')
        with patch.dict('os.environ', {'CHAOS_RESPONSE_EXECUTION_MODE':'observe'}):
            self.roll.return_value = 1
            self.assertEqual(self.encounter('bob')['encounter']['execution_status'], 'not_enabled')
        self.encounter('bob')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_bystander_no_operation_can_receive_fine(self):
        result = self.encounter('bob')['execution']
        self.assertEqual(result['status'], 'executed')
        self.assertIsNone(result['effects']['cancelled_operation_id'])

    def test_rollout_all_players_does_not_upgrade_old_allowlist_receipts(self):
        with patch.dict('os.environ', {'CHAOS_RESPONSE_EXECUTION_ACTORS':'alice'}):
            self.assertEqual(self.encounter('bob')['encounter']['execution_status'], 'not_enabled')
        self.encounter('bob')  # Wildcard now enabled; same incident must stay untouched.
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)
        self.incident = self.incidents.upsert({**self.incident, 'incident_id':'rollout-new'}, now=self.now)
        from response_network.npc_capsule_factory import NPCCapsuleFactory, position_at
        self.capsule = NPCCapsuleFactory().build_for_incident(self.incident, now=self.now)[0]
        self.capsules.upsert(self.capsule, now=self.now)
        self.now += timedelta(seconds=30)
        self.point = position_at(self.capsule, self.now)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_positions SET lat=?,lng=? WHERE username='bob'", (self.point['lat'], self.point['lng']))
            conn.execute("UPDATE mail_presence SET last_seen_at=? WHERE username='bob'", (self.now.isoformat(),))
        result = self.encounter('bob')
        self.assertEqual(result['execution']['status'], 'executed')
        self.assertEqual(result['encounter']['chance'], 30)
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 1)

    def test_detention_and_protected_inventory_are_not_counted_as_executed(self):
        self.incidents.upsert({**self.incident, 'level':5}, now=self.now)
        self.assertEqual(self.encounter()['execution']['status'], 'unsupported')
        self.incidents.upsert({**self.incident, 'level':3}, now=self.now)
        self.assertEqual(self.encounter('bob')['execution']['status'], 'no_effect')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_worker_recovers_pending_and_expires_closed_source(self):
        with patch.object(self.executor, 'execute', side_effect=RuntimeError('unavailable')):
            self.encounter()
        self.store.scan(now=self.now)
        self.assertEqual(self.rows()[0]['execution_status'], 'executed')
        self.assertEqual(self.roll.call_count, 2)  # worker also encounters bob
        # New isolated pending receipt for cleanup, without any historical replay.
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_encounters SET execution_status='pending'")
        self.incidents.upsert({**self.incident, 'status':'resolved'}, now=self.now)
        self.executor.expire_pending(now=self.now)
        self.assertTrue(all(r['execution_status']=='expired' for r in self.rows()))

    def test_large_profile_is_never_read_and_payload_is_bounded(self):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE users SET profile_json=? WHERE username='alice'", (dumps_json({'padding':'x'*35000000}),))
        token = reset_hot_path_metrics()
        try:
            start = time.perf_counter()
            result = self.encounter()
            elapsed = time.perf_counter()-start
            metrics = get_hot_path_metrics()
            self.assertEqual(result['execution']['status'], 'executed')
            self.assertEqual(metrics.get('profile_bytes', 0), 0)
            self.assertLess(len(dumps_json(result)), 10000)
            print(f'[CONSEQUENCE_BENCH] large_profile elapsed_ms={elapsed*1000:.1f} metrics={metrics}')
        finally:
            restore_hot_path_metrics(token)

    def test_local_baseline_queries_writer_lock_and_profile_denial(self):
        original = db_connect
        statements, locks = [], []
        @contextmanager
        def guarded(path):
            with original(path) as conn:
                started = [None]
                def trace(sql):
                    statements.append(sql)
                    if sql.startswith('BEGIN IMMEDIATE'):
                        started[0] = time.perf_counter()
                    if sql in ('COMMIT', 'ROLLBACK') and started[0] is not None:
                        locks.append((time.perf_counter()-started[0])*1000)
                def authorize(action, table, column, *_):
                    if action == sqlite3.SQLITE_READ and table == 'users' and column == 'profile_json':
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                conn.set_trace_callback(trace)
                conn.set_authorizer(authorize)
                yield conn
        for size in (0, 35000000):
            timings, query_counts, max_locks = [], [], []
            with original(self.path) as conn:
                conn.execute("UPDATE users SET profile_json=? WHERE username='alice'", (dumps_json({'padding':'x'*size}),))
            for number in range(10):
                # Isolated fixture resets only; never a production recovery path.
                with original(self.path) as conn:
                    conn.execute('DELETE FROM response_criminal_records')
                    conn.execute('DELETE FROM response_penalty_history')
                self.incident = self.incidents.upsert({**self.incident,
                    'incident_id':f'bench-{size}-{number}', 'operation_ids':[]}, now=self.now)
                self.capsule = {**self.capsule, 'incident_id':self.incident['incident_id']}
                self.capsules.upsert(self.capsule, now=self.now)
                statements.clear(); locks.clear()
                with patch('response_network.canonical_executor.db_connect', guarded), \
                     patch('response_network.encounters.db_connect', guarded), \
                     patch('database.init_db', side_effect=AssertionError('schema init on hot path')):
                    start = time.perf_counter()
                    result = self.encounter()
                    timings.append((time.perf_counter()-start)*1000)
                self.assertEqual(result['execution']['status'], 'executed')
                query_counts.append(len(statements)); max_locks.append(max(locks))
            self.assertLessEqual(max(query_counts), 80)
            print(f'[CONSEQUENCE_BASELINE] profile_bytes={size} samples=10 p95_ms={sorted(timings)[9]:.1f} '
                  f'max_queries={max(query_counts)} writer_p95_ms={sorted(max_locks)[9]:.1f}')

    def test_world_lock_and_epoch_change_never_apply_old_penalty(self):
        with patch.object(self.executor.world, 'get_gameplay_lock', return_value={'cycle_id':'locked'}):
            result = self.encounter()
        self.assertEqual(result['execution']['reason'], 'ghostsignal_gameplay_locked')
        with patch.object(self.executor.world, 'get_client_restart', return_value={'created_at':(self.now+timedelta(seconds=1)).isoformat()}):
            result = self.encounter()
        self.assertEqual(result['execution']['status'], 'expired')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_pending_kill_switch_and_stale_position_cannot_execute(self):
        with patch.object(self.executor, 'execute', side_effect=RuntimeError('stop')):
            receipt = self.encounter()['encounter']
        with patch.dict('os.environ', {'CHAOS_RESPONSE_EXECUTION_MODE':'observe'}):
            result = self.executor.execute(receipt['encounter_id'], self.candidate(), 'observer', now=self.now)
            self.assertEqual(result['status'], 'disabled')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_positions SET version=version+1 WHERE username='alice'")
        result = self.executor.execute(receipt['encounter_id'], self.candidate(), 'observer', now=self.now)
        self.assertEqual(result['reason'], 'stale_position_version')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_empty_wallet_and_last_tool_do_not_increment_record(self):
        with db_connect(self.path) as conn:
            conn.execute('UPDATE wallet_balances SET balance=0')
        self.assertEqual(self.encounter()['execution']['status'], 'no_effect')
        self.incidents.upsert({**self.incident, 'level':3}, now=self.now)
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO player_apps(username,app_id,app_json,updated_at) VALUES ('bob','last',?, 'now')",
                (dumps_json({'id':'last','operation_types':['port_scan']}),))
        self.assertEqual(self.encounter('bob')['execution']['status'], 'no_effect')
        self.assertEqual(self.scalar('SELECT count(*) FROM response_penalty_history'), 0)

    def test_large_arsenal_still_confiscates_only_bounded_selected_tools(self):
        with db_connect(self.path) as conn:
            conn.executemany("INSERT INTO player_apps(username,app_id,app_json,updated_at) VALUES ('alice',?,?,'now')",
                [(f'extra-{i}',dumps_json({'id':f'extra-{i}','operation_types':['port_scan']})) for i in range(150)])
        self.incidents.upsert({**self.incident, 'level':3}, now=self.now)
        result = self.encounter()['execution']
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(result['effects']['tool_ids'], ['tool-1'])

    def test_recovery_result_after_source_closes_is_readonly_and_private(self):
        first = self.encounter()['execution']
        self.incidents.upsert({**self.incident, 'status':'resolved'}, now=self.now)
        self.assertEqual(self.store.get_result('alice', self.incident['incident_id'])['execution'], first)
        self.assertIsNone(self.store.get_result('bob', self.incident['incident_id']))
        self.assertEqual(self.scalar('SELECT count(*) FROM wallet_balance_events'), 2)

    def test_legacy_judgment_import_is_explicit_and_does_not_fabricate_recidivism(self):
        from tools.migrate_response_judgment import migrate
        source = dumps_json({'judgment':{'points':10},'judgment_history':[{'points_added':10}]})
        with db_connect(self.path) as conn:
            conn.execute("UPDATE users SET profile_json=? WHERE username='alice'", (source,))
        preview = migrate(self.path)
        self.assertEqual(preview['eligible'], ['alice'])
        self.assertEqual(self.scalar('SELECT count(*) FROM response_judgment'), 0)
        self.encounter()
        self.assertEqual(migrate(self.path, apply=True)['imported'], ['alice'])
        self.assertEqual(migrate(self.path, apply=True)['imported'], [])
        self.assertEqual(self.scalar("SELECT points FROM response_judgment WHERE actor_id='alice'"), 12)
        self.assertEqual(self.scalar('SELECT executed_count FROM response_criminal_records'), 1)
        self.assertEqual(self.scalar("SELECT profile_json FROM users WHERE username='alice'"), source)
