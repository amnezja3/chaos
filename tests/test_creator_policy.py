import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

from creator_policy import (generate_contract, power_cap, roll_power, security_effect, configure_draft,
                            validate_effect, validate_presentation, runtime_effect)
from creator_store import CreatorStore
from ghostlab_store import GhostLabError


class CreatorPolicyTest(unittest.TestCase):
    def test_required_files_are_enforced_for_every_interface(self):
        from creator_policy import FILE_REQUIRED_ACTIONS, INTERFACES
        for action in FILE_REQUIRED_ACTIONS:
            for interface in INTERFACES:
                with self.subTest(action=action, interface=interface):
                    contract = generate_contract(dict(name='Tool', icon='X', action=action,
                        interface=interface, creates_file=False), 100)
                    self.assertTrue(contract['creates_file'])
                    self.assertTrue(contract['resource_types'])
        optional = generate_contract(dict(name='Tool', icon='X', action='camera_stream',
            interface='window', creates_file=False), 40)
        self.assertFalse(optional['creates_file'])

    def test_assignment_syntax_boolean_states_and_each_option_level_gate(self):
        data = dict(name='Buttons', icon='X', interface='button_choices', action='exploit', creates_file=False)
        contract = generate_contract(data, 40)
        changes = {'options': [{'effect': 'risk_level=10,firewall=false', 'price': 0},
                               {'effect': 'firewall=true,vpn_enabled=false', 'price': 0}]}
        low = configure_draft(contract, changes, 99)
        self.assertEqual([o['effect'] for o in low['options']], [{}, {}])
        high = configure_draft(contract, changes, 100)
        app = dict(creator_contract_version=1, creator_contract=high, levels=[{'options': [{}, {}]}])
        self.assertEqual(runtime_effect(app, {'firewall': True}, 0), {'risk_level': 10, 'firewall': False})
        self.assertEqual(runtime_effect(app, {'firewall': False}, 1), {'firewall': True, 'vpn_enabled': False})

    def test_bad_assignments_rejected_even_below_level_threshold(self):
        invalid = ['firewall', 'firewall=false,', 'firewall=false,firewall=true',
                   'firewall=1', 'firewall=ON', 'firewall=False', 'risk_level=true',
                   'risk_level=101', 'risk_level=-1', 'risk_level=1.5',
                   'hackcoins=100', '__proto__=false', 'firewall=eval(1)',
                   'firewall=false;alert(1)', ['firewall=false'], {'firewall': []}]
        for level in (99, 100):
            for value in invalid:
                with self.subTest(level=level, value=value), self.assertRaises(ValueError):
                    validate_effect(value, action='exploit', interface='button_choices', level=level)

    def test_approved_caps_and_both_rolls(self):
        for level, cap in [(1,25),(10,50),(20,75),(30,95),(40,100),(100,100)]:
            self.assertEqual(power_cap(level), cap)
            self.assertEqual(roll_power(level, Mock(random=lambda:0))['power'], cap)
            rng = Mock(random=lambda:0.9, randint=Mock(return_value=20))
            self.assertEqual(roll_power(level, rng)['power'],20)
            rng.randint.assert_called_once_with(20,cap-1)
        caps = [power_cap(level) for level in range(1,101)]
        self.assertEqual(caps, sorted(caps))

    def test_effect_unlock_and_validation(self):
        for level in (30,40,99):
            self.assertEqual(validate_effect('security.clear',action='exploit',interface='button_choices',level=level),{})
        for level in (100,101):
            self.assertTrue(validate_effect('security.clear',action='exploit',interface='button_choices',level=level))
        for effect in ({'access_level':9999},{'firewall':1},'unknown'):
            with self.assertRaises(ValueError):
                validate_effect(effect,action='exploit',interface='button_choices',level=100)
        with self.assertRaises(ValueError):
            validate_effect('security.clear',action='exploit',interface='terminal',level=100)

    def test_power_changes_real_boolean_security_not_arbitrary_fields(self):
        data=dict(name='Tool',icon='X',interface='terminal',action='exploit',creates_file=False)
        contract=generate_contract(data,40,Mock(random=lambda:0))
        security={'firewall':True,'vpn_enabled':True,'access_level':8}
        self.assertEqual(security_effect(contract,security),{'firewall':False,'vpn_enabled':False})
        contract['power']=50
        effect=security_effect(contract,security)
        self.assertEqual(len(effect),1)
        self.assertEqual(security_effect(contract,{**security,**effect}),effect)
        with self.assertRaises(ValueError): generate_contract(dict(data,power=100),1)

    def test_presentation_rejects_wrong_types_and_hidden_logic(self):
        for value in ({'name': ['Bad']}, {'commands': 'run'},
                      {'commands': [{'command': 'run', 'logs': [], 'effect': {}}]},
                      {'commands': [{'command': 'run', 'logs': []}, {'command': 'RUN', 'logs': []}]},
                      {'commands': [{'command': '', 'logs': []}]}):
            with self.assertRaises(ValueError):
                validate_presentation('terminal', value)
        with self.assertRaises(ValueError):
            validate_presentation('window', {'button_labels': []})

    def test_runtime_uses_installed_contract_and_validates_choice(self):
        data=dict(name='Tool',icon='X',interface='button_choices',action='exploit',creates_file=False)
        contract=generate_contract(data,40,Mock(random=lambda:0))
        app=dict(creator_contract_version=1,creator_contract=contract,
                 levels=[{'options':[{'effect':{'access_level':999}}]}])
        security={'firewall':True,'access_level':3}
        self.assertEqual(runtime_effect(app,security,0),{'firewall':False})
        self.assertEqual(runtime_effect(app,security,'0'),{'firewall':False})
        self.assertEqual(runtime_effect(app,security,operation_only=True),{})
        for choice in (None, -1, True, '-1', '00', 1):
            with self.assertRaises(ValueError):runtime_effect(app,security,choice)
        # Existing XMapper is dispatched to its original effect handler unchanged.
        self.assertIsNone(runtime_effect({'id':'XMapper','levels':app['levels']},security,0))


