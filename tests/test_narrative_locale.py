import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ghostnetwork.narrative_locale import freeze_language, task_language, english_layers, english_fallback, language_registry
from ghostnetwork.ollama_policy import build_ollama_task_package, parse_and_validate_ollama_content
from ghostnetwork.llm.registry import OLLAMA_TASK_POLICY_REGISTRY
from ghostnetwork.narrative_support import NarrativeSupportLayer
from ghostnetwork.repository import GhostNetworkRepository
import test_narrative_support as support_fixtures


class NarrativeLocaleTest(unittest.TestCase):
    def task(self, **changes):
        return {**support_fixtures.NarrativeSupportLayerTest().task(), **changes}

    def test_every_active_policy_has_both_prompt_layers(self):
        for policy in OLLAMA_TASK_POLICY_REGISTRY.values():
            system, domain = english_layers(policy)
            self.assertIn('English', system)
            self.assertTrue(domain.strip())
            self.assertNotIn('po polsku', system + domain)

    def test_canary_packages_cover_both_languages_and_three_media_without_queue(self):
        from tools.narrative_locale_canary import package_for
        for locale in ('pl','en'):
            for medium in ('blacknet','cyberner','googleplex_news'):
                package=package_for(locale,medium)
                self.assertEqual(package['output_locale'],locale)
                self.assertEqual(package['policy'].target_medium,medium)

    def test_event_instructions_do_not_offer_cross_channel_text_as_headline(self):
        from tools.narrative_locale_canary import package_for
        for locale in ('pl', 'en'):
            package = package_for(locale, 'cyberner')
            instructions = package['messages'][0]['content'].lower()
            self.assertNotIn('blacknet', instructions)
            self.assertNotIn('cyberner', instructions)
            self.assertEqual(package['model_input']['medium'], 'cyberner')

    def test_canary_reports_fallback_as_failure_for_explicit_mistral_probe(self):
        import io
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        from tools.narrative_locale_canary import main
        with tempfile.NamedTemporaryFile() as database:
            for requested, actual, expected in [('mistral','ollama',1),('mistral','mistral',0),('ollama','ollama',0)]:
                with self.subTest(requested=requested, actual=actual), patch('sys.argv',
                        ['canary','--db',database.name,'--locale','en','--provider',requested,'--generate']), patch(
                        'ghostnetwork.llm.router.NarrativeRouter') as router, patch(
                        'ghostnetwork.ollama_policy.parse_and_validate_ollama_content',
                        return_value={'status':'accepted','errors':[]}):
                    router.return_value.config = {'total_seconds': 630}
                    router.return_value.generate.return_value=SimpleNamespace(content='{}',provider=actual,model='test')
                    output=io.StringIO()
                    with redirect_stdout(output):
                        self.assertEqual(main(), expected)
                    report=json.loads(output.getvalue())
                    self.assertFalse(report['published'])
                    self.assertEqual(report['provider'],actual)
                    self.assertEqual(report['generation_budget_seconds'], 630)
                    self.assertEqual(router.return_value.provider,requested)

    def test_bn_canary_enforces_literal_prefix_and_rejects_invented_frequencies(self):
        from tools.narrative_locale_canary import package_for
        package = package_for('en', 'blacknet')
        instruction = package['messages'][0]['content']
        self.assertIn('"body": "..."', instruction)
        output = dict(title='INTERCEPT // Canary Station discovery',
                      body='... A hidden GhostNetwork part was discovered at Canary Station.',
                      tone='warning', fact_refs=list(package['fact_refs']), cta_ref=None)
        self.assertEqual(parse_and_validate_ollama_content(json.dumps(output), package)['status'], 'accepted')
        missing = {**output, 'body':output['body'][4:]}
        self.assertIn('voice_body_prefix_mismatch', parse_and_validate_ollama_content(json.dumps(missing), package)['errors'])
        invented = {**output, 'body':output['body'] + ' A pulse appears in the 1200–1400 MHz band.'}
        self.assertIn('voice_unsupported_number', parse_and_validate_ollama_content(json.dumps(invented), package)['errors'])
        for locale in ('pl', 'en'):
            other = package_for(locale, 'cyberner')
            bad = {**output, 'title':'Canary Station', 'body':'Canary Station: 2108 / 1200 MHz.', 'fact_refs':list(other['fact_refs'])}
            self.assertIn('voice_unsupported_number', parse_and_validate_ollama_content(json.dumps(bad), other)['errors'])

    def test_discovery_is_not_activation_in_either_language_or_medium(self):
        from tools.narrative_locale_canary import package_for
        for locale in ('pl','en'):
            for medium in ('blacknet','cyberner','googleplex_news'):
                package = package_for(locale, medium)
                prefix = ('PRZECHWYT // ' if locale=='pl' else 'INTERCEPT // ') if medium=='blacknet' else ''
                body_prefix = '... ' if medium=='blacknet' else ''
                output = dict(title=prefix+'Canary Station', body=body_prefix+(
                    'Wykryto aktywację ukrytego modułu przy obiekcie Canary Station.' if locale=='pl' else
                    'A hidden GhostNetwork part was activated at Canary Station.'),
                    tone='warning', fact_refs=list(package['fact_refs']), cta_ref=None)
                if 'asset_ref' in package['format']['properties']:
                    output['asset_ref'] = next(iter(package.get('allowed_asset_refs') or [None]))
                result = parse_and_validate_ollama_content(json.dumps(output), package)
                self.assertIn('voice_discovery_changed_to_activation', result['errors'], (locale,medium,result))

    def test_selection_is_frozen_across_reopen_retry_and_dedupe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'locale.sqlite3')
            repo = GhostNetworkRepository(path)
            with patch.dict(os.environ, {'CHAOS_NARRATIVE_LOCALES':'pl,en'}):
                task = self.task(output_locale='en')
                created = repo.enqueue_narrative_task(task)
                # Source fixture has no event row; this only tests persistence.
            reread = GhostNetworkRepository(path).get_narrative_outbox(created['outbox_id'])
            self.assertEqual(task_language(reread)[0], 'en')
            with patch.dict(os.environ, {'CHAOS_NARRATIVE_LOCALES':'pl'}):
                duplicate = repo.enqueue_narrative_task(self.task())
            self.assertEqual(duplicate['outbox_id'], created['outbox_id'])
            self.assertEqual(task_language(duplicate)[0], 'en')
            self.assertEqual(build_ollama_task_package(reread)['output_locale'], 'en')

    def test_english_fallback_keeps_language_and_facts(self):
        with patch.dict(os.environ, {'CHAOS_NARRATIVE_LOCALES':'pl,en'}):
            task = freeze_language(self.task(output_locale='en'))
        package = build_ollama_task_package(task)
        result = NarrativeSupportLayer().apply(task, package,
            {'status':'invalid_json','errors':['invalid_json']}, parse_and_validate_ollama_content)
        self.assertIsNotNone(result)
        self.assertEqual(result['validation']['status'], 'accepted')
        self.assertTrue(result['validation']['output']['title'].startswith('INTERCEPT //'))
        self.assertIn('Zara', result['validation']['output']['body'])
        self.assertEqual(result['validation']['output']['fact_refs'], ['fact:drop-1'])

    def test_invalid_locales_rejected_and_legacy_remains_polish(self):
        self.assertEqual(task_language(self.task()), ('pl', None))
        for locale in ('ANY','ru','en-US',''):
            with patch.dict(os.environ, {'CHAOS_NARRATIVE_LOCALES':'pl,en'}):
                with self.assertRaises(ValueError):
                    freeze_language(self.task(output_locale=locale))

    def test_frozen_facts_cannot_be_silently_replaced(self):
        task = freeze_language(self.task())
        task['facts'] = [{**task['facts'][0], 'fact_type':'different_event'}]
        with self.assertRaisesRegex(ValueError, 'narrative_language_facts_changed'):
            build_ollama_task_package(task)

    def test_third_approved_locale_is_a_registry_package_not_application_branch(self):
        registry=copy.deepcopy(language_registry())
        registry['zz']=copy.deepcopy(registry['en'])
        registry['zz']['blacknet_title_prefix']='TEST // '
        with patch('ghostnetwork.narrative_locale.language_registry',return_value=registry), patch(
                'ghostnetwork.narrative_locale.approved_locales',return_value=('pl','en','zz')):
            task=freeze_language(self.task(output_locale='zz'))
            package=build_ollama_task_package(task)
            self.assertEqual(package['output_locale'],'zz')
            self.assertEqual(package['voice_contract']['title_prefix'],'TEST // ')

    def test_source_task_not_mutated_and_audiences_share_one_bn_language(self):
        before = self.task()
        original = copy.deepcopy(before)
        with patch.dict(os.environ, {'CHAOS_NARRATIVE_LOCALES':'pl,en'}):
            a = freeze_language(before)
            b = freeze_language({**before,'audience_scope':'owner'})
        self.assertEqual(before, original)
        self.assertEqual(task_language(a)[0], task_language(b)[0])
        for family in support_fixtures.NarrativeSupportLayerTest.ENDGAME_FAMILIES:
            self.assertIsNotNone(english_fallback('blacknet', family, 'public'))
