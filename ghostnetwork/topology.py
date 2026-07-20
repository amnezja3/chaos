from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict, deque

from database import DB_PATH

from .catalog import CATALOG_VERSION, TOPOLOGY_ANCHOR, get_catalog
from .errors import CycleNotFound, RepositoryIntegrityError, TopologyGenerationError
from .repository import GhostNetworkRepository, _clean


class GhostTopologyService:
    """Internal topology service for the GhostNetwork closed ring.

    The topology is logical infrastructure only. It does not expose map lines,
    discovery, drops or visibility projection.
    """

    REQUIRED_PARTS = 20
    REQUIRED_CONNECTIONS = 20
    MAX_GENERATION_ATTEMPTS = 256

    def __init__(self, repository=None, db_path=DB_PATH):
        self.repository = repository or GhostNetworkRepository(db_path=db_path)

    def generate_topology(self, cycle_id):
        cycle = self._require_cycle(cycle_id)
        existing = self.repository.list_connections(cycle["cycle_id"])
        if existing:
            validation = self.validate_topology(cycle["cycle_id"])
            if validation["valid"]:
                return {
                    "ok": True,
                    "created": False,
                    "cycle_id": cycle["cycle_id"],
                    "topology_checksum": validation["topology_checksum"],
                    "ring_order": validation["ring_order"],
                    "connections": existing,
                    "validation": validation,
                }
            raise RepositoryIntegrityError(f"Existing GhostNetwork topology is invalid: {validation['errors']}")

        parts = self.repository.list_parts(cycle["cycle_id"])
        if len(parts) != self.REQUIRED_PARTS:
            raise TopologyGenerationError("GhostNetwork topology requires exactly 20 parts.")
        part_by_code = {part["part_code"]: part for part in parts}
        ring_codes = self._build_ring_codes(cycle, parts)
        ring_parts = [part_by_code[code] for code in ring_codes]
        self._validate_ring_candidates(ring_parts)
        checksum = self.calculate_topology_checksum(ring_codes)

        with self.repository.transaction():
            created_connections = []
            for position, part in enumerate(ring_parts):
                neighbor = ring_parts[(position + 1) % len(ring_parts)]
                created_connections.append(
                    self.repository.create_connection(
                        cycle["cycle_id"],
                        part["part_id"],
                        neighbor["part_id"],
                        position_in_ring=position,
                    )
                )
            self.repository.update_cycle(cycle["cycle_id"], topology_checksum=checksum)
            state_version = self.repository.get_state_version(cycle["cycle_id"])
            self.repository.append_event(
                "ghost.topology_created",
                cycle_id=cycle["cycle_id"],
                entity_id=cycle["cycle_id"],
                state_version=state_version,
                dedupe_key=f"ghost:topology_created:{cycle['cycle_id']}:{checksum}",
                payload={
                    "cycle_id": cycle["cycle_id"],
                    "topology_seed": cycle.get("topology_seed") or "",
                    "topology_checksum": checksum,
                    "nodes_count": len(ring_parts),
                    "connections_count": len(created_connections),
                    "catalog_version": cycle.get("catalog_version") or "",
                    "state_version": state_version,
                },
            )
            validation = self.validate_topology(cycle["cycle_id"])
            if not validation["valid"]:
                raise TopologyGenerationError(f"Generated topology failed validation: {validation['errors']}")
            return {
                "ok": True,
                "created": True,
                "cycle_id": cycle["cycle_id"],
                "topology_checksum": checksum,
                "ring_order": validation["ring_order"],
                "connections": created_connections,
                "validation": validation,
            }

    def validate_topology(self, cycle_id):
        cycle = self._require_cycle(cycle_id)
        parts = self.repository.list_parts(cycle["cycle_id"])
        connections = self.repository.list_connections(cycle["cycle_id"])
        part_by_id = {part["part_id"]: part for part in parts}
        errors = []
        degree = Counter()
        adjacency = defaultdict(set)
        duplicate_edges = []
        same_clan_edges = []
        self_loops = []
        invalid_endpoints = []
        positions = []
        edge_keys = set()
        ordered_edges = []

        if len(parts) != self.REQUIRED_PARTS:
            errors.append("topology_node_count_not_20")
        if len(connections) != self.REQUIRED_CONNECTIONS:
            errors.append("topology_connection_count_not_20")

        for connection in connections:
            a_id = connection["part_a_id"]
            b_id = connection["part_b_id"]
            positions.append(int(connection["position_in_ring"]))
            if a_id == b_id:
                self_loops.append(connection["connection_id"])
                errors.append("topology_self_loop")
                continue
            if a_id not in part_by_id or b_id not in part_by_id:
                invalid_endpoints.append(connection["connection_id"])
                errors.append("topology_invalid_endpoint")
                continue
            edge_key = tuple(sorted((a_id, b_id)))
            if edge_key in edge_keys:
                duplicate_edges.append(connection["connection_id"])
                errors.append("topology_duplicate_edge")
            edge_keys.add(edge_key)
            if part_by_id[a_id]["clan_code"] == part_by_id[b_id]["clan_code"]:
                same_clan_edges.append(connection["connection_id"])
                errors.append("topology_same_clan_edge")
            degree[a_id] += 1
            degree[b_id] += 1
            adjacency[a_id].add(b_id)
            adjacency[b_id].add(a_id)
            ordered_edges.append((int(connection["position_in_ring"]), a_id, b_id))

        if len(set(positions)) != len(positions):
            errors.append("topology_duplicate_position")
        if connections and sorted(positions) != list(range(len(connections))):
            errors.append("topology_position_gap")

        degree_errors = {
            part_id: degree.get(part_id, 0)
            for part_id in part_by_id
            if degree.get(part_id, 0) != 2
        }
        if degree_errors:
            errors.append("topology_degree_not_2")

        components = self._connected_components(part_by_id, adjacency)
        if len(components) != 1:
            errors.append("topology_not_connected")

        ring_order = self._derive_ring_order(parts, adjacency)
        if len(ring_order) != len(parts):
            errors.append("topology_ring_order_incomplete")
        if ring_order and ring_order[0] not in adjacency.get(ring_order[-1], set()):
            errors.append("topology_ring_order_not_closed")

        anchor_errors = self._validate_anchor_edges(part_by_id, adjacency)
        if anchor_errors:
            errors.append("topology_missing_anchor")

        ring_codes = [part_by_id[part_id]["part_code"] for part_id in ring_order if part_id in part_by_id]
        topology_checksum = self.calculate_topology_checksum(ring_codes) if len(ring_codes) == len(parts) else ""
        checksum_match = bool(topology_checksum and topology_checksum == (cycle.get("topology_checksum") or ""))
        if cycle.get("topology_checksum") and topology_checksum and not checksum_match:
            errors.append("topology_checksum_mismatch")

        return {
            "valid": not errors,
            "ok": not errors,
            "cycle_id": cycle["cycle_id"],
            "nodes": len(parts),
            "connections": len(connections),
            "connected_components": len(components),
            "degree_errors": degree_errors,
            "same_clan_edges": same_clan_edges,
            "duplicate_edges": duplicate_edges,
            "missing_parts": sorted(part["part_id"] for part in parts if degree.get(part["part_id"], 0) == 0),
            "anchor_errors": anchor_errors,
            "checksum_match": checksum_match,
            "topology_checksum": topology_checksum,
            "stored_topology_checksum": cycle.get("topology_checksum") or "",
            "ring_order": ring_order,
            "ring_codes": ring_codes,
            "errors": sorted(set(errors)),
        }

    def get_neighbors(self, part_id):
        part_id = _clean(part_id)
        active = self.repository.get_active_cycle()
        cycle_id = active["cycle_id"] if active else ""
        if not cycle_id:
            return []
        neighbors = []
        for connection in self.repository.list_connections(cycle_id):
            if connection["part_a_id"] == part_id:
                neighbors.append(connection["part_b_id"])
            elif connection["part_b_id"] == part_id:
                neighbors.append(connection["part_a_id"])
        return sorted(neighbors)

    def list_connections(self, cycle_id):
        return self.repository.list_connections(cycle_id)

    def get_ring_order(self, cycle_id):
        return self.validate_topology(cycle_id)["ring_order"]

    def resolve_connection_state(self, part_a, part_b):
        status_a = _clean((part_a or {}).get("status"))
        status_b = _clean((part_b or {}).get("status"))
        discovered_a = self._is_discovered(part_a)
        discovered_b = self._is_discovered(part_b)
        active_a = status_a == "active"
        active_b = status_b == "active"
        if not discovered_a and not discovered_b:
            return "hidden"
        if active_a and discovered_b and not active_b:
            return "half_from_a"
        if active_b and discovered_a and not active_a:
            return "half_from_b"
        if active_a and active_b:
            return "active"
        if discovered_a and discovered_b:
            return "inactive"
        return "hidden"

    def calculate_topology_checksum(self, ring_codes):
        edges = [
            {
                "position": index,
                "a": _clean(ring_codes[index]),
                "b": _clean(ring_codes[(index + 1) % len(ring_codes)]),
            }
            for index in range(len(ring_codes))
        ]
        payload = json.dumps(edges, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _build_ring_codes(self, cycle, parts):
        catalog = get_catalog()
        canonical = list(catalog.get("topology_anchor") or TOPOLOGY_ANCHOR)
        available = {part["part_code"] for part in parts}
        if int(cycle.get("ghostsystem_version") or 0) <= 1 and set(canonical) == available:
            return canonical
        seed = "|".join(
            [
                _clean(cycle.get("topology_seed") or cycle["cycle_id"]),
                _clean(cycle.get("catalog_version") or CATALOG_VERSION),
                str(cycle.get("ghostsystem_version") or ""),
            ]
        )
        for attempt in range(self.MAX_GENERATION_ATTEMPTS):
            rng = random.Random(f"{seed}:{attempt}")
            shuffled = list(parts)
            rng.shuffle(shuffled)
            codes = [part["part_code"] for part in shuffled]
            part_by_code = {part["part_code"]: part for part in shuffled}
            candidate = [part_by_code[code] for code in codes]
            if self._ring_has_same_clan_neighbor(candidate):
                continue
            if not self._codes_have_required_anchor(codes):
                continue
            return codes
        raise TopologyGenerationError("Could not generate a valid GhostNetwork topology.")

    def _validate_ring_candidates(self, ring_parts):
        if len(ring_parts) != self.REQUIRED_PARTS:
            raise TopologyGenerationError("Topology ring must contain exactly 20 parts.")
        if len({part["part_id"] for part in ring_parts}) != len(ring_parts):
            raise TopologyGenerationError("Topology ring contains duplicate parts.")
        if self._ring_has_same_clan_neighbor(ring_parts):
            raise TopologyGenerationError("Topology ring connects parts from the same clan.")
        if not self._codes_have_required_anchor([part["part_code"] for part in ring_parts]):
            raise TopologyGenerationError("Topology ring misses required anchor edge.")

    def _ring_has_same_clan_neighbor(self, ring_parts):
        return any(
            ring_parts[index]["clan_code"] == ring_parts[(index + 1) % len(ring_parts)]["clan_code"]
            for index in range(len(ring_parts))
        )

    def _codes_have_required_anchor(self, codes):
        if len(TOPOLOGY_ANCHOR) < 2:
            return True
        required = frozenset((TOPOLOGY_ANCHOR[0], TOPOLOGY_ANCHOR[1]))
        return any(
            frozenset((codes[index], codes[(index + 1) % len(codes)])) == required
            for index in range(len(codes))
        )

    def _validate_anchor_edges(self, part_by_id, adjacency):
        if len(TOPOLOGY_ANCHOR) < 2:
            return []
        code_to_id = {part["part_code"]: part_id for part_id, part in part_by_id.items()}
        a_id = code_to_id.get(TOPOLOGY_ANCHOR[0])
        b_id = code_to_id.get(TOPOLOGY_ANCHOR[1])
        if not a_id or not b_id:
            return [f"{TOPOLOGY_ANCHOR[0]}:{TOPOLOGY_ANCHOR[1]}"]
        if b_id not in adjacency.get(a_id, set()):
            return [f"{TOPOLOGY_ANCHOR[0]}:{TOPOLOGY_ANCHOR[1]}"]
        return []

    def _connected_components(self, part_by_id, adjacency):
        unseen = set(part_by_id)
        components = []
        while unseen:
            start = unseen.pop()
            component = {start}
            queue = deque([start])
            while queue:
                node = queue.popleft()
                for neighbor in adjacency.get(node, set()):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.add(neighbor)
                        queue.append(neighbor)
            components.append(component)
        return components

    def _derive_ring_order(self, parts, adjacency):
        if not parts:
            return []
        part_by_id = {part["part_id"]: part for part in parts}
        part_by_code = {part["part_code"]: part for part in parts}
        start = part_by_code.get(TOPOLOGY_ANCHOR[0], sorted(parts, key=lambda item: item["part_code"])[0])
        order = [start["part_id"]]
        previous = None
        current = start["part_id"]
        preferred = part_by_code.get(TOPOLOGY_ANCHOR[1])
        if preferred and preferred["part_id"] in adjacency.get(current, set()):
            previous, current = current, preferred["part_id"]
            order.append(current)
        while len(order) < len(parts):
            neighbors = sorted(
                adjacency.get(current, set()),
                key=lambda part_id: part_by_id.get(part_id, {}).get("part_code", part_id),
            )
            candidates = [neighbor for neighbor in neighbors if neighbor != previous]
            next_id = None
            for candidate in candidates:
                if candidate not in order or (len(order) == len(parts) - 1 and order[0] in adjacency.get(candidate, set())):
                    next_id = candidate
                    break
            if not next_id or next_id in order:
                break
            previous, current = current, next_id
            order.append(current)
        return order

    def _part_code(self, parts, part_id):
        for part in parts:
            if part["part_id"] == part_id:
                return part["part_code"]
        return ""

    def _is_discovered(self, part):
        part = part or {}
        return bool(
            part.get("target_id")
            or part.get("discovered_by")
            or part.get("discovered_at")
            or part.get("status") in {"public", "contained", "active", "contested", "consumed"}
        )

    def _require_cycle(self, cycle_id):
        cycle = self.repository.get_cycle(cycle_id)
        if not cycle:
            raise CycleNotFound(f"GhostNetwork cycle not found: {cycle_id}")
        return cycle
