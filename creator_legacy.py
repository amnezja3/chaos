"""Offline adoption of historical definitions; runtime semantics stay legacy."""
import copy
from ghostlab_store import digest, encoded, now
from creator_policy import INTERFACES, validate_presentation
from database import db_connect


def validate_update(conn, installed, available):
    import json
    from run import normalize_app_contract
    row = conn.execute('SELECT project_json FROM creator_projects WHERE id=?',
                       (available.get('creator_project_id'),)).fetchone()
    project = json.loads(row[0]) if row else {}
    baseline = project.get('legacy_snapshot')
    if not baseline or installed.get('creator_username') != project.get('owner'):
        raise ValueError('Brak zgodnego historycznego projektu.')
    cosmetic = {'name', 'icon', 'description', 'title', 'project_file', 'version', 'published', 'downloads'}
    level_text = {'command', 'logs', 'list', 'title', 'text', 'steps', 'result_success', 'result_failure'}
    def clean(value):
        levels = copy.deepcopy(value)
        for level in levels or []:
            for key in level_text:
                level.pop(key, None)
            for group in ('options', 'buttons'):
                for option in level.get(group, []):
                    option.pop('label', None)
        return levels
    def mechanics(app):
        normalized = normalize_app_contract(copy.deepcopy(app))
        return {k: clean(normalized.get(k)) if k == 'levels' else normalized.get(k)
                for k in baseline if k not in cosmetic}
    if mechanics(installed) != mechanics(baseline) or mechanics(available) != mechanics(baseline):
        raise ValueError('Historyczna mechanika jest niezgodna; wymagana kontrola migracji.')


def project_from_app(app):
    kind = app.get('interface')
    levels = app.get('levels')
    if kind not in INTERFACES or not isinstance(levels, list) or not levels:
        raise ValueError('unsupported_interface')
    if type(app.get('price')) is not int or app['price'] < 0:
        raise ValueError('invalid_price')
    if kind != 'terminal' and len(levels) != 1:
        raise ValueError('multiple_stages_require_review')
    for key in ('id', 'creator_username', 'project_file', 'name', 'icon'):
        if not isinstance(app.get(key), str) or not app[key].strip():
            raise ValueError('missing_' + key)
    p = {key: app.get(key, '') for key in ('name', 'icon', 'description')}
    first = levels[0]
    if kind == 'terminal':
        p['commands'] = [dict(command=x['command'], logs=x.get('logs', [])) for x in levels]
    else:
        p['title'] = first.get('title') or app['name']
        if kind == 'window':
            p.update(logs=first.get('list', []), button_labels=[x['label'] for x in first['buttons']])
        elif kind == 'button_choices':
            p.update(prompt=first.get('text', ''), option_labels=[x['label'] for x in first['options']])
        else:
            p.update({key: first.get(key, [] if key == 'steps' else '')
                      for key in ('steps', 'result_success', 'result_failure')})
    validate_presentation(kind, p)
    version = app.get('version') or 1
    if type(version) is not int or version < 1:
        raise ValueError('invalid_version')
    contract = dict(interface=kind, price=app['price'], action='legacy',
                    legacy=True, source_hash=digest(app))
    if kind == 'button_choices':
        contract['options'] = [dict(effect=x.get('effect', {}), price=x.get('price', 0)) for x in first['options']]
    return dict(id='crp_' + digest([app['creator_username'], app['id']])[:32],
        app_id=app['id'], owner=app['creator_username'], revision=1, version=version,
        created_at=now(), contract=contract, presentation=p,
        legacy_snapshot=copy.deepcopy(app), legacy_project_file=app['project_file'])


def build(project, version):
    app = copy.deepcopy(project['legacy_snapshot'])
    p, kind = project['presentation'], project['contract']['interface']
    for key in ('name', 'icon', 'description'):
        app[key] = p[key]
    if kind == 'terminal':
        if len(p['commands']) != len(app['levels']):
            raise ValueError('Nie mozna zmieniac liczby historycznych etapow.')
        for level, command in zip(app['levels'], p['commands']):
            level.update(command=command['command'], logs=command['logs'])
    else:
        level = app['levels'][0]
        level['title'] = p['title']
        if kind == 'window':
            level['list'] = p['logs']
            for button, label in zip(level['buttons'], p['button_labels']):
                button['label'] = label
        elif kind == 'button_choices':
            level['text'] = p['prompt']
            for option, label in zip(level['options'], p['option_labels']):
                option['label'] = label
        else:
            for key in ('steps', 'result_success', 'result_failure'):
                level[key] = p[key]
    app.update(version=version, creator_project_id=project['id'], creator_legacy_project=True, published=True)
    return app


def adopt(store, apps, owners, apply=False):
    import sqlite3
    from pathlib import Path
    from contextlib import closing
    results = []
    owners = set(owners)
    if not owners:
        raise ValueError('Wymagana jawna lista autorow.')
    for app in apps:
        if app.get('creator_username') not in owners or not app.get('generated') or app.get('ghostlab_generated') or app.get('creator_contract_version'):
            continue
        try:
            if sum(x.get('id') == app.get('id') for x in apps) != 1 or sum(
                    x.get('creator_username') == app.get('creator_username') and x.get('project_file') == app.get('project_file')
                    for x in apps) != 1:
                raise ValueError('ambiguous_project_identity')
            project = project_from_app(app)
        except (ValueError, KeyError, TypeError) as error:
            results.append(dict(id=app.get('id'), status='review', reason=str(error)))
            continue
        with (db_connect(store.db_path) if apply else closing(sqlite3.connect(
                Path(store.db_path).resolve().as_uri() + '?mode=ro', uri=True))) as conn:
            conn.row_factory = sqlite3.Row
            if apply:
                conn.execute('BEGIN IMMEDIATE')
            previous = conn.execute('SELECT project_json FROM creator_projects WHERE id=?', (project['id'],)).fetchone()
            if previous:
                import json
                old = json.loads(previous[0])
                if old['contract']['source_hash'] != project['contract']['source_hash'] and not (
                        app.get('creator_legacy_project') and app.get('creator_project_id') == old['id']):
                    raise ValueError('Zmienione zrodlo migracji: ' + app['id'])
                status = 'already_adopted'
            elif apply:
                conn.execute('INSERT INTO creator_projects VALUES(?,?,?,?,?,?)',
                    (project['id'], project['owner'], 'legacy:' + project['app_id'], digest(app), 1, encoded(project)))
                conn.execute('INSERT INTO creator_editions VALUES(?,?,?,?)',
                    (project['id'], project['version'], 1, encoded(app)))
                status = 'adopted'
            else:
                status = 'ready'
        results.append(dict(id=app['id'], project_id=project['id'], status=status))
    return results
