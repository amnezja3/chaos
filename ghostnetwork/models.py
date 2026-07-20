from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GhostCycle:
    cycle_id: str
    signal_number: int
    ghostsystem_version: int
    status: str
    topology_seed: str
    topology_checksum: str = ""
    catalog_version: str = ""
    catalog_checksum: str = ""
    source_version: str = ""
    next_version: str = ""
    state_version: int = 0
    started_at: str = ""
    locked_at: str = ""
    transmitted_at: str = ""
    stabilization_until: str = ""
    closed_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GhostPart:
    part_id: str
    cycle_id: str
    part_code: str
    clan_code: str
    machine_code: str
    profession_code: str
    status: str
    catalog_version: str = ""
    target_id: str = ""
    latitude: float | None = None
    longitude: float | None = None
    discovered_by: str = ""
    discovered_at: str = ""
    territory_id: str = ""
    territory_owner_id: str = ""
    territory_clan: str = ""
    activated_at: str = ""
    deactivated_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GhostReservation:
    reservation_id: str
    cycle_id: str
    part_id: str
    target_id: str
    player_id: str
    player_clan: str
    status: str
    reserved_at: str
    expires_at: str
    committed_at: str = ""
    released_at: str = ""
    operation_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GhostConnection:
    connection_id: str
    cycle_id: str
    part_a_id: str
    part_b_id: str
    position_in_ring: int
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GhostNetworkSnapshot:
    cycle: dict[str, Any] | None
    parts: list[dict[str, Any]] = field(default_factory=list)
    connections: list[dict[str, Any]] = field(default_factory=list)
    topology: dict[str, Any] = field(default_factory=dict)
    active_reservations: list[dict[str, Any]] = field(default_factory=list)
    state_version: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
