from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict


CATALOG_VERSION = "ghost-canon-1"

TOPOLOGY_ANCHOR = (
    "V1", "S5", "E4", "P3", "V2",
    "E1", "S4", "P5", "V3", "S2",
    "E5", "P1", "V4", "E3", "S1",
    "P4", "V5", "S3", "E2", "P2",
)

CLANS = (
    {
        "code": "virex",
        "name": "VIREX",
        "short_code": "VIR",
        "machine_code": "virex_oracle",
        "description": "Klan predykcji, przeplywow zasobow i agresywnej optymalizacji tras.",
        "motto": "Zysk jest mapa ryzyka.",
        "ui_color_token": "ghost-clan-virex",
        "sort_order": 1,
    },
    {
        "code": "echo_freedom",
        "name": "Echo Wolności",
        "short_code": "ECH",
        "machine_code": "echo_libertas",
        "description": "Klan ujawniania prawdy, narracji oporu i przelamywania monopoli informacji.",
        "motto": "Niech sygnal przejdzie przez cisze.",
        "ui_color_token": "ghost-clan-echo",
        "sort_order": 2,
    },
    {
        "code": "phantom_mesh",
        "name": "Siatka Widmo",
        "short_code": "PHM",
        "machine_code": "phantom_veil",
        "description": "Klan ukrycia, dezinformacji, pelenia chaosu i maskowania tras.",
        "motto": "Najlepszy slad to ten, ktory prowadzi gdzie indziej.",
        "ui_color_token": "ghost-clan-phantom",
        "sort_order": 3,
    },
    {
        "code": "sentinel_order",
        "name": "Strażnicy Ładu",
        "short_code": "SEN",
        "machine_code": "sentinel_aegis",
        "description": "Klan integralnosci, obrony, rekonstrukcji i cyfrowego porzadku.",
        "motto": "System przetrwa, jesli ufa swoim granicom.",
        "ui_color_token": "ghost-clan-sentinel",
        "sort_order": 4,
    },
)

MACHINES = (
    {
        "code": "virex_oracle",
        "name": "VIREX ORACLE",
        "clan_code": "virex",
        "purpose": "Wyznacza najlepszy moment, trase i wariant transmisji GhostSignalu.",
        "risk_extreme": "Moze potraktowac ludzi jak aktywa optymalizowane tak samo jak infrastruktura.",
        "full_function": "prediction_and_routing",
        "part_codes": ["V1", "V2", "V3", "V4", "V5"],
        "sort_order": 1,
    },
    {
        "code": "echo_libertas",
        "name": "ECHO LIBERTAS",
        "clan_code": "echo_freedom",
        "purpose": "Sklada, wzmacnia i przepycha przekaz przez zaklocone kanaly oporu.",
        "risk_extreme": "Moze zmienic prawde w narzedzie masowego wplywu.",
        "full_function": "message_assembly_and_transmission",
        "part_codes": ["E1", "E2", "E3", "E4", "E5"],
        "sort_order": 2,
    },
    {
        "code": "phantom_veil",
        "name": "PHANTOM VEIL",
        "clan_code": "phantom_mesh",
        "purpose": "Maskuje zrodlo, cel i trase sygnalu przed systemami predykcyjnymi.",
        "risk_extreme": "Moze zgubic roznice miedzy ochrona a falszem.",
        "full_function": "concealment_and_route_masking",
        "part_codes": ["P1", "P2", "P3", "P4", "P5"],
        "sort_order": 3,
    },
    {
        "code": "sentinel_aegis",
        "name": "SENTINEL AEGIS",
        "clan_code": "sentinel_order",
        "purpose": "Chroni integralnosc sieci, naprawia szkody i izoluje skazone segmenty.",
        "risk_extreme": "Moze zamienic ochrone w kwarantanne calej wolnosci.",
        "full_function": "integrity_and_protection",
        "part_codes": ["S1", "S2", "S3", "S4", "S5"],
        "sort_order": 4,
    },
)

