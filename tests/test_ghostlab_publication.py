import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
import database
from database import db_connect, init_db
from ghostlab_store import GhostLabStore, GhostLabError, encoded, now
from ghostlab_policy import default_ghostlab_blueprint, validate_ghostlab_blueprint
from tools.migrate_ghostlab_projects import migrate_account


class GhostLabPublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'game.sqlite3')
        init_db(self.path)
        self.store = GhostLabStore(self.path)
        self.author = dict(nick='Author', level=40, respect=100, hackcoins=1000)

    def project(self, owner='alice', name='Same name'):
        return self.store.create(owner, dict(name=name, slug='same_name', template_id='system_log_reader',
                 template_name='Logs', tool_category='intel', icon='G',
                 blueprint=default_ghostlab_blueprint('system_log_reader')), 'create-request-' + name)

    def compile(self, p):
        return self.store.compile(p['owner'],p['id'],p['revision'],p['blueprint'],run.build_ghostlab_artifact)

    def publish(self, p):
        return self.store.publish(p['owner'],p['id'],p['revision'],p['artifact']['artifact_id'],
                                  run.build_ghostlab_googleplex_app,self.author)

    def test_owner_identity_retry_and_cas(self):
        a, b = self.project(), self.project('bob')
        self.assertNotEqual(a['googleplex_app_id'],b['googleplex_app_id'])
        self.assertEqual(a['id'],self.project()['id'])
        with self.assertRaises(GhostLabError):
            self.store.get('bob',a['id'])
        self.store.update('alice',a['id'],1,{'name':'New'})
        with self.assertRaises(GhostLabError):
            self.store.update('alice',a['id'],1,{'name':'Stale'})

    def test_stale_build_and_unsaved_blueprint_rejected(self):
        p = self.compile(self.project())
        self.assertEqual(p,self.compile(p))
        edited = dict(p['blueprint'],log_limit=1)
        with self.assertRaises(GhostLabError):
            self.store.compile('alice',p['id'],1,edited,run.build_ghostlab_artifact)
        p = self.store.update('alice',p['id'],1,{'blueprint':edited})
        with self.assertRaises(GhostLabError):
            self.publish(p)
        p = self.compile(p)
        published, app = self.publish(p)
        self.assertEqual(1,app['metadata']['blueprint']['log_limit'])
        self.assertEqual('pending_custom_runtime',app['runtime_status'])
        self.assertEqual((published,app),self.publish(published))

    def test_publish_owner_collision_and_transaction_rollback(self):
        p = self.compile(self.project())
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO json_resources VALUES('app_config','',?,?)",
                         (encoded([dict(id=p['googleplex_app_id'],creator_username='bob',ghostlab_generated=True)]),now()))
        with self.assertRaises(GhostLabError): self.publish(p)
        with db_connect(self.path) as conn:
            conn.execute("DELETE FROM json_resources WHERE key='app_config'")
            conn.execute("""CREATE TRIGGER fail_project BEFORE UPDATE ON ghostlab_projects
                BEGIN SELECT RAISE(ABORT, 'simulated failure'); END""")
        with self.assertRaises(Exception): self.publish(p)
        with db_connect(self.path) as conn:
            self.assertIsNone(conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone())
            self.assertEqual(0,conn.execute('SELECT published FROM ghostlab_builds').fetchone()[0])

    def test_concurrent_publish_preserves_both(self):
        projects = [self.compile(self.project('alice','A')),self.compile(self.project('bob','B'))]
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(self.publish,projects))
        with db_connect(self.path) as conn:
            apps = json.loads(conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()[0])
        self.assertEqual({'A','B'},{a['name'] for a in apps})

    def test_legacy_catalog_writer_cannot_revert_publication_or_withdrawal(self):
        resources = database.JsonResourceStore(self.path)
        stale = resources.get('app_config',default=[])
        p, app = self.publish(self.compile(self.project()))
        resources.set('app_config',stale)
        self.assertIn(app['id'],{a['id'] for a in resources.get('app_config')})
        stale = resources.get('app_config')
        p = self.store.withdraw('alice',p['id'],p['revision'])
        resources.set('app_config',stale)
        self.assertFalse(next(a for a in resources.get('app_config') if a['id']==app['id'])['published'])
        self.assertEqual('withdrawn',p['status'])
        p, republished = self.publish(p)
        self.assertTrue(republished['published'])

    def test_schema_rejects_untrusted_values(self):
        for template in ['financial_sniffer','friend_kicker','security_panel_proxy','system_log_reader','arsenal_cleaner']:
            bp = default_ghostlab_blueprint(template)
            self.assertTrue(validate_ghostlab_blueprint(template,bp)['valid'])
            self.assertFalse(validate_ghostlab_blueprint(template,dict(bp,extra=True))['valid'])
        for value in [True,float('nan'),float('inf'),0,6,1.5]:
            self.assertFalse(validate_ghostlab_blueprint('system_log_reader',dict(default_ghostlab_blueprint('system_log_reader'),log_limit=value))['valid'])
        bp = default_ghostlab_blueprint('arsenal_cleaner'); bp['protected_apps']='none'
        self.assertFalse(validate_ghostlab_blueprint('arsenal_cleaner',bp)['valid'])

    def test_published_delete_preserves_evidence(self):
        p,_ = self.publish(self.compile(self.project()))
        with self.assertRaises(GhostLabError): self.store.delete('alice',p['id'],p['revision'])
        draft = self.project('bob')
        self.store.delete('bob',draft['id'],1)
        self.assertEqual([],self.store.list('bob'))

    def test_migration_dry_run_idempotency_and_ownership(self):
        legacy = dict(id='legacy1',name='Legacy',slug='legacy',template_id='system_log_reader',
                      blueprint=default_ghostlab_blueprint('system_log_reader'),builds=[],artifact={})
        with db_connect(self.path) as conn:
            conn.execute('INSERT INTO users(username,profile_json,created_at,updated_at) VALUES(?,?,?,?)',
                         ('old',encoded({'files':{'pro_system_projects':[legacy]},'untouched':123}),now(),now()))
            conn.execute("INSERT INTO ghostlab_migrations VALUES('old','required',NULL,?)",(now(),))
            before = conn.execute("SELECT profile_json FROM users WHERE username='old'").fetchone()[0]
            self.assertEqual('would_migrate',migrate_account(conn,'old')['status'])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM ghostlab_projects').fetchone()[0])
        with self.assertRaises(GhostLabError): self.store.list('old')
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.assertEqual('migrated',migrate_account(conn,'old',True)['status'])
            self.assertEqual('already_migrated',migrate_account(conn,'old',True)['status'])
            self.assertEqual(before,conn.execute("SELECT profile_json FROM users WHERE username='old'").fetchone()[0])
        self.assertEqual(1,len(self.store.list('old')))

    def test_http_path_zero_heavy_profile(self):
        app = run.app
        original_testing = app.testing; app.testing = True
        self.addCleanup(setattr,app,'testing',original_testing)
        client = app.test_client()
        with client.session_transaction() as sess: sess['user']='alice'
        execute = database.InstrumentedConnection.execute
        traced = []
        def guarded(conn,sql,*args,**kwargs):
            lowered = sql.lower()
            if 'profile_json' in lowered or ('select * from users' in lowered):
                raise AssertionError('Heavy profile SQL: ' + sql)
            traced.append(sql)
            return execute(conn,sql,*args,**kwargs)
        with patch.object(run,'ghostlab_store',self.store), \
             patch.object(run,'sync_session_profile',side_effect=AssertionError('heavy sync')), \
             patch.object(run.user_store,'get_profile',side_effect=AssertionError('heavy read')), \
             patch.object(run.user_store,'save_profile',side_effect=AssertionError('heavy write')), \
             patch.object(run,'UserProfileManager',side_effect=AssertionError('heavy manager')), \
             patch.object(run.identity_projection_store,'get_creator_identity',return_value={'nick':'Alice','respect':10}), \
             patch.object(run.capability_projection_store,'get_capabilities',return_value={'level':40}), \
             patch.object(run.wallet_balance_store,'get_balance',return_value=1000), \
             patch.object(database.InstrumentedConnection,'execute',guarded):
            response = client.post('/api/ghostlab/projects',json=dict(name='HTTP',template_id='system_log_reader',request_id='http-create-1'))
            self.assertEqual(200,response.status_code,response.get_json())
            p = response.get_json()['project']; base='/api/ghostlab/projects/'+p['id']
            self.assertEqual(200,client.get('/api/ghostlab/projects').status_code)
            response=client.post(base+'/compile',json=dict(revision=p['revision'],blueprint=p['blueprint']))
            self.assertEqual(200,response.status_code,response.get_json()); p=response.get_json()['project']
            response=client.post(base+'/publisher',json=dict(revision=p['revision'],artifact_id=p['artifact']['artifact_id']))
            self.assertEqual(200,response.status_code,response.get_json())
            self.assertEqual(200,client.get(base+'/export').status_code)
            self.assertEqual(409,client.patch(base,json=dict(revision=0,name='stale')).status_code)
            self.assertEqual(400,client.patch(base+'/blueprint',json=dict(revision=1,blueprint={'bad':True})).status_code)
            self.assertEqual(409,client.delete(base,json=dict(revision=1)).status_code)
        self.assertTrue(traced)

    def test_real_creator_projection_has_level_and_no_profile_fallback(self):
        profile = dict(username='author',nick='Creator',level=37,respect=456,apps=[],files={},security={})
        with db_connect(self.path) as conn:
            conn.execute('''INSERT INTO users(username,profile_json,created_at,updated_at,
                profile_revision,profile_checksum,profile_integrity_status) VALUES(?,?,?,?,?,?,?)''',
                ('author','{}',now(),now(),1,'checksum',database.PROFILE_INTEGRITY_VALID))
            database._upsert_identity_projection_with_conn(conn,profile,1,'checksum')
        identity = database.UserIdentityProjectionStore(self.path)
        caps = database.UserCapabilityProjectionStore(self.path)
        self.assertEqual({'nick':'Creator','respect':456},identity.get_creator_identity('author'))
        self.assertEqual(37,caps.get_capabilities('author')['level'])
        with db_connect(self.path) as conn:
            conn.execute("UPDATE users SET profile_revision=2 WHERE username='author'")
        with self.assertRaises(database.ProfileRecoveryRequired): identity.get_creator_identity('author')

    def test_migration_preserves_publication_id_and_blocks_wrong_owner(self):
        legacy = dict(id='old-project',name='Existing',template_id='system_log_reader',slug='existing',
                      blueprint=default_ghostlab_blueprint('system_log_reader'),builds=[],artifact={},
                      googleplex_app_id='legacy-app',published_at=now())
        app = dict(id='legacy-app',source_project_id='old-project',creator_username='other',ghostlab_generated=True)
        with db_connect(self.path) as conn:
            conn.execute('INSERT INTO users(username,profile_json,created_at,updated_at) VALUES(?,?,?,?)',
                         ('old',encoded({'files':{'pro_system_projects':[legacy]}}),now(),now()))
            conn.execute("INSERT INTO json_resources VALUES('app_config','',?,?)",(encoded([app]),now()))
            self.assertEqual('blocked',migrate_account(conn,'old',True)['status'])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM ghostlab_projects').fetchone()[0])
            app['creator_username']='old'
            conn.execute("UPDATE json_resources SET value_json=? WHERE key='app_config'",(encoded([app]),))
            before=conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()[0]
            self.assertEqual('migrated',migrate_account(conn,'old',True)['status'])
            self.assertEqual(before,conn.execute("SELECT value_json FROM json_resources WHERE key='app_config'").fetchone()[0])
        migrated=self.store.list('old')[0]
        self.assertEqual('legacy-app',migrated['googleplex_app_id'])
        self.assertEqual({},migrated['artifact'])
        self.assertEqual('old-project',migrated['legacy_id'])


if __name__ == '__main__': unittest.main()
