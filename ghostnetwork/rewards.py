from __future__ import annotations

import copy

from config import (
    GHOSTNETWORK_CLAN_REPUTATION_WEIGHTS,
    GHOSTNETWORK_PAUSE_HOLD_REWARDS_DURING_CONFLICT,
    GHOSTNETWORK_REWARD_BASE_RSP,
    GHOSTNETWORK_REWARD_MULTIPLIERS,
)


ALLOWED_CONTRIBUTION_TYPES = {
    "part_discovered",
    "part_first_contained",
    "part_first_activated",
    "part_recovered",
    "part_stable_held",
    "part_defended",
    "defense_support",
    "attack_support",
    "territory_repaired",
    "ability_support",
    "transmission_node_held",
    "network_closer",
}

REWARD_STATUSES = {"pending", "applied", "rejected", "failed", "cancelled"}

PART_UNIQUE_REWARD_TYPES = {
    "part_discovered",
    "part_first_contained",
    "part_first_activated",
    "part_recovered",
}

EVENT_TO_CONTRIBUTION = {
    "ghost.part_discovered": "part_discovered",
    "ghost.part_first_contained": "part_first_contained",
    "ghost.part_contained": "part_first_contained",
    "ghost.part_first_activated": "part_first_activated",
    "ghost.part_activated": "part_first_activated",
    "ghost.part_recovered": "part_recovered",
    "ghost.part_stable_held": "part_stable_held",
    "ghost.part_defended": "part_defended",
    "ghost.defense_support": "defense_support",
    "ghost.attack_support": "attack_support",
    "ghost.territory_repaired": "territory_repaired",
    "ghost.ability_support": "ability_support",
    "ghost.transmission_node_held": "transmission_node_held",
    "ghost.network_closer": "network_closer",
}

PROFILE_STAT_BY_REWARD = {
    "part_discovered": "parts_discovered",
    "part_first_contained": "parts_first_contained",
    "part_first_activated": "parts_activated",
    "part_recovered": "parts_recovered",
    "part_stable_held": "parts_stable_held",
    "part_defended": "parts_defended",
    "defense_support": "defense_support",
    "attack_support": "attack_support",
    "territory_repaired": "territories_repaired",
    "ability_support": "ability_support",
    "transmission_node_held": "transmission_nodes_held",
    "network_closer": "networks_closed",
}

CLAN_REP_FIELD_BY_REWARD = {
    "part_discovered": "parts_discovered",
    "part_first_contained": "parts_first_contained",
    "part_first_activated": "parts_activated",
    "part_recovered": "parts_recovered",
    "part_defended": "territories_defended",
    "transmission_node_held": "transmission_nodes_held",
    "network_closer": "networks_closed",
}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _event_type(event):
    event = event if isinstance(event, dict) else {}
    return _clean(event.get("event_type") or event.get("type"))


def _payload(event):
    event = event if isinstance(event, dict) else {}
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _first_present(*values):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return ""


def resolve_standard_operation_rsp(profile=None, context=None):
    """Resolve the base RSP amount for a GhostNetwork event.

    GhostNetwork feeds the existing RSP/respect field. This helper only decides
    the base amount; it never changes level thresholds and never mutates profile.
    """
    context = context if isinstance(context, dict) else {}
    score = int(context.get("score") or context.get("operation_score") or GHOSTNETWORK_REWARD_BASE_RSP)
    risk_bonus = int(context.get("risk_bonus") or 0)
    quality_bonus = int(context.get("quality_bonus") or 0)
    return max(0, score + risk_bonus + quality_bonus)


class GhostClanReputationPolicy:
    def __init__(self, weights=None):
        self.weights = dict(GHOSTNETWORK_CLAN_REPUTATION_WEIGHTS)
        if isinstance(weights, dict):
            self.weights.update(weights)

    def reputation_for(self, contribution_type, score=1, weight=1.0):
        contribution_type = _clean(contribution_type)
        base = int(self.weights.get(contribution_type, 0) or 0)
        return max(0, int(round(base * max(1, int(score or 1)) * max(0.0, float(weight or 1.0)))))

    def increments_for_reward(self, reward):
        reward = reward if isinstance(reward, dict) else {}
        reward_type = _clean(reward.get("reward_type"))
        score = int((reward.get("metadata") or {}).get("score") or 1)
        weight = float((reward.get("metadata") or {}).get("weight") or 1.0)
        reputation = self.reputation_for(reward_type, score=score, weight=weight)
        increments = {"total_reputation": reputation}
        field = CLAN_REP_FIELD_BY_REWARD.get(reward_type)
        if field:
            increments[field] = 1
        return increments