PART_DEFINITIONS = (
    ("V1", "Ledger Nexus", "virex", "virex_oracle", "broker", "Broker", "insider_feed", "Przeplywy rynku", "Analizuje popyt i wykrywa przesuniecia wartosci zanim stana sie jawne.", "ledger_nexus"),
    ("V2", "Backdoor Forge", "virex", "virex_oracle", "architect", "Architekt", "service_entrance", "Wejscia serwisowe", "Projektuje boczne wejscia do struktur bez burzenia calej fasady.", "backdoor_forge"),
    ("V3", "Mimicry Engine", "virex", "virex_oracle", "manipulator", "Manipulator", "false_image", "Obrazy zastepcze", "Buduje wiarygodne odbicia i falszywe sylwetki infrastruktury.", "mimicry_engine"),
    ("V4", "Acquisition Drive", "virex", "virex_oracle", "profit_enforcer", "Egzekutor Zysku", "hostile_takeover", "Przejecia", "Wykrywa moment, w ktorym obcy zasob mozna przejac z minimalnym oporem.", "acquisition_drive"),
    ("V5", "Probability Core", "virex", "virex_oracle", "algorithm_curator", "Kurator Algorytmu", "operational_prediction", "Predykcja operacji", "Wylicza najbardziej prawdopodobny przebieg ruchow na osi czasu.", "probability_core"),
    ("E1", "Breach Voice", "echo_freedom", "echo_libertas", "hacktivist", "Haktywista", "expose", "Ujawnienie", "Przelamuje cisze wokol ukrytych slabosci i pokazuje je szerszej sieci.", "breach_voice"),
    ("E2", "Influence Relay", "echo_freedom", "echo_libertas", "social_engineer", "Socjotechnik", "narrative_takeover", "Przejecie narracji", "Przestawia kontekst informacji tak, aby przeciwnik reagowal za pozno.", "influence_relay"),
    ("E3", "Truth Lens", "echo_freedom", "echo_libertas", "revealer", "Odsłaniacz", "full_disclosure", "Pelne ujawnienie", "Dociera do ukrytych warstw celu i usuwa ochronne niedopowiedzenia.", "truth_lens"),
    ("E4", "Resonance Beacon", "echo_freedom", "echo_libertas", "visionary", "Wizjoner", "resistance_signal", "Beacon oporu", "Wzmacnia sygnal klanu i laczy rozproszone decyzje w jeden rytm.", "resonance_beacon"),
    ("E5", "Spark Chamber", "echo_freedom", "echo_libertas", "igniter", "Zapalnik", "domino_effect", "Efekt domina", "Inicjuje reakcje lancuchowe w sasiednich segmentach systemu.", "spark_chamber"),
    ("P1", "Mirage Projector", "phantom_mesh", "phantom_veil", "illusionist", "Iluzjonista", "phantom_node", "Wezel-widmo", "Stawia pozorne aktywnosci, ktore odciagaja wzrok od prawdziwego ruchu.", "mirage_projector"),
    ("P2", "Glitch Reactor", "phantom_mesh", "phantom_veil", "virologist", "Wirusolog", "glitch_injection", "Wstrzykniecie glitcha", "Zakloca stabilnosc warstw terytorium i wprowadza kontrolowany blad.", "glitch_reactor"),
    ("P3", "Paranoia Loop", "phantom_mesh", "phantom_veil", "paranoid", "Paranoik", "false_tracking", "Falszywe tropienie", "Karmi system tropami, ktore wygladaja na zbyt prawdziwe, by byly przypadkiem.", "paranoia_loop"),
    ("P4", "Fracture Engine", "phantom_mesh", "phantom_veil", "network_splitter", "Rozlamowiec", "network_fracture", "Rozlam sieci", "Rozcina ciaglosc kontroli i zmusza system do obrony kilku wersji naraz.", "fracture_engine"),
    ("P5", "Mirror Kernel", "phantom_mesh", "phantom_veil", "mirror_judge", "Lustrzany Sędzia", "reflection", "Odbicie", "Zawraca czesc presji w strone nadawcy i pokazuje koszt ataku.", "mirror_kernel"),
    ("S1", "Deep Sensor", "sentinel_order", "sentinel_aegis", "analyzer", "Analizator", "integrity_scan", "Skan integralnosci", "Wykrywa pekniecia systemu zanim zamienia sie w trwale uszkodzenia.", "deep_sensor"),
    ("S2", "Bastion Matrix", "sentinel_order", "sentinel_aegis", "defender", "Obrońca", "bastion", "Bastion", "Podnosi warstwy obronne i wzmacnia stabilnosc kontrolowanego obszaru.", "bastion_matrix"),
    ("S3", "Restoration Engine", "sentinel_order", "sentinel_aegis", "reconstructor", "Rekonstruktor", "rollback", "Odtworzenie", "Przywraca utracony porzadek z ostatniego stabilnego odcisku systemu.", "restoration_engine"),
    ("S4", "Accord Relay", "sentinel_order", "sentinel_aegis", "mediator", "Mediator", "trust_corridor", "Korytarz zaufania", "Tworzy bezpieczne przejscie pomiedzy segmentami, ktore powinny sobie nie ufac.", "accord_relay"),
    ("S5", "Judgment Core", "sentinel_order", "sentinel_aegis", "executor", "Egzekutor", "quarantine", "Kwarantanna", "Izoluje skazony ruch i wymusza twarda decyzje o granicy systemu.", "judgment_core"),
)

