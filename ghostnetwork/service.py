from __future__ import annotations

from time import perf_counter

from database import DB_PATH, PlayerOperationStore, PlayerTargetRuntimeStore
from config import (
    GHOSTNETWORK_DROP_CHANCE,
    GHOSTNETWORK_DROPS_ENABLED,
    GHOSTNETWORK_ABILITY_ALLOWED_CODES,
    GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS,
    GHOSTNETWORK_ABILITY_DURATION_SECONDS,
    GHOSTNETWORK_MIN_PART_DISTANCE_KM,
    GHOSTNETWORK_RUNTIME_MODE,
    GHOSTNETWORK_TEST_MODE,
)

from .catalog import (
    get_catalog_diagnostics,
    get_onboarding_catalog,
    normalize_ghostnetwork_profile_identity,
    validate_catalog,
)
from .abilities import GhostAbilityRegistry
from .ability_realizers import GhostAbilityProductionRealizer
from .archive import GhostArchiveService
from .closure import GhostNetworkClosureService
from .cycles import GhostCycleService, ensure_active_ghostnetwork_cycle
from .errors import RepositoryIntegrityError
from .conflicts import GhostDefenseRewardPolicy, GhostStrategicConflictService
from .lifecycle import GhostPartLifecycleService
from .module_state import GhostModuleStateService
from .narrative import GhostNarrativePublisher
from .part_assets import part_superpower_asset_contract, part_visual_asset_contract
from .repository import GhostNetworkRepository
from .rewards import GhostContributionService, GhostRewardService
from .reservations import GhostDropPolicy, GhostReservationService, is_ghostnetwork_eligible_target
from .territory import GhostTerritoryAdapter
from .topology import GhostTopologyService
from .transmission import GhostTransmissionService
from .visibility import build_viewer_projection


