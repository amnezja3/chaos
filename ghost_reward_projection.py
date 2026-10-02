"""Scoped GhostNetwork reward receipts; no runtime profile hydration."""
import json

SCHEMAS = (
    '''CREATE TABLE IF NOT EXISTS player_ghost_reward_state (
       username TEXT PRIMARY KEY, stats_json TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS player_ghost_reward_receipts (
       username TEXT NOT NULL, reward_key TEXT NOT NULL, entry_json TEXT NOT NULL,
       PRIMARY KEY(username,reward_key))''',
)


def seed(conn, profile):
    """Registration/offline migration only; historical receipts never repay RSP."""
    username = profile['username']
    inserted = conn.execute('INSERT OR IGNORE INTO player_ghost_reward_state VALUES (?,?)',
                           (username, json.dumps(profile.get('ghostnetwork_stats') or {})))
    if not inserted.rowcount:
        return
    for entry in profile.get('ghostnetwork_reward_history') or []:
        if not isinstance(entry, dict) or not entry.get('reward_key'):
            raise ValueError('Invalid GhostNetwork reward history: ' + username)
        conn.execute('INSERT OR IGNORE INTO player_ghost_reward_receipts VALUES (?,?,?)',
                     (username, entry['reward_key'], json.dumps(entry)))


def settle(progression, service, reward):
    """Commit RSP and a receipt together, then finalize the durable clan saga.

    A crash between the two databases reuses the receipt; clan finalization is
    already idempotent in GhostNetwork's repository transaction.
    """
    from database import db_connect, ProfileRecoveryRequired
    from ghostnetwork.rewards import PROFILE_STAT_BY_REWARD
    username, key = str(reward.get('player_id') or ''), str(reward.get('reward_key') or '')
    if not username or not key:
        raise ValueError('GhostNetwork reward identity missing')
    rsp = int(reward.get('final_rsp') or 0)
    if rsp < 0:
        raise ValueError('Negative GhostNetwork reward')
    with db_connect(progression.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        state = conn.execute('SELECT stats_json FROM player_ghost_reward_state WHERE username=?', (username,)).fetchone()
        if not state:
            raise ProfileRecoveryRequired('GhostNetwork reward migration required: ' + username)
        previous = conn.execute('SELECT entry_json FROM player_ghost_reward_receipts WHERE username=? AND reward_key=?',
                                (username, key)).fetchone()
        duplicate = previous is not None
        if duplicate:
            entry = json.loads(previous['entry_json'])
        else:
            if reward.get('status') != 'pending':
                raise ProfileRecoveryRequired('GhostNetwork applied reward has no verifiable receipt')
            progression.award(conn, username, 0, rsp)
            entry = dict(reward_key=key, reward_type=reward['reward_type'], rsp=rsp, source='ghostnetwork')
            stats = json.loads(state['stats_json'])
            stats['ghostnetwork_rsp_total'] = int(stats.get('ghostnetwork_rsp_total') or 0) + rsp
            stat_key = PROFILE_STAT_BY_REWARD.get(reward['reward_type'])
            if stat_key:
                stats[stat_key] = int(stats.get(stat_key) or 0) + 1
            conn.execute('UPDATE player_ghost_reward_state SET stats_json=? WHERE username=?', (json.dumps(stats), username))
            conn.execute('INSERT INTO player_ghost_reward_receipts VALUES (?,?,?)', (username, key, json.dumps(entry)))
    finalized = service.finalize_projected_reward(
        dict(username=username, ghostnetwork_reward_history=[entry]), reward_id=reward['reward_id'])
    if not finalized.get('ok'):
        raise ProfileRecoveryRequired('GhostNetwork reward finalization failed: ' + str(finalized.get('status')))
    return dict(ok=True, status=finalized.get('status'), duplicate=duplicate,
                profile_changed=False, reward_changed=not duplicate, finalization=finalized)
