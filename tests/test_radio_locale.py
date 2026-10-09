import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from radio_locale import matches_filter, track_allowed, track_metadata, validate_contract


class RadioLocaleTest(unittest.TestCase):
    def test_published_inventory_blacknet_confirmed_polish_music_unverified(self):
        root = Path(__file__).resolve().parents[1] / 'static/mp3/radio/channel'
        for channel_id, expected in [('blacknet_radio_2', 'pl'), ('ghost_streem_1', 'unknown')]:
            contract = json.loads((root / channel_id / 'meta.channel').read_text(encoding='utf8'))
            validate_contract(contract)
            self.assertEqual(contract['language'], expected)
            self.assertTrue(contract['programs'])
            self.assertEqual({item['language'] for item in contract['programs'].values()}, {expected})

    def test_filter_matrix_and_unknown_not_neutral(self):
        for selected, expected in [('pl', {'pl', 'neutral'}), ('en', {'en', 'neutral'}),
                                   ('ANY', {'pl', 'en', 'neutral', 'mixed', 'unknown'})]:
            actual = {value for value in ('pl', 'en', 'neutral', 'mixed', 'unknown')
                      if matches_filter({'language': value}, selected)}
            self.assertEqual(actual, expected)
        self.assertFalse(matches_filter({}, 'pl'))
        with self.assertRaises(ValueError):
            matches_filter({}, 'ru')

    def test_program_must_be_explicit_and_compatible(self):
        self.assertEqual(track_metadata({'language': 'pl'}, 'new.mp3'), {'language': 'unknown'})
        for channel, accepted in [('pl', {'pl', 'neutral'}), ('en', {'en', 'neutral'}),
                                  ('neutral', {'neutral'}), ('mixed', {'pl', 'en', 'neutral', 'mixed', 'unknown'})]:
            for program in ('pl', 'en', 'neutral', 'mixed', 'unknown'):
                self.assertEqual(track_allowed({'language': channel}, {'language': program}), program in accepted)

    def test_strict_contract_validation(self):
        valid = {'language': 'pl', 'programs': {'a.mp3': {'language': 'pl'}}}
        self.assertEqual(validate_contract(valid), valid)
        for invalid in ({}, {'language': 'ANY'}, {'language': 'ru'},
                        {'language': 'pl', 'programs': {'a.mp3': {'language': 'en'}}},
                        {'language': 'pl', 'programs': {'../a.mp3': {'language': 'pl'}}}):
            with self.assertRaises(ValueError):
                validate_contract(invalid)

    def test_endpoint_excludes_wrong_language_and_keeps_authored_title(self):
        with tempfile.TemporaryDirectory() as folder:
            channel = Path(folder) / 'mp3/radio/channel/demo'
            channel.mkdir(parents=True)
            (channel / 'meta.channel').write_text(json.dumps({
                'schema': 1, 'language': 'pl', 'name': 'Author EN title',
                'programs': {'OK.mp3': {'language': 'pl'}, 'Other.mp3': {'language': 'en'}}
            }), encoding='utf8')
            for filename in ('OK.mp3', 'Other.mp3', 'Unknown.mp3'):
                (channel / filename).touch()
            with patch.object(run.app, '_static_folder', folder), run.app.test_request_context():
                payload = run.radio_channel_manifest('demo').get_json()
            self.assertEqual(payload['channel']['name'], 'Author EN title')
            self.assertEqual(payload['tracks'], [{'title': 'OK', 'file': 'OK.mp3', 'language': 'pl'}])
