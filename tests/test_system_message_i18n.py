import json
import tempfile
import unittest
from pathlib import Path

from database import SystemMessageStore, MailStore, db_connect
from ghost_i18n import translator
from system_message_i18n import project_system_copy, COMPILED_TEMPLATES


class SystemMessageLocaleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'messages.sqlite3')
        self.store = SystemMessageStore(self.path)
        self.message = {
            'title': 'Instalacja zakończona',
            'text': 'Aplikacja <b>Moje <narzędzie> & test</b> została poprawnie zainstalowana!',
            'type': 'success', 'dedupe_key': 'googleplex_app_install:receipt1',
        }

    def test_persisted_copy_and_locale_do_not_repeat_consumption(self):
        saved, created = self.store.add_message('operator',self.message,source='googleplex_install')
        self.assertTrue(created)
        copy = saved['system_copy']
        self.assertEqual(copy['params']['name'],'Moje <narzędzie> & test')
        self.assertEqual(translator().t(copy['title_key'],locale='en'),'Installation complete')
        self.assertIn('Moje <narzędzie> & test',translator().t(copy['text_key'],copy['params'],'en'))
        delivered = self.store.consume_pending('operator')
        self.assertEqual(len(delivered),1)
        self.assertEqual(delivered[0]['system_copy'],copy)
        self.assertEqual(self.store.consume_pending('operator'),[])
        duplicate, created = self.store.add_message('operator',self.message,source='googleplex_install')
        self.assertFalse(created)
        self.assertEqual(saved['id'],duplicate['id'])
        self.assertEqual(self.store.consume_pending('operator'),[])

    def test_store_default_source_keeps_system_document_and_risk_copy(self):
        for title, text in (
            ('Dokument PTK', 'Pobrano dokument do Pliki → Plexcak.'),
            ('Risk event', 'atm_alarm: Terminal finansowy wykryl nietypowa probe odczytu danych.'),
        ):
            saved, created = self.store.add_message('operator', {'title':title, 'text':text})
            self.assertTrue(created)
            self.assertIn('system_copy', saved)
            self.assertNotEqual(translator().t(saved['system_copy']['text_key'], locale='en'), text)

    def test_legacy_projection_is_read_only_and_preserves_consumed_status(self):
        saved, _ = self.store.add_message('operator',self.message,source='googleplex_install')
        self.store.consume_pending('operator')
        with db_connect(self.path) as conn:
            payload = dict(saved)
            payload.pop('system_copy')
            conn.execute('UPDATE system_messages SET payload_json=?',(json.dumps(payload),))
            row = conn.execute('SELECT * FROM system_messages').fetchone()
            before = dict(row)
            projected = self.store._row_to_message(row)
            self.assertIn('system_copy',projected)
            self.assertEqual(dict(conn.execute('SELECT * FROM system_messages').fetchone()),before)
        self.assertEqual(self.store.consume_pending('operator'),[])

    def test_user_text_and_ambiguous_legacy_are_never_translated(self):
        forged = {**self.message, 'system_copy': {'schema_version':1}}
        self.assertNotIn('system_copy',project_system_copy(forged,'api'))
        self.assertNotIn('system_copy',project_system_copy({**forged,'text':'Custom text'},'googleplex_install'))
        self.assertEqual(forged['text'],project_system_copy(forged,'api')['text'])

    def test_cyberner_preview_is_original_even_when_it_matches_system_text(self):
        message = dict(notification_type='cyberner',source='friends',title='ZNAJOMI',
                       text='Nowa wiadomosc.',system_preview=False)
        copy = project_system_copy(message, 'cyberner')['system_copy']
        self.assertEqual(translator().t(copy['title_key'],locale='en'), 'FRIENDS')
        self.assertEqual(translator().t(copy['text_key'],copy['params'],'en'),message['text'])
        empty = project_system_copy({**message,'system_preview':True}, 'cyberner')['system_copy']
        self.assertEqual(translator().t(empty['text_key'],empty['params'],'en'),'New message.')
        self.assertNotIn('system_copy',project_system_copy(message,'api'))

    def test_system_mail_retains_copy_but_player_mail_with_same_text_does_not(self):
        store=MailStore(self.path)
        text='👋 Gracz <b> wysyla Ci gest przywitania. Odpowiedz, zeby dodac go do znajomych.'
        store.add_direct_notification('operator','player','Gracz <b>','Gest przywitania',text)
        store.add_message('operator','direct','player','operator',text,subject='Gest przywitania')
        messages=store.list_messages('operator','direct','player')
        system,player=messages
        self.assertTrue(system['system_copy'])
        self.assertFalse(player['system_copy'])
        self.assertEqual(system['body'],player['body'])
        copy=system['system_copy']
        self.assertIn('Gracz <b>',translator().t(copy['text_key'],copy['params'],'en'))
        with db_connect(self.path) as conn:
            before=[dict(row) for row in conn.execute('SELECT * FROM chat_messages ORDER BY id')]
        store.list_messages('operator','direct','player')
        with db_connect(self.path) as conn:
            self.assertEqual(before,[dict(row) for row in conn.execute('SELECT * FROM chat_messages ORDER BY id')])

    def test_inventory_is_read_only_bounded_and_does_not_export_private_text(self):
        from tools.system_copy_inventory import inventory
        self.store.add_message('operator', self.message, source='googleplex_install')
        mail = MailStore(self.path)
        mail.add_message('operator', 'direct', 'peer', 'operator', 'private text')
        with db_connect(self.path) as conn:
            before = [tuple(row) for row in conn.execute('SELECT * FROM chat_messages')]
        notifications = inventory(self.path, 'notifications', limit=1)
        messages = inventory(self.path, 'mail', limit=1)
        self.assertTrue(notifications['records'][0]['has_system_copy'])
        self.assertTrue(messages['records'][0]['review_required'])
        self.assertNotIn('private text', json.dumps(messages))
        self.assertNotIn('Moje', json.dumps(notifications))
        self.assertEqual(inventory(self.path, 'mail', messages['next_after'])['records'], [])
        with db_connect(self.path) as conn:
            self.assertEqual(before, [tuple(row) for row in conn.execute('SELECT * FROM chat_messages')])
        with self.assertRaises(ValueError):
            inventory(self.path, 'mail', limit=501)

    def test_every_historical_template_has_both_catalogs_and_correct_params(self):
        runtime = translator()
        for _, _, pattern, key in COMPILED_TEMPLATES:
            for locale in ('pl','en'):
                title = runtime.catalogs[locale]['messages']['apps.notifications.' + key + '_title']
                body = runtime.catalogs[locale]['messages']['apps.notifications.' + key + '_text']
                self.assertEqual(title['params'],{})
                self.assertEqual(set(body['params']),set(pattern.groupindex))
                self.assertTrue(runtime.t('apps.notifications.' + key + '_text',
                    {name:'Original <name>' for name in pattern.groupindex},locale))

    def test_restart_and_territory_copy_preserve_user_names_and_dedupe(self):
        message = {'title':'Utrata punktu terytorium',
                   'text':'Gracz EN przejal twoj obiekt Mój sklep. Terytorium jest przebudowywane.',
                   'dedupe_key':'territory:test'}
        saved, created = self.store.add_message('operator',message,source='domain_event')
        self.assertTrue(created)
        copy = saved['system_copy']
        self.assertEqual(copy['params'],{'actor':'Gracz EN','target':'Mój sklep'})
        self.assertEqual(translator().t(copy['text_key'],copy['params'],'en'),
            'Gracz EN captured your object Mój sklep. Your territory is being rebuilt.')
        self.assertNotIn('system_copy',project_system_copy(message,'api'))
        self.assertEqual(len(self.store.consume_pending('operator')),1)
        self.assertFalse(self.store.add_message('operator',message,source='domain_event')[1])
        self.assertEqual(self.store.consume_pending('operator'),[])


if __name__ == '__main__':
    unittest.main()
