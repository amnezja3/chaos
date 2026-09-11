from __future__ import annotations

import copy
import hashlib
import json
import logging
from collections import defaultdict

from config import GHOSTNETWORK_RANKING_POLICY
from database import db_connect


RANKING_CONTRACT = "ghostsignal-ranking-v2"


def _clean(value):
    return str(value or "").strip()


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _checksum(payload):
    clean = copy.deepcopy(payload if isinstance(payload, dict) else {})
    clean.pop("snapshot_checksum", None)
    encoded = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def allocate_pool(pool, basis):
    """Largest-remainder allocation with a stable lexical tie-break."""
    pool = max(0, _int(pool))
    positive = {
        _clean(key): max(0.0, _float(value))
        for key, value in (basis or {}).items()
        if _clean(key) and _float(value) > 0
    }
    total = sum(positive.values())
    if not pool or total <= 0:
        return {key: 0 for key in sorted(positive)}
    exact = {key: pool * value / total for key, value in positive.items()}
    awarded = {key: int(value) for key, value in exact.items()}
    remaining = pool - sum(awarded.values())
    order = sorted(positive, key=lambda key: (-(exact[key] - awarded[key]), key))
    for key in order[:remaining]:
        awarded[key] += 1
    return awarded


class GhostSignalRankingService:
    """Immutable per-signal ranking and rebuild-only all-time projection."""

    def __init__(self, repository, policy=None):
        self.repository = repository
        self.policy = copy.deepcopy(policy or GHOSTNETWORK_RANKING_POLICY)

    def _identity_snapshots(self, player_ids):
        player_ids = sorted({_clean(value) for value in player_ids if _clean(value)})
        snapshots = {
            player_id: {
                "username_snapshot": player_id,
                "display_alias_snapshot": player_id,
                "clan_id_snapshot": "",
                "clan_name_snapshot": "",
            }
            for player_id in player_ids
        }
        if not player_ids:
            return snapshots
        placeholders = ",".join("?" for _ in player_ids)
        try:
            with db_connect(self.repository.db_path) as conn:
                known = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_identity_projection'"
                ).fetchone()
                if not known:
                    return snapshots
                rows = conn.execute(
                    "SELECT username, display_alias, clan_code FROM user_identity_projection "
                    f"WHERE username IN ({placeholders})",
                    player_ids,
                ).fetchall()
        except Exception:
            return snapshots
        for row in rows:
            player_id = _clean(row["username"])
            clan = _clean(row["clan_code"])
            snapshots[player_id] = {
                "username_snapshot": player_id,
                "display_alias_snapshot": _clean(row["display_alias"]) or player_id,
                "clan_id_snapshot": clan,
                "clan_name_snapshot": clan,
            }
        return snapshots

    @staticmethod
    def _new_player(player_id):
        return {
            "user_id": player_id,
            "username_snapshot": player_id,
            "display_alias_snapshot": player_id,
            "clan_id_snapshot": "",
            "clan_name_snapshot": "",
            "rsp_signal": 0,
            "nodes_held": 0,
            "territories_consumed": 0,
            "territory_area_consumed": 0.0,
            "closer": False,
            "conflict_metrics": {"actions": 0, "offensive": 0, "defensive": 0, "score": 0},
        }

    def build_snapshot(self, signal_id):
        signal = self.repository.get_signal(signal_id)
        if not signal:
            return {"ok": False, "error": "signal_not_found", "signal_id": _clean(signal_id)}
        lock = self.repository.get_cycle_lock_snapshot(signal["cycle_id"])
        if not lock:
            return {"ok": False, "error": "lock_snapshot_missing", "signal_id": signal["signal_id"]}
        lock_payload = copy.deepcopy(lock.get("snapshot") or {})
        show = self.repository.get_signal_show_for_signal(signal["signal_id"]) or {}
        rewards = self.repository.list_rewards(signal_id=signal["signal_id"], limit=5000)
        territories = self.repository.list_signal_territory_consumptions(signal["signal_id"], limit=5000)
        parts = copy.deepcopy(lock_payload.get("parts") or [])
        conflicts = copy.deepcopy(lock_payload.get("conflicts") or [])
        conflict_actions = copy.deepcopy(lock_payload.get("conflict_actions") or [])
        closing = lock_payload.get("closing") or {}

        player_ids = set()
        for part in parts:
            player_ids.update(filter(None, (_clean(part.get("territory_owner_id")), _clean(part.get("discovered_by")))))
        for reward in rewards:
            if _clean(reward.get("player_id")):
                player_ids.add(_clean(reward.get("player_id")))
        for action in conflict_actions:
            if _clean(action.get("player_id")):
                player_ids.add(_clean(action.get("player_id")))
        if _clean(closing.get("closing_player_id")):
            player_ids.add(_clean(closing.get("closing_player_id")))
        identities = self._identity_snapshots(player_ids)
        players = {player_id: self._new_player(player_id) for player_id in sorted(player_ids)}

        def set_clan(player_id, clan_code):
            player_id, clan_code = _clean(player_id), _clean(clan_code)
            if not player_id or player_id not in players or not clan_code:
                return
            # Endgame lock/ledger membership is canonical for this signal;
            # the live identity projection is used only as a display fallback.
            players[player_id]["clan_id_snapshot"] = clan_code
            players[player_id]["clan_name_snapshot"] = clan_code

        for player_id, identity in identities.items():
            players[player_id].update(identity)
        for part in parts:
            owner = _clean(part.get("territory_owner_id") or part.get("discovered_by"))
            if owner and owner in players:
                players[owner]["nodes_held"] += 1
                set_clan(owner, part.get("territory_clan") or part.get("clan_code"))
        for territory in territories:
            owner = _clean(territory.get("owner_id"))
            if owner and owner in players:
                players[owner]["territories_consumed"] += 1
                players[owner]["territory_area_consumed"] += max(0.0, _float(territory.get("area_size")))
                set_clan(owner, territory.get("clan_code"))
        for reward in rewards:
            player_id = _clean(reward.get("player_id"))
            if player_id and player_id in players:
                players[player_id]["rsp_signal"] += max(0, _int(reward.get("final_rsp") or reward.get("rsp_amount")))
                set_clan(player_id, reward.get("clan_code"))
        closer_id = _clean(closing.get("closing_player_id"))
        if closer_id in players:
            players[closer_id]["closer"] = True
            set_clan(closer_id, closing.get("closing_clan_code"))
        for action in conflict_actions:
            player_id = _clean(action.get("player_id"))
            if player_id not in players:
                continue
            side = _clean(action.get("side"))
            score = max(0, _int(action.get("mechanical_value")))
            metrics = players[player_id]["conflict_metrics"]
            metrics["actions"] += 1
            metrics["score"] += score
            if side in {"offensive", "defensive"}:
                metrics[side] += score
            set_clan(player_id, action.get("clan_code"))

        clans = defaultdict(lambda: {
            "clan_id": "", "clan_name_snapshot": "", "member_count_participating": 0,
            "nodes_held": 0, "territories_consumed": 0, "territory_area_consumed": 0.0,
            "rsp_members_total": 0, "closer_count": 0,
            "conflict_metrics": {"actions": 0, "offensive": 0, "defensive": 0, "score": 0},
            "score_breakdown": {}, "clan_ghost_score": 0,
        })
        for player in players.values():
            clan_id = _clean(player.get("clan_id_snapshot")) or "unaffiliated"
            clan = clans[clan_id]
            clan["clan_id"] = clan_id
            clan["clan_name_snapshot"] = _clean(player.get("clan_name_snapshot")) or clan_id
            clan["member_count_participating"] += 1
            clan["nodes_held"] += player["nodes_held"]
            clan["territories_consumed"] += player["territories_consumed"]
            clan["territory_area_consumed"] += player["territory_area_consumed"]
            clan["rsp_members_total"] += player["rsp_signal"]
            clan["closer_count"] += int(player["closer"])
            for key in ("actions", "offensive", "defensive", "score"):
                clan["conflict_metrics"][key] += player["conflict_metrics"][key]

        weights = copy.deepcopy(self.policy.get("weights") or {})
        bases = {
            "node_control": {key: value["nodes_held"] for key, value in clans.items()},
            "territory_contribution": {
                key: value["territory_area_consumed"] for key, value in clans.items()
            },
            "conflict_contribution": {
                key: value["conflict_metrics"]["score"] for key, value in clans.items()
            },
            "signal_closer": {key: value["closer_count"] for key, value in clans.items()},
        }
        if not any(bases["territory_contribution"].values()):
            bases["territory_contribution"] = {
                key: value["territories_consumed"] for key, value in clans.items()
            }
        allocations = {
            category: allocate_pool(weights.get(category), basis)
            for category, basis in bases.items()
        }
        for clan_id, clan in clans.items():
            clan["territory_area_consumed"] = round(clan["territory_area_consumed"], 6)
            clan["score_breakdown"] = {
                category: allocation.get(clan_id, 0)
                for category, allocation in allocations.items()
            }
            clan["clan_ghost_score"] = sum(clan["score_breakdown"].values())

        player_rows = sorted(players.values(), key=lambda item: (
            -item["rsp_signal"], -item["nodes_held"], -item["territories_consumed"], item["user_id"]
        ))
        for index, player in enumerate(player_rows, 1):
            player["territory_area_consumed"] = round(player["territory_area_consumed"], 6)
            player["rank"] = index
        clan_rows = sorted(clans.values(), key=lambda item: (
            -item["clan_ghost_score"], -item["nodes_held"], item["clan_id"]
        ))
        for index, clan in enumerate(clan_rows, 1):
            clan["rank"] = index

        snapshot = {
            "contract": RANKING_CONTRACT,
            "signal_id": signal["signal_id"],
            "signal_number": _int(signal.get("signal_number")),
            "cycle_id": signal["cycle_id"],
            "system_version_from": _int(signal.get("source_version")),
            "system_version_to": _int(signal.get("next_version")),
            "sent_at": signal.get("sent_at") or signal.get("created_at") or "",
            "show_started_at": show.get("show_started_at") or "",
            "show_ended_at": show.get("show_ends_at") or "",
            "players": player_rows,
            "clans": clan_rows,
            "territories": copy.deepcopy(territories),
            "parts": parts,
            "conflicts": conflicts,
            "rewards": copy.deepcopy(rewards),
            "score_policy": {"policy_version": self.policy.get("policy_version"), "weights": weights},
            "snapshot_schema": _int(self.policy.get("snapshot_schema")) or 2,
        }
        snapshot["snapshot_checksum"] = _checksum(snapshot)
        return {"ok": True, "snapshot": snapshot, "snapshot_checksum": snapshot["snapshot_checksum"]}

    def finalize(self, signal_id):
        existing = self.repository.get_signal_ranking(signal_id)
        if existing:
            valid = self.validate(existing)
            if valid["valid"]:
                self._prepare_show_scene(existing)
            return {"ok": valid["valid"], "ranking": existing, "validation": valid, "idempotent": True}
        built = self.build_snapshot(signal_id)
        if not built.get("ok"):
            return built
        snapshot = built["snapshot"]
        ranking = self.repository.create_signal_ranking({
            "ranking_id": "ghost_ranking_" + hashlib.sha1(signal_id.encode("utf-8")).hexdigest()[:20],
            "signal_id": snapshot["signal_id"],
            "cycle_id": snapshot["cycle_id"],
            "signal_number": snapshot["signal_number"],
            "snapshot_schema": snapshot["snapshot_schema"],
            "snapshot_checksum": snapshot["snapshot_checksum"],
            "snapshot": snapshot,
        })
        valid = self.validate(ranking)
        if valid["valid"]:
            self._prepare_show_scene(ranking)
        return {"ok": valid["valid"], "ranking": ranking, "validation": valid, "idempotent": False}

    def _prepare_show_scene(self, ranking):
        try:
            self._store_show_scene(ranking)
        except Exception as exc:
            # Presentation must never become another endgame/restart gate.
            logging.getLogger(__name__).warning("Show settlement projection deferred: %s", type(exc).__name__)

    def _store_show_scene(self, ranking):
        show = self.repository.get_signal_show_for_signal(ranking["signal_id"])
        if not show or (show.get("scene_snapshot") or {}).get("settlement"):
            return
        projection = self.build_show_scene(ranking)
        self.repository.store_show_settlement_scene(ranking["signal_id"], projection)

    def build_show_scene(self, ranking):
        """Read-only presentation preparation shared with the historical preview."""
        from .show_manifest import prepare_settlement_scene
        publications = self.repository.list_show_publication_excerpts(
            ranking["cycle_id"], ranking.get("created_at") or self.repository.now())
        snapshot = ranking.get("snapshot") or {}
        references = {str(row.get("conflict_id") or row.get("source_conflict_id") or "")
                      for key in ("parts", "conflicts", "territories") for row in snapshot.get(key) or []}
        references.discard("")
        production = self.repository.list_endgame_production_conflicts(sorted(references), limit=500) if references else []
        cutoff = ranking.get("created_at") or self.repository.now()
        production = [row for row in production if row.get("conflict_id") in references
                      and row.get("status") in {"resolved", "closed"}
                      and (row.get("resolved_at") or row.get("closed_at"))
                      and (row.get("resolved_at") or row.get("closed_at")) <= cutoff]
        return prepare_settlement_scene(ranking, publications, production)

    def validate(self, ranking):
        ranking = ranking if isinstance(ranking, dict) else {}
        snapshot = ranking.get("snapshot") if isinstance(ranking.get("snapshot"), dict) else {}
        expected = _checksum(snapshot)
        actual = _clean(ranking.get("snapshot_checksum"))
        embedded = _clean(snapshot.get("snapshot_checksum"))
        reasons = []
        if not snapshot:
            reasons.append("ranking_snapshot_missing")
        if expected != actual or embedded != actual:
            reasons.append("ranking_checksum_mismatch")
        if _int(snapshot.get("snapshot_schema")) != _int(ranking.get("snapshot_schema")):
            reasons.append("ranking_schema_mismatch")
        return {"valid": not reasons, "reasons": reasons, "expected_checksum": expected}

    @staticmethod
    def public_snapshot(ranking):
        ranking = ranking if isinstance(ranking, dict) else {}
        snapshot = ranking.get("snapshot") if isinstance(ranking.get("snapshot"), dict) else {}
        return {
            "ranking_id": ranking.get("ranking_id") or "",
            "signal_id": ranking.get("signal_id") or "",
            "signal_number": _int(ranking.get("signal_number")),
            "snapshot_schema": _int(ranking.get("snapshot_schema")),
            "snapshot_checksum": ranking.get("snapshot_checksum") or "",
            "system_version_from": snapshot.get("system_version_from"),
            "system_version_to": snapshot.get("system_version_to"),
            "sent_at": snapshot.get("sent_at") or "",
            "show_started_at": snapshot.get("show_started_at") or "",
            "show_ended_at": snapshot.get("show_ended_at") or "",
            "players": copy.deepcopy(snapshot.get("players") or []),
            "clans": copy.deepcopy(snapshot.get("clans") or []),
            "score_policy": copy.deepcopy(snapshot.get("score_policy") or {}),
        }

    def list_public(self, limit=100):
        return [self.public_snapshot(item) for item in self.repository.list_signal_rankings(limit=limit)]

    def all_time(self):
        rankings = self.repository.list_signal_rankings(limit=1000)
        players = defaultdict(lambda: {
            "user_id": "", "username_snapshot": "", "display_alias_snapshot": "",
            "signals_participated": 0,
            "signals_closed": 0, "nodes_held_total": 0, "territories_consumed_total": 0,
            "territory_area_consumed_total": 0.0, "ghostnetwork_rsp_total": 0,
        })
        clans = defaultdict(lambda: {
            "clan_id": "", "clan_name_snapshot": "", "signals_participated": 0,
            "signals_with_closer": 0, "nodes_held_total": 0,
            "territories_consumed_total": 0, "territory_area_consumed_total": 0.0,
            "member_rsp_total": 0, "clan_ghost_score_total": 0, "best_signal_score": 0,
        })
        for ranking in rankings:
            snapshot = ranking.get("snapshot") or {}
            for item in snapshot.get("players") or []:
                key = _clean(item.get("user_id"))
                if not key:
                    continue
                row = players[key]
                row["user_id"] = key
                if not row["username_snapshot"]:
                    row["username_snapshot"] = item.get("username_snapshot") or key
                    row["display_alias_snapshot"] = item.get("display_alias_snapshot") or row["username_snapshot"]
                row["signals_participated"] += 1
                row["signals_closed"] += int(bool(item.get("closer")))
                row["nodes_held_total"] += _int(item.get("nodes_held"))
                row["territories_consumed_total"] += _int(item.get("territories_consumed"))
                row["territory_area_consumed_total"] += _float(item.get("territory_area_consumed"))
                row["ghostnetwork_rsp_total"] += _int(item.get("rsp_signal"))
            for item in snapshot.get("clans") or []:
                key = _clean(item.get("clan_id"))
                if not key:
                    continue
                row = clans[key]
                row["clan_id"] = key
                if not row["clan_name_snapshot"]:
                    row["clan_name_snapshot"] = item.get("clan_name_snapshot") or key
                row["signals_participated"] += 1
                row["signals_with_closer"] += int(_int(item.get("closer_count")) > 0)
                row["nodes_held_total"] += _int(item.get("nodes_held"))
                row["territories_consumed_total"] += _int(item.get("territories_consumed"))
                row["territory_area_consumed_total"] += _float(item.get("territory_area_consumed"))
                row["member_rsp_total"] += _int(item.get("rsp_members_total"))
                score = _int(item.get("clan_ghost_score"))
                row["clan_ghost_score_total"] += score
                row["best_signal_score"] = max(row["best_signal_score"], score)
        player_rows = sorted(players.values(), key=lambda row: (-row["ghostnetwork_rsp_total"], row["user_id"]))
        clan_rows = sorted(clans.values(), key=lambda row: (-row["clan_ghost_score_total"], row["clan_id"]))
        for index, row in enumerate(player_rows, 1):
            row["rank"] = index
            row["territory_area_consumed_total"] = round(row["territory_area_consumed_total"], 6)
        for index, row in enumerate(clan_rows, 1):
            row["rank"] = index
            row["territory_area_consumed_total"] = round(row["territory_area_consumed_total"], 6)
        return {
            "ok": True,
            "contract": RANKING_CONTRACT,
            "rebuilt_from_snapshots": len(rankings),
            "players": player_rows,
            "clans": clan_rows,
        }
