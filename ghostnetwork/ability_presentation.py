"""Canonical, code-owned presentation profiles for production superpowers."""

from __future__ import annotations


ABILITY_PRESENTATIONS = {
    "insider_feed": ("Insider Feed", "MEGA HOSSA", "operation_cards"),
    "service_entrance": ("Wejście Serwisowe", "BACKDOOR GOTOWY", "target_action_dots"),
    "false_image": ("Fałszywy Obraz", "NIE WIERZ OCZOM", "operation_risk"),
    "hostile_takeover": ("Wrogie Przejęcie", "POTRÓJNY ZYSK", "file_yield"),
    "operational_prediction": ("Predykcja Operacyjna", "CZAS OBLICZONY", "operation_cards"),
    "expose": ("Ujawnienie", "SŁABOŚĆ UJAWNIONA", "target_security_bar"),
    "narrative_takeover": ("Przejęcie Narracji", "REAKCJA OPÓŹNIONA", "operation_risk"),
    "full_disclosure": ("Pełne Ujawnienie", "PRAWDA BEZ FILTRA", "data_quality"),
    "resistance_signal": ("Beacon Oporu", "ŚWIAT W ZASIĘGU", "scan_range"),
    "domino_effect": ("Efekt Domina", "ISKRA POSZŁA", "target_security_bar"),
    "phantom_node": ("Węzeł Widmo", "RUCH POZORNY", "operation_risk"),
    "glitch_injection": ("Glitch Injection", "SYSTEM PĘKA", "target_security_bar"),
    "false_tracking": ("Fałszywe Tropienie", "WSZĘDZIE SĄ ŚLADY", "scan_range"),
    "network_fracture": ("Pęknięcie Sieci", "HORYZONT PĘKA", "map_zoom"),
    "reflection": ("Odbicie", "RÓJ ODBITY", "territory_defense"),
    "integrity_scan": ("Skan Integralności", "SIEĆ PRZEŚWIETLONA", "scan_range"),
    "bastion": ("Bastion", "MUR PODNIESIONY", "territory_defense"),
    "rollback": ("Odtworzenie", "DOSTĘP ODTWORZONY", "target_action_dots"),
    "trust_corridor": ("Korytarz Zaufania", "PRZEJŚCIE ZABEZPIECZONE", "operation_risk"),
    "quarantine": ("Kwarantanna", "GRANICA WYZNACZONA", "map_zoom"),
}


def ability_presentation_profile(ability_code):
    """Return a defensive presentation dict for one production ability."""
    values = ABILITY_PRESENTATIONS.get(str(ability_code or "").strip())
    if not values:
        return {}
    display_name, activation_tagline, impact_ui = values
    return {
        "display_name": display_name,
        "activation_tagline": activation_tagline,
        "impact_ui": impact_ui,
    }
