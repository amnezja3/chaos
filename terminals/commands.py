from database import JsonResourceStore


resource_store = JsonResourceStore()


def interpret_command(text, user_profile):
    text = text.strip().lower()
    if text in {"exit", "logout"}:
        return {"logout": True}

    parts = text.split()
    if len(parts) == 3 and parts[0] == "sudo" and parts[1] == "userdel":
        return {"confirm_userdel": parts[2]}

    terminal_data = resource_store.get(
        "terminal_command",
        default={}
    )

    if not terminal_data:
        return {"response": "Błąd terminala: brak komend terminala"}

    app_data = user_profile

    if text in terminal_data:
        cmd = terminal_data[text]
        if cmd.get("type") == "system":
            return {"response": cmd.get("result", "⛔ Brak odpowiedzi.")}

    matching_app = next(
        (a for a in app_data if a["name"].lower() == text or a["id"].lower() == text),
        None
    )
    if matching_app:
        return {"runApp": matching_app["id"]}

    return {"response": f"Nieznana komenda: {text}"}
