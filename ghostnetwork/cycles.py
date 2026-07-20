from __future__ import annotations

from collections import Counter
from sqlite3 import IntegrityError

from database import DB_PATH

from .catalog import CATALOG_VERSION, get_catalog, get_catalog_checksum, validate_catalog
from .errors import CycleAlreadyActive, CycleNotFound, InvalidStateTransition, RepositoryIntegrityError
from .repository import GhostNetworkRepository, _clean
from .topology import GhostTopologyService


GHOSTSYSTEM_MAJOR = 1
GHOSTSYSTEM_MINOR = 0
TRANSITIONAL_STATUSES = {"preparing", "active", "transmitting", "stabilizing"}


class GhostCycleService:
    """Domain lifecycle service for GhostNetwork cycles.

    The service owns status transitions and cycle initialization. It does not
    place parts on the map, create drops or render topology.
    """

    ALLOWED_TRANSITIONS = {
        "preparing": {"active", "closed"},
        "active": {"transmitting"},
        "transmitting": {"stabilizing"},
        "stabilizing": {"closed"},
        "closed": set(),
    }

    def __init__(self, repository=None, db_path=DB_PATH):
        self.repository = repository or GhostNetworkRepository(db_path=db_path)

    def format_ghostsystem_version(self, cycle_number):
        return f"{GHOSTSYSTEM_MAJOR}.{GHOSTSYSTEM_MINOR}.{int(cycle_number or 0)}"

    def get_active_cycle(self):
        return self.repository.get_active_cycle()

    def create_cycle(self, signal_number=None, ghostsystem_version=None, topology_seed=""):
        catalog = get_catalog()
        validation = validate_catalog(catalog)
        if not validation.get("ok"):
            raise RepositoryIntegrityError(f"Invalid GhostNetwork catalog: {validation.get('errors')}")
        catalog_version = _clean(catalog.get("catalog_version") or CATALOG_VERSION)
        catalog_checksum = get_catalog_checksum(catalog)
        with self.repository.transaction():
            if self.repository.get_active_cycle():
                raise CycleAlreadyActive("GhostNetwork already has an active or transitional cycle.")
            signal_number = int(signal_number or self._next_signal_number())
            ghostsystem_version = int(ghostsystem_version or signal_number)
            cycle_id = f"ghostnetwork_{signal_number:04d}"
            cycle = self.repository.create_cycle(
                cycle_id=cycle_id,
                signal_number=signal_number,
                ghostsystem_version=ghostsystem_version,
                status="preparing",
                topology_seed=topology_seed or cycle_id,
                catalog_version=catalog_version,
                catalog_checksum=catalog_checksum,
                source_version=self.format_ghostsystem_version(ghostsystem_version),
                next_version="",
            )
            self.repository.create_parts(self._build_cycle_parts(cycle["cycle_id"], catalog, catalog_version))
            integrity = self.validate_cycle_integrity(cycle["cycle_id"], require_catalog=True)
            if not integrity["ok"]:
                raise RepositoryIntegrityError(f"Invalid initialized GhostNetwork cycle: {integrity['errors']}")
            topology = GhostTopologyService(repository=self.repository).generate_topology(cycle["cycle_id"])
            if not topology["validation"]["valid"]:
                raise RepositoryIntegrityError(f"Invalid GhostNetwork topology: {topology['validation']['errors']}")
            cycle = self.activate_cycle(cycle["cycle_id"])
            return {
                "ok": True,
                "created": True,
                "cycle": cycle,
                "parts": self.repository.list_parts(cycle["cycle_id"]),
                "parts_summary": self.get_parts_summary(cycle["cycle_id"]),
                "topology": {
                    "checksum": topology["topology_checksum"],
                    "connections_count": len(topology["connections"]),
                    "valid": topology["validation"]["valid"],
                },
                "catalog_version": catalog_version,
                "catalog_checksum": catalog_checksum,
            }

    def ensure_active_cycle(self):
        active = self.repository.get_active_cycle()
        if active:
            return {
                "ok": True,
                "created": False,
                "cycle": active,
                "parts": self.repository.list_parts(active["cycle_id"]),
                "parts_summary": self.get_parts_summary(active["cycle_id"]),
                "integrity": self.validate_cycle_integrity(active["cycle_id"], require_catalog=bool(active.get("catalog_version"))),
            }
        try:
            return self.create_cycle()
        except CycleAlreadyActive:
            active = self.repository.get_active_cycle()
            if not active:
                raise
            return {
                "ok": True,
                "created": False,
                "cycle": active,
                "parts": self.repository.list_parts(active["cycle_id"]),
                "parts_summary": self.get_parts_summary(active["cycle_id"]),
                "integrity": self.validate_cycle_integrity(active["cycle_id"], require_catalog=bool(active.get("catalog_version"))),
            }

    def activate_cycle(self, cycle_id):
        cycle = self._require_cycle(cycle_id)
        if cycle.get("catalog_version"):
            validation = GhostTopologyService(repository=self.repository).validate_topology(cycle_id)
            if not validation["valid"]:
                raise InvalidStateTransition(f"Cycle cannot become active with invalid topology: {validation['errors']}")
        return self._transition(cycle_id, "active", event_type="ghost.cycle_activated")

    def lock_cycle(self, cycle_id):
        return self._transition(cycle_id, "transmitting", fields={"locked_at": self.repository.now()})

    def begin_stabilization(self, cycle_id):
        return self._transition(cycle_id, "stabilizing", fields={"stabilization_until": ""})

    def close_cycle(self, cycle_id):
        return self._transition(cycle_id, "closed", fields={"closed_at": self.repository.now()})

    def create_next_cycle(self):
        if self.repository.get_active_cycle():
            raise CycleAlreadyActive("Cannot create next GhostNetwork cycle while current cycle is transitional.")
        return self.create_cycle()

    def increment_ghostsystem_version(self, cycle_id):
        cycle = self._require_cycle(cycle_id)
        if cycle["status"] != "closed":
            raise InvalidStateTransition("GhostSystem version can advance only after a closed cycle.")
        return self.format_ghostsystem_version(int(cycle["ghostsystem_version"]) + 1)

    def get_cycle_diagnostics(self, cycle_id=None):
        cycle = self.repository.get_cycle(cycle_id) if cycle_id else self.repository.get_active_cycle()
        if not cycle:
            return {"ok": False, "cycle": None, "reason": "no_cycle"}
        return {
            "ok": True,
            "cycle": cycle,
            "state_version": self.repository.get_state_version(cycle["cycle_id"]),
            "parts_summary": self.get_parts_summary(cycle["cycle_id"]),
            "integrity": self.validate_cycle_integrity(cycle["cycle_id"], require_catalog=bool(cycle.get("catalog_version"))),
        }

    def get_parts_summary(self, cycle_id):
        parts = self.repository.list_parts(cycle_id)
        by_status = Counter(part["status"] for part in parts)
        discovered = sum(
            1
            for part in parts
            if part.get("target_id")
            or part.get("discovered_by")
            or part["status"] in {"public", "contained", "active", "contested", "consumed"}
        )
        return {
            "parts_total": len(parts),
            "parts_pooled": by_status.get("pooled", 0),
            "parts_reserved": by_status.get("reserved", 0),
            "parts_discovered": discovered,
            "parts_public": by_status.get("public", 0),
            "parts_contained": by_status.get("contained", 0),
            "parts_active": by_status.get("active", 0),
            "parts_consumed": by_status.get("consumed", 0),
        }

    def validate_cycle_integrity(self, cycle_id, require_catalog=False):
        cycle = self._require_cycle(cycle_id)
        parts = self.repository.list_parts(cycle_id)
        errors = []
        warnings = []
        catalog = get_catalog()
        catalog_version = _clean(cycle.get("catalog_version"))
        catalog_part_codes = {part["part_code"] for part in catalog.get("parts", [])}
        if require_catalog and not catalog_version:
            errors.append("cycle_missing_catalog_version")
        if catalog_version and catalog_version != CATALOG_VERSION:
            warnings.append("cycle_catalog_version_differs_from_runtime")
        if cycle.get("catalog_checksum") and cycle["catalog_checksum"] != get_catalog_checksum(catalog):
            warnings.append("cycle_catalog_checksum_differs_from_runtime")
        if len(parts) != 20:
            errors.append("cycle_part_count_not_20")
        part_codes = [part["part_code"] for part in parts]
        if len(set(part_codes)) != len(part_codes):
            errors.append("duplicate_part_code")
        if set(part_codes) != catalog_part_codes:
            errors.append("parts_do_not_match_catalog")
        clans = Counter(part["clan_code"] for part in parts)
        machines = Counter(part["machine_code"] for part in parts)
        if len(parts) == 20 and (set(clans.values()) != {5} or set(machines.values()) != {5}):
            errors.append("invalid_part_distribution")
        for part in parts:
            if catalog_version and part.get("catalog_version") != catalog_version:
                errors.append("part_catalog_version_mismatch")
            if part["status"] == "pooled":
                has_anchor = any(
                    part.get(key)
                    for key in (
                        "target_id",
                        "discovered_by",
                        "discovered_at",
                        "territory_id",
                        "territory_owner_id",
                        "territory_clan",
                        "activated_at",
                    )
                ) or part.get("latitude") is not None or part.get("longitude") is not None
                if has_anchor:
                    errors.append("pooled_part_has_anchor")
        return {
            "ok": not errors,
            "errors": sorted(set(errors)),
            "warnings": sorted(set(warnings)),
            "parts_summary": self.get_parts_summary(cycle_id),
            "catalog_version": catalog_version,
            "catalog_checksum": cycle.get("catalog_checksum") or "",
        }

    def _transition(self, cycle_id, next_status, fields=None, event_type="ghost.cycle_status_changed"):
        fields = dict(fields or {})
        with self.repository.transaction():
            cycle = self._require_cycle(cycle_id)
            previous = cycle["status"]
            allowed = self.ALLOWED_TRANSITIONS.get(previous, set())
            if next_status not in allowed:
                raise InvalidStateTransition(f"Invalid GhostNetwork cycle transition: {previous} -> {next_status}")
            updated = self.repository.update_cycle(cycle_id, status=next_status, **fields)
            payload = {
                "previous_status": previous,
                "status": next_status,
                "signal_number": updated["signal_number"],
                "ghostsystem_version": updated["ghostsystem_version"],
                "ghostsystem_version_label": self.format_ghostsystem_version(updated["ghostsystem_version"]),
            }
            self._append_domain_event("ghost.cycle_status_changed", cycle_id, payload)
            if event_type != "ghost.cycle_status_changed":
                self._append_domain_event(event_type, cycle_id, payload)
            return updated

    def _append_domain_event(self, event_type, cycle_id, payload):
        try:
            return self.repository.append_event(
                event_type,
                cycle_id=cycle_id,
                entity_id=cycle_id,
                dedupe_key=f"{event_type}:{cycle_id}:{payload.get('previous_status','')}:{payload.get('status','')}",
                payload=payload,
            )
        except RepositoryIntegrityError as exc:
            if "Duplicate GhostNetwork event" in str(exc):
                return None
            raise

    def _build_cycle_parts(self, cycle_id, catalog, catalog_version):
        parts = []
        for definition in catalog.get("parts", []):
            part_code = _clean(definition.get("part_code"))
            parts.append(
                {
                    "part_id": f"{cycle_id}_{part_code.lower()}",
                    "cycle_id": cycle_id,
                    "part_code": part_code,
                    "clan_code": _clean(definition.get("clan_code")),
                    "machine_code": _clean(definition.get("machine_code")),
                    "profession_code": _clean(definition.get("profession_code")),
                    "status": "pooled",
                    "catalog_version": catalog_version,
                    "target_id": "",
                    "latitude": None,
                    "longitude": None,
                    "discovered_by": "",
                    "discovered_at": "",
                    "territory_id": "",
                    "territory_owner_id": "",
                    "territory_clan": "",
                    "activated_at": "",
                    "deactivated_at": "",
                }
            )
        return parts

    def _next_signal_number(self):
        cycles = self.repository.list_cycles(limit=500)
        if not cycles:
            return 1
        return max(int(cycle.get("signal_number") or 0) for cycle in cycles) + 1

    def _require_cycle(self, cycle_id):
        cycle = self.repository.get_cycle(cycle_id)
        if not cycle:
            raise CycleNotFound(f"Cycle not found: {cycle_id}")
        return cycle


def ensure_active_ghostnetwork_cycle(repository=None, db_path=DB_PATH):
    return GhostCycleService(repository=repository, db_path=db_path).ensure_active_cycle()
