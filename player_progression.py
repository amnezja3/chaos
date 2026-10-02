"""Canonical territory rewards, with checkpoints for legacy profile readers.

Only explicit profile/registration writers may seed this store. Runtime settlement
never reads a profile and never reconstructs a missing progression row.
"""
import json

CHECKPOINT = 'territory_progression_checkpoint'
SCHEMA = '''CREATE TABLE IF NOT EXISTS player_progression (
    username TEXT PRIMARY KEY, level_gain INTEGER NOT NULL DEFAULT 0,
    respect_gain INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
    territory_stats_json TEXT NOT NULL, exp TEXT NOT NULL)'''


def strategic_reward(level, encirclement, resolutions):
    encirclement = encirclement or {}
    transferred = max(0, int(encirclement.get('transferred_pillar_count') or 0))
    gained = 1 if encirclement.get('awarded') else 0
    rewards, seen = [], set()
    for item in resolutions or ():
        conflict_id = str(item.get('conflict_id') or '').strip()
        version = int(item.get('resolution_version') or 0)
        key = f'conflict:{conflict_id}:{version}'
        if not conflict_id or key in seen:
            continue
        seen.add(key)
        rewards.append(dict(reward_key=key, conflict_id=conflict_id,
            resolution_version=version, level_before=level, levels_gained=1, respect_gain=level))
    levels = gained + len(rewards)
    respect = (transferred if gained else 0) + sum(item['respect_gain'] for item in rewards)
    return dict(territory_progression=dict(respect_gain=0,levels_gained=0),
        encirclement=dict(reward_key=str(encirclement.get('reward_key') or 'encirclement'),
            levels_gained=gained,transferred_pillar_count=transferred,respect_gain=transferred if gained else 0),
        conflict_resolutions=rewards,totals=dict(respect_gain=respect,levels_gained=levels,
                                               level_before=level,level_after=level+levels))


def seed(conn, profile):
    if profile.get(CHECKPOINT):
        exists = conn.execute('SELECT 1 FROM player_progression WHERE username=?', (profile['username'],)).fetchone()
        if not exists:
            raise ValueError('Cannot recreate a missing reward ledger from its checkpoint')
    conn.execute('INSERT OR IGNORE INTO player_progression '
        '(username,territory_stats_json,exp) VALUES(?,?,?)',
        (profile['username'], json.dumps(profile.get('territory_stats') or {}), str(profile.get('exp') or '')))

    from ghost_reward_projection import seed as seed_ghost_rewards
    seed_ghost_rewards(conn, profile)


def overlay(conn, username, profile):
    row = conn.execute('SELECT * FROM player_progression WHERE username=?', (username,)).fetchone()
    return overlay_row(profile, row)


def overlay_row(profile, row):
    from database import ProfileRecoveryRequired
    if row is None:
        if profile.get(CHECKPOINT):
            raise ProfileRecoveryRequired('Progression checkpoint has no ledger')
        return profile
    marker = profile.get(CHECKPOINT) or {}
    validate_checkpoint(marker, row)
    for key, column in (('level', 'level_gain'), ('respect', 'respect_gain')):
        if type(profile.get(key)) in (int, float):
            profile[key] = profile[key] + row[column] - int(marker.get(column, 0))
    if row['version'] > int(marker.get('version', 0)):
        profile['territory_stats'] = json.loads(row['territory_stats_json'])
        profile['exp'] = row['exp']
    profile[CHECKPOINT] = {key: row[key] for key in ('level_gain', 'respect_gain', 'version')}
    return profile


def validate_checkpoint(marker, row):
    from database import ProfileRecoveryRequired
    if not isinstance(marker, dict) or (marker and set(marker) != {'level_gain','respect_gain','version'}):
        raise ProfileRecoveryRequired('Invalid progression checkpoint')
    if any(type(marker.get(key,0)) is not int or not 0 <= marker.get(key,0) <= row[key]
           for key in ('level_gain','respect_gain','version')):
        raise ProfileRecoveryRequired('Progression checkpoint is ahead of ledger')


