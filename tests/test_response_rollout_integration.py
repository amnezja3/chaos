"""142.7: scan evidence -> HTTP shutdown -> incident -> patrol -> canonical fine."""
import unittest
from datetime import timedelta
from unittest.mock import patch

import run
from database import db_connect, WalletBalanceStore
from ghostnetwork.repository import GhostNetworkRepository
from session_generation_store import SessionGenerationStore, username_digest
from response_network.incident_store import IncidentStore
from response_network.incident_initializer import IncidentInitializer
from response_network.npc_capsule_store import NPCCapsuleStore
from response_network.npc_capsule_factory import position_at
from response_network.response_dispatcher import ResponseDispatcher
from response_network.encounters import EncounterStore
from response_network.criminal_record import CriminalRecordStore
from response_network.canonical_executor import CanonicalConsequenceExecutor
import test_camera_exposure as camera


class ResponseRolloutIntegrationTest(unittest.TestCase):
    setUp = camera.CameraExposureTest.setUp
    seed = camera.CameraExposureTest.seed
    prepare = camera.CameraExposureTest.prepare
    scene = camera.CameraExposureTest.scene
    operation = camera.CameraExposureTest.operation
    shutdown = camera.CameraExposureTest.shutdown
    refresh = camera.CameraExposureTest.refresh

    def test_shutdown_incident_public_source_offline_then_mapless_execution(self):
        self.scene()
        incidents = IncidentStore(self.path)
        initializer = IncidentInitializer(incidents)
        op = self.operation()
        self.assertEqual(op['operation_risk_meter']['current_heat'], 62)
        self.operations.upsert_operations('attacker', [op])
        initializer.sync_operations([op], now=self.now)
        incident_id = op['operation_risk_meter']['incident_id']
        self.assertTrue(incident_id)

        self.shutdown()  # Actual authenticated HTTP app authorization + canonical write.
        self.assertEqual(self.refresh(op)['current_heat'], 58)
        initializer.sync_operations([op], now=self.now)
        incident = incidents.get(incident_id)
        self.assertEqual(incident['heat'], 58)
        # Camera protection lowers the incident to L1; no fine is due there.
        # Continued operation adds independent time risk and crosses L2 again.
        self.now += timedelta(seconds=30)
        self.assertEqual(self.refresh(op)['camera_modifier'], 0)
        initializer.sync_operations([op], now=self.now)
        incident = incidents.get(incident_id)
        self.assertEqual(incident['level'], 2)
        self.assertIn(incident_id, [i['incident_id'] for i in incidents.list_public(now=self.now)])
        with patch.object(run, 'incident_store', incidents):
            self.assertTrue(run.build_blacknet_incident_facts(self.now))
        with db_connect(self.path) as conn:
            self.assertIsNotNone(conn.execute(
                'SELECT incident_id FROM response_incident_publications WHERE incident_id=?',
                (incident_id,)).fetchone())

        capsules = NPCCapsuleStore(self.path)
        ResponseDispatcher(capsules).dispatch_incident(incident, now=self.now)
        capsule = capsules.list_by_incident(incident_id)[0]
        now = self.now + timedelta(seconds=30)
        point = position_at(capsule, now)
        SessionGenerationStore(self.path)
        GhostNetworkRepository(db_path=self.path)
        wallet = WalletBalanceStore(self.path)
        records = CriminalRecordStore(self.path)
        encounters = EncounterStore(incidents, capsules, self.path, lambda: 1)
        encounters.executor = CanonicalConsequenceExecutor(self.path, incidents, capsules,
            records, wallet, self.inventory, self.operations, self.messages, self.delta)
        with db_connect(self.path) as conn:
            conn.execute("INSERT OR REPLACE INTO wallet_balances(username,balance,version,updated_at) VALUES ('attacker',10000,1,?)", (now.isoformat(),))
            conn.execute('INSERT OR REPLACE INTO account_login_ownership(username_hash,status,created_at,updated_at) VALUES (?,?,?,?)',
                         (username_digest('attacker'), 'logged_out', now.isoformat(), now.isoformat()))
            conn.execute("INSERT OR REPLACE INTO mail_presence(username,last_seen_at) VALUES ('attacker',?)", (now.isoformat(),))
            conn.execute("UPDATE player_positions SET lat=?,lng=?,version=version+1,updated_at=? WHERE username='attacker'",
                         (point['lat'], point['lng'], now.isoformat()))
        with patch.dict('os.environ', {
            'CHAOS_RESPONSE_ENCOUNTERS_ENABLED':'true',
            'CHAOS_RESPONSE_QUALIFICATION_MODE':'observe',
            'CHAOS_RESPONSE_EXECUTION_MODE':'enforce',
            'CHAOS_RESPONSE_EXECUTION_ACTORS':'*'}):
            encounters.scan(now=now)
            with db_connect(self.path) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM response_encounters').fetchone()[0], 0)
                conn.execute("UPDATE account_login_ownership SET status='active' WHERE username_hash=?", (username_digest('attacker'),))
            # No frontend request: worker detects a non-main account after return online.
            encounters.scan(now=now)
            encounters.scan(now=now)
        with db_connect(self.path) as conn:
            row = conn.execute("SELECT chance,execution_status FROM response_encounters WHERE actor_id='attacker'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(tuple(row), (80, 'executed'))
            self.assertEqual(conn.execute("SELECT executed_count FROM response_criminal_records WHERE actor_id='attacker'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT balance FROM wallet_balances WHERE username='attacker'").fetchone()[0], 9970)
            self.assertEqual(conn.execute('SELECT count(*) FROM response_penalty_history').fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM wallet_balance_events WHERE reason='response.fine'").fetchone()[0], 1)
