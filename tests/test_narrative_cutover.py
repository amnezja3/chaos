import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ghostnetwork.narrative_cutover import (
    CUTOVER_CONTRACT_VERSION,
    NarrativeCutoverConfig,
    build_ghost_event_lineage_report,
    build_narrative_cutover_report,
    retire_cutover_ineligible_tasks,
)
from ghostnetwork.ollama_worker import active_ollama_worker_policies
from ghostnetwork.repository import GhostNetworkRepository


class CutoverRepositoryFixture:
    def __init__(self, *, ineligible=0, expired=0, legacy=0, unstaged=0):
        self.task_counts = {
            "statuses": {"completed": 3},
            "eligible_ready": 0,
            "ineligible_ready": ineligible,
            "oldest_eligible_ready": "",
            "expired_leases": expired,
            "active_legacy_file_tasks": legacy,
        }
        self.publication_counts = {
            "statuses": {"published": 3},
            "published_by_medium": {
                "blacknet": 1, "googleplex_news": 1, "cyberner": 1,
            },
            "ready_now": 0,
            "oldest_ready": "",
            "expired_claims": 0,
            "unstaged_accepted": unstaged,
        }

    def narrative_task_queue_counts(self, policies, now=None):
        self.policies = policies
        return dict(self.task_counts)

    def narrative_publication_queue_counts(self, now=None):
        return dict(self.publication_counts)


class NarrativeCutoverTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
        self.enabled = NarrativeCutoverConfig(
            ollama_worker_enabled=True,
            publisher_enabled=True,
            legacy_file_queue_enabled=False,
        )

    def test_readiness_report_is_bounded_and_profile_free(self):
        repository = CutoverRepositoryFixture()
        with patch(
            "ghostnetwork.narrative_cutover.verify_prompt_registry",
            return_value={"ok": True, "errors": []},
        ):
            report = build_narrative_cutover_report(
                repository, config=self.enabled, now=self.now
            )

        self.assertTrue(report["ok"])
        self.assertEqual(report["contract_version"], CUTOVER_CONTRACT_VERSION)
        self.assertTrue(repository.policies)
        self.assertEqual(report["heavy_profile"], {
            "profile_full_read": 0,
            "profile_full_write": 0,
            "profile_bytes": 0,
            "account_scan": 0,
        })
        self.assertTrue(report["legacy_file_outbox"]["diagnostic_export_only"])

    def test_cutover_fails_closed_on_runtime_or_queue_regression(self):
        repository = CutoverRepositoryFixture(
            ineligible=2, expired=1, legacy=1, unstaged=1
        )
        disabled = NarrativeCutoverConfig(
            ollama_worker_enabled=False,
            publisher_enabled=False,
            legacy_file_queue_enabled=True,
        )
        with patch(
            "ghostnetwork.narrative_cutover.verify_prompt_registry",
            return_value={"ok": False, "errors": ["prompt_missing"]},
        ):
            report = build_narrative_cutover_report(
                repository, config=disabled, now=self.now
            )

        self.assertFalse(report["ok"])
        for error in (
            "ollama_worker_disabled", "narrative_publisher_disabled",
            "legacy_file_queue_enabled", "prompt_registry_invalid",
            "active_legacy_file_tasks", "ineligible_ready_tasks",
            "expired_task_leases",
        ):
            self.assertIn(error, report["errors"])
        self.assertIn("unstaged_accepted_candidates", report["warnings"])

    def test_cutover_fails_closed_on_bounded_backpressure(self):
        repository = CutoverRepositoryFixture()
        repository.task_counts["eligible_ready"] = 6
        repository.publication_counts["ready_now"] = 4
        config = NarrativeCutoverConfig(
            ollama_worker_enabled=True,
            publisher_enabled=True,
            legacy_file_queue_enabled=False,
            max_ready_tasks=5,
            max_ready_publications=3,
        )
        with patch(
            "ghostnetwork.narrative_cutover.verify_prompt_registry",
            return_value={"ok": True, "errors": []},
        ):
            report = build_narrative_cutover_report(
                repository, config=config, now=self.now
            )

        self.assertFalse(report["ok"])
        self.assertIn("task_backpressure_limit_exceeded", report["errors"])
        self.assertIn(
            "publication_backpressure_limit_exceeded", report["errors"]
        )

    def test_cutover_retires_only_queued_ineligible_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = GhostNetworkRepository(
                db_path=os.path.join(tmpdir, "cutover.sqlite3"),
                clock=lambda: self.now,
            )
            policy = active_ollama_worker_policies()[0]
            source_scope, task_variant, target_medium, prompt, schema, model = (
                policy.eligibility_tuple()
            )

            def task(event_id, prompt_version):
                return {
                    "event_id": event_id,
                    "source_scope": source_scope,
                    "source_event_id": event_id,
                    "processor": "ollama",
                    "target_medium": target_medium,
                    "audience_scope": "public",
                    "truth_class": "canonical",
                    "facts": [{"fact_id": f"fact:{event_id}"}],
                    "allowed_actions": [],
                    "task_variant": task_variant,
                    "prompt_version": prompt_version,
                    "output_schema_version": schema,
                    "model_policy_version": model,
                }

            eligible = repository.enqueue_narrative_task(
                task("cutover-eligible", prompt)
            )
            stale = repository.enqueue_narrative_task(
                task("cutover-stale", "superseded-prompt")
            )
            retired = retire_cutover_ineligible_tasks(
                repository, now=self.now
            )

            self.assertEqual(retired, [stale["outbox_id"]])
            self.assertEqual(
                repository.get_narrative_outbox(eligible["outbox_id"])["status"],
                "ready",
            )
            retired_task = repository.get_narrative_outbox(stale["outbox_id"])
            self.assertEqual(retired_task["status"], "dead_letter")
            self.assertEqual(
                retired_task["last_error_code"], "policy_superseded_cutover"
            )

    def test_worker_policy_set_excludes_legacy_multi_fact_digest(self):
        policies = active_ollama_worker_policies()
        self.assertTrue(policies)
        self.assertFalse(any(
            policy.source_scope == "blacknet_world"
            and policy.task_variant == "world_digest"
            for policy in policies
        ))

    def test_cutover_runtime_has_no_heavy_profile_callsite(self):
        root = Path(__file__).resolve().parents[1]
        source = "\n".join(
            (root / path).read_text(encoding="utf-8")
            for path in (
                "ghostnetwork/narrative_cutover.py",
                "scripts/audit_narrative_cutover.py",
            )
        )
        for forbidden in (
            "profile_json", "get_profile(", "load_profile",
            "list_profiles", "sync_session_profile", "user_store",
        ):
            self.assertNotIn(forbidden, source)

    def test_lineage_audit_detects_and_then_closes_persisted_event_gap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = GhostNetworkRepository(
                db_path=os.path.join(tmpdir, "lineage.sqlite3"),
                clock=lambda: datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            )
            service = __import__(
                "ghostnetwork.service", fromlist=["GhostNetworkService"]
            ).GhostNetworkService(repository=repository)
            created = service.cycles.ensure_active_cycle()
            cycle_id = created["cycle"]["cycle_id"]
            event = next(
                item for item in repository.list_events(cycle_id, limit=1000)
                if item["event_type"] == "ghost.cycle_activated"
            )

            missing = build_ghost_event_lineage_report(repository)
            self.assertGreater(missing["eligible_without_task"], 0)
            self.assertTrue(any(
                sample.get("event_id") == event["event_id"]
                for sample in missing["samples"]
            ))

            service.narrative.reconcile_persisted_events()
            closed = build_ghost_event_lineage_report(repository)
            self.assertEqual(closed["eligible_without_task"], 0)
            self.assertEqual(closed["wrong_audience"], 0)


if __name__ == "__main__":
    unittest.main()