def sync_profile_stats(conn, profile):
    """A validated legacy write may update stats after incorporating rewards."""
    marker = profile.get(CHECKPOINT)
    if marker:
        conn.execute('''UPDATE player_progression SET territory_stats_json=?,exp=?
            WHERE username=? AND version=? AND level_gain=? AND respect_gain=?''',
            (json.dumps(profile.get('territory_stats') or {}),str(profile.get('exp') or ''),
             profile['username'],marker['version'],marker['level_gain'],marker['respect_gain']))


def projection_values(conn, username, *, level=None, respect=None):
    row = conn.execute('''SELECT g.level_gain,g.respect_gain,g.version,
        json_extract(p.desktop_boot_json,'$.territory_progression_checkpoint') AS checkpoint
        FROM player_progression g JOIN user_identity_projection p USING(username)
        WHERE g.username=?''', (username,)).fetchone()
    if row:
        marker = json.loads(row['checkpoint']) if row['checkpoint'] is not None else {}
        validate_checkpoint(marker, row)
        if level is not None:
            level += row['level_gain'] - int(marker.get('level_gain',0))
        if respect is not None:
            respect += row['respect_gain'] - int(marker.get('respect_gain',0))
    return level, respect


class PlayerProgressionStore:
    def __init__(self, db_path):
        from database import SystemMessageStore
        self.db_path = db_path
        self.messages = SystemMessageStore(db_path)

    def get(self, username, *, conn=None):
        from contextlib import nullcontext
        from database import (db_connect, ProfileRecoveryRequired, PROFILE_INTEGRITY_VALID,
                              CAPABILITY_PROJECTION_VERSION, IDENTITY_PROJECTION_VERSION)
        with (db_connect(self.db_path) if conn is None else nullcontext(conn)) as db:
            if not db.in_transaction:
                db.execute('BEGIN')
            row = db.execute('''SELECT g.territory_stats_json,g.exp,g.version,
                p.player_level,json_extract(i.desktop_boot_json,'$.respect') AS respect
                FROM player_progression g
                JOIN user_capability_projection p USING(username)
                JOIN user_identity_projection i USING(username)
                JOIN users u USING(username)
                WHERE g.username=? AND u.profile_integrity_status=?
                  AND p.source_profile_revision=u.profile_revision
                  AND i.source_profile_revision=u.profile_revision
                  AND p.source_profile_checksum=u.profile_checksum
                  AND i.source_profile_checksum=u.profile_checksum
                  AND json_extract(i.desktop_boot_json,'$.source_profile_revision')=u.profile_revision
                  AND json_extract(i.desktop_boot_json,'$.source_profile_checksum')=u.profile_checksum
                  AND p.projection_version=? AND i.projection_version=?''',
                (username, PROFILE_INTEGRITY_VALID, CAPABILITY_PROJECTION_VERSION,
                 IDENTITY_PROJECTION_VERSION)).fetchone()
            if not row:
                raise ProfileRecoveryRequired('Progression migration required: ' + username)
            if row['respect'] is None:
                raise ProfileRecoveryRequired('Progression respect projection missing')
            level, respect = projection_values(db, username, level=int(row['player_level']), respect=int(row['respect']))
            return dict(username=username, level=level, respect=respect,
                        territory_stats=json.loads(row['territory_stats_json']), exp=row['exp'],
                        progression_version=row['version'])

    def award(self, conn, username, level_gain, respect_gain, stats=None, exp=None):
        from database import ProfileRecoveryRequired, _run_profile_precommit_guard
        if type(level_gain) is not int or type(respect_gain) is not int or min(level_gain, respect_gain) < 0:
            raise ValueError('Invalid progression delta')
        if not conn.in_transaction:
            raise ValueError('A progression award requires an explicit transaction')
        self.get(username, conn=conn)  # fail closed before any mutation
        revision = conn.execute('SELECT profile_revision FROM users WHERE username=?', (username,)).fetchone()[0]
        _run_profile_precommit_guard(None, conn, username, revision)
        updated = conn.execute('''UPDATE player_progression SET level_gain=level_gain+?,
            respect_gain=respect_gain+?,version=version+1,
            territory_stats_json=COALESCE(?,territory_stats_json),exp=COALESCE(?,exp)
            WHERE username=?''', (level_gain, respect_gain,
                json.dumps(stats) if stats is not None else None, exp, username))
        if updated.rowcount != 1:
            raise ProfileRecoveryRequired('Progression migration required: ' + username)
        # Invalidate legacy CAS readers without touching the heavy payload/checksum.
        conn.execute('UPDATE users SET profile_revision=profile_revision+1 WHERE username=?', (username,))
        conn.execute('UPDATE user_capability_projection SET source_profile_revision=source_profile_revision+1 WHERE username=?', (username,))
        conn.execute('''UPDATE user_identity_projection SET source_profile_revision=source_profile_revision+1,
            desktop_boot_json=json_set(desktop_boot_json,'$.source_profile_revision',source_profile_revision+1)
            WHERE username=?''', (username,))

    def refresh_stats(self, username, calculate):
        """Recalculate statistics against the current ledger under its writer lock.

        The callback is pure: it receives the current small progression snapshot.
        No reward is granted, and an unchanged retry does not bump revisions.
        """
        from database import db_connect
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current = self.get(username, conn=conn)
            updated = calculate(dict(current))
            stats, exp = updated['territory_stats'], updated.get('exp')
            if stats != current['territory_stats'] or exp != current['exp']:
                self.award(conn, username, 0, 0, stats, exp)
            return self.get(username, conn=conn)

    def settle(self, receipt_id, progression, stats=None, exp=None, messages=(), *, coalesced_receipts=(), conn=None):
        from database import db_connect, utc_now
        from contextlib import nullcontext
        with (db_connect(self.db_path) if conn is None else nullcontext(conn)) as conn:
            if not conn.in_transaction:
                conn.execute('BEGIN IMMEDIATE')
            receipt = conn.execute('SELECT actor_username,status,result_json FROM territory_progression_receipts WHERE receipt_id=?',
                                   (receipt_id,)).fetchone()
            if not receipt:
                return dict(ok=False, reason='receipt_not_found')
            if receipt['status'] == 'applied':
                return dict(ok=True, duplicate=True, result=json.loads(receipt['result_json']))
            if receipt['status'] != 'pending':
                return dict(ok=False, reason='receipt_not_pending')
            actor = receipt['actor_username']
            if callable(progression):
                progression = progression(self.get(actor, conn=conn))
            deltas = progression.get('totals', progression)
            self.award(conn, actor, deltas.get('levels_gained', 0),
                       deltas.get('respect_gain', 0), stats, exp)
            current = self.get(actor, conn=conn)
            result = dict(progression)
            if 'totals' not in result:
                result['level'] = current['level']
            for index, message in enumerate(messages):
                self.messages.add_message(actor, dict(message, id=f'{receipt_id}:message:{index}'),
                                          source='territory_progression', conn=conn)
            timestamp = utc_now()
            conn.execute("UPDATE territory_progression_receipts SET status='applied',result_json=?,updated_at=?,applied_at=? WHERE receipt_id=?",
                         (json.dumps(result), timestamp, timestamp, receipt_id))
            for extra_id in coalesced_receipts:
                extra = conn.execute('SELECT actor_username FROM territory_progression_receipts WHERE receipt_id=?', (extra_id,)).fetchone()
                if not extra or extra['actor_username'] != actor:
                    raise ValueError('Invalid coalesced receipt owner')
                consumed = self.settle(extra_id, dict(area_gain=0, effective_gain=0,
                    respect_gain=0, levels_gained=0, coalesced_into=receipt_id), stats, exp, conn=conn)
                if not consumed.get('ok'):
                    raise ValueError('Coalesced receipt cannot be settled')
            return dict(ok=True, duplicate=False, result=result)
