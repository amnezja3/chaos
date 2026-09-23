"""Credit a verified historical bail sink to admin once. Dry-run unless --apply."""
import argparse
import json
import sys
import sqlite3
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import db_connect, WalletBalanceStore, GameStateDeltaBus
from response_network.treasury import TREASURY


def reconcile(db_path, sanction_id, apply=False):
    path = Path(db_path).resolve(strict=True)
    wallet, deltas = (WalletBalanceStore(db_path), GameStateDeltaBus(db_path)) if apply else (None, None)
    key = 'detention_bail:' + sanction_id
    connection = db_connect(db_path) if apply else closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True))
    with connection as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        payment = conn.execute('''SELECT t.bail_payer,t.bail_paid_hc,s.status,s.release_reason
            FROM response_detention_transport t JOIN response_sanctions s USING(sanction_id)
            WHERE sanction_id=?''', (sanction_id,)).fetchone()
        if not payment or payment['status'] != 'released' or payment['release_reason'] != 'bail':
            raise ValueError('No completed bail payment for this sentence')
        amount = int(payment['bail_paid_hc'])
        debit = conn.execute('''SELECT amount_delta,reason FROM wallet_balance_events
            WHERE username=? AND transaction_key=?''', (payment['bail_payer'], key)).fetchone()
        if amount <= 0 or not debit or debit['amount_delta'] != -amount or debit['reason'] != 'response.bail':
            raise ValueError('Bail receipt does not match the canonical debit')
        credit = conn.execute('''SELECT amount_delta FROM wallet_balance_events
            WHERE username=? AND transaction_key=?''', (TREASURY, key + ':treasury')).fetchone()
        if credit and credit['amount_delta'] != amount:
            raise ValueError('Treasury credit mismatch')
        result = {'sanction_id': sanction_id, 'payer': payment['bail_payer'], 'recipient': TREASURY,
                  'amount_hc': amount, 'status': 'already_credited' if credit else 'would_credit'}
        if apply and not credit:
            state = wallet.credit(TREASURY, amount, key + ':treasury', reason='response.bail',
                source='bail_treasury_reconciliation', peer_username=payment['bail_payer'], conn=conn)
            deltas.record_change(TREASURY, 'wallet', 'wallet.balance_changed',
                {'balance': state['balance'], 'currency': 'HC'}, entity_id='wallet',
                dedupe_key=key + ':treasury', conn=conn)
            result.update(status='credited', balance=state['balance'])
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/game.sqlite3')
    parser.add_argument('--sanction-id', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(reconcile(args.db, args.sanction_id, args.apply), ensure_ascii=False, indent=2))
