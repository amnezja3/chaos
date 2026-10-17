import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from database import hash_password, verify_password
from identity_gateway.audit import audit_database, email_key, nick_key
from identity_gateway.config import load_config


class IdentityConfigurationTests(unittest.TestCase):
    def test_disabled_defaults_and_callbacks(self):
        config = load_config({})
        self.assertFalse(config.enabled)
        self.assertFalse(config.registration_enabled)
        self.assertFalse(config.linking_enabled)
        self.assertFalse(config.mail.configured)
        for provider in config.providers:
            self.assertFalse(provider.enabled)
            self.assertEqual(provider.callback, f'https://chaos.re/auth/{provider.name}/callback')
        self.assertTrue(config.providers[-1].configured)  # Steam has no OAuth secret.

    def test_secrets_not_in_status_or_repr(self):
        config = load_config({'CHAOS_IDENTITY_GOOGLE_CLIENT_ID': 'private-client',
                              'CHAOS_IDENTITY_GOOGLE_CLIENT_SECRET': 'secret-value',
                              'CHAOS_IDENTITY_SMTP_PASSWORD': 'mail-secret'})
        for value in ('private-client', 'secret-value', 'mail-secret'):
            self.assertNotIn(value, repr(config))
            self.assertNotIn(value, json.dumps(config.status()))
        self.assertTrue(config.providers[0].configured)
        self.assertFalse(config.providers[0].enabled)

    def test_origin_is_fixed_not_request_host(self):
        for origin in ('http://chaos.re', 'https://evil.test/path', 'https://user:pass@chaos.re',
                       'https://chaos.re?next=x', 'https://chaos.re#x', '//chaos.re', 'https://chaos.re\n.evil',
                       'https://chaos.re:bad', 'https://chaos.re:65536', 'https://chaos.re:0',
                       'https://chaos.re\\evil'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                load_config({'CHAOS_IDENTITY_PUBLIC_ORIGIN': origin})
        self.assertEqual(load_config({'CHAOS_IDENTITY_PUBLIC_ORIGIN': 'http://127.0.0.1:8996'}, testing=True).origin,
                         'http://127.0.0.1:8996')

    def test_mock_mail_is_test_only(self):
        with self.assertRaises(ValueError):
            load_config({'CHAOS_IDENTITY_MAIL_MODE': 'mock'})
        config = load_config({'CHAOS_IDENTITY_MAIL_MODE': 'mock'}, testing=True)
        self.assertEqual(config.mail.mode, 'mock')
        self.assertFalse(config.mail.configured)

    def test_bad_configuration_fails_closed(self):
        for values in ({'CHAOS_IDENTITY_ENABLED': 'yes'}, {'CHAOS_IDENTITY_SMTP_TLS': 'none'},
                       {'CHAOS_IDENTITY_SMTP_PORT': '0'}, {'CHAOS_IDENTITY_SMTP_PORT': 'secret'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                load_config(values)


class LegacyAuditTests(unittest.TestCase):
    def test_collisions_report_ids_without_mutating_or_leaking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, password TEXT, profile_json TEXT)')
                conn.executemany('INSERT INTO users VALUES (?,?,?)', [
                    (1, 'pbkdf2_sha256$240000$fixture$fixture', json.dumps({'nick': 'Pilot', 'email': 'Pilot@example.test'})),
                    (2, 'legacy-secret', json.dumps({'nick': ' ＰＩＬＯＴ ', 'email': 'pilot@EXAMPLE.test'})),
                    (3, '', json.dumps({'nick': '', 'email': None})),
                    (4, None, '[]'), (5, 'legacy-secret', 'invalid-json')])
            conn.close()
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            report = audit_database(path)
            self.assertEqual(report['collisions'], {'nick': [[1, 2]], 'email': [[1, 2]]})
            self.assertEqual(report['malformed_profile_ids'], [4, 5])
            self.assertEqual(report['empty_password_ids'], [3, 4])
            self.assertEqual(report['legacy_password_ids'], [2, 5])
            self.assertEqual(report['missing'], {'nick': [3], 'email': [3]})
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
            self.assertNotIn('example.test', json.dumps(report))
            self.assertNotIn('legacy-secret', json.dumps(report))

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.sqlite3'
            with self.assertRaises(FileNotFoundError):
                audit_database(path)
            self.assertFalse(path.exists())

    def test_no_provider_alias_merging(self):
        self.assertNotEqual(email_key('a.b@example.test'), email_key('ab@example.test'))
        self.assertNotEqual(email_key('a+tag@example.test'), email_key('a@example.test'))
        self.assertEqual(nick_key(' Ｐilot '), 'pilot')


class MissingCredentialTests(unittest.TestCase):
    def test_absent_or_empty_password_never_authenticates(self):
        empty_hash, _ = hash_password('')
        for supplied in ('', None, 0, False):
            for stored in ('', None, empty_hash):
                with self.subTest(supplied=supplied, stored=stored):
                    self.assertFalse(verify_password(supplied, stored))

    def test_nonempty_legacy_and_current_credentials_work(self):
        encoded, _ = hash_password('Valid1234')
        self.assertTrue(verify_password('Valid1234', encoded))
        self.assertTrue(verify_password('legacy', 'legacy'))
        self.assertFalse(verify_password('Wrong1234', encoded))
        self.assertFalse(verify_password('Valid1234', ''))
