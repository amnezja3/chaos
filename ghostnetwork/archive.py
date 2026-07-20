from __future__ import annotations

from collections import Counter, defaultdict

from .catalog import CATALOG_VERSION
from .repository import GhostNetworkRepository


ARCHIVE_VERSION = "ghostnetwork.archive.v1"

ACHIEVEMENT_DEFINITIONS = {
    "first_contact": "Odkryto czesc GhostNetworku.",
    "anchor": "Utrzymano wezel w cyklu GhostSignalu.",
    "module_online": "Aktywowano modul GhostNetworku.",
    "recovered_fragment": "Odzyskano fragment sieci.",
    "unbroken_node": "Wezel przetrwal do transmisji.",
    "defense_line": "Obroniono strategiczna czesc.",
    "signal_operator": "Uczestnictwo w transmisji GhostSignalu.",
    "final_circuit": "Domknieto finalny obwod sygnalu.",
    "ghostsystem_veteran": "Udzial w zakonczonym cyklu GhostSystemu.",
}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _safe_int(value, default=0):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _node_public(node):
    node = node if isinstance(node, dict) else {}
    return {
        "historical_node_id": node.get("historical_node_id") or "",
        "part_id": node.get("part_id") or "",
        "part_code": node.get("part_code") or "",
        "latitude": node.get("latitude"),
        "longitude": node.get("longitude"),
        "clan_code": node.get("clan_code") or "",
        "machine_code": node.get("machine_code") or "",
        "profession_code": node.get("profession_code") or "",
        "status": node.get("status") or "spent",
        "active_since": node.get("active_since") or "",
        "active_until": node.get("active_until") or "",
        "defense_count": _safe_int(node.get("defense_count")),
    }