class GhostContributionService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def build_dedupe_key(cycle_id, contribution_type, player_id="", part_id="", source_event_id="", operation_id=""):
        return "ghost-contribution:{}:{}:{}:{}:{}:{}".format(
            _clean(cycle_id),
            _clean(contribution_type),
            _clean(player_id),
            _clean(part_id),
            _clean(source_event_id),
            _clean(operation_id),
        )

    def record_contribution(self, **kwargs):
        contribution_type = _clean(kwargs.get("contribution_type"))
        if contribution_type not in ALLOWED_CONTRIBUTION_TYPES:
            return {
                "ok": False,
                "status": "rejected",
                "reason": "invalid_contribution_type",
                "contribution_type": contribution_type,
            }
        data = copy.deepcopy(kwargs)
        data.setdefault(
            "dedupe_key",
            self.build_dedupe_key(
                data.get("cycle_id"),
                contribution_type,
                player_id=data.get("player_id"),
                part_id=data.get("part_id"),
                source_event_id=data.get("source_event_id"),
                operation_id=data.get("operation_id"),
            ),
        )
        data.setdefault("score", 1)
        data.setdefault("weight", 1.0)
        saved = self.repository.insert_contribution(data)
        event = None
        if not saved.get("idempotent"):
            try:
                event = self.repository.append_event(
                    "ghost.contribution_recorded",
                    cycle_id=saved["cycle_id"],
                    part_id=saved.get("part_id") or "",
                    entity_id=saved["contribution_id"],
                    player_id=saved.get("player_id") or "",
                    clan_code=saved.get("clan_code") or "",
                    territory_id=saved.get("territory_id") or "",
                    audience_scope="internal",
                    dedupe_key=f"ghost:contribution_recorded:{saved['dedupe_key'] or saved['contribution_id']}",
                    payload={
                        "contribution_id": saved["contribution_id"],
                        "contribution_type": saved["contribution_type"],
                        "score": saved["score"],
                        "weight": saved["weight"],
                    },
                )
            except Exception:
                event = None
        return {"ok": True, "status": "recorded", "contribution": saved, "event": event}

    def list_player_contributions(self, player_id, cycle_id=None, limit=500):
        return self.repository.list_player_contributions(player_id, cycle_id=cycle_id, limit=limit)

    def list_cycle_contributions(self, cycle_id, limit=1000):
        return self.repository.list_cycle_contributions(cycle_id, limit=limit)

    def aggregate_player_contribution(self, player_id, cycle_id=None):
        return self.repository.aggregate_player_contribution(player_id, cycle_id=cycle_id)

    def aggregate_clan_contribution(self, clan_code, cycle_id=None):
        return self.repository.aggregate_clan_contribution(clan_code, cycle_id=cycle_id)


