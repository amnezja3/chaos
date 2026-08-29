from __future__ import annotations

import hashlib
import os

from .repository import GhostNetworkRepository
from .ollama_policy import owner_analysis_echoes_input, presentation_safety_errors


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
        if (
            candidate.get("source_scope") == "googleplex_app"
            and task.get("task_variant") == "owner-analysis"
            and owner_analysis_echoes_input(
                candidate.get("title"), candidate.get("body"), task.get("facts") or []
            )
        ):
            return False, "owner_analysis_echo"
        return True, "ok"

    def stage_accepted(self, limit=100):
        staged = []
        for candidate in self.repository.list_narrative_candidates(
            validation_status="accepted", limit=max(1, min(int(limit or 100), 500))
        ):
            task = self.repository.get_narrative_outbox(candidate.get("task_id"))
            valid, _reason = self.validate_candidate(candidate, task)
            if not valid:
                continue
            receipt = self.repository.ensure_narrative_publication(candidate["candidate_id"])
            if receipt:
                staged.append(receipt)
        return staged

    def process_once(self, lease_seconds=60):
        self.stage_accepted(limit=100)
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
        published = self.repository.publish_claimed_narrative_candidate(
            receipt["publication_receipt_id"], self.worker_id, receipt["lease_until"]
        )
        if not published:
            return {"ok": False, "result": "ownership_lost"}
        return {"ok": True, "result": "published", **published}
