"""Real endpoint and transaction regression for Sprint 156.2."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import run
import test_session_generation_precommit as fixtures
from database import set_request_transaction_precommit_guard, reset_request_transaction_precommit_guard
from session_generation_store import SessionGenerationStateError


class PersistentFlowTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SessionGenerationPrecommitTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        self.store = self.fixture.generation_store
        self.users = self.fixture.user_store
        self.now = datetime.now(timezone.utc)
        self.store.clock = lambda: self.now
        with patch.dict(run.app.config, {'CHAOS_PERSISTENT_SESSION_ENABLED': True}), \
                patch.object(run, 'authenticate_user', return_value=True):
            result = self.client.post('/', data={'username': 'alice', 'password': 'secret'})
        self.assertEqual(302, result.status_code)
        with self.client.session_transaction() as current:
            self.lineage = current[run.SESSION_LINEAGE_KEY]
            self.generation = current[run.SESSION_GENERATION_KEY]
            self.headers = {run.SESSION_GENERATION_HEADER: self.generation,
                            'X-Chaos-CSRF': current['session_csrf'], 'Origin': 'http://localhost'}

    def test_activity_renews_only_with_csrf_and_generation(self):
        before = self.store.get_state(self.lineage)
        self.now += timedelta(days=10)
        for bad in ({}, {**self.headers, 'X-Chaos-CSRF': 'bad'},
                    {**self.headers, 'Origin': 'https://evil.test'}):
            response = self.client.post('/api/session/activity', headers=bad)
            self.assertIn(response.status_code, (403, 409))
            self.assertEqual(before, self.store.get_state(self.lineage))
        response = self.client.post('/api/session/activity', headers=self.headers)
        self.assertEqual({'ok': True, 'renewed': True}, response.get_json())
        self.assertIn('Expires=', response.headers['Set-Cookie'])
        response = self.client.post('/api/session/activity', headers=self.headers)
        self.assertFalse(response.get_json()['renewed'])
        self.assertNotIn('Set-Cookie', response.headers)
        after = self.store.get_state(self.lineage)
        self.assertEqual(before['absolute_expires_at'], after['absolute_expires_at'])
        self.assertNotEqual(before['idle_expires_at'], after['idle_expires_at'])

    def test_expired_or_replaced_activity_cannot_revive(self):
        self.now += timedelta(days=30)
        response = self.client.post('/api/session/activity', headers=self.headers)
        self.assertEqual(409, response.status_code)
        self.assertNotIn('Set-Cookie', response.headers)
        self.store.activate('new', 'new', 'alice', reason='login')
        response = self.client.post('/api/session/activity', headers=self.headers)
        self.assertEqual(409, response.status_code)
        self.assertTrue(self.store.is_current('new', 'new', 'alice'))

    def test_get_logout_is_readonly_post_requires_csrf_and_no_cookie_deletion(self):
        response = self.client.get('/logout', headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertTrue(self.store.is_current(self.lineage, self.generation, 'alice'))
        denied = self.client.post('/logout', headers={run.SESSION_GENERATION_HEADER: self.generation})
        self.assertEqual(403, denied.status_code)
        response = self.client.post('/logout', headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertFalse(self.store.is_current(self.lineage, self.generation, 'alice'))

    def test_old_recovery_does_not_clear_new_login(self):
        with patch.object(run, 'authenticate_user', return_value=True):
            self.client.post('/', data={'username': 'alice', 'password': 'secret'})
        with self.client.session_transaction() as current:
            newer = current[run.SESSION_GENERATION_KEY]
        response = self.client.get('/session/recover?reason=browser_session_replaced')
        self.assertEqual(302, response.status_code)
        self.assertNotIn('Set-Cookie', response.headers)
        with self.client.session_transaction() as current:
            self.assertEqual(newer, current[run.SESSION_GENERATION_KEY])

    def test_password_endpoint_revokes_and_reports_reauthentication(self):
        with patch.object(run, 'authenticate_user', return_value=True):
            response = self.client.post('/api/profile/account', headers=self.headers,
                json={'current_password': 'secret', 'new_password': 'New-password-2026!'})
        self.assertEqual(200, response.status_code, response.get_json())
        self.assertTrue(response.get_json()['reauthenticate'])
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertFalse(self.store.is_current(self.lineage, self.generation, 'alice'))
        self.assertTrue(self.users.authenticate('alice', 'New-password-2026!'))

    def password_candidate(self):
        record = self.users.get_profile_with_revision('alice')
        candidate = copy.deepcopy(record['profile'])
        candidate.update(password='New-password-2026!', salt='')
        return record, candidate

    def test_credential_revocation_failure_rolls_back_password(self):
        record, candidate = self.password_candidate()
        with patch('session_generation_store.revoke_credentials_with_conn', side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError):
                self.users.save_profile_guarded(candidate, expected_revision=record['profile_revision'],
                                                source='admin.password_reset')
        self.assertEqual(record, self.users.get_profile_with_revision('alice'))
        self.assertTrue(self.store.is_current(self.lineage, self.generation, 'alice'))

    def test_stale_password_transaction_rolls_back_before_revocation(self):
        record, candidate = self.password_candidate()
        guard = self.store.build_transaction_precommit_guard(self.lineage, self.generation, 'alice')
        self.store.activate('other', 'newer', 'alice', reason='login')
        token = set_request_transaction_precommit_guard(guard)
        try:
            from database import ProfilePrecommitRejected
            with self.assertRaises(ProfilePrecommitRejected):
                self.users.save_profile_guarded(candidate, expected_revision=record['profile_revision'],
                                                source='admin.password_reset')
        finally:
            reset_request_transaction_precommit_guard(token)
        self.assertTrue(self.store.is_current('other', 'newer', 'alice'))
        self.assertEqual(record, self.users.get_profile_with_revision('alice'))

    def test_noncredential_profile_edit_keeps_session(self):
        record = self.users.get_profile_with_revision('alice')
        candidate = copy.deepcopy(record['profile'])
        candidate['email'] = 'new@example.test'
        self.users.save_profile_guarded(candidate, expected_revision=record['profile_revision'],
                                        source='profile.account_credentials')
        self.assertTrue(self.store.is_current(self.lineage, self.generation, 'alice'))


if __name__ == '__main__':
    unittest.main()
