"""Transactional identity primitives; callers own commit/rollback and account creation."""
import hashlib
import secrets
import time


DDL = (
    """CREATE TABLE IF NOT EXISTS user_identities (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL CHECK(provider IN ('google','discord','github','steam')),
        provider_user_id TEXT NOT NULL CHECK(length(provider_user_id)>0),
        provider_email TEXT, email_verified INTEGER NOT NULL DEFAULT 0 CHECK(email_verified IN (0,1)),
        linked_at INTEGER NOT NULL, last_used_at INTEGER,
        UNIQUE(provider,provider_user_id), UNIQUE(user_id,provider))""",
    """CREATE TABLE IF NOT EXISTS identity_account_security (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        local_password_enabled INTEGER NOT NULL CHECK(local_password_enabled IN (0,1)),
        verified_email TEXT, email_verified_at INTEGER,
        CHECK((verified_email IS NULL) = (email_verified_at IS NULL)))""",
    """CREATE TABLE IF NOT EXISTS identity_consents (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        terms_version TEXT NOT NULL CHECK(length(terms_version)>0), accepted_at INTEGER NOT NULL,
        PRIMARY KEY(user_id,terms_version))""",
    """CREATE TABLE IF NOT EXISTS identity_intents (
        token_hash TEXT PRIMARY KEY, purpose TEXT NOT NULL
            CHECK(purpose IN ('login','register','link','reauth','email')),
        provider TEXT NOT NULL CHECK(provider IN ('google','discord','github','steam','local')),
        client_hash TEXT NOT NULL, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        generation_hash TEXT, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
        CHECK(expires_at>created_at),
        CHECK(purpose NOT IN ('link','reauth','email') OR
              (user_id IS NOT NULL AND generation_hash IS NOT NULL)))""",
    "CREATE INDEX IF NOT EXISTS identity_intents_expiry ON identity_intents(expires_at)",
)


def initialize(conn):
    from .schema import EXTRA
    for sql in DDL + EXTRA:
        conn.execute(sql)
    if 'user_id' not in {row[1] for row in conn.execute('PRAGMA table_info(identity_mail_challenges)')}:
        conn.execute('ALTER TABLE identity_mail_challenges ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE')
    # Preserve all existing credentials/profiles; missing credentials are disabled.
    conn.execute("""INSERT INTO identity_account_security(user_id,local_password_enabled)
        SELECT id, CASE WHEN typeof(password)='text' AND length(password)>0 THEN 1 ELSE 0 END
        FROM users WHERE id NOT IN (SELECT user_id FROM identity_account_security)""")


def digest(value):
    if not isinstance(value, str) or not value:
        raise ValueError('missing_binding')
    return hashlib.sha256(value.encode()).hexdigest()


def transaction_required(conn):
    if not conn.in_transaction or conn.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ValueError('identity_transaction_required')


def issue_intent(conn, *, purpose, provider, client, ttl, user_id=None, generation=None, now=None):
    transaction_required(conn)
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 1800:
        raise ValueError('invalid_intent_ttl')
    now = int(time.time()) if now is None else now
    token = secrets.token_urlsafe(32)
    conn.execute('INSERT INTO identity_intents VALUES (?,?,?,?,?,?,?,?)',
                 (digest(token), purpose, provider, digest(client), user_id,
                  digest(generation) if generation is not None else None, now, now + ttl))
    return token


def consume_intent(conn, token, *, purpose, provider, client, user_id=None, generation=None, now=None):
    """Consumption rolls back with account/identity writes on the same connection."""
    transaction_required(conn)
    now = int(time.time()) if now is None else now
    cursor = conn.execute('''DELETE FROM identity_intents WHERE token_hash=? AND purpose=?
        AND provider=? AND client_hash=? AND user_id IS ? AND generation_hash IS ?
        AND created_at<=? AND expires_at>?''',
        (digest(token), purpose, provider, digest(client), user_id,
         digest(generation) if generation is not None else None, now, now))
    if cursor.rowcount != 1:
        raise ValueError('invalid_or_expired_intent')


def cleanup(conn, *, now=None):
    transaction_required(conn)
    moment = int(time.time()) if now is None else now
    count = conn.execute('DELETE FROM identity_intents WHERE expires_at<=?', (moment,)).rowcount
    for table in ('identity_tickets', 'identity_grants', 'identity_mail_challenges'):
        conn.execute(f'DELETE FROM {table} WHERE expires_at<=?', (moment,))
    conn.execute('DELETE FROM identity_rate_limits WHERE window_start<?', (moment-86400,))
    conn.execute('DELETE FROM identity_security_events WHERE created_at<?', (moment-90*86400,))
    return count
