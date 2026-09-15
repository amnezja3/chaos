import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import run
import test_intruder_kicker as kicker
from database import db_connect


class AreaIntrusionAlarmTest(unittest.TestCase):
    setUp = kicker.IntruderKickerTest.setUp
    seed = kicker.IntruderKickerTest.seed
    prepare = kicker.IntruderKickerTest.prepare

    def setup_intruder(self, heavy=False):
        self.prepare(heavy=heavy)
        record = self.users.get_profile_with_revision('victim')
        self.users.patch_profile_guarded('victim', {'clan': '', 'ghost_clan_code': ''},
                                        source='test.alarm_fixture', expected_revision=record['profile_revision'])

    def enter(self):
        return run.notify_area_intrusion('victim', 52.2, 21.0)

    def test_new_intrusion_after_consumed_alarm_has_new_id(self):
        self.setup_intruder(heavy=True)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full profile')), \
             patch.object(self.users, 'list_profiles', side_effect=AssertionError('all profiles')):
            self.assertIsNotNone(self.enter())
            first = self.client.get('/system-messages').json
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]['type'], 'warning')
            self.enter()
            self.assertEqual(self.client.get('/system-messages').json, [])
            with db_connect(self.path) as conn:
                conn.execute("UPDATE area_events SET created_at='2000-01-01T00:00:00'")
            self.enter()
            second = self.client.get('/system-messages').json
            self.assertEqual(len(second), 1)
            self.assertNotEqual(first[0]['message_id'], second[0]['message_id'])
            self.assertEqual(first[0]['text'], second[0]['text'])
        self.assertEqual(self.messages.consume_pending('victim'), [])

    def test_same_clan_and_outside_do_not_alarm(self):
        self.prepare()
        self.assertIsNone(self.enter())
        self.assertIsNone(run.notify_area_intrusion('victim', 53, 22))
        self.assertEqual(self.messages.consume_pending('attacker'), [])

    def test_static_territory_detection_alarms_once_without_profiles(self):
        self.setup_intruder()
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('full profile')), \
             patch.object(self.users, 'list_profiles', side_effect=AssertionError('all profiles')):
            first = run.sync_static_area_intruders_for_owner('attacker', [self.area])
            self.assertEqual(len(first), 1)
            self.assertEqual(len(self.messages.consume_pending('attacker')), 1)
            self.enter()
            self.assertEqual(run.sync_static_area_intruders_for_owner('attacker', [self.area]), [])
            self.assertEqual(self.messages.consume_pending('attacker'), [])

    def test_concurrent_producers_emit_one_alarm(self):
        self.setup_intruder()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.enter(), range(2)))
        self.assertEqual(len(self.messages.consume_pending('attacker')), 1)
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM area_events WHERE event_type='intruder_enter'").fetchone()[0], 1)

    def test_message_failure_rolls_back_intrusion_event(self):
        self.setup_intruder()
        with patch.object(self.messages, 'add_message', side_effect=RuntimeError('write failure')):
            with self.assertRaises(RuntimeError):
                self.enter()
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM area_events WHERE event_type='intruder_enter'").fetchone()[0], 0)
        self.enter()
        self.assertEqual(len(self.messages.consume_pending('attacker')), 1)
