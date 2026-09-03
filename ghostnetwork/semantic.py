from __future__ import annotations

from .catalog import get_catalog
from .llm.semantic_input import attach_semantic_content, normalize_location


GHOST_EVENT_STATEMENTS = {
    "part_discovered": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
    "part_contained": "Element GhostNetwork znalazł się wewnątrz kontrolowanego terytorium.",
    "part_activated": "Element GhostNetwork został aktywowany przez prawidłowe otoczenie terytorium.",
    "part_deactivated": "Element GhostNetwork utracił aktywny stan.",
    "part_revealed": "Ukryta tożsamość elementu GhostNetwork została ujawniona.",
    "part_contested": "Kontrola nad elementem GhostNetwork została zakwestionowana.",
    "part_conflict_resolved": "Konflikt o element GhostNetwork został rozstrzygnięty.",
    "part_recovered": "Kontrola nad elementem GhostNetwork została odzyskana.",
    "part_defended": "Próba przejęcia elementu GhostNetwork została odparta.",
    "machine_progress_changed": "Zmienił się postęp składania maszyny GhostNetwork.",
    "machine_online": "Maszyna GhostNetwork osiągnęła stan online.",
    "machine_offline": "Maszyna GhostNetwork utraciła stan online.",
    "connection_created": "Utworzono nowe połączenie pomiędzy elementami GhostNetwork.",
    "cycle_locked": "Bieżący cykl GhostNetwork został nieodwracalnie zamknięty.",
    "version_changed": "Ghost System przeszedł do kolejnej wersji.",
    "stabilization_started": "Rozpoczęła się stabilizacja zamkniętej sieci GhostNetwork.",
    "cycle_activated": "Nowy cykl GhostNetwork został aktywowany.",
    "signal_sent": "GhostSignal został wysłany z zamkniętej sieci.",
    "network_closed": "Sieć GhostNetwork osiągnęła pełne zamknięcie.",
    "restart_required": "Ghost System wymaga przejścia do kolejnego cyklu.",
}

PUBLIC_TARGET_LABEL_FAMILIES = {
    "part_discovered", "part_activated", "part_deactivated", "part_revealed",
    "part_recovered", "part_defended",
}


def _clean(value):
    return str(value or "").strip()


def _event_kind(event_type):
    return _clean(event_type).removeprefix("ghost.")


def _attribute(name, value):
    if value in (None, ""):
        return None
    return {"name": name, "value": value}


