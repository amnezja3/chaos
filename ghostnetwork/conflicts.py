from __future__ import annotations

from datetime import datetime, timezone

from config import (
    GHOSTNETWORK_DEFENSE_POLICY,
    GHOSTNETWORK_RECOVERY_POLICY,
    GHOSTNETWORK_REWARD_COOLDOWNS,
)


OFFENSIVE_ACTION_TYPES = {
    "security_disarmed",
    "pillar_captured",
    "inner_attacked",
    "offensive_ability_used",
    "territory_operation_completed",
    "geometry_changed",
    "defense_layer_destroyed",
}

DEFENSIVE_ACTION_TYPES = {
    "security_rebuilt",
    "rollback",
    "infection_removed",
    "territory_link_repaired",
    "bastion_started",
    "quarantine_started",
    "active_operation_stopped",
    "pillar_recaptured",
    "stable_control_held",
}

REWARD_EVALUATION_STATUSES = {
    "full_reward",
    "reduced_reward",
    "cooldown",
    "review",
    "no_reward",
}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_dt(value):
    if isinstance(value, datetime):
        dt = value
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _seconds_between(start, end):
    try:
        return max(0, int((_as_dt(end) - _as_dt(start)).total_seconds()))
    except Exception:
        return 0


def _unique(values):
    seen = set()
    result = []
    for value in values:
        value = _clean(value)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _action_score(actions):
    return sum(max(0, int(action.get("mechanical_value") or 0)) for action in actions if isinstance(action, dict))


def _actors(actions):
    return _unique(action.get("player_id") for action in actions if isinstance(action, dict))