class GhostRewardService:
    def __init__(self, repository, contribution_service=None, reputation_policy=None):
        self.repository = repository
        self.contributions = contribution_service or GhostContributionService(repository)
        self.reputation_policy = reputation_policy or GhostClanReputationPolicy()

    @staticmethod
    def reward_key(cycle_id, reward_type, player_id="", part_id="", source_event_id="", period_start=""):
        suffix = period_start if period_start else source_event_id
        return "ghost-reward:{}:{}:{}:{}:{}".format(
            _clean(cycle_id),
            _clean(part_id),
            _clean(reward_type),
            _clean(player_id),
            _clean(suffix),
        )

    def evaluate_event_reward(self, event, profile=None, context=None):
        event = event if isinstance(event, dict) else {}
        context = context if isinstance(context, dict) else {}
        payload = _payload(event)
        event_type = _event_type(event)
        reward_type = _clean(context.get("reward_type") or EVENT_TO_CONTRIBUTION.get(event_type))
        if reward_type not in ALLOWED_CONTRIBUTION_TYPES:
            return {"ok": False, "status": "rejected", "reason": "unsupported_event", "event_type": event_type}

        cycle_id = _clean(_first_present(event.get("cycle_id"), payload.get("cycle_id"), context.get("cycle_id")))
        if not cycle_id:
            active = self.repository.get_active_cycle()
            cycle_id = (active or {}).get("cycle_id") or ""
        cycle = self.repository.get_cycle(cycle_id) if cycle_id else None
        if not cycle or cycle.get("status") not in {"active", "stabilizing", "transmitting"}:
            return {"ok": False, "status": "rejected", "reason": "inactive_cycle", "cycle_id": cycle_id}

        player_id = _clean(_first_present(
            event.get("player_id"),
            payload.get("player_id"),
            payload.get("discovered_by"),
            payload.get("owner_id"),
            (profile or {}).get("username") if isinstance(profile, dict) else "",
        ))
        if not player_id:
            return {"ok": False, "status": "rejected", "reason": "missing_player", "reward_type": reward_type}
        part_id = _clean(_first_present(event.get("part_id"), payload.get("part_id"), context.get("part_id")))
        source_event_id = _clean(_first_present(event.get("event_id"), payload.get("event_id"), context.get("source_event_id")))
        period_start = _clean(_first_present(payload.get("period_start"), context.get("period_start")))

        if reward_type == "part_stable_held":
            if GHOSTNETWORK_PAUSE_HOLD_REWARDS_DURING_CONFLICT and _clean(payload.get("conflict_state"), "none") != "none":
                return {"ok": False, "status": "rejected", "reason": "hold_paused_by_conflict", "reward_type": reward_type}
            if _clean(payload.get("owner_clan")) and _clean(payload.get("part_clan")) and _clean(payload.get("owner_clan")) != _clean(payload.get("part_clan")):
                return {"ok": False, "status": "rejected", "reason": "foreign_hold_not_rewarded", "reward_type": reward_type}
            if not period_start:
                return {"ok": False, "status": "rejected", "reason": "missing_hold_period", "reward_type": reward_type}

        base_rsp = resolve_standard_operation_rsp(profile=profile, context={**context, **payload})
        multiplier = float(GHOSTNETWORK_REWARD_MULTIPLIERS.get(reward_type, 1.0) or 1.0)
        final_rsp = max(0, int(round(base_rsp * multiplier)))
        reward_source_id = source_event_id
        if reward_type in PART_UNIQUE_REWARD_TYPES:
            reward_source_id = ""
        reward_key = self.reward_key(
            cycle_id,
            reward_type,
            player_id=player_id,
            part_id=part_id,
            source_event_id=reward_source_id,
            period_start=period_start,
        )
        existing = self.repository.get_reward_by_key(reward_key)
        if existing:
            return {"ok": True, "status": "exists", "reward": existing, "idempotent": True}
        clan_code = _clean(_first_present(event.get("clan_code"), payload.get("clan_code"), payload.get("player_clan"), context.get("clan_code")))
        return {
            "ok": True,
            "status": "eligible",
            "reward_key": reward_key,
            "cycle_id": cycle_id,
            "signal_id": _clean(_first_present(event.get("signal_id"), payload.get("signal_id"), context.get("signal_id"))),
            "player_id": player_id,
            "clan_code": clan_code,
            "profession_code": _clean(_first_present(payload.get("profession_code"), context.get("profession_code"))),
            "reward_type": reward_type,
            "contribution_type": reward_type,
            "part_id": part_id,
            "territory_id": _clean(_first_present(event.get("territory_id"), payload.get("territory_id"), context.get("territory_id"))),
            "operation_id": _clean(_first_present(payload.get("operation_id"), context.get("operation_id"))),
            "source_event_id": source_event_id,
            "base_rsp": base_rsp,
            "multiplier": multiplier,
            "final_rsp": final_rsp,
            "score": int(payload.get("score") or context.get("score") or 1),
            "weight": float(payload.get("weight") or context.get("weight") or 1.0),
            "metadata": {
                "event_type": event_type,
                "score": int(payload.get("score") or context.get("score") or 1),
                "weight": float(payload.get("weight") or context.get("weight") or 1.0),
                "period_start": period_start,
                "source": "ghostnetwork",
            },
        }

    def create_reward_entry(self, reward_plan):
        reward_plan = reward_plan if isinstance(reward_plan, dict) else {}
        if not reward_plan.get("ok"):
            return {"ok": False, "status": "rejected", "reason": reward_plan.get("reason") or "not_eligible"}
        if reward_plan.get("status") == "exists":
            return {"ok": True, "status": "exists", "reward": reward_plan.get("reward"), "idempotent": True}

        contribution = self.contributions.record_contribution(
            cycle_id=reward_plan.get("cycle_id"),
            signal_id=reward_plan.get("signal_id"),
            player_id=reward_plan.get("player_id"),
            clan_code=reward_plan.get("clan_code"),
            profession_code=reward_plan.get("profession_code"),
            contribution_type=reward_plan.get("contribution_type"),
            part_id=reward_plan.get("part_id"),
            territory_id=reward_plan.get("territory_id"),
            operation_id=reward_plan.get("operation_id"),
            score=reward_plan.get("score"),
            weight=reward_plan.get("weight"),
            source_event_id=reward_plan.get("source_event_id"),
            metadata=reward_plan.get("metadata"),
        )
        reward = self.repository.insert_reward({
            "reward_key": reward_plan.get("reward_key"),
            "cycle_id": reward_plan.get("cycle_id"),
            "signal_id": reward_plan.get("signal_id"),
            "player_id": reward_plan.get("player_id"),
            "clan_code": reward_plan.get("clan_code"),
            "reward_type": reward_plan.get("reward_type"),
            "source_event_id": reward_plan.get("source_event_id"),
            "base_rsp": reward_plan.get("base_rsp"),
            "multiplier": reward_plan.get("multiplier"),
            "final_rsp": reward_plan.get("final_rsp"),
            "status": "pending" if int(reward_plan.get("final_rsp") or 0) > 0 else "rejected",
            "failure_reason": "" if int(reward_plan.get("final_rsp") or 0) > 0 else "zero_reward",
            "metadata": reward_plan.get("metadata"),
        })
        if not reward.get("idempotent"):
            try:
                self.repository.append_event(
                    "ghost.reward_pending",
                    cycle_id=reward["cycle_id"],
                    entity_id=reward["reward_id"],
                    player_id=reward.get("player_id") or "",
                    clan_code=reward.get("clan_code") or "",
                    audience_scope="internal",
                    dedupe_key=f"ghost:reward_pending:{reward['reward_key']}",
                    payload={"reward_id": reward["reward_id"], "reward_type": reward["reward_type"], "final_rsp": reward["final_rsp"]},
                )
            except Exception:
                pass
        return {"ok": True, "status": "created", "reward": reward, "contribution": contribution.get("contribution")}

    def apply_pending_reward(self, profile, reward_id=None, reward_key=None):
        profile = profile if isinstance(profile, dict) else {}
        reward = self.repository.get_reward(reward_id) if reward_id else self.repository.get_reward_by_key(reward_key)
        if not reward:
            return {"ok": False, "status": "missing_reward"}
        if reward.get("status") == "applied":
            return {"ok": True, "status": "already_applied", "reward": reward}
        if reward.get("status") != "pending":
            return {"ok": False, "status": reward.get("status"), "reward": reward}

        rsp = int(reward.get("final_rsp") or 0)
        profile["respect"] = int(profile.get("respect") or 0) + rsp
        stats = profile.setdefault("ghostnetwork_stats", {})
        stats["ghostnetwork_rsp_total"] = int(stats.get("ghostnetwork_rsp_total") or 0) + rsp
        stat_key = PROFILE_STAT_BY_REWARD.get(reward.get("reward_type"))
        if stat_key:
            stats[stat_key] = int(stats.get(stat_key) or 0) + 1
        history = profile.setdefault("ghostnetwork_reward_history", [])
        if reward["reward_key"] not in {item.get("reward_key") for item in history if isinstance(item, dict)}:
            history.append({
                "reward_key": reward["reward_key"],
                "reward_type": reward["reward_type"],
                "rsp": rsp,
                "source": "ghostnetwork",
            })

        applied = self.repository.update_reward_status(reward["reward_id"], "applied")
        clan_code = reward.get("clan_code") or ""
        reputation = None
        if clan_code:
            reputation = self.repository.increment_clan_reputation(
                clan_code,
                self.reputation_policy.increments_for_reward(reward),
                metadata={"reward_key": reward["reward_key"], "reward_type": reward["reward_type"]},
            )
            try:
                self.repository.append_event(
                    "ghost.clan_reputation_changed",
                    cycle_id=reward["cycle_id"],
                    entity_id=clan_code,
                    clan_code=clan_code,
                    audience_scope="internal",
                    dedupe_key=f"ghost:clan_reputation:{reward['reward_key']}",
                    payload={"clan_code": clan_code, "reward_key": reward["reward_key"]},
                )
            except Exception:
                pass
        try:
            self.repository.append_event(
                "ghost.reward_applied",
                cycle_id=reward["cycle_id"],
                entity_id=reward["reward_id"],
                player_id=reward.get("player_id") or "",
                clan_code=clan_code,
                audience_scope="internal",
                dedupe_key=f"ghost:reward_applied:{reward['reward_key']}",
                payload={"reward_id": reward["reward_id"], "final_rsp": rsp},
            )
            self.repository.append_event(
                "ghost.player_history_changed",
                cycle_id=reward["cycle_id"],
                entity_id=reward.get("player_id") or "",
                player_id=reward.get("player_id") or "",
                clan_code=clan_code,
                audience_scope="internal",
                dedupe_key=f"ghost:player_history:{reward['reward_key']}",
                payload={"reward_key": reward["reward_key"], "source": "ghostnetwork"},
            )
        except Exception:
            pass
        return {"ok": True, "status": "applied", "reward": applied, "rsp": rsp, "clan_reputation": reputation}

    def apply_pending_rewards(self, profile, player_id=None, cycle_id=None, limit=100):
        player_id = _clean(player_id or (profile or {}).get("username"))
        rewards = self.repository.list_pending_rewards(player_id=player_id or None, cycle_id=cycle_id, limit=limit)
        results = [self.apply_pending_reward(profile, reward_id=reward["reward_id"]) for reward in rewards]
        return {"ok": True, "count": len(results), "results": results}

    def get_player_reward_summary(self, player_id, cycle_id=None):
        return self.repository.get_player_reward_summary(player_id, cycle_id=cycle_id)

    def handle_event(self, event, profile=None, context=None, apply=False):
        plan = self.evaluate_event_reward(event, profile=profile, context=context)
        if not plan.get("ok"):
            return {"ok": False, "status": plan.get("status"), "reason": plan.get("reason"), "plan": plan}
        created = self.create_reward_entry(plan)
        applied = None
        if apply and created.get("reward") and not created.get("idempotent") and created.get("status") != "exists":
            applied = self.apply_pending_reward(profile or {}, reward_id=created["reward"]["reward_id"])
        return {"ok": True, "plan": plan, "created": created, "applied": applied}

    def reconcile_ghost_rewards(self, cycle_id=None, player_id=None, dry_run=True):
        cycle_id = _clean(cycle_id)
        player_id = _clean(player_id)
        contributions = (
            self.repository.list_player_contributions(player_id, cycle_id=cycle_id, limit=5000)
            if player_id
            else self.repository.list_cycle_contributions(cycle_id, limit=5000)
        )
        issues = []
        for contribution in contributions:
            source_event_id = contribution.get("source_event_id") or ""
            if not source_event_id:
                continue
            summary = self.repository.get_player_reward_summary(contribution.get("player_id"), cycle_id=contribution.get("cycle_id"))
            if contribution.get("contribution_type") not in summary.get("by_type", {}):
                issues.append({
                    "type": "contribution_without_reward",
                    "contribution_id": contribution["contribution_id"],
                    "source_event_id": source_event_id,
                })
        return {
            "ok": True,
            "dry_run": bool(dry_run),
            "cycle_id": cycle_id,
            "player_id": player_id,
            "issues": issues,
            "repair_supported": False,
        }
