from __future__ import annotations

import os
import random
import socket
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass

from .ollama_client import ChaosOllamaClient, OllamaClientError
from .ollama_policy import (
    build_ollama_task_package,
    parse_and_validate_ollama_content,
    registered_ollama_policies,
    resolve_ollama_task_policy,
    verify_prompt_registry,
)
from .repository import GhostNetworkRepository, narrative_task_retry_backoff_seconds
from .narrative import GhostNarrativePublisher
from .narrative_support import NarrativeSupportLayer
from .llm.output_safety import verify_ghost_output_safety


OLLAMA_RUNTIME_CONTRACT_VERSION = "ghostnetwork-ollama-runtime-v1"
OLLAMA_TASK_RETRY_BACKOFF_SECONDS = (5, 10, 20, 40, 80)


def is_database_contention(error):
    return isinstance(error, sqlite3.OperationalError) and any(
        marker in str(error).lower()
        for marker in ("database is locked", "database table is locked", "database is busy")
    )


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OllamaWorkerConfig:
    enabled: bool = False
    poll_seconds: float = 1.5
    poll_jitter_seconds: float = 0.25
    lease_seconds: int = 180
    heartbeat_seconds: int = 30
    preflight_interval_seconds: int = 300
    preflight_retry_seconds: int = 30
    database_contention_min_seconds: float = 0.25
    database_contention_max_seconds: float = 2.0

    @classmethod
    def from_env(cls):
        return cls(
            enabled=_env_bool("CHAOS_OLLAMA_WORKER_ENABLED", False),
            poll_seconds=max(0.1, float(os.environ.get("CHAOS_OLLAMA_POLL_SECONDS", "1.5"))),
            poll_jitter_seconds=max(
                0.0, float(os.environ.get("CHAOS_OLLAMA_POLL_JITTER_SECONDS", "0.25"))
            ),
            lease_seconds=max(30, int(os.environ.get("CHAOS_OLLAMA_LEASE_SECONDS", "180"))),
            heartbeat_seconds=max(
                5, int(os.environ.get("CHAOS_OLLAMA_HEARTBEAT_SECONDS", "30"))
            ),
            preflight_interval_seconds=max(
                30, int(os.environ.get("CHAOS_OLLAMA_PREFLIGHT_INTERVAL_SECONDS", "300"))
            ),
            preflight_retry_seconds=max(
                5, int(os.environ.get("CHAOS_OLLAMA_PREFLIGHT_RETRY_SECONDS", "30"))
            ),
            database_contention_min_seconds=max(
                0.05,
                float(os.environ.get("CHAOS_OLLAMA_DB_CONTENTION_MIN_SECONDS", "0.25")),
            ),
            database_contention_max_seconds=max(
                0.05,
                float(os.environ.get("CHAOS_OLLAMA_DB_CONTENTION_MAX_SECONDS", "2.0")),
            ),
        )

    def validate(self):
        errors = []
        if self.heartbeat_seconds >= self.lease_seconds:
            errors.append("heartbeat_must_be_shorter_than_lease")
        if self.poll_seconds > 60:
            errors.append("poll_interval_out_of_policy")
        if self.database_contention_min_seconds > self.database_contention_max_seconds:
            errors.append("database_contention_backoff_invalid")
        if self.database_contention_max_seconds > 10:
            errors.append("database_contention_backoff_out_of_policy")
        return errors


def verify_ollama_runtime_policy(config=None):
    config = config or OllamaWorkerConfig.from_env()
    errors = list(config.validate())
    observed = tuple(narrative_task_retry_backoff_seconds(index) for index in range(1, 6))
    if observed != OLLAMA_TASK_RETRY_BACKOFF_SECONDS:
        errors.append("task_retry_backoff_contract_mismatch")
    return {
        "ok": not errors,
        "contract_version": OLLAMA_RUNTIME_CONTRACT_VERSION,
        "errors": errors,
        "task_retry_backoff_seconds": list(observed),
        "task_max_attempts": 5,
        "database_contention_backoff_seconds": {
            "minimum": config.database_contention_min_seconds,
            "maximum": config.database_contention_max_seconds,
        },
        "database_contention_is_retryable": True,
    }


class LeaseHeartbeat:
    def __init__(self, repository, task, worker_id, config):
        self.repository = repository
        self.task_id = task["outbox_id"]
        self.worker_id = worker_id
        self.config = config
        self._lease_until = task["lease_until"]
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread = None

    @property
    def lease_until(self):
        with self._lock:
            return self._lease_until

    @property
    def lost(self):
        return self._lost.is_set()

    def start(self):
        self._thread = threading.Thread(
            target=self._run,
            name="ollama-lease-heartbeat",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(1, self.config.heartbeat_seconds + 1))

    def _run(self):
        while not self._stop.wait(self.config.heartbeat_seconds):
            current = self.lease_until
            try:
                renewed = self.repository.renew_narrative_task_lease(
                    self.task_id,
                    self.worker_id,
                    current,
                    lease_seconds=self.config.lease_seconds,
                )
            except Exception:
                renewed = None
            if not renewed:
                self._lost.set()
                return
            with self._lock:
                self._lease_until = renewed["lease_until"]


