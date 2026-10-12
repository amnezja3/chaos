import unittest

from ghostnetwork.llm.prompt_metrics import prompt_metrics
from tools.narrative_locale_canary import package_for


class NarrativePromptBudgetTest(unittest.TestCase):
    def test_real_canaries_keep_facts_and_voice_with_smaller_prompts(self):
        # Pre-optimization complete message sizes, measured on the same fixture.
        previous = {
            ('pl', 'blacknet'): 2473, ('pl', 'cyberner'): 2297,
            ('pl', 'googleplex_news'): 2331, ('en', 'blacknet'): 2519,
            ('en', 'cyberner'): 2327, ('en', 'googleplex_news'): 3633,
        }
        for (locale, medium), size in previous.items():
            with self.subTest(locale=locale, medium=medium):
                package = package_for(locale, medium)
                metrics = prompt_metrics(package)
                self.assertLess(metrics['message_bytes'], size * .85)
                self.assertIn('Canary Station', package['messages'][1]['content'])
                self.assertEqual(package['output_locale'], locale)
                self.assertTrue(package['voice_contract']['discovery_only'])
                if medium == 'blacknet':
                    self.assertEqual(package['voice_contract']['body_prefix'], '...')
                    self.assertIn(package['voice_contract']['title_prefix'],
                                  package['messages'][0]['content'])

    def test_metrics_count_all_messages_utf8_and_schema_without_exposing_text(self):
        package = {'messages': [{'role': 'system', 'content': 'ą'},
                                {'role': 'user', 'content': 'abc'}],
                   'format': {'type': 'object'}}
        original = prompt_metrics(package)
        self.assertEqual(original['message_chars'], 4)
        self.assertEqual(original['message_bytes'], 5)
        self.assertGreater(original['schema_bytes'], 0)
        package['format']['additionalProperties'] = False
        self.assertNotEqual(original['prompt_sha256'], prompt_metrics(package)['prompt_sha256'])
        package['messages'][0]['content'] = 'ł'
        self.assertNotEqual(original['prompt_sha256'], prompt_metrics(package)['prompt_sha256'])


if __name__ == '__main__':
    unittest.main()
