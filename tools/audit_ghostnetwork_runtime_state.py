"""Read-only GhostNetwork audit probe for the configured local runtime."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from database import UserStore
from ghostnetwork import GhostNetworkService


def build_discovery_audit(service, cycle, user_store=None):
    if not cycle:
        return {"ok": True, "count": 0, "items": [], "errors": []}
    repository = service.repository
    cycle_id = cycle["cycle_id"]
    parts = repository.list_parts(cycle_id)
    events = repository.list_events(cycle_id, limit=5000)
    contributions = repository.list_contributions(cycle_id=cycle_id, limit=5000)
    rewards = repository.list_rewards(cycle_id=cycle_id, limit=5000)
    effects = repository.list_capture_effects(limit=5000)
    discovered = [part for part in parts if part.get("discovered_at")]
    errors = []
    target_counts = {}
    for part in discovered:
        target_id = part.get("target_id") or ""
        if target_id:
            target_counts[target_id] = target_counts.get(target_id, 0) + 1

    items = []
    for part in discovered:
        part_id = part.get("part_id") or ""
        player_id = part.get("discovered_by") or ""
        discovery_events = [
            event for event in events
            if event.get("event_type") == "ghost.part_discovered"
            and event.get("part_id") == part_id
        ]
        part_contributions = [
            item for item in contributions
            if item.get("contribution_type") == "part_discovered"
            and item.get("part_id") == part_id
            and item.get("player_id") == player_id
        ]
        reward_key = service.rewards.reward_key(
            cycle_id, "part_discovered", player_id=player_id, part_id=part_id
        )
        part_rewards = [item for item in rewards if item.get("reward_key") == reward_key]
        matching_effects = [
            effect for effect in effects
            if effect.get("cycle_id") == cycle_id
            and effect.get("player_id") == player_id
            and effect.get("target_id") == (part.get("target_id") or "")
        ]
        profile = user_store.get_profile(player_id) if user_store and player_id else {}
        history = (profile or {}).get("ghostnetwork_reward_history") or []
        history_count = sum(
            1 for item in history
            if isinstance(item, dict) and item.get("reward_key") == reward_key
        )
        item_errors = []
        if part.get("cycle_id") != cycle_id:
            item_errors.append("cycle_mismatch")
        if part.get("status") not in {"public", "contained", "active", "consumed"}:
            item_errors.append("invalid_discovered_lifecycle")
        if target_counts.get(part.get("target_id") or "", 0) != 1:
            item_errors.append("duplicate_discovered_target")
        if len(discovery_events) != 1:
            item_errors.append("discovery_event_count_not_one")
        if len(part_contributions) != 1:
            item_errors.append("contribution_count_not_one")
        if len(part_rewards) != 1:
            item_errors.append("reward_count_not_one")
        elif part_rewards[0].get("status") != "applied":
            item_errors.append("reward_not_applied")
        if history_count != 1:
            item_errors.append("profile_history_count_not_one")
        if matching_effects and sum(1 for effect in matching_effects if effect.get("status") == "applied") != 1:
            item_errors.append("capture_effect_applied_count_not_one")
        errors.extend(f"{part_id}:{error}" for error in item_errors)
        items.append({
            "part_id": part_id,
            "part_code": part.get("part_code") or "",
            "cycle_id": part.get("cycle_id") or "",
            "status": part.get("status") or "",
            "target_id": part.get("target_id") or "",
            "player_id": player_id,
            "discovered_at": part.get("discovered_at") or "",
            "discovery_events": len(discovery_events),
            "contributions": len(part_contributions),
            "rewards": len(part_rewards),
            "reward_status": (part_rewards[0].get("status") if len(part_rewards) == 1 else ""),
            "profile_history": history_count,
            "capture_effects": len(matching_effects),
            "applied_capture_effects": sum(
                1 for effect in matching_effects if effect.get("status") == "applied"
            ),
            "errors": item_errors,
        })
    return {"ok": not errors, "count": len(items), "items": items, "errors": errors}


def main():
    service = GhostNetworkService()
    cycle = service.get_active_cycle()
    snapshot = (
        service.repository.build_internal_snapshot(cycle["cycle_id"])
        if cycle else {}
    )
    payload = {
        "drops_enabled": config.GHOSTNETWORK_DROPS_ENABLED,
        "drop_chance": config.GHOSTNETWORK_DROP_CHANCE,
        "reservation_ttl_seconds": config.GHOSTNETWORK_RESERVATION_TTL_SECONDS,
        "min_part_distance_km": config.GHOSTNETWORK_MIN_PART_DISTANCE_KM,
        "cycle": cycle,
        "parts_summary": (
            service.cycles.get_parts_summary(cycle["cycle_id"])
            if cycle else None
        ),
        "parts_count": len(snapshot.get("parts", [])),
        "active_reservations": len(snapshot.get("active_reservations", [])),
        "discoveries": build_discovery_audit(service, cycle, user_store=UserStore()),
        "health": service.health_check(),
        "runtime_readiness": service.get_runtime_readiness(),
    }
    print(json.dumps(payload, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