def active_ollama_worker_policies():
    """Policies claimable after the deterministic single-source cutover."""
    return tuple(
        policy for policy in registered_ollama_policies()
        if not (
            policy.source_scope == "blacknet_world"
            and policy.task_variant == "world_digest"
        )
    )


class OllamaNarrativeWorker:
    def __init__(
        self, repository=None, client=None, config=None, worker_id=None,
        narrative_support=None,
    ):
        self.repository = repository or GhostNetworkRepository()
        self.client = client or ChaosOllamaClient()
        self.config = config or OllamaWorkerConfig.from_env()
        nonce = uuid.uuid4().hex[:10]
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{nonce}"
        self.narrative_support = narrative_support or NarrativeSupportLayer()
        # Sprint 135.5.1 cutover: keep legacy policy definitions readable for
        # historical audit/tests, but never claim the old multi-fact world
        # digest queue. New work is single-source only.
        self.policies = active_ollama_worker_policies()
        self._preflight_result = None
        self._preflight_expires_at = 0.0
        self._event_reconcile_expires_at = 0.0
        self._event_reconcile_result = None
        self._runtime_metrics = {
            "database_contention_total": 0,
            "database_contention_consecutive": 0,
            "last_runtime_error_code": "",
        }

    def status(self):
        return {
            "enabled": self.config.enabled,
            "worker_id": self.worker_id,
            "config_errors": self.config.validate(),
            "queue": self.repository.narrative_task_queue_counts(self.policies),
            "runtime_safety": verify_ollama_runtime_policy(self.config),
            "runtime_metrics": dict(self._runtime_metrics),
            "profiles_loaded": False,
        }

    def verify(self):
        try:
            result = self.client.verify()
        except OllamaClientError as exc:
            result = {"ok": False, "errors": [exc.code]}
        result["prompt_registry"] = verify_prompt_registry()
        result["narrative_support"] = self.narrative_support.verify()
        result["output_safety"] = verify_ghost_output_safety()
        result["runtime_safety"] = verify_ollama_runtime_policy(self.config)
        result["queue"] = self.repository.narrative_task_queue_counts(self.policies)
        result["database_ok"] = True
        result["worker_config_errors"] = self.config.validate()
        result["ok"] = (
            bool(result.get("ok"))
            and result["prompt_registry"]["ok"]
            and result["narrative_support"]["ok"]
            and result["output_safety"]["ok"]
            and result["runtime_safety"]["ok"]
            and result["database_ok"]
            and not result["worker_config_errors"]
        )
        return result

    def _ensure_preflight(self):
        now = time.monotonic()
        if self._preflight_result is not None and now < self._preflight_expires_at:
            return self._preflight_result
        result = self.verify()
        ttl = (
            self.config.preflight_interval_seconds
            if result.get("ok")
            else self.config.preflight_retry_seconds
        )
        self._preflight_result = result
        self._preflight_expires_at = now + ttl
        return result

    def _reconcile_persisted_events(self):
        now = time.monotonic()
        if self._event_reconcile_result is not None and now < self._event_reconcile_expires_at:
            return self._event_reconcile_result
        try:
            result = GhostNarrativePublisher(
                repository=self.repository
            ).reconcile_persisted_events(limit=500)
        except Exception as exc:
            result = {
                "ok": False,
                "processed": 0,
                "errors": [{"reason": "event_reconcile_failed", "error": str(exc)[:160]}],
            }
        self._event_reconcile_result = result
        self._event_reconcile_expires_at = now + self.config.preflight_interval_seconds
        return result

    def _finish_attempt(self, attempt, **kwargs):
        if attempt:
            self.repository.finish_narrative_attempt(attempt["attempt_id"], **kwargs)

    def _terminal_candidate_completion(self, task):
        candidate = self.repository.get_narrative_candidate_for_task(task["outbox_id"])
        if not candidate:
            return None
        completed = self.repository.complete_narrative_task(
            task["outbox_id"], self.worker_id, task["lease_until"]
        )
        if completed and candidate.get("attempt_id"):
            self.repository.finish_narrative_attempt(
                candidate["attempt_id"],
                status="completed",
                result="candidate_recovered",
                retryable=False,
            )
        return {
            "result": "candidate_recovered" if completed else "lease_lost",
            "task_id": task["outbox_id"],
            "candidate_id": candidate["candidate_id"],
        }

    def _complete_with_support(
        self, task, attempt, package, lease_until, model_validation,
        *, error_code="", error_message="",
    ):
        support = self.narrative_support.apply(
            task, package, model_validation, parse_and_validate_ollama_content
        )
        if not support:
            return None
        candidate = self.repository.record_narrative_candidate(
            task,
            attempt["attempt_id"],
            self.worker_id,
            lease_until,
            support["validation"],
            support["content"],
            {},
        )
        if not candidate:
            self._finish_attempt(
                attempt, status="lease_lost", error_code="lease_lost", retryable=True
            )
            return {"result": "lease_lost", "task_id": task["outbox_id"]}
        completed = self.repository.complete_narrative_task(
            task["outbox_id"], self.worker_id, lease_until
        )
        self._finish_attempt(
            attempt,
            status="completed" if completed else "lease_lost",
            result=(
                f"accepted_support_{support['mode']}"
                if completed else "lease_lost"
            ),
            error_code=error_code if completed else "lease_lost",
            error_message=error_message if completed else "",
            retryable=False,
        )
        return {
            "result": "completed" if completed else "lease_lost",
            "task_id": task["outbox_id"],
            "candidate_id": candidate["candidate_id"],
            "validation_status": candidate["validation_status"],
            "narrative_support_mode": support["mode"],
            "recovered_from_error_code": error_code,
            "input_bytes": package["input_bytes"],
            "fact_count": package["fact_count"],
        }

    def process_once(self, target_medium=None):
        try:
            result = self._process_once(target_medium=target_medium)
        except sqlite3.OperationalError as exc:
            if not is_database_contention(exc):
                raise
            self._runtime_metrics["database_contention_total"] += 1
            self._runtime_metrics["database_contention_consecutive"] += 1
            self._runtime_metrics["last_runtime_error_code"] = "sqlite_busy"
            retry_after = random.uniform(
                self.config.database_contention_min_seconds,
                self.config.database_contention_max_seconds,
            )
            return {
                "result": "database_contention",
                "error_code": "sqlite_busy",
                "retryable": True,
                "retry_after_seconds": round(retry_after, 3),
            }
        if result.get("result") != "database_contention":
            self._runtime_metrics["database_contention_consecutive"] = 0
            self._runtime_metrics["last_runtime_error_code"] = ""
        return result

    def _process_once(self, target_medium=None):
        if self.config.validate():
            return {"result": "invalid_worker_config", "errors": self.config.validate()}
        registry_status = verify_prompt_registry()
        if not registry_status["ok"]:
            return {"result": "invalid_prompt_registry", "errors": registry_status["errors"]}
        # Event-to-task repair is local SQLite work and must not depend on the
        # current availability of Ollama. Generation preflight comes after it.
        self._reconcile_persisted_events()
        preflight = self._ensure_preflight()
        if not preflight.get("ok"):
            return {"result": "preflight_failed", "errors": preflight.get("errors") or []}
        task = self.repository.claim_next_narrative_task(
            self.worker_id,
            lease_seconds=self.config.lease_seconds,
            eligible_policies=self.policies,
            target_medium=target_medium,
        )
        if not task:
            return {"result": "idle"}

        recovered = self._terminal_candidate_completion(task)
        if recovered:
            return recovered

        policy = resolve_ollama_task_policy(
            task.get("source_scope"), task.get("task_variant"), task.get("target_medium"),
            task.get("prompt_version"), task.get("output_schema_version"),
            task.get("model_policy_version"),
        )
        if not policy:
            dead = self.repository.dead_letter_narrative_task(
                task["outbox_id"], self.worker_id, task["lease_until"], "policy_not_registered"
            )
            return {"result": "dead_letter" if dead else "lease_lost", "task_id": task["outbox_id"]}
        try:
            package = build_ollama_task_package(task, policy)
        except ValueError as exc:
            dead = self.repository.dead_letter_narrative_task(
                task["outbox_id"], self.worker_id, task["lease_until"], str(exc)
            )
            return {"result": "dead_letter" if dead else "lease_lost", "task_id": task["outbox_id"]}

        processing = self.repository.mark_narrative_task_processing(
            task["outbox_id"], self.worker_id, task["lease_until"]
        )
        if not processing:
            return {"result": "lease_lost", "task_id": task["outbox_id"]}
        task = processing
        attempt = self.repository.begin_narrative_attempt(
            task,
            self.worker_id,
            task["lease_until"],
            policy.model_name,
            policy.model_digest,
            request_hash=package["request_hash"],
            input_bytes=package["input_bytes"],
            fact_count=package["fact_count"],
        )
        if not attempt:
            return {"result": "lease_lost", "task_id": task["outbox_id"]}

        heartbeat = LeaseHeartbeat(
            self.repository, task, self.worker_id, self.config
        ).start()
        try:
            generation = self.client.generate(package, policy)
        except OllamaClientError as exc:
            heartbeat.stop()
            if heartbeat.lost:
                self._finish_attempt(
                    attempt, status="lease_lost", error_code="lease_lost", retryable=True
                )
                return {"result": "lease_lost", "task_id": task["outbox_id"]}
            lease_until = heartbeat.lease_until
            if not exc.retryable or task["attempt_count"] >= task["max_attempts"]:
                supported = self._complete_with_support(
                    task,
                    attempt,
                    package,
                    lease_until,
                    {
                        "status": "rejected",
                        "errors": [f"model_transport_failure:{exc.code}"],
                        "output": None,
                    },
                    error_code=exc.code,
                    error_message=str(exc),
                )
                if supported:
                    return supported
            self._finish_attempt(
                attempt,
                status="retry" if exc.retryable else "failed",
                error_code=exc.code,
                error_message=str(exc),
                retryable=exc.retryable,
            )
            if exc.retryable:
                updated = self.repository.retry_narrative_task(
                    task["outbox_id"], self.worker_id, lease_until, exc.code
                )
            else:
                updated = self.repository.dead_letter_narrative_task(
                    task["outbox_id"], self.worker_id, lease_until, exc.code
                )
            return {
                "result": (updated or {}).get("status", "lease_lost"),
                "task_id": task["outbox_id"],
                "error_code": exc.code,
            }
        except Exception as exc:
            heartbeat.stop()
            lease_until = heartbeat.lease_until
            self._finish_attempt(
                attempt,
                status="retry" if not heartbeat.lost else "lease_lost",
                error_code="worker_exception" if not heartbeat.lost else "lease_lost",
                error_message=type(exc).__name__,
                retryable=True,
            )
            updated = None if heartbeat.lost else self.repository.retry_narrative_task(
                task["outbox_id"], self.worker_id, lease_until, "worker_exception"
            )
            return {"result": (updated or {}).get("status", "lease_lost"), "task_id": task["outbox_id"]}
        finally:
            heartbeat.stop()

        if heartbeat.lost:
            self._finish_attempt(
                attempt, status="lease_lost", error_code="lease_lost", retryable=True
            )
            return {"result": "lease_lost", "task_id": task["outbox_id"]}

        generation_data = generation.as_dict()
        validation = parse_and_validate_ollama_content(generation.content, package)
        lease_until = heartbeat.lease_until
        if validation["status"] == "invalid_json" and task["attempt_count"] < 2:
            self._finish_attempt(
                attempt,
                status="retry",
                result="invalid_json",
                error_code="invalid_json",
                retryable=True,
                generation=generation_data,
            )
            updated = self.repository.retry_narrative_task(
                task["outbox_id"], self.worker_id, lease_until, "invalid_json"
            )
            return {"result": (updated or {}).get("status", "lease_lost"), "task_id": task["outbox_id"]}
        if validation["status"] == "invalid_json":
            validation = {"status": "rejected", "errors": ["invalid_json"], "output": None}

        support = self.narrative_support.apply(
            task, package, validation, parse_and_validate_ollama_content
        )
        if support:
            validation = support["validation"]

        candidate = self.repository.record_narrative_candidate(
            task,
            attempt["attempt_id"],
            self.worker_id,
            lease_until,
            validation,
            support["content"] if support else generation.content,
            generation_data,
        )
        if not candidate:
            self._finish_attempt(
                attempt, status="lease_lost", error_code="lease_lost", retryable=True,
                generation=generation_data,
            )
            return {"result": "lease_lost", "task_id": task["outbox_id"]}
        completed = self.repository.complete_narrative_task(
            task["outbox_id"], self.worker_id, lease_until
        )
        self._finish_attempt(
            attempt,
            status="completed" if completed else "lease_lost",
            result=(
                f"accepted_support_{support['mode']}"
                if support else validation["status"]
            ),
            error_code="" if completed else "lease_lost",
            retryable=False,
            generation=generation_data,
        )
        return {
            "result": "completed" if completed else "lease_lost",
            "task_id": task["outbox_id"],
            "candidate_id": candidate["candidate_id"],
            "validation_status": candidate["validation_status"],
            "narrative_support_mode": support["mode"] if support else "",
            "input_bytes": package["input_bytes"],
            "fact_count": package["fact_count"],
        }

    def run(self, stop_event=None, on_result=None):
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            if self.config.enabled:
                result = self.process_once()
                if callable(on_result) and result.get("result") != "idle":
                    on_result(result)
            delay = (
                float(result.get("retry_after_seconds") or 0)
                if self.config.enabled and result.get("result") == "database_contention"
                else self.config.poll_seconds + random.uniform(
                    0.0, self.config.poll_jitter_seconds
                )
            )
            stop_event.wait(delay)
