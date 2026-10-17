"""Additive runtime tables. No provider access or refresh tokens are retained."""
EXTRA = (
    """CREATE TABLE IF NOT EXISTS identity_flow_data (
        token_hash TEXT PRIMARY KEY REFERENCES identity_intents(token_hash) ON DELETE CASCADE,
        data_json TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS identity_tickets (
        token_hash TEXT PRIMARY KEY, client_hash TEXT NOT NULL, provider TEXT NOT NULL,
        subject TEXT NOT NULL, email TEXT, verified_email TEXT, expires_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS identity_grants (
        token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        generation_hash TEXT NOT NULL, action TEXT NOT NULL, expires_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS identity_mail_challenges (
        binding_hash TEXT PRIMARY KEY, email TEXT NOT NULL, code_hash TEXT NOT NULL,
        expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE)""",
    """CREATE TABLE IF NOT EXISTS identity_rate_limits (
        bucket TEXT PRIMARY KEY, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS identity_retired_subjects (
        provider TEXT NOT NULL, subject_hash TEXT NOT NULL, retired_at INTEGER NOT NULL,
        PRIMARY KEY(provider,subject_hash))""",
    """CREATE TABLE IF NOT EXISTS identity_security_events (
        id INTEGER PRIMARY KEY, event TEXT NOT NULL, actor_id INTEGER, target_id INTEGER,
        created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS identity_mail_settings (
        id INTEGER PRIMARY KEY CHECK(id=1), settings_json TEXT NOT NULL,
        password_ciphertext TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL)""",
)