class GhostArchiveService:
    """Read model for finished GhostNetwork cycles.

    The archive is not a second state store. It only projects already persisted
    signals, lock snapshots, historical nodes and ledgers into lightweight read
    contracts for future UI, diagnostics and endgame readiness checks.
    """

    def __init__(self, repository=None):
        self.repository = repository or GhostNetworkRepository()

    def finalize_signal_archive(self, signal_id):
        signal = self.repository.get_signal(signal_id)
        if not signal:
            return {"ok": False, "error": "signal_not_found", "signal_id": _clean(signal_id)}
        nodes = self.repository.list_historical_nodes_for_signal(signal["signal_id"])
        rewards = self.repository.list_rewards(signal_id=signal["signal_id"], limit=5000)
        contributions = self.repository.list_contributions(signal_id=signal["signal_id"], limit=5000)
        awarded = []
        for item in self._achievement_candidates(signal, nodes, rewards, contributions):
            achievement = self.repository.insert_achievement(item)
            if achievement:
                awarded.append(achievement)
        return {
            "ok": True,
            "signal_id": signal["signal_id"],
            "archive_version": ARCHIVE_VERSION,
            "achievements_awarded": len(awarded),
            "achievements": awarded,
        }

    def _achievement_candidates(self, signal, nodes, rewards, contributions):
        signal_id = signal.get("signal_id") or ""
        cycle_id = signal.get("cycle_id") or ""
        for node in nodes:
            part_id = node.get("part_id") or node.get("historical_node_id") or ""
            discovered_by = _clean(node.get("discovered_by"))
            owner_id = _clean(node.get("owner_id"))
            clan_code = _clean(node.get("clan_code"))
            if discovered_by:
                yield self._achievement("first_contact", discovered_by, clan_code, cycle_id, signal_id, f"{part_id}:discover")
            if owner_id:
                yield self._achievement("anchor", owner_id, clan_code, cycle_id, signal_id, f"{part_id}:anchor")
                yield self._achievement("unbroken_node", owner_id, clan_code, cycle_id, signal_id, f"{part_id}:held")
            if _safe_int(node.get("defense_count")) > 0 and owner_id:
                yield self._achievement("defense_line", owner_id, clan_code, cycle_id, signal_id, f"{part_id}:defense")
        for contribution in contributions:
            player_id = _clean(contribution.get("player_id"))
            if not player_id:
                continue
            contribution_type = _clean(contribution.get("contribution_type"))
            source = contribution.get("contribution_id") or contribution.get("part_id") or signal_id
            code = {
                "activation": "module_online",
                "part_activated": "module_online",
                "recovery": "recovered_fragment",
                "defense": "defense_line",
            }.get(contribution_type)
            if code:
                yield self._achievement(code, player_id, contribution.get("clan_code"), cycle_id, signal_id, source)
        for reward in rewards:
            player_id = _clean(reward.get("player_id"))
            if not player_id:
                continue
            source = reward.get("reward_id") or reward.get("reward_key") or signal_id
            yield self._achievement("ghostsystem_veteran", player_id, reward.get("clan_code"), cycle_id, signal_id, source)
            if reward.get("reward_type") in {"closure", "ghost_signal_closer"}:
                yield self._achievement("signal_operator", player_id, reward.get("clan_code"), cycle_id, signal_id, source)
                yield self._achievement("final_circuit", player_id, reward.get("clan_code"), cycle_id, signal_id, source)

    def _achievement(self, code, player_id, clan_code, cycle_id, signal_id, source_id):
        source_id = _clean(source_id, signal_id)
        return {
            "player_id": _clean(player_id),
            "clan_code": _clean(clan_code),
            "achievement_code": code,
            "cycle_id": _clean(cycle_id),
            "signal_id": _clean(signal_id),
            "source_id": source_id,
            "metadata": {
                "archive_version": ARCHIVE_VERSION,
                "description": ACHIEVEMENT_DEFINITIONS.get(code, ""),
            },
            "dedupe_key": f"achievement:{_clean(player_id)}:{code}:{source_id}",
        }

    def list_signals(self, limit=50):
        return [
            self._signal_summary(
                signal,
                rewards=self.repository.list_rewards(signal_id=signal.get("signal_id"), limit=5000),
            )
            for signal in self.repository.list_signals(limit=limit)
        ]

    def get_signal_detail(self, signal_id, include_private=False):
        signal = self.repository.get_signal(signal_id)
        if not signal:
            return {"ok": False, "error": "signal_not_found", "signal_id": _clean(signal_id)}
        nodes = self.repository.list_historical_nodes_for_signal(signal["signal_id"])
        rewards = self.repository.list_rewards(signal_id=signal["signal_id"], limit=5000)
        contributions = self.repository.list_contributions(signal_id=signal["signal_id"], limit=5000)
        lock = self.repository.get_cycle_lock_snapshot(signal["cycle_id"])
        return {
            "ok": True,
            "archive_version": ARCHIVE_VERSION,
            "signal": self._signal_summary(signal, nodes=nodes, rewards=rewards),
            "lock_snapshot": self._lock_summary(lock),
            "historical_nodes": [_node_public(node) for node in nodes],
            "participation": self._participation_summary(nodes, rewards, contributions),
            "rewards": self._reward_summary(rewards),
            "achievements": self.repository.list_achievements(signal_id=signal["signal_id"], limit=1000),
            "private": self._private_signal_detail(nodes, rewards, contributions) if include_private else {},
        }

    def _signal_summary(self, signal, nodes=None, rewards=None):
        signal = signal if isinstance(signal, dict) else {}
        nodes = nodes if nodes is not None else self.repository.list_historical_nodes_for_signal(signal.get("signal_id"))
        rewards = rewards if rewards is not None else []
        clans = sorted({node.get("clan_code") for node in nodes if node.get("clan_code")})
        participants = sorted({
            player
            for player in [
                *(node.get("discovered_by") for node in nodes),
                *(node.get("owner_id") for node in nodes),
                *(reward.get("player_id") for reward in rewards),
            ]
            if player
        })
        return {
            "signal_id": signal.get("signal_id") or "",
            "signal_number": _safe_int(signal.get("signal_number")),
            "cycle_id": signal.get("cycle_id") or "",
            "source_version": _safe_int(signal.get("source_version")),
            "next_version": _safe_int(signal.get("next_version")),
            "sent_at": signal.get("sent_at") or signal.get("created_at") or "",
            "initial_status": signal.get("status") or "",
            "outcome": signal.get("outcome") or "pending",
            "integrity": signal.get("integrity"),
            "recipient": signal.get("recipient") or "",
            "clan_participation": clans,
            "participants_count": len(participants),
            "historical_nodes_count": len(nodes),
            "catalog_version": CATALOG_VERSION,
            "ghostsystem_version": _safe_int(signal.get("target_year"), 2108),
            "signal_checksum": signal.get("signal_checksum") or "",
        }

    def _lock_summary(self, lock):
        lock = lock if isinstance(lock, dict) else {}
        snapshot = lock.get("snapshot") if isinstance(lock.get("snapshot"), dict) else {}
        parts = snapshot.get("parts") if isinstance(snapshot.get("parts"), list) else []
        return {
            "lock_snapshot_id": lock.get("lock_snapshot_id") or "",
            "cycle_id": lock.get("cycle_id") or "",
            "locked_at": lock.get("locked_at") or "",
            "closing_part_id": lock.get("closing_part_id") or "",
            "snapshot_checksum": lock.get("snapshot_checksum") or "",
            "parts_count": len(parts),
        }

    def _participation_summary(self, nodes, rewards, contributions):
        players = Counter()
        clans = Counter()
        for node in nodes:
            for player in (node.get("discovered_by"), node.get("owner_id")):
                if player:
                    players[player] += 1
            if node.get("clan_code"):
                clans[node["clan_code"]] += 1
        for reward in rewards:
            if reward.get("player_id"):
                players[reward["player_id"]] += 1
            if reward.get("clan_code"):
                clans[reward["clan_code"]] += 1
        by_type = Counter(contribution.get("contribution_type") or "unknown" for contribution in contributions)
        return {
            "players": dict(players),
            "clans": dict(clans),
            "contribution_types": dict(by_type),
        }

    def _reward_summary(self, rewards):
        by_type = defaultdict(lambda: {"count": 0, "rsp": 0})
        total_rsp = 0
        for reward in rewards:
            reward_type = reward.get("reward_type") or "unknown"
            value = _safe_int(reward.get("final_rsp") or reward.get("rsp_amount"))
            by_type[reward_type]["count"] += 1
            by_type[reward_type]["rsp"] += value
            total_rsp += value
        return {"count": len(rewards), "total_rsp": total_rsp, "by_type": dict(by_type)}

    def _private_signal_detail(self, nodes, rewards, contributions):
        return {
            "discoverers": sorted({node.get("discovered_by") for node in nodes if node.get("discovered_by")}),
            "owners": sorted({node.get("owner_id") for node in nodes if node.get("owner_id")}),
            "reward_players": sorted({reward.get("player_id") for reward in rewards if reward.get("player_id")}),
            "contribution_count": len(contributions),
        }

    def get_player_history(self, player_id, limit=50):
        player_id = _clean(player_id)
        nodes = self.repository.list_historical_nodes(player_id=player_id, limit=5000)
        rewards = self.repository.list_rewards(player_id=player_id, limit=5000)
        contributions = self.repository.list_contributions(player_id=player_id, limit=5000)
        achievements = self.repository.list_achievements(player_id=player_id, limit=5000)
        signals = sorted({
            item.get("signal_id")
            for item in [*nodes, *rewards, *contributions, *achievements]
            if item.get("signal_id")
        }, reverse=True)[:limit]
        contribution_types = Counter(item.get("contribution_type") or "unknown" for item in contributions)
        return {
            "ok": True,
            "archive_version": ARCHIVE_VERSION,
            "player_id": player_id,
            "signals": signals,
            "signals_count": len(signals),
            "parts_discovered": sum(1 for node in nodes if node.get("discovered_by") == player_id),
            "nodes_held_at_transmission": sum(1 for node in nodes if node.get("owner_id") == player_id),
            "modules_activated": contribution_types.get("activation", 0) + contribution_types.get("part_activated", 0),
            "recoveries": contribution_types.get("recovery", 0),
            "defenses": contribution_types.get("defense", 0),
            "ghostnetwork_rsp": sum(_safe_int(reward.get("final_rsp") or reward.get("rsp_amount")) for reward in rewards),
            "achievements": achievements,
        }

    def get_clan_history(self, limit=100):
        rows = self.repository.list_clan_reputation(limit=limit)
        return {
            "ok": True,
            "archive_version": ARCHIVE_VERSION,
            "clans": [
                {
                    **row,
                    "active_node_hours": round(_safe_int(row.get("active_node_seconds")) / 3600, 2),
                }
                for row in rows
            ],
        }

    def get_historical_map_layer(self, signal_id=None, limit=200):
        nodes = self.repository.list_historical_nodes(signal_id=signal_id, limit=limit)
        return {
            "ok": True,
            "archive_version": ARCHIVE_VERSION,
            "signal_id": _clean(signal_id),
            "nodes": [_node_public(node) for node in nodes],
        }

    def build_readiness_report(self):
        health = self.repository.health_check()
        signals = self.repository.list_signals(limit=25)
        latest = signals[0] if signals else None
        latest_detail = self.get_signal_detail(latest["signal_id"]) if latest else {"ok": True}
        return {
            "ok": bool(health.get("ok")) and bool(latest_detail.get("ok", True)),
            "archive_version": ARCHIVE_VERSION,
            "health": health,
            "latest_signal": self._signal_summary(latest) if latest else None,
            "latest_signal_detail_ok": bool(latest_detail.get("ok", True)),
            "signals_archived": len(signals),
            "achievement_codes": sorted(ACHIEVEMENT_DEFINITIONS.keys()),
            "flags": {
                "archive_read_only": True,
                "suite_ui_enabled": False,
                "ollama_control_enabled": False,
                "endgame_ready": bool(health.get("ok")) and latest is not None,
            },
        }
