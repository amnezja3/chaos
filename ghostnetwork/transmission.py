from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone

from database import dumps_json

from .closure import GhostNetworkClosureService
from .errors import InvalidStateTransition, RepositoryIntegrityError
from .lifecycle import GhostPartLifecycleService
from .repository import GhostNetworkRepository, _clean


STABILIZATION_MINUTES = 15


def _parse_iso(value):
    text = _clean(value)
    if not text:
        return None
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _add_minutes(value, minutes):
    dt = _parse_iso(value) or datetime.now(timezone.utc)
    return (dt + timedelta(minutes=int(minutes or 0))).isoformat()


def _checksum(payload):
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

    def __init__(self, repository=None, lifecycle_service=None, closure_service=None):
        self.repository = repository or GhostNetworkRepository()
        self.lifecycle = lifecycle_service or GhostPartLifecycleService(self.repository)
        self.closure = closure_service or GhostNetworkClosureService(repository=self.repository)

    def start_transmission(self, cycle_id):
        cycle_id = _clean(cycle_id)
        with self.repository.transaction():
            validation = self.validate_transmission(cycle_id)
            if validation.get("existing_signal"):
                return self.resume_interrupted_transmission(cycle_id)
            if not validation.get("ok"):
                return {
                    "ok": False,
                    "status": "blocked",
                    "cycle_id": cycle_id,
                    "reasons": validation.get("reasons") or [],
                    "validation": validation,
                }

            signal = self.create_signal_from_lock(validation["lock_snapshot"])
            rewards = self.apply_transmission_rewards(signal["signal_id"])
            consumed = self.consume_cycle_parts(signal["signal_id"])
            history = self.archive_historical_nodes(signal["signal_id"])
            connections = self.repository.remove_connections_for_cycle(cycle_id, signal_id=signal["signal_id"])
            abilities = self.disable_superpowers(signal["signal_id"])
            version = self.advance_ghostsystem_version(signal["signal_id"])
            stabilization = self.begin_stabilization(signal["signal_id"])
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
            return {
                "ok": True,
                "status": "sent",
                "cycle_id": cycle_id,
                "signal": self.repository.get_signal(signal["signal_id"]),
                "rewards": rewards,
                "consumed": consumed,
                "history": history,
                "connections": connections,
                "abilities": abilities,
                "version": version,
                "stabilization": stabilization,
            }

    def create_signal_from_lock(self, lock_snapshot):
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
            "machines": snapshot.get("machines") or [],
            "closing": snapshot.get("closing") or {},
        }
        signal = self.repository.create_signal(
            {
                "signal_id": f"ghost_signal_{cycle_id}",
                "signal_number": int(payload["signal_number"]),
                "cycle_id": cycle_id,
                "source_version": int(payload["source_version"]),
                "target_year": 2108,
                "status": "sent",
                "outcome": "pending",
                "integrity": 0,
                "recipient": "",
                "sent_at": self.repository.now(),
                "resolved_at": "",
                "next_version": next_version,
                "lock_snapshot_id": lock_snapshot.get("lock_snapshot_id"),
                "signal_checksum": _checksum(payload),
                "payload": payload,
            }
        )
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
        rewards = []
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
                        "base_rsp": 8,
                        "multiplier": 1.0,
                        "final_rsp": 8,
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
                        "base_rsp": 20,
                        "multiplier": 1.0,
                        "final_rsp": 20,
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
                        "active_until": signal.get("sent_at"),
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
        updated = self.repository.update_cycle(
            signal["cycle_id"],
            ghostsystem_version=next_number,
            source_version=source_version,
            next_version=next_version,
            transmitted_at=signal.get("sent_at") or self.repository.now(),
            restart_required=1,
            restart_reason="ghostsignal_transmission",
            restart_signal_id=signal_id,
            restart_from_version=source_version,
            restart_to_version=next_version,
            restart_required_at=self.repository.now(),
        )
        self._append_once(
            "ghost.version_changed",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:version_changed:{signal_id}",
            payload={
                "signal_id": signal_id,
                "source_version": source_version,
                "next_version": next_version,
                "reason": "ghostsignal_transmission",
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
        until = cycle.get("stabilization_until")
        if not until:
            until = _add_minutes(signal.get("sent_at") or self.repository.now(), STABILIZATION_MINUTES)
        updated = self.repository.update_cycle(
            signal["cycle_id"],
            status="stabilizing",
            stabilization_until=until,
        )
        event = self._append_once(
            "ghost.stabilization_started",
            cycle_id=signal["cycle_id"],
            entity_id=signal_id,
            dedupe_key=f"ghost:stabilization_started:{signal_id}",
            payload={"signal_id": signal_id, "stabilization_until": until},
        )
        return {"cycle": updated, "stabilization_until": until, "event": event}

    def resume_interrupted_transmission(self, cycle_id):
        cycle_id = _clean(cycle_id)
        signal = self.repository.get_signal_for_cycle(cycle_id)
        if not signal:
            return self.start_transmission(cycle_id)
        rewards = self.apply_transmission_rewards(signal["signal_id"])
        consumed = self.consume_cycle_parts(signal["signal_id"])
        history = self.archive_historical_nodes(signal["signal_id"])
        connections = self.repository.remove_connections_for_cycle(cycle_id, signal_id=signal["signal_id"])
        abilities = self.disable_superpowers(signal["signal_id"])
        version = self.advance_ghostsystem_version(signal["signal_id"])
        stabilization = self.begin_stabilization(signal["signal_id"])
        return {
            "ok": True,
            "status": "resumed",
            "cycle_id": cycle_id,
            "signal": self.repository.get_signal(signal["signal_id"]),
            "rewards": rewards,
            "consumed": consumed,
            "history": history,
            "connections": connections,
            "abilities": abilities,
            "version": version,
            "stabilization": stabilization,
            "idempotent": True,
        }

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
            machines = snapshot.get("machines") or snapshot.get("machine_progress") or []
            if len(parts) != 20:
                reasons.append("lock_parts_count_not_20")
            if len(connections) != 20:
                reasons.append("lock_connections_count_not_20")
            if sum(1 for part in parts if part.get("status") == "active") != 20:
                reasons.append("lock_active_parts_not_20")
            if sum(1 for machine in machines if machine.get("machine_online")) != 4:
                reasons.append("lock_machines_not_online")
        if existing_signal:
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
