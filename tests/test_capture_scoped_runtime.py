import unittest
from contextlib import contextmanager
from unittest.mock import patch

import database
import run
from creator_policy import SECURITY_KEYS
from ghostnetwork import GhostNetworkRepository, GhostNetworkService, GhostCycleService
from ghost_reward_projection import settle
from tests import test_player_hack_read_paths as read_tests
from tests import test_ghostlab_alignment as alignment_tests


class CaptureScopedRuntimeTest(unittest.TestCase):
    @contextmanager
    def no_heavy(self):
        forbidden = []
        execute = database.InstrumentedConnection.execute
        def guarded(conn, sql, *args, **kwargs):
            if 'profile_json' in sql.lower() or 'select * from users' in sql.lower():
                forbidden.append(sql)
                raise AssertionError('Heavy SQL: ' + sql)
            return execute(conn, sql, *args, **kwargs)
        with alignment_tests.GhostLabAlignmentTest.no_heavy(self), patch.object(
                database.InstrumentedConnection, 'execute', guarded):
            yield
        self.assertEqual(forbidden, [], 'Heavy SQL must not be swallowed by an optional hook')

    def setUp(self):
        read_tests.PlayerHackReadPathsTest.setUp(self)
        self.users.save_profile(dict(read_tests.valid_profile('attacker'), level=40, respect=500))
        self.inventory.seed_from_profile('attacker', read_tests.valid_profile('attacker'))
        for name in ('territory_store', 'territory_conflict_store', 'territory_conflict_engagement_store',
                     'territory_target_ownership_store', 'territory_progression_receipt_store',
                     'vulnerability_store', 'player_target_runtime_store', 'player_marked_target_store',
                     'player_position_store', 'player_operation_store', 'app_action_receipt_store', 'delta_bus', 'mail_store'):
            self.stack.enter_context(patch.object(run, name, type(getattr(run, name))(self.path)))
        self.progression = run.territory_progression_receipt_store.progression
        self.repo = GhostNetworkRepository(db_path=self.path)
        self.service = GhostNetworkService(repository=self.repo)
        self.stack.enter_context(patch.object(run, 'get_ghostnetwork_service', return_value=self.service))

    def reward(self):
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()['cycle']
        return self.service.handle_reward_event(dict(event_id='scoped-discovery',
            event_type='ghost.part_discovered', cycle_id=cycle['cycle_id'], part_id='part-test',
            player_id='attacker', clan_code='', payload=dict(score=10, discovered_by='attacker')),
            profile=dict(username='attacker'), apply=False)['created']['reward']

    def test_ghost_reward_crash_retry_and_worker_do_not_repay(self):
        reward = self.reward()
        with self.no_heavy():
            with patch.object(self.service, 'finalize_projected_reward', side_effect=RuntimeError('crash')):
                with self.assertRaises(RuntimeError):
                    settle(self.progression, self.service, reward)
            after = self.progression.get('attacker')
            self.assertEqual(after['respect'], 500 + reward['final_rsp'])
            replay = run.process_ghostnetwork_pending_reward_projection(service=self.service, worker_id='test')
            self.assertTrue(replay['duplicate'])
            self.assertEqual(self.progression.get('attacker'), after)
            self.assertEqual(self.repo.get_reward(reward['reward_id'])['status'], 'applied')

    def test_ghost_reward_missing_migration_fails_closed(self):
        reward = self.reward()
        with database.db_connect(self.path) as conn:
            conn.execute('DELETE FROM player_ghost_reward_state')
        with self.no_heavy(), self.assertRaises(database.ProfileRecoveryRequired):
            settle(self.progression, self.service, reward)
        self.assertEqual(self.progression.get('attacker')['respect'], 500)
        self.assertEqual(self.repo.get_reward(reward['reward_id'])['status'], 'pending')

    def test_historical_ghost_receipt_is_migrated_without_repayment(self):
        import json
        from tools.migrate_player_progression import migrate
        reward = self.reward()
        record = self.users.get_profile_with_revision('attacker')
        profile = record['profile']
        profile['ghostnetwork_reward_history'] = [dict(reward_key=reward['reward_key'],
            reward_type=reward['reward_type'], rsp=reward['final_rsp'], source='ghostnetwork')]
        self.users.save_profile_guarded(profile, expected_revision=record['profile_revision'], source='test.legacy')
        with database.db_connect(self.path) as conn:
            conn.execute('DELETE FROM player_ghost_reward_state')
        self.assertEqual(migrate(self.path, ['attacker'])[0]['status'], 'ready')
        migrate(self.path, ['attacker'], apply=True)
        with self.no_heavy():
            result = settle(self.progression, self.service, reward)
            self.assertTrue(result['duplicate'])
            self.assertEqual(self.progression.get('attacker')['respect'], 500)

    def test_coalesced_capture_receipts_rollback_as_one_transaction(self):
        receipts = run.territory_progression_receipt_store
        first = receipts.ensure('group-one', 'attacker', {})['receipt_id']
        second = receipts.ensure('group-two', 'attacker', {})['receipt_id']
        with self.no_heavy():
            before = self.progression.get('attacker')
            with self.assertRaises(ValueError):
                self.progression.settle(first, dict(levels_gained=1, respect_gain=10),
                    coalesced_receipts=[second, 'missing-receipt'])
            self.assertEqual(before, self.progression.get('attacker'))
            result = self.progression.settle(first, dict(levels_gained=1, respect_gain=10),
                                            coalesced_receipts=[second])
            self.assertTrue(result['ok'])
            replay = self.progression.settle(second, dict(levels_gained=100, respect_gain=1000))
            self.assertTrue(replay['duplicate'])
            self.assertEqual(self.progression.get('attacker')['respect'], 510)

    def test_conflict_worker_stats_retry_preserves_reward_and_avoids_profile(self):
        with patch.object(run.territory_conflict_store, 'get_by_key', return_value=dict(participants=['attacker'])), self.no_heavy():
            first = run.finalize_conflict_rebuild_profiles('conflict-test')
            state = self.progression.get('attacker')
            second = run.finalize_conflict_rebuild_profiles('conflict-test')
            self.assertEqual(first, second)
            self.assertEqual(state, self.progression.get('attacker'))
            self.assertEqual(state['respect'], 500)

    def test_complete_legacy_capture_without_full_profile(self):
        self.capture()

    def test_contested_capture_and_owner_loss_without_full_profile(self):
        self.capture(contested=True)

    def test_vehicle_capture_does_not_rebuild_or_reward_territory(self):
        before = self.progression.get('attacker')
        with patch.object(run, 'rebuild_player_areas_with_territory_delta',
                          side_effect=AssertionError('vehicle rebuilt territory')), \
             patch.object(run, 'discover_and_queue_new_territory_conflicts',
                          side_effect=AssertionError('vehicle discovered conflicts')):
            self.capture(vehicle=True)
        after = self.progression.get('attacker')
        self.assertEqual(before['level'], after['level'])
        self.assertEqual(before['respect'], after['respect'])
        self.assertFalse(run.territory_store.list_captured_targets('attacker')[0]['stationary'])

    def capture(self, contested=False, vehicle=False):
        target = dict(target_id='poi:test', target_mode='standard', label='Test',
                      lat=52., lng=21., source_type='poi',
                      security={key: True for key in SECURITY_KEYS},
                      actions_allowed=dict(scan_ports=True, sniff=True, trace=True, exploit=False))
        app = dict(id='legacy-xmapper', name='XMapper', interface='choice',
                   map_actions=['exploit'], levels=[dict(options=[dict(label='Hack', effect={key: False for key in SECURITY_KEYS})])])
        if vehicle:
            # Older saved markers can lack generated; source identity still
            # must prevent a car becoming a stationary territory anchor.
            target.update(source_type='vehicle', label='VW')
            app['map_actions'] = ['car_hack']
        if contested:
            self.users.save_profile(read_tests.valid_profile('victim'))
            run.territory_store.save_captured_target('victim', target)
            target.update(target_mode='territory_contest', contest_owner_username='victim',
                          expected_owner_username='victim', ownership_version=1)
        self.inventory.install_app('attacker', app, purchase_key='legacy')
        run.player_target_runtime_store.upsert_aimed('attacker', target)
        run.player_marked_target_store.ensure_seeded('attacker')
        with self.no_heavy():
            response = self.client.post('/gonna-win', json=dict(app_id=app['id'], choice_id=0, target=target))
            self.assertEqual(response.status_code, 200, response.json)
            self.assertTrue(response.json['success'], response.json)
            self.assertEqual(len(run.territory_store.list_captured_targets('attacker')), 1)
            self.assertFalse(run.player_target_runtime_store.get_active_target('attacker'))
            if contested:
                self.assertEqual(run.territory_store.list_captured_targets('victim'), [])


if __name__ == '__main__':
    unittest.main()
