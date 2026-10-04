"""Sprint 147 backend; the new editor is activated together with sprint 148."""
from flask import jsonify, request, session
import config
from creator_policy import RECIPES, SECURITY_KEYS, power_cap
from ghostlab_store import GhostLabError


def register(app, services):
    creator_apps = {'terminal': 'termcreator', 'window': 'windowmaker',
                    'button_choices': 'buttonmaker', 'progressbar_random': 'appforge'}

    def require_creator(interface):
        app_id = creator_apps.get(interface)
        if not app_id or not services['player_inventory_store'].has_app(owner(), app_id):
            raise GhostLabError('creator_not_installed', 'Brak narzędzia kreatorskiego. Zainstaluj odpowiedni kreator.', 403)

    def owned_project(project_id):
        project = store().get(owner(), project_id)
        require_creator(project['contract']['interface'])
        return project

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
            installed_interfaces=[kind for kind, app_id in creator_apps.items()
                                  if services['player_inventory_store'].has_app(owner(), app_id)],
            recipes=RECIPES, security_keys=SECURITY_KEYS, level=level, power_cap=power_cap(level),
            maximum_chance=config.CREATOR_MAX_POWER_CHANCE,
            effect_min_level=config.CREATOR_EFFECT_MIN_LEVEL,
            effect_enabled=level >= config.CREATOR_EFFECT_MIN_LEVEL)

    @app.get('/api/creators/installed/<app_id>/runtime')
    @guard
    def creator_installed_runtime(app_id):
        import json
        from database import db_connect
        # Read the owner's installed snapshot, never the publication or full profile.
        with db_connect(services['player_inventory_store'].db_path) as conn:
            row = conn.execute(
                "SELECT app_json FROM player_apps WHERE username=? AND app_id=? AND status='installed'",
                (owner(), app_id)).fetchone()
        if not row:
            raise GhostLabError('not_installed', 'Brak zainstalowanej aplikacji.', 404)
        product = json.loads(row[0])
        return jsonify(success=True, applicationEffect=product)

    @app.route('/api/creators/installed/<app_id>', methods=['GET', 'POST'])
    @guard
    def creator_installed(app_id):
        from database import db_connect
        from creator_updates import view, update
        enabled()
        if request.method == 'POST':
            data = payload()
            result = update(owner(), app_id, data.get('expected_version'), data.get('version'),
                            services['player_inventory_store'], services['delta_bus'])
        else:
            with db_connect(services['player_inventory_store'].db_path) as conn:
                result = view(conn, owner(), app_id)
        return jsonify(success=True, **result)

    @app.get('/api/creators/installed/<app_id>/options/<choice>')
    @guard
    def creator_option_quote(app_id, choice):
        from database import db_connect
        from creator_payments import option_quote
        with db_connect(services['player_inventory_store'].db_path) as conn:
            quote = option_quote(conn, owner(), app_id, choice)
        if quote is None:
            raise ValueError('To nie jest wersjonowana opcja Button Choice.')
        return jsonify(success=True, quote=quote)

    @app.get('/api/creators/files')
    @guard
    def creator_files():
        # Legacy catalog metadata is small; never reconstruct files from the profile.
        catalog = services['get_app_catalog']()
        files = {item['project_file'] for item in catalog if item.get('creator_username') == owner()
                 and item.get('project_file') and item.get('published', True) and not item.get('ghostlab_generated')}
        files.update(store().files(owner()))
        files.update(store().project_files(owner()))
        metadata = {item['project_file']: {'name': item.get('name', '') + '.sh', 'icon': item.get('icon', '')}
                    for item in catalog if item.get('creator_username') == owner() and item.get('project_file')}
        metadata.update(store().project_file_metadata(owner()))
        return jsonify(success=True, files=sorted(files), metadata=metadata)

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
        require_creator(data.get('interface'))
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
        return jsonify(success=True, project=owned_project(project_id))

    @app.get('/api/creators/project-file')
    @guard
    def creator_project_file():
        from database import db_connect
        enabled()
        filename = str(request.args.get('name', ''))[:250]
        with db_connect(store().db_path) as conn:
            rows = conn.execute("""SELECT id FROM creator_projects WHERE owner=? AND
                (id || '.sh'=? OR json_extract(project_json,'$.legacy_project_file')=?) LIMIT 2""",
                (owner(), filename, filename)).fetchall()
        if len(rows) != 1:
            raise GhostLabError('project_not_migrated', 'Projekt wymaga migracji lub sprawdzenia przez administratora.', 409)
        return jsonify(success=True, project=owned_project(rows[0]['id']))

    @app.patch('/api/creators/projects/<project_id>')
    @guard
    def creator_edit(project_id):
        enabled()
        owned_project(project_id)
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
        owned_project(project_id)
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
        project = owned_project(project_id)
        reserved = [item.get('name', '') for item in services['get_app_catalog']()
                    if item.get('id') != project['app_id']]
        product = store().publish(owner(), project_id, data['revision'],
                                  services['build_creator_edition'], reserved_names=reserved)
        return jsonify(success=True, app=product)
