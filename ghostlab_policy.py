import math

def default_ghostlab_blueprint(template_id):
    defaults = {
        "financial_sniffer": {
            "steal_percent": 8,
            "detection_percent": 18,
            "cooldown_minutes": 180,
            "success_message": "Financial Sniffer przechwycil drobny przeplyw HC.",
            "failure_message": "Operacja finansowa zostala wygaszona przez zabezpieczenia.",
            "reward_note": "HC transfer draft",
        },
        "friend_kicker": {
            "success_percent": 45,
            "detection_percent": 20,
            "target_policy": "random_contact",
            "victim_message": "Wykryto probe manipulacji kontaktami.",
            "contact_message": "Polaczenie z jednym z graczy zostalo zerwane.",
        },
        "security_panel_proxy": {
            "allowed_switches": "boolean_security_only",
            "presets": "open, low, regular, secure, all",
            "rules": "apply SECURITY_CONFLICTS",
            "conflict_matrix": "locked_until_compiler",
        },
        "system_log_reader": {
            "log_limit": 5,
            "include_type": True,
            "include_status": True,
            "include_created_at": True,
            "redaction_policy": "system_messages_only",
        },
        "arsenal_cleaner": {
            "success_percent": 40,
            "detection_percent": 22,
            "target_policy": "random_non_core_app",
            "protected_apps": "Terminal, Mapa, Browser, Email, Wallet HC, Profil, Pliki",
            "remove_tools_file": True,
        },
    }
    return dict(defaults.get(str(template_id or ""), {"notes": ""}))


def validate_ghostlab_blueprint(template_id, blueprint):
    errors = []
    defaults = default_ghostlab_blueprint(template_id)
    supported = {"financial_sniffer", "friend_kicker", "security_panel_proxy", "system_log_reader", "arsenal_cleaner", "", "custom"}
    if template_id not in supported or not isinstance(blueprint, dict):
        return {"valid": False, "errors": ["Nieprawidlowy szablon lub blueprint."], "warnings": [], "preview": []}
    if set(blueprint) != set(defaults):
        errors.append("Blueprint musi zawierac dokladnie pola wybranego szablonu.")
    locked = {"target_policy", "allowed_switches", "presets", "rules", "conflict_matrix", "redaction_policy", "protected_apps"}
    for key in locked.intersection(defaults):
        if blueprint.get(key) != defaults[key]:
            errors.append(f"{key}: wymagana polityka serwera.")
    warnings = []

    def number_between(key, label, min_value, max_value):
        value = blueprint.get(key)
        if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
            errors.append(f"{label} musi byc skonczona liczba.")
            return None
        if key in {"log_limit", "cooldown_minutes"} and int(value) != value:
            errors.append(f"{label} musi byc liczba calkowita.")
        if value < min_value or value > max_value:
            errors.append(f"{label} musi byc w zakresie {min_value}-{max_value}.")
        return value

    def required_text(key, label, max_len=240):
        if not isinstance(blueprint.get(key), str):
            errors.append(f"{label} musi byc tekstem.")
        value = str(blueprint.get(key) or "").strip()
        if not value:
            errors.append(f"{label} nie moze byc puste.")
        if len(value) > max_len:
            errors.append(f"{label} jest za dlugie.")
        return value

    template_id = str(template_id or "")
    if template_id == "financial_sniffer":
        steal = number_between("steal_percent", "Steal %", 1, 8)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        cooldown = number_between("cooldown_minutes", "Cooldown", 5, 1440)
        required_text("success_message", "Success message")
        required_text("failure_message", "Failure message")
        required_text("reward_note", "Rewards", 160)
        if steal and steal > 6:
            warnings.append("Steal % powyzej 6 zwiekszy balansowe ryzyko w compilerze.")
        if detection is not None and detection < 10:
            warnings.append("Detection % ponizej 10 moze zostac podbite w compilerze.")
        preview = [
            f"kradziez do {steal or '?'}% salda ofiary",
            f"wykrycie {detection if detection is not None else '?'}%",
            f"cooldown {cooldown or '?'} min",
        ]
    elif template_id == "friend_kicker":
        success = number_between("success_percent", "Success %", 1, 85)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        required_text("target_policy", "Targets", 80)
        required_text("victim_message", "Victim system message")
        required_text("contact_message", "Contact system message")
        preview = [
            f"szansa wypchniecia {success or '?'}%",
            f"wykrycie {detection if detection is not None else '?'}%",
            "atakujacy nie widzi listy kontaktow",
        ]
    elif template_id == "security_panel_proxy":
        required_text("allowed_switches", "Allowed switches", 120)
        required_text("presets", "Presets", 160)
        required_text("rules", "Rules")
        required_text("conflict_matrix", "Conflict matrix")
        preview = [
            "panel zmiany boolean security",
            "presety beda mapowane w compilerze",
            "SECURITY_CONFLICTS pozostaje zrodlem zasad",
        ]
    elif template_id == "system_log_reader":
        limit = number_between("log_limit", "Log limit", 1, 5)
        for key in ("include_type", "include_status", "include_created_at"):
            if not isinstance(blueprint.get(key), bool):
                errors.append(f"{key} musi byc boolean.")
        required_text("redaction_policy", "Redaction policy", 120)
        preview = [
            f"odczyt maksymalnie {limit or '?'} system messages",
            "bez prywatnych maili i chatu",
            "wynik tylko podczas aktywnego dostepu",
        ]
    elif template_id == "arsenal_cleaner":
        success = number_between("success_percent", "Success %", 1, 80)
        detection = number_between("detection_percent", "Detection %", 0, 95)
        required_text("target_policy", "Targets", 100)
        required_text("protected_apps", "Protected apps")
        if not isinstance(blueprint.get("remove_tools_file"), bool):
            errors.append("Remove files/tools entry musi byc boolean.")
        preview = [
            f"szansa usuniecia {success or '?'}%",
            f"wykrycie {detection if detection is not None else '?'}%",
            "chronione aplikacje nie beda kandydatami",
        ]
    else:
        required_text("notes", "Notes")
        preview = ["custom draft bez kompilatora"]

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "preview": preview,
    }


