import json
import os
import tempfile
import unittest
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ghostnetwork.ollama_client import OllamaGenerationResult
from ghostnetwork.ollama_policy import assign_ollama_task_policy
from ghostnetwork.ollama_worker import OllamaNarrativeWorker, OllamaWorkerConfig
from ghostnetwork.publication import NarrativePublicationService
from ghostnetwork.repository import GhostNetworkRepository
from ghostnetwork.editorial import GoogleplexEditorialProducer
from ghostnetwork.llm.semantic_input import attach_semantic_content
from googleplex_news import build_googleplex_news_snapshot, merge_googleplex_news_publications
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
        intercepted = bool(package.get("voice_contract"))
        output = {
            "title": (
                "PRZECHWYT // AKTYWNY SYGNAL" if intercepted else "Canonical title"
            ),
            "body": (
                "...the canonical signal remains active." if intercepted
                else "The canonical signal remains active."
            ),
            "tone": "info",
            "fact_refs": [next(iter(package["fact_refs"]))],
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


class SequencedAcceptedClient(AcceptedClient):
    def __init__(self):
        self.sequence = 0

    def generate(self, package, policy):
        self.sequence += 1
        generated = super().generate(package, policy)
        output = json.loads(generated.content)
        intercepted = bool(package.get("voice_contract"))
        output["title"] = (
            f"PRZECHWYT // AKTYWNY SYGNAL {self.sequence}"
            if intercepted else f"Canonical title {self.sequence}"
        )
        output["body"] = (
            f"...the canonical signal remains active: {self.sequence}."
            if intercepted else f"The canonical signal remains active: {self.sequence}."
        )
        return OllamaGenerationResult(
            model=generated.model,
            model_digest=generated.model_digest,
            runtime_version=generated.runtime_version,
            content=json.dumps(output),
            done=generated.done,
            done_reason=generated.done_reason,
            total_duration_ns=generated.total_duration_ns,
            load_duration_ns=generated.load_duration_ns,
            prompt_eval_count=generated.prompt_eval_count,
            eval_count=generated.eval_count,
            raw_response_hash=generated.raw_response_hash,
        )


class RoleAcceptedClient(AcceptedClient):
    def generate(self, package, policy):
        output = {
            "title": "Modelowa nazwa jest ignorowana",
            "body": "Znajdz szczeline w osloniemym wezle i otworz droge dla sygnalu.",
            "tone": "mystery",
            "fact_refs": [next(iter(package["fact_refs"]))],
            "cta_ref": None,
            "asset_role": next(iter(package.get("allowed_asset_roles") or ()), None),
        }
        return OllamaGenerationResult(
            model=policy.model_name, model_digest=policy.model_digest,
            runtime_version="test", content=json.dumps(output), done=True,
            done_reason="stop", total_duration_ns=1, load_duration_ns=0,
            prompt_eval_count=1, eval_count=1, raw_response_hash="role-hash",
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
        task_variant="part_activated", target_medium="blacknet", validation=None,
        client=None, narrative_thread_id="", world_state_version="1", priority=80,
    ):
        task_validation = dict(validation or {})
        if source_scope == "ghostnetwork":
            task_validation.setdefault("event_family", "part_activated")
            task_validation.setdefault("significance", "high")
        fact = {
            "fact_id": "fact:one", "fact_type": "test",
            "title": "Canonical body",
        }
        if source_scope == "ghostnetwork":
            fact = attach_semantic_content(
                fact, {"statement": "Czesc GhostNetwork zostala aktywowana."},
            )
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
            "facts": [fact],
            "allowed_actions": [],
            "canon_version": "test-v1",
            "task_variant": task_variant,
            "narrative_intent": (
                "intercepted_world_signal"
                if source_scope == "blacknet_world"
                and task_variant in {"blacknet_signal_narration", "googleplex_world_dispatch"}
                else "ghost_part_activation" if source_scope == "ghostnetwork" else ""
            ),
            "narrative_thread_id": (
                narrative_thread_id
                or (f"ghost-part:{audience_scope}:test" if source_scope == "ghostnetwork" else "")
            ),
            "world_state_version": world_state_version,
            "priority": priority,
            "validation": task_validation,
        })
        item = self.repo.enqueue_narrative_task(task)
        worker = OllamaNarrativeWorker(
            repository=self.repo,
            client=client or AcceptedClient(),
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
            task_variant="googleplex_world_dispatch", target_medium="googleplex_news",
            validation={
                "selected_source_ref": "fact:one",
                "presentation_slot": "gp-home-world-grid",
            },
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
        self.assertEqual(
            published["record"]["presentation_slot"], "gp-home-world-grid"
        )
        self.assertEqual(
            published["record"]["narrative_intent"], "intercepted_world_signal"
        )
        slot = self.repo.get_narrative_slot_state(
            "googleplex_news", "gp-home-world-grid"
        )
        self.assertEqual(slot["version"], 1)
        self.assertEqual(
            slot["active_medium_record_id"], published["record"]["medium_record_id"]
        )
        active = self.repo.list_active_narrative_slot_records_for_viewer(
            "googleplex_news", owner="alice", limit=6
        )
        self.assertEqual([item["medium_record_id"] for item in active], [
            published["record"]["medium_record_id"]
        ])

    def test_ghostnetwork_publication_carries_code_owned_lifecycle(self):
        self.accepted_candidate(
            "lifecycle-one", narrative_thread_id="ghost-part:public:one",
            world_state_version="41", priority=85,
            validation={"event_family": "part_activated", "significance": "high"},
        )
        published = NarrativePublicationService(
            repository=self.repo, worker_id="lifecycle-publisher"
        ).process_once()
        record = published["record"]

        self.assertEqual(record["active_state"], "active")
        self.assertEqual(record["narrative_thread_id"], "ghost-part:public:one")
        self.assertEqual(record["event_family"], "part_activated")
        self.assertEqual(record["significance"], "high")
        self.assertEqual(record["priority"], 85)
        self.assertEqual(record["source_state_version"], 41)
        self.assertEqual(record["presentation_family"], "ghost_activation")
        self.assertEqual(
            record["semantic_contract_version"], "chaos-llm-semantic-input-v1"
        )
        self.assertEqual(
            record["lifecycle_contract_version"],
            "ghostnetwork-publication-lifecycle-v1",
        )
        self.assertTrue(record["valid_until"] > record["valid_from"])

    def test_newer_thread_state_invalidates_previous_head(self):
        client = SequencedAcceptedClient()
        self.accepted_candidate(
            "thread-state-one", client=client,
            narrative_thread_id="ghost-part:public:shared", world_state_version="10",
        )
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="thread-publisher"
        )
        first = publisher.process_once()
        self.clock.advance(1)
        self.accepted_candidate(
            "thread-state-two", client=client,
            narrative_thread_id="ghost-part:public:shared", world_state_version="11",
        )
        second = publisher.process_once()

        records = self.repo.list_narrative_medium_records("blacknet", limit=10)
        old = next(item for item in records if item["medium_record_id"] == first["record"]["medium_record_id"])
        new = next(item for item in records if item["medium_record_id"] == second["record"]["medium_record_id"])
        self.assertEqual(old["active_state"], "invalidated")
        self.assertEqual(old["invalidated_by_event_id"], "thread-state-two")
        self.assertEqual(old["invalidation_reason"], "canonical_state_observed")
        self.assertEqual(new["active_state"], "active")
        self.assertEqual(new["supersedes_medium_record_id"], old["medium_record_id"])
        visible = self.repo.list_narrative_medium_records_for_viewer("blacknet", limit=10)
        self.assertEqual([item["medium_record_id"] for item in visible], [new["medium_record_id"]])

    def test_new_canonical_task_hides_old_head_before_model_generation(self):
        self.accepted_candidate(
            "observed-state-one",
            narrative_thread_id="ghost-part:public:observed", world_state_version="30",
        )
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="observed-state-publisher"
        )
        old = publisher.process_once()["record"]
        base_task = self.repo.list_narrative_outbox(limit=1)[0]
        next_task = dict(base_task)
        for key in ("outbox_id", "dedupe_key"):
            next_task.pop(key, None)
        next_task.update({
            "event_id": "observed-state-two",
            "source_event_id": "observed-state-two",
            "world_state_version": "31",
            "status": "ready",
        })

        queued = self.repo.enqueue_narrative_task(next_task)

        self.assertEqual(queued["status"], "ready")
        self.assertEqual(
            self.repo.list_narrative_medium_records_for_viewer("blacknet", limit=10),
            [],
        )
        historical = self.repo.list_narrative_medium_records("blacknet", limit=10)
        stale = next(
            item for item in historical
            if item["medium_record_id"] == old["medium_record_id"]
        )
        self.assertEqual(stale["active_state"], "invalidated")
        self.assertEqual(stale["invalidated_by_event_id"], "observed-state-two")
        self.assertEqual(stale["invalidation_reason"], "canonical_state_observed")

    def test_pending_old_candidate_cannot_publish_after_new_state_is_observed(self):
        self.accepted_candidate(
            "pending-old-state",
            narrative_thread_id="ghost-part:public:pending", world_state_version="40",
        )
        base_task = self.repo.list_narrative_outbox(limit=1)[0]
        next_task = dict(base_task)
        for key in ("outbox_id", "dedupe_key"):
            next_task.pop(key, None)
        next_task.update({
            "event_id": "observed-new-state",
            "source_event_id": "observed-new-state",
            "world_state_version": "41",
            "status": "ready",
        })
        newer = self.repo.enqueue_narrative_task(next_task)

        result = NarrativePublicationService(
            repository=self.repo, worker_id="pending-old-publisher"
        ).process_once()

        self.assertEqual(result["result"], "rejected")
        self.assertEqual(result["reason"], "lifecycle_state_superseded")
        self.assertEqual(result["newer_task_id"], newer["outbox_id"])
        self.assertEqual(
            self.repo.list_narrative_medium_records_for_viewer("blacknet", limit=10),
            [],
        )

    def test_idempotent_task_replay_repairs_stale_active_head(self):
        self.accepted_candidate(
            "repair-state-one",
            narrative_thread_id="ghost-part:owner:repair", world_state_version="50",
        )
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="repair-state-publisher"
        )
        old = publisher.process_once()["record"]
        base_task = self.repo.list_narrative_outbox(limit=1)[0]
        next_task = dict(base_task)
        for key in ("outbox_id", "dedupe_key"):
            next_task.pop(key, None)
        next_task.update({
            "event_id": "repair-state-two",
            "source_event_id": "repair-state-two",
            "world_state_version": "51",
            "status": "ready",
        })
        self.repo.enqueue_narrative_task(next_task)
        with self.repo._conn() as conn:
            conn.execute(
                """
                UPDATE ghost_narrative_medium_records
                SET active_state = 'active', invalidated_by_event_id = '',
                    invalidation_reason = ''
                WHERE medium_record_id = ?
                """,
                (old["medium_record_id"],),
            )

        replay = self.repo.enqueue_narrative_task(next_task)

        self.assertTrue(replay["idempotent"])
        repaired = self.repo.list_narrative_medium_records("blacknet", limit=10)[0]
        self.assertEqual(repaired["active_state"], "invalidated")
        self.assertEqual(repaired["invalidated_by_event_id"], "repair-state-two")
        self.assertEqual(repaired["invalidation_reason"], "canonical_state_observed")

    def test_late_older_state_cannot_replace_active_head(self):
        client = SequencedAcceptedClient()
        self.accepted_candidate(
            "newer-first", client=client,
            narrative_thread_id="ghost-part:public:late", world_state_version="20",
        )
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="late-state-publisher"
        )
        active = publisher.process_once()["record"]
        self.clock.advance(1)
        self.accepted_candidate(
            "older-late", client=client,
            narrative_thread_id="ghost-part:public:late", world_state_version="19",
        )
        rejected = publisher.process_once()

        self.assertEqual(rejected["result"], "rejected")
        self.assertEqual(rejected["reason"], "lifecycle_state_superseded")
        visible = self.repo.list_narrative_medium_records_for_viewer("blacknet", limit=10)
        self.assertEqual([item["medium_record_id"] for item in visible], [active["medium_record_id"]])

    def test_ttl_expiry_removes_record_from_active_read_model(self):
        self.accepted_candidate("expiring-publication")
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="expiry-publisher"
        )
        record = publisher.process_once()["record"]
        self.clock.advance(24 * 60 * 60 + 1)

        self.assertEqual(self.repo.expire_narrative_medium_records(), 1)
        self.assertEqual(
            self.repo.list_narrative_medium_records_for_viewer("blacknet", limit=10),
            [],
        )
        historical = self.repo.list_narrative_medium_records("blacknet", limit=10)
        self.assertEqual(historical[0]["medium_record_id"], record["medium_record_id"])
        self.assertEqual(historical[0]["active_state"], "expired")
        self.assertEqual(historical[0]["invalidation_reason"], "ttl_expired")

    def test_rejected_completed_candidate_does_not_hold_slot_busy(self):
        candidate = self.accepted_candidate(
            "rejected-slot-holder",
            source_scope="blacknet_world",
            task_variant="googleplex_world_dispatch",
            target_medium="googleplex_news",
            validation={
                "selected_source_ref": "fact:one",
                "presentation_slot": "gp-home-world-grid",
            },
        )
        self.assertEqual(candidate["validation_status"], "accepted")
        with self.repo._conn() as conn:
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET presentation_slot = 'gp-home-world-grid'
                WHERE outbox_id = ?
                """,
                (candidate["task_id"],),
            )
        self.assertTrue(self.repo.has_open_narrative_slot_assignment(
            "googleplex_news", "gp-home-world-grid"
        ))

        with self.repo._conn() as conn:
            conn.execute(
                """
                UPDATE ghost_narrative_inbox_candidates
                SET validation_status = 'rejected',
                    validation_errors_json = '["signal_source_echo"]'
                WHERE candidate_id = ?
                """,
                (candidate["candidate_id"],),
            )

        self.assertFalse(self.repo.has_open_narrative_slot_assignment(
            "googleplex_news", "gp-home-world-grid"
        ))

    def test_stage_two_product_publishes_one_slot_with_canonical_commerce_data(self):
        catalog = [{
            "id": "v_map", "name": "V-MAP",
            "description": "Skanuje otwarte porty i luki w zabezpieczeniach.",
            "published": True, "available": True, "downloads": 15,
            "price": 955, "category": "scanner_recon",
        }]
        assignment = GoogleplexEditorialProducer(self.repo).enqueue_next(
            catalog, now=self.clock.value
        )
        worker = OllamaNarrativeWorker(
            repository=self.repo, client=RoleAcceptedClient(),
            config=OllamaWorkerConfig(
                enabled=True, poll_seconds=0.1, poll_jitter_seconds=0,
                lease_seconds=60, heartbeat_seconds=30,
            ), worker_id="stage-two-ollama",
        )
        completed = worker.process_once()
        candidate = self.repo.get_narrative_candidate_for_task(
            assignment["task"]["outbox_id"]
        )

        self.assertEqual(completed["validation_status"], "accepted")
        self.assertEqual(candidate["title"], "V-MAP")
        self.assertEqual(candidate["asset_ref"], "gp_fallback_tool")
        self.assertEqual(candidate["cta_action"], "open_googleplex_search")
        self.assertEqual(candidate["cta_payload"]["price_hc"], 955)

        published = NarrativePublicationService(
            repository=self.repo, worker_id="stage-two-publisher"
        ).process_once()
        self.assertEqual(published["result"], "published", published)
        self.assertEqual(
            published["record"]["narrative_intent"], "product_benefit_promo"
        )
        slot = self.repo.get_narrative_slot_state(
            "googleplex_news", "gp-home-featured"
        )
        self.assertEqual(slot["version"], 1)
        self.assertEqual(slot["creative_epoch"], 1)
        self.assertEqual(slot["next_refresh_at"], "2026-08-29T18:00:00+00:00")

        snapshot = build_googleplex_news_snapshot(
            catalog=catalog, viewer_key="alice", session_generation="one", limit=20,
            now=self.clock.value,
        )
        active = self.repo.list_active_narrative_slot_records_for_viewer(
            "googleplex_news", owner="alice", limit=12
        )
        merged = merge_googleplex_news_publications(snapshot, active, limit=20)
        featured = next(
            item for item in merged["entries"]
            if item["content"]["news_id"] == "gp-home-featured"
        )
        self.assertEqual(featured["content"]["title"], "V-MAP")
        self.assertEqual(featured["presentation"]["primary_stat"], "955 HC")
        self.assertEqual(featured["action"]["action_type"], "open_googleplex_search")
        self.assertEqual(featured["action"]["action_target"], "V-MAP")
        self.assertEqual(featured["action"]["action_payload_ref"], "v_map")
        self.assertEqual(merged["diagnostics"]["publication_slot_ids"], [
            "gp-home-featured"
        ])

    def test_googleplex_slot_cas_rejects_stale_assignment(self):
        client = SequencedAcceptedClient()
        assignment = {
            "selected_source_ref": "fact:one",
            "selected_source_version": "source-v1",
            "presentation_slot": "gp-home-world-grid",
            "content_kind": "world_dispatch",
            "expected_slot_version": 0,
        }
        first = self.accepted_candidate(
            "slot-cas-one", source_scope="blacknet_world",
            task_variant="googleplex_world_dispatch",
            target_medium="googleplex_news", validation=assignment,
            client=client,
        )
        second = self.accepted_candidate(
            "slot-cas-two", source_scope="blacknet_world",
            task_variant="googleplex_world_dispatch",
            target_medium="googleplex_news", validation={
                **assignment, "selected_source_version": "source-v2",
            }, client=client,
        )

        first_receipt = self.repo.ensure_narrative_publication(first["candidate_id"])
        first_claim = self.repo.claim_next_narrative_publication(
            "slot-publisher", lease_seconds=60
        )
        first_result = self.repo.publish_claimed_narrative_candidate(
            first_receipt["publication_receipt_id"], "slot-publisher",
            first_claim["lease_until"],
        )
        self.assertFalse(first_result.get("slot_superseded", False))

        second_receipt = self.repo.ensure_narrative_publication(second["candidate_id"])
        second_claim = self.repo.claim_next_narrative_publication(
            "slot-publisher", lease_seconds=60
        )
        stale = self.repo.publish_claimed_narrative_candidate(
            second_receipt["publication_receipt_id"], "slot-publisher",
            second_claim["lease_until"],
        )
        self.assertEqual(stale, {"slot_superseded": True})
        self.assertEqual(
            self.repo.get_narrative_slot_state(
                "googleplex_news", "gp-home-world-grid"
            )["active_medium_record_id"],
            first_result["record"]["medium_record_id"],
        )

    def test_googleplex_candidate_without_asset_is_not_publishable(self):
        valid, reason = NarrativePublicationService.validate_candidate({
            "validation_status": "accepted",
            "target_medium": "googleplex_news",
            "audience_scope": "public",
            "title": "Aktualnosci z Googleplex",
            "body": "Canonical world update.",
            "asset_ref": "",
        }, {"facts": []})
        self.assertFalse(valid)
        self.assertEqual(reason, "missing_asset_ref")

    def test_superseded_googleplex_candidate_is_not_publishable(self):
        valid, reason = NarrativePublicationService.validate_candidate({
            "validation_status": "accepted",
            "source_scope": "blacknet_world",
            "target_medium": "googleplex_news",
            "audience_scope": "public",
            "title": "Googleplex News",
            "body": "Canonical world update.",
            "asset_ref": "gp_scene_world_danger_01",
        }, {
            "task_variant": "world_digest",
            "prompt_version": "googleplex-news-assets-prompt-v4",
            "output_schema_version": "chaos-narrative-output-assets-v2",
            "facts": [],
        })
        self.assertFalse(valid)
        self.assertEqual(reason, "candidate_policy_superseded")

    def test_superseded_cyberner_candidate_is_not_publishable(self):
        valid, reason = NarrativePublicationService.validate_candidate({
            "validation_status": "accepted",
            "source_scope": "googleplex_app",
            "target_medium": "cyberner",
            "audience_scope": "owner",
            "audience_owner": "alice",
            "title": "Stary wynik AGI",
            "body": "Odpowiedz pochodzi z poprzedniej polityki.",
        }, {
            "task_variant": "owner-analysis",
            "prompt_version": "cyberner-agi-2108-prompt-v2",
            "output_schema_version": "chaos-narrative-output-v1",
            "facts": [],
        })
        self.assertFalse(valid)
        self.assertEqual(reason, "candidate_policy_superseded")

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

    def test_staging_lists_only_unstaged_candidates_newest_first(self):
        oldest = self.accepted_candidate("staging-oldest")
        self.clock.advance(1)
        middle = self.accepted_candidate("staging-middle")
        self.clock.advance(1)
        newest = self.accepted_candidate("staging-newest")
        self.repo.ensure_narrative_publication(oldest["candidate_id"])
        self.repo.ensure_narrative_publication(middle["candidate_id"])

        unstaged = self.repo.list_unstaged_narrative_candidates(limit=10)

        self.assertEqual(
            [candidate["candidate_id"] for candidate in unstaged],
            [newest["candidate_id"]],
        )

    def test_staging_does_not_revisit_existing_receipts_and_is_bounded(self):
        candidates = []
        for index in range(6):
            candidates.append(self.accepted_candidate(f"bounded-staging-{index}"))
            self.clock.advance(1)
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="bounded-staging-publisher"
        )

        first = publisher.stage_accepted(limit=2, scan_limit=10)
        second = publisher.stage_accepted(limit=2, scan_limit=10)

        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertTrue(
            {item["candidate_id"] for item in first}.isdisjoint(
                {item["candidate_id"] for item in second}
            )
        )
        self.assertEqual(
            len(self.repo.list_unstaged_narrative_candidates(limit=10)), 2
        )

    def test_nonpublishable_accepted_candidate_gets_terminal_receipt(self):
        candidate = self.accepted_candidate("terminal-prepublish-rejection")
        publisher = NarrativePublicationService(
            repository=self.repo, worker_id="rejecting-publisher"
        )

        with patch.object(
            NarrativePublicationService, "validate_candidate",
            return_value=(False, "candidate_policy_superseded"),
        ):
            result = publisher.process_once()

        self.assertEqual(result["result"], "rejected")
        self.assertEqual(result["reason"], "candidate_policy_superseded")
        self.assertEqual(result["receipt"]["status"], "dead_letter")
        self.assertEqual(
            result["receipt"]["candidate_id"], candidate["candidate_id"]
        )
        self.assertEqual(self.repo.list_unstaged_narrative_candidates(limit=10), [])

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
