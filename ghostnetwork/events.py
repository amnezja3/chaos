from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GhostNetworkEvent:
    event_id: str
    event_type: str
    cycle_id: str
    part_id: str = ""
    entity_id: str = ""
    state_version: int = 0
    audience_scope: str = "system"
    audience_clan: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    dedupe_key: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
