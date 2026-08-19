"""Operator CLI for GhostNetwork runtime readiness and cycle bootstrap."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DB_PATH
from database import TerritoryStore, TerritoryTargetOwnershipStore, UserStore
from ghostnetwork import GhostNetworkService, GhostRuntimeCoordinator


def reconcile_reward_history(service, users, apply=False):
    cycle = service.get_active_cycle()
    rewards = service.repository.list_rewards(
        cycle_id=(cycle or {}).get("cycle_id") or "", status="applied", limit=5000
    ) if cycle else []
    missing = []
    repaired = []
    profiles = {}
    for reward in rewards:
        player_id = str(reward.get("player_id") or "").strip()
        reward_key = str(reward.get("reward_key") or "").strip()
        if not player_id or not reward_key:
            continue
        profile = profiles.get(player_id)
        if profile is None:
            profile = users.get_profile(player_id) or {}
            profiles[player_id] = profile
        history = profile.get("ghostnetwork_reward_history") or []
        if reward_key in {
            item.get("reward_key") for item in history if isinstance(item, dict)
        }:
            continue
        missing.append({"player_id": player_id, "reward_key": reward_key})
        if apply and profile:
            profile.setdefault("ghostnetwork_reward_history", []).append({
                "reward_key": reward_key,
                "reward_type": reward.get("reward_type") or "",
                "rsp": int(reward.get("final_rsp") or 0),
                "source": "ghostnetwork",
            })
            repaired.append({"player_id": player_id, "reward_key": reward_key})
    if apply:
        for player_id in {item["player_id"] for item in repaired}:
            users.save_profile(profiles[player_id])
    return {
        "ok": True,
        "dry_run": not apply,
        "missing": missing,
        "missing_count": len(missing),
        "repaired": repaired,
        "repaired_count": len(repaired),
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "verify", "bootstrap", "reconcile", "drain"))
    parser.add_argument("--db-path", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--apply", action="store_true", help="Apply bootstrap mutation")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default output is also JSON)")
    return parser


def execute(args):
    service = GhostNetworkService(db_path=args.db_path)
    before = service.get_runtime_readiness()
    if args.command in {"status", "verify"}:
        return before, 0 if before["ready"] else 2
    if args.command in {"reconcile", "drain"}:
        territory = TerritoryStore(args.db_path)
        ownership = TerritoryTargetOwnershipStore(args.db_path)
        users = UserStore(args.db_path)

        def captured_reader(player_id, target_id):
            canonical = ownership.get(target_id)
            if canonical and canonical.get("owner_username") == player_id:
                return dict(canonical.get("target") or {})
            for target in territory.list_captured_targets(player_id):
                if str(target.get("target_id") or "") == str(target_id or ""):
                    return target
            return None

        coordinator = GhostRuntimeCoordinator(
            service=service,
            captured_target_reader=captured_reader,
            profile_loader=lambda player_id: users.get_profile(player_id) or {},
            profile_saver=users.save_profile,
        )
        if args.command == "reconcile" and not args.apply:
            reservations = service.repository.list_active_reservations(
                (service.get_active_cycle() or {}).get("cycle_id"), limit=1000
            )
            return {
                "ok": True, "dry_run": True,
                "active_reservations": len(reservations),
                "effect_summary": service.repository.get_capture_effect_summary(),
                "reward_history": reconcile_reward_history(service, users, apply=False),
            }, 0
        if args.command == "reconcile":
            result = coordinator.reconcile_missing_effects(limit=1000)
            result["reward_history"] = reconcile_reward_history(service, users, apply=True)
        else:
            result = coordinator.drain(limit=1000, reconcile=True) if args.apply else {
                "ok": True, "dry_run": True,
                "effect_summary": service.repository.get_capture_effect_summary(),
            }
        return result, 0 if result.get("ok") else 2
    if not args.apply:
        return {
            "ok": True,
            "applied": False,
            "dry_run": True,
            "action": "validate_existing" if before["active_cycle_id"] else "create_active_cycle",
            "readiness": before,
        }, 0
    result = service.ensure_active_cycle()
    after = service.get_runtime_readiness()
    return {
        "ok": bool(after["ready"]),
        "applied": True,
        "dry_run": False,
        "created": bool(result.get("created")),
        "active_cycle_id": after["active_cycle_id"],
        "readiness": after,
    }, 0 if after["ready"] else 2


def main(argv=None):
    args = build_parser().parse_args(argv)
    payload, exit_code = execute(args)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