class GhostDefenseRewardPolicy:
    """Qualifies real defenses/recoveries without deciding territory ownership."""

    def __init__(self, defense=None, recovery=None, cooldowns=None):
        self.defense = dict(GHOSTNETWORK_DEFENSE_POLICY)
        self.recovery = dict(GHOSTNETWORK_RECOVERY_POLICY)
        self.cooldowns = dict(GHOSTNETWORK_REWARD_COOLDOWNS)
        if isinstance(defense, dict):
            self.defense.update(defense)
        if isinstance(recovery, dict):
            self.recovery.update(recovery)
        if isinstance(cooldowns, dict):
            self.cooldowns.update(cooldowns)

    def evaluate_defense(self, conflict, actions, final_state=None):
        conflict = conflict if isinstance(conflict, dict) else {}
        final_state = final_state if isinstance(final_state, dict) else {}
        offensive = [a for a in actions if a.get("side") == "offensive"]
        defensive = [a for a in actions if a.get("side") == "defensive"]
        final_owner = _clean(final_state.get("owner_id") or final_state.get("territory_owner_id"))
        final_clan = _clean(final_state.get("clan_code") or final_state.get("territory_clan"))
        stable = _clean(final_state.get("territory_state") or final_state.get("state") or final_state.get("status"), "stable")
        same_owner = bool(final_owner and final_owner == _clean(conflict.get("initial_owner_id")))
        same_clan = bool(final_clan and final_clan == _clean(conflict.get("initial_clan")))
        duration = _seconds_between(conflict.get("started_at"), final_state.get("resolved_at") or final_state.get("ended_at"))
        attack_progress = max(_int(conflict.get("max_attack_progress")), _action_score(offensive))
        integrity_loss = max(0, _int(conflict.get("initial_integrity"), 100) - _int(final_state.get("integrity"), _int(conflict.get("initial_integrity"), 100)))
        reasons = []
        if not (same_owner or same_clan):
            reasons.append("owner_or_clan_changed")
        if stable not in {"stable", "active", "contained"}:
            reasons.append("not_stable_after_conflict")
        if len(offensive) < _int(self.defense.get("min_offensive_actions")):
            reasons.append("too_few_offensive_actions")
        if attack_progress < _int(self.defense.get("min_attack_progress")) and integrity_loss < _int(self.defense.get("min_integrity_loss")):
            reasons.append("attack_below_threshold")
        if _action_score(defensive) < _int(self.defense.get("min_defensive_score")):
            reasons.append("defense_below_threshold")
        if duration and duration < _int(self.defense.get("min_conflict_seconds")):
            reasons.append("conflict_too_short")
        if reasons:
            return {
                "status": "no_reward",
                "reason": reasons[0],
                "reasons": reasons,
                "duration_seconds": duration,
                "attack_progress": attack_progress,
                "integrity_loss": integrity_loss,
                "offensive_actions": len(offensive),
                "defensive_actions": len(defensive),
            }
        return {
            "status": "full_reward",
            "reason": "real_defense",
            "duration_seconds": duration,
            "attack_progress": attack_progress,
            "integrity_loss": integrity_loss,
            "offensive_actions": len(offensive),
            "defensive_actions": len(defensive),
        }

    def evaluate_recovery(self, part, previous_period, conflict, actions, context=None):
        part = part if isinstance(part, dict) else {}
        previous_period = previous_period if isinstance(previous_period, dict) else {}
        conflict = conflict if isinstance(conflict, dict) else {}
        context = context if isinstance(context, dict) else {}
        offensive = [a for a in actions if a.get("side") == "offensive"]
        final_clan = _clean(context.get("final_clan") or part.get("territory_clan") or part.get("clan_code"))
        proper_clan = _clean(part.get("clan_code"))
        previous_clan = _clean(previous_period.get("clan_code"))
        duration = _int(previous_period.get("duration_seconds"))
        disarm_score = sum(
            max(0, int(action.get("mechanical_value") or 0))
            for action in offensive
            if action.get("action_type") in {"security_disarmed", "defense_layer_destroyed", "pillar_captured", "inner_attacked"}
        )
        reasons = []
        if not previous_period:
            reasons.append("missing_previous_control")
        if previous_clan and proper_clan and previous_clan == proper_clan:
            reasons.append("previous_control_not_foreign")
        if final_clan and proper_clan and final_clan != proper_clan:
            reasons.append("not_recovered_by_proper_clan")
        if _clean(part.get("status")) not in {"active", "contained", "public"}:
            reasons.append("part_not_active_after_recovery")
        if len(offensive) < _int(self.recovery.get("min_offensive_actions")) or disarm_score < _int(self.recovery.get("min_disarm_score")):
            reasons.append("real_disarm_missing")
        if not duration or duration < _int(self.recovery.get("min_previous_control_seconds")):
            reasons.append("previous_control_too_short")
        if reasons:
            status = "reduced_reward" if reasons == ["previous_control_too_short"] else "no_reward"
            return {
                "status": status,
                "reason": reasons[0],
                "reasons": reasons,
                "previous_control_seconds": duration,
                "disarm_score": disarm_score,
                "offensive_actions": len(offensive),
            }
        return {
            "status": "full_reward",
            "reason": "real_recovery",
            "previous_control_seconds": duration,
            "disarm_score": disarm_score,
            "offensive_actions": len(offensive),
        }

    def evaluate_pair_risk(self, transfer_history, previous_owner, new_owner, now=None):
        previous_owner = _clean(previous_owner)
        new_owner = _clean(new_owner)
        now_dt = _as_dt(now)
        for item in transfer_history or []:
            if not isinstance(item, dict):
                continue
            same_pair = (
                _clean(item.get("previous_owner_id")) == new_owner
                and _clean(item.get("new_owner_id")) == previous_owner
            ) or (
                _clean(item.get("previous_owner_id")) == previous_owner
                and _clean(item.get("new_owner_id")) == new_owner
            )
            if not same_pair:
                continue
            age = max(0, int((now_dt - _as_dt(item.get("created_at"))).total_seconds()))
            if age <= _int(self.cooldowns.get("same_pair_seconds")):
                return {"status": "cooldown", "reason": "same_pair_cooldown", "age_seconds": age}
        return {"status": "full_reward", "reason": "no_pair_risk"}


