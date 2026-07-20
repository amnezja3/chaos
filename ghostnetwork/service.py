from __future__ import annotations

from database import DB_PATH

from .catalog import (
    get_catalog_diagnostics,
    get_onboarding_catalog,
    normalize_ghostnetwork_profile_identity,
    validate_catalog,
)
from .abilities import GhostAbilityRegistry
from .archive import GhostArchiveService
from .closure import GhostNetworkClosureService
from .cycles import GhostCycleService, ensure_active_ghostnetwork_cycle
from .conflicts import GhostDefenseRewardPolicy, GhostStrategicConflictService
from .lifecycle import GhostPartLifecycleService
from .module_state import GhostModuleStateService
from .narrative import GhostNarrativePublisher
from .repository import GhostNetworkRepository
from .rewards import GhostContributionService, GhostRewardService
from .reservations import GhostDropPolicy, GhostReservationService, is_ghostnetwork_eligible_target
from .territory import GhostTerritoryAdapter
from .topology import GhostTopologyService
from .transmission import GhostTransmissionService
from .visibility import build_viewer_projection


class GhostNetworkService:
    """Central GhostNetwork entry point for future integrations."""

    def __init__(self, repository=None, db_path=DB_PATH, drop_policy=None):
        self.repository = repository or GhostNetworkRepository(db_path=db_path)
        self.cycles = GhostCycleService(repository=self.repository)
        self.topology = GhostTopologyService(repository=self.repository)
        self.lifecycle = GhostPartLifecycleService(repository=self.repository)
        self.territory = GhostTerritoryAdapter(repository=self.repository, lifecycle=self.lifecycle)
        self.modules = GhostModuleStateService(repository=self.repository)
        self.abilities = GhostAbilityRegistry(repository=self.repository, module_state_service=self.modules)
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

    def get_catalog_diagnostics(self):
        return get_catalog_diagnostics()

    def ensure_active_cycle(self):
        return self.cycles.ensure_active_cycle()

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
        return self.closure.attempt_cycle_lock(cycle_id, trigger_event_id=trigger_event_id)

    def build_lock_snapshot(self, cycle_id, trigger_event_id=""):
        return self.closure.build_lock_snapshot(cycle_id, trigger_event_id=trigger_event_id)

    def get_locked_cycle_snapshot(self, cycle_id):
        return self.closure.get_locked_cycle_snapshot(cycle_id)

    def validate_locked_snapshot(self, cycle_id):
        return self.closure.validate_locked_snapshot(cycle_id)

    def start_transmission(self, cycle_id):
        result = self.transmission.start_transmission(cycle_id)
        return self._with_transmission_narrative(result)

    def resume_interrupted_transmission(self, cycle_id):
        result = self.transmission.resume_interrupted_transmission(cycle_id)
        return self._with_transmission_narrative(result)

    def validate_transmission(self, cycle_id):
        return self.transmission.validate_transmission(cycle_id)

    def _with_transmission_narrative(self, result):
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
        return result

    def publish_narrative_event(self, event):
        return self.narrative.publish_domain_event(event)

    def retry_failed_narrative_publications(self, limit=100):
        return self.narrative.retry_failed_publications(limit=limit)

    def list_narrative_outbox(self, **filters):
        return self.repository.list_narrative_outbox(**filters)

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
        return self.reservations.on_target_aimed(player, target, context=context)

    def attach_reservation_to_operation(self, player_id, target_id, operation_id):
        return self.reservations.attach_reservation_to_operation(player_id, target_id, operation_id)

    def release_reservation(self, reservation_id, reason):
        return self.reservations.release_reservation(reservation_id, reason)

    def expire_due_reservations(self, now=None):
        return self.reservations.expire_due_reservations(now=now)

    def get_reservation_status(self):
        return self.reservations.get_reservation_status()

    def on_territory_stabilized(self, event):
        return self._with_module_progress(self.territory.on_territory_stabilized(event))

    def on_territory_contested(self, event):
        return self._with_module_progress(self.territory.on_territory_contested(event))

    def on_territory_released(self, event):
        return self._with_module_progress(self.territory.on_territory_released(event))

    def on_territory_owner_changed(self, event):
        return self._with_module_progress(self.territory.on_territory_owner_changed(event))

    def reconcile_parts_with_territories(self, cycle_id=None, territories=None, apply=False):
        report = self.territory.reconcile_parts_with_territories(cycle_id=cycle_id, territories=territories, apply=apply)
        if apply:
            return self._with_module_progress(report, changed_key="changes")
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
        return self.conflicts.resolve_conflict_outcome(
            conflict_id,
            final_state=final_state,
            context=context,
            apply_rewards=apply_rewards,
        )

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
