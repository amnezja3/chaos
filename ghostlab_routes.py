"""HTTP adapter for canonical GhostLab; dependencies resolved from application scope."""
import json
from flask import jsonify, request, session
from ghostlab_store import GhostLabError
from config import GHOSTLAB_MAX_REQUEST_BYTES
from ghostlab_registry import get_template, public_templates, template_available
from ghostlab_branding import project_branding, validate_branding


def register(app, services):
    def service(name):
        return services[name]

    def actor():
        if not session.get('user'):
            raise GhostLabError('not_logged_in', 'Nie jestes zalogowany.', 401)
        return session['user']

    def payload():
        if request.content_length is not None and request.content_length > GHOSTLAB_MAX_REQUEST_BYTES:
            raise GhostLabError('invalid_payload', 'Request jest zbyt duzy.', 413)
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or len(json.dumps(data)) > GHOSTLAB_MAX_REQUEST_BYTES:
            raise GhostLabError('invalid_payload', 'Nieprawidlowy lub zbyt duzy request.', 400)
        return data

    def valid(project, blueprint, compiling=False):
        result = service('validate_ghostlab_blueprint')(project.get('template_id'), blueprint)
        if not result['valid']:
            raise GhostLabError('invalid_blueprint', '; '.join(result['errors']), 400)
        if compiling and project.get('template_id') in {'', 'custom', None}:
            raise GhostLabError('custom_runtime_unsupported', 'Custom pozostaje szkicem. Uzyj gotowego szablonu.', 400)

    def branding(data, project):
        try:
            return validate_branding(data, project.get('template_id'), service('validate_generated_app_icon'))
        except ValueError as exc:
            raise GhostLabError('invalid_branding', str(exc), 400) from exc

    def reply(owner, project=None, **extra):
        serialize = service('serialize_ghostlab_project')
        return jsonify(success=True, projects=[serialize(p) for p in service('ghostlab_store').list(owner)],
                       project=serialize(project) if project else None, **extra)

    @app.errorhandler(GhostLabError)
    def ghostlab_error(exc):
        return jsonify(success=False, reason=exc.reason, message=str(exc)), exc.status

    @app.get('/api/ghostlab/projects')
    def ghostlab_projects():
        return reply(actor())

    @app.get('/api/ghostlab/templates')
    def ghostlab_templates():
        actor()
        return jsonify(success=True, templates=public_templates(), registry_version=1)

    @app.post('/api/ghostlab/projects')
    def ghostlab_create_project():
        owner, data = actor(), payload()
        name, template = str(data.get('name') or '').strip(), str(data.get('template_id') or '')
        if not name or len(name) > 64 or (template and not get_template(template)):
            raise GhostLabError('invalid_project', 'Nieprawidlowa nazwa lub szablon.', 400)
        if template and not template_available(template, 'creation'):
            raise GhostLabError('template_creation_disabled', 'Tworzenie tego szablonu jest wylaczone.')
        if any(len(str(data.get(k) or '')) > limit for k, limit in [('template_name',80),('tool_category',40)]):
            raise GhostLabError('invalid_project', 'Metadane sa za dlugie.', 400)
        try:
            icon = service('validate_generated_app_icon')(data.get('icon') or '🧪')
        except ValueError as exc:
            raise GhostLabError('invalid_icon', str(exc), 400) from exc
        seed = dict(name=name, slug=service('ghostlab_project_slug')(name), template_id=template,
                    template_name=str(data.get('template_name') or template),
                    tool_category=str(data.get('tool_category') or ''), icon=icon,
                    blueprint=service('default_ghostlab_blueprint')(template))
        seed.update(project_branding(seed))
        project = service('ghostlab_store').create(owner, seed, data.get('request_id'))
        return reply(owner, project, message='Projekt utworzony.')

    @app.patch('/api/ghostlab/projects/<project_id>')
    def ghostlab_rename_project(project_id):
        owner, data = actor(), payload()
        name = str(data.get('name') or '').strip()
        if not name or len(name) > 64:
            raise GhostLabError('invalid_name', 'Nieprawidlowa nazwa.', 400)
        project = service('ghostlab_store').update(owner, project_id, data.get('revision'),
                    dict(name=name, slug=service('ghostlab_project_slug')(name)))
        return reply(owner, project)

    @app.patch('/api/ghostlab/projects/<project_id>/blueprint')
    def ghostlab_update_project_blueprint(project_id):
        owner, data = actor(), payload()
        project = service('ghostlab_store').get(owner, project_id)
        valid(project, data.get('blueprint'))
        changes = {'blueprint': data['blueprint']}
        if 'branding' in data:
            changes.update(branding(data['branding'], project))
            changes['slug'] = service('ghostlab_project_slug')(changes['name'])
        project = service('ghostlab_store').update(owner, project_id, data.get('revision'), changes)
        return reply(owner, project, message='Draft zapisany. Skompiluj przed publikacja.')

    @app.post('/api/ghostlab/projects/<project_id>/compile')
    def ghostlab_compile_project(project_id):
        owner, data = actor(), payload()
        project = service('ghostlab_store').get(owner, project_id)
        valid(project, data.get('blueprint'), compiling=True)
        if 'branding' in data and branding(data['branding'], project) != project_branding(project):
            raise GhostLabError('unsaved_branding', 'Zapisz marke produktu przed kompilacja.')
        project = service('ghostlab_store').compile(owner, project_id, data.get('revision'), data['blueprint'], service('build_ghostlab_artifact'))
        return reply(owner, project, artifact=project['artifact'], message='Build gotowy. Runtime nadal oczekuje.')

    @app.get('/api/ghostlab/projects/<project_id>/export')
    def ghostlab_export_project(project_id):
        owner = actor()
        project = service('ghostlab_store').get(owner, project_id)
        response = jsonify(format='ghostlab-project', format_version=2, owner=owner, project=service('serialize_ghostlab_project')(project))
        response.headers['Content-Disposition'] = f'attachment; filename="{project["id"]}.glab"'
        return response

    @app.post('/api/ghostlab/projects/<project_id>/publisher')
    def ghostlab_publish_project(project_id):
        owner, data = actor(), payload()
        project = service('ghostlab_store').get(owner, project_id)
        valid(project, project['blueprint'], compiling=True)
        identity = service('identity_projection_store').get_creator_identity(owner)
        capabilities = service('capability_projection_store').get_capabilities(owner)
        if not capabilities:
            raise GhostLabError('creator_projection_unavailable', 'Brak projekcji poziomu autora.')
        author = dict(nick=identity['nick'], level=capabilities['level'], respect=identity['respect'],
                      hackcoins=service('wallet_balance_store').get_balance(owner))
        project, app_data = service('ghostlab_store').publish(owner, project_id, data.get('revision'), data.get('artifact_id'),
                                      service('build_ghostlab_googleplex_app'), author)
        return reply(owner, project, app=app_data, message='Opublikowano build. Custom runtime nadal oczekuje.')

    @app.delete('/api/ghostlab/projects/<project_id>')
    def ghostlab_delete_project(project_id):
        owner, data = actor(), payload()
        service('ghostlab_store').delete(owner, project_id, data.get('revision'))
        return reply(owner, message='Szkic usuniety.')

    @app.post('/api/ghostlab/projects/<project_id>/withdraw')
    def ghostlab_withdraw_project(project_id):
        owner, data = actor(), payload()
        project = service('ghostlab_store').withdraw(owner, project_id, data.get('revision'))
        return reply(owner, project, message='Wycofano sprzedaz. Zakupione wersje i buildy pozostaja.')
