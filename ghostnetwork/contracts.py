"""Small GhostNetwork service contracts for future integrations."""

from .catalog import normalize_ghostnetwork_profile_identity

FUTURE_HOOKS = (
    "on_target_aimed",
    "on_target_hacked",
    "on_territory_event",
    "resolve_part_state",
    "attempt_transmission",
)


def normalize_ghost_clan(profile):
    """Return canonical catalog clan code without mutating a profile."""
    return normalize_ghostnetwork_profile_identity(profile)["clan_code"] or ""


def normalize_ghost_profession(profile):
    """Return canonical catalog profession code without mutating a profile."""
    return normalize_ghostnetwork_profile_identity(profile)["profession_code"] or ""
