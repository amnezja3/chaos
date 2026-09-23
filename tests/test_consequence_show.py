import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from database import db_connect
from response_network.consequence_show import claim
from tests import test_canonical_consequences as fixture


class ConsequenceShowTest(unittest.TestCase):
    setUp = fixture.CanonicalConsequencesTest.setUp
    seed_actor = fixture.CanonicalConsequencesTest.seed_actor
    candidate = fixture.CanonicalConsequencesTest.candidate
    rows = fixture.CanonicalConsequencesTest.rows
    encounter = fixture.CanonicalConsequencesTest.encounter

    def test_committed_receipt_is_private_and_claimed_only_once_across_tabs(self):
        result = self.encounter()
        eid = result['encounter']['encounter_id']
        self.assertIsNone(claim(self.path, 'bob', eid, now=self.now))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(self.path, 'alice', eid, now=self.now), range(2)))
        shows = [result for result in results if result]
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]['stage'], 1)
        self.assertEqual(shows[0]['effects'], result['execution']['effects'])

    def test_old_missing_and_unexecuted_are_not_shown(self):
        result = self.encounter()
        eid = result['encounter']['encounter_id']
        self.assertIsNone(claim(self.path, 'alice', eid, now=self.now + timedelta(seconds=61)))
        self.assertIsNone(claim(self.path, 'alice', 'missing', now=self.now))
        with db_connect(self.path) as conn:
            conn.execute("UPDATE response_encounters SET execution_status='unsupported' WHERE encounter_id=?", (eid,))
        self.assertIsNone(claim(self.path, 'alice', eid, now=self.now))

    def test_http_claim_uses_session_actor_and_validates_input(self):
        import run
        from tests import test_target_persistence as http_fixture
        result = self.encounter()
        eid = result['encounter']['encounter_id']
        http_fixture.setUpModule()
        self.addCleanup(http_fixture.tearDownModule)
        original = claim
        with patch.object(run, 'detention_service', self.executor.detention), patch(
                'response_network.consequence_show.claim',
                side_effect=lambda path, actor, key: original(path, actor, key, now=self.now)):
            client = run.app.test_client()
            with client.session_transaction() as session: session['user'] = 'bob'
            response = client.post('/api/response/consequence-show/claim', json={'encounter_id': eid, 'actor_id': 'alice'})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.get_json()['show'])
            client = run.app.test_client()
            with client.session_transaction() as session: session['user'] = 'alice'
            self.assertEqual(client.post('/api/response/consequence-show/claim', json=[]).status_code, 400)
            response = client.post('/api/response/consequence-show/claim', json={'encounter_id': eid})
            self.assertEqual(response.get_json()['show']['stage'], 1)

    def test_delta_failure_rolls_back_penalty_and_receipt(self):
        original = self.deltas.record_change
        def fail_show(*args, **kwargs):
            if args[2] == 'response.consequence_executed':
                raise RuntimeError('show delta failure')
            return original(*args, **kwargs)
        balance = self.wallet.get_balance('alice')
        with patch.object(self.deltas, 'record_change', side_effect=fail_show):
            self.assertEqual(self.encounter()['execution']['status'], 'deferred')
        self.assertEqual(self.wallet.get_balance('alice'), balance)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM response_encounters WHERE execution_status='executed'").fetchone()[0], 0)
