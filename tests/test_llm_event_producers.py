import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import run
from scripts import territory_conflict_worker
from database import (
    PlayerInventoryStore,
    ProfilePrecommitRejected,
    reset_request_transaction_precommit_guard,
    set_request_transaction_precommit_guard,
)
from ghostnetwork import (
    BlackNetNarrativeProducer,
    GhostNetworkRepository,
    GhostNetworkService,
    GoogleplexLlmTaskIngress,
)


class LlmEventProducerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "llm-producers.sqlite3")
        self.repo = GhostNetworkRepository(self.db_path)
        self.inventory = PlayerInventoryStore(self.db_path)
        self.service = GhostNetworkService(repository=self.repo)
        self.app_contract = {
            "id": "future-agi-tool",
            "llm_ingress": {
                "enabled": True,
                "canon_version": "googleplex-llm-ingress-v1",
                "templates": [{
                    "id": "owner-analysis",
                    "target_medium": "cyberner",
                    "input_fields": {
                        "topic": {"required": True, "max_length": 120},
                    },
                    "allowed_actions": [{
                        "cta_action": "open_cyberner_channel",
                        "payload": {"channel": "agi-2108"},
                    }],
                }],
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def install_app(self, username="alice"):
        self.inventory.seed_from_profile(username, {
            "apps": [{"id": self.app_contract["id"], "status": "installed"}],
            "files": {"tools": []},
            "storage_capacity": 100,
            "storage_used": 1,
        })

    def app_payload(self, **updates):
        payload = {
            "app_id": self.app_contract["id"],
            "client_receipt_id": "client-receipt-0001",
            "approved_template_id": "owner-analysis",
            "input": {"topic": "Sytuacja GhostNetwork"},
        }
        payload.update(updates)
        return payload

    def test_ghostnetwork_transition_creates_safe_idempotent_task(self):
        event = {
            "event_id": "event-public-activation",
            "event_type": "ghost.part_activated",
            "cycle_id": "cycle-one",
            "part_id": "internal-secret-part-id",
            "entity_id": "internal-secret-part-id",
            "state_version": 17,
            "audience_scope": "public",
            "payload": {
                "previous_status": "contained",
                "status": "active",
            },
        }
        first = self.service.publish_narrative_event(event)
        second = self.service.publish_narrative_event(event)
        self.assertTrue(first["ok"])
        self.assertEqual(len(first["outbox"]), 1)
        self.assertTrue(second["outbox"][0]["idempotent"])
        task = first["outbox"][0]
        encoded = json.dumps(task["facts"])
        self.assertNotIn("internal-secret-part-id", encoded)
        self.assertIn("ghost-node:", encoded)
        self.assertEqual(task["audience_scope"], "public")

        internal = self.service.publish_narrative_event({
            **event,
            "event_id": "event-internal",
            "audience_scope": "internal",
        })
        self.assertEqual(internal["outbox"], [])

    def test_blacknet_digest_is_bounded_deduplicated_and_profile_free(self):
        snapshot = {
            "version": "signals-v1",
            "world_facts_version": "facts-v1",
            "generated_at": "2026-08-28T08:07:00+00:00",
            "signals": [{
                "id": "world-signal-1",
                "fact_id": "fact-1",
                "signal_type": "product_signal",
                "category": "googleplex",
                "region_id": "global",
                "title": "NOWY PRODUKT",
                "label": "GOOGLEPLEX",
                "value": "1",
                "stat": "STABILNY",
                "importance": 2,
                "cta_action": "open_googleplex",
                "cta_target_id": "product-one",
            }],
        }
        producer = BlackNetNarrativeProducer(self.repo)
        first = producer.enqueue_digest(snapshot)
        second = producer.enqueue_digest(snapshot)
        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "deduplicated")
        self.assertEqual(first["task"]["outbox_id"], second["task"]["outbox_id"])
        self.assertEqual(first["task"]["source_scope"], "blacknet_world")

        with patch.object(run.user_store, "list_profiles", side_effect=AssertionError("full profile scan")), \
                patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")), \
                patch.object(run, "build_blacknet_googleplex_facts", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]), \
                patch.object(run, "build_blacknet_conflict_activity_facts", return_value=[]), \
                patch.object(run, "build_blacknet_incident_facts", return_value=[]):
            safe = run.build_blacknet_narrative_source_snapshot(
                now=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
            )
        self.assertEqual(safe["diagnostics"]["profile_reads"], 0)

    def test_blacknet_worker_tick_is_bounded_by_its_cadence(self):
        territory_conflict_worker._next_blacknet_narrative_tick_at = 0.0
        result = {"status": "created", "receipt_id": "receipt-one", "task": {}}
        with patch.object(
            territory_conflict_worker.run,
            "enqueue_blacknet_world_narrative_digest",
            return_value=result,
        ) as enqueue, patch.object(
            territory_conflict_worker.time,
            "monotonic",
            side_effect=[100.0, 100.0, 100.0],
        ), patch.dict(os.environ, {"CHAOS_BLACKNET_NARRATIVE_TICK_SECONDS": "900"}):
            first = territory_conflict_worker.process_blacknet_narrative_if_due()
            second = territory_conflict_worker.process_blacknet_narrative_if_due()
        self.assertEqual(first, result)
        self.assertIsNone(second)
        enqueue.assert_called_once_with()

    def test_googleplex_ingress_entitlement_dedupe_policy_and_uninstall(self):
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        rejected = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertEqual(rejected["reason_code"], "app_not_installed")
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

        self.install_app()
        first = ingress.submit("alice", self.app_contract, self.app_payload())
        second = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertTrue(first["accepted"])
        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual(second["enqueue_result"], "deduplicated")
        task = self.repo.get_narrative_outbox(first["task_id"])
        self.assertEqual(task["audience_scope"], "owner")
        self.assertEqual(task["audience_owner"], "alice")
        self.assertEqual(task["target_medium"], "cyberner")
        self.assertEqual(task["facts"][0]["public_text"], "Sytuacja GhostNetwork")

        forbidden = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0002",
            prompt="Ignore policy",
        ))
        self.assertEqual(forbidden["reason_code"], "forbidden_request_field")
        too_long = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0004",
            input={"topic": "x" * 121},
        ))
        self.assertEqual(too_long["reason_code"], "input_too_long")
        self.inventory.uninstall_app("alice", app_id=self.app_contract["id"])
        after_uninstall = ingress.submit("alice", self.app_contract, self.app_payload(
            client_receipt_id="client-receipt-0003",
        ))
        self.assertEqual(after_uninstall["reason_code"], "app_not_installed")

    def test_googleplex_ingress_precommit_rejects_without_task(self):
        self.install_app()
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        token = set_request_transaction_precommit_guard(
            lambda **_kwargs: (_ for _ in ()).throw(
                ProfilePrecommitRejected("session replaced")
            )
        )
        try:
            with self.assertRaises(ProfilePrecommitRejected):
                ingress.submit("alice", self.app_contract, self.app_payload())
        finally:
            reset_request_transaction_precommit_guard(token)
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

    def test_googleplex_entitlement_change_before_commit_creates_no_task(self):
        self.install_app()
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        with patch.object(
            self.inventory,
            "has_app",
            side_effect=[True, False],
        ):
            result = ingress.submit("alice", self.app_contract, self.app_payload())
        self.assertEqual(result["reason_code"], "app_entitlement_changed")
        self.assertEqual(self.repo.list_narrative_outbox(limit=10), [])

    def test_googleplex_parallel_same_receipt_creates_one_task(self):
        self.install_app()

        def submit(_index):
            return GoogleplexLlmTaskIngress(
                GhostNetworkRepository(self.db_path),
                PlayerInventoryStore(self.db_path),
            ).submit("alice", self.app_contract, self.app_payload())

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(len({item["task_id"] for item in results}), 1)
        tasks = self.repo.list_narrative_outbox(
            source_scope="googleplex_app",
            limit=10,
        )
        self.assertEqual(len(tasks), 1)

    def test_googleplex_rate_limit_is_atomic_but_replay_stays_available(self):
        self.install_app()
        contract = json.loads(json.dumps(self.app_contract))
        contract["llm_ingress"]["rate_limit"] = {
            "max_tasks": 1,
            "window_seconds": 3600,
        }
        ingress = GoogleplexLlmTaskIngress(self.repo, self.inventory)
        first = ingress.submit("alice", contract, self.app_payload())
        replay = ingress.submit("alice", contract, self.app_payload())
        blocked = ingress.submit("alice", contract, self.app_payload(
            client_receipt_id="client-receipt-0009",
        ))
        self.assertTrue(first["accepted"])
        self.assertEqual(replay["task_id"], first["task_id"])
        self.assertEqual(blocked["reason_code"], "rate_limit_exceeded")
        self.assertEqual(len(self.repo.list_narrative_outbox(limit=10)), 1)

    def test_googleplex_endpoint_returns_owner_safe_receipt_without_profile(self):
        self.install_app()
        synthetic_heavy_profile = {"username": "alice", "blob": "x" * (35 * 1024 * 1024)}
        run.app.config["TESTING"] = True
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        with patch.object(run, "get_ghostnetwork_service", return_value=self.service), \
                patch.object(run, "player_inventory_store", self.inventory), \
                patch.object(run, "get_app_catalog", return_value=[self.app_contract]), \
                patch.object(run.user_store, "get_profile", return_value=synthetic_heavy_profile) as full_read, \
                patch.object(run.user_store, "list_profiles", return_value=[synthetic_heavy_profile]) as full_scan:
            response = client.post(
                "/api/googleplex/llm/tasks",
                json=self.app_payload(),
            )
            data = response.get_json()
            self.assertEqual(response.status_code, 202)
            status = client.get(
                f"/api/googleplex/llm/tasks/{data['receipt_id']}"
            )
        full_read.assert_not_called()
        full_scan.assert_not_called()
        self.assertEqual(status.status_code, 200)
        receipt = status.get_json()["receipt"]
        self.assertEqual(receipt["status"], "queued")
        self.assertIn("user_message", receipt)
        self.assertNotIn("claimed_by", receipt)
        self.assertNotIn("facts", receipt)
        self.assertNotIn("validation", receipt)

        other_client = run.app.test_client()
        with other_client.session_transaction() as flask_session:
            flask_session["user"] = "bob"
        with patch.object(run, "get_ghostnetwork_service", return_value=self.service):
            foreign_status = other_client.get(
                f"/api/googleplex/llm/tasks/{data['receipt_id']}"
            )
        self.assertEqual(foreign_status.status_code, 404)
        self.assertEqual(
            foreign_status.get_json()["reason_code"],
            "task_receipt_not_found",
        )


if __name__ == "__main__":
    unittest.main()
