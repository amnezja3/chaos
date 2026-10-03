import copy
import json
import unittest
from creator_legacy import adopt, build, validate_update
from creator_store import CreatorStore
from database import db_connect, GameStateDeltaBus
from tests import test_player_hack_read_paths as fixtures
valid_profile = fixtures.valid_profile


class CreatorLegacyTest(unittest.TestCase):
    setUp = fixtures.PlayerHackReadPathsTest.setUp

    def prepare(self):
        self.users.save_profile(valid_profile('attacker'))
        self.inventory.seed_from_profile('attacker', valid_profile('attacker'))
        self.store = CreatorStore(self.path)
        self.app = dict(id='legacy-xmapper', name='XMapper', icon='X', creator_username='author',
            project_file='XMapper.sh', generated=True, published=True, price=100,
            interface='button_choices', type='exploit', map_actions=['exploit'],
            levels=[dict(title='XMapper', text='Choose', options=[dict(id=0, label='All',
                price=500, effect={'firewall': False, 'legacy_key': False})])])
        self.store.publish_legacy('author', self.app)
        return adopt(self.store, [self.app], ['author'], apply=True)[0]['project_id']

    def test_snapshot_edit_publication_and_free_update(self):
        from creator_updates import update
        project_id = self.prepare()
        original = copy.deepcopy(self.app)
        self.assertEqual(self.store.catalog(), [original])
        self.assertEqual(self.store.publish('author', project_id, 1, build)['version'], 1)
        self.assertEqual(self.store.catalog(), [original])
        self.assertEqual(adopt(self.store, [original], ['author'], apply=True)[0]['status'], 'already_adopted')
        self.inventory.install_app('attacker', original, purchase_key='paid-original')
        old = self.inventory.desktop_apps('attacker')[0]
        project = self.store.update('author', project_id, 1,
            dict(name='XMapper corrected', option_labels=['Hack all'], prompt='New prompt'))
        available = self.store.publish('author', project_id, project['revision'], build)
        self.assertNotIn('creator_contract_version', available)
        self.assertEqual(available['levels'][0]['options'][0]['effect'], original['levels'][0]['options'][0]['effect'])
        self.assertEqual(available['levels'][0]['options'][0]['price'], 500)
        self.assertEqual(self.inventory.desktop_apps('attacker')[0], old)
        with db_connect(self.path) as conn:
            validate_update(conn, old, available)
            validate_update(conn, dict(old, downloads=999), available)
            altered = copy.deepcopy(available)
            altered['levels'][0]['options'][0]['effect']['firewall'] = True
            with self.assertRaises(ValueError): validate_update(conn, old, altered)
            altered = copy.deepcopy(available)
            altered['levels'][0]['options'][0]['effect']['text'] = False
            with self.assertRaises(ValueError): validate_update(conn, old, altered)
        result = update('attacker', original['id'], 1, 2, self.inventory, GameStateDeltaBus(self.path))
        self.assertEqual(result['installed_version'], 2)
        self.assertTrue(update('attacker', original['id'], 1, 2, self.inventory, GameStateDeltaBus(self.path))['duplicate'])
        self.assertEqual(len(self.store.list('author')), 1)
        self.assertEqual(self.store.project_files('author'), ['XMapper.sh'])
        with self.assertRaises(Exception): self.store.configure('author', project_id, project['revision'], {'price': 0}, 100)

    def test_dry_run_and_ambiguous_stage_do_not_mutate(self):
        self.prepare()
        app = dict(self.app, id='other', project_file='other.sh')
        self.assertEqual(adopt(self.store, [app], ['author'])[0]['status'], 'ready')
        self.assertEqual(len(self.store.list('author')), 1)
        app['levels'] = app['levels'] * 2
        self.assertEqual(adopt(self.store, [app], ['author'], apply=True)[0]['status'], 'review')
        self.assertEqual(len(self.store.list('author')), 1)

    def test_replay_does_not_restore_withdrawn_publication(self):
        self.prepare()
        self.store.withdraw('author', 'XMapper.sh')
        adopt(self.store, [self.app], ['author'], apply=True)
        self.assertFalse(self.store.catalog()[0]['published'])

    def test_file_route_checks_owner_and_installed_creator(self):
        import os
        import run
        from unittest.mock import patch
        self.prepare()
        # The authenticated fixture is attacker; use an attacker-owned history.
        app = dict(self.app, id='owned-legacy', creator_username='attacker', project_file='Owned.sh')
        adopt(self.store, [app], ['attacker'], apply=True)
        with patch.object(run, 'creator_store', self.store), patch.dict(os.environ, CHAOS_CREATORS_V2_ENABLED='true'):
            self.assertEqual(self.client.get('/api/creators/project-file?name=Owned.sh').status_code, 403)
            self.inventory.install_app('attacker', dict(id='buttonmaker', name='ButtonMaker'), purchase_key='creator')
            response = self.client.get('/api/creators/project-file?name=Owned.sh')
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['project']['owner'], 'attacker')
            self.assertEqual(self.client.get('/api/creators/project-file?name=XMapper.sh').status_code, 409)
