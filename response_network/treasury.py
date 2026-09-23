"""System collections keep HC in the admin treasury, in the caller transaction."""
from database import utc_now

TREASURY = 'admin'


def collect(wallet, deltas, conn, payer, amount, key, reason, *, up_to=False, **kwargs):
    charge = wallet.debit_up_to if up_to else wallet.debit
    debit = charge(payer, amount, key, reason=reason,
                        source='response_network', peer_username=TREASURY, conn=conn, **kwargs)
    amount = abs(int(debit['amount_delta']))
    credit = wallet.credit(TREASURY, amount, key + ':treasury', reason=reason,
                           source='response_network', peer_username=payer, conn=conn)
    conn.execute('''INSERT INTO wallet_transactions
        (from_username,to_username,amount,transaction_key,note,created_at) VALUES (?,?,?,?,?,?)
        ON CONFLICT(transaction_key) WHERE transaction_key <> '' DO NOTHING''',
        (payer, TREASURY, amount, key, reason, utc_now()))
    deltas.record_change(TREASURY, 'wallet', 'wallet.balance_changed',
        {'balance': credit['balance'], 'currency': 'HC'}, entity_id='wallet',
        dedupe_key=key + ':treasury', conn=conn)
    if payer == TREASURY:
        debit = {**debit, 'balance': credit['balance']}
    return debit
