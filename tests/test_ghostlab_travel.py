import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
import database
from database import db_connect
from ghostlab_store import GhostLabStore, GhostLabError
from ghostlab_travel import TravelStore
from ghostlab_registry import default_blueprint, validate_fields
from tests import test_ghostlab_alignment as alignment
from tests.test_player_hack_read_paths import valid_profile


class GhostLabTravelTest(unittest.TestCase):
    no_heavy = alignment.GhostLabAlignmentTest.no_heavy

    def setUp(self):
        alignment.GhostLabAlignmentTest.setUp(self)
        self.store = GhostLabStore(self.path)
        self.travel = TravelStore(self.path)
        self.wallet = database.WalletBalanceStore(self.path)
        self.positions = database.PlayerPositionStore(self.path)
        self.deltas = database.GameStateDeltaBus(self.path)
        for name, store in [('ghostlab_store', self.store), ('travel_store', self.travel),
                ('wallet_balance_store', self.wallet), ('player_position_store', self.positions),
                ('delta_bus', self.deltas), ('resources_store', database.JsonResourceStore(self.path))]:
            self.stack.enter_context(patch.object(run, name, store))
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_TRAVEL_RUNTIME_ENABLED='true',
            CHAOS_GHOSTLAB_RUNTIME_ACTORS='attacker,victim,admin'))
        for username in ('attacker','victim','admin'):
            profile = dict(valid_profile(username), level=40, respect=500)
            self.users.save_profile(profile)
            self.inventory.seed_from_profile(username, profile)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghostlab_migrations SET status='complete'")
        self.project = self.store.create('victim', dict(name='Ostrowiec',template_id='travel_ticket',
            icon='🎫',description='Miejsce autora',blueprint=dict(default_blueprint('travel_ticket'),
                lat=50.943,lng=21.386,city='Ostrowiec',place_name='Rynek')), 'create-ticket')
        self.publish()
        self.wallet.credit('attacker',100000,transaction_key='fund',source='test')

    def publish(self, **changes):
        if changes:
            self.project = self.store.update('victim',self.project['id'],self.project['revision'],
                {'blueprint':dict(self.project['blueprint'],**changes)})
        self.project = self.store.compile('victim',self.project['id'],self.project['revision'],
            self.project['blueprint'],run.build_ghostlab_artifact)
        self.project, self.offer = self.store.publish('victim',self.project['id'],self.project['revision'],
            self.project['artifact']['artifact_id'],run.build_ghostlab_googleplex_app,{'level':40,'respect':500})

    def buy(self, key='journey', offer=None, **extra):
        offer = offer or self.offer
        return self.client.post('/install-app',json=dict(app_id=offer['id'],client_action_key=key,
            expected_artifact_id=offer.get('artifact_id'),expected_price=offer['price'],**extra))

    def state(self):
        return self.client.get('/api/travel-tickets/'+self.offer['id'])

    def react(self, receipt, reaction='happy'):
        return self.client.post('/api/travel-tickets/'+self.offer['id']+'/reaction',
            json={'receipt':receipt,'reaction':reaction})

    def test_catalog_purchase_reaction_no_heavy_and_no_launcher(self):
        before = self.wallet.get_balance('victim')
        with self.no_heavy():
            catalog = self.client.get('/api/catalog')
            self.assertEqual(catalog.status_code,200,catalog.json)
            ticket = next(t for t in catalog.json if t['id']==self.offer['id'])
            self.assertFalse(ticket['installed'])
            self.assertEqual(ticket['product_type'],'travel_ticket')
            self.assertIsNone(self.state().json['reaction_receipt'])
            self.assertEqual(self.react('forged').status_code,403)
            response = self.buy(lat=0,lng=0)
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['travel']['position'],{'lat':50.943,'lng':21.386})
            self.assertEqual(self.wallet.get_balance('victim'),before+self.offer['price'])
            self.assertFalse(self.inventory.has_app('attacker',self.offer['id']))
            receipt = response.json['reaction_receipt']
            self.assertEqual(self.react(receipt).status_code,200)
            self.assertEqual(self.react(receipt,'bad').status_code,200)
            self.assertEqual(self.state().json['counts'],{'bad':1,'happy':0,'very_happy':0})
            self.assertTrue(self.buy().json['duplicate'])
            self.assertEqual(self.wallet.get_balance('victim'),before+self.offer['price'])
            self.assertNotIn(self.offer['id'],self.inventory.catalog_download_counts([self.offer['id']]))

    def test_builtin_and_self_paid_tickets_are_bounded_replay_safe(self):
        ticket = next(t for t in run.googleplex_product_catalog() if t['id']=='ticket_warszawa')
        with self.no_heavy():
            first = self.buy(offer=ticket)
            self.assertEqual(first.status_code,200,first.json)
            self.positions.upsert('attacker',{'lat':1,'lng':2},source='test')
            repeated = self.buy(offer=ticket)
            self.assertTrue(repeated.json['duplicate'])
            self.assertIsNone(repeated.json['travel'])
            self.assertEqual(self.positions.get('attacker')['lat'],1)
        self.generation.authenticate(self.client,'admin')
        with self.no_heavy():
            before = self.wallet.get_balance('admin')
            first = self.buy(offer=ticket)
            self.assertEqual(first.status_code,200,first.json)
            self.assertTrue(self.buy(offer=ticket).json['duplicate'])
            self.assertEqual(self.wallet.get_balance('admin'),before)
            self.assertEqual(self.client.post('/api/travel-tickets/'+ticket['id']+'/reaction',
                json={'receipt':first.json['travel']['receipt'],'reaction':'happy'}).status_code,403)

    def test_rollback_and_stale_quote_and_withdrawal(self):
        before = self.wallet.get_balance('attacker')
        with self.no_heavy(), patch.object(self.deltas,'record_change',side_effect=RuntimeError('failure')):
            response = self.buy()
            self.assertEqual(response.status_code,500,response.json)
        self.assertEqual(self.wallet.get_balance('attacker'),before)
        self.assertIsNone(self.positions.get('attacker'))
        self.assertIsNone(self.state().json['reaction_receipt'])
        old = self.offer
        self.publish(lng=21.4)
        with self.no_heavy():
            self.assertEqual(self.buy(offer=old).json['reason'],'offer_changed')
            self.store.withdraw('victim',self.project['id'],self.project['revision'])
            self.assertEqual(self.buy().json['reason'],'publication_withdrawn')
            self.assertEqual(self.wallet.get_balance('attacker'),before)

    def test_reactions_follow_destination_and_require_owned_receipt(self):
        receipt = self.buy().json['reaction_receipt']
        self.react(receipt)
        self.publish(lng=22)
        with self.no_heavy():
            state = self.state().json
            self.assertEqual(state['counts']['happy'],0)
            self.assertEqual(state['historical_counts']['happy'],1)
            self.assertIsNone(state['reaction_receipt'])
            self.assertTrue(self.buy().json['reason']=='purchase_key_conflict')
            second = self.buy('second').json['reaction_receipt']
            self.react(second,'very_happy')
            self.assertEqual(sum(self.state().json['counts'].values()),1)
            self.assertEqual(sum(self.state().json['historical_counts'].values()),0)
        self.generation.authenticate(self.client,'victim')
        with self.no_heavy():
            self.assertEqual(self.react(receipt).status_code,403)

    def test_concurrency_same_key_one_journey(self):
        def purchase():
            return self.travel.purchase('attacker',self.offer['id'],'parallel',self.offer['artifact_id'],self.offer['price'],
                system_catalog=run.googleplex_product_catalog(),cities=run.TRAVEL_CITIES,wallet=self.wallet,
                positions=self.positions,deltas=self.deltas,inventory=self.inventory,requirements=lambda *args:None)
        before = self.wallet.get_balance('attacker')
        with self.no_heavy(), ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _:purchase(),range(2)))
        self.assertEqual(sum(not r['duplicate'] for r in results),1)
        self.assertEqual(self.wallet.get_balance('attacker'),before-self.offer['price'])

    def test_invalid_coordinates_flag_and_arrest(self):
        for value in (float('nan'),float('inf'),91,True,'50'):
            self.assertTrue(validate_fields('travel_ticket',dict(default_blueprint('travel_ticket'),lat=value)))
        before = self.wallet.get_balance('attacker')
        with self.no_heavy(), patch.dict(os.environ,CHAOS_GHOSTLAB_TRAVEL_RUNTIME_ENABLED='false'):
            self.assertEqual(self.buy().json['reason'],'ticket_runtime_disabled')
        from datetime import datetime, timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        sanctions = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn,encounter_id='arrest',actor_id='attacker',incident_id='i',
                plan=plan_consequence(5,0),now=datetime.now(timezone.utc))
        with self.no_heavy():
            self.assertEqual(self.buy().status_code,409)
            ticket = next(t for t in run.googleplex_product_catalog() if t['id']=='ticket_warszawa')
            self.assertEqual(self.buy(offer=ticket).status_code,409)
            self.assertEqual(self.wallet.get_balance('attacker'),before)

    def test_legacy_receipt_retry_does_not_charge_or_teleport(self):
        from response_network.travel_purchase import purchase_travel
        import hashlib
        ticket = next(t for t in run.googleplex_product_catalog() if t['id']=='ticket_warszawa')
        key = 'old-browser-key'
        legacy_key = 'googleplex:purchase:attacker:ticket_warszawa:' + hashlib.sha256(key.encode()).hexdigest()
        purchase_travel(self.wallet,self.positions,actor='attacker',payee='admin',price=ticket['price'],
            key=legacy_key,note='googleplex:ticket_warszawa',destination={'lat':52,'lng':21})
        self.positions.upsert('attacker',{'lat':1,'lng':2},source='test')
        before = self.wallet.get_balance('attacker')
        with self.no_heavy():
            response = self.buy(key,offer=ticket)
            self.assertEqual(response.status_code,200,response.json)
            self.assertTrue(response.json['duplicate'])
            self.assertIsNone(response.json['travel'])
            self.assertEqual(self.positions.get('attacker')['lat'],1)
            self.assertEqual(self.wallet.get_balance('attacker'),before)

    def test_large_profile_and_no_funds_never_use_heavy_fallback(self):
        record = self.users.get_profile_with_revision('attacker')
        self.users.save_profile_guarded(dict(record['profile'],padding='x'*(35*1024*1024)),
            source='test',expected_revision=record['profile_revision'])
        with self.no_heavy():
            self.assertEqual(self.client.get('/api/catalog').status_code,200)
            self.assertEqual(self.buy().status_code,200)
            self.wallet.debit('attacker',self.wallet.get_balance('attacker'),transaction_key='empty',source='test')
            position = self.positions.get('attacker')
            denied = self.buy('no-money')
            self.assertEqual(denied.json['reason'],'insufficient_hc')
            self.assertEqual(self.positions.get('attacker'),position)
            from admin_panel import page
            admin = page(self.path,'ghostlab',template_id='travel_ticket')['items'][0]
            self.assertIn('Ostrowiec',admin['destination'])
            self.assertIn('happy',admin['reactions'])
