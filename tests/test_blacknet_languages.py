import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from ghostnetwork.signal_language import resolve, pin, SignalLanguageError
from tools.blacknet_language_migrate import run as migrate


class BlacknetLanguagesTest(unittest.TestCase):
    def test_actual_signal_to_task_keeps_source_locale_and_replays(self):
        import run
        from datetime import datetime, timezone, timedelta
        from types import SimpleNamespace
        from ghostnetwork.repository import GhostNetworkRepository
        from ghostnetwork.producers import BlackNetNarrativeProducer
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory)/'game.db')
            repo = GhostNetworkRepository(db_path=path)
            migrate(path, 'migrate', True)
            now = datetime.now(timezone.utc)
            fact = dict(fact_id='bnf:radio:test', fact_type='radio_channels_available',
                category='Polska audycja', value=1, expires_at=(now+timedelta(hours=1)).isoformat(),
                metadata=dict(channel_id='pl-channel', track_file='one.mp3', channel_language='pl', track_language='pl', tracks_total=9))
            with patch.object(run, 'user_store', SimpleNamespace(db_path=path)), patch.dict(os.environ,
                    CHAOS_BLACKNET_LANGUAGES_ENABLED='1', CHAOS_NARRATIVE_LOCALES='en,pl'):
                signal = run.blacknet_signal_from_fact(fact, now)
                self.assertEqual(signal['output_locale'], 'pl')
                producer = BlackNetNarrativeProducer(repo)
                first = producer.enqueue_signal({'version':'v1'}, signal)
                second = producer.enqueue_signal({'version':'v1'}, signal)
                self.assertEqual(first['task']['outbox_id'], second['task']['outbox_id'])
                self.assertEqual(first['task']['validation']['language_contract']['output_locale'], 'pl')
                self.assertEqual(first['task']['validation']['source_language_contract']['source_type'], 'radio')
                # Another recording in this same slot may have a different source language.
                fact['metadata'].update(channel_id='en-channel', track_file='two.mp3', channel_language='en', track_language='en')
                next_signal = run.blacknet_signal_from_fact(fact, now)
                self.assertEqual(next_signal['output_locale'], 'en')
                self.assertEqual(next_signal['id'], signal['id'])

    def test_new_presentation_decorates_once_without_weakening_references(self):
        from tools.narrative_locale_canary import package_for
        from ghostnetwork.ollama_policy import parse_and_validate_ollama_content
        with patch.dict(os.environ, CHAOS_BLACKNET_LANGUAGES_ENABLED='1'):
            package = package_for('en', 'blacknet')
        self.assertEqual(package['language_contract']['presentation'], 'blacknet-prefix-v1')
        content = dict(title='Hidden node near Canary Station',
            body='A previously concealed network component has surfaced near Canary Station.',
            tone='warning', fact_refs=['f01'], cta_ref=None)
        result = parse_and_validate_ollama_content(json.dumps(content), package)
        self.assertNotIn('voice_title_prefix_mismatch', result['errors'])
        self.assertNotIn('voice_body_prefix_mismatch', result['errors'])
        content['fact_refs'] = ['invented']
        invalid = parse_and_validate_ollama_content(json.dumps(content), package)
        self.assertEqual(invalid['status'], 'quarantined')

    def test_sources_and_unknown_are_not_any(self):
        for locale in ('pl', 'en'):
            for track in (locale, 'neutral'):
                result = resolve('radio', dict(channel_id='r', track_file='a.mp3',
                    channel_language=locale, track_language=track), enabled=('pl', 'en'))
                self.assertEqual(result['output_locale'], locale)
            result = resolve('product', dict(product_id='x', signal_language=locale), enabled=('pl','en'))
            self.assertEqual(result['output_locale'], locale)
        for metadata in (
            dict(product_id='x'),
            dict(channel_id='r', track_file='a.mp3', channel_language='pl', track_language='en'),
            dict(channel_id='r', track_file='a.mp3', channel_language='unknown', track_language='unknown'),
            dict(product_id='x', signal_language='xx')):
            with self.assertRaises(SignalLanguageError):
                resolve('x', metadata, enabled=('pl', 'en'))
        with self.assertRaisesRegex(SignalLanguageError, 'not_enabled'):
            resolve('x', {'product_id':'x', 'signal_language':'en'}, enabled=('pl',))

    def test_rotation_and_pinning_survive_pool_change_and_concurrency(self):
        locales = {resolve(str(i), {}, enabled=('pl','en'))['output_locale'] for i in range(100)}
        self.assertEqual(locales, {'pl','en'})
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory)/'game.db')
            sqlite3.connect(path).close()
            self.assertFalse(migrate(path, 'migrate')['ledger_exists'])
            migrate(path, 'migrate', True)
            with patch.dict(os.environ, CHAOS_NARRATIVE_LOCALES='pl,en'):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    values = list(pool.map(lambda _: pin(path, 'one-event', {}), range(8)))
            self.assertTrue(all(value == values[0] for value in values))
            with patch.dict(os.environ, CHAOS_NARRATIVE_LOCALES='pl'):
                self.assertEqual(pin(path, 'one-event', {}), values[0])
            self.assertEqual(migrate(path, 'check')['pinned_signals'], 1)
            with self.assertRaisesRegex(ValueError, 'ledger_in_use'):
                migrate(path, 'rollback', True)

    def test_all_rule_descriptors_have_pl_en(self):
        import run
        from ghostnetwork.blacknet_copy import descriptors, render
        for fact_type, rule in run.BLACKNET_SIGNAL_RULES.items():
            fact = {'fact_type': fact_type, 'category': 'ATM', 'metadata': {'product_name': 'Mój produkt <keep>', 'target_label': 'Canary Station'}}
            copy = descriptors(fact, rule, 2)
            for locale in ('pl', 'en'):
                texts = render(copy, locale)
                self.assertEqual(set(texts), {'title', 'channel', 'label', 'stat'})
                self.assertTrue(all(texts.values()))
            if fact_type == 'radio_channels_available':
                self.assertEqual(render(copy, 'en')['label'], 'CHANNELS ONLINE')
            if fact_type == 'googleplex_product_signal':
                self.assertIn('Mój produkt <keep>', render(copy, 'en')['title'])