class GhostNetworkService:
    """Central GhostNetwork entry point for future integrations."""

    def __init__(
        self, repository=None, db_path=DB_PATH, drop_policy=None,
        ability_pilot_harness=None, ability_production_realizer=None,
    ):
        self.repository = repository or GhostNetworkRepository(db_path=db_path)
        self.cycles = GhostCycleService(repository=self.repository)
        self.topology = GhostTopologyService(repository=self.repository)
        self.lifecycle = GhostPartLifecycleService(repository=self.repository)
        self.territory = GhostTerritoryAdapter(repository=self.repository, lifecycle=self.lifecycle)
        self.modules = GhostModuleStateService(repository=self.repository)
        self.abilities = GhostAbilityRegistry(repository=self.repository, module_state_service=self.modules)
        # Certification-only dependency injection. Production construction does
        # not provide a harness and therefore cannot select a test realizer.
        self.ability_pilot_harness = ability_pilot_harness
        self.ability_production_realizer = (
            None if ability_production_realizer is False else ability_production_realizer
        )
        if ability_production_realizer is None and ability_pilot_harness is None:
            self.ability_production_realizer = GhostAbilityProductionRealizer(
                PlayerOperationStore(self.repository.db_path),
                PlayerTargetRuntimeStore(self.repository.db_path),
            )
        self.contributions = GhostContributionService(repository=self.repository)
        self.rewards = GhostRewardService(
            repository=self.repository,
            contribution_service=self.contributions,
        )
        self.conflicts = GhostStrategicConflictService(
            repository=self.repository,
            reward_service=self.rewards,
            policy=GhostDefenseRewardPolicy(),
        )
        self.reservations = GhostReservationService(
            repository=self.repository,
            policy=drop_policy or GhostDropPolicy(),
        )
        self.closure = GhostNetworkClosureService(
            repository=self.repository,
            topology_service=self.topology,
            module_state_service=self.modules,
        )
        self.transmission = GhostTransmissionService(
            repository=self.repository,
            lifecycle_service=self.lifecycle,
            closure_service=self.closure,
        )
        self.narrative = GhostNarrativePublisher(repository=self.repository)
        self.archive = GhostArchiveService(repository=self.repository)

    def _event_cursor(self, cycle_id=""):
        cycle_id = str(cycle_id or "").strip()
        if not cycle_id:
            cycle_id = str((self.repository.get_active_cycle() or {}).get("cycle_id") or "")
        return cycle_id, (
            self.repository.get_state_version(cycle_id) if cycle_id else 0
        )

    @staticmethod
    def _collect_returned_events(value, seen=None):
        seen = seen if isinstance(seen, set) else set()
        events = []
        if isinstance(value, dict):
            if value.get("event_id") and value.get("event_type"):
                event_id = str(value.get("event_id") or "").strip()
                if event_id and event_id not in seen:
                    seen.add(event_id)
                    events.append(value)
            for item in value.values():
                events.extend(GhostNetworkService._collect_returned_events(item, seen))
        elif isinstance(value, (list, tuple)):
            for item in value:
                events.extend(GhostNetworkService._collect_returned_events(item, seen))
        return events

    def _dispatch_persisted_events(self, result=None, *, cycle_id="", after_state_version=None):
        """Fail-open post-commit dispatch from canonical persisted event rows."""
        try:
            candidates = self._collect_returned_events(result)
            if cycle_id and after_state_version is not None:
                candidates.extend(
                    self.repository.list_events_after(
                        cycle_id, after_state_version, limit=250,
                    )
                )
            dispatch = self.narrative.publish_persisted_events(candidates)
        except Exception as exc:
            dispatch = {
                "ok": False,
                "processed": 0,
                "results": [],
                "errors": [{"reason": "narrative_dispatch_failed", "error": str(exc)[:160]}],
            }
        if isinstance(result, dict):
            result["narrative_dispatch"] = dispatch
        return dispatch

    def get_active_cycle(self):
        return self.repository.get_active_cycle()

    def get_state_version(self):
        active = self.repository.get_active_cycle()
        if not active:
            return 0
        return self.repository.get_state_version(active["cycle_id"])

    def get_snapshot_for_viewer(self, viewer=None):
        active = self.repository.get_active_cycle()
        if not active:
            return {
                "viewer": viewer or "internal",
                "projection": "internal_recovery",
                "snapshot": {
                    "cycle": None,
                    "parts": [],
                    "connections": [],
                    "active_reservations": [],
                    "state_version": 0,
                },
            }
        snapshot = self.repository.build_internal_snapshot(active["cycle_id"])
        validation = self.topology.validate_topology(active["cycle_id"])
        snapshot["topology"].update(
            {
                "checksum": validation["topology_checksum"],
                "ring_order": validation["ring_order"],
                "validation": validation,
            }
        )
        return build_viewer_projection(snapshot, viewer=viewer)

    def health_check(self):
        report = self.repository.health_check()
        catalog = get_catalog_diagnostics()
        report["catalog"] = catalog
        if not catalog["validation"]["ok"]:
            report["ok"] = False
            report.setdefault("errors", []).append("catalog_validation_failed")
        return report

    def get_runtime_readiness(self):
        """Return system-only readiness without mutating GhostNetwork state."""
        errors = []
        warnings = []
        health = self.health_check()
        cycle = self.repository.get_active_cycle()
        parts_summary = self.cycles.get_parts_summary(cycle["cycle_id"]) if cycle else {
            "parts_total": 0,
            "parts_pooled": 0,
            "parts_reserved": 0,
            "parts_public": 0,
            "parts_contained": 0,
            "parts_active": 0,
        }
        topology_valid = False
        last_event = None
        if not health.get("ok"):
            errors.extend(health.get("errors") or ["repository_unavailable"])
        if not cycle:
            errors.append("no_active_cycle")
        else:
            if cycle.get("status") != "active":
                errors.append("cycle_not_active")
            integrity = self.cycles.validate_cycle_integrity(
                cycle["cycle_id"], require_catalog=bool(cycle.get("catalog_version"))
            )
            errors.extend(integrity.get("errors") or [])
            warnings.extend(integrity.get("warnings") or [])
            topology = self.topology.validate_topology(cycle["cycle_id"])
            topology_valid = bool(topology.get("valid"))
            if not topology_valid:
                errors.append("topology_invalid")
            event = self.repository.get_last_event(cycle["cycle_id"])
            if event:
                last_event = {
                    "event_type": event.get("event_type") or "",
                    "created_at": event.get("created_at") or "",
                    "state_version": int(event.get("state_version") or 0),
                }
        chance = float(GHOSTNETWORK_DROP_CHANCE)
        min_part_distance_km = float(GHOSTNETWORK_MIN_PART_DISTANCE_KM)
        if chance < 0 or chance > 1:
            errors.append("drop_chance_out_of_range")
        if GHOSTNETWORK_DROPS_ENABLED and not (0 < chance <= 1):
            errors.append("drops_enabled_without_valid_chance")
        if not GHOSTNETWORK_DROPS_ENABLED:
            errors.append("drops_disabled")
        if min_part_distance_km < 0:
            errors.append("min_part_distance_out_of_range")
        runtime_mode = GHOSTNETWORK_RUNTIME_MODE or "production"
        if runtime_mode not in {"production", "development", "test"}:
            errors.append("invalid_runtime_mode")
        if GHOSTNETWORK_TEST_MODE and runtime_mode == "production":
            errors.append("test_mode_forbidden_in_production")
        effects = self.repository.get_capture_effect_summary()
        if effects["pending"]:
            errors.append("pending_capture_effects")
        if effects["failed"]:
            errors.append("unreconciled_capture_effects")
        telemetry = self.repository.get_pipeline_telemetry_summary(
            cycle["cycle_id"] if cycle else ""
        )
        ability_telemetry = self.repository.get_ability_telemetry_summary(
            cycle["cycle_id"] if cycle else ""
        )
        errors = sorted(set(errors))
        return {
            "ok": not errors,
            "ready": not errors,
            "status": "READY" if not errors else "NOT READY",
            "active_cycle_id": (cycle or {}).get("cycle_id") or "",
            "parts_total": int(parts_summary.get("parts_total") or 0),
            "pooled": int(parts_summary.get("parts_pooled") or 0),
            "reserved": int(parts_summary.get("parts_reserved") or 0),
            "public": int(parts_summary.get("parts_public") or 0),
            "contained": int(parts_summary.get("parts_contained") or 0),
            "active": int(parts_summary.get("parts_active") or 0),
            "drops_enabled": bool(GHOSTNETWORK_DROPS_ENABLED),
            "drop_chance": chance,
            "min_part_distance_km": min_part_distance_km,
            "runtime_mode": runtime_mode,
            "test_mode": bool(GHOSTNETWORK_TEST_MODE),
            "topology_valid": topology_valid,
            "pending_effects": effects["pending"],
            "unreconciled_effects": effects["failed"],
            "last_event": last_event,
            "telemetry": telemetry,
            "ability_telemetry": ability_telemetry,
            "errors": errors,
            "warnings": sorted(set(warnings)),
        }

    def get_catalog_diagnostics(self):
        return get_catalog_diagnostics()

    def ensure_active_cycle(self):
        result = self.cycles.ensure_active_cycle()
        if result.get("created"):
            cycle_id = str((result.get("cycle") or {}).get("cycle_id") or "")
            self._dispatch_persisted_events(
                result, cycle_id=cycle_id, after_state_version=0,
            )
        return result

    def get_cycle_diagnostics(self, cycle_id=None):
        return self.cycles.get_cycle_diagnostics(cycle_id)

    def get_topology_diagnostics(self, cycle_id=None):
        active = self.repository.get_active_cycle()
        selected_cycle_id = cycle_id or (active or {}).get("cycle_id")
        if not selected_cycle_id:
            return {"ok": False, "valid": False, "cycle_id": "", "reason": "no_cycle"}
        return self.topology.validate_topology(selected_cycle_id)

    def evaluate_network_readiness(self, cycle_id):
        return self.closure.evaluate_network_readiness(cycle_id)

    def attempt_cycle_lock(self, cycle_id, trigger_event_id=""):
        cycle_id, cursor = self._event_cursor(cycle_id)
        result = self.closure.attempt_cycle_lock(cycle_id, trigger_event_id=trigger_event_id)
        self._dispatch_persisted_events(
            result, cycle_id=cycle_id, after_state_version=cursor,
        )
        return result

    def build_lock_snapshot(self, cycle_id, trigger_event_id=""):
        return self.closure.build_lock_snapshot(cycle_id, trigger_event_id=trigger_event_id)

    def get_locked_cycle_snapshot(self, cycle_id):
        return self.closure.get_locked_cycle_snapshot(cycle_id)

    def validate_locked_snapshot(self, cycle_id):
        return self.closure.validate_locked_snapshot(cycle_id)

    def start_transmission(self, cycle_id):
        cycle_id, cursor = self._event_cursor(cycle_id)
        result = self.transmission.start_transmission(cycle_id)
        return self._with_transmission_narrative(result, after_state_version=cursor)

    def resume_interrupted_transmission(self, cycle_id):
        cycle_id, cursor = self._event_cursor(cycle_id)
        result = self.transmission.resume_interrupted_transmission(cycle_id)
        # Replay only the bounded transmission tail; canonical task identity
        # makes this safe while avoiding a full-cycle narrative backfill.
        return self._with_transmission_narrative(
            result, after_state_version=max(0, cursor - 50),
        )

    def validate_transmission(self, cycle_id):
        return self.transmission.validate_transmission(cycle_id)

    def reconcile_transmission_postcommit(self, cycle_id):
        """Repair idempotent archive/narrative effects after signal commit.

        The durable marker is deliberately narrower than the complete endgame
        settlement contract. Delta fan-out and reward profile projection get
        their own markers in P0.3 and P0.2, respectively.
        """
        cycle_id = str(cycle_id or "").strip()
        marker_key = f"ghost:endgame_postcommit_reconciled:{cycle_id}:archive_narrative:v1"
        existing = self.repository.get_event_by_dedupe_key(marker_key)
        if existing:
            return {
                "ok": True,
                "status": "complete",
                "cycle_id": cycle_id,
                "idempotent": True,
                "marker_event": existing,
            }

        cycle = self.repository.get_cycle(cycle_id)
        signal = self.repository.get_signal_for_cycle(cycle_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(cycle_id)
        reasons = []
        if not cycle or cycle.get("status") != "stabilizing":
            reasons.append("cycle_not_stabilizing")
        if not signal:
            reasons.append("signal_missing")
        if not lock_snapshot:
            reasons.append("lock_snapshot_missing")
        if reasons:
            return {
                "ok": False,
                "status": "blocked",
                "cycle_id": cycle_id,
                "reasons": reasons,
            }

        try:
            archive = self.archive.finalize_signal_archive(signal["signal_id"])
        except Exception as exc:
            archive = {"ok": False, "error": str(exc)[:160]}
        if not archive.get("ok"):
            return {
                "ok": False,
                "status": "retry",
                "cycle_id": cycle_id,
                "reasons": ["archive_reconciliation_failed"],
                "archive": archive,
            }

        first_version = max(0, int(lock_snapshot.get("state_version") or 0) - 1)
        events = self.repository.list_events_after(
            cycle_id, state_version=first_version, limit=100,
        )
        event_types = {str(event.get("event_type") or "") for event in events}
        required_event_types = {
            "ghost.cycle_locked",
            "ghost.signal_sent",
            "ghost.version_changed",
            "ghost.restart_required",
            "ghost.stabilization_started",
        }
        missing_event_types = sorted(required_event_types - event_types)
        current_version = int(self.repository.get_state_version(cycle_id) or 0)
        maximum_event_version = max(
            (int(event.get("state_version") or 0) for event in events),
            default=first_version,
        )
        if missing_event_types or maximum_event_version < current_version:
            reasons = []
            if missing_event_types:
                reasons.append("postcommit_events_missing")
            if maximum_event_version < current_version:
                reasons.append("postcommit_event_window_exceeded")
            return {
                "ok": False,
                "status": "blocked",
                "cycle_id": cycle_id,
                "reasons": reasons,
                "missing_event_types": missing_event_types,
                "events_checked": len(events),
                "current_state_version": current_version,
                "maximum_event_version": maximum_event_version,
                "archive": archive,
            }
        try:
            narrative = self.narrative.publish_persisted_events(events)
        except Exception as exc:
            narrative = {
                "ok": False,
                "processed": 0,
                "results": [],
                "errors": [{"reason": "narrative_dispatch_failed", "error": str(exc)[:160]}],
            }
        if not narrative.get("ok"):
            return {
                "ok": False,
                "status": "retry",
                "cycle_id": cycle_id,
                "reasons": ["narrative_reconciliation_failed"],
                "archive": archive,
                "narrative": narrative,
            }

        try:
            marker = self.repository.append_event(
                "ghost.endgame_postcommit_reconciled",
                cycle_id=cycle_id,
                entity_id=signal["signal_id"],
                audience_scope="system",
                dedupe_key=marker_key,
                payload={
                    "signal_id": signal["signal_id"],
                    "effects": ["archive", "narrative"],
                    "events_checked": len(events),
                    "contract_version": "ghostnetwork-endgame-postcommit-v1",
                },
            )
        except RepositoryIntegrityError:
            marker = self.repository.get_event_by_dedupe_key(marker_key)
        return {
            "ok": True,
            "status": "complete",
            "cycle_id": cycle_id,
            "idempotent": False,
            "archive": archive,
            "narrative": narrative,
            "marker_event": marker,
        }

    def validate_rollover_settlement(self, cycle_id):
        """Validate the mechanical endgame ledger before creating a new cycle."""
        cycle_id = str(cycle_id or "").strip()
        cycle = self.repository.get_cycle(cycle_id)
        signal = self.repository.get_signal_for_cycle(cycle_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(cycle_id)
        parts = self.repository.list_parts(cycle_id) if cycle else []
        connections = self.repository.list_connections(cycle_id) if cycle else []
        history = (
            self.repository.list_historical_nodes_for_signal(signal["signal_id"])
            if signal else []
        )
        rewards = (
            self.repository.list_rewards(signal_id=signal["signal_id"], limit=5000)
            if signal else []
        )
        reasons = []
        if not cycle:
            reasons.append("cycle_missing")
        elif cycle.get("status") not in {"stabilizing", "closed"}:
            reasons.append("cycle_not_stabilizing_or_closed")
        if not signal or signal.get("status") != "sent":
            reasons.append("sent_signal_missing")
        if not lock_snapshot:
            reasons.append("lock_snapshot_missing")
        elif signal and signal.get("lock_snapshot_id") != lock_snapshot.get("lock_snapshot_id"):
            reasons.append("signal_lock_snapshot_mismatch")
        if lock_snapshot:
            lock_validation = self.closure.validate_locked_snapshot(cycle_id)
            if not lock_validation.get("valid"):
                reasons.append("lock_snapshot_invalid")
        signal_id = str((signal or {}).get("signal_id") or "")
        if len(parts) != 20 or any(
            part.get("status") != "consumed"
            or part.get("consumed_signal_id") != signal_id
            for part in parts
        ):
            reasons.append("parts_not_fully_consumed")
        if connections:
            reasons.append("connections_not_closed")
        if len(history) != 20 or any(node.get("signal_id") != signal_id for node in history):
            reasons.append("historical_nodes_incomplete")

        snapshot = (lock_snapshot or {}).get("snapshot") or {}
        closing = snapshot.get("closing") or {}
        expected_reward_keys = {
            f"ghost-signal:{signal_id}:node:{part.get('part_id')}:{owner_id}"
            for part in snapshot.get("parts") or []
            for owner_id in [str(part.get("territory_owner_id") or part.get("discovered_by") or "").strip()]
            if owner_id
        }
        closer_id = str(closing.get("closing_player_id") or "").strip()
        if closer_id:
            expected_reward_keys.add(f"ghost-signal:{signal_id}:closer:{closer_id}")
        actual_reward_keys = {str(reward.get("reward_key") or "") for reward in rewards}
        if not expected_reward_keys or not expected_reward_keys.issubset(actual_reward_keys):
            reasons.append("final_rewards_incomplete")
        if not self.repository.get_event_by_dedupe_key(
            f"ghost:endgame_postcommit_reconciled:{cycle_id}:archive_narrative:v1"
        ):
            reasons.append("archive_narrative_reconciliation_missing")
        if not self.repository.get_event_by_dedupe_key(
            f"ghost:endgame_delta_reconciled:{cycle_id}:v1"
        ):
            reasons.append("delta_reconciliation_missing")
        return {
            "ok": not reasons,
            "cycle_id": cycle_id,
            "reasons": sorted(set(reasons)),
            "cycle": cycle,
            "signal": signal,
            "counts": {
                "parts": len(parts),
                "connections": len(connections),
                "historical_nodes": len(history),
                "expected_rewards": len(expected_reward_keys),
                "rewards": len(rewards),
            },
        }

    def rollover_stabilized_cycle(self, cycle_id):
        """Atomically close one settled cycle and activate exactly one successor."""
        cycle_id = str(cycle_id or "").strip()
        with self.repository.transaction():
            cycle = self.repository.get_cycle(cycle_id)
            if not cycle:
                return {"ok": False, "status": "blocked", "reasons": ["cycle_missing"]}
            expected_signal_number = int(cycle.get("signal_number") or 0) + 1
            active = self.repository.get_active_cycle()
            if cycle.get("status") == "closed":
                if active and int(active.get("signal_number") or 0) == expected_signal_number:
                    return {
                        "ok": True, "status": "rolled_over", "idempotent": True,
                        "closed_cycle": cycle, "next_cycle": active,
                    }
                if active:
                    return {
                        "ok": False, "status": "blocked",
                        "reasons": ["unexpected_active_cycle_after_close"],
                        "closed_cycle": cycle, "active_cycle": active,
                    }
            elif cycle.get("status") != "stabilizing":
                return {
                    "ok": False, "status": "blocked",
                    "reasons": ["cycle_not_stabilizing_or_closed"], "cycle": cycle,
                }

            settlement = self.validate_rollover_settlement(cycle_id)
            if not settlement.get("ok"):
                return {
                    "ok": False, "status": "settlement_blocked",
                    "reasons": settlement.get("reasons") or [], "settlement": settlement,
                }
            closed = cycle
            if cycle.get("status") == "stabilizing":
                closed = self.cycles.close_cycle(cycle_id)
            created = self.cycles.create_cycle(
                signal_number=expected_signal_number,
                ghostsystem_version=int(closed.get("ghostsystem_version") or expected_signal_number),
            )
            return {
                "ok": True,
                "status": "rolled_over",
                "idempotent": False,
                "closed_cycle": closed,
                "next_cycle": created.get("cycle"),
                "created": created,
                "settlement": settlement,
            }

    def _with_transmission_narrative(self, result, after_state_version=None):
        result = result if isinstance(result, dict) else {}
        signal = result.get("signal") if isinstance(result.get("signal"), dict) else {}
        signal_id = signal.get("signal_id")
        if not result.get("ok") or not signal_id:
            return result
        try:
            archive = self.archive.finalize_signal_archive(signal_id)
        except Exception as exc:  # archive/readiness failures must not rollback transmission
            archive = {"ok": False, "error": str(exc), "signal_id": signal_id}
        try:
            narrative = self.narrative.publish_signal_transmission(signal_id)
        except Exception as exc:  # media/outbox failures must not rollback mechanics
            narrative = {"ok": False, "errors": [{"medium": "narrative", "error": str(exc)}], "outbox": []}
        result["archive"] = archive
        result["narrative"] = narrative
        self._dispatch_persisted_events(
            result,
            cycle_id=str(result.get("cycle_id") or signal.get("cycle_id") or ""),
            after_state_version=after_state_version,
        )
        return result

    def publish_narrative_event(self, event):
        return self.narrative.publish_domain_event(event)

    def retry_failed_narrative_publications(self, limit=100):
        return self.narrative.retry_failed_publications(limit=limit)

    def list_narrative_outbox(self, **filters):
        return self.repository.list_narrative_outbox(**filters)

    def enqueue_narrative_task(self, task):
        return self.repository.enqueue_narrative_task(task)

    def get_narrative_task(self, task_id):
        return self.repository.get_narrative_outbox(task_id)

    def claim_next_narrative_task(self, worker_id, **options):
        return self.repository.claim_next_narrative_task(worker_id, **options)

    def renew_narrative_task_lease(
        self,
        task_id,
        worker_id,
        expected_lease_until,
        **options,
    ):
        return self.repository.renew_narrative_task_lease(
            task_id,
            worker_id,
            expected_lease_until,
            **options,
        )

    def mark_narrative_task_processing(
        self,
        task_id,
        worker_id,
        expected_lease_until,
        **options,
    ):
        return self.repository.mark_narrative_task_processing(
            task_id,
            worker_id,
            expected_lease_until,
            **options,
        )

    def complete_narrative_task(
        self,
        task_id,
        worker_id,
        expected_lease_until,
        **options,
    ):
        return self.repository.complete_narrative_task(
            task_id,
            worker_id,
            expected_lease_until,
            **options,
        )

    def retry_narrative_task(
        self,
        task_id,
        worker_id,
        expected_lease_until,
        reason_code,
        **options,
    ):
        return self.repository.retry_narrative_task(
            task_id,
            worker_id,
            expected_lease_until,
            reason_code,
            **options,
        )

    def dead_letter_narrative_task(
        self,
        task_id,
        worker_id,
        expected_lease_until,
        reason_code,
        **options,
    ):
        return self.repository.dead_letter_narrative_task(
            task_id,
            worker_id,
            expected_lease_until,
            reason_code,
            **options,
        )

    def recover_expired_narrative_leases(self, **options):
        return self.repository.recover_expired_narrative_leases(**options)

    def finalize_signal_archive(self, signal_id):
        return self.archive.finalize_signal_archive(signal_id)

    def list_signal_archive(self, limit=50):
        return self.archive.list_signals(limit=limit)

    def get_signal_archive_detail(self, signal_id, include_private=False):
        return self.archive.get_signal_detail(signal_id, include_private=include_private)

    def get_player_archive_history(self, player_id, limit=50):
        return self.archive.get_player_history(player_id, limit=limit)

    def get_clan_archive_history(self, limit=100):
        return self.archive.get_clan_history(limit=limit)

    def get_historical_map_layer(self, signal_id=None, limit=200):
        return self.archive.get_historical_map_layer(signal_id=signal_id, limit=limit)

    def get_archive_readiness_report(self):
        report = self.archive.build_readiness_report()
        catalog = get_catalog_diagnostics()
        report["catalog"] = catalog
        if not catalog["validation"]["ok"]:
            report["ok"] = False
        return report

    def get_onboarding_catalog(self):
        return get_onboarding_catalog()

    def validate_catalog(self):
        return validate_catalog()

    def is_target_eligible_for_drop(self, target):
        return is_ghostnetwork_eligible_target(target)

    def on_target_aimed(self, player, target, context=None):
        result = self.reservations.on_target_aimed(player, target, context=context)
        self._record_pipeline_outcome("aim", result)
        status = result.get("status") or "unknown"
        if status not in {"no_active_cycle", "cycle_not_active", "not_eligible"}:
            self.repository.record_pipeline_outcome("aim", "eligible", result.get("cycle_id") or "")
        if status in {"roll_missed", "reserved", "no_candidate_parts", "reservation_conflict"}:
            self.repository.record_pipeline_outcome("aim", "roll", result.get("cycle_id") or "")
        if result.get("internal_reason") == "part_too_close":
            self.repository.record_pipeline_outcome("aim", "part_too_close", result.get("cycle_id") or "")
        if status == "reserved":
            self.repository.record_pipeline_outcome("aim", "reservation", result.get("cycle_id") or "")
        return result

    def _record_pipeline_outcome(self, phase, result):
        result = result if isinstance(result, dict) else {}
        cycle_id = result.get("cycle_id") or (self.repository.get_active_cycle() or {}).get("cycle_id") or ""
        try:
            self.repository.record_pipeline_outcome(
                phase, result.get("status") or "unknown", cycle_id
            )
        except Exception:
            # Gameplay hooks stay fail-open; repository health/readiness exposes storage failures.
            return False
        return True

    def attach_reservation_to_operation(self, player_id, target_id, operation_id):
        return self.reservations.attach_reservation_to_operation(player_id, target_id, operation_id)

    def release_reservation(self, reservation_id, reason):
        return self.reservations.release_reservation(reservation_id, reason)

    def expire_due_reservations(self, now=None):
        return self.reservations.expire_due_reservations(now=now)

    def get_reservation_status(self):
        return self.reservations.get_reservation_status()

    def on_territory_stabilized(self, event):
        cycle_id, cursor = self._event_cursor()
        result = self._with_module_progress(self.territory.on_territory_stabilized(event))
        self._dispatch_persisted_events(result, cycle_id=cycle_id, after_state_version=cursor)
        return result

    def on_territory_contested(self, event):
        cycle_id, cursor = self._event_cursor()
        result = self._with_module_progress(self.territory.on_territory_contested(event))
        self._dispatch_persisted_events(result, cycle_id=cycle_id, after_state_version=cursor)
        return result

    def on_territory_released(self, event):
        cycle_id, cursor = self._event_cursor()
        result = self._with_module_progress(self.territory.on_territory_released(event))
        self._dispatch_persisted_events(result, cycle_id=cycle_id, after_state_version=cursor)
        return result

    def on_territory_owner_changed(self, event):
        cycle_id, cursor = self._event_cursor()
        result = self._with_module_progress(self.territory.on_territory_owner_changed(event))
        self._dispatch_persisted_events(result, cycle_id=cycle_id, after_state_version=cursor)
        return result

    def reconcile_parts_with_territories(self, cycle_id=None, territories=None, apply=False):
        selected_cycle_id, cursor = self._event_cursor(cycle_id)
        report = self.territory.reconcile_parts_with_territories(cycle_id=cycle_id, territories=territories, apply=apply)
        if apply:
            report = self._with_module_progress(report, changed_key="changes")
            self._dispatch_persisted_events(
                report, cycle_id=selected_cycle_id, after_state_version=cursor,
            )
            return report
        return report

    def _with_module_progress(self, report, changed_key="changed"):
        report = report if isinstance(report, dict) else {}
        module_progress = []
        for item in report.get(changed_key, []) or []:
            part = None
            if isinstance(item, dict):
                part = item.get("part") if isinstance(item.get("part"), dict) else item
            part_id = (part or {}).get("part_id") if isinstance(part, dict) else ""
            if not part_id and isinstance(item, dict):
                part_id = item.get("part_id")
            if not part_id:
                continue
            module_progress.append(self.modules.recompute_after_part_change(part_id))
        report["module_progress"] = module_progress
        return report

    @staticmethod
    def _target_id(target):
        target = target if isinstance(target, dict) else {}
        return str(target.get("target_id") or target.get("id") or "").strip()

    @staticmethod
    def _operation_id(operation=None, result=None, context=None):
        for source in (operation, result, context):
            if isinstance(source, dict):
                value = source.get("operation_id") or source.get("id")
                if value:
                    return str(value).strip()
            elif source:
                return str(source).strip()
        return ""

    @staticmethod
    def _is_final_capture_success(result=None, context=None):
        result = result if isinstance(result, dict) else {}
        context = context if isinstance(context, dict) else {}
        return bool(
            result.get("target_captured") is True
            or result.get("captured_target") is True
            or context.get("target_captured") is True
            or context.get("capture_confirmed") is True
        )

    def on_target_hacked(self, player, target, operation=None, result=None, context=None):
        cycle_id, cursor = self._event_cursor()
        outcome = self._on_target_hacked(
            player, target, operation=operation, result=result, context=context
        )
        self._record_pipeline_outcome("capture", outcome)
        if outcome.get("status") == "already_discovered":
            part = outcome.get("part") if isinstance(outcome.get("part"), dict) else {}
            discovered = [
                event for event in self.repository.list_events(cycle_id, limit=1000)
                if event.get("event_type") == "ghost.part_discovered"
                and event.get("part_id") == part.get("part_id")
            ][-1:]
            outcome["recovered_events"] = discovered
        self._dispatch_persisted_events(
            outcome, cycle_id=cycle_id, after_state_version=cursor,
        )
        return outcome

    def _on_target_hacked(self, player, target, operation=None, result=None, context=None):
        """Commit a hidden GhostNetwork reservation after a real target capture.

        This hook is intentionally strict: it ignores scans, partial disarms,
        operation starts and frontend acknowledgements. Only the canonical
        persisted target-capture flow may pass `target_captured=True`.
        """
        raw_player = player if isinstance(player, dict) else {}
        player_identity = normalize_ghostnetwork_profile_identity(raw_player)
        player_identity["player_id"] = str(
            raw_player.get("player_id") or raw_player.get("username") or raw_player.get("login") or ""
        ).strip()
        player_id = player_identity.get("player_id") or ""
        target_id = self._target_id(target)
        if not self._is_final_capture_success(result=result, context=context):
            return {"ok": True, "status": "not_final_success"}
        if not player_id:
            return {"ok": False, "status": "missing_player"}
        if not target_id:
            return {"ok": False, "status": "missing_target"}
        eligibility = is_ghostnetwork_eligible_target(target)
        if not eligibility.get("eligible"):
            return {"ok": True, "status": "target_not_eligible", "reason": eligibility.get("reason")}

        self.expire_due_reservations()
        active = self.repository.get_active_cycle()
        if not active:
            return {"ok": True, "status": "no_active_cycle"}
        if active.get("status") != "active":
            return {"ok": True, "status": "cycle_not_active"}

        operation_id = self._operation_id(operation=operation, result=result, context=context)
        reservation = self.repository.find_active_reservation_for_discovery(
            active["cycle_id"],
            player_id,
            target_id,
            operation_id=operation_id,
        )
        if not reservation:
            part = self.repository.find_part_by_target(active["cycle_id"], target_id)
            if part and part.get("status") == "public":
                return {
                    "ok": True,
                    "status": "already_discovered",
                    "part": part,
                    "reservation": None,
                    "event": None,
                }
            return {"ok": True, "status": "no_matching_reservation"}
        if (
            operation_id
            and reservation.get("operation_id")
            and reservation.get("operation_id") != operation_id
        ):
            return {"ok": True, "status": "operation_mismatch"}

        return self.lifecycle.discover_part(
            reservation["reservation_id"],
            player=player_identity,
            target=target,
            operation_id=operation_id or reservation.get("operation_id") or "",
            result=result,
            context=context,
        )

    def on_territory_event(self, *args, **kwargs):
        return {"ok": False, "status": "not_implemented", "hook": "on_territory_event"}

    def resolve_part_state(self, part_or_part_id, *args, **kwargs):
        part = part_or_part_id
        if not isinstance(part, dict):
            part = self.repository.get_part(part_or_part_id)
        if not part:
            return {"ok": False, "status": "part_not_found", "part_id": str(part_or_part_id or "")}
        return self.modules.resolve_part_module_state(part)

    def resolve_part_module_state(self, part_or_part_id):
        return self.resolve_part_state(part_or_part_id)

    def resolve_part_viewer_relation(self, part_or_part_id, viewer):
        part = part_or_part_id
        if not isinstance(part, dict):
            part = self.repository.get_part(part_or_part_id)
        if not part:
            return ""
        return self.modules.resolve_part_viewer_relation(part, viewer)

    def resolve_cycle_module_states(self, cycle_id):
        return self.modules.resolve_cycle_module_states(cycle_id)

    def resolve_player_abilities(self, player_context):
        return self.abilities.resolve_player_abilities(player_context)

    def _ability_presentation(self, ability):
        ability = ability if isinstance(ability, dict) else {}
        part_code = str(ability.get("part_code") or ability.get("source_part_code") or "").strip()
        clan_code = str(ability.get("clan_code") or "").strip()
        parts = {
            str(item.get("part_code") or ""): item
            for item in self.abilities.catalog.get("parts", [])
            if isinstance(item, dict)
        }
        clans = {
            str(item.get("code") or ""): item
            for item in self.abilities.catalog.get("clans", [])
            if isinstance(item, dict)
        }
        part_definition = parts.get(part_code) or {}
        asset = part_superpower_asset_contract(part_definition)
        timer_asset = part_visual_asset_contract(part_definition)
        clan = clans.get(clan_code) or {}
        display_names = {
            "insider_feed": "Insider Feed",
            "service_entrance": "Wejście Serwisowe",
            "false_image": "Fałszywy Obraz",
        }
        activation_taglines = {
            "insider_feed": "MEGA HOSSA",
            "service_entrance": "BACKDOOR GOTOWY",
            "false_image": "NIE WIERZ OCZOM",
        }
        impact_ui = {
            "insider_feed": "operation_cards",
            "service_entrance": "target_action_dots",
            "false_image": "operation_risk",
        }
        ability_code = str(ability.get("ability_code") or "")
        return {
            "clan_code": clan_code,
            "clan_color_token": clan.get("ui_color_token") or "",
            "visual_asset_url": asset.get("visual_asset_url") or "",
            "timer_asset_url": timer_asset.get("visual_asset_url") or "",
            "visual_asset_max_px": asset.get("presentation_asset_max_px") or 560,
            "visual_asset_padding_px": asset.get("presentation_asset_padding_px") or 52,
            "visual_asset_motion": asset.get("presentation_asset_motion") or "shake",
            "show_duration_ms": 6000,
            "sound_event": "ghostnetwork.part_activated",
            "display_name": display_names.get(
                ability_code,
                ability.get("ability_name") or "GhostNetwork",
            ),
            "activation_tagline": activation_taglines.get(ability_code) or "MOC AKTYWNA",
            "impact_ui": impact_ui.get(ability_code) or "",
            "semantic_description": ability.get("ability_description") or "",
        }

    def get_player_ability_window_snapshot(self, player_context, now=None):
        player_context = player_context if isinstance(player_context, dict) else {}
        player_id = str(
            player_context.get("player_id") or player_context.get("username") or ""
        ).strip()
        resolved = self.resolve_player_abilities(player_context)
        eligible_ability = next(iter(resolved.get("active_abilities") or []), None)
        allowed_codes = set(GHOSTNETWORK_ABILITY_ALLOWED_CODES)
        ability = eligible_ability if (
            eligible_ability
            and eligible_ability.get("ability_code") in allowed_codes
        ) else None
        window = self.repository.get_latest_ability_window(player_id) if player_id else None
        now_dt = self.repository.now() if now is None else now
        from .repository import _utc_datetime
        current = _utc_datetime(now_dt)
        active = self._ability_window_matches(
            window, ability, current=current, require_unexpired=True,
        )
        cooldown = bool(
            window and current < _utc_datetime(window.get("cooldown_until"))
        )
        public_window = None
        if window:
            public_window = {
                key: window.get(key) for key in (
                    "window_id", "ability_code", "source_part_code",
                    "activated_at", "expires_at", "cooldown_until",
                    "level_snapshot",
                )
            }
        public_ability = None
        if ability:
            public_ability = {
                key: ability.get(key) for key in (
                    "ability_code", "ability_name", "ability_description",
                    "part_code", "part_name", "source_part_code",
                )
            }
        return {
            "ok": True,
            "available": bool(ability and not cooldown),
            "active": active,
            "cooldown": cooldown and not active,
            "ability": public_ability,
            "presentation": self._ability_presentation(ability) if ability else None,
            "window": public_window,
            "reason": (
                "realizer_unavailable" if eligible_ability and not ability
                else "cooldown" if cooldown and not active
                else "active" if active
                else "available" if ability
                else (resolved.get("ability") or {}).get("activation_reason") or "not_eligible"
            ),
        }

    @staticmethod
    def _ability_window_matches(window, ability, *, current, require_unexpired):
        """Match current eligibility and reject a window from an older part activation."""
        if (
            not window or not ability
            or window.get("ability_code") != ability.get("ability_code")
            or window.get("source_part_id") != ability.get("source_part_id")
        ):
            return False
        from .repository import _utc_datetime
        if require_unexpired and current >= _utc_datetime(window.get("expires_at")):
            return False
        part_activated_at = str(
            ability.get("source_part_last_activated_at") or ""
        ).strip()
        if (
            part_activated_at
            and _utc_datetime(part_activated_at)
            > _utc_datetime(window.get("activated_at"))
        ):
            return False
        return True

    def activate_player_ability(self, player_context, request_key, now=None):
        activation_started = perf_counter()
        player_context = player_context if isinstance(player_context, dict) else {}
        request_key = str(request_key or "").strip()
        metric_ability = None

        def finish(payload, ability=None):
            selected = ability if isinstance(ability, dict) else metric_ability or {}
            try:
                self.repository.record_ability_metric(
                    "activation",
                    str((payload or {}).get("status") or "unknown"),
                    cycle_id=str(selected.get("cycle_id") or ""),
                    ability_code=str(selected.get("ability_code") or ""),
                    value=(perf_counter() - activation_started) * 1000.0,
                )
            except Exception:
                # Telemetry is diagnostic and must never change gameplay outcome.
                pass
            return payload

        if not request_key or len(request_key) > 128:
            return finish({"ok": False, "status": "invalid_request_key"})
        player_id = str(
            player_context.get("player_id") or player_context.get("username") or ""
        ).strip()
        resolved = self.resolve_player_abilities(player_context)
        eligible_ability = next(iter(resolved.get("active_abilities") or []), None)
        metric_ability = eligible_ability
        ability = eligible_ability if (
            eligible_ability
            and eligible_ability.get("ability_code") in set(GHOSTNETWORK_ABILITY_ALLOWED_CODES)
        ) else None
        replayed = self.repository.get_ability_window_by_request(
            player_id, request_key,
        )
        if replayed:
            from .repository import _utc_datetime
            replay_current = _utc_datetime(self.repository.now() if now is None else now)
            if (
                self._ability_window_matches(
                    replayed, ability, current=replay_current,
                    require_unexpired=True,
                )
                and self.ability_production_realizer is not None
            ):
                realizer_started = perf_counter()
                internal_realizer_result = self.ability_production_realizer.apply_activation(
                    player_id, replayed,
                )
                self._record_ability_realizer_metrics(
                    replayed, internal_realizer_result, realizer_started,
                )
            return finish(
                {"ok": True, "status": "replayed", "window": replayed},
                replayed,
            )
        if not ability:
            return finish({
                "ok": False,
                "status": (
                    "realizer_unavailable" if eligible_ability
                    else "ability_unavailable"
                ),
                "reason": (
                    "ability_not_enabled_for_runtime" if eligible_ability
                    else (resolved.get("ability") or {}).get("activation_reason") or "not_eligible"
                ),
            }, eligible_ability)
        activation_target_id = ""
        if self.ability_production_realizer is not None:
            target_binding = self.ability_production_realizer.resolve_activation_target(
                player_id, ability.get("ability_code"),
            )
            activation_target_id = str(target_binding.get("target_id") or "").strip()
            if target_binding.get("required") and not activation_target_id:
                return finish({
                    "ok": False,
                    "status": "target_unavailable",
                    "reason": "select_target_before_activation",
                    "message": "Najpierw oznacz cel na mapie.",
                }, ability)
        result = self.repository.activate_ability_window(
            player_id=resolved.get("player_id"),
            ability_code=ability.get("ability_code"),
            cycle_id=ability.get("cycle_id"),
            source_part_id=ability.get("source_part_id"),
            source_part_code=ability.get("source_part_code"),
            level_snapshot=player_context.get("level") or 1,
            source_state_version=ability.get("state_version") or 0,
            request_key=request_key,
            duration_seconds=GHOSTNETWORK_ABILITY_DURATION_SECONDS,
            cooldown_seconds=GHOSTNETWORK_ABILITY_COOLDOWN_SECONDS,
            target_id=activation_target_id,
            now=now,
        )
        pilot_evidence = None
        if result.get("status") == "activated" and self.ability_pilot_harness is not None:
            pilot_evidence = self.ability_pilot_harness.apply(result.get("window") or {})
        realizer_result = None
        if result.get("status") == "activated" and self.ability_production_realizer is not None:
            realizer_started = perf_counter()
            internal_realizer_result = self.ability_production_realizer.apply_activation(
                player_id, result.get("window") or {},
            )
            self._record_ability_realizer_metrics(
                result.get("window") or {}, internal_realizer_result,
                realizer_started,
            )
            realizer_result = {
                "status": internal_realizer_result.get("status") or "",
                "applied_operations": len(internal_realizer_result.get("persisted") or []),
                "applied_targets": int(bool(internal_realizer_result.get("target_applied"))),
                "applied_changes": len(internal_realizer_result.get("changed") or []),
            }
        return finish({
            "ok": result.get("status") in {"activated", "replayed"},
            **result,
            **({"pilot_evidence": pilot_evidence} if pilot_evidence is not None else {}),
            **({"realizer": realizer_result} if realizer_result is not None else {}),
        }, ability)

    def _record_ability_realizer_metrics(self, window, result, started_at):
        window = window if isinstance(window, dict) else {}
        result = result if isinstance(result, dict) else {}
        common = {
            "cycle_id": str(window.get("cycle_id") or ""),
            "ability_code": str(window.get("ability_code") or ""),
        }
        try:
            self.repository.record_ability_metric(
                "realizer", str(result.get("status") or "unknown"),
                value=(perf_counter() - started_at) * 1000.0, **common,
            )
            retries = max(0, int(result.get("cas_retries") or 0))
            if retries:
                self.repository.record_ability_metric(
                    "realizer", "cas_retry", value=retries, **common,
                )
        except Exception:
            # Metrics remain fail-open and never expose player/operation identity.
            pass

    def apply_active_ability_to_new_operation(self, player_context, operation, now=None):
        """Apply the frozen production realizer while building one operation."""
        if self.ability_production_realizer is None or not isinstance(operation, dict):
            return False
        snapshot = self.get_player_ability_window_snapshot(player_context, now=now)
        if not snapshot.get("active"):
            return False
        return self.ability_production_realizer.apply_to_new_operation(
            operation, snapshot.get("window") or {},
        )

    def active_operation_risk_rules(self, player_context, now=None):
        """Return one bounded rules input from an active eligible window."""
        snapshot = self.get_player_ability_window_snapshot(player_context, now=now)
        ability = snapshot.get("ability") or {}
        if not snapshot.get("active") or ability.get("ability_code") != "false_image":
            return {}
        return {"ability_heat_modifier": -15}

    def apply_active_ability_to_aimed_target(self, player_context, target_id, now=None):
        """Apply an active target realizer at the canonical aimed-target call-site."""
        if self.ability_production_realizer is None:
            return {"ok": True, "status": "realizer_unavailable", "target_applied": False}
        target_id = str(target_id or "").strip()
        if not target_id:
            return {"ok": True, "status": "target_unavailable", "target_applied": False}
        snapshot = self.get_player_ability_window_snapshot(player_context, now=now)
        if not snapshot.get("active"):
            return {"ok": True, "status": "inactive", "target_applied": False}
        window = snapshot.get("window") or {}
        started_at = perf_counter()
        result = self.ability_production_realizer.apply_to_aimed_target(
            str(player_context.get("player_id") or player_context.get("username") or "").strip(),
            target_id,
            window,
        )
        self._record_ability_realizer_metrics(window, result, started_at)
        return result

    def is_ability_active(self, player_context, ability_code):
        return self.abilities.is_ability_active(player_context, ability_code)

    def collect_ability_effects(self, effect_type, context):
        return self.abilities.collect_effects(effect_type, context)

    def apply_ability_modifier(self, effect_type, context, value):
        return self.abilities.apply_modifier(effect_type, context, value)

    def record_contribution(self, **kwargs):
        return self.contributions.record_contribution(**kwargs)

    def list_player_contributions(self, player_id, cycle_id=None, limit=500):
        return self.contributions.list_player_contributions(player_id, cycle_id=cycle_id, limit=limit)

    def list_cycle_contributions(self, cycle_id, limit=1000):
        return self.contributions.list_cycle_contributions(cycle_id, limit=limit)

    def aggregate_player_contribution(self, player_id, cycle_id=None):
        return self.contributions.aggregate_player_contribution(player_id, cycle_id=cycle_id)

    def aggregate_clan_contribution(self, clan_code, cycle_id=None):
        return self.contributions.aggregate_clan_contribution(clan_code, cycle_id=cycle_id)

    def evaluate_event_reward(self, event, profile=None, context=None):
        return self.rewards.evaluate_event_reward(event, profile=profile, context=context)

    def create_reward_entry(self, reward_plan):
        return self.rewards.create_reward_entry(reward_plan)

    def apply_pending_reward(self, profile, reward_id=None, reward_key=None):
        return self.rewards.apply_pending_reward(profile, reward_id=reward_id, reward_key=reward_key)

    def project_reward_to_profile(self, profile, reward_id=None, reward_key=None):
        return self.rewards.project_reward_to_profile(
            profile,
            reward_id=reward_id,
            reward_key=reward_key,
        )

    def finalize_projected_reward(self, profile, reward_id=None, reward_key=None):
        return self.rewards.finalize_projected_reward(
            profile,
            reward_id=reward_id,
            reward_key=reward_key,
        )

    def apply_pending_rewards(self, profile, player_id=None, cycle_id=None, limit=100):
        return self.rewards.apply_pending_rewards(profile, player_id=player_id, cycle_id=cycle_id, limit=limit)

    def get_player_reward_summary(self, player_id, cycle_id=None):
        return self.rewards.get_player_reward_summary(player_id, cycle_id=cycle_id)

    def handle_reward_event(self, event, profile=None, context=None, apply=False):
        return self.rewards.handle_event(event, profile=profile, context=context, apply=apply)

    def reconcile_ghost_rewards(self, cycle_id=None, player_id=None, dry_run=True):
        return self.rewards.reconcile_ghost_rewards(cycle_id=cycle_id, player_id=player_id, dry_run=dry_run)

    def on_ghost_conflict_started(self, part, territory_snapshot=None, context=None):
        return self.conflicts.on_conflict_started(part, territory_snapshot=territory_snapshot, context=context)

    def record_ghost_conflict_progress(self, conflict_id, progress=0, source_event_id="", metadata=None):
        return self.conflicts.record_conflict_progress(
            conflict_id,
            progress=progress,
            source_event_id=source_event_id,
            metadata=metadata,
        )

    def record_ghost_offensive_action(self, conflict_id, action_type, **kwargs):
        return self.conflicts.record_offensive_action(conflict_id, action_type, **kwargs)

    def record_ghost_defensive_action(self, conflict_id, action_type, **kwargs):
        return self.conflicts.record_defensive_action(conflict_id, action_type, **kwargs)

    def evaluate_ghost_defense_reward(self, conflict_id, final_state=None):
        return self.conflicts.evaluate_defense_reward(conflict_id, final_state=final_state)

    def evaluate_ghost_recovery_reward(self, part, previous_period=None, conflict_id="", context=None):
        return self.conflicts.evaluate_recovery_reward(
            part,
            previous_period=previous_period,
            conflict_id=conflict_id,
            context=context,
        )

    def resolve_ghost_conflict_outcome(self, conflict_id, final_state=None, context=None, apply_rewards=False):
        conflict = self.repository.get_strategic_conflict(conflict_id) or {}
        cycle_id, cursor = self._event_cursor(conflict.get("cycle_id"))
        result = self.conflicts.resolve_conflict_outcome(
            conflict_id,
            final_state=final_state,
            context=context,
            apply_rewards=apply_rewards,
        )
        self._dispatch_persisted_events(
            result, cycle_id=cycle_id, after_state_version=cursor,
        )
        return result

    def reconcile_ghost_conflict_outcomes(self, conflict_id=None, dry_run=True):
        return self.conflicts.reconcile_ghost_conflict_outcomes(conflict_id=conflict_id, dry_run=dry_run)

    def resolve_machine_progress(self, cycle_id, machine_code):
        return self.modules.resolve_machine_progress(cycle_id, machine_code)

    def resolve_clan_machine_progress(self, cycle_id, clan_code):
        return self.modules.resolve_clan_machine_progress(cycle_id, clan_code)

    def get_modules_status_report(self, cycle_id=None, include_parts=False):
        return self.modules.get_modules_status_report(cycle_id=cycle_id, include_parts=include_parts)

    def build_cluster_ghost_component_contract(self, cycle_id, territory_id, viewer=None):
        return self.modules.build_cluster_ghost_component_contract(cycle_id, territory_id, viewer=viewer)

    def attempt_transmission(self, *args, **kwargs):
        return {"ok": False, "status": "not_implemented", "hook": "attempt_transmission"}
