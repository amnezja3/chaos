"""Bound Flask-Session writes to durable ownership and server expiry."""
from datetime import datetime, timedelta, timezone
from flask import g, request, url_for
from session_generation_store import SessionGenerationStateError


def install_persistent_session_interface(app, store_provider):
    original = app.session_interface

    class GuardedSessionInterface(type(original)):
        def open_session(self, app, request):
            current = super().open_session(app, request)
            if current is not None:
                current._chaos_original_identity = (
                    current.get('session_lineage'), current.get('session_generation'))
            return current

        def get_cookie_secure(self, app):
            # Turning issuance off must not weaken cookies already issued.
            from flask import session
            return bool(getattr(session, '_chaos_expiry', None)) or super().get_cookie_secure(app)

        def get_expiration_time(self, app, session):
            return getattr(session, '_chaos_expiry', None) or super().get_expiration_time(app, session)

        def _upsert_session(self, lifetime, session, store_id):
            expiry = getattr(session, '_chaos_expiry', None)
            if expiry:
                lifetime = max(timedelta(seconds=1), expiry - datetime.now(timezone.utc))
            return super()._upsert_session(lifetime, session, store_id)

        def save_session(self, app, session, response):
            if getattr(g, 'suppress_session_cookie', False):
                return
            lineage = session.get('session_lineage')
            original_lineage, original_generation = getattr(
                session, '_chaos_original_identity', (None, None))
            if original_lineage and not session.get('user'):
                if store_provider().has_newer_login(original_lineage, original_generation):
                    # Recovery/logout from an old request must not replace B's cookie.
                    return
            if lineage and session.get('user'):
                store = store_provider()
                try:
                    store.assert_current(lineage, session.get('session_generation'), session['user'],
                        login_identity_secret=session.get('session_login_identity'),
                        account_revision=session.get('session_account_revision'))
                except SessionGenerationStateError as exc:
                    # No stale response may restore its old SID or delete the new one.
                    app.logger.warning('session_save_rejected method=%s endpoint=%s reason=%s',
                                       request.method, request.endpoint, exc.reason)
                    # A guard can reject after any route/early middleware response,
                    # not just the root redirect. Recover document navigation without
                    # clearing/reissuing cookies or reviving the old generation.
                    document = (request.headers.get('Sec-Fetch-Dest') in {'document','iframe'}
                                or 'text/html' in request.headers.get('Accept',''))
                    if (request.method in {'GET','HEAD'} and document
                            and not request.path.startswith('/api/') and 'index' in app.view_functions):
                        response.status_code = 303
                        response.set_data('')
                        response.content_type = 'text/html; charset=utf-8'
                        response.headers['Location'] = url_for('index', login='1', session_notice='session.stale')
                        response.headers['Cache-Control'] = 'no-store'
                        return
                    response.status_code = 409
                    response.headers.pop('Location', None)
                    response.set_data(app.json.dumps({'ok': False, 'error': 'session_generation_mismatch',
                        'reason': 'stale_session_write', 'reload_required': True}))
                    response.content_type = 'application/json'
                    response.headers['Cache-Control'] = 'no-store'
                    return
                state = store.get_state(lineage)
                if state.get('persistence_policy_version'):
                    session._chaos_expiry = min(datetime.fromisoformat(state[k])
                        for k in ('idle_expires_at', 'absolute_expires_at'))
                    if not session.permanent:
                        session.permanent = True
            return super().save_session(app, session, response)

    guarded = GuardedSessionInterface.__new__(GuardedSessionInterface)
    guarded.__dict__.update(original.__dict__)
    app.session_interface = guarded