class GhostNetworkSemanticConverter:
    """Deterministic GhostNetwork canonical-data to semantic-fact converter."""

    def __init__(self):
        catalog = get_catalog()
        self.clans = {item["code"]: item for item in catalog.get("clans", [])}
        self.machines = {item["code"]: item for item in catalog.get("machines", [])}
        self.parts = {item["part_code"]: item for item in catalog.get("parts", [])}

    @staticmethod
    def _anchor(event, part):
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        event_anchor = payload.get("anchor") if isinstance(payload.get("anchor"), dict) else {}
        part_anchor = part.get("anchor_snapshot") if isinstance(part.get("anchor_snapshot"), dict) else {}
        return {**part_anchor, **event_anchor}

    @staticmethod
    def _location(anchor):
        location = anchor.get("location") if isinstance(anchor.get("location"), dict) else {}
        return normalize_location(location)

    @staticmethod
    def _target_label(anchor):
        for key in ("label", "display_label", "name", "title"):
            value = _clean(anchor.get(key))
            if value and value.lower() not in {"unknown", "target"}:
                return value
        return ""

    def _catalog_labels(self, part):
        part_catalog = self.parts.get(_clean(part.get("part_code")), {})
        machine_catalog = self.machines.get(_clean(part.get("machine_code")), {})
        clan_catalog = self.clans.get(_clean(part.get("clan_code")), {})
        return {
            "part": _clean(part_catalog.get("name")),
            "machine": _clean(machine_catalog.get("name")),
            "clan": _clean(clan_catalog.get("name")),
        }

    def enrich(self, fact, event, audience, part=None, projected=None):
        fact = fact if isinstance(fact, dict) else {}
        event = event if isinstance(event, dict) else {}
        audience = audience if isinstance(audience, dict) else {}
        part = part if isinstance(part, dict) else {}
        projected = projected if isinstance(projected, dict) else {}
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        kind = _clean(fact.get("fact_type")) or _event_kind(event.get("event_type"))
        statement = GHOST_EVENT_STATEMENTS.get(kind)
        if not statement:
            raise ValueError(f"ghost_semantic_event_family_unsupported:{kind}")

        content = {"statement": statement}
        provenance = [{
            "semantic_path": "statement",
            "source_path": "ghost_part_events.event_type",
        }]
        entities = []
        anchor = self._anchor(event, part)
        target_label = self._target_label(anchor)
        scope = _clean(audience.get("scope")) or "public"

        if target_label and (scope in {"owner", "clan"} or kind in PUBLIC_TARGET_LABEL_FAMILIES):
            entities.append({
                "role": "lokalizacja zakotwiczenia zdarzenia",
                "kind": "target", "label": target_label,
            })
            provenance.append({
                "semantic_path": "entities[target].label",
                "source_path": "ghost_part_events.payload.anchor.label|ghost_parts.anchor_snapshot.label",
            })

        labels = self._catalog_labels(part)
        if scope == "owner":
            owner_entities = (
                ("element sieci", "part", labels["part"], "ghost_parts.part_code->catalog.parts.name"),
                ("maszyna powiązana z elementem", "machine", labels["machine"], "ghost_parts.machine_code->catalog.machines.name"),
                ("klan elementu", "clan", labels["clan"], "ghost_parts.clan_code->catalog.clans.name"),
            )
            if kind == "part_discovered":
                owner_entities = owner_entities[:1]
            for role, entity_kind, label, source_path in owner_entities:
                if label:
                    entities.append({"role": role, "kind": entity_kind, "label": label})
                    provenance.append({
                        "semantic_path": f"entities[{entity_kind}].label",
                        "source_path": source_path,
                    })
        elif scope == "clan" and kind != "part_discovered":
            visible_clan_code = _clean(projected.get("target_clan"))
            audience_clan = _clean(audience.get("clan"))
            if visible_clan_code and visible_clan_code == audience_clan:
                clan_label = _clean((self.clans.get(visible_clan_code) or {}).get("name"))
                if clan_label:
                    entities.append({
                        "role": "klan odbiorcy", "kind": "clan", "label": clan_label,
                    })
                    provenance.append({
                        "semantic_path": "entities[clan].label",
                        "source_path": "audience.clan->catalog.clans.name",
                    })

        if entities:
            content["entities"] = entities

        location = self._location(anchor)
        if location and (scope in {"owner", "clan"} or kind in PUBLIC_TARGET_LABEL_FAMILIES):
            content["location"] = location
            for key in sorted(location):
                provenance.append({
                    "semantic_path": f"location.{key}",
                    "source_path": f"ghost_part_events.payload.anchor.location.{key}",
                })

        attributes = []
        attribute_sources = (
            ("stan", projected.get("status") or payload.get("status"), "projected.status"),
            ("poprzedni stan", projected.get("previous_status") or payload.get("previous_status"), "projected.previous_status"),
            ("stan konfliktu", projected.get("conflict_state") or payload.get("conflict_state"), "projected.conflict_state"),
            ("liczba aktywnych części", payload.get("active_parts"), "ghost_part_events.payload.active_parts"),
            ("liczba zdarzeń", fact.get("event_count"), "ghost_narrative_outbox.facts.event_count"),
            ("liczba części", fact.get("part_count"), "ghost_narrative_outbox.facts.part_count"),
            ("liczba połączeń", fact.get("connection_count"), "ghost_narrative_outbox.facts.connection_count"),
            ("liczba maszyn", fact.get("machine_count"), "ghost_narrative_outbox.facts.machine_count"),
            ("wynik", fact.get("outcome"), "ghost_narrative_outbox.facts.outcome"),
        )
        for name, value, source_path in attribute_sources:
            item = _attribute(name, value)
            if item:
                attributes.append(item)
                provenance.append({
                    "semantic_path": f"attributes.{name}",
                    "source_path": source_path,
                })
        if attributes:
            content["attributes"] = attributes

        return attach_semantic_content(fact, content, provenance)
