"""Presentation data for the existing show controller; no gameplay authority."""
from .catalog import CATALOG_VERSION, CLANS, MACHINES, PARTS, PROFESSIONS, ABILITIES


MANIFEST_VERSION = "ghostsignal-show-manifest-v2"
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
    (455, "transmission_replay", "GHOSTSIGNAL — ZAPIS EMISJI"),
    (458, "signal_point", "ŚLAD SYGNAŁU"),
    (463, "terminal_2108", "KANAŁ 2108"),
    (475, "signal_confirmation", "GHOSTSIGNAL WYSŁANY"),
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


def build_manifest(facts):
    """Bounded public configuration plus narrow canonical readiness facts.

    Cycle history/geometry are deliberately not fetched from a changing world.
    Later scene adapters must supply frozen, audience-safe projections.
    """
    def fields(rows, keys):
        return [{key: list(row[key]) if isinstance(row.get(key), list) else row.get(key)
                 for key in keys} for row in rows]

    scenes = [{"id": code, "label": label, "start": start,
               "end": SCENES[index + 1][0] if index + 1 < len(SCENES) else 900,
               "requires_signal_sent": start >= 455,
               "fallback": "text"}
              for index, (start, code, label) in enumerate(SCENES)]
    return {
        "version": MANIFEST_VERSION, "nominal_duration_seconds": 900,
        "catalog_version": CATALOG_VERSION, "scenes": scenes,
        "signal_sent_at": facts.get("sent_at") or None,
        "signal_confirmed": bool(facts.get("sent_at") and facts.get("sent_event")),
        "ranking_available": bool(facts.get("ranking_available")),
        "cycle_history": {"available": False, "reason": "scene_projection_pending"},
        "catalog": {
            "clans": fields(CLANS, ("code", "name", "ui_color_token")),
            "machines": fields(MACHINES, ("code", "name", "clan_code", "part_codes")),
            "parts": fields(PARTS, ("part_code", "name", "clan_code", "machine_code",
                                    "profession_code", "ability_code", "icon_key")),
            "professions": fields(PROFESSIONS, ("code", "name", "part_code", "machine_code")),
            "abilities": fields(ABILITIES, ("ability_code", "name")),
        },
        "assets": [
            {"id": "machine_" + machine["code"], "kind": "image", "src": None,
             "available": False, "fallback": "canonical_parts"} for machine in MACHINES
        ] + [{"id": "ghostsignal_transmission_video", "kind": "video", "src": None,
              "available": False, "duration_seconds": 30, "fallback": "text"}],
        "audio": {"event": "ghost.signal_sent", "sfx_key": "ghostnetwork.signal",
                  "owner": "existing_delta_sfx", "replay": False},
    }
