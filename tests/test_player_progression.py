import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import database
from database import UserStore, TerritoryProgressionReceiptStore, db_connect, ProfileRecoveryRequired
from player_progression import PlayerProgressionStore, overlay, CHECKPOINT
from tools.migrate_player_progression import migrate
from tests.test_hot_path_recovery import complete_profile


class PlayerProgressionTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=str(Path(tmp.name)/'game.sqlite')
        self.users=UserStore(self.path,seed_path=str(Path(tmp.name)/'missing.json'))
        self.profile=dict(complete_profile('alice'),level=10,respect=100)
        self.users.save_profile(self.profile)
        self.receipts=TerritoryProgressionReceiptStore(self.path)
        self.store=PlayerProgressionStore(self.path)
        migrate(self.path,['alice'],apply=True)

    def receipt(self,key='capture-1'):
        return self.receipts.ensure(key,'alice',{})['receipt_id']

    def no_heavy(self):
        original=database.InstrumentedConnection.execute
        def execute(conn,sql,*args,**kwargs):
            if 'profile_json' in sql.lower() or 'select * from users' in sql.lower():
                raise AssertionError('Heavy SQL: '+sql)
            return original(conn,sql,*args,**kwargs)
        return patch.object(database.InstrumentedConnection,'execute',execute)

    def test_atomic_reward_messages_retry_and_untouched_payload(self):
        receipt=self.receipt()
        with db_connect(self.path) as conn:
            before=conn.execute("SELECT profile_json,profile_checksum FROM users WHERE username='alice'").fetchone()
        with self.no_heavy():
            result=self.store.settle(receipt,dict(levels_gained=1,respect_gain=25),
                {'total_area':123},'123 m2',messages=[{'title':'Reward','text':'+25'}])
            duplicate=self.store.settle(receipt,dict(levels_gained=999,respect_gain=999))
            self.assertTrue(result['ok'])
            self.assertTrue(duplicate['duplicate'])
            self.assertEqual(self.store.get('alice')['level'],11)
            self.assertEqual(self.store.get('alice')['respect'],125)
        with db_connect(self.path) as conn:
            after=conn.execute("SELECT profile_json,profile_checksum FROM users WHERE username='alice'").fetchone()
            self.assertEqual(tuple(before),tuple(after))
            self.assertEqual(conn.execute('SELECT count(*) FROM system_messages').fetchone()[0],1)
            view=overlay(conn,'alice',copy.deepcopy(self.profile))
            self.assertEqual(view['level'],11)
            self.assertEqual(view['respect'],125)
            self.assertEqual(overlay(conn,'alice',copy.deepcopy(view)),view)

    def test_parallel_receipts_and_duplicate_do_not_lose_rewards(self):
        first,second=self.receipt('one'),self.receipt('two')
        with self.no_heavy(),ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda rid:self.store.settle(rid,dict(levels_gained=1,respect_gain=5)),
                                  [first,second,first]))
        self.assertEqual(sum(bool(item['duplicate']) for item in results),1)
        self.assertEqual(self.store.get('alice')['level'],12)
        self.assertEqual(self.store.get('alice')['respect'],110)

    def test_failed_notification_rolls_back_reward_and_receipt(self):
        receipt=self.receipt()
        with self.no_heavy(),patch.object(self.store.messages,'add_message',side_effect=RuntimeError('write failure')):
            with self.assertRaises(RuntimeError):
                self.store.settle(receipt,dict(levels_gained=1,respect_gain=5),messages=[{'text':'Reward'}])
        self.assertEqual(self.store.get('alice')['level'],10)
        self.assertEqual(self.receipts.get(receipt)['status'],'pending')

    def test_missing_projection_fails_closed(self):
        receipt=self.receipt()
        with db_connect(self.path) as conn:
            conn.execute("DELETE FROM user_capability_projection WHERE username='alice'")
        with self.no_heavy(),self.assertRaises(ProfileRecoveryRequired):
            self.store.settle(receipt,dict(levels_gained=1,respect_gain=5))
        self.assertEqual(self.receipts.get(receipt)['status'],'pending')

    def test_offline_migration_is_idempotent_and_dry_run_does_not_write(self):
        self.users.save_profile(complete_profile('bob'))
        with db_connect(self.path) as conn:
            before=conn.execute('SELECT count(*) FROM player_progression').fetchone()[0]
        with db_connect(self.path) as conn:
            conn.execute("DELETE FROM player_progression WHERE username='bob'")
            before=conn.execute('SELECT count(*) FROM player_progression').fetchone()[0]
        self.assertEqual(migrate(self.path,['bob'])[0]['status'],'ready')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_progression').fetchone()[0],before)
        self.assertEqual(migrate(self.path,['bob'],apply=True)[0]['status'],'seeded')
        self.assertEqual(migrate(self.path,['bob'],apply=True)[0]['status'],'already_seeded')
        self.assertEqual(migrate(self.path,['absent'])[0]['status'],'review')

    def test_profile_write_preserves_reward_once_and_later_award(self):
        self.store.settle(self.receipt(),dict(levels_gained=1,respect_gain=25))
        profile=self.users.get_profile('alice')
        self.assertEqual((profile['level'],profile['respect']),(11,125))
        record=self.users.get_profile_with_revision('alice')
        changed=self.users.patch_profile_guarded('alice',{'nick':'Changed'},source='test.progression.compatibility')
        self.assertEqual(changed['profile']['level'],11)
        self.assertEqual(self.store.get('alice')['level'],11)
        self.store.settle(self.receipt('later'),dict(levels_gained=1,respect_gain=7))
        self.assertEqual(self.store.get('alice')['level'],12)
        self.assertEqual(self.users.get_profile('alice')['respect'],132)
        # Absolute legacy mutations start from the overlaid current value.
        self.users.patch_profile_guarded('alice',{'respect':130},source='test.progression.spend')
        self.assertEqual(self.store.get('alice')['respect'],130)
        with self.assertRaises(database.ProfileWriteConflict):
            self.users.save_profile_guarded(record['profile'],expected_revision=record['profile_revision'],
                                           source='test.progression.stale')

    def test_small_readers_see_same_rewards_without_heavy_profile(self):
        identity=database.UserIdentityProjectionStore(self.path)
        capability=database.UserCapabilityProjectionStore(self.path)
        with self.no_heavy():
            self.receipts.settle(self.receipt(),dict(levels_gained=2,respect_gain=9),{},'updated')
            self.assertEqual(capability.get_capabilities('alice')['level'],12)
            self.assertEqual(identity.get_creator_identity('alice')['respect'],109)
            self.assertEqual(identity.get_desktop_boot('alice')['respect'],109)

    def test_invalid_checkpoint_and_missing_ledger_fail_closed(self):
        for marker in ({'version':999}, {'version':1,'level_gain':-1,'respect_gain':0},
                       {'version':1,'level_gain':True,'respect_gain':0}):
            with db_connect(self.path) as conn,self.assertRaises(ProfileRecoveryRequired):
                overlay(conn,'alice',dict(self.profile,**{CHECKPOINT:marker}))
        with db_connect(self.path) as conn:
            view=overlay(conn,'alice',copy.deepcopy(self.profile))
            conn.execute("DELETE FROM player_progression WHERE username='alice'")
            with self.assertRaises(ProfileRecoveryRequired):overlay(conn,'alice',view)

    def test_legacy_stats_update_and_full_save_do_not_duplicate_reward(self):
        self.store.settle(self.receipt(),dict(levels_gained=1,respect_gain=2),{'total_area':50},'50')
        record=self.users.get_profile_with_revision('alice')
        record['profile']['nick']='Updated'
        self.users.save_profile_guarded(record['profile'],expected_revision=record['profile_revision'],source='test.full')
        self.assertEqual(self.store.get('alice')['level'],11)
        self.users.patch_profile_guarded('alice',{'territory_stats':{'total_area':60},'exp':'60'},source='test.stats')
        self.assertEqual(self.store.get('alice')['territory_stats'],{'total_area':60})
        self.assertEqual(self.store.get('alice')['exp'],'60')

    def test_reward_during_patch_retry_is_not_lost_by_absolute_respect_update(self):
        receipt=self.receipt()
        prepare=database._prepare_profile_lkg
        injected=[]
        def concurrent_award(profile):
            if not injected:
                injected.append(True)
                self.store.settle(receipt,dict(levels_gained=1,respect_gain=25))
            return prepare(profile)
        with patch.object(database,'_prepare_profile_lkg',side_effect=concurrent_award):
            self.users.patch_profile_guarded('alice',{'respect':98},source='test.concurrent.spend')
        self.assertEqual(self.store.get('alice')['respect'],123)
        self.assertEqual(self.store.get('alice')['level'],11)

    def test_account_deletion_does_not_leave_a_reward_ledger(self):
        self.assertTrue(self.users.delete_user('alice'))
        with db_connect(self.path) as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM player_progression WHERE username='alice'").fetchone())

    def test_session_precommit_rejection_cannot_award_or_consume_receipt(self):
        receipt=self.receipt()
        with patch.object(database,'_run_profile_precommit_guard',side_effect=database.ProfilePrecommitRejected('stale session')):
            with self.assertRaises(database.ProfilePrecommitRejected):
                self.store.settle(receipt,dict(levels_gained=1,respect_gain=5))
        self.assertEqual(self.store.get('alice')['level'],10)
        self.assertEqual(self.receipts.get(receipt)['status'],'pending')

    def test_strategic_wrapper_uses_current_level_without_full_profile(self):
        receipt=self.receipt('strategic')
        with self.no_heavy():
            result=self.receipts.settle_strategic(receipt,
                encirclement={'awarded':True,'transferred_pillar_count':3},
                conflict_resolutions=[{'conflict_id':'one','resolution_version':1}])
            self.assertEqual(result['result']['totals']['level_before'],10)
            self.assertEqual(self.store.get('alice')['level'],12)
            self.assertEqual(self.store.get('alice')['respect'],113)


if __name__=='__main__':unittest.main()
