"""Sprint 147 backend; the new editor is activated together with sprint 148."""
from flask import jsonify, request, session
import config
from creator_policy import RECIPES, SECURITY_KEYS, power_cap
from ghostlab_store import GhostLabError


def register(app, services):
    def owner():
        if not session.get('user'):
            raise GhostLabError('not_logged_in', 'Zaloguj sie.', 401)
        return session['user']

    def store():
        return services['creator_store']

    def enabled():
        if not config.env_bool('CHAOS_CREATORS_V2_ENABLED', False):
            raise GhostLabError('creator_rollout_pending', 'Nowy kreator oczekuje na aktywacje.', 409)

    def payload():
        if request.content_length and request.content_length > 32768:
            raise GhostLabError('request_too_large', 'Projekt przekracza limit.', 413)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Wymagany obiekt JSON.')
        return data

    def guard(fn):
        from functools import wraps
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                owner()
                return fn(*args, **kwargs)
            except GhostLabError as exc:
                return jsonify(success=False, reason=exc.reason, message=str(exc)), exc.status
            except (ValueError, TypeError, KeyError) as exc:
                return jsonify(success=False, reason='invalid_creator_input', message=str(exc)), 400
        return wrapped

    @app.get('/api/creators/policy')
    @guard
    def creator_policy_view():
        capabilities = services['capability_projection_store'].get_capabilities(owner())
        if not capabilities:
            raise GhostLabError('projection_unavailable', 'Brak projekcji poziomu.', 503)
        level = capabilities['level']
        return jsonify(success=True, enabled=config.env_bool('CHAOS_CREATORS_V2_ENABLED', False),
            recipes=RECIPES, security_keys=SECURITY_KEYS, level=level, power_cap=power_cap(level),
            maximum_chance=config.CREATOR_MAX_POWER_CHANCE,
            effect_min_level=config.CREATOR_EFFECT_MIN_LEVEL,
            effect_enabled=level >= config.CREATOR_EFFECT_MIN_LEVEL)

    @app.get('/api/creators/files')
    @guard
    def creator_files():
        # Legacy catalog metadata is small; never reconstruct files from the profile.
        catalog = services['get_app_catalog']()
        files = {item['project_file'] for item in catalog if item.get('creator_username') == owner()
                 and item.get('project_file') and item.get('published', True) and not item.get('ghostlab_generated')}
        files.update(store().files(owner()))
        return jsonify(success=True, files=sorted(files))

    @app.get('/api/creators/projects')
    @guard
    def creator_projects():
        enabled()
        projects = store().list(owner(), str(request.args.get('after', ''))[:80])
        return jsonify(success=True, projects=projects,
                       next_cursor=projects[-1]['id'] if len(projects) == 100 else None)

    @app.post('/api/creators/projects')
    @guard
    def creator_create():
        enabled()
        data = payload()
        request_id = data.pop('request_id', None)
        name = data.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or ';' in name:
            raise ValueError('Nieprawidlowa nazwa aplikacji.')
        services['validate_generated_app_icon'](data.get('icon'))
        capabilities = services['capability_projection_store'].get_capabilities(owner())
        if not capabilities:
            raise GhostLabError('projection_unavailable', 'Brak projekcji poziomu.', 503)
        project = store().create(owner(), data, request_id, capabilities['level'],
                                 quote=services['quote_creator_price'])
        return jsonify(success=True, project=project)

    @app.get('/api/creators/projects/<project_id>')
    @guard
    def creator_get(project_id):
        enabled()
        return jsonify(success=True, project=store().get(owner(), project_id))

    @app.patch('/api/creators/projects/<project_id>')
    @guard
    def creator_edit(project_id):
        enabled()
        data = payload()
        if set(data) != {'revision', 'presentation'}:
            raise ValueError('Dozwolona jest tylko edycja prezentacji.')
        presentation = data['presentation']
        if isinstance(presentation, dict) and 'icon' in presentation:
            services['validate_generated_app_icon'](presentation['icon'])
        return jsonify(success=True, project=store().update(owner(), project_id, data['revision'], presentation))

    @app.patch('/api/creators/projects/<project_id>/configuration')
    @guard
    def creator_configure(project_id):
        enabled()
        data = payload()
        if set(data) != {'revision', 'configuration'}:
            raise ValueError('Wymagana rewizja i konfiguracja projektu.')
        capabilities = services['capability_projection_store'].get_capabilities(owner())
        if not capabilities:
            raise GhostLabError('projection_unavailable', 'Brak projekcji poziomu.', 503)
        return jsonify(success=True, project=store().configure(owner(), project_id,
            data['revision'], data['configuration'], capabilities['level']))

    @app.post('/api/creators/projects/<project_id>/publish')
    @guard
    def creator_publish(project_id):
        enabled()
        data = payload()
        if set(data) != {'revision'}:
            raise ValueError('Publikacja przyjmuje tylko rewizje projektu.')
        project = store().get(owner(), project_id)
        reserved = [item.get('name', '') for item in services['get_app_catalog']()
                    if item.get('id') != project['app_id']]
        product = store().publish(owner(), project_id, data['revision'],
                                  services['build_creator_edition'], reserved_names=reserved)
        return jsonify(success=True, app=product)
