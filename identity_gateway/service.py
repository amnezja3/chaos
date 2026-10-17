"""Identity operations inside the existing CHAOS transaction coordinator."""
import json
import secrets
import time
from .audit import nick_key, email_key
from .store import digest


class IdentityError(ValueError):
    pass


def ready(conn):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE name='identity_account_security'").fetchone())


def event(conn, name, actor=None, target=None):
    conn.execute('INSERT INTO identity_security_events(event,actor_id,target_id,created_at) VALUES (?,?,?,?)',
                 (name, actor, target, int(time.time())))


def rate_limit(conn, bucket, maximum=10, window=600):
    now = int(time.time())
    key = digest(bucket)
    row = conn.execute('SELECT window_start,attempts FROM identity_rate_limits WHERE bucket=?',(key,)).fetchone()
    if row and row[0] > now-window:
        if row[1] >= maximum:
            raise IdentityError('rate_limited')
        conn.execute('UPDATE identity_rate_limits SET attempts=attempts+1 WHERE bucket=?',(key,))
    else:
        conn.execute('INSERT OR REPLACE INTO identity_rate_limits VALUES (?,?,1)',(key,now))


def account(conn, username):
    row = conn.execute('SELECT id,username FROM users WHERE username=?',(username,)).fetchone()
    if not row:
        raise IdentityError('account_unavailable')
    return row


def assert_available(conn, profile, username):
    """Writer-locked check against legacy and new profiles, no silent renames."""
    for row in conn.execute("SELECT username, json_extract(profile_json,'$.nick'), json_extract(profile_json,'$.email') FROM users WHERE username<>?",(username,)):
        if profile.get('nick') and nick_key(str(row[1] or '')) == nick_key(profile['nick']):
            raise IdentityError('identity_collision')
        if profile.get('email') and email_key(str(row[2] or '')) == email_key(profile['email']):
            raise IdentityError('identity_collision')


def sync_profile(conn, profile, previous=None):
    """Used by guarded writes so changing an email invalidates its verification."""
    if not ready(conn):
        return
    previous = previous or {}
    if any(profile.get(k) != previous.get(k) for k in ('nick','email')):
        assert_available(conn, profile, profile['username'])
    user_id = account(conn,profile['username'])[0]
    conn.execute('''INSERT INTO identity_account_security(user_id,local_password_enabled) VALUES (?,?)
        ON CONFLICT(user_id) DO UPDATE SET local_password_enabled=excluded.local_password_enabled''',
        (user_id,int(bool(profile.get('password')))))
    conn.execute('''UPDATE identity_account_security SET verified_email=NULL,email_verified_at=NULL
        WHERE user_id=? AND verified_email IS NOT NULL AND verified_email<>?''',
        (user_id,email_key(str(profile.get('email') or ''))))


def grant(conn, user_id, generation, action):
    if action not in ('link','unlink','password','email','delete','mail_settings'):
        raise IdentityError('invalid_action')
    token = secrets.token_urlsafe(32)
    conn.execute('INSERT INTO identity_grants VALUES (?,?,?,?,?)',
                 (digest(token),user_id,digest(generation),action,int(time.time())+300))
    return token


def use_grant(conn, token, user_id, generation, action):
    if not token:
        raise IdentityError('reauth_required')
    row=conn.execute('SELECT expires_at FROM identity_grants WHERE token_hash=?',(digest(token),)).fetchone()
    changed = conn.execute('''DELETE FROM identity_grants WHERE token_hash=? AND user_id=?
        AND generation_hash=? AND action=? AND expires_at>?''',
        (digest(token),user_id,digest(generation),action,int(time.time()))).rowcount
    if changed != 1:
        raise IdentityError('reauth_required')
    return row[0]


def link(conn, user_id, identity):
    if conn.execute('SELECT 1 FROM identity_retired_subjects WHERE provider=? AND subject_hash=?',
                    (identity['provider'],digest(identity['subject']))).fetchone():
        raise IdentityError('identity_retired')
    conn.execute('''INSERT INTO user_identities(user_id,provider,provider_user_id,provider_email,
        email_verified,linked_at) VALUES (?,?,?,?,?,?)''',
        (user_id,identity['provider'],identity['subject'],identity.get('email'),
         int(bool(identity.get('email_verified'))),int(time.time())))
    event(conn,'identity_linked',user_id,user_id)


def unlink(conn, user_id, provider):
    state = conn.execute('SELECT local_password_enabled FROM identity_account_security WHERE user_id=?',(user_id,)).fetchone()
    count = conn.execute('SELECT count(*) FROM user_identities WHERE user_id=?',(user_id,)).fetchone()[0]
    if count <= 1 and not (state and state[0]):
        raise IdentityError('last_method')
    if conn.execute('DELETE FROM user_identities WHERE user_id=? AND provider=?',(user_id,provider)).rowcount != 1:
        raise IdentityError('identity_missing')
    event(conn,'identity_unlinked',user_id,user_id)


def retire(conn, user_id, actor_id):
    username=conn.execute('SELECT username FROM users WHERE id=?',(user_id,)).fetchone()[0]
    for provider, subject in conn.execute('SELECT provider,provider_user_id FROM user_identities WHERE user_id=?',(user_id,)):
        conn.execute('INSERT OR IGNORE INTO identity_retired_subjects VALUES (?,?,?)',
                     (provider,digest(subject),int(time.time())))
    conn.execute('DELETE FROM identity_flow_data WHERE token_hash IN (SELECT token_hash FROM identity_intents WHERE user_id=?)',(user_id,))
    for table in ('user_identities','identity_account_security','identity_consents','identity_intents','identity_grants','identity_mail_challenges'):
        conn.execute(f'DELETE FROM {table} WHERE user_id=?',(user_id,))
    # Personal copies only. Financial receipts and shared world history retain
    # their stable actor references, protected by the existing username tombstone.
    for table in ('player_apps','player_tool_files','player_data_files','system_messages','wallet_balances',
                  'player_scan_snapshots','response_camera_observations'):
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
            conn.execute(f'DELETE FROM {table} WHERE username=?',(username,))
    event(conn,'account_deleted',actor_id,user_id)