ABILITY_EFFECT_TYPES = {
    "insider_feed": "market_demand_preview",
    "service_entrance": "hack_threshold_modifier",
    "false_image": "territory_information_mask",
    "hostile_takeover": "territory_attack_window",
    "operational_prediction": "operation_probability_zone",
    "expose": "security_weakness_reveal",
    "narrative_takeover": "operation_alert_delay",
    "full_disclosure": "scan_detail_modifier",
    "resistance_signal": "clan_operation_beacon",
    "domino_effect": "neighbor_security_reduction",
    "phantom_node": "false_activity_marker",
    "glitch_injection": "territory_stability_damage",
    "false_tracking": "false_tracking_traces",
    "network_fracture": "territory_connection_disruption",
    "reflection": "attack_reflection",
    "integrity_scan": "territory_integrity_scan",
    "bastion": "territory_defense_layer",
    "rollback": "territory_repair",
    "trust_corridor": "trusted_access_corridor",
    "quarantine": "operation_quarantine",
}


def _build_parts():
    parts = []
    for sort_order, item in enumerate(PART_DEFINITIONS, 1):
        (
            part_code, name, clan_code, machine_code, profession_code,
            _profession_name, ability_code, function, description, icon_key,
        ) = item
        parts.append({
            "part_code": part_code,
            "name": name,
            "clan_code": clan_code,
            "machine_code": machine_code,
            "profession_code": profession_code,
            "ability_code": ability_code,
            "function": function,
            "description": description,
            "icon_key": icon_key,
            "sort_order": sort_order,
        })
    return tuple(parts)


def _build_professions():
    professions = []
    for sort_order, item in enumerate(PART_DEFINITIONS, 1):
        (
            part_code, _part_name, clan_code, machine_code, profession_code,
            profession_name, ability_code, function, description, _icon_key,
        ) = item
        professions.append({
            "code": profession_code,
            "name": profession_name,
            "clan_code": clan_code,
            "machine_code": machine_code,
            "part_code": part_code,
            "role": function,
            "play_style": _play_style_for_clan(clan_code),
            "description": description,
            "ability_code": ability_code,
            "base_capabilities": _base_capabilities_for_clan(clan_code),
            "sort_order": sort_order,
        })
    return tuple(professions)


def _build_abilities():
    abilities = []
    profession_by_ability = {
        item[6]: {
            "part_code": item[0],
            "part_name": item[1],
            "clan_code": item[2],
            "profession_code": item[4],
            "profession_name": item[5],
            "function": item[7],
            "description": item[8],
        }
        for item in PART_DEFINITIONS
    }
    for sort_order, (ability_code, effect_type) in enumerate(ABILITY_EFFECT_TYPES.items(), 1):
        source = profession_by_ability[ability_code]
        abilities.append({
            "ability_code": ability_code,
            "effect_type": effect_type,
            "name": source["function"],
            "description": source["description"],
            "activation_scope": "ghostnetwork_part",
            "target_scope": _target_scope_for_effect(effect_type),
            "requires_active_part": True,
            "mechanics_status": "catalog_only",
            "sort_order": sort_order,
        })
    return tuple(abilities)


def _play_style_for_clan(clan_code):
    return {
        "virex": "predykcja, przejecia i optymalizacja",
        "echo_freedom": "ujawnianie, narracja i mobilizacja",
        "phantom_mesh": "maskowanie, chaos i falszywe tropy",
        "sentinel_order": "obrona, stabilizacja i naprawa",
    }[clan_code]


def _base_capabilities_for_clan(clan_code):
    return {
        "virex": ["prediction", "routing", "resource_pressure"],
        "echo_freedom": ["disclosure", "broadcast", "social_pressure"],
        "phantom_mesh": ["masking", "misdirection", "instability"],
        "sentinel_order": ["integrity", "defense", "recovery"],
    }[clan_code]


