import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from database import JsonResourceStore
from tests.test_player_hack_read_paths import PlayerHackReadPathsTest


class RadioAdminTest(unittest.TestCase):
    setUp = PlayerHackReadPathsTest.setUp

    def test_default_persistence_validation_and_admin_gate(self):
        resource = JsonResourceStore(self.path)
        with tempfile.TemporaryDirectory() as folder:
            for channel in ('ghost_streem_1', 'blacknet_radio_2'):
                directory = Path(folder) / 'mp3' / 'radio' / 'channel' / channel
                directory.mkdir(parents=True)
                (directory / 'meta.channel').write_text(json.dumps({'schema': 1, 'name': channel}), encoding='utf-8')
            with patch.object(run.app, '_static_folder', folder), patch.object(run, 'resources_store', resource), \
                 patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy profile')):
                self.assertEqual(self.client.get('/api/radio/channels').json['default_channel'], 'blacknet_radio_2')
                self.assertEqual(self.client.get('/api/admin/radio').status_code, 403)
                self.assertEqual(self.client.post('/api/admin/radio', json={'autostart_channel':'ghost_streem_1'}).status_code, 403)
                with patch.object(run, 'require_dev_admin', return_value=True):
                    self.assertEqual(self.client.get('/api/admin/radio').status_code, 200)
                    response = self.client.post('/api/admin/radio', json={'autostart_channel':'ghost_streem_1'})
                    self.assertEqual(response.status_code, 200, response.json)
                    self.assertEqual(resource.get('radio_settings')['autostart_channel'], 'ghost_streem_1')
                    self.assertEqual(self.client.get('/api/radio/channels').json['default_channel'], 'ghost_streem_1')
                    for invalid in ('../other', 'missing', ['ghost_streem_1'], None):
                        self.assertEqual(self.client.post('/api/admin/radio', json={'autostart_channel':invalid}).status_code, 400)
                    self.assertEqual(self.client.get('/api/radio/channels').json['default_channel'], 'ghost_streem_1')
