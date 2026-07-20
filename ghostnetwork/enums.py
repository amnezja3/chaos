"""Canonical GhostNetwork domain constants."""

CYCLE_STATUSES = {
    "preparing",
    "active",
    "transmitting",
    "stabilizing",
    "closed",
}

BLOCKING_CYCLE_STATUSES = {
    "preparing",
    "active",
    "transmitting",
    "stabilizing",
}

PART_STATUSES = {
    "pooled",
    "reserved",
    "public",
    "contained",
    "active",
    "consumed",
}

PART_CONFLICT_STATES = {
    "none",
    "contested",
}

PART_MODULE_STATES = {
    "neutral",
    "blocked",
    "active",
}

PART_VIEWER_RELATIONS = {
    "public_neutral",
    "self_foreign_blocked",
    "self_own_active",
    "clan_own_active",
    "foreign_blocked",
    "foreign_active",
}

RESERVATION_STATUSES = {
    "active",
    "committed",
    "released",
    "expired",
    "cancelled",
}

AUDIENCE_SCOPES = {
    "internal",
    "system",
    "public",
    "clan",
    "owner",
    "player",
}

GHOSTNETWORK_SCOPE = "ghostnetwork"