class GhostStrategicConflictService:
    def __init__(self, repository, reward_service=None, policy=None):
        self.repository = repository
        self.rewards = reward_service
        self.policy = policy or GhostDefenseRewardPolicy()

    @staticmethod
    def _cycle_id(repository, cycle_id=""):
        cycle_id = _clean(cycle_id)
        if cycle_id:
            return cycle_id
        active = repository.get_active_cycle()
        return (active or {}).get("cycle_id") or ""

    def on_conflict_started(self, part, territory_snapshot=None, context=None):
        part = part if isinstance(part, dict) else {}
        territory_snapshot = territory_snapshot if isinstance(territory_snapshot, dict) else {}
        context = context if isinstance(context, dict) else {}
        cycle_id = self._cycle_id(self.repository, part.get("cycle_id") or context.get("cycle_id"))
        part_id = _clean(part.get("part_id") or context.get("part_id"))
        territory_id = _clean(territory_snapshot.get("territory_id") or part.get("territory_id") or context.get("territory_id"))
        started_at = _clean(context.get("started_at") or territory_snapshot.get("started_at") or self.repository.now())
        dedupe_key = _clean(context.get("dedupe_key") or f"ghost-conflict:{cycle_id}:{part_id}:{territory_id}:{started_at}")
        snapshot = {
            "part_id": part_id,
            "territory_id": territory_id,
            "initial_owner_id": _clean(territory_snapshot.get("owner_id") or territory_snapshot.get("territory_owner_id") or part.get("territory_owner_id")),
            "initial_clan": _clean(territory_snapshot.get("clan_code") or territory_snapshot.get("territory_clan") or part.get("territory_clan")),
            "initial_status": _clean(part.get("status")),
            "initial_integrity": _int(territory_snapshot.get("integrity"), 100),
            "initial_security_score": _int(territory_snapshot.get("security_score")),
            "active_offensive_operations": _int(territory_snapshot.get("active_offensive_operations") or context.get("active_offensive_operations")),
            "initial_participants": territory_snapshot.get("participants") if isinstance(territory_snapshot.get("participants"), list) else [],
        }
        conflict = self.repository.insert_strategic_conflict({
            "cycle_id": cycle_id,
            "part_id": part_id,
            "territory_id": territory_id,
            "initial_owner_id": snapshot["initial_owner_id"],
            "initial_clan": snapshot["initial_clan"],
            "initial_status": snapshot["initial_status"],
            "initial_integrity": snapshot["initial_integrity"],
            "initial_security_score": snapshot["initial_security_score"],
            "active_offensive_operations": snapshot["active_offensive_operations"],
            "initial_participants": snapshot["initial_participants"],
            "snapshot": snapshot,
            "started_at": started_at,
            "dedupe_key": dedupe_key,
        })
        if not conflict.get("idempotent"):
            self._safe_event(
                "ghost.defense_started",
                conflict,
                audience_scope="clan",
                audience_clan=conflict.get("initial_clan"),
                payload={
                    "conflict_id": conflict["conflict_id"],
                    "territory_id": conflict.get("territory_id"),
                    "owner_id": conflict.get("initial_owner_id"),
                    "clan_code": conflict.get("initial_clan"),
                    "started_at": conflict.get("started_at"),
                },
            )
        return {"ok": True, "status": "started", "conflict": conflict}

    def record_conflict_progress(self, conflict_id, progress=0, source_event_id="", metadata=None):
        conflict = self.repository.get_strategic_conflict(conflict_id)
        if not conflict:
            return {"ok": False, "status": "conflict_not_found"}
        progress = max(_int(progress), int(conflict.get("max_attack_progress") or 0))
        updated = self.repository.update_strategic_conflict(
            conflict_id,
            max_attack_progress=progress,
        )
        self._safe_event(
            "ghost.defense_progress_changed",
            updated,
            payload={
                "conflict_id": updated["conflict_id"],
                "territory_id": updated.get("territory_id"),
                "max_attack_progress": updated.get("max_attack_progress"),
                "source_event_id": _clean(source_event_id),
                "metadata": metadata if isinstance(metadata, dict) else {},
            },
            dedupe_suffix=f":{_clean(source_event_id) or progress}",
        )
        return {"ok": True, "status": "progress_recorded", "conflict": updated}

    def record_offensive_action(self, conflict_id, action_type, **kwargs):
        return self._record_action("offensive", OFFENSIVE_ACTION_TYPES, conflict_id, action_type, **kwargs)

    def record_defensive_action(self, conflict_id, action_type, **kwargs):
        return self._record_action("defensive", DEFENSIVE_ACTION_TYPES, conflict_id, action_type, **kwargs)

    def _record_action(self, side, allowed, conflict_id, action_type, **kwargs):
        action_type = _clean(action_type)
        if action_type not in allowed:
            return {"ok": False, "status": "ignored", "reason": "unconfirmed_action_type", "action_type": action_type}
        conflict = self.repository.get_strategic_conflict(conflict_id)
        if not conflict:
            return {"ok": False, "status": "conflict_not_found"}
        score = max(0, _int(kwargs.get("mechanical_value") or kwargs.get("score") or 1))
        player_id = _clean(kwargs.get("player_id"))
        dedupe_key = _clean(
            kwargs.get("dedupe_key")
            or f"ghost-conflict-action:{conflict_id}:{side}:{action_type}:{player_id}:{_clean(kwargs.get('source_event_id') or kwargs.get('operation_id'))}"
        )
        action = self.repository.insert_conflict_action({
            "conflict_id": conflict_id,
            "cycle_id": conflict["cycle_id"],
            "part_id": conflict["part_id"],
            "side": side,
            "action_type": action_type,
            "player_id": player_id,
            "clan_code": kwargs.get("clan_code"),
            "profession_code": kwargs.get("profession_code"),
            "target_id": kwargs.get("target_id"),
            "operation_id": kwargs.get("operation_id"),
            "mechanical_value": score,
            "weight": kwargs.get("weight") or 1.0,
            "source_event_id": kwargs.get("source_event_id"),
            "dedupe_key": dedupe_key,
            "metadata": kwargs.get("metadata") if isinstance(kwargs.get("metadata"), dict) else {},
            "created_at": kwargs.get("created_at"),
        })
        actions = self.repository.list_conflict_actions(conflict_id)
        offensive = [item for item in actions if item.get("side") == "offensive"]
        defensive = [item for item in actions if item.get("side") == "defensive"]
        updated = self.repository.update_strategic_conflict(
            conflict_id,
            max_attack_progress=max(_int(conflict.get("max_attack_progress")), _action_score(offensive)),
            offensive_score=_action_score(offensive),
            defensive_score=_action_score(defensive),
            offensive_actors_json=_actors(offensive),
            defensive_actors_json=_actors(defensive),
        )
        return {"ok": True, "status": "recorded", "action": action, "conflict": updated}

    def evaluate_defense_reward(self, conflict_id, final_state=None):
        conflict = self.repository.get_strategic_conflict(conflict_id)
        if not conflict:
            return {"ok": False, "status": "conflict_not_found"}
        actions = self.repository.list_conflict_actions(conflict_id)
        assessment = self.policy.evaluate_defense(conflict, actions, final_state=final_state)
        return {"ok": True, "status": assessment["status"], "assessment": assessment}

    def evaluate_recovery_reward(self, part, previous_period=None, conflict_id="", context=None):
        part = part if isinstance(part, dict) else {}
        conflict = self.repository.get_strategic_conflict(conflict_id) if conflict_id else {}
        actions = self.repository.list_conflict_actions(conflict_id) if conflict_id else []
        previous_period = previous_period or self._latest_foreign_period(part)
        assessment = self.policy.evaluate_recovery(part, previous_period, conflict or {}, actions, context=context)
        return {"ok": True, "status": assessment["status"], "assessment": assessment, "previous_period": previous_period}

    def resolve_conflict_outcome(self, conflict_id, final_state=None, context=None, apply_rewards=False):
        final_state = final_state if isinstance(final_state, dict) else {}
        context = context if isinstance(context, dict) else {}
        conflict = self.repository.get_strategic_conflict(conflict_id)
        if not conflict:
            return {"ok": False, "status": "conflict_not_found"}
        if conflict.get("status") == "resolved":
            return {"ok": True, "status": "already_resolved", "conflict": conflict, "idempotent": True}
        actions = self.repository.list_conflict_actions(conflict_id)
        defense = self.policy.evaluate_defense(conflict, actions, final_state=final_state)
        part = self.repository.get_part(conflict.get("part_id"))
        previous_period = context.get("previous_period") if isinstance(context.get("previous_period"), dict) else self._latest_foreign_period(part or {})
        recovery = self.policy.evaluate_recovery(part or {}, previous_period, conflict, actions, context={**context, **final_state})
        pair_risk = self.policy.evaluate_pair_risk(
            self.repository.list_transfer_history(
                part_id=conflict.get("part_id"),
                previous_owner_id=final_state.get("owner_id") or final_state.get("territory_owner_id"),
                new_owner_id=conflict.get("initial_owner_id"),
                limit=20,
            ),
            conflict.get("initial_owner_id"),
            final_state.get("owner_id") or final_state.get("territory_owner_id"),
            now=final_state.get("resolved_at") or self.repository.now(),
        )
        if pair_risk.get("status") != "full_reward":
            if defense.get("status") == "full_reward":
                defense = {**defense, "status": pair_risk["status"], "reason": pair_risk["reason"]}
            if recovery.get("status") == "full_reward":
                recovery = {**recovery, "status": pair_risk["status"], "reason": pair_risk["reason"]}
        rewards = []
        event = None
        if defense.get("status") in {"full_reward", "reduced_reward"}:
            event = self._safe_event(
                "ghost.part_defended",
                conflict,
                audience_scope="clan",
                audience_clan=conflict.get("initial_clan"),
                payload=self._public_conflict_payload(conflict, final_state, defense),
            )
            rewards.extend(self._create_defense_rewards(conflict, actions, defense, event, apply_rewards=apply_rewards))
        elif defense.get("status") in {"cooldown", "no_reward"}:
            self._safe_event("ghost.reward_reduced", conflict, payload=self._public_conflict_payload(conflict, final_state, defense))
        elif defense.get("status") == "review":
            self._safe_event("ghost.reward_flagged", conflict, payload=self._public_conflict_payload(conflict, final_state, defense))

        recovery_event = None
        if recovery.get("status") in {"full_reward", "reduced_reward"}:
            recovery_event = self._safe_event(
                "ghost.part_recovered",
                conflict,
                audience_scope="clan",
                audience_clan=(part or {}).get("clan_code") or final_state.get("clan_code") or "",
                payload=self._public_recovery_payload(conflict, part or {}, previous_period or {}, recovery, final_state),
                dedupe_suffix=":recovery",
            )
            rewards.extend(self._create_recovery_rewards(conflict, actions, recovery, recovery_event, final_state, apply_rewards=apply_rewards))
        elif recovery.get("status") in {"cooldown", "no_reward"} and recovery.get("reason") != "missing_previous_control":
            self._safe_event("ghost.reward_reduced", conflict, payload=self._public_recovery_payload(conflict, part or {}, previous_period or {}, recovery, final_state), dedupe_suffix=":recovery")
        elif recovery.get("status") == "review":
            self._safe_event("ghost.reward_flagged", conflict, payload=self._public_recovery_payload(conflict, part or {}, previous_period or {}, recovery, final_state), dedupe_suffix=":recovery")

        reward_status = recovery.get("status") if recovery.get("status") in {"full_reward", "reduced_reward"} else defense.get("status")
        reward_amount = sum(_int((item.get("created") or item.get("reward") or {}).get("final_rsp")) for item in rewards if isinstance(item, dict))
        self.repository.insert_transfer_history({
            "cycle_id": conflict["cycle_id"],
            "part_id": conflict["part_id"],
            "previous_owner_id": conflict.get("initial_owner_id"),
            "new_owner_id": final_state.get("owner_id") or final_state.get("territory_owner_id"),
            "previous_clan": conflict.get("initial_clan"),
            "new_clan": final_state.get("clan_code") or final_state.get("territory_clan"),
            "conflict_id": conflict_id,
            "reward_status": reward_status,
            "reward_amount": reward_amount,
            "metadata": {"defense": defense, "recovery": recovery, "pair_risk": pair_risk},
            "dedupe_key": f"ghost-transfer:{conflict_id}",
            "created_at": final_state.get("resolved_at") or self.repository.now(),
        })
        assessment = {"defense": defense, "recovery": recovery, "pair_risk": pair_risk, "reward_count": len(rewards)}
        updated = self.repository.update_strategic_conflict(
            conflict_id,
            status="resolved",
            outcome=_clean(context.get("outcome") or "stabilized"),
            resolved_at=final_state.get("resolved_at") or self.repository.now(),
            assessment_json=assessment,
        )
        return {
            "ok": True,
            "status": "resolved",
            "conflict": updated,
            "defense": defense,
            "recovery": recovery,
            "rewards": rewards,
            "events": [event, recovery_event],
        }

    def reconcile_ghost_conflict_outcomes(self, conflict_id=None, dry_run=True):
        conflicts = []
        if conflict_id:
            item = self.repository.get_strategic_conflict(conflict_id)
            if item:
                conflicts.append(item)
        else:
            active = self.repository.get_active_cycle()
            cycle_id = (active or {}).get("cycle_id")
            if not cycle_id:
                return {"ok": True, "dry_run": dry_run, "issues": []}
            conflicts = self._list_conflicts_for_cycle(cycle_id)
        issues = []
        for conflict in conflicts:
            actions = self.repository.list_conflict_actions(conflict["conflict_id"])
            if conflict.get("status") == "active":
                issues.append({"type": "active_conflict_without_outcome", "conflict_id": conflict["conflict_id"]})
            if conflict.get("status") == "resolved" and not conflict.get("assessment"):
                issues.append({"type": "resolved_conflict_without_assessment", "conflict_id": conflict["conflict_id"]})
            if conflict.get("status") == "resolved" and not actions:
                issues.append({"type": "resolved_conflict_without_actions", "conflict_id": conflict["conflict_id"]})
        return {"ok": True, "dry_run": dry_run, "issues": issues, "count": len(issues)}

    def _list_conflicts_for_cycle(self, cycle_id):
        # Repository keeps this table private, but the reconciliation service needs
        # read-only access for diagnostics.
        with self.repository._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_strategic_conflicts
                WHERE cycle_id = ?
                ORDER BY started_at DESC
                LIMIT 500
                """,
                (_clean(cycle_id),),
            ).fetchall()
            return [self.repository._strategic_conflict(row) for row in rows]

    def _latest_foreign_period(self, part):
        part = part if isinstance(part, dict) else {}
        periods = self.repository.list_control_periods(part.get("part_id"), cycle_id=part.get("cycle_id"), limit=20)
        proper_clan = _clean(part.get("clan_code"))
        for period in periods:
            if _clean(period.get("clan_code")) and _clean(period.get("clan_code")) != proper_clan:
                return period
        return None

    def _safe_event(self, event_type, conflict, payload=None, audience_scope="internal", audience_clan="", dedupe_suffix=""):
        try:
            return self.repository.append_event(
                event_type,
                cycle_id=conflict.get("cycle_id"),
                part_id=conflict.get("part_id"),
                entity_id=conflict.get("conflict_id"),
                clan_code=audience_clan or conflict.get("initial_clan") or "",
                territory_id=conflict.get("territory_id") or "",
                audience_scope=audience_scope,
                audience_clan=audience_clan or "",
                dedupe_key=f"ghost:{event_type}:{conflict.get('conflict_id')}{dedupe_suffix}",
                payload=payload if isinstance(payload, dict) else {},
            )
        except Exception:
            return None

    def _public_conflict_payload(self, conflict, final_state, assessment):
        return {
            "conflict_id": conflict.get("conflict_id"),
            "territory_id": conflict.get("territory_id"),
            "owner_id": final_state.get("owner_id") or final_state.get("territory_owner_id") or conflict.get("initial_owner_id"),
            "clan_code": final_state.get("clan_code") or final_state.get("territory_clan") or conflict.get("initial_clan"),
            "duration_seconds": assessment.get("duration_seconds", 0),
            "max_attack_progress": assessment.get("attack_progress", conflict.get("max_attack_progress", 0)),
            "participants": {
                "offensive": conflict.get("offensive_actors", []),
                "defensive": conflict.get("defensive_actors", []),
            },
            "result": assessment.get("status"),
            "reason": assessment.get("reason"),
        }

    def _public_recovery_payload(self, conflict, part, previous_period, assessment, final_state):
        return {
            "conflict_id": conflict.get("conflict_id"),
            "territory_id": conflict.get("territory_id"),
            "previous_owner_id": previous_period.get("owner_id"),
            "previous_clan": previous_period.get("clan_code"),
            "new_owner_id": final_state.get("owner_id") or final_state.get("territory_owner_id"),
            "new_clan": final_state.get("clan_code") or final_state.get("territory_clan"),
            "previous_control_seconds": assessment.get("previous_control_seconds", 0),
            "result": assessment.get("status"),
            "reason": assessment.get("reason"),
        }

    def _reward_plan(self, event, reward_type, player_id, clan_code, score, weight, metadata):
        if not self.rewards:
            return None
        plan = self.rewards.evaluate_event_reward(
            {
                "event_id": event.get("event_id") if isinstance(event, dict) else "",
                "event_type": "ghost." + reward_type if not reward_type.startswith("ghost.") else reward_type,
                "cycle_id": event.get("cycle_id") if isinstance(event, dict) else "",
                "part_id": event.get("part_id") if isinstance(event, dict) else "",
                "player_id": player_id,
                "clan_code": clan_code,
                "territory_id": event.get("territory_id") if isinstance(event, dict) else "",
                "payload": {
                    "player_id": player_id,
                    "clan_code": clan_code,
                    "score": score,
                    "weight": weight,
                    **(metadata if isinstance(metadata, dict) else {}),
                },
            },
            context={"reward_type": reward_type, "score": score, "weight": weight},
        )
        return plan

    def _create_defense_rewards(self, conflict, actions, assessment, event, apply_rewards=False):
        if not self.rewards or not isinstance(event, dict):
            return []
        cap = _int(self.policy.defense.get("total_rsp_cap"))
        owner_id = conflict.get("initial_owner_id")
        clan_code = conflict.get("initial_clan")
        results = []
        owner_plan = self._reward_plan(
            event,
            "part_defended",
            owner_id,
            clan_code,
            self.policy.defense.get("owner_reward_score", 1),
            1.0 if assessment.get("status") == "full_reward" else 0.5,
            {"conflict_id": conflict.get("conflict_id"), "assessment": assessment},
        )
        if owner_plan and owner_plan.get("ok"):
            owner_plan["final_rsp"] = min(_int(owner_plan.get("final_rsp")), cap)
            results.append(self.rewards.create_reward_entry(owner_plan))
        remaining = max(0, cap - sum(_int((item.get("reward") or {}).get("final_rsp")) for item in results))
        by_player = {}
        for action in actions:
            if action.get("side") != "defensive" or action.get("player_id") == owner_id:
                continue
            by_player.setdefault(action["player_id"], {"score": 0, "clan_code": action.get("clan_code") or clan_code})
            by_player[action["player_id"]]["score"] += _int(action.get("mechanical_value"))
        for player_id, data in by_player.items():
            if remaining <= 0 or data["score"] < _int(self.policy.defense.get("support_min_score")):
                continue
            plan = self._reward_plan(
                event,
                "defense_support",
                player_id,
                data["clan_code"],
                self.policy.defense.get("support_reward_score", 1),
                min(1.0, max(0.2, data["score"] / 10.0)),
                {"conflict_id": conflict.get("conflict_id"), "support_score": data["score"], "assessment": assessment},
            )
            if plan and plan.get("ok"):
                plan["final_rsp"] = min(_int(plan.get("final_rsp")), remaining)
                created = self.rewards.create_reward_entry(plan)
                results.append(created)
                remaining -= _int((created.get("reward") or {}).get("final_rsp"))
        return results

    def _create_recovery_rewards(self, conflict, actions, assessment, event, final_state, apply_rewards=False):
        if not self.rewards or not isinstance(event, dict):
            return []
        cap = _int(self.policy.recovery.get("total_rsp_cap"))
        player_id = _clean(final_state.get("activator_id") or final_state.get("owner_id") or final_state.get("territory_owner_id"))
        clan_code = _clean(final_state.get("clan_code") or final_state.get("territory_clan"))
        plan = self._reward_plan(
            event,
            "part_recovered",
            player_id,
            clan_code,
            self.policy.recovery.get("owner_reward_score", 1),
            1.0 if assessment.get("status") == "full_reward" else 0.5,
            {"conflict_id": conflict.get("conflict_id"), "assessment": assessment},
        )
        if not plan or not plan.get("ok"):
            return []
        plan["final_rsp"] = min(_int(plan.get("final_rsp")), cap)
        return [self.rewards.create_reward_entry(plan)]
