"""Bounded creator projects and immutable editions, separate from player profiles."""
import json
import uuid

from creator_messages import CreatorValidationError, presentation_defaults
from ghost_i18n import normalize_locale
import config
from database import db_connect
from ghostlab_store import GhostLabError, encoded, digest, now
from creator_policy import generate_contract, validate_presentation, configure_draft, parse_effect


class CreatorStore:
    ACTIVE_PROJECT = """COALESCE(json_extract(project_json,'$.withdrawn'),0)=0 AND NOT EXISTS (SELECT 1 FROM creator_publications p
        WHERE p.owner=creator_projects.owner
        AND p.app_id=json_extract(creator_projects.project_json,'$.app_id')
        AND json_extract(p.app_json,'$.published')=0)"""
    def __init__(self, db_path):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS creator_projects (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, request_id TEXT NOT NULL,
                input_hash TEXT NOT NULL, revision INTEGER NOT NULL, project_json TEXT NOT NULL,
                UNIQUE(owner,request_id))''')
            conn.execute('CREATE INDEX IF NOT EXISTS creator_owner ON creator_projects(owner,id)')
            conn.execute('''CREATE TABLE IF NOT EXISTS wallet_holds (
                receipt_key TEXT PRIMARY KEY, username TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>0))''')
            conn.execute('CREATE INDEX IF NOT EXISTS wallet_hold_owner ON wallet_holds(username)')
            conn.execute('''CREATE TABLE IF NOT EXISTS creator_option_pending (
                receipt_key TEXT PRIMARY KEY, username TEXT NOT NULL, recipient TEXT NOT NULL,
                amount INTEGER NOT NULL, operations_json TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS creator_option_receipts (
                receipt_key TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                response_json TEXT NOT NULL, status_code INTEGER NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS creator_editions (
                project_id TEXT NOT NULL, version INTEGER NOT NULL, revision INTEGER NOT NULL,
                app_json TEXT NOT NULL, PRIMARY KEY(project_id,version), UNIQUE(project_id,revision))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS creator_publications (
                app_id TEXT PRIMARY KEY, owner TEXT NOT NULL, project_file TEXT NOT NULL,
                app_json TEXT NOT NULL)''')
            conn.execute('CREATE INDEX IF NOT EXISTS creator_publication_owner ON creator_publications(owner,project_file)')

    def _get(self, conn, owner, project_id):
        row = conn.execute('SELECT project_json FROM creator_projects WHERE owner=? AND id=? AND ' + self.ACTIVE_PROJECT,
                           (owner, project_id)).fetchone()
        if not row:
            raise GhostLabError('project_not_found', 'Brak projektu autora.', 404)
        return json.loads(row[0])

    def get(self, owner, project_id):
        with db_connect(self.db_path) as conn:
            return self._get(conn, owner, project_id)

    def list(self, owner, after=''):
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT id, revision,
                json_extract(project_json,'$.app_id') AS app_id,
                json_extract(project_json,'$.presentation.name') AS name,
                json_extract(project_json,'$.presentation.icon') AS icon,
                json_extract(project_json,'$.contract.interface') AS interface,
                json_extract(project_json,'$.version') AS version
                FROM creator_projects WHERE owner=? AND id>? AND ''' + self.ACTIVE_PROJECT + ' ORDER BY id LIMIT 100',
                (owner, after)).fetchall()
        return [dict(row) for row in rows]

    def create(self, owner, data, request_id, level, rng=None, quote=None, locale='pl'):
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
            raise CreatorValidationError('request_id', 'Wymagany identyfikator generacji (8–128 znakow).')
        signature = digest(data)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            previous = conn.execute('SELECT id,input_hash FROM creator_projects WHERE owner=? AND request_id=?',
                                    (owner, request_id)).fetchone()
            if previous:
                if previous['input_hash'] != signature:
                    raise GhostLabError('request_conflict', 'Ten identyfikator nalezy do innej generacji.')
                return self._get(conn, owner, previous['id'])
            if conn.execute('SELECT count(*) FROM creator_projects WHERE owner=? AND ' + self.ACTIVE_PROJECT, (owner,)).fetchone()[0] >= config.CREATOR_MAX_PROJECTS:
                raise GhostLabError('project_limit', 'Osiagnieto limit projektow.')
            contract = generate_contract(data, level, rng)
            if quote is not None:
                contract['price'] = quote(contract, data.get('price'))
            project_id = 'crp_' + uuid.uuid4().hex
            project = dict(id=project_id, app_id='creator_' + uuid.uuid4().hex, owner=owner,
                revision=1, version=0, created_at=now(), contract=contract, presentation_locale=normalize_locale(locale),
                presentation=validate_presentation(contract['interface'], {
                    **presentation_defaults(contract['interface'], locale), 'name':data['name'], 'icon':data['icon']}))
            conn.execute('INSERT INTO creator_projects VALUES(?,?,?,?,?,?)',
                         (project_id, owner, request_id, signature, 1, encoded(project)))
            return project

    def update(self, owner, project_id, revision, presentation):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = self._get(conn, owner, project_id)
            if type(revision) is not int or project['revision'] != revision:
                raise GhostLabError('revision_conflict', 'Projekt zmienil sie. Odswiez edytor.')
            changes = validate_presentation(project['contract']['interface'], presentation)
            if project.get('legacy_snapshot') and 'commands' in changes:
                if len(changes['commands']) != len(project['presentation']['commands']):
                    raise CreatorValidationError('legacy_steps', 'Nie mozna zmieniac liczby historycznych etapow.')
            if project['version']:
                for key in ('button_labels', 'option_labels'):
                    if key in changes and len(changes[key]) != len(project['presentation'].get(key, ['Uruchom'])):
                        raise CreatorValidationError('published_actions', 'Po publikacji nie mozna dodawac ani usuwac akcji.')
            project['presentation'].update(changes)
            project['revision'] += 1
            conn.execute('UPDATE creator_projects SET revision=?,project_json=? WHERE id=?',
                         (project['revision'], encoded(project), project_id))
            return project

    def configure(self, owner, project_id, revision, changes, level):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = self._get(conn, owner, project_id)
            if type(revision) is not int or project['revision'] != revision:
                raise GhostLabError('revision_conflict', 'Projekt zmienil sie.')
            if project['version']:
                raise GhostLabError('mechanics_frozen', 'Opublikowana mechanika i ceny sa niezmienne.')
            project['contract'] = configure_draft(project['contract'], changes, level)
            project['revision'] += 1
            conn.execute('UPDATE creator_projects SET revision=?,project_json=? WHERE id=?',
                         (project['revision'], encoded(project), project_id))
            return project

    def publish(self, owner, project_id, revision, builder, reserved_names=()):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = self._get(conn, owner, project_id)
            if type(revision) is not int or project['revision'] != revision:
                raise GhostLabError('revision_conflict', 'Projekt zmienil sie.')
            from creator_policy import fileless_data_operation
            contract = project['contract']
            if fileless_data_operation({'creator_contract_version': contract.get('policy_version'), 'creator_contract': contract}):
                effects = ([option.get('effect') for option in contract['options']]
                           if 'options' in contract else [contract.get('effect')])
                if not effects or not all(effects):
                    raise CreatorValidationError('file_required', 'Ta aplikacja zbiera dane, ale ma wyłączone tworzenie pliku. Utwórz nowe narzędzie z opcją Tworzy plik: TAK albo skonfiguruj effect dla każdej opcji Button Choice.')
            previous = conn.execute('SELECT app_json FROM creator_editions WHERE project_id=? AND revision=?',
                                    (project_id, revision)).fetchone()
            if previous:
                edition = json.loads(previous[0])
                if project.get('legacy_snapshot'):
                    edition['version'] = edition.get('version') or project['version']
                return edition
            if project['version'] >= config.CREATOR_MAX_VERSIONS:
                raise GhostLabError('version_limit', 'Osiagnieto limit wydan.')
            version = project['version'] + 1
            parse_effect(project['contract'].get('effect'))
            for index, option in enumerate([] if project.get('legacy_snapshot') else project['contract'].get('options', [])):
                try:
                    parse_effect(option.get('effect'))
                except CreatorValidationError as error:
                    raise error.in_option(index + 1)
            app = builder(project, version)
            if app.get('id') != project['app_id'] or app.get('creator_username') != owner:
                raise CreatorValidationError('identity', 'Niezgodna tozsamosc produktu.')
            if app['name'].strip().casefold() in {str(name).strip().casefold() for name in reserved_names}:
                raise GhostLabError('name_conflict', 'Aplikacja o takiej nazwie juz istnieje.')
            self._publish(conn, owner, app)
            conn.execute('INSERT INTO creator_editions VALUES(?,?,?,?)',
                         (project_id, version, revision, encoded(app)))
            project['version'] = version
            conn.execute('UPDATE creator_projects SET project_json=? WHERE id=?', (encoded(project), project_id))
            return app

    def _publish(self, conn, owner, app):
        # SQLite lower() only folds ASCII; terminal names can contain Polish text.
        for row in conn.execute("SELECT app_id,owner,json_extract(app_json,'$.name') AS name FROM creator_publications"):
            if row['app_id'] == app['id']:
                if row['owner'] != owner:
                    raise GhostLabError('publication_owner_conflict', 'Produkt nalezy do innego autora.')
            elif str(row['name']).strip().casefold() == app['name'].strip().casefold():
                raise GhostLabError('name_conflict', 'Aplikacja o takiej nazwie juz istnieje.')
        conn.execute('''INSERT INTO creator_publications VALUES(?,?,?,?)
            ON CONFLICT(app_id) DO UPDATE SET app_json=excluded.app_json, project_file=excluded.project_file''',
            (app['id'], owner, app['project_file'], encoded(app)))

    def publish_legacy(self, owner, app):
        """Compatibility publication without touching files/projects in a profile."""
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conflict = conn.execute('''SELECT app_id FROM creator_publications
                WHERE lower(json_extract(app_json,'$.name'))=lower(?)''', (app['name'],)).fetchone()
            if conflict:
                raise GhostLabError('name_conflict', 'Aplikacja o takiej nazwie juz istnieje.')
            self._publish(conn, owner, app)

    def catalog(self):
        with db_connect(self.db_path) as conn:
            return [json.loads(row[0]) for row in conn.execute('SELECT app_json FROM creator_publications')]

    def files(self, owner):
        with db_connect(self.db_path) as conn:
            return [row[0] for row in conn.execute('''SELECT project_file FROM creator_publications
                WHERE owner=? AND json_extract(app_json,'$.published')=1 LIMIT ?''',
                                                  (owner, config.CREATOR_MAX_PROJECTS))]

    def project_files(self, owner):
        with db_connect(self.db_path) as conn:
            return [row[0] for row in conn.execute(
                "SELECT COALESCE(json_extract(project_json,'$.legacy_project_file'),id || '.sh') FROM creator_projects WHERE owner=? AND " + self.ACTIVE_PROJECT + " ORDER BY id LIMIT ?",
                (owner, config.CREATOR_MAX_PROJECTS))]

    def project_file_metadata(self, owner):
        with db_connect(self.db_path) as conn:
            rows = conn.execute("""SELECT
                COALESCE(json_extract(project_json,'$.legacy_project_file'),id || '.sh') AS filename,
                json_extract(project_json,'$.presentation.name') AS name,
                json_extract(project_json,'$.presentation.icon') AS icon
                FROM creator_projects WHERE owner=? AND """ + self.ACTIVE_PROJECT + " ORDER BY id LIMIT ?",
                (owner, config.CREATOR_MAX_PROJECTS)).fetchall()
        return {row['filename']: {'name': row['name'] + '.sh', 'icon': row['icon']} for row in rows}

    def withdraw(self, owner, project_file, legacy=None):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT app_json FROM creator_publications WHERE owner=? AND project_file=?',
                               (owner, project_file)).fetchone()
            project_row = conn.execute("""SELECT id,project_json FROM creator_projects WHERE owner=?
                AND COALESCE(json_extract(project_json,'$.legacy_project_file'),id || '.sh')=?""",
                (owner, project_file)).fetchone()
            app = json.loads(row[0]) if row else legacy
            if not app and project_row:
                project = json.loads(project_row['project_json'])
                app = dict(id=project['app_id'], name=project['presentation']['name'], creator_username=owner)
            if not app or app.get('creator_username') != owner:
                raise GhostLabError('project_not_found', 'Brak projektu autora.', 404)
            app = dict(app, published=False)
            if row or legacy:
                self._publish(conn, owner, app)
            if project_row:
                project = json.loads(project_row['project_json'])
                project['withdrawn'] = True
                conn.execute('UPDATE creator_projects SET project_json=? WHERE id=?',
                             (encoded(project), project_row['id']))
            return app
