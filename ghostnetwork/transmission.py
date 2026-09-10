from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone

from database import dumps_json
from config import GHOSTNETWORK_ENDGAME_REWARD_POLICY, GHOSTNETWORK_SIGNAL_SHOW_POLICY

from .closure import GhostNetworkClosureService
from .errors import InvalidStateTransition, RepositoryIntegrityError
from .lifecycle import GhostPartLifecycleService
from .repository import GhostNetworkRepository, _clean
from .show import GhostSignalShowService


def _parse_iso(value):
    text = _clean(value)
    if not text:
        return None
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def signal_payload_checksum(payload):
    """Return the canonical checksum stored with a GhostSignal payload."""
    return hashlib.sha1(dumps_json(payload).encode("utf-8")).hexdigest()


def _version_text(value):
    number = int(value or 0)
    return f"1.0.{number}"


class GhostTransmissionService:
    """Finalize a locked GhostNetwork cycle into a durable GhostSignal.

    Sprint 128 deliberately uses the immutable lock snapshot from Sprint 127.
    It does not re-read mutable territory ownership to decide rewards, topology
    or the transmitted payload.
    """

    def __init__(self, repository=None, lifecycle_service=None, closure_service=None, show_service=None):
        self.repository = repository or GhostNetworkRepository()
        self.lifecycle = lifecycle_service or GhostPartLifecycleService(self.repository)
        self.closure = closure_service or GhostNetworkClosureService(repository=self.repository)
        self.show = show_service or GhostSignalShowService(repository=self.repository)

    def start_transmission(self, cycle_id):
        return self._transmit(cycle_id)

    def _completed_result(self, cycle_id, signal):
        # Preserve the existing result contract using receipts, never reapply
        # effects (a late retry can arrive even after rollover).
        signal_id = signal["signal_id"]
        cycle = self.repository.get_cycle(cycle_id)
        show = self.repository.get_signal_show_for_cycle(cycle_id)
        territories = self.repository.list_signal_territory_consumptions(signal_id, limit=5000)
        rewards = self.repository.list_rewards(signal_id=signal_id, limit=5000)
        parts = self.repository.list_parts(cycle_id)
        nodes = self.repository.list_historical_nodes_for_signal(signal_id)
        plan = (signal.get("payload") or {}).get("territory_consumption_plan") or {}
        return {
            "ok": True, "status": "resumed", "idempotent": True,
            "cycle_id": cycle_id, "signal": signal,
            "territories": {"count": len(territories), "territories": territories,
                            "enabled": bool(plan.get("execution_required")),
                            "plan_counts": copy.deepcopy(plan.get("counts") or {}),
                            "event": self.repository.get_event_by_dedupe_key(
                                f"ghost:territories_consumed:{signal_id}")},
            "rewards": {"count": len(rewards), "rewards": rewards},
            "consumed": {"count": len(parts), "parts": parts},
            "history": {"count": len(nodes), "nodes": nodes},
            "connections": {"cycle_id": cycle_id, "removed": 0},
            "abilities": {"disabled": True, "event": self.repository.get_event_by_dedupe_key(
                f"ghost:abilities_disabled:{signal_id}")},
            "version": {"cycle": cycle, "source_version": cycle.get("source_version"),
                        "next_version": cycle.get("next_version")},
            "stabilization": {"cycle": cycle, "show": show,
                              "event": self.repository.get_event_by_dedupe_key(
                                  f"ghost:stabilization_started:{signal_id}"),
                              "show_event": self.repository.get_event_by_dedupe_key(
                                  f"ghost:signal_show_started:{signal_id}"),
                              "stabilization_until": cycle.get("stabilization_until")},
        }

    def _transmit(self, cycle_id, resume=False):
        cycle_id = _clean(cycle_id)
        # A nested transaction would hide the show until the caller commits.
        # All production entry points own their transaction boundaries here.
        if self.repository.in_transaction:
            raise InvalidStateTransition("Transmission requires its own commit boundary.")
        validation = self.validate_transmission(cycle_id)
        signal = validation.get("existing_signal")
        cycle = validation.get("cycle") or {}
        if signal and cycle.get("status") in {"stabilizing", "closed"}:
            return self._completed_result(cycle_id, signal)
        if not validation.get("ok"):
            return {"ok": False, "status": "blocked", "cycle_id": cycle_id,
                    "reasons": validation.get("reasons") or [], "validation": validation}
        lock = validation["lock_snapshot"]
        # Snapshot copying/checksum work happens before acquiring the writer.
        prepared = self._build_signal_from_lock(lock) if not signal else None
        serialized = dumps_json(prepared["payload"]) if prepared else None
        with self.repository.transaction():
            current = self.repository.get_cycle(cycle_id) or {}
            existing = self.repository.get_signal_for_cycle(cycle_id)
            if existing and current.get("status") in {"stabilizing", "closed"}:
                return self._completed_result(cycle_id, existing)
            current_lock = self.repository.get_cycle_lock_snapshot(cycle_id) or {}
            if (current.get("status") != "transmitting"
                    or current_lock.get("snapshot_checksum") != lock.get("snapshot_checksum")
                    or current_lock.get("lock_snapshot_id") != lock.get("lock_snapshot_id")
                    or (not existing and current.get("state_version") != cycle.get("state_version"))):
                return {"ok": False, "status": "blocked", "cycle_id": cycle_id,
                        "reasons": ["transmission_state_changed"]}
            signal = existing or self._persist_signal(prepared, serialized_payload=serialized)
            if signal.get("lock_snapshot_id") != lock.get("lock_snapshot_id"):
                raise RepositoryIntegrityError("Transmission signal/lock lineage mismatch.")
            self._ensure_transmission_show(signal, current, lock)
        # The show and its start events are now visible to independent readers.
        # Existing ledgers own recovery; no parallel job/state store is needed.
        results = {}
        steps = (
            ("territories", lambda: self.consume_signal_territories(signal["signal_id"])),
            ("rewards", lambda: self.apply_transmission_rewards(signal["signal_id"])),
            ("consumed", lambda: self.consume_cycle_parts(signal["signal_id"])),
            ("history", lambda: self.archive_historical_nodes(signal["signal_id"])),
            ("connections", lambda: self.repository.remove_connections_for_cycle(
                cycle_id, signal_id=signal["signal_id"])),
            ("abilities", lambda: self.disable_superpowers(signal["signal_id"])),
            ("version", lambda: self.advance_ghostsystem_version(signal["signal_id"])),
        )
        for name, apply in steps:
            with self.repository.transaction():
                current = self.repository.get_cycle(cycle_id) or {}
                if current.get("status") in {"stabilizing", "closed"}:
                    return self._completed_result(cycle_id, self._require_signal(signal["signal_id"]))
                if current.get("status") != "transmitting":
                    raise InvalidStateTransition("Transmission cycle changed during recovery.")
                results[name] = apply()
        with self.repository.transaction():
            current = self.repository.get_cycle(cycle_id) or {}
            if current.get("status") in {"stabilizing", "closed"}:
                return self._completed_result(cycle_id, self._require_signal(signal["signal_id"]))
            if current.get("status") != "transmitting":
                raise InvalidStateTransition("Transmission cycle changed before completion.")
            signal = self.repository.mark_signal_sent(signal["signal_id"])
            self._append_once(
                "ghost.signal_sent",
                cycle_id=cycle_id,
                entity_id=signal["signal_id"],
                dedupe_key=f"ghost:signal_sent:{cycle_id}",
                audience_scope="public",
                payload={
                    "signal_id": signal["signal_id"],
                    "signal_number": signal["signal_number"],
                    "lock_snapshot_id": signal.get("lock_snapshot_id"),
                    "signal_checksum": signal.get("signal_checksum"),
                },
            )
            stabilization = self.begin_stabilization(signal["signal_id"])
            return {
                "ok": True,
                "status": "resumed" if resume or existing else "sent",
                "idempotent": bool(resume or existing),
                "cycle_id": cycle_id,
                "signal": self.repository.get_signal(signal["signal_id"]),
                **results,
                "stabilization": stabilization,
            }

    def create_signal_from_lock(self, lock_snapshot):
        prepared = self._build_signal_from_lock(lock_snapshot)
        serialized = dumps_json(prepared["payload"])
        with self.repository.transaction():
            return self._persist_signal(prepared, serialized_payload=serialized)

    def _build_signal_from_lock(self, lock_snapshot):
        lock_snapshot = lock_snapshot if isinstance(lock_snapshot, dict) else {}
        snapshot = copy.deepcopy(lock_snapshot.get("snapshot") or {})
        cycle_id = _clean(lock_snapshot.get("cycle_id") or snapshot.get("cycle_id"))
        existing = self.repository.get_signal_for_cycle(cycle_id)
        if existing:
            existing["idempotent"] = True
            return existing
        cycle = self.repository.get_cycle(cycle_id)
        if not cycle:
            raise InvalidStateTransition("Cannot create GhostSignal without cycle.")
        next_version = int(cycle.get("ghostsystem_version") or 0) + 1
        payload = {
            "schema": 1,
            "kind": "ghost_signal",
            "cycle_id": cycle_id,
            "signal_number": int(cycle.get("signal_number") or lock_snapshot.get("signal_number") or 0),
            "source_version": int(cycle.get("ghostsystem_version") or lock_snapshot.get("ghostsystem_version") or 0),
            "target_year": 2108,
            "next_version": next_version,
            "lock_snapshot_id": lock_snapshot.get("lock_snapshot_id"),
            "lock_snapshot_checksum": lock_snapshot.get("snapshot_checksum"),
            "parts": snapshot.get("parts") or [],
            "topology": snapshot.get("topology") or {},
            "machine_progress": copy.deepcopy(snapshot.get("machine_progress") or []),
            # Public compatibility alias. ``machine_progress`` remains the
            # only canonical source in the immutable lock and signal payload.
            "machines": copy.deepcopy(snapshot.get("machine_progress") or []),
            "closing": snapshot.get("closing") or {},
            "territory_consumption_plan": copy.deepcopy(
                snapshot.get("territory_consumption_plan") or {}
            ),
            "reward_plan": copy.deepcopy(snapshot.get("reward_plan") or {}),
        }
        return {
                "signal_id": f"ghost_signal_{cycle_id}",
                "signal_number": int(payload["signal_number"]),
                "cycle_id": cycle_id,
                "source_version": int(payload["source_version"]),
                "target_year": 2108,
                "status": "transmitting",
                "outcome": "pending",
                "integrity": 0,
                "recipient": "",
                "sent_at": "",
                "resolved_at": "",
                "next_version": next_version,
                "lock_snapshot_id": lock_snapshot.get("lock_snapshot_id"),
                "signal_checksum": signal_payload_checksum(payload),
                "payload": payload,
            }

    def _persist_signal(self, prepared, *, serialized_payload=None):
        signal = self.repository.create_signal(prepared, serialized_payload=serialized_payload)
        cycle_id = signal["cycle_id"]
        self._append_once(
            "ghost.signal_created",
            cycle_id=cycle_id,
            entity_id=signal["signal_id"],
            dedupe_key=f"ghost:signal_created:{cycle_id}",
            payload={
                "signal_id": signal["signal_id"],
                "signal_number": signal["signal_number"],
                "lock_snapshot_id": signal.get("lock_snapshot_id"),
                "signal_checksum": signal.get("signal_checksum"),
            },
        )
        return signal

    def apply_transmission_rewards(self, signal_id):
        signal = self._require_signal(signal_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(signal["cycle_id"])
        snapshot = (lock_snapshot or {}).get("snapshot") or {}
        closing = snapshot.get("closing") or {}
        planned = (snapshot.get("reward_plan") or {}).get("entries") or []
        territory_required = bool(
            (snapshot.get("territory_consumption_plan") or {}).get("execution_required")
        )
        rewards = []
        if planned:
            for item in planned:
                reward_type = _clean(item.get("reward_type"))
                if reward_type == "ghost_signal_territory_consumed" and not territory_required:
                    continue
                player_id = _clean(item.get("subject_id"))
                reference_id = _clean(item.get("reference_id"))
                if not player_id or not reference_id:
                    continue
                if reward_type == "ghost_signal_node_holder":
                    reward_key = f"ghost-signal:{signal_id}:node:{reference_id}:{player_id}"
                elif reward_type == "ghost_signal_closer":
                    reward_key = f"ghost-signal:{signal_id}:closer:{player_id}"
                else:
                    reward_key = (
                        f"ghost-signal:{signal_id}:{reward_type}:{player_id}:{reference_id}"
                    )
                rewards.append(self.repository.insert_reward({
                    "reward_key": reward_key,
                    "cycle_id": signal["cycle_id"],
                    "signal_id": signal_id,
                    "player_id": player_id,
                    "clan_code": item.get("clan_code"),
                    "reward_type": reward_type,
                    "base_rsp": int(item.get("base_rsp") or 0),
                    "multiplier": float(item.get("multiplier") or 1.0),
                    "final_rsp": int(item.get("final_rsp") or 0),
                    "source_event_id": lock_snapshot.get("lock_event_id"),
                    "metadata": copy.deepcopy(item.get("metadata") or {}),
                }))
            self._append_once(
                "ghost.final_rewards_created",
                cycle_id=signal["cycle_id"],
                entity_id=signal_id,
                dedupe_key=f"ghost:final_rewards:{signal_id}",
                payload={"signal_id": signal_id, "count": len(rewards)},
            )
            return {"count": len(rewards), "rewards": rewards}

        node_rsp = max(0, int(GHOSTNETWORK_ENDGAME_REWARD_POLICY.get("node_holder_rsp") or 0))
        closer_rsp = max(0, int(GHOSTNETWORK_ENDGAME_REWARD_POLICY.get("closer_rsp") or 0))
        for part in snapshot.get("parts") or []:
            owner_id = _clean(part.get("territory_owner_id") or part.get("discovered_by"))
            if not owner_id:
                continue
            rewards.append(
                self.repository.insert_reward(
                    {
                        "reward_key": f"ghost-signal:{signal_id}:node:{part.get('part_id')}:{owner_id}",
                        "cycle_id": signal["cycle_id"],
                        "signal_id": signal_id,
                        "player_id": owner_id,
                        "clan_code": part.get("territory_clan") or part.get("clan_code"),
                        "reward_type": "ghost_signal_node_holder",
                        "base_rsp": node_rsp,
                        "multiplier": 1.0,
                        "final_rsp": node_rsp,
                        "source_event_id": lock_snapshot.get("lock_event_id"),
                        "metadata": {
                            "part_id": part.get("part_id"),
                            "part_code": part.get("part_code"),
                            "held_until_signal": True,
                        },
                    }
                )
            )

        closer_id = _clean(closing.get("closing_player_id"))
        if closer_id:
            rewards.append(
                self.repository.insert_reward(
                    {
                        "reward_key": f"ghost-signal:{signal_id}:closer:{closer_id}",
                        "cycle_id": signal["cycle_id"],
                        "signal_id": signal_id,
                        "player_id": closer_id,
                        "clan_code": closing.get("closing_clan_code"),
                        "reward_type": "ghost_signal_closer",
                        "base_rsp": closer_rsp,
                        "multiplier": 1.0,
                        "final_rsp": closer_rsp,
                        "source_event_id": lock_snapshot.get("lock_event_id"),
                        "metadata": {
                            "closing_part_id": closing.get("closing_part_id"),
                            "prestige_bonus": True,
                        },
                    }
                )
            )

        self._append_once(
            "ghost.final_rewards_created",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:final_rewards:{signal_id}",
            payload={"signal_id": signal_id, "count": len(rewards)},
        )
        return {"count": len(rewards), "rewards": rewards}

    def consume_signal_territories(self, signal_id):
        signal = self._require_signal(signal_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(signal["cycle_id"]) or {}
        snapshot = lock_snapshot.get("snapshot") or {}
        plan = snapshot.get("territory_consumption_plan") or {}
        if not plan.get("execution_required"):
            return {
                "enabled": False,
                "count": 0,
                "territories": [],
                "plan_counts": copy.deepcopy(plan.get("counts") or {}),
            }
        consumed = self.repository.consume_signal_territories(
            signal_id,
            signal["cycle_id"],
            plan,
        )
        event = self._append_once(
            "ghost.territories_consumed",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:territories_consumed:{signal_id}",
            payload={
                "signal_id": signal_id,
                "count": len(consumed),
                "territory_ids": [item.get("territory_id") for item in consumed],
            },
        )
        return {
            "enabled": True,
            "count": len(consumed),
            "territories": consumed,
            "event": event,
            "plan_counts": copy.deepcopy(plan.get("counts") or {}),
        }

    def consume_cycle_parts(self, signal_id):
        signal = self._require_signal(signal_id)
        consumed = []
        for part in self.repository.list_parts(signal["cycle_id"]):
            if part.get("status") == "consumed" and part.get("consumed_signal_id") == signal_id:
                consumed.append(part)
                continue
            consumed.append(
                self.lifecycle.consume_part(
                    part["part_id"],
                    signal_id,
                    reason="ghostsignal_transmission",
                    source_event_id=f"ghost:signal:{signal_id}",
                )
            )
        self._append_once(
            "ghost.parts_consumed",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:parts_consumed:{signal_id}",
            payload={"signal_id": signal_id, "count": len(consumed)},
        )
        return {"count": len(consumed), "parts": consumed}

    def archive_historical_nodes(self, signal_id):
        signal = self._require_signal(signal_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(signal["cycle_id"]) or {}
        snapshot = lock_snapshot.get("snapshot") or {}
        consumed_at = {part["part_id"]: part.get("consumed_at")
                       for part in self.repository.list_parts(signal["cycle_id"])}
        nodes = []
        for part in snapshot.get("parts") or []:
            anchor = part.get("anchor") if isinstance(part.get("anchor"), dict) else {}
            nodes.append(
                self.repository.insert_historical_node(
                    {
                        "signal_id": signal_id,
                        "cycle_id": signal["cycle_id"],
                        "part_id": part.get("part_id"),
                        "part_code": part.get("part_code"),
                        "latitude": anchor.get("latitude"),
                        "longitude": anchor.get("longitude"),
                        "discovered_by": part.get("discovered_by"),
                        "owner_id": part.get("territory_owner_id"),
                        "clan_code": part.get("territory_clan") or part.get("clan_code"),
                        "machine_code": part.get("machine_code"),
                        "profession_code": part.get("profession_code"),
                        "active_since": part.get("activated_at") or part.get("last_activated_at"),
                        "active_until": signal.get("sent_at") or consumed_at.get(part.get("part_id")),
                        "defense_count": len(part.get("hold_time") or []),
                        "metadata": {
                            "target_id": part.get("target_id"),
                            "territory_id": part.get("territory_id"),
                            "territory_state_version": part.get("territory_state_version"),
                        },
                    }
                )
            )
        return {"count": len([node for node in nodes if node]), "nodes": nodes}

    def disable_superpowers(self, signal_id):
        signal = self._require_signal(signal_id)
        event = self._append_once(
            "ghost.abilities_disabled",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:abilities_disabled:{signal_id}",
            payload={"signal_id": signal_id, "reason": "parts_consumed"},
        )
        return {"disabled": True, "event": event}

    def advance_ghostsystem_version(self, signal_id):
        signal = self._require_signal(signal_id)
        cycle = self.repository.get_cycle(signal["cycle_id"])
        source_number = int(cycle.get("ghostsystem_version") or signal.get("source_version") or 0)
        next_number = int(signal.get("next_version") or source_number + 1)
        source_version = cycle.get("source_version") or _version_text(source_number)
        next_version = cycle.get("next_version") or _version_text(next_number)
        updated = cycle
        if not self.repository.get_event_by_dedupe_key(f"ghost:version_prepared:{signal_id}"):
            updated = self.repository.update_cycle(
                signal["cycle_id"],
                source_version=source_version,
                next_version=next_version,
                upgrade_pending=1,
                restart_required=1,
                restart_reason="ghostsignal_transmission",
                restart_signal_id=signal_id,
                restart_from_version=source_version,
                restart_to_version=next_version,
                restart_required_at=self.repository.now(),
            )
        self._append_once(
            "ghost.version_prepared",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:version_prepared:{signal_id}",
            payload={
                "signal_id": signal_id,
                "source_version": source_version,
                "next_version": next_version,
                "reason": "ghostsignal_show_pending",
            },
        )
        # Compatibility event for existing narrative/delta consumers.  The
        # payload explicitly marks this as a prepared cutover; the cycle's
        # current numeric version is intentionally unchanged until rollover.
        self._append_once(
            "ghost.version_changed",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:version_changed:{signal_id}",
            payload={
                "signal_id": signal_id,
                "source_version": source_version,
                "next_version": next_version,
                "cutover_pending": True,
                "reason": "ghostsignal_show_pending",
            },
        )
        self._append_once(
            "ghost.restart_required",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:restart_required:{signal_id}",
            payload={
                "signal_id": signal_id,
                "from_version": source_version,
                "to_version": next_version,
                "reason": "ghostsignal_transmission",
            },
        )
        return {"cycle": updated, "source_version": source_version, "next_version": next_version}

    def begin_stabilization(self, signal_id):
        signal = self._require_signal(signal_id)
        cycle = self.repository.get_cycle(signal["cycle_id"])
        show = self.repository.get_signal_show_for_signal(signal_id)
        until = (show or {}).get("show_ends_at") or cycle.get("stabilization_until")
        if not until:
            duration = max(60, int(GHOSTNETWORK_SIGNAL_SHOW_POLICY.get("duration_seconds") or 900))
            start = _parse_iso(signal.get("sent_at") or self.repository.now())
            until = (start + timedelta(seconds=duration)).isoformat()
        updated = self.repository.update_cycle(
            signal["cycle_id"],
            status="stabilizing",
            stabilization_until=until,
            transmitted_at=signal.get("sent_at"),
        )
        event = self._append_once(
            "ghost.stabilization_started",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:stabilization_started:{signal_id}",
            payload={"signal_id": signal_id, "stabilization_until": until},
        )
        return {"cycle": updated, "stabilization_until": until, "event": event,
                "show": show, "show_event": self.repository.get_event_by_dedupe_key(
                    f"ghost:signal_show_started:{signal_id}")}

    def _ensure_transmission_show(self, signal, cycle, lock):
        show = self.show.ensure_for_signal(
            signal, cycle=cycle,
            # Legacy interrupted signals retain their original clock. New
            # transmissions start at the canonical immutable lock timestamp.
            started_at=signal.get("sent_at") or lock.get("locked_at"),
            ends_at=cycle.get("stabilization_until") or None,
        )
        self._append_once(
            "ghost.transmission_started", cycle_id=signal["cycle_id"],
            entity_id=signal["signal_id"],
            dedupe_key=f"ghost:transmission_started:{signal['cycle_id']}",
            payload={"signal_id": signal["signal_id"],
                     "lock_snapshot_id": signal.get("lock_snapshot_id"),
                     "started_at": show["show_started_at"],
                     "ends_at": show["show_ends_at"],
                     "phase_policy_version": show["phase_policy_version"]},
        )
        show_event = self._append_once(
            "ghost.signal_show_started",
            cycle_id=signal["cycle_id"],
            entity_id=signal["signal_id"],
            dedupe_key=f"ghost:signal_show_started:{signal['signal_id']}",
            audience_scope="public",
            payload={
                "signal_public_id": show.get("signal_public_id"),
                "show_started_at": show.get("show_started_at"),
                "show_ends_at": show.get("show_ends_at"),
                "from_system_version": show.get("from_system_version"),
                "to_system_version": show.get("to_system_version"),
            },
        )
        return {"show": show, "show_event": show_event}

    def resume_interrupted_transmission(self, cycle_id):
        return self._transmit(cycle_id, resume=True)

    def validate_transmission(self, cycle_id):
        cycle_id = _clean(cycle_id)
        cycle = self.repository.get_cycle(cycle_id)
        reasons = []
        if not cycle:
            return {"ok": False, "cycle_id": cycle_id, "reasons": ["cycle_not_found"]}
        if cycle.get("status") != "transmitting":
            reasons.append("cycle_not_transmitting")
        existing_signal = self.repository.get_signal_for_cycle(cycle_id)
        lock_snapshot = self.repository.get_cycle_lock_snapshot(cycle_id)
        if not lock_snapshot:
            reasons.append("lock_snapshot_missing")
        else:
            closure_validation = self.closure.validate_locked_snapshot(cycle_id)
            if not closure_validation.get("valid"):
                reasons.append("lock_snapshot_invalid_checksum")
            snapshot = lock_snapshot.get("snapshot") or {}
            parts = snapshot.get("parts") or []
            connections = ((snapshot.get("topology") or {}).get("connections") or [])
            machines = snapshot.get("machine_progress") or []
            if len(parts) != 20:
                reasons.append("lock_parts_count_not_20")
            if len(connections) != 20:
                reasons.append("lock_connections_count_not_20")
            if sum(1 for part in parts if part.get("status") == "active") != 20:
                reasons.append("lock_active_parts_not_20")
            if sum(1 for machine in machines if machine.get("machine_online")) != 4:
                reasons.append("lock_machines_not_online")
            if any(int(machine.get("parts_active") or 0) != 5 for machine in machines):
                reasons.append("lock_machines_not_five_of_five")
            territory_plan = snapshot.get("territory_consumption_plan") or {}
            if territory_plan.get("execution_required"):
                entries = territory_plan.get("entries") or []
                expected_primary = {
                    _clean(part.get("territory_id")) for part in parts
                    if _clean(part.get("territory_id"))
                }
                actual_primary = {
                    _clean(item.get("territory_id")) for item in entries
                    if _clean(item.get("role")) == "primary"
                }
                if not entries:
                    reasons.append("lock_territory_plan_empty")
                if expected_primary != actual_primary:
                    reasons.append("lock_primary_territories_incomplete")
                if any(
                    bool(item.get("blocking"))
                    for item in territory_plan.get("warnings") or []
                    if isinstance(item, dict)
                ):
                    reasons.append("lock_territory_plan_has_warnings")
        if existing_signal:
            if existing_signal.get("lock_snapshot_id") != (lock_snapshot or {}).get("lock_snapshot_id"):
                reasons.append("signal_lock_snapshot_mismatch")
            if signal_payload_checksum(existing_signal.get("payload") or {}) != existing_signal.get("signal_checksum"):
                reasons.append("signal_payload_invalid_checksum")
            return {
                "ok": not reasons,
                "cycle_id": cycle_id,
                "cycle": cycle,
                "lock_snapshot": lock_snapshot,
                "existing_signal": existing_signal,
                "reasons": reasons,
            }
        return {
            "ok": not reasons,
            "cycle_id": cycle_id,
            "cycle": cycle,
            "lock_snapshot": lock_snapshot,
            "existing_signal": None,
            "reasons": reasons,
        }

    def _require_signal(self, signal_id):
        signal = self.repository.get_signal(signal_id)
        if not signal:
            raise InvalidStateTransition(f"GhostSignal not found: {signal_id}")
        return signal

    def _append_once(self, event_type, cycle_id, entity_id, dedupe_key, payload=None,
                     audience_scope="system"):
        try:
            return self.repository.append_event(
                event_type,
                cycle_id=cycle_id,
                entity_id=entity_id,
                audience_scope=audience_scope,
                dedupe_key=dedupe_key,
                payload=payload or {},
            )
        except RepositoryIntegrityError:
            return self.repository.get_event_by_dedupe_key(dedupe_key)
