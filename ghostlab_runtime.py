"""Bounded, transactional executors for code-owned GhostLab contracts."""
import json
import logging
from datetime import datetime, timedelta
import hashlib
import math
from database import db_connect, PlayerHackAccessChanged
from ghostlab_products import resolve

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FamilyCooldown(ValueError):
    pass


def financial_cooldown_seconds(conn, actor, target):
    previous = conn.execute('''SELECT result,created_at FROM player_hack_tool_usage
        WHERE attacker_username=? AND victim_username=? AND tool_id='financialSniffer'
        ORDER BY id DESC LIMIT 1''', (actor, target)).fetchone()
    if not previous:
        return 0
    text = previous['result'] or ''
    saved = json.loads(text[9:]) if text.startswith('response:') else {}
    until = (datetime.fromisoformat(saved['cooldown_until']) if saved.get('cooldown_until') else
             datetime.fromisoformat(previous['created_at'].replace('Z', '')) + timedelta(minutes=180))
    return max(0, math.ceil((until - datetime.utcnow()).total_seconds()))


def commit_mutation(actor, target, product, access, access_store, guard, builtins, execute):
    """One immutable family receipt and all domain effects in the same transaction."""
    with db_connect(access_store.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        guard(conn=conn)
        current = resolve(conn, actor, product['id'], builtins)
        if not current or not current['runtime_enabled'] or current.get('artifact_id') != product.get('artifact_id'):
            raise PlayerHackAccessChanged('Artifact changed')
        family = current['family_id']
        if access_store.get_tool_usage(access, actor, target, family, conn=conn):
            return {'duplicate': True}
        payload = execute(conn)
        guard(conn=conn)
        identity = dict(actor=actor, target=target, app=product['id'], artifact=product.get('artifact_id'),
                        policy=product.get('policy_version', 1), family=family, status='committed')
        # Inventory executors can already have created the family receipt in this transaction.
        receipt = access_store.record_tool_usage(access, actor, target, family, result='pending:atomic', conn=conn)
        stored = dict(payload, execution=identity)
        conn.execute('UPDATE player_hack_tool_usage SET result=?,amount=? WHERE id=?',
            ('response:' + json.dumps(stored, ensure_ascii=False),
             int(payload.get('stolen_amount', bool(payload.get('removed') or payload.get('kicked')))), receipt['id']))
    logger.info('GLAB_EXECUTION receipt=%s identity=%s', receipt['id'], json.dumps(identity))
    return dict(payload, tool_id=product['id'], tool=product, receipt_id=receipt['id'])


def financial_effect(conn, *, actor, target, product, access, access_store, wallet, deltas,
                     messages, level, respect, randint, random):
    policy = product['blueprint']
    now = datetime.utcnow()
    if financial_cooldown_seconds(conn, actor, target):
        raise FamilyCooldown('Financial Sniffer: trwa cooldown rodziny dla tego celu.')
    row = conn.execute('SELECT balance FROM wallet_balances WHERE username=?', (target,)).fetchone()
    if row is None:
        raise PlayerHackAccessChanged('Wallet unavailable')
    balance = max(0, int(row['balance']))
    maximum = 25 + min(75, level * 3) + min(100, respect // 5)
    roll = randint(5, max(5, maximum)) if balance else 0
    amount = min(roll, math.floor(balance * policy['steal_percent'] / 100), balance)
    detection_roll = random() * 100
    detected = detection_roll < policy['detection_percent']
    key = 'financial_sniffer:' + hashlib.sha256(
        f"{access_store.access_key(access)}:{actor}:{target}:financialSniffer".encode()).hexdigest()
    transfer = wallet.transfer(target, actor, amount, transaction_key=key, note='financialSniffer',
                               debit_up_to=True, source='wallet.technical_transfer', conn=conn)
    for username, side in ((target, 'source'), (actor, 'target')):
        deltas.record_change(username, 'wallet', 'wallet.balance_changed',
            {'balance': transfer[side + '_balance'], 'currency': 'HC', 'reason': 'financial_sniffer'},
            entity_id=username, dedupe_key=key + ':' + side, conn=conn)
    if detected:
        messages.add_message(target, {'dedupe_key': key + ':detected', 'type': 'warning',
            'title': 'Podejrzany ruch finansowy', 'text': 'Wykryto próbę sniffingu finansowego na twoim koncie.'},
            source='financial_sniffer', conn=conn)
    return dict(success=True, result_type='financial_sniffer', stolen_amount=transfer['amount'], currency='HC',
        attacker_balance=transfer['target_balance'], victim_balance_after_known=False, detected=detected,
        roll=roll, detection_roll=detection_roll, cooldown_until=(now + timedelta(minutes=policy['cooldown_minutes'])).isoformat(),
        message=policy['success_message'] if transfer['amount'] else policy['failure_message'], reward_note=policy['reward_note'])


def installed_state(conn, actor, app_id, builtins):
    from ghostlab_products import published_product, runtime_artifact_ready
    product = resolve(conn, actor, app_id, builtins)
    if not product or not product.get('artifact_id'):
        raise PlayerHackAccessChanged('Installed GhostLab artifact unavailable')
    available = published_product(conn, app_id)
    if available and available.get('published') is not False:
        row = conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE artifact_id=?', (available['artifact_id'],)).fetchone()
        if not row or not runtime_artifact_ready(json.loads(row[0])):
            available = None
    else:
        available = None
    return product, available


def update_installed(actor, app_id, expected, desired, inventory, builtins, requirements, delta_bus):
    from response_network.capabilities import require_targeting_allowed
    with db_connect(inventory.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        require_targeting_allowed(conn, actor)
        product, available = installed_state(conn, actor, app_id, builtins)
        if not available or available['artifact_id'] != desired:
            raise PlayerHackAccessChanged('Publication changed')
        if product['artifact_id'] == desired:
            return {'duplicate': True, 'artifact_id': desired}
        if product['artifact_id'] != expected:
            raise PlayerHackAccessChanged('Installed version changed')
        requirements(available, conn)
        old = json.loads(conn.execute('SELECT app_json FROM player_apps WHERE username=? AND app_id=?', (actor, app_id)).fetchone()[0])
        storage = conn.execute('SELECT capacity,used FROM player_storage WHERE username=?', (actor,)).fetchone()
        added = inventory._inventory_storage_size(available, app=True) - inventory._inventory_storage_size(old, app=True)
        if not storage or (added > 0 and storage['used'] + added > storage['capacity']):
            raise ValueError('Brak miejsca na aktualizację.')
        removed_tools = []
        inventory.uninstall_app(actor, app_id=app_id, conn=conn, removed_tools=removed_tools)
        # Preserve purchase identity; update never charges or increments downloads.
        updated = inventory.install_app_with_conn(conn, actor, dict(available, bounded_install=False),
            purchase_key=old.get('wallet_transaction_key') or 'ghostlab:update:' + desired)
        require_targeting_allowed(conn, actor)
        current_storage = dict(conn.execute('SELECT used,capacity,unit FROM player_storage WHERE username=?', (actor,)).fetchone())
        updated_tools = [json.loads(row[0]) for row in conn.execute(
            'SELECT tool_json FROM player_tool_files WHERE username=? AND app_id=?', (actor, app_id))]
        delta_bus.record_change(actor, 'apps', 'apps.app_installed',
            {'app': updated['app'], 'app_id': app_id, 'reason': 'ghostlab_update',
             'removed_tool_ids': [item['tool_id'] for item in removed_tools], 'updated_tools': updated_tools},
            entity_id=app_id, dedupe_key=f'glab:update:{actor}:{app_id}:{desired}', conn=conn)
        delta_bus.record_change(actor, 'storage', 'storage.used_changed',
            current_storage,
            entity_id=actor, dedupe_key=f'glab:update:storage:{actor}:{app_id}:{desired}', conn=conn)
        return {'duplicate': False, 'artifact_id': desired}


def execute_logs(actor, target, product, access, access_store, messages, guard, builtins):
    with db_connect(access_store.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        guard(conn=conn)
        current = resolve(conn, actor, product['id'], builtins)
        if (not current or not current['runtime_enabled']
                or current.get('artifact_id') != product.get('artifact_id')
                or current.get('installed_version') != product.get('installed_version')):
            raise PlayerHackAccessChanged('Runtime disabled')
        if access_store.get_tool_usage(access, actor, target, 'systemLogReader', conn=conn):
            return {'duplicate': True}
        logs = messages.recent_player_hack_logs(target, conn=conn)
        if current.get('artifact_id'):
            policy = current['blueprint']
            logs = logs[-int(policy['log_limit']):]
            for item in logs:
                for field in ('type', 'status', 'created_at'):
                    if not policy['include_' + field]:
                        item.pop(field, None)
        identity = dict(app=product['id'], artifact=product.get('artifact_id'),
                        policy=product.get('policy_version', 1), status='read')
        receipt = access_store.record_tool_usage(access, actor, target, 'systemLogReader',
            result=json.dumps(identity) if product.get('artifact_id') else 'read', conn=conn)
        guard(conn=conn)
        result = dict(success=True, tool_id=product['id'], tool=product, result_type='system_logs',
                      logs=logs, receipt_id=receipt['id'],
                      message='Odczytano komunikaty systemowe celu.' if logs else 'Brak komunikatow systemowych do odczytu.')
    logger.info('GLAB_EXECUTION actor=%s target=%s receipt=%s identity=%s', actor, target, receipt['id'], json.dumps(identity))
    return result
