"""Presentation data for the existing show controller; no gameplay authority."""
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from .catalog import CATALOG_VERSION, CLANS, MACHINES, PARTS, PROFESSIONS, ABILITIES


def prepare_scene_snapshot(lock, signal_id):
    """Prepare the public, bounded scene projection before the show writer."""
    source = (lock or {}).get("snapshot") or {}
    known = {p["part_code"] for p in PARTS}
    rows = []
    for part in (source.get("parts") or [])[:20]:
        if part.get("part_code") not in known:
            continue
        anchor = part.get("anchor") or {}
        row = {key: part.get(key) for key in (
            "part_code", "status", "discovered_at", "activated_at")}
        lat, lon = anchor.get("latitude"), anchor.get("longitude")
        if (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and math.isfinite(lat) and math.isfinite(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180):
            row.update(latitude=lat, longitude=lon)
        rows.append(row)
    ring = (source.get("topology") or {}).get("ring_codes") or []
    ring = ring if len(ring) == 20 and set(ring) == known else []
    # Stable backend-selected date, persisted with this show's projection.
    seconds = int(hashlib.sha256(("show-2108:" + signal_id).encode()).hexdigest()[:16], 16) % (366 * 86400)
    future = datetime(2108, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    payload = {"version": 1, "available": len(rows) == 20 and len({r['part_code'] for r in rows}) == 20,
               "parts": rows, "ring_codes": ring,
               "future_2108_timestamp": future.isoformat()}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


MANIFEST_VERSION = "ghostsignal-show-manifest-v2"


def prepare_settlement_scene(ranking, publications=(), production_conflicts=()):
    """Small public replay prepared from the already validated ranking, never in polling."""
    snapshot = ranking.get("snapshot") or {}
    signal_id = ranking.get("signal_id")
    def text(value, limit=80):
        return str(value or "")[:limit]
    def number(value):
        try:
            result = float(value or 0)
            return max(0, result) if math.isfinite(result) else 0
        except (TypeError, ValueError):
            return 0
    territories = snapshot.get("territories") or []
    rewards = [r for r in snapshot.get("rewards") or [] if r.get("signal_id") == signal_id]
    players = snapshot.get("players") or []
    clans = snapshot.get("clans") or []
    conflicts = snapshot.get("conflicts") or []
    shapes = []
    for index, row in enumerate(territories[:40]):
        vertices = row.get("vertices") or []
        # Oversized geometry is omitted, not distorted into a fictitious polygon.
        points = []
        if 3 <= len(vertices) <= 32:
            for point in vertices:
                try:
                    lat, lon = float(point["lat"]), float(point.get("lng", point.get("lon")))
                except (KeyError, TypeError, ValueError):
                    points = []
                    break
                if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                    points = []
                    break
                points.append([round(lon, 6), round(lat, 6)])
        shapes.append({"label": "T" + str(index + 1), "clan": text(row.get("clan_code")),
                       "outcome": "consumed", "area": number(row.get("area_size")),
                       "points": points, "geometry_available": bool(points),
                       "consumed_at": text(row.get("consumed_at"))})
    reward_groups = {}
    for row in rewards:
        key = text(row.get("reward_type"))
        group = reward_groups.setdefault(key, {"type": key, "count": 0, "rsp": 0})
        group["count"] += 1
        group["rsp"] += number(row.get("final_rsp"))
    payload = {
        "version": 1, "available": True, "source": "validated_signal_ranking",
        "scope": "signal_settlement", "territories": shapes,
        "territories_total": len(territories), "territories_truncated": len(territories) > 40,
        "area_consumed": sum(number(t.get("area_size")) for t in territories),
        "preserved_available": False, "reduced_available": False,
        "players_total": len(players), "players_truncated": len(players) > 20,
        "players": [{"alias": text(p.get("display_alias_snapshot") or p.get("username_snapshot")),
                     "clan": text(p.get("clan_id_snapshot")), "rank": number(p.get("rank")),
                     "rsp": number(p.get("rsp_signal")), "nodes": number(p.get("nodes_held")),
                     "closer": bool(p.get("closer"))} for p in players[:20]],
        "clans": [{"code": text(c.get("clan_id")), "rank": number(c.get("rank")),
                   "members": number(c.get("member_count_participating")),
                   "score": number(c.get("clan_ghost_score")), "rsp": number(c.get("rsp_members_total"))}
                  for c in clans[:8]],
        "score_policy": text((snapshot.get("score_policy") or {}).get("policy_version")),
        "reward_groups": list(reward_groups.values())[:16], "rewards_total": len(rewards),
        "rsp_total": sum(number(r.get("final_rsp")) for r in rewards),
        "conflicts_total": len(conflicts), "conflicts_scope": "strategic_lock_snapshot",
        "conflicts": [{"label": "C" + str(i + 1), "status": text(c.get("status"))}
                      for i, c in enumerate(conflicts[:20])],
        "production_conflicts": [{"label": "P" + str(i + 1), "status": text(c.get("status")),
                                  "resolved_at": text(c.get("resolved_at") or c.get("closed_at"))}
                                 for i, c in enumerate(production_conflicts[:20])],
        "production_conflicts_scope": "explicit_lock_and_receipt_references",
        "publications": [{"medium": text(p.get("target_medium")), "title": text(p.get("title"), 160),
                          "body": text(p.get("body"), 480), "published_at": text(p.get("published_at"))}
                         for p in publications[:6]],
    }
    # Explicit fixed transfer budget; fallback retains counts if geometry is too large.
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 24576:
        for shape in payload["territories"]:
            shape.update(points=[], geometry_available=False)
    while len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 24576 and payload["publications"]:
        payload["publications"].pop()
    while len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 24576 and payload["players"]:
        payload["players"].pop()
        payload["players_truncated"] = True
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 24576:
        for key in ("territories", "conflicts", "production_conflicts", "reward_groups", "clans"):
            payload[key] = []
        payload.update(territories_truncated=True, details_truncated=True)
    return payload
# Half-open scene intervals on the nominal 900-second storyboard.
SCENES = (
    (0, "takeover", "PRZEJĘCIE INTERFEJSU"),
    (15, "network_layer", "GHOST NETWORK"),
    (30, "parts_enter", "HISTORIA CZĘŚCI"),
    (60, "parts_complete", "DWADZIEŚCIA CZĘŚCI"),
    (90, "connections", "POŁĄCZENIA"),
    (120, "history_logs", "HISTORIA CYKLU"),
    (140, "part_states", "STANY CZĘŚCI"),
    (160, "machine_groups", "CZTERY MASZYNY"),
    (180, "machine_group_1", "MASZYNA 01"),
    (210, "machine_group_2", "MASZYNA 02"),
    (240, "machine_group_3", "MASZYNA 03"),
    (270, "machine_group_4", "MASZYNA 04"),
    (300, "network_expand", "WSPÓLNA SIEĆ"),
    (320, "network_ring", "GHOST NETWORK"),
    (340, "network_tension", "SYNCHRONIZACJA"),
    (350, "network_ready", "SIEĆ GOTOWA"),
    (360, "machine_hero_1", "MASZYNA 01"),
    (375, "machine_hero_2", "MASZYNA 02"),
    (390, "machine_hero_3", "MASZYNA 03"),
    (405, "machine_hero_4", "MASZYNA 04"),
    (420, "transmission_quiet", "ZAPIS TRANSMISJI"),
    (425, "transmission_video", "REKONSTRUKCJA TRANSMISJI"),
    (463.12, "transmission_replay", "GHOSTSIGNAL — ZAPIS EMISJI"),
    (466.12, "signal_point", "ŚLAD SYGNAŁU"),
    (469.12, "terminal_2108", "KANAŁ 2108"),
    (477, "signal_confirmation", "GHOSTSIGNAL WYSŁANY"),
    (480, "aftershock", "WORLD SETTLEMENT"),
    (495, "world_before", "ŚWIAT PRZED ROZLICZENIEM"),
    (525, "territory_outcomes", "LOSY TERYTORIÓW"),
    (555, "territory_reduction", "ROZLICZENIE TERYTORIÓW"),
    (585, "conflict_results", "WYNIKI KONFLIKTÓW"),
    (615, "world_final", "FINAL WORLD STATE"),
    (630, "reward_ledger", "NAGRODY"),
    (660, "players", "UCZESTNICY"),
    (680, "achievements", "OSIĄGNIĘCIA"),
    (700, "clans", "KLANY"),
    (720, "system_layers", "REKONSTRUKCJA CHAOS"),
    (740, "googleplex", "GOOGLEPLEX"),
    (760, "pro_tools", "PRO TOOLS / TERMINAL"),
    (780, "file_system", "PLIKI I DANE"),
    (800, "blacknet_history", "BLACKNET / HISTORIA"),
    (820, "desktop_assembly", "REKONSTRUKCJA PULPITU"),
    (835, "system_ready", "REKONSTRUKCJA — PODSUMOWANIE"),
    (840, "player_ranking", "RANKING GRACZY"),
    (855, "clan_ranking", "RANKING KLANÓW"),
    (870, "cycle_statistics", "STATYSTYKI CYKLU"),
    (880, "archive", "ARCHIWUM CYKLU"),
    (890, "shutdown", "ZAMYKANIE WIDOKU"),
    (896, "restart", "OCZEKIWANIE NA NOWY CYKL"),
)


def build_manifest(facts, scene_snapshot=None):
    """Bounded public configuration plus narrow canonical readiness facts.

    Cycle history/geometry are deliberately not fetched from a changing world.
    Later scene adapters must supply frozen, audience-safe projections.
    """
    def fields(rows, keys):
        return [{key: list(row[key]) if isinstance(row.get(key), list) else row.get(key)
                 for key in keys} for row in rows]

    scenes = [{"id": code, "label": label, "start": start,
               "end": SCENES[index + 1][0] if index + 1 < len(SCENES) else 900,
               "requires_signal_sent": start >= 463.12,
               "fallback": "text"}
              for index, (start, code, label) in enumerate(SCENES)]
    return {
        "version": MANIFEST_VERSION, "nominal_duration_seconds": 900,
        "catalog_version": CATALOG_VERSION, "scenes": scenes,
        "signal_sent_at": facts.get("sent_at") or None,
        "signal_confirmed": bool(facts.get("sent_at") and facts.get("sent_event")),
        "ranking_available": bool(facts.get("ranking_available")),
        "cycle_history": scene_snapshot or {"available": False, "reason": "scene_projection_pending"},
        "catalog": {
            "clans": fields(CLANS, ("code", "name", "ui_color_token")),
            "machines": fields(MACHINES, ("code", "name", "clan_code", "part_codes")),
            "parts": fields(PARTS, ("part_code", "name", "clan_code", "machine_code",
                                    "profession_code", "ability_code", "icon_key")),
            "professions": fields(PROFESSIONS, ("code", "name", "part_code", "machine_code")),
            "abilities": fields(ABILITIES, ("ability_code", "name", "description")),
        },
        "assets": [
            {"id": "machine_" + machine["code"], "kind": "image",
             "src": "/static/images/ghostnetwork/signal_sends/machine_" + machine["code"] + ".png",
             "active_src": "/static/images/ghostnetwork/signal_sends/machine_" + machine["code"] + "_active.png",
             "available": True, "fallback": "canonical_parts"} for machine in MACHINES
        ] + [{"id": "ghostsignal_transmission_video", "kind": "video",
              "src": "/static/video/ghostsignal_transmission_video.mp4",
              "available": True, "duration_seconds": 38.12, "muted": False, "fallback": "text"}],
        "audio": {"event": "ghost.signal_sent", "sfx_key": "ghostnetwork.signal",
                  "owner": "existing_delta_sfx", "replay": False,
                  "show_tracks": [{"src": "/static/audio/ghostnetwork/show/ghostsignal_show_part_0" + str(i + 1) + ".mp3",
                                   "duration": duration} for i, duration in enumerate(
                                       (203.702813, 210.964875, 234.083250, 211.304438))],
                  "video_start": 425, "video_end": 463.12, "video_audio": True,
                  "fade_seconds": 0.5, "overlap_video_intro": True},
    }
