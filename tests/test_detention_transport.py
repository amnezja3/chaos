import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from database import db_connect, WalletInsufficientFunds, PlayerPositionStore
from response_network.detention import DetentionService
from response_network.prison_catalog import list_prisons
from response_network.movement_guard import MovementBlocked
from session_generation_store import username_digest
from tests import test_canonical_consequences as fixture


class DetentionTransportTest(unittest.TestCase):
    seed_actor = fixture.CanonicalConsequencesTest.seed_actor
    candidate = fixture.CanonicalConsequencesTest.candidate
    rows = fixture.CanonicalConsequencesTest.rows

    def setUp(self):
        fixture.CanonicalConsequencesTest.setUp(self)
        flag = patch.dict('os.environ', {'CHAOS_RESPONSE_DETENTION_ENABLED': 'true'})
        flag.start(); self.addCleanup(flag.stop)
        self.service = self.executor.detention
        self.positions = PlayerPositionStore(self.path)
        self.origin = self.positions.get_position('alice')
        self.incident = self.incidents.upsert({**self.incident, 'level': 4, 'heat': 100}, now=self.now)
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO response_criminal_records VALUES ('alice',1,?)", (self.now.isoformat(),))
            conn.execute('UPDATE account_login_ownership SET active_revision=1')
            conn.execute("UPDATE wallet_balances SET balance=2000000 WHERE username IN ('alice','bob')")

    def arrest(self):
        result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['execution']['status'], 'executed', result)
        self.sid = result['execution']['effects']['sanction_id']
        return result

    def test_arrest_clears_target_and_legacy_profile_cannot_restore_after_bail(self):
        from database import PlayerTargetRuntimeStore, PlayerMarkedTargetStore
        from response_network.capabilities import DetentionDenied
        targets = PlayerTargetRuntimeStore(self.path)
        old = {'target_id':'map:old','lat':52,'lng':21,'label':'Old target'}
        targets.upsert_aimed('alice', old)
        self.arrest()
        self.assertEqual(targets.get_active_target('alice'), {})
        with self.assertRaises(DetentionDenied): targets.upsert_aimed('alice', old)
        with self.assertRaises(DetentionDenied): PlayerMarkedTargetStore(self.path).upsert('alice',old)
        self.service.pay_bail('bob',self.sid,now=self.now)
        self.assertEqual(targets.seed_from_profile('alice', {'aimed_target':old}), {})
        self.assertEqual(targets.get_active_target('alice'), {})
        self.assertTrue(targets.upsert_aimed('alice', {**old,'target_id':'map:new'})['changed'])

    def test_already_running_sentence_clears_old_target_on_tick(self):
        self.arrest()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_target_runtime SET status='aimed',target_json=? WHERE username='alice'",
                         (json.dumps({'target_id':'old'}),))
        self.service.tick(now=self.now)
        with db_connect(self.path) as conn:
            row = conn.execute("SELECT status,target_json FROM player_target_runtime WHERE username='alice'").fetchone()
            self.assertEqual(tuple(row),('cleared','{}'))

    def test_arrest_ends_active_superpower_without_resetting_cooldown(self):
        from ghostnetwork.repository import GhostNetworkRepository
        from response_network.capabilities import DetentionDenied
        repo = GhostNetworkRepository(db_path=self.path)
        args = dict(player_id='alice',ability_code='insider_feed',cycle_id='cycle',source_part_id='part',
                    source_part_code='V1',level_snapshot=10,source_state_version=1,
                    request_key='ability',duration_seconds=300,cooldown_seconds=600,now=self.now)
        before = repo.activate_ability_window(**args)['window']
        self.arrest()
        after = repo.get_latest_ability_window('alice')
        self.assertEqual(after['cooldown_until'],before['cooldown_until'])
        from datetime import datetime
        self.assertLessEqual(datetime.fromisoformat(after['expires_at']),self.now)
        with self.assertRaises(DetentionDenied): repo.activate_ability_window(**args)
        with self.assertRaises(DetentionDenied):
            self.ops.compare_and_swap_runtime('alice', [], event_type='operation.ability_speed')

    def presence(self, seconds, status='active', revision=1):
        at = self.now + timedelta(seconds=seconds)
        with db_connect(self.path) as conn:
            conn.execute('UPDATE account_login_ownership SET status=?,active_revision=? WHERE username_hash=?',
                         (status, revision, username_digest('alice')))
            conn.execute("UPDATE mail_presence SET last_seen_at=? WHERE username='alice'", (at.isoformat(),))
        return at

    def test_atomic_sentence_saved_prison_return_and_no_new_rolls(self):
        result = self.arrest()
        with db_connect(self.path) as conn:
            transport = conn.execute('SELECT * FROM response_detention_transport').fetchone()
            prison = json.loads(transport['prison_json'])
            self.assertIn(prison, list_prisons())
            self.assertEqual((transport['return_lat'], transport['return_lng']), (self.point['lat'], self.point['lng']))
            self.assertEqual(conn.execute("SELECT executed_count FROM response_criminal_records WHERE actor_id='alice'").fetchone()[0], 2)
        self.assertEqual(self.positions.get_position('alice'), {'lat': prison['lat'], 'lng': prison['lng']})
        self.assertEqual(result['execution']['effects']['detention_seconds'], 300)
        with self.assertRaises(MovementBlocked):
            self.positions.upsert('alice', self.point, source='prison_transport')
        with patch.object(self.store, 'roller', side_effect=AssertionError('new roll in prison')):
            denied = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(denied['reason'], 'actor_detained')
        self.assertEqual(len(self.rows()), 1)

    def test_crash_rolls_back_transport_sentence_history_and_message(self):
        before = self.positions.get('alice')
        with patch.object(self.deltas, 'record_change', side_effect=RuntimeError('outbox failed')):
            result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['execution']['status'], 'deferred')
        self.assertEqual(self.positions.get('alice'), before)
        with db_connect(self.path) as conn:
            for table in ('response_sanctions','response_detention_transport','response_penalty_history'):
                self.assertEqual(conn.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)
        self.arrest()
        self.assertEqual(self.roll.call_count, 1)

    def test_offline_freeze_restart_new_session_and_automatic_return_with_flag_off(self):
        self.arrest()
        at = self.presence(60)
        self.service.tick(now=at)
        self.assertEqual(self.service.quote('alice')['remaining_seconds'], 240)
        self.service.tick(now=self.presence(61, 'logged_out'))
        self.service = DetentionService(self.path, self.wallet, self.messages, self.deltas)
        self.service.tick(now=self.now + timedelta(hours=4))
        self.assertEqual(self.service.quote('alice')['remaining_seconds'], 240)
        self.service.tick(now=self.presence(15000, revision=2))
        self.assertEqual(self.service.quote('alice')['remaining_seconds'], 240)
        with patch.dict('os.environ', {'CHAOS_RESPONSE_DETENTION_ENABLED': 'false'}):
            for t in (15060, 15120, 15180, 15240):
                self.service.tick(now=self.presence(t, revision=2))
        self.assertIsNone(self.service.quote('alice'))
        self.assertEqual(self.positions.get_position('alice'), self.origin)
        self.assertEqual(self.service.tick(now=self.now + timedelta(seconds=15241))['checked'], 0)

    def test_two_payers_charge_once_and_do_not_clear_record(self):
        self.arrest()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda payer: self.service.pay_bail(payer, self.sid, now=self.now), ['alice','bob']))
        self.assertEqual(sum(r['paid'] for r in results), 1)
        self.assertEqual(self.wallet.get_balance('alice') + self.wallet.get_balance('bob'), 3750000)
        self.assertEqual(self.wallet.get_balance('admin'), 250000)
        self.assertEqual(self.positions.get_position('alice'), self.origin)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT executed_count FROM response_criminal_records WHERE actor_id='alice'").fetchone()[0], 2)
            self.assertEqual(conn.execute('SELECT bail_paid_hc FROM response_detention_transport').fetchone()[0], 250000)

    def test_bail_rollback_and_insufficient_funds_leave_prisoner_and_balance(self):
        self.arrest()
        prison = self.positions.get('alice')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE wallet_balances SET balance=1 WHERE username='bob'")
        with self.assertRaises(WalletInsufficientFunds):
            self.service.pay_bail('bob', self.sid, now=self.now)
        with patch.object(self.service, '_move', side_effect=RuntimeError('return failed')):
            with self.assertRaises(RuntimeError):
                self.service.pay_bail('alice', self.sid, now=self.now)
        self.assertEqual(self.wallet.get_balance('alice'), 2000000)
        self.assertEqual(self.wallet.get_balance('admin'), 0)
        self.assertEqual(self.positions.get('alice'), prison)
        self.assertEqual(self.service.quote('alice')['status'], 'active')

    def test_treasury_payer_keeps_money_and_retry_never_charges_again(self):
        self.arrest()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE wallet_balances SET balance=500000 WHERE username='admin'")
        result = self.service.pay_bail('admin', self.sid, now=self.now)
        self.assertEqual(result['balance'], 500000)
        self.assertEqual(self.wallet.get_balance('admin'), 500000)
        self.assertFalse(self.service.pay_bail('bob', self.sid, now=self.now)['paid'])
        self.assertEqual(self.wallet.get_balance('bob'), 2000000)
        with db_connect(self.path) as conn:
            receipt = conn.execute('SELECT * FROM wallet_transactions').fetchone()
            self.assertEqual((receipt['from_username'], receipt['to_username'], receipt['amount']), ('admin','admin',250000))

    def test_historical_bail_reconciliation_is_verified_and_once(self):
        from tools.reconcile_bail_treasury import reconcile
        self.arrest()
        # Reproduce the previously deployed debit-only implementation.
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.wallet.debit('bob',250000,'detention_bail:'+self.sid,reason='response.bail',conn=conn)
            conn.execute('UPDATE response_detention_transport SET bail_payer=?,bail_paid_hc=? WHERE sanction_id=?', ('bob',250000,self.sid))
            self.service._release(conn,self.service.sanctions.get(conn,self.sid),reason='bail',now=self.now)
        self.assertEqual(reconcile(self.path,self.sid)['status'],'would_credit')
        self.assertEqual(self.wallet.get_balance('admin'),0)
        self.assertEqual(reconcile(self.path,self.sid,True)['status'],'credited')
        self.assertEqual(reconcile(self.path,self.sid,True)['status'],'already_credited')
        self.assertEqual(self.wallet.get_balance('admin'),250000)
        with self.assertRaises(ValueError): reconcile(self.path,'not-a-sentence',True)

    def test_legacy_collection_only_credits_actual_debit_and_replay_once(self):
        from response_network.treasury import collect
        for _ in range(2):
            with db_connect(self.path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                result = collect(self.wallet,self.deltas,conn,'bob',3000000,'legacy-test',
                                 'response_network.hc_confiscation',up_to=True)
                self.assertEqual(result['amount_delta'],-2000000)
        self.assertEqual(self.wallet.get_balance('bob'),0)
        self.assertEqual(self.wallet.get_balance('admin'),2000000)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM wallet_transactions').fetchone()[0],1)

    def test_served_sentence_does_not_charge_bail_and_quote_has_no_coordinates(self):
        self.arrest()
        self.assertNotIn('lat', json.dumps(self.service.quote('alice')))
        for seconds in (60, 120, 180, 240):
            self.service.tick(now=self.presence(seconds))
        result = self.service.pay_bail('bob', self.sid, now=self.presence(300))
        self.assertEqual(result, {'paid': False, 'reason': 'sentence_served'})
        self.assertEqual(self.wallet.get_balance('bob'), 2000000)
        self.assertEqual(self.positions.get_position('alice'), self.origin)

    def test_old_unsupported_receipt_is_not_reactivated(self):
        with patch.dict('os.environ', {'CHAOS_RESPONSE_DETENTION_ENABLED': 'false'}):
            result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['execution']['status'], 'unsupported')
        result = self.store.encounter(self.candidate(), 'alice', now=self.now)
        self.assertEqual(result['execution']['status'], 'unsupported')
        self.assertIsNone(self.service.quote('alice'))

    def test_worker_failure_rolls_back_release_and_remains_retryable(self):
        self.arrest()
        for seconds in (60, 120, 180, 240):
            self.service.tick(now=self.presence(seconds))
        at = self.presence(300)
        with patch.object(self.service, '_move', side_effect=RuntimeError('return unavailable')):
            with self.assertLogs('response_network.detention', level='ERROR'):
                self.assertEqual(self.service.tick(now=at)['errors'], 1)
        self.assertEqual(self.service.quote('alice')['remaining_seconds'], 60)
        self.assertEqual(self.service.tick(now=at)['released'], 1)
        self.assertEqual(self.positions.get_position('alice'), self.origin)

    def test_http_bail_uses_authenticated_payer_and_saved_amount(self):
        import run
        from tests import test_target_persistence as http_fixture
        self.arrest()
        http_fixture.setUpModule()
        self.addCleanup(http_fixture.tearDownModule)
        with patch.object(run, 'detention_service', self.service):
            client = run.app.test_client()
            self.assertEqual(client.get('/api/response/detention').status_code, 401)
            with client.session_transaction() as session:
                session['user'] = 'bob'
            own = client.get('/api/response/detention?username=alice')
            self.assertEqual(own.status_code, 200, own.json)
            self.assertIsNone(own.json['detention'])
            quote = client.get('/api/response/detention/bail-quote?username=alice')
            self.assertEqual(quote.status_code, 200, quote.json)
            self.assertEqual(quote.json['quote']['bail_hc'], 250000)
            self.assertNotIn('return_lat', str(quote.json))
            malformed = client.post('/api/response/detention/bail', json=['wrong'])
            self.assertEqual(malformed.status_code, 400, malformed.json)
            result = client.post('/api/response/detention/bail', json={
                'sanction_id': self.sid, 'payer': 'alice', 'amount_hc': 1})
            self.assertEqual(result.status_code, 200, result.json)
            self.assertTrue(result.json['paid'])
        self.assertEqual(self.wallet.get_balance('alice'), 2000000)
        self.assertEqual(self.wallet.get_balance('bob'), 1750000)

    def test_self_bail_offer_uses_own_canonical_balance_at_exact_threshold(self):
        import run
        from tests import test_target_persistence as http_fixture
        self.arrest()
        http_fixture.setUpModule()
        self.addCleanup(http_fixture.tearDownModule)
        with patch.object(run, 'detention_service', self.service):
            client = run.app.test_client()
            with client.session_transaction() as session: session['user'] = 'alice'
            for balance, expected in [(249999,False),(250000,True)]:
                with db_connect(self.path) as conn:
                    conn.execute("UPDATE wallet_balances SET balance=? WHERE username='alice'", (balance,))
                response = client.get('/api/response/detention?bail_offer=1&username=bob&balance=9999999')
                self.assertEqual(response.status_code,200,response.json)
                self.assertEqual(response.json['bail_offer'], {'actor_id':'alice','balance_hc':balance,'can_pay':expected})
            self.assertNotIn('bail_offer',client.get('/api/response/detention').json)
            bob = run.app.test_client()
            with bob.session_transaction() as session: session['user'] = 'bob'
            response = bob.get('/api/response/detention?bail_offer=1&username=alice')
            self.assertEqual(response.status_code,200,response.json)
            self.assertNotIn('bail_offer',response.json)

    def test_stage_nine_sentence_can_commit_from_detection_request(self):
        import run
        from tests import test_target_persistence as http_fixture
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_criminal_records SET executed_count=4 WHERE actor_id='alice'")
        http_fixture.setUpModule()
        self.addCleanup(http_fixture.tearDownModule)
        endpoint = next(rule.endpoint for rule in run.app.url_map.iter_rules()
                        if rule.rule == '/api/map/incidents/detection-candidates')
        def detection():
            return self.store.encounter(self.candidate(), 'alice', now=self.now)
        with patch.object(run,'detention_service',self.service), patch.dict(run.app.view_functions,{endpoint:detection}):
            client=run.app.test_client()
            with client.session_transaction() as session: session['user']='alice'
            response=client.post('/api/map/incidents/detection-candidates',json={})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['execution']['status'],'executed',response.json)
        self.assertEqual(self.service.quote('alice')['stage'],9)
