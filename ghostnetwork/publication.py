from __future__ import annotations

import hashlib
import os

from .repository import GhostNetworkRepository
from .ollama_policy import (
    GENERATION_OUTPUT_LIMITS,
    normalize_canonical_identifier_leaks,
    owner_analysis_echoes_input,
    presentation_safety_errors,
    source_metadata_leak_errors,
    unknown_canonical_poi_names,
)
from .llm.registry import resolve_ollama_task_policy


SUPPORTED_PUBLICATION_MEDIA = {"blacknet", "googleplex_news", "cyberner"}
SUPPORTED_AUDIENCE_SCOPES = {"public", "clan", "owner"}


class NarrativePublicationService:
    """Bounded accepted-candidate publisher; never reads a player profile."""

    def __init__(self, repository=None, worker_id=""):
        self.repository = repository or GhostNetworkRepository()
        self.worker_id = str(worker_id or "").strip() or self._default_worker_id()

    @staticmethod
    def _default_worker_id():
        seed = f"{os.getpid()}:{id(object())}"
        return "narrative-publisher-" + hashlib.sha1(seed.encode()).hexdigest()[:12]

    @staticmethod
    def validate_candidate(candidate, task=None):
        candidate = candidate if isinstance(candidate, dict) else {}
        if candidate.get("validation_status") != "accepted":
            return False, "candidate_not_accepted"
        if candidate.get("target_medium") not in SUPPORTED_PUBLICATION_MEDIA:
            return False, "unsupported_target_medium"
        scope = str(candidate.get("audience_scope") or "").strip()
        if scope not in SUPPORTED_AUDIENCE_SCOPES:
            return False, "invalid_audience_scope"
        if scope == "clan" and not str(candidate.get("audience_clan") or "").strip():
            return False, "missing_audience_clan"
        if scope == "owner" and not str(candidate.get("audience_owner") or "").strip():
            return False, "missing_audience_owner"
        if not str(candidate.get("title") or "").strip() or not str(candidate.get("body") or "").strip():
            return False, "empty_candidate_content"
        safety_errors = presentation_safety_errors(
            candidate.get("title"), candidate.get("body")
        )
        if safety_errors:
            return False, safety_errors[0]
        task = task if isinstance(task, dict) else {}
        metadata_errors = source_metadata_leak_errors(
            candidate.get("title"), candidate.get("body"), task.get("facts") or []
        )
        if metadata_errors:
            return False, metadata_errors[0]
        if (
            candidate.get("target_medium") in {"googleplex_news", "cyberner"}
            and candidate.get("source_scope") and task.get("task_variant")
        ):
            current_policy = resolve_ollama_task_policy(
                candidate.get("source_scope"), task.get("task_variant"),
                candidate.get("target_medium"),
                task.get("prompt_version"), task.get("output_schema_version"),
                task.get("model_policy_version"),
            )
            if not current_policy:
                return False, "candidate_policy_superseded"
        if unknown_canonical_poi_names(
            candidate.get("title"), candidate.get("body"), task.get("facts") or []
        ):
            return False, "unknown_canonical_poi_name"
        limits = GENERATION_OUTPUT_LIMITS.get(candidate.get("target_medium"))
        if limits and (
            len(str(candidate.get("title") or "")) > limits["title"]
            or len(str(candidate.get("body") or "")) > limits["body"]
        ):
            return False, "candidate_exceeds_presentation_limit"
        if (
            candidate.get("target_medium") == "googleplex_news"
            and not str(candidate.get("asset_ref") or "").strip()
        ):
            return False, "missing_asset_ref"
        normalized_title, normalized_body, normalized = normalize_canonical_identifier_leaks(
            candidate.get("title"), candidate.get("body"), task.get("facts") or []
        )
        if normalized and (
            normalized_title != candidate.get("title")
            or normalized_body != candidate.get("body")
        ):
            return False, "candidate_requires_normalization"
        if (
            candidate.get("source_scope") == "googleplex_app"
            and task.get("task_variant") == "owner-analysis"
            and owner_analysis_echoes_input(
                candidate.get("title"), candidate.get("body"), task.get("facts") or []
            )
        ):
            return False, "owner_analysis_echo"
        return True, "ok"

    def stage_accepted(self, limit=4, scan_limit=500):
        limit = max(1, min(int(limit or 4), 32))
        scan_limit = max(limit, min(int(scan_limit or 500), 500))
        staged = []
        for candidate in self.repository.list_unstaged_narrative_candidates(
            validation_status="accepted", limit=scan_limit
        ):
            # Every accepted candidate receives an auditable publication
            # identity. Validation happens after the receipt is claimed below;
            # superseded or unsafe historical candidates become terminally
            # rejected instead of being rescanned forever.
            receipt = self.repository.ensure_narrative_publication(candidate["candidate_id"])
            if receipt:
                staged.append(receipt)
                if len(staged) >= limit:
                    break
        return staged

    def process_once(self, lease_seconds=60):
        # Keep writer pressure bounded: stage only a small number of genuinely
        # unstaged candidates per loop, then publish one receipt.  Historical
        # accepted candidates that already have receipts are never rewritten.
        expired = self.repository.expire_narrative_medium_records(limit=100)
        self.stage_accepted(limit=4, scan_limit=500)
        receipt = self.repository.claim_next_narrative_publication(
            self.worker_id, lease_seconds=lease_seconds
        )
        if not receipt:
            return {"ok": True, "result": "idle"}
        candidate = self.repository.get_narrative_candidate(receipt["candidate_id"])
        task = self.repository.get_narrative_outbox(candidate.get("task_id"))
        valid, reason = self.validate_candidate(candidate, task)
        if not valid:
            rejected = self.repository.reject_claimed_narrative_publication(
                receipt["publication_receipt_id"], self.worker_id,
                receipt["lease_until"], reason,
            )
            return {"ok": False, "result": "rejected", "reason": reason, "receipt": rejected}
        if self.repository.has_recent_narrative_content(
            candidate.get("target_medium"), candidate.get("title"), candidate.get("body"),
            audience_scope=candidate.get("audience_scope"),
            audience_clan=candidate.get("audience_clan"),
            audience_owner=candidate.get("audience_owner"),
            limit=100,
        ):
            rejected = self.repository.reject_claimed_narrative_publication(
                receipt["publication_receipt_id"], self.worker_id,
                receipt["lease_until"], "duplicate_content",
            )
            return {
                "ok": False, "result": "rejected",
                "reason": "duplicate_content", "receipt": rejected,
            }
        published = self.repository.publish_claimed_narrative_candidate(
            receipt["publication_receipt_id"], self.worker_id, receipt["lease_until"]
        )
        if published and published.get("slot_superseded"):
            rejected = self.repository.reject_claimed_narrative_publication(
                receipt["publication_receipt_id"], self.worker_id,
                receipt["lease_until"], "slot_assignment_superseded",
            )
            return {
                "ok": False, "result": "rejected",
                "reason": "slot_assignment_superseded", "receipt": rejected,
            }
        if published and published.get("lifecycle_superseded"):
            rejected = self.repository.reject_claimed_narrative_publication(
                receipt["publication_receipt_id"], self.worker_id,
                receipt["lease_until"], "lifecycle_state_superseded",
            )
            return {
                "ok": False, "result": "rejected",
                "reason": "lifecycle_state_superseded", "receipt": rejected,
                "active_medium_record_id": published.get("active_medium_record_id"),
                "newer_task_id": published.get("newer_task_id"),
            }
        if not published:
            return {"ok": False, "result": "ownership_lost"}
        return {"ok": True, "result": "published", "expired": expired, **published}
