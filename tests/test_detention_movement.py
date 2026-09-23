import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from database import db_connect, PlayerPositionStore, WalletBalanceStore
from response_network.consequence_table import plan_consequence
from response_network.sanctions import SanctionStore
from response_network.movement_guard import MovementBlocked, require_profile_position_allowed
from response_network.travel_purchase import purchase_travel


class DetentionMovementTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'game.db')
        self.positions = PlayerPositionStore(self.path)
        self.wallet = WalletBalanceStore(self.path)
        self.sanctions = SanctionStore(self.path)
        self.now = datetime.now(timezone.utc)
        self.origin, self.destination = {'lat': 52., 'lng': 21.}, {'lat': 53., 'lng': 20.}
        self.positions.upsert('main', self.origin)
        with db_connect(self.path) as conn:
            for actor in ('main', 'admin'):
                conn.execute("INSERT INTO users(username,profile_json,created_at,updated_at) VALUES (?,'{}','now','now')", (actor,))
                conn.execute("INSERT INTO wallet_balances(username,balance,version,updated_at) VALUES (?,10000,1,'now')", (actor,))

    def detain(self):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row, _ = self.sanctions.impose(conn, encounter_id='e', actor_id='main', incident_id='i',
                plan=plan_consequence(5, 0), now=self.now)
            return row['sanction_id']

    def buy(self, price=500, destination=None):
        return purchase_travel(self.wallet, self.positions, actor='main', payee='admin',
            price=price, key='ticket', note='googleplex:ticket', destination=destination or self.destination)

    def test_every_source_denied_and_release_pending_stays_blocked(self):
        sid = self.detain()
        before = self.positions.get('main')
        for source in ('travel', 'blacknet', 'terminal', 'ghostnetwork_suite',
                       'intruderKicker', 'googleplex_travel', 'prison_transport', 'admin'):
            with self.assertRaises(MovementBlocked):
                self.positions.upsert('main', self.destination, source=source)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_sanctions SET remaining_ms=0,status='release_pending'")
        with self.assertRaises(MovementBlocked):
            self.positions.upsert('main', self.destination)
        self.assertEqual(self.positions.get('main'), before)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.sanctions.release(conn, sid, reason='served', now=self.now)
        self.assertTrue(self.positions.upsert('main', self.destination)['changed'])

    def test_paid_and_free_ticket_denial_has_no_wallet_or_position_effect(self):
        self.detain()
        for price in (500, 0):
            with self.assertRaises(MovementBlocked):
                self.buy(price)
        self.assertEqual(self.wallet.get_balance('main'), 10000)
        self.assertEqual(self.wallet.get_balance('admin'), 10000)
        self.assertEqual(self.positions.get_position('main'), self.origin)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM wallet_transactions').fetchone()[0], 0)

    def test_sanction_between_preflight_and_payment_is_checked_inside_transaction(self):
        from response_network.movement_guard import require_movement_allowed
        with db_connect(self.path) as conn:
            require_movement_allowed(conn, 'main')
        self.detain()
        with self.assertRaises(MovementBlocked):
            self.buy()
        self.assertEqual(self.wallet.get_balance('main'), 10000)

    def test_payment_and_move_rollback_on_writer_failure_and_replay_does_not_move(self):
        with patch.object(self.positions, 'upsert', side_effect=RuntimeError('write failed')):
            with self.assertRaises(RuntimeError):
                self.buy()
        self.assertEqual(self.wallet.get_balance('main'), 10000)
        self.buy()
        self.assertEqual(self.wallet.get_balance('main'), 9500)
        self.positions.upsert('main', self.origin)
        payment, _ = self.buy()
        self.assertTrue(payment['duplicate'])
        self.assertEqual(self.positions.get_position('main'), self.origin)
        self.assertEqual(self.wallet.get_balance('main'), 9500)

    def test_legacy_alias_cannot_move_but_canonical_sync_and_unrelated_save_can(self):
        self.detain()
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for key in ('curently_possition', 'current_position'):
                with self.assertRaises(MovementBlocked):
                    require_profile_position_allowed(conn, 'main', {key:self.origin}, {key:self.destination})
                require_profile_position_allowed(conn, 'main', {key:self.destination}, {key:self.origin})
            require_profile_position_allowed(conn, 'main', {'nick':'before'}, {'nick':'after'})

    def test_normalizer_does_not_swallow_denial_or_storage_error(self):
        import run
        self.detain()
        with patch.object(run, 'player_position_store', self.positions):
            with self.assertRaises(MovementBlocked):
                run.normalize_profile_position_update(self.destination, username='main')
        with patch.object(run.player_position_store, 'upsert', side_effect=RuntimeError('locked')):
            with self.assertRaises(RuntimeError):
                run.normalize_profile_position_update(self.destination, username='main')