class CreatorStoreTest(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store=CreatorStore(str(Path(folder.name)/'creator.sqlite'))
        self.data=dict(name='Tool',icon='X',interface='terminal',action='exploit',creates_file=False,price=0)

    def create(self,key='request-1'):
        return self.store.create('author',self.data,key,40)

    @staticmethod
    def builder(project,version):
        return dict(id=project['app_id'],creator_username=project['owner'],name=project['presentation']['name'],
                    version=version,project_file=project['id']+'.sh',contract=project['contract'],published=True)

    def test_concurrent_retry_does_not_reroll(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.create(),range(4)))
        self.assertTrue(all(p==results[0] for p in results))
        with self.assertRaises(GhostLabError):
            self.store.create('author',dict(self.data,name='Other'),'request-1',40)
        with self.assertRaises(GhostLabError):self.store.get('other',results[0]['id'])

    def test_editions_identity_frozen_logic_and_withdrawal(self):
        project=self.create()
        first=self.store.publish('author',project['id'],1,self.builder)
        self.assertEqual(self.store.publish('author',project['id'],1,self.builder),first)
        for field in ('price','effect','power','creates_file','action'):
            with self.assertRaises(ValueError):self.store.update('author',project['id'],1,{field:100})
        updated=self.store.update('author',project['id'],1,{'name':'Corrected'})
        second=self.store.publish('author',project['id'],updated['revision'],self.builder)
        self.assertEqual(first['id'],second['id'])
        self.assertEqual(first['contract'],second['contract'])
        self.assertEqual(first['name'],'Tool')
        self.assertEqual(second['version'],2)
        self.assertEqual(len(self.store.catalog()),1)
        self.store.withdraw('author',first['project_file'])
        self.assertFalse(self.store.catalog()[0]['published'])
        with self.assertRaises(GhostLabError):self.store.update('author',project['id'],1,{'name':'Stale'})

    def test_draft_configuration_keeps_roll_and_freezes_on_publish(self):
        self.data['interface']='button_choices'
        project=self.create()
        updated=self.store.configure('author',project['id'],1,
            {'price':75,'options':[{'effect':'security.clear','price':10}]},100)
        self.assertEqual(project['contract']['power'],updated['contract']['power'])
        self.assertTrue(updated['contract']['options'][0]['effect'])
        self.store.publish('author',project['id'],2,self.builder)
        with self.assertRaises(GhostLabError):
            self.store.configure('author',project['id'],2,{'price':0},100)
        with self.assertRaises(GhostLabError):
            self.store.configure('author',project['id'],1,{'price':0},100)

    def test_unicode_name_collision_is_atomic(self):
        project=self.create()
        self.store.update('author',project['id'],1,{'name':'ŻÓŁW'})
        self.store.publish('author',project['id'],2,self.builder)
        second=self.create('request-2')
        self.store.update('author',second['id'],1,{'name':'żółw'})
        with self.assertRaises(GhostLabError):
            self.store.publish('author',second['id'],2,self.builder)
        self.assertEqual(self.store.get('author',second['id'])['version'],0)


if __name__=='__main__':unittest.main()
