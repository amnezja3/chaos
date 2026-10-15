"""Read-only session bootstrap. Never activates ownership or upgrades legacy cookies."""
import hashlib
import hmac
import secrets

from flask import g, jsonify, render_template, request, session
from session_generation_store import SessionGenerationStateError


def register_launch_controller(app, runtime):
    def digest(purpose, value):
        key = app.secret_key
        if isinstance(key, str):
            key = key.encode()
        return hmac.new(key, (purpose + ':' + str(value or '')).encode(), hashlib.sha256).hexdigest()

    def binding():
        # Domain separated from the legacy query token: this cannot authorize API calls.
        return digest('launch-binding', session.get('session_generation'))

    def csrf():
        return digest('launch-csrf', str(getattr(session, 'sid', '')) + ':'
                      + str(session.get('session_generation', '')))

    def private_headers_off():
        g.launch_public_response = True
        g.suppress_session_cookie = True

    def same_origin():
        origin = request.headers.get('Origin')
        return (request.headers.get('Sec-Fetch-Site') not in {'cross-site', 'same-site'}
                and request.headers.get('X-Chaos-Launch') == '1'
                and (not origin or origin in {request.host_url.rstrip('/'), 'https://' + request.host}))

    def current():
        if not session.get('user'):
            return 'not_authenticated'
        keys = ('session_lineage', 'session_generation', 'session_login_identity', 'session_account_revision', 'session_csrf')
        if not all(session.get(key) for key in keys):
            return 'incomplete_session'
        try:
            runtime['session_generation_store'].assert_current(
                session['session_lineage'], session['session_generation'], session['user'],
                login_identity_secret=session['session_login_identity'],
                account_revision=session['session_account_revision'])
        except SessionGenerationStateError as error:
            return error.reason
        if not runtime['user_store'].has_user(session['user']):
            return 'account_missing'
        return ''

    def pin_request():
        g.session_generation = session['session_generation']
        g.session_lineage = session['session_lineage']
        g.session_generation_user = session['user']
        g.session_login_identity = session['session_login_identity']
        g.session_account_revision = session['session_account_revision']
        runtime['bind_request_profile_precommit_guard']()

    def check_binding(required=False):
        provided = request.headers.get('X-Chaos-Launch-Binding', '')
        return (not provided and not required) or (bool(provided) and secrets.compare_digest(provided, binding()))

    def shell(view='desktop'):
        private_headers_off()
        # The public document must not consult or embed the current account's locale/profile.
        g.ghost_ui_locale = request.accept_languages.best_match(['pl', 'en']) or 'pl'
        return render_template('launch.html', launch_config={
            'csrf': csrf(), 'view': view, 'locale': g.ghost_ui_locale,
            'text': {key: runtime['locale_translator']().t('entry.launch.' + key, locale=g.ghost_ui_locale)
                     for key in ('start', 'retry', 'stale', 'storage', 'retry_button', 'login', 'javascript')},
        })

    @app.get('/launch')
    def launch():
        return shell()

    @app.get('/api/session/status')
    def launch_status():
        private_headers_off()
        if not same_origin():
            return jsonify(ok=False, error='origin_rejected'), 403
        try:
            if not check_binding():
                return jsonify(ok=False, error='session_binding_mismatch'), 409
            reason = current()
            if reason:
                return jsonify(ok=True, authenticated=False, reason=reason)
            pin_request()
            return jsonify(ok=True, authenticated=True, binding=binding())
        except Exception:
            app.logger.exception('Launch status unavailable')
            return jsonify(ok=False, error='session_unavailable'), 503

    @app.post('/api/session/bootstrap')
    def launch_bootstrap():
        private_headers_off()
        if not same_origin() or not request.headers.get('Origin'):
            return jsonify(ok=False, error='csrf_rejected'), 403
        try:
            if not check_binding(required=True):
                return jsonify(ok=False, error='session_binding_mismatch'), 409
            if not secrets.compare_digest(request.headers.get('X-Chaos-Launch-CSRF', ''), csrf()):
                return jsonify(ok=False, error='csrf_rejected'), 403
            reason = current()
            if reason:
                return jsonify(ok=False, error='authentication_required', reason=reason), 401
            pin_request()
            context = runtime['session_generation_client_context']()
            return jsonify(ok=True, context=context, binding=binding())
        except Exception:
            app.logger.exception('Launch bootstrap unavailable')
            return jsonify(ok=False, error='session_unavailable'), 503

    @app.get('/api/desktop-shell')
    def desktop_shell():
        if not session.get('user'):
            return jsonify(ok=False, error='authentication_required'), 401
        return runtime['desktop']()

    return {'shell': shell, 'binding': binding}
