"""Canonical GhostLab projects. No user profile reads or writes in runtime."""
import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone

from database import DB_PATH, db_connect
from config import GHOSTLAB_MAX_PROJECTS, GHOSTLAB_MAX_BUILDS, GHOSTLAB_VISIBLE_BUILD_HISTORY
from ghostlab_registry import template_available, artifact_compatible


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode('utf-8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


class GhostLabError(ValueError):
    def __init__(self, reason, message, status=409):
        super().__init__(message)
        self.reason, self.status = reason, status


class GhostLabStore:
    MAX_PROJECTS = GHOSTLAB_MAX_PROJECTS
    MAX_BUILDS = GHOSTLAB_MAX_BUILDS  # Never evict published/installed artifacts implicitly.

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('CREATE TABLE IF NOT EXISTS ghostlab_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_migrations (
                owner TEXT PRIMARY KEY, status TEXT NOT NULL, source_hash TEXT, updated_at TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_projects (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, app_id TEXT NOT NULL UNIQUE,
                revision INTEGER NOT NULL, project_json TEXT NOT NULL,
                deleted INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)''')
            conn.execute('CREATE INDEX IF NOT EXISTS ghostlab_owner ON ghostlab_projects(owner, deleted, id)')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_builds (
                project_id TEXT NOT NULL, version INTEGER NOT NULL, artifact_id TEXT NOT NULL UNIQUE,
                revision INTEGER NOT NULL, input_hash TEXT NOT NULL, artifact_json TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(project_id, version))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_requests (
                owner TEXT NOT NULL, request_id TEXT NOT NULL, input_hash TEXT NOT NULL,
                project_id TEXT NOT NULL, PRIMARY KEY(owner, request_id))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_publications (
                app_id TEXT PRIMARY KEY, owner TEXT NOT NULL, artifact_id TEXT NOT NULL,
                app_json TEXT NOT NULL, updated_at TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS ghostlab_legacy_ids (
                owner TEXT NOT NULL, legacy_id TEXT NOT NULL, project_id TEXT NOT NULL,
                PRIMARY KEY(owner, legacy_id))''')
            conn.execute("CREATE INDEX IF NOT EXISTS ghostlab_template_page ON ghostlab_publications(json_extract(app_json,'$.template_id'),app_id)")
            first = conn.execute("INSERT OR IGNORE INTO ghostlab_meta VALUES ('initialized', ?)", (now(),)).rowcount
            if first:
                # Bounded identity columns only. Existing accounts must be migrated offline.
                conn.execute("""INSERT OR IGNORE INTO ghostlab_migrations(owner,status,updated_at)
                    SELECT username,'required',? FROM users""", (now(),))

    def ready(self, conn, owner):
        row = conn.execute('SELECT status FROM ghostlab_migrations WHERE owner=?', (owner,)).fetchone()
        if row and row['status'] != 'complete':
            raise GhostLabError('ghostlab_migration_required', 'GhostLab wymaga migracji projektow przez administratora.')

    def _get(self, conn, owner, project_id, include_deleted=False):
        row = conn.execute('SELECT * FROM ghostlab_projects WHERE id=? AND owner=?', (project_id, owner)).fetchone()
        if not row or (row['deleted'] and not include_deleted):
            raise GhostLabError('project_not_found', 'Nie znaleziono projektu.', 404)
        project = json.loads(row['project_json'])
        project.update(id=row['id'], owner=owner, revision=row['revision'], googleplex_app_id=row['app_id'])
        return project

    @staticmethod
    def check_revision(project, revision):
        if type(revision) is not int or revision != project['revision']:
            raise GhostLabError('project_revision_conflict', 'Projekt zmienil sie. Odswiez liste i otworz ponownie.')

    def _save(self, conn, project):
        conn.execute('UPDATE ghostlab_projects SET revision=?,project_json=?,updated_at=? WHERE id=? AND owner=?',
                     (project['revision'], encoded(project), now(), project['id'], project['owner']))

    def list(self, owner):
        with db_connect(self.db_path) as conn:
            self.ready(conn, owner)
            rows = conn.execute('SELECT project_json FROM ghostlab_projects WHERE owner=? AND deleted=0 ORDER BY id LIMIT ?',
                                (owner, self.MAX_PROJECTS + 1)).fetchall()
            if len(rows) > self.MAX_PROJECTS:
                raise GhostLabError('project_limit', 'Przekroczono limit projektow.')
            return [json.loads(row['project_json']) for row in rows]

    def get(self, owner, project_id):
        with db_connect(self.db_path) as conn:
            self.ready(conn, owner)
            return self._get(conn, owner, project_id)

    def create(self, owner, seed, request_id):
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 100:
            raise GhostLabError('request_id_required', 'Brak identyfikatora utworzenia projektu.', 400)
        signature = digest(seed)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            receipt = conn.execute('SELECT * FROM ghostlab_requests WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
            if receipt:
                if receipt['input_hash'] != signature:
                    raise GhostLabError('request_id_conflict', 'Identyfikator dotyczy innego projektu.')
                return self._get(conn, owner, receipt['project_id'])
            count = conn.execute('SELECT count(*) FROM ghostlab_projects WHERE owner=? AND deleted=0', (owner,)).fetchone()[0]
            if count >= self.MAX_PROJECTS:
                raise GhostLabError('project_limit', 'Limit 100 projektow. Usun nieuzywane szkice.')
            project_id = 'glp_' + uuid.uuid4().hex
            project = dict(seed, id=project_id, owner=owner, schema_version=1, revision=1,
                           googleplex_app_id='ghostlab_' + uuid.uuid4().hex, builds=[], artifact={},
                           status='draft', created_at=now(), updated_at=now())
            conn.execute('INSERT INTO ghostlab_projects(id,owner,app_id,revision,project_json,updated_at) VALUES(?,?,?,?,?,?)',
                         (project_id, owner, project['googleplex_app_id'], 1, encoded(project), now()))
            conn.execute('INSERT INTO ghostlab_requests VALUES(?,?,?,?)', (owner, request_id, signature, project_id))
            return project

    def update(self, owner, project_id, revision, changes):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            project = self._get(conn, owner, project_id)
            # A retry of exactly the accepted edit is harmless; stale different edits fail.
            if all(project.get(k) == v for k, v in changes.items()):
                return project
            self.check_revision(project, revision)
            project.update(copy.deepcopy(changes))
            project.update(revision=project['revision'] + 1, status='draft', updated_at=now())
            self._save(conn, project)
            return project

    def compile(self, owner, project_id, revision, blueprint, build):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            project = self._get(conn, owner, project_id)
            self.check_revision(project, revision)
            if project['blueprint'] != blueprint:
                raise GhostLabError('unsaved_blueprint', 'Zapisz blueprint przed kompilacja.')
            if (project.get('artifact', {}).get('source_revision') == revision
                    and artifact_compatible(project['artifact'], project.get('template_id'))):
                return project
            version = conn.execute('SELECT coalesce(max(version),0)+1 FROM ghostlab_builds WHERE project_id=?', (project_id,)).fetchone()[0]
            if version > self.MAX_BUILDS:
                raise GhostLabError('build_limit', 'Limit historii buildow; archiwizacja wymaga administratora.')
            artifact = build(project, blueprint, version)
            artifact.update(source_revision=revision, input_hash=digest(blueprint))
            artifact.setdefault('schema_version', 1)
            artifact.setdefault('policy_version', 1)
            conn.execute('INSERT INTO ghostlab_builds(project_id,version,artifact_id,revision,input_hash,artifact_json) VALUES(?,?,?,?,?,?)',
                         (project_id, version, artifact['artifact_id'], revision, artifact['input_hash'], encoded(artifact)))
            project['artifact'] = artifact
            project['builds'] = (project.get('builds', []) + [{'version': version, 'compiled_at': artifact['compiled_at'],
                                  'artifact_id': artifact['artifact_id'], 'status': 'compiled'}])[-GHOSTLAB_VISIBLE_BUILD_HISTORY:]
            project.update(status='compiled', updated_at=now())
            self._save(conn, project)
            return project

    def publish(self, owner, project_id, revision, artifact_id, builder, author):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            project = self._get(conn, owner, project_id)
            if not template_available(project.get('template_id'), 'publication'):
                raise GhostLabError('template_publication_disabled', 'Publikacja tego szablonu jest wylaczona.')
            self.check_revision(project, revision)
            artifact = project.get('artifact') or {}
            if (not artifact_id or artifact.get('artifact_id') != artifact_id
                    or artifact.get('source_revision') != revision
                    or artifact.get('input_hash') != digest(project['blueprint'])):
                raise GhostLabError('build_stale', 'Zapisz i skompiluj aktualna rewizje przed publikacja.')
            row = conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE project_id=? AND artifact_id=?', (project_id, artifact_id)).fetchone()
            if not row or json.loads(row['artifact_json']) != artifact:
                raise GhostLabError('artifact_mismatch', 'Niezgodny artefakt.')
            app = builder(project, owner, author)
            resource = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
            catalog = json.loads(resource['value_json']) if resource else []
            previous = next((a for a in catalog if a.get('id') == app['id']), None)
            if previous and (previous.get('creator_username') != owner or not previous.get('ghostlab_generated')):
                raise GhostLabError('publication_owner_conflict', 'Istniejaca publikacja nie nalezy do autora.')
            if any(a.get('id') != app['id'] and str(a.get('name', '')).strip().casefold() == app['name'].strip().casefold() for a in catalog):
                raise GhostLabError('publication_name_conflict', 'Nazwa jest juz zajeta w Googleplex.')
            if previous and project.get('published_artifact_id') == artifact_id and project.get('status') == 'published':
                return project, previous
            app['downloads'] = (previous or {}).get('downloads', 0)
            catalog = [app if a.get('id') == app['id'] else a for a in catalog]
            if previous is None:
                catalog.append(app)
            conn.execute("""INSERT INTO json_resources(key,source_path,value_json,updated_at) VALUES('app_config','',?,?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""", (encoded(catalog), now()))
            conn.execute('''INSERT INTO ghostlab_publications VALUES(?,?,?,?,?)
                ON CONFLICT(app_id) DO UPDATE SET artifact_id=excluded.artifact_id,
                app_json=excluded.app_json,updated_at=excluded.updated_at''',
                         (app['id'], owner, artifact_id, encoded(app), now()))
            conn.execute('UPDATE ghostlab_builds SET published=1 WHERE project_id=? AND artifact_id=?', (project_id, artifact_id))
            project.update(status='published', published_artifact_id=artifact_id, published_at=now(), updated_at=now())
            self._save(conn, project)
            return project, app

    def withdraw(self, owner, project_id, revision):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            project = self._get(conn, owner, project_id)
            self.check_revision(project, revision)
            row = conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()
            catalog = json.loads(row['value_json']) if row else []
            app = next((a for a in catalog if a.get('id') == project['googleplex_app_id']), None)
            if not app or app.get('creator_username') != owner or not app.get('ghostlab_generated'):
                raise GhostLabError('publication_owner_conflict', 'Brak publikacji autora.')
            app['published'] = False
            conn.execute("UPDATE json_resources SET value_json=?,updated_at=? WHERE key='app_config'", (encoded(catalog), now()))
            conn.execute('''INSERT INTO ghostlab_publications VALUES(?,?,?,?,?) ON CONFLICT(app_id)
                DO UPDATE SET app_json=excluded.app_json,updated_at=excluded.updated_at''',
                         (app['id'], owner, app.get('artifact_id','legacy'), encoded(app), now()))
            project.update(status='withdrawn', updated_at=now())
            self._save(conn, project)
            return project

    def delete(self, owner, project_id, revision):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.ready(conn, owner)
            project = self._get(conn, owner, project_id, include_deleted=True)
            self.check_revision(project, revision)
            if project.get('published_artifact_id') or project.get('published_at'):
                raise GhostLabError('published_project_retained', 'Opublikowany projekt pozostaje archiwum zakupionych wersji.')
            conn.execute('UPDATE ghostlab_projects SET deleted=1 WHERE id=? AND owner=?', (project_id, owner))
