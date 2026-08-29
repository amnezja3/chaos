import json
import os
import tempfile
import unittest
import sqlite3
from datetime import datetime, timedelta, timezone

from ghostnetwork.ollama_client import OllamaGenerationResult
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.publication import NarrativePublicationService
from ghostnetwork.repository import GhostNetworkRepository
from scripts.narrative_publication_worker import is_database_contention


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class AcceptedClient:
    def verify(self):
        return {"ok": True, "errors": []}

    def generate(self, package, policy):
        output = {
            "title": "Canonical title",
            "body": "Canonical body",
            "tone": "info",
            "fact_refs": ["fact:one"],
            "cta_ref": None,
        }
        if "asset_ref" in (package.get("format", {}).get("properties") or {}):
            output["asset_ref"] = next(iter(package.get("allowed_asset_refs") or ()), None)
        return OllamaGenerationResult(
            model=policy.model_name,
            model_digest=policy.model_digest,
            runtime_version="test",
            content=json.dumps(output),
            done=True,
            done_reason="stop",
            total_duration_ns=1,
            load_duration_ns=0,
            prompt_eval_count=1,
            eval_count=1,
            raw_response_hash="hash",
        )


class NarrativePublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = MutableClock()
        self.repo = GhostNetworkRepository(
            db_path=os.path.join(self.tmp.name, "publication.sqlite3"),
            clock=self.clock,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def accepted_candidate(
        self, event_id="publication-one", *, audience_scope="public",
        audience_clan="", audience_owner="", source_scope="ghostnetwork",
        task_variant="part_activated", target_medium="blacknet",
    ):
        task = assign_ollama_task_policy({
            "event_id": event_id,
            "source_scope": source_scope,
            "source_app_id": "agi2108Console" if source_scope == "googleplex_app" else "",
            "source_event_id": event_id,
            "processor": "ollama",
            "target_medium": target_medium,
            "audience_scope": audience_scope,
            "audience_clan": audience_clan,
            "audience_owner": audience_owner,
            "truth_class": "canonical",
            "truth_class_policy": "canonical_facts_only",
            "facts": [{"fact_id": "fact:one", "fact_type": "test"}],
            "allowed_actions": [],
            "canon_version": "test-v1",
            "task_variant": task_variant,
        })
        item = self.repo.enqueue_narrative_task(task)
        worker = OllamaNarrativeWorker(
            repository=self.repo,
            client=AcceptedClient(),
            config=OllamaWorkerConfig(
                enabled=True, poll_seconds=0.1, poll_jitter_seconds=0,
                lease_seconds=60, heartbeat_seconds=30,
            ),
            worker_id="ollama-test",
        )
        self.assertEqual(worker.process_once()["result"], "completed")
        return self.repo.get_narrative_candidate_for_task(item["outbox_id"])

    def test_accepted_candidate_publishes_exactly_once(self):
        candidate = self.accepted_candidate()
        first = self.repo.ensure_narrative_publication(candidate["candidate_id"])
        duplicate = self.repo.ensure_narrative_publication(candidate["candidate_id"])
        self.assertEqual(first["publication_receipt_id"], duplicate["publication_receipt_id"])

        claim = self.repo.claim_next_narrative_publication("publisher-a", lease_seconds=60)
        published = self.repo.publish_claimed_narrative_candidate(
            claim["publication_receipt_id"], "publisher-a", claim["lease_until"]
        )
        replay = self.repo.publish_claimed_narrative_candidate(
            claim["publication_receipt_id"], "publisher-a", claim["lease_until"]
        )

        self.assertEqual(published["receipt"]["status"], "published")
        self.assertFalse(published["duplicate"])
        self.assertTrue(replay["duplicate"])
        records = self.repo.list_narrative_medium_records("blacknet", limit=10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["fact_refs"], ["fact:one"])
        self.assertEqual(records[0]["truth_class"], "canonical")

    def test_googleplex_asset_ref_survives_candidate_and_medium_projection(self):
        candidate = self.accepted_candidate(
            "googleplex-asset", source_scope="blacknet_world",
            task_variant="world_digest", target_medium="googleplex_news",
        )
        self.assertEqual(candidate["asset_ref"], "gp_scene_world_neutral_01")
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="googleplex-publisher"
        )
        published = publisher.process_once()
        self.assertEqual(published["result"], "published")
        self.assertEqual(
            published["record"]["asset_ref"], "gp_scene_world_neutral_01"
        )

    def test_only_one_worker_owns_publication_lease(self):
        candidate = self.accepted_candidate("two-publishers")
        self.repo.ensure_narrative_publication(candidate["candidate_id"])
        first = self.repo.claim_next_narrative_publication("publisher-a", lease_seconds=60)
        second = self.repo.claim_next_narrative_publication("publisher-b", lease_seconds=60)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_expired_lease_recovers_without_duplicate_record(self):
        candidate = self.accepted_candidate("lease-recovery")
        self.repo.ensure_narrative_publication(candidate["candidate_id"])
        first = self.repo.claim_next_narrative_publication("publisher-a", lease_seconds=10)
        self.clock.advance(11)
        recovered = self.repo.claim_next_narrative_publication("publisher-b", lease_seconds=10)
        self.assertEqual(first["publication_receipt_id"], recovered["publication_receipt_id"])
        result = self.repo.publish_claimed_narrative_candidate(
            recovered["publication_receipt_id"], "publisher-b", recovered["lease_until"]
        )
        self.assertEqual(result["receipt"]["status"], "published")
        self.assertEqual(len(self.repo.list_narrative_medium_records("blacknet")), 1)

    def test_rejected_candidate_is_not_publishable(self):
        self.assertIsNone(self.repo.ensure_narrative_publication("missing"))

    def test_service_stages_and_publishes_without_profile_dependency(self):
        self.accepted_candidate("service-flow")
        result = NarrativePublicationService(
            repository=self.repo, worker_id="publisher-service"
        ).process_once()
        self.assertEqual(result["result"], "published")
        self.assertEqual(len(self.repo.list_narrative_medium_records("blacknet")), 1)

    def test_public_clan_and_owner_records_are_projected_without_cross_account_leak(self):
        self.accepted_candidate("audience-public")
        self.accepted_candidate(
            "audience-clan", audience_scope="clan", audience_clan="alpha"
        )
        self.accepted_candidate(
            "audience-owner", audience_scope="owner", audience_owner="alice"
        )
        publisher = NarrativePublicationService(repository=self.repo, worker_id="audience-publisher")
        for _index in range(3):
            self.assertEqual(publisher.process_once()["result"], "published")

        alice = self.repo.list_narrative_medium_records_for_viewer(
            "blacknet", owner="alice", clan="alpha"
        )
        bob = self.repo.list_narrative_medium_records_for_viewer(
            "blacknet", owner="bob", clan="alpha"
        )
        carol = self.repo.list_narrative_medium_records_for_viewer(
            "blacknet", owner="carol", clan="beta"
        )
        self.assertEqual(len(alice), 3)
        self.assertEqual({item["audience_scope"] for item in bob}, {"public", "clan"})
        self.assertEqual({item["audience_scope"] for item in carol}, {"public"})
        self.assertFalse(any(item["audience_owner"] == "alice" for item in bob + carol))

    def test_queue_status_is_bounded_aggregate(self):
        self.accepted_candidate("queue-count")
        publisher = NarrativePublicationService(repository=self.repo, worker_id="count-publisher")
        self.assertEqual(publisher.process_once()["result"], "published")
        counts = self.repo.narrative_publication_queue_counts()
        self.assertEqual(counts["statuses"], {"published": 1})
        self.assertEqual(counts["published_by_medium"], {"blacknet": 1})

    def test_publisher_classifies_only_transient_sqlite_contention_as_retryable(self):
        self.assertTrue(is_database_contention(sqlite3.OperationalError("database is locked")))
        self.assertTrue(is_database_contention(sqlite3.OperationalError("database is busy")))
        self.assertFalse(is_database_contention(sqlite3.OperationalError("no such table")))

    def test_owner_cyberner_unread_ordinal_is_exactly_once_and_advances(self):
        self.accepted_candidate(
            "agi-owner-unread", audience_scope="owner", audience_owner="alice",
            source_scope="googleplex_app", task_variant="owner-analysis",
            target_medium="cyberner",
        )
        publisher = NarrativePublicationService(repository=self.repo, worker_id="agi-publisher")
        self.assertEqual(publisher.process_once()["result"], "published")
        records = self.repo.list_narrative_medium_records(
            "cyberner", audience_scope="owner", audience_owner="alice"
        )
        self.assertEqual(len(records), 1)
        ordinal = records[0]["publication_ordinal"]
        self.assertGreater(ordinal, 0)
        self.assertEqual(self.repo.count_narrative_medium_records_for_viewer_after(
            "cyberner", owner="alice", audience_scope="owner", after_ordinal=0
        ), 1)
        self.assertEqual(self.repo.count_narrative_medium_records_for_viewer_after(
            "cyberner", owner="alice", audience_scope="owner", after_ordinal=ordinal
        ), 0)
        self.assertEqual(self.repo.count_narrative_medium_records_for_viewer_after(
            "cyberner", owner="bob", audience_scope="owner", after_ordinal=0
        ), 0)
        self.assertEqual(publisher.process_once()["result"], "idle")


if __name__ == "__main__":
    unittest.main()
