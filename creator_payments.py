"""Installed option pricing and atomic immediate-effect settlement."""
import hashlib
import json
from database import atomic_runtime_transaction, db_connect, wallet_reserved
from ghostlab_store import GhostLabError, encoded


def publish_wallet_state(conn, wallet, delta_bus, actor, key):
    balance = wallet.get_balance(actor)
    reserved = wallet_reserved(conn, actor)
    delta_bus.record_change(actor, 'wallet', 'wallet.balance_changed',
        dict(balance=balance, reserved=reserved, available=max(0, balance-reserved), currency='HC'),
        entity_id='wallet', dedupe_key=key, conn=conn)


def option_quote(conn, actor, app_id, choice):
    row = conn.execute("SELECT app_json FROM player_apps WHERE username=? AND app_id=? AND status='installed'",
                       (actor, app_id)).fetchone()
    if not row:
        raise GhostLabError('not_installed', 'Brak zainstalowanej aplikacji.', 409)
    app = json.loads(row[0])
    contract = app.get('creator_contract') or {}
    if not app.get('creator_contract_version') or contract.get('interface') != 'button_choices':
        return None
    if isinstance(choice, str) and choice in {str(i) for i in range(32)}:
        choice = int(choice)
    options = contract.get('options') or [{'price': 0} for _ in app.get('levels', [{}])[0].get('options', [])]
    if type(choice) is not int or not 0 <= choice < len(options):
        raise ValueError('Wybierz prawidłową opcję.')
    price = options[choice].get('price', 0)
    if type(price) is not int or price < 0:
        raise ValueError('Nieprawidłowa cena zainstalowanej opcji.')
    author = app.get('creator_username')
    recipient = author if conn.execute('SELECT 1 FROM users WHERE username=?', (author,)).fetchone() else 'admin'
    if price and not conn.execute('SELECT 1 FROM users WHERE username=?', (recipient,)).fetchone():
        raise GhostLabError('recipient_missing', 'Brak konta odbiorcy opłaty.', 409)
    return dict(price=0 if recipient == actor else price, listed_price=price,
                recipient=recipient, version=app.get('version'), choice=choice,
                # Asynchronous completion needs its own finalizer, not a launch fee.
                asynchronous=bool(contract.get('operation_types'))
                    and contract.get('action') != 'camera_shutdown'
                    and not bool(options[choice].get('effect') or contract.get('effect')))


def execute(actor, data, inventory, wallet, delta_bus, operation, make_response):
    """Return None for the existing non-creator/free path."""
    with db_connect(inventory.db_path) as conn:
        row = conn.execute("SELECT app_json FROM player_apps WHERE username=? AND app_id=? AND status='installed'",
                           (actor, data.get('app_id'))).fetchone()
        candidate = json.loads(row[0]) if row else {}
        if not candidate.get('creator_contract_version') or (candidate.get('creator_contract') or {}).get('interface') != 'button_choices':
            return None
        quote = option_quote(conn, actor, data.get('app_id'), data.get('choice_id'))
    if not quote or not quote['price']:
        return None
    receipt = data.get('launch_receipt') or data.get('receipt') or data.get('launch_key')
    if not isinstance(receipt, str) or not 8 <= len(receipt) <= 160:
        raise ValueError('Płatna opcja wymaga identyfikatora użycia. Otwórz aplikację ponownie.')
    if data.get('operation_only'):
        raise GhostLabError('choice_required', 'Wybierz opcję w aplikacji.', 409)
    key = 'creator:option:' + hashlib.sha256(encoded([actor, data['app_id'], quote['choice'], receipt]).encode()).hexdigest()
    signature = hashlib.sha256(encoded(data.get('expected_target') or data.get('target') or {}).encode()).hexdigest()
    with atomic_runtime_transaction(inventory.db_path) as conn:
        previous = conn.execute('SELECT request_hash,response_json,status_code FROM creator_option_receipts WHERE receipt_key=?', (key,)).fetchone()
        if previous:
            if previous['request_hash'] != signature:
                raise GhostLabError('receipt_conflict', 'Identyfikator użycia należy do innego celu.', 409)
            return make_response((json.loads(previous['response_json']), previous['status_code']))
        quote = option_quote(conn, actor, data['app_id'], data.get('choice_id'))
        if quote is None:
            raise GhostLabError('edition_changed', 'Wersja aplikacji zmieniła się.', 409)
        if wallet.get_balance(actor) - wallet_reserved(conn, actor) < quote['price']:
            raise GhostLabError('insufficient_funds', 'Brak HC na skuteczne użycie opcji.', 409)
        response = make_response(operation())
        payload = response.get_json()
        if not isinstance(payload, dict):
            raise ValueError('Nieprawidłowa odpowiedź wykonania opcji.')
        charged = 0
        reserved = 0
        if response.status_code == 200 and payload.get('success') is True and not payload.get('duplicate'):
            if quote['price'] and quote['asynchronous']:
                ids = [item['operation_id'] for item in payload.get('created_operations', []) if item.get('operation_id')]
                if not ids:
                    raise GhostLabError('no_new_operation', 'Ta próba nie utworzyła nowej operacji.', 409)
                conn.execute('INSERT INTO wallet_holds VALUES(?,?,?)', (key, actor, quote['price']))
                reserved = quote['price']
                publish_wallet_state(conn, wallet, delta_bus, actor, key + ':hold')
                conn.execute('INSERT INTO creator_option_pending VALUES(?,?,?,?,?)',
                             (key, actor, quote['recipient'], quote['price'], encoded(ids)))
                for operation_id in ids:
                    row = conn.execute('SELECT operation_json FROM player_operations WHERE username=? AND operation_id=?', (actor, operation_id)).fetchone()
                    if not row:
                        raise ValueError('Brak kanonicznej operacji.')
                    saved = json.loads(row[0])
                    saved['creator_payment_pending'] = key
                    conn.execute('UPDATE player_operations SET operation_json=?,version=version+1 WHERE username=? AND operation_id=?',
                                 (encoded(saved), actor, operation_id))
            elif quote['price']:
                payment = wallet.transfer(actor, quote['recipient'], quote['price'], transaction_key=key,
                    note='Skuteczne użycie opcji aplikacji', source='creator.option', conn=conn)
                charged = quote['price']
                for username in (actor, quote['recipient']):
                    publish_wallet_state(conn, wallet, delta_bus, username, key + ':' + username)
        payload['option_payment'] = dict(amount=charged, recipient=quote['recipient'], success_only=True,
            reserved=reserved)
        conn.execute('INSERT INTO creator_option_receipts VALUES(?,?,?,?)',
                     (key, signature, encoded(payload), response.status_code))
        return make_response((payload, response.status_code))


