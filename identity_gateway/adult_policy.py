"""Versioned adult declaration; shares Identity storage and session ownership."""
import os
import sqlite3
import time
from flask import current_app, jsonify, redirect, request, session
from database import db_connect
from .service import IdentityError

TERMS_VERSION = '157-18-v1'
AGE_VERSION = '18-v1'


def enabled():
    value = current_app.config.get('CHAOS_ADULT_POLICY_ENABLED', os.getenv('CHAOS_ADULT_POLICY_ENABLED', '0'))
    return value is True or str(value).lower() in ('1', 'true', 'yes', 'on')


def validate(data):
    if not isinstance(data, dict) or data.get('age_confirmed') is not True or data.get('age_statement_version') != AGE_VERSION:
        raise IdentityError('adult_declaration_required')
    if data.get('terms') != TERMS_VERSION:
        raise IdentityError('current_terms_required')


def require_schema(conn):
    try:
        conn.execute('SELECT age_confirmed,age_statement_version FROM identity_consents LIMIT 0')
        conn.execute('SELECT age_restricted FROM identity_account_security LIMIT 0')
    except sqlite3.OperationalError:
        raise IdentityError('migration_required') from None


def record(conn, user_id, data):
    validate(data)
    require_schema(conn)
    restricted = conn.execute('SELECT age_restricted FROM identity_account_security WHERE user_id=?', (user_id,)).fetchone()
    if restricted and restricted[0]:
        raise IdentityError('age_restricted')
    conn.execute('''INSERT INTO identity_consents
        (user_id,terms_version,accepted_at,age_confirmed,age_statement_version) VALUES (?,?,?,1,?)
        ON CONFLICT(user_id,terms_version) DO NOTHING''', (user_id, TERMS_VERSION, int(time.time()), AGE_VERSION))


def state(conn, username):
    row = conn.execute('''SELECT s.age_restricted,c.age_confirmed,c.age_statement_version
        FROM users u LEFT JOIN identity_account_security s ON s.user_id=u.id
        LEFT JOIN identity_consents c ON c.user_id=u.id AND c.terms_version=?
        WHERE u.username=?''', (TERMS_VERSION, username)).fetchone()
    if row and row[0]:
        return 'age_restricted'
    if row and row[1] == 1 and row[2] == AGE_VERSION:
        return ''
    return 'adult_acceptance_required'


def install(runtime):
    # Exact endpoint allowlist: new gameplay routes are denied by default.
    public = {'static', 'legal_page', 'index', 'logout', 'session_recover',
              'installation_manifest', 'installation_worker', 'installation_shortcut'}
    account = {'identity.account_page', 'identity.identities', 'identity.reauth',
               'identity.manage', 'identity.password', 'identity.account_email', 'identity.delete_account',
               'identity.start', 'identity.callback', 'identity.adult_terms', 'identity.accept_adult_terms',
               'identity.decline_adult_terms'}

    def gate():
        if not enabled() or not session.get('user') or request.method == 'OPTIONS':
            return None
        if request.endpoint in public | account:
            return None
        try:
            with db_connect(runtime.user_store.db_path) as conn:
                reason = state(conn, session['user'])
        except sqlite3.OperationalError:
            return jsonify(ok=False, error='adult_policy_unavailable'), 503
        if not reason:
            return None
        if request.method in ('GET', 'HEAD') and not request.path.startswith('/api/') and not request.headers.get('X-Chaos-Session-Generation'):
            return redirect('/account/terms')
        return jsonify(ok=False, error=reason, redirect='/account/terms'), 403

    # Run before detention/epoch gates and launch interception, including warm PWA sessions.
    runtime.app.before_request_funcs.setdefault(None, []).insert(0, gate)

    @runtime.app.context_processor
    def context():
        return dict(adult_policy_enabled=enabled(), adult_terms_version=TERMS_VERSION,
                    age_statement_version=AGE_VERSION)
