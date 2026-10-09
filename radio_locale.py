"""Language contracts for radio. Unknown audio is never implicitly neutral."""

from ghost_i18n import approved_locales, radio_locale_filters


def language(value):
    allowed = (*approved_locales("radio"), "neutral", "mixed", "unknown")
    return value if isinstance(value, str) and value in allowed else "unknown"


def channel_metadata(channel):
    result = dict(channel)
    result["language"] = language(channel.get("language"))
    return result


def track_metadata(channel, filename):
    entries = channel.get("programs")
    entry = entries.get(filename, {}) if isinstance(entries, dict) else {}
    entry = entry if isinstance(entry, dict) else {}
    return {"language": language(entry.get("language"))}


def track_allowed(channel, track):
    channel_language = language(channel.get("language"))
    program_language = language(track.get("language"))
    if channel_language in approved_locales("radio"):
        return program_language in (channel_language, "neutral")
    if channel_language == "neutral":
        return program_language == "neutral"
    return True


def matches_filter(channel, selected):
    if selected not in radio_locale_filters():
        raise ValueError("invalid_radio_filter")
    return selected == "ANY" or language(channel.get("language")) in (selected, "neutral")


def validate_contract(channel):
    """Strict for publishing; legacy reads safely project missing fields as unknown."""
    if channel.get("language") != language(channel.get("language")):
        raise ValueError("invalid_channel_language")
    programs = channel.get("programs", {})
    if not isinstance(programs, dict):
        raise ValueError("invalid_radio_programs")
    for filename, entry in programs.items():
        if not isinstance(filename, str) or not filename.lower().endswith(".mp3") or "/" in filename or "\\" in filename:
            raise ValueError("invalid_program_filename")
        if not isinstance(entry, dict) or entry.get("language") != language(entry.get("language")):
            raise ValueError("invalid_program_language")
        if not track_allowed(channel, entry):
            raise ValueError("program_language_conflict")
    return channel
