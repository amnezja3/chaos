from __future__ import annotations

import copy
import hashlib

from database import dumps_json

from .catalog import CATALOG_VERSION, get_catalog_checksum
from .errors import RepositoryIntegrityError
from .module_state import GhostModuleStateService
from .repository import GhostNetworkRepository, _clean
from .topology import GhostTopologyService


UNRESOLVED_CONFLICT_STATUSES = {"active", "contested", "escalating", "pending"}
CLOSING_EVENT_TYPES = {
    "ghost.part_activated",
    "ghost.part_conflict_resolved",
    "ghost.part_recovered",
}


def _canonical_checksum(payload):
    encoded = dumps_json(payload)
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _snapshot_checksum(snapshot):
    clean = copy.deepcopy(snapshot if isinstance(snapshot, dict) else {})
    clean.pop("snapshot_checksum", None)
    return _canonical_checksum(clean)


class GhostNetworkClosureService:
    """Validate and atomically lock a complete GhostNetwork cycle.

    Sprint 127 deliberately stops at the immutable lock snapshot. Transmission,
    GhostSignal creation and GhostSystem version changes belong to later sprints.
    """

    def __init__(self, repository=None, topology_service=None, module_state_service=None):
        self.repository = repository or GhostNetworkRepository()
        self.topology = topology_service or GhostTopologyService(repository=self.repository)
        self.modules = module_state_service or GhostModuleStateService(repository=self.repository)

    def evaluate_network_readiness(self, cycle_id):
        cycle_id = _clean(cycle_id)
        cycle = self.repository.get_cycle(cycle_id)
        if not cycle:
            return {"ok": False, "ready": False, "cycle_id": cycle_id, "reasons": ["cycle_not_found"]}

        parts = self.repository.list_parts(cycle_id)
        parts_by_id = {part["part_id"]: part for part in parts}
        connections = self.repository.list_connections(cycle_id)
        module_state = self.modules.resolve_cycle_module_states(cycle_id)
        module_by_id = {item["part_id"]: item for item in module_state.get("parts", [])}
        topology = self.topology.validate_topology(cycle_id)
        lock_snapshots = self.repository.list_cycle_lock_snapshots(cycle_id)
        signals = self.repository.list_signals_for_cycle(cycle_id, limit=1000)
        conflicts = self.repository.list_strategic_conflicts(cycle_id=cycle_id, limit=1000)
        unresolved_conflicts = [
            conflict
            for conflict in conflicts
            if _clean(conflict.get("status")).lower() in UNRESOLVED_CONFLICT_STATUSES
        ]

        reasons = []
        if cycle.get("status") != "active":
            reasons.append("cycle_not_active")
        if len(parts) != 20:
            reasons.append("parts_count_not_20")
        if len(connections) != 20:
            reasons.append("connections_count_not_20")
        if lock_snapshots:
            reasons.append("lock_snapshot_already_exists")
        if signals:
            reasons.append("ghost_signal_already_exists")
        if unresolved_conflicts:
            reasons.append("unresolved_strategic_conflict")

        active_part_ids = set()
        for part in parts:
            part_id = part["part_id"]
            part_code = part["part_code"]
            state = module_by_id.get(part_id, {})
            if not self._part_is_discovered(part):
                reasons.append(f"part_not_discovered:{part_code}")
            if state.get("module_state") != "active":
                reasons.append(f"part_not_active:{part_code}")
            else:
                active_part_ids.add(part_id)
            if not part.get("territory_id") or not part.get("territory_owner_id"):
                reasons.append(f"part_missing_territory:{part_code}")
            if part.get("territory_clan") != part.get("clan_code"):
                reasons.append(f"part_wrong_territory_clan:{part_code}")
            if int(part.get("territory_state_version") or 0) <= 0:
                reasons.append(f"part_missing_territory_version:{part_code}")
            if _clean(part.get("conflict_state"), "none") not in {"none", "resolved"}:
                reasons.append(f"part_conflict_active:{part_code}")
            if not self._part_has_valid_anchor(part):
                reasons.append(f"part_invalid_anchor:{part_code}")

        for connection in connections:
            if connection.get("part_a_id") not in active_part_ids or connection.get("part_b_id") not in active_part_ids:
                reasons.append(f"connection_endpoint_not_active:{connection.get('connection_id')}")

        machine_errors = []
        for machine in module_state.get("machines", []):
            if int(machine.get("parts_total") or 0) != 5:
                machine_errors.append(f"{machine.get('machine_code')}:parts_total")
            if int(machine.get("parts_active") or 0) != 5:
                machine_errors.append(f"{machine.get('machine_code')}:parts_active")
            if not machine.get("machine_online"):
                machine_errors.append(f"{machine.get('machine_code')}:offline")
        if machine_errors:
            reasons.append("machine_progress_incomplete")

        if not topology.get("valid"):
            reasons.append("topology_invalid")
        if not topology.get("checksum_match"):
            reasons.append("topology_checksum_mismatch")

        unique_reasons = []
        for reason in reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)

        return {
            "ok": True,
            "ready": not unique_reasons,
            "cycle_id": cycle_id,
            "reasons": unique_reasons,
            "counts": {
                "parts": len(parts),
                "connections": len(connections),
                "lock_snapshots": len(lock_snapshots),
                "ghost_signals": len(signals),
                "unresolved_conflicts": len(unresolved_conflicts),
            },
            "cycle": cycle,
            "parts": parts,
            "connections": connections,
            "machines": module_state.get("machines", []),
            "cycle_progress": module_state.get("cycle_progress", {}),
            "topology": topology,
            "unresolved_conflicts": unresolved_conflicts,
        }

    def attempt_cycle_lock(self, cycle_id, trigger_event_id=""):
        cycle_id = _clean(cycle_id)
        trigger_event_id = _clean(trigger_event_id)
        with self.repository.transaction():
            existing = self.repository.get_cycle_lock_snapshot(cycle_id)
            cycle = self.repository.get_cycle(cycle_id)
            if existing and cycle and cycle.get("status") == "transmitting":
                return {
                    "ok": True,
                    "locked": True,
                    "idempotent": True,
                    "status": "already_locked",
                    "snapshot": existing,
                    "validation": self.validate_locked_snapshot(cycle_id),
                }

            readiness = self.evaluate_network_readiness(cycle_id)
            if not readiness.get("ready"):
                return {
                    "ok": readiness.get("ok", False),
                    "locked": False,
                    "status": "not_ready",
                    "readiness": readiness,
                }

            locked_at = self.repository.now()
            next_state_version = int(readiness["cycle"].get("state_version") or 0) + 1
            lock_payload = self.build_lock_snapshot(
                cycle_id,
                trigger_event_id=trigger_event_id,
                locked_at=locked_at,
                state_version=next_state_version,
            )
            snapshot = lock_payload["snapshot"]
            closing = snapshot["closing"]

            updated_cycle = self.repository.update_cycle(
                cycle_id,
                status="transmitting",
                locked_at=locked_at,
                lock_event_id=trigger_event_id,
                closing_part_id=closing.get("closing_part_id", ""),
            )
            snapshot["cycle"] = copy.deepcopy(updated_cycle)
            snapshot["state_version"] = int(updated_cycle.get("state_version") or next_state_version)
            snapshot["snapshot_checksum"] = _snapshot_checksum(snapshot)

            lock_snapshot = self.repository.create_cycle_lock_snapshot(
                {
                    "lock_snapshot_id": f"lock_{cycle_id}_{snapshot['snapshot_checksum'][:16]}",
                    "cycle_id": cycle_id,
                    "signal_number": updated_cycle.get("signal_number"),
                    "ghostsystem_version": updated_cycle.get("ghostsystem_version"),
                    "state_version": snapshot["state_version"],
                    "locked_at": locked_at,
                    "lock_event_id": trigger_event_id,
                    "closing_part_id": closing.get("closing_part_id", ""),
                    "snapshot": snapshot,
                    "snapshot_checksum": snapshot["snapshot_checksum"],
                    "created_at": locked_at,
                }
            )
            try:
                event = self.repository.append_event(
                    "ghost.cycle_locked",
                    cycle_id=cycle_id,
                    part_id=closing.get("closing_part_id", ""),
                    entity_id=cycle_id,
                    player_id=closing.get("closing_player_id", ""),
                    clan_code=closing.get("closing_clan_code", ""),
                    territory_id=closing.get("closing_territory_id", ""),
                    state_version=snapshot["state_version"],
                    dedupe_key=f"ghost:cycle_locked:{cycle_id}:{snapshot['snapshot_checksum']}",
                    payload={
                        "lock_snapshot_id": lock_snapshot["lock_snapshot_id"],
                        "snapshot_checksum": snapshot["snapshot_checksum"],
                        "closing": closing,
                    },
                )
            except RepositoryIntegrityError:
                event = None

            return {
                "ok": True,
                "locked": True,
                "status": "locked",
                "cycle": updated_cycle,
                "snapshot": lock_snapshot,
                "lock_event": event,
                "readiness": readiness,
            }

    def build_lock_snapshot(self, cycle_id, trigger_event_id="", locked_at=None, state_version=None):
        cycle_id = _clean(cycle_id)
        readiness = self.evaluate_network_readiness(cycle_id)
        cycle = readiness.get("cycle") or self.repository.get_cycle(cycle_id)
        parts = readiness.get("parts") or self.repository.list_parts(cycle_id)
        connections = readiness.get("connections") or self.repository.list_connections(cycle_id)
        topology = readiness.get("topology") or self.topology.validate_topology(cycle_id)
        modules = self.modules.resolve_cycle_module_states(cycle_id)
        events = self.repository.list_events(cycle_id=cycle_id, limit=1000)
        closing = self._resolve_closing_metadata(parts, events, trigger_event_id)
        locked_at = _clean(locked_at or self.repository.now())
        state_version = int(state_version if state_version is not None else (cycle or {}).get("state_version") or 0)

        part_snapshots = []
        for part in sorted(parts, key=lambda item: item.get("part_code", "")):
            part_snapshots.append(
                {
                    "part_id": part["part_id"],
                    "part_code": part["part_code"],
                    "clan_code": part["clan_code"],
                    "machine_code": part["machine_code"],
                    "profession_code": part["profession_code"],
                    "status": part["status"],
                    "target_id": part.get("target_id", ""),
                    "anchor": {
                        "latitude": part.get("latitude"),
                        "longitude": part.get("longitude"),
                        "snapshot": copy.deepcopy(part.get("anchor_snapshot") or {}),
                    },
                    "discovered_by": part.get("discovered_by", ""),
                    "discovered_clan": part.get("discovered_clan", ""),
                    "discovered_at": part.get("discovered_at", ""),
                    "territory_id": part.get("territory_id", ""),
                    "territory_owner_id": part.get("territory_owner_id", ""),
                    "territory_clan": part.get("territory_clan", ""),
                    "territory_state_version": int(part.get("territory_state_version") or 0),
                    "activated_at": part.get("activated_at", ""),
                    "last_activated_at": part.get("last_activated_at", ""),
                    "hold_time": self.repository.list_control_periods(part["part_id"], cycle_id=cycle_id, limit=25),
                    "conflict_state": part.get("conflict_state", "none"),
                    "conflict_id": part.get("conflict_id", ""),
                }
            )

        snapshot = {
            "schema": 1,
            "snapshot_kind": "ghost_cycle_lock",
            "cycle_id": cycle_id,
            "signal_number": int((cycle or {}).get("signal_number") or 0),
            "ghostsystem_version": int((cycle or {}).get("ghostsystem_version") or 0),
            "catalog": {
                "version": (cycle or {}).get("catalog_version") or CATALOG_VERSION,
                "checksum": (cycle or {}).get("catalog_checksum") or get_catalog_checksum(),
            },
            "cycle": copy.deepcopy(cycle),
            "topology": {
                "checksum": topology.get("topology_checksum", ""),
                "checksum_match": bool(topology.get("checksum_match")),
                "ring_order": list(topology.get("ring_order") or []),
                "ring_codes": list(topology.get("ring_codes") or []),
                "connections": [dict(connection, status="active") for connection in connections],
            },
            "parts": part_snapshots,
            "machine_progress": modules.get("machines", []),
            "cycle_progress": modules.get("cycle_progress", {}),
            "operator_contributions": self.repository.list_cycle_contributions(cycle_id, limit=5000),
            "clan_reputation": self.repository.list_clan_reputation(limit=100),
            "conflicts": self.repository.list_strategic_conflicts(cycle_id=cycle_id, limit=1000),
            "transfers": self.repository.list_transfer_history(cycle_id=cycle_id, limit=1000),
            "closing": dict(closing, closed_at=locked_at, closing_event_id=_clean(trigger_event_id) or closing.get("closing_event_id", "")),
            "state_version": state_version,
            "locked_at": locked_at,
        }
        snapshot["snapshot_checksum"] = _snapshot_checksum(snapshot)
        return {
            "ok": True,
            "cycle_id": cycle_id,
            "snapshot_checksum": snapshot["snapshot_checksum"],
            "snapshot": snapshot,
        }

    def get_locked_cycle_snapshot(self, cycle_id):
        return self.repository.get_cycle_lock_snapshot(cycle_id)

    def validate_locked_snapshot(self, cycle_id):
        cycle_id = _clean(cycle_id)
        cycle = self.repository.get_cycle(cycle_id)
        snapshots = self.repository.list_cycle_lock_snapshots(cycle_id)
        reasons = []
        if cycle and cycle.get("status") == "transmitting" and not snapshots:
            reasons.append("transmitting_snapshot_missing")
        if len(snapshots) > 1:
            reasons.append("multiple_lock_snapshots")
        snapshot = snapshots[0] if snapshots else None
        if snapshot:
            payload = copy.deepcopy(snapshot.get("snapshot") or {})
            expected = _snapshot_checksum(payload)
            if expected != snapshot.get("snapshot_checksum"):
                reasons.append("snapshot_checksum_mismatch")
            if payload.get("snapshot_checksum") != snapshot.get("snapshot_checksum"):
                reasons.append("payload_checksum_mismatch")
        return {
            "ok": not reasons,
            "valid": not reasons,
            "cycle_id": cycle_id,
            "cycle_status": (cycle or {}).get("status", ""),
            "snapshot_count": len(snapshots),
            "reasons": reasons,
            "snapshot": snapshot,
        }

    @staticmethod
    def _part_is_discovered(part):
        return bool(
            part.get("target_id")
            and (part.get("discovered_by") or part.get("discovered_at") or part.get("activated_at"))
        )

    @staticmethod
    def _part_has_valid_anchor(part):
        if not part.get("target_id"):
            return False
        if part.get("latitude") is None or part.get("longitude") is None:
            return False
        anchor = part.get("anchor_snapshot")
        return isinstance(anchor, dict) and bool(anchor)

    @staticmethod
    def _resolve_closing_metadata(parts, events, trigger_event_id=""):
        trigger_event_id = _clean(trigger_event_id)
        event = None
        if trigger_event_id:
            for candidate in events:
                if candidate.get("event_id") == trigger_event_id:
                    event = candidate
                    break
        if not event:
            for candidate in reversed(events or []):
                if candidate.get("event_type") in CLOSING_EVENT_TYPES:
                    event = candidate
                    break
        parts_by_id = {part.get("part_id"): part for part in parts}
        part = None
        if event:
            part = parts_by_id.get(event.get("part_id") or event.get("entity_id"))
        if not part:
            active_parts = sorted(
                [item for item in parts if item.get("activated_at") or item.get("last_activated_at")],
                key=lambda item: item.get("last_activated_at") or item.get("activated_at") or "",
            )
            part = active_parts[-1] if active_parts else (parts[-1] if parts else {})
        event_payload = (event or {}).get("payload") if isinstance((event or {}).get("payload"), dict) else {}
        return {
            "closing_part_id": _clean((part or {}).get("part_id")),
            "closing_part_code": _clean((part or {}).get("part_code")),
            "closing_player_id": _clean((event or {}).get("player_id") or event_payload.get("player_id") or (part or {}).get("discovered_by")),
            "closing_clan_code": _clean((event or {}).get("clan_code") or (part or {}).get("clan_code")),
            "closing_territory_id": _clean((event or {}).get("territory_id") or (part or {}).get("territory_id")),
            "closing_event_id": _clean((event or {}).get("event_id")),
        }
