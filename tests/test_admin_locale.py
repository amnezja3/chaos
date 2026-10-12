import json
import re
import unittest
from unittest.mock import patch

import run
from ghost_i18n import translator


class AdminLocaleTest(unittest.TestCase):
    def test_all_panels_render_recipient_language_without_profile_reads(self):
        for locale in ('pl', 'en'):
            for tab in ('users','ghostlab','radio','narrative','territories','vulnerabilities','bugs'):
                with self.subTest(locale=locale, tab=tab), run.app.test_request_context('/admin?tab='+tab):
                    run.session['user']='admin'
                    run.g.ghost_ui_locale=locale
                    with patch.object(run, 'require_dev_admin', return_value=True), patch.object(
                            run, 'session_generation_client_context', return_value={'query_token':'fixture'}), patch.object(
                            run, 'build_admin_dashboard_state', side_effect=AssertionError('heavy dashboard')):
                        html=run.dev_dashboard()
                    self.assertIn('Administration sections' if locale=='en' else 'Sekcje administracji', html)
                    config=json.loads(re.search(r'id="admin-locale-config" type="application/json">(.*?)</script>',html,re.S)[1])
                    self.assertEqual(config['locale'],locale)
                    self.assertTrue(all(key.startswith('apps.admin.') for catalog in config['catalogs'].values() for key in catalog['messages']))
                    if locale=='en':
                        self.assertNotIn('Wróć do gry', html.split('<script id="admin-locale-config"')[0])
                        self.assertIn('Return to game', html)

    def test_admin_parameter_insertion_does_not_translate_user_text(self):
        for locale in ('pl','en'):
            result=translator().t('apps.admin.outside_lab', {'names':'Moje <narzędzie> {name}'},locale)
            self.assertIn('Moje <narzędzie> {name}',result)

    def test_profession_labels_change_but_canonical_update_does_not(self):
        profile = {'username':'player','clan':'VIREX','fraction':{'id':'3','name':'VIREX','role':'4'}}
        pl = run.build_admin_profession_contract(profile, 'broker', locale='pl')
        en = run.build_admin_profession_contract(profile, 'broker', locale='en')
        self.assertEqual(pl['updates'], en['updates'])
        self.assertEqual(en['choices'][3]['name'], 'Profit Enforcer')