def _target_scope_for_effect(effect_type):
    if effect_type.startswith("territory_") or effect_type in {"neighbor_security_reduction", "attack_reflection"}:
        return "territory"
    if effect_type.startswith("operation_"):
        return "operation"
    if effect_type in {"scan_detail_modifier", "security_weakness_reveal"}:
        return "target"
    if effect_type in {"clan_operation_beacon", "trusted_access_corridor"}:
        return "clan"
    return "ghostnetwork"


PARTS = _build_parts()
PROFESSIONS = _build_professions()
ABILITIES = _build_abilities()


def get_catalog():
    return copy.deepcopy({
        "catalog_version": CATALOG_VERSION,
        "clans": list(CLANS),
        "machines": list(MACHINES),
        "professions": list(PROFESSIONS),
        "parts": list(PARTS),
        "abilities": list(ABILITIES),
        "topology_anchor": list(TOPOLOGY_ANCHOR),
    })


def get_catalog_checksum(catalog=None):
    catalog = get_catalog() if catalog is None else catalog
    payload = json.dumps(catalog, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_catalog(catalog=None):
    catalog = get_catalog() if catalog is None else copy.deepcopy(catalog)
    errors = []
    warnings = []

    clans = catalog.get("clans") or []
    machines = catalog.get("machines") or []
    professions = catalog.get("professions") or []
    parts = catalog.get("parts") or []
    abilities = catalog.get("abilities") or []

    _expect_count(errors, "clans", clans, 4)
    _expect_count(errors, "machines", machines, 4)
    _expect_count(errors, "professions", professions, 20)
    _expect_count(errors, "parts", parts, 20)
    _expect_count(errors, "abilities", abilities, 20)

    _require_unique(errors, "clan.code", [item.get("code") for item in clans])
    _require_unique(errors, "machine.code", [item.get("code") for item in machines])
    _require_unique(errors, "profession.code", [item.get("code") for item in professions])
    _require_unique(errors, "part.part_code", [item.get("part_code") for item in parts])
    _require_unique(errors, "ability.ability_code", [item.get("ability_code") for item in abilities])

    clans_by_code = {item.get("code"): item for item in clans}
    machines_by_code = {item.get("code"): item for item in machines}
    professions_by_code = {item.get("code"): item for item in professions}
    parts_by_code = {item.get("part_code"): item for item in parts}
    abilities_by_code = {item.get("ability_code"): item for item in abilities}

    for collection_name, items, required_fields in (
        ("clans", clans, ("code", "name", "machine_code", "description", "motto", "ui_color_token", "sort_order")),
        ("machines", machines, ("code", "name", "clan_code", "purpose", "risk_extreme", "full_function", "part_codes", "sort_order")),
        ("professions", professions, ("code", "name", "clan_code", "machine_code", "part_code", "role", "play_style", "description", "ability_code", "base_capabilities", "sort_order")),
        ("parts", parts, ("part_code", "name", "clan_code", "machine_code", "profession_code", "ability_code", "function", "description", "icon_key", "sort_order")),
        ("abilities", abilities, ("ability_code", "effect_type", "name", "description", "activation_scope", "target_scope", "requires_active_part", "mechanics_status", "sort_order")),
    ):
        for index, item in enumerate(items):
            for field in required_fields:
                value = item.get(field)
                if value is None or value == "" or value == []:
                    errors.append(f"{collection_name}[{index}] missing {field}")

    for clan in clans:
        machine = machines_by_code.get(clan.get("machine_code"))
        if not machine:
            errors.append(f"clan {clan.get('code')} references missing machine {clan.get('machine_code')}")
        elif machine.get("clan_code") != clan.get("code"):
            errors.append(f"clan {clan.get('code')} machine clan mismatch")

    parts_by_machine = defaultdict(list)
    parts_by_clan = defaultdict(list)
    for part in parts:
        parts_by_machine[part.get("machine_code")].append(part)
        parts_by_clan[part.get("clan_code")].append(part)
        machine = machines_by_code.get(part.get("machine_code"))
        profession = professions_by_code.get(part.get("profession_code"))
        if not machine:
            errors.append(f"part {part.get('part_code')} references missing machine {part.get('machine_code')}")
        elif machine.get("clan_code") != part.get("clan_code"):
            errors.append(f"part {part.get('part_code')} clan does not match machine")
        if part.get("clan_code") not in clans_by_code:
            errors.append(f"part {part.get('part_code')} references missing clan {part.get('clan_code')}")
        if not profession:
            errors.append(f"part {part.get('part_code')} references missing profession {part.get('profession_code')}")
        elif profession.get("part_code") != part.get("part_code"):
            errors.append(f"part {part.get('part_code')} profession back-reference mismatch")
        if part.get("ability_code") not in abilities_by_code:
            errors.append(f"part {part.get('part_code')} references missing ability {part.get('ability_code')}")

    for machine in machines:
        machine_parts = parts_by_machine.get(machine.get("code"), [])
        if len(machine_parts) != 5:
            errors.append(f"machine {machine.get('code')} has {len(machine_parts)} parts")
        if list(machine.get("part_codes") or []) != [part.get("part_code") for part in sorted(machine_parts, key=lambda item: item.get("sort_order", 0))]:
            errors.append(f"machine {machine.get('code')} part_codes mismatch")

    for clan in clans:
        clan_parts = parts_by_clan.get(clan.get("code"), [])
        if len(clan_parts) != 5:
            errors.append(f"clan {clan.get('code')} has {len(clan_parts)} parts")

    profession_part_counts = Counter(item.get("part_code") for item in professions)
    part_profession_counts = Counter(item.get("profession_code") for item in parts)
    for part_code in parts_by_code:
        if profession_part_counts[part_code] != 1:
            errors.append(f"part {part_code} has {profession_part_counts[part_code]} professions")
    for profession_code in professions_by_code:
        if part_profession_counts[profession_code] != 1:
            errors.append(f"profession {profession_code} has {part_profession_counts[profession_code]} parts")

    for profession in professions:
        part = parts_by_code.get(profession.get("part_code"))
        machine = machines_by_code.get(profession.get("machine_code"))
        if profession.get("clan_code") not in clans_by_code:
            errors.append(f"profession {profession.get('code')} references missing clan {profession.get('clan_code')}")
        if not machine:
            errors.append(f"profession {profession.get('code')} references missing machine {profession.get('machine_code')}")
        elif machine.get("clan_code") != profession.get("clan_code"):
            errors.append(f"profession {profession.get('code')} clan does not match machine")
        if not part:
            errors.append(f"profession {profession.get('code')} references missing part {profession.get('part_code')}")
        elif part.get("profession_code") != profession.get("code"):
            errors.append(f"profession {profession.get('code')} part back-reference mismatch")
        if profession.get("ability_code") not in abilities_by_code:
            errors.append(f"profession {profession.get('code')} references missing ability {profession.get('ability_code')}")

    for ability in abilities:
        if ability.get("mechanics_status") != "catalog_only":
            errors.append(f"ability {ability.get('ability_code')} mechanics_status must be catalog_only")

    _require_sort_order(errors, "clans", clans)
    _require_sort_order(errors, "machines", machines)
    _require_sort_order(errors, "professions", professions)
    _require_sort_order(errors, "parts", parts)
    _require_sort_order(errors, "abilities", abilities)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _expect_count(errors, name, items, expected):
    if len(items) != expected:
        errors.append(f"{name} count {len(items)} != {expected}")


def _require_unique(errors, name, values):
    counts = Counter(values)
    for value, count in counts.items():
        if not value:
            errors.append(f"{name} contains empty value")
        elif count != 1:
            errors.append(f"{name} duplicate {value}")


def _require_sort_order(errors, name, items):
    orders = [item.get("sort_order") for item in items]
    if sorted(orders) != list(range(1, len(items) + 1)):
        errors.append(f"{name} sort_order must be 1..{len(items)}")


def get_catalog_diagnostics():
    catalog = get_catalog()
    validation = validate_catalog(catalog)
    return {
        "catalog_version": catalog["catalog_version"],
        "clans_count": len(catalog["clans"]),
        "machines_count": len(catalog["machines"]),
        "professions_count": len(catalog["professions"]),
        "parts_count": len(catalog["parts"]),
        "abilities_count": len(catalog["abilities"]),
        "validation": validation,
        "checksum": get_catalog_checksum(catalog),
    }


def get_onboarding_catalog():
    catalog = get_catalog()
    machines_by_code = {item["code"]: item for item in catalog["machines"]}
    parts_by_code = {item["part_code"]: item for item in catalog["parts"]}
    abilities_by_code = {item["ability_code"]: item for item in catalog["abilities"]}
    professions_by_clan = defaultdict(list)
    for profession in catalog["professions"]:
        professions_by_clan[profession["clan_code"]].append(profession)

    clans = []
    for clan in sorted(catalog["clans"], key=lambda item: item["sort_order"]):
        machine = machines_by_code[clan["machine_code"]]
        professions = []
        for profession in sorted(professions_by_clan[clan["code"]], key=lambda item: item["sort_order"]):
            part = parts_by_code[profession["part_code"]]
            ability = abilities_by_code[profession["ability_code"]]
            professions.append({
                "code": profession["code"],
                "name": profession["name"],
                "part_code": part["part_code"],
                "part_name": part["name"],
                "role": profession["role"],
                "play_style": profession["play_style"],
                "description": profession["description"],
                "ability_code": ability["ability_code"],
                "ability_name": ability["name"],
                "status": "inactive",
            })
        clans.append({
            "code": clan["code"],
            "name": clan["name"],
            "short_code": clan["short_code"],
            "description": clan["description"],
            "motto": clan["motto"],
            "ui_color_token": clan["ui_color_token"],
            "sort_order": clan["sort_order"],
            "machine": {
                "code": machine["code"],
                "name": machine["name"],
                "purpose": machine["purpose"],
                "status": "inactive",
            },
            "professions": professions,
        })

    return {
        "catalog_version": catalog["catalog_version"],
        "clans": clans,
    }


def normalize_ghostnetwork_profile_identity(profile):
    profile = profile if isinstance(profile, dict) else {}
    validation_errors = []

    clan_code = _normalize_clan_value(
        _first_present(profile, ("ghost_clan", "ghost_clan_code", "clan_code", "clan", "fraction", "faction"))
    )
    profession_code = _normalize_profession_value(
        _first_present(profile, ("ghost_profession", "ghost_profession_code", "profession_code", "profession", "role", "class"))
    )

    if not clan_code:
        validation_errors.append("missing_or_unknown_clan")
    if not profession_code:
        validation_errors.append("missing_or_unknown_profession")

    professions_by_code = {item["code"]: item for item in PROFESSIONS}
    if clan_code and profession_code:
        profession = professions_by_code.get(profession_code)
        if not profession:
            validation_errors.append("unknown_profession")
        elif profession["clan_code"] != clan_code:
            validation_errors.append("profession_clan_mismatch")

    return {
        "clan_code": clan_code,
        "profession_code": profession_code,
        "catalog_valid": not validation_errors,
        "validation_errors": validation_errors,
    }


def _first_present(profile, keys):
    for key in keys:
        value = profile.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_key(value):
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


CLAN_ALIASES = {
    "1": "virex",
    "v": "virex",
    "vir": "virex",
    "virex": "virex",
    "virex_oracle": "virex",
    "2": "echo_freedom",
    "echo": "echo_freedom",
    "echo_freedom": "echo_freedom",
    "echo_wolnosci": "echo_freedom",
    "echo_wolnosci_": "echo_freedom",
    "wolnosci": "echo_freedom",
    "3": "phantom_mesh",
    "phantom": "phantom_mesh",
    "phantom_mesh": "phantom_mesh",
    "siatka": "phantom_mesh",
    "siatka_widmo": "phantom_mesh",
    "widmo": "phantom_mesh",
    "4": "sentinel_order",
    "sentinel": "sentinel_order",
    "sentinel_order": "sentinel_order",
    "straznicy": "sentinel_order",
    "straznicy_ladu": "sentinel_order",
    "straznicy_adu": "sentinel_order",
}


def _profession_aliases():
    aliases = {}
    for profession in PROFESSIONS:
        aliases[_normalize_key(profession["code"])] = profession["code"]
        aliases[_normalize_key(profession["name"])] = profession["code"]
    aliases.update({
        "egzekutor_zysku": "profit_enforcer",
        "egzekutor": "executor",
        "odslaniacz": "revealer",
        "obronca": "defender",
        "lustrzany_sedzia": "mirror_judge",
        "kurator_algorytmu": "algorithm_curator",
        "socjotechnik": "social_engineer",
    })
    return aliases


PROFESSION_ALIASES = _profession_aliases()


def _normalize_clan_value(value):
    return CLAN_ALIASES.get(_normalize_key(value), "")


def _normalize_profession_value(value):
    return PROFESSION_ALIASES.get(_normalize_key(value), "")