def settle_pending(inventory, wallet, delta_bus, finalize, limit=32, on_error=None):
    """Restart-safe queue: terminal operations remain candidates until settlement commits."""
    with db_connect(inventory.db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='creator_option_pending'").fetchone():
            return 0
        keys = [row[0] for row in conn.execute('''SELECT p.receipt_key FROM creator_option_pending p
            WHERE NOT EXISTS (SELECT 1 FROM json_each(p.operations_json) ids
                JOIN player_operations o ON o.operation_id=ids.value AND o.username=p.username
                WHERE o.status NOT IN ('completed','timeout','failed','detected','cancelled','canceled'))
            ORDER BY p.rowid LIMIT ?''', (limit,))]
    settled = 0
    for key in keys:
        try:
            settled += bool(_settle_receipt(key, inventory, wallet, delta_bus, finalize))
        except Exception as error:
            if on_error is None:
                raise
            on_error(key, error)
    return settled


def _settle_receipt(key, inventory, wallet, delta_bus, finalize):
    with atomic_runtime_transaction(inventory.db_path) as conn:
        pending = conn.execute('SELECT * FROM creator_option_pending WHERE receipt_key=?', (key,)).fetchone()
        if not pending:
            return False
        operations = []
        for operation_id in json.loads(pending['operations_json']):
            row = conn.execute('SELECT status,operation_json FROM player_operations WHERE username=? AND operation_id=?',
                               (pending['username'], operation_id)).fetchone()
            operations.append((row['status'], json.loads(row['operation_json'])) if row else ('missing', {}))
        terminal = {'completed', 'timeout', 'failed', 'detected', 'cancelled', 'canceled', 'missing'}
        if any(status not in terminal for status, _ in operations):
            return False
        success = bool(operations) and all(status in {'completed', 'timeout'} for status, _ in operations)
        recipient = pending['recipient']
        if not conn.execute('SELECT 1 FROM users WHERE username=?', (recipient,)).fetchone():
            recipient = 'admin'
        if not conn.execute('SELECT 1 FROM users WHERE username=?', (recipient,)).fetchone() or not conn.execute(
                'SELECT 1 FROM users WHERE username=?', (pending['username'],)).fetchone():
            success = False
        conn.execute('DELETE FROM wallet_holds WHERE receipt_key=?', (key,))
        amount = 0
        if success and recipient != pending['username']:
            payment = wallet.transfer(pending['username'], recipient, pending['amount'], transaction_key=key,
                note='Skuteczne zakończenie operacji aplikacji', source='creator.option.completed', conn=conn)
            amount = pending['amount']
            publish_wallet_state(conn, wallet, delta_bus, recipient, key + ':incoming')
        if conn.execute('SELECT 1 FROM users WHERE username=?', (pending['username'],)).fetchone():
            publish_wallet_state(conn, wallet, delta_bus, pending['username'], key + ':released')
        for status, operation in operations:
            if not operation:
                continue
            operation.pop('creator_payment_pending', None)
            operation['creator_payment_settled'] = {'amount': amount, 'success': success}
            operation['status'] = status
            conn.execute('UPDATE player_operations SET operation_json=?,version=version+1 WHERE username=? AND operation_id=?',
                (encoded(operation), pending['username'], operation['operation_id']))
            if success:
                finalize(pending['username'], operation)
        row = conn.execute('SELECT response_json FROM creator_option_receipts WHERE receipt_key=?', (key,)).fetchone()
        response = json.loads(row[0])
        response['success'] = success
        response['created_operations'] = [operation for _, operation in operations if operation]
        if not success:
            response['message'] = 'Operacja zakończona bez sukcesu. Rezerwacja HC została zwolniona.'
        response['option_payment'] = dict(amount=amount, recipient=recipient, success_only=True, reserved=0, settled=True)
        conn.execute('UPDATE creator_option_receipts SET response_json=? WHERE receipt_key=?', (encoded(response), key))
        conn.execute('DELETE FROM creator_option_pending WHERE receipt_key=?', (key,))
        return True
