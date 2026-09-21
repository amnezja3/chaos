import unittest
from contextlib import ExitStack
from unittest.mock import patch

import run
from session_generation_fixture import SessionGenerationFixture


class ConflictSupportPillarAimTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        generation = SessionGenerationFixture().start()
        self.addCleanup(generation.stop)
        self.client = run.app.test_client()
        self.headers = generation.authenticate(self.client, 'robot')
        self.target = {'lat':52.0998879, 'lng':21.0602215, 'label':'POI-6AC002',
            'target_id':'map:52.09989:21.06022:POI-6AC002', 'node_role':'pillar'}
        self.conflict = {'conflict_id':'territory_conflict_3212cccd8a589e32',
            'participants':['robot','main'], 'status':'active', 'area_ids':[],
            'intersections':[[[52.10,21.06],[52.10,21.07],[52.11,21.07],[52.11,21.06]]],
            'targets':[{'owner_username':'main','status':'contested','node_role':'pillar',
                       'target':self.target}]}
        context = {'member_conflict_ids':set(), 'engagements':[], 'ownership_by_target_id':{},
                   'profile_cache':{}, 'accepted_contacts':set()}
        self.context = context
        for owner, name, value in (
            (run.territory_store,'list_player_areas',[]),
            (run.territory_conflict_store,'list_active_for_player',[self.conflict]),
            (run.territory_conflict_store,'list_active',[self.conflict]),
            (run,'build_territory_engagement_visibility_context',context),
            (run,'territory_combat_relation','hostile'),
            (run,'territory_viewer_relation','enemy'),
            (run.user_store,'get_profile',{'username':'main','nick':'Main'}),
            (run.user_store,'get_profile_identity',{'username':'robot'}),
            (run,'find_foreign_area_for_point',{'owner_username':'main','owner_nick':'Main'}),
            (run.player_target_runtime_store,'get_active_target',{}),
        ):
            self.stack.enter_context(patch.object(owner,name,return_value=value))
        self.persist = self.stack.enter_context(patch.object(run,'set_player_aimed_target',
            side_effect=lambda username,profile,target,**kwargs: target))
        self.stack.enter_context(patch.object(run,'record_map_target_delta'))

    def aim(self, **changes):
        payload = {**self.target, 'target_mode':'territory_contest',
                   'stable_conflict_id':self.conflict['conflict_id'], **changes}
        return self.client.post('/api/map/aim-target', headers=self.headers, json=payload)

    def test_canonical_support_pillar_outside_overlap_can_be_aimed(self):
        response = self.aim()
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['target']['target_id'],self.target['target_id'])
        self.assertEqual(response.json['target']['target_mode'],'territory_contest')

    def test_outside_inner_remains_protected(self):
        self.target['node_role'] = 'inner'
        self.conflict['targets'][0]['node_role'] = 'inner'
        self.assertEqual(self.aim().status_code,403)
        self.persist.assert_not_called()

    def test_client_cannot_invent_pillar_membership(self):
        self.conflict['targets'] = []
        self.assertEqual(self.aim(node_role='pillar').status_code,403)
        self.persist.assert_not_called()

    def test_legacy_capture_without_known_holder_remains_protected(self):
        self.conflict['targets'][0]['captured'] = True
        self.assertEqual(self.aim().status_code,403)
        self.persist.assert_not_called()

    def test_robot_can_aim_historical_capture_by_main_in_new_conflict(self):
        # Production case: captured on Sep 15, registry reused in Sep 21 conflict.
        self.target.update(previous_owner_username='robot',
            stable_conflict_id='territory_conflict_2dd48c56fc1ffbdd',
            expected_owner_username='robot', ownership_version=1,
            actions_allowed={'exploit':True, 'scan_ports':True})
        self.conflict['targets'][0].update(status='captured', captured=True,
            captured_by='main', previous_owner='robot')
        self.context['ownership_by_target_id'][self.target['target_id']] = {
            'owner_username':'main', 'ownership_version':2}
        response = self.aim()
        self.assertEqual(response.status_code,200,response.json)
        target = response.json['target']
        self.assertEqual(target['stable_conflict_id'],self.conflict['conflict_id'])
        self.assertEqual(target['expected_owner_username'],'main')
        self.assertEqual(target['ownership_version'],2)
        self.assertFalse(any(target['actions_allowed'].values()))

    def test_canonical_current_owner_cannot_attack_stale_enemy_projection(self):
        self.context['ownership_by_target_id'][self.target['target_id']] = {
            'owner_username':'robot', 'ownership_version':3}
        self.assertEqual(self.aim().status_code,403)
        self.persist.assert_not_called()

    def test_same_clan_and_nonparticipant_cannot_use_support_exception(self):
        with patch.object(run,'territory_combat_relation',return_value='protected_same_clan'):
            self.assertEqual(self.aim().status_code,403)
        self.conflict['participants'] = ['someone','main']
        self.assertEqual(self.aim().status_code,403)
        self.persist.assert_not_called()
