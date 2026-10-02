import unittest
from unittest.mock import patch

import run
from database import db_connect
from ghostnetwork import GhostCycleService
from tools.audit_ghostnetwork_delivery import audit
from tests import test_ghostnetwork_post130_bridge as fixtures


class ConflictDeliveryRecoveryTest(unittest.TestCase):
    setUp = fixtures.GhostNetworkPost130BridgeTest.setUp
    tearDown = fixtures.GhostNetworkPost130BridgeTest.tearDown

    def event(self, suffix='one'):
        return self.repo.append_event('ghost.part_activated',
            cycle_id=self.repo.get_active_cycle()['cycle_id'], event_id='replay-' + suffix,
            part_id='replay-part-' + suffix, player_id='alice', clan_code='virex',
            audience_scope='public', payload={'score': 10})

    def test_narrative_summary_resolves_original_cycle_not_current_cycle(self):
        event = self.event()
        # The active-cycle lookup must never be used to fill an old event's cycle.
        with patch.object(self.repo, 'get_active_cycle', return_value={'cycle_id': 'later-cycle'}), \
             patch.object(run, 'enqueue_ghostnetwork_event_delta') as deliver:
            run.apply_ghostnetwork_runtime_result(self.service, {
                'narrative_dispatch': {'results': [{'event_id': event['event_id'],
                                                   'event_type': event['event_type'], 'ok': True}]}})
        self.assertEqual(deliver.call_args.args[0]['cycle_id'], event['cycle_id'])
        self.assertEqual(deliver.call_args.args[0]['audience_scope'], 'public')

    def test_missing_canonical_event_fails_without_guessing_cycle(self):
        with patch.object(run, 'enqueue_ghostnetwork_event_delta') as deliver:
            with self.assertRaisesRegex(RuntimeError, 'Canonical GhostNetwork event missing'):
                run.apply_ghostnetwork_runtime_result(self.service,
                    {'event_id': 'absent', 'event_type': 'ghost.part_activated'})
            deliver.assert_not_called()

    def test_old_conflict_marker_does_not_reactivate_part_from_closed_cycle(self):
        old_cycle = self.repo.get_active_cycle()['cycle_id']
        old_part = self.repo.get_part(self.part['part_id'])
        self.repo.update_cycle(old_cycle, status='closed')
        new_cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()['cycle']['cycle_id']
        self.assertNotEqual(new_cycle, old_cycle)
        with patch.object(run, 'build_ghostnetwork_territory_publication', return_value=[]), \
             patch.object(run, 'maybe_finalize_ghostnetwork_cycle', return_value={'ok': True}), \
             patch.object(run, 'enqueue_ghostnetwork_event_delta') as deliver:
            result = run.bridge_ghostnetwork_conflict_publication(
                {'conflict': {'conflict_id': 'historic-marker', 'status': 'resolved', 'cycle_id': old_cycle}},
                service=self.service)
        self.assertTrue(result['ok'], result)
        self.assertEqual(self.repo.get_part(self.part['part_id']), old_part)
        self.assertEqual(self.progression.progression.get('alice')['respect'], 100)
        deliver.assert_not_called()

    def test_retry_after_transition_and_reward_commit_delivers_once_without_second_reward(self):
        job = self.job_store.enqueue('areas', 'alice', 'conflict-resolution')
        created = []
        def transition(**kwargs):
            if not created:
                created.append(self.event())
            return {'ok': True, 'changes': []}
        with patch.object(run, 'ghostnetwork_territory_job_store', self.job_store), \
             patch.object(run, 'ghostnetwork_delta_delivery_job_store', self.delivery_store), \
             patch.object(run, 'bridge_ghostnetwork_territory_publication', side_effect=transition), \
             patch.object(run, 'maybe_finalize_ghostnetwork_cycle', return_value={'ok': True}), \
             patch.object(run.user_store, 'get_profile', side_effect=AssertionError('heavy profile')):
            with patch.object(self.delivery_store, 'enqueue', side_effect=RuntimeError('delivery interrupted')):
                failed = run.process_ghostnetwork_territory_job('first', service=self.service)
            self.assertFalse(failed['ok'])
            reward_after_failure = self.progression.progression.get('alice')['respect']
            self.assertGreater(reward_after_failure, 100)
            with db_connect(self.db_path) as conn:
                conn.execute('UPDATE ghostnetwork_territory_jobs SET next_attempt_at=0 WHERE job_id=?', (job['job_id'],))
            recovered = run.process_ghostnetwork_territory_job('retry', service=self.service)
            self.assertTrue(recovered['ok'], recovered)
            self.assertEqual(recovered['error'], '')
            self.assertEqual(self.progression.progression.get('alice')['respect'], reward_after_failure)
            self.assertEqual(self.repo.get_clan_reputation('virex')['parts_activated'], 1)
            with db_connect(self.db_path) as conn:
                count = conn.execute('SELECT COUNT(*) FROM ghostnetwork_delta_delivery_jobs WHERE event_id=?',
                                     (created[0]['event_id'],)).fetchone()[0]
            self.assertEqual(count, 1)
            self.assertEqual(self.job_store.diagnostics()['depth'], 0)

    def test_started_job_is_not_coalesced_away(self):
        original = self.job_store.enqueue('areas', 'alice', 'first')
        claim = self.job_store.claim('worker')
        self.job_store.event_cursor(claim['job_id'], 'worker', initial_cursor=12)
        self.job_store.finish(claim['job_id'], 'worker', ok=False, error='interrupted')
        self.job_store.enqueue('areas', 'alice', 'second')
        with db_connect(self.db_path) as conn:
            conn.execute('UPDATE ghostnetwork_territory_jobs SET next_attempt_at=0')
        retry = self.job_store.claim('retry')
        self.assertEqual(retry['job_id'], original['job_id'])
        self.assertEqual(self.job_store.event_cursor(retry['job_id'], 'retry', initial_cursor=999), '12')

    def test_ownerless_fresh_geometry_is_not_reported_invalid(self):
        area = fixtures.GhostNetworkPost130BridgeTest.area('alice')
        del area['owner_username']
        with patch.object(run.identity_projection_store, 'map_actor_candidates', return_value=[]) as candidates, \
             patch('builtins.print') as output:
            run.sync_static_area_intruders_for_owner('alice', [area])
        candidates.assert_called_once()
        self.assertFalse(any('skipped invalid' in str(c) for c in output.call_args_list))
        self.assertNotIn('owner_username', area)

    def test_pagination_preserves_events_sharing_state_version(self):
        cursor = self.repo.runtime_event_cursor()
        cycle = self.repo.get_active_cycle()['cycle_id']
        expected = [self.repo.append_event('ghost.part_updated', cycle_id=cycle,
                    event_id=f'page-{i}', state_version=100)['event_id'] for i in range(3)]
        through = self.repo.runtime_event_cursor()
        first = self.repo.runtime_events_after(cursor, through, limit=2)
        second = self.repo.runtime_events_after(first[-1][0], through, limit=2)
        self.assertEqual([event['event_id'] for _, event in first + second], expected)

    def test_fresh_geometry_uses_persisted_area_identity(self):
        saved = fixtures.GhostNetworkPost130BridgeTest.area('alice')
        raw = {'vertices': saved['vertices']}
        with patch.object(run.territory_store, 'list_player_areas', return_value=[saved]) as read, \
             patch.object(run.identity_projection_store, 'map_actor_candidates', return_value=[]) as candidates, \
             patch('builtins.print') as output:
            run.sync_static_area_intruders_for_owner('alice', [raw])
        read.assert_called_once_with('alice', limit=1000)
        candidates.assert_called_once()
        self.assertFalse(any('skipped invalid' in str(c) for c in output.call_args_list))

    def test_operator_audit_is_read_only_and_marks_missing_delivery(self):
        event = self.event('audit')
        from pathlib import Path
        before = Path(self.db_path).read_bytes()
        report = audit(self.db_path, '2020-01-01T00:00:00Z', '2030-01-01T00:00:00Z')
        self.assertIn(event['event_id'], report['missing_delivery_ids'])
        self.assertTrue(report['read_only'])
        self.assertFalse(report['truncated'])
        self.assertEqual(Path(self.db_path).read_bytes(), before)
