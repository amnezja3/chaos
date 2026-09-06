from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone


ALLOWED_REALIZER_FAMILIES = (
    "operation_speed",
    "file_yield",
    "data_quality",
    "hack_actions",
    "target_security",
    "operation_risk",
    "scan_range",
    "map_zoom",
    "territory_defense",
)

DEFERRED_REALIZER_FAMILIES = (
    "file_value",
    "actor_visibility",
    "incident_decoy",
)

ACTION_KEYS = ("scan_ports", "exploit", "sniff", "trace")
QUALITY_CATEGORIES = {"audio", "camera", "credentials"}
MAX_ACTIVE_OPERATIONS = 8
MAX_OPERATION_SPEED_FACTOR = 20.0
OPERATION_SPEED_POLICIES = {
    "insider_feed": {
        "level_multiplier": 0.1,
        "minimum_factor": 1.0,
        "maximum_factor": MAX_OPERATION_SPEED_FACTOR,
    },
    "operational_prediction": {
        "level_multiplier": 0.1,
        "minimum_factor": 1.0,
        "maximum_factor": MAX_OPERATION_SPEED_FACTOR,
    },
}
OPERATION_RISK_POLICIES = {
    "false_image": {"ability_heat_modifier": -15},
    "narrative_takeover": {"ability_heat_modifier": -15},
}
DATA_QUALITY_POLICIES = {
    "full_disclosure": {
        "base_bonus": 10,
        "priority_bonus": 30,
        "priority_categories": ("audio", "camera", "network", "personal"),
        "max_files": 16,
    },
}
FILE_YIELD_COPY_VARIANTS = ("backup", "fullbackup")
MAX_BONUS_FILES_PER_SOURCE = len(FILE_YIELD_COPY_VARIANTS)
MAX_QUALITY_FILES = 16
MAX_SECURITY_CHANGES = 2
SCAN_RANGE_METERS_PER_LEVEL = 25_000
MAX_SCAN_RANGE_METERS = 10_000_000


def _clamp_int(value, minimum, maximum):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = minimum
    return max(minimum, min(maximum, value))


def _parse_datetime(value):
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_datetime(value):
    return value.astimezone(timezone.utc).isoformat()


def _stable_id(*parts):
    raw = ":".join(str(part or "") for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:18]


def calculate_operation_speed_factor(level_snapshot, ability_code="insider_feed"):
    """Return the backend-owned multiplier for one speed ability snapshot."""
    try:
        level = float(level_snapshot or 1)
    except (TypeError, ValueError):
        level = 1.0
    policy = OPERATION_SPEED_POLICIES.get(str(ability_code or "").strip())
    policy = policy or OPERATION_SPEED_POLICIES["insider_feed"]
    return max(
        policy["minimum_factor"],
        min(policy["maximum_factor"], level * policy["level_multiplier"]),
    )


def calculate_scan_range_m(level_snapshot, ability_code="resistance_signal"):
    """Return the frozen, backend-owned scan invocation range for E4."""
    if str(ability_code or "").strip() != "resistance_signal":
        return 0
    level = _clamp_int(
        level_snapshot, 1,
        MAX_SCAN_RANGE_METERS // SCAN_RANGE_METERS_PER_LEVEL,
    )
    return min(MAX_SCAN_RANGE_METERS, SCAN_RANGE_METERS_PER_LEVEL * level)


def operation_risk_modifier(ability_code):
    """Return one backend-owned heat modifier for a supported risk ability."""
    policy = OPERATION_RISK_POLICIES.get(str(ability_code or "").strip())
    return int((policy or OPERATION_RISK_POLICIES["false_image"])["ability_heat_modifier"])


def data_quality_policy(ability_code):
    """Return one copy of the backend-owned quality policy."""
    policy = DATA_QUALITY_POLICIES.get(str(ability_code or "").strip()) or {}
    return {
        "base_bonus": _clamp_int(policy.get("base_bonus"), 0, 100),
        "priority_bonus": _clamp_int(policy.get("priority_bonus"), 0, 100),
        "priority_categories": tuple(policy.get("priority_categories") or ()),
        "max_files": max(1, min(int(policy.get("max_files") or 1), MAX_QUALITY_FILES)),
    }


def _operation_speed(state, window):
    operations = state.setdefault("operations", [])
    now = _parse_datetime(window["activated_at"])
    ability_code = str(window.get("ability_code") or "insider_feed").strip()
    factor = calculate_operation_speed_factor(window.get("level_snapshot"), ability_code)
    marker = f'{window["window_id"]}:operation_speed'
    changed = []
    for operation in operations[:MAX_ACTIVE_OPERATIONS]:
        markers = operation.setdefault("ability_application_keys", [])
        if marker in markers or str(operation.get("status") or "") not in {
            "active", "running", "processing", "in_progress",
        }:
            continue
        expires_at = _parse_datetime(operation["expires_at"])
        remaining = max(0.0, (expires_at - now).total_seconds())
        operation["expires_at"] = _iso_datetime(
            now + max(expires_at - now, timedelta(0)) / factor
        )
        operation["remaining_seconds"] = round(remaining / factor)
        markers.append(marker)
        if ability_code == "operational_prediction":
            operation["operation_speed_provenance"] = {
                "ability_code": ability_code,
                "window_id": window["window_id"],
                "family": "operation_speed",
                "factor": factor,
            }
        changed.append(str(operation.get("operation_id") or ""))
    return {"changed": changed, "factor": factor, "bounded_limit": MAX_ACTIVE_OPERATIONS}


def apply_operation_speed_to_new_operation(operation, window):
    """Apply Insider Feed once while constructing a new canonical operation."""
    operation = operation if isinstance(operation, dict) else {}
    window = window if isinstance(window, dict) else {}
    ability_code = str(window.get("ability_code") or "").strip()
    if ability_code not in OPERATION_SPEED_POLICIES or not window.get("window_id"):
        return False
    try:
        started_at = _parse_datetime(operation.get("started_at"))
        expires_at = _parse_datetime(operation.get("expires_at"))
        window_start = _parse_datetime(window.get("activated_at"))
        window_end = _parse_datetime(window.get("expires_at"))
    except (TypeError, ValueError):
        return False
    if started_at < window_start or started_at >= window_end or expires_at <= started_at:
        return False
    marker = f'{window["window_id"]}:operation_speed'
    markers = operation.get("ability_application_keys")
    markers = list(markers) if isinstance(markers, list) else []
    if marker in markers:
        return False
    factor = calculate_operation_speed_factor(window.get("level_snapshot"), ability_code)
    duration = max(1, round((expires_at - started_at).total_seconds() / factor))
    operation["expires_at"] = _iso_datetime(started_at + timedelta(seconds=duration))
    operation["duration_seconds"] = duration
    markers.append(marker)
    operation["ability_application_keys"] = markers
    operation["ability_provenance"] = {
        "ability_code": ability_code,
        "window_id": window["window_id"],
        "family": "operation_speed",
        "factor": factor,
    }
    if ability_code == "operational_prediction":
        operation["operation_speed_provenance"] = dict(operation["ability_provenance"])
    return True


def _file_yield_window_id(operation):
    provenance = (
        operation.get("file_yield_provenance")
        if isinstance((operation or {}).get("file_yield_provenance"), dict)
        else {}
    )
    window_id = str(provenance.get("window_id") or "").strip()
    if window_id:
        return window_id
    markers = operation.get("ability_application_keys")
    markers = markers if isinstance(markers, list) else []
    for marker in reversed(markers):
        marker = str(marker or "")
        if marker.endswith(":file_yield"):
            return marker[:-len(":file_yield")]
    return ""


def _file_yield_copy_name(value, variant):
    value = str(value or "").strip()
    if not value:
        return value
    head, separator, tail = value.rpartition(".")
    if not separator or not head:
        return f"{value}.{variant}"
    return f"{head}.{variant}.{tail}"


def replicate_file_yield_files(operation, files):
    """Return two sellable file copies per base artifact for a touched operation."""
    operation = operation if isinstance(operation, dict) else {}
    window_id = _file_yield_window_id(operation)
    if not window_id:
        return []
    copies = []
    existing_ids = {
        str(item.get("id") or item.get("file_id") or "")
        for item in files or [] if isinstance(item, dict)
    }
    for source in list(files or []):
        if (
            not isinstance(source, dict)
            or source.get("copy_variant") in FILE_YIELD_COPY_VARIANTS
            or source.get("sellable") is False
        ):
            continue
        source_id = str(source.get("id") or source.get("file_id") or "").strip()
        if not source_id:
            continue
        for variant in FILE_YIELD_COPY_VARIANTS:
            copy_id = "ghost_copy_" + _stable_id(source_id, window_id, variant)
            if copy_id in existing_ids:
                continue
            entry = copy.deepcopy(source)
            entry["id"] = copy_id
            entry["file_id"] = copy_id
            entry["source_file_id"] = source_id
            entry["copy_variant"] = variant
            entry["ability_window_id"] = window_id
            if entry.get("name"):
                entry["name"] = _file_yield_copy_name(entry["name"], variant)
            if entry.get("filename"):
                entry["filename"] = _file_yield_copy_name(entry["filename"], variant)
            metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
            metadata = copy.deepcopy(metadata)
            metadata["source_file_id"] = source_id
            metadata["copy_variant"] = variant
            metadata["ability_window_id"] = window_id
            entry["metadata"] = metadata
            markers = entry.get("ability_application_keys")
            markers = list(markers) if isinstance(markers, list) else []
            marker = f"{window_id}:file_yield:{variant}"
            if marker not in markers:
                markers.append(marker)
            entry["ability_application_keys"] = markers
            for field in ("batch_id", "listed_at", "sold_at", "sale_id"):
                entry.pop(field, None)
            copies.append(entry)
            existing_ids.add(copy_id)
    return copies


def _data_quality_window_id(operation):
    provenance = (
        operation.get("data_quality_provenance")
        if isinstance((operation or {}).get("data_quality_provenance"), dict)
        else {}
    )
    window_id = str(provenance.get("window_id") or "").strip()
    if window_id:
        return window_id
    markers = operation.get("ability_application_keys")
    markers = markers if isinstance(markers, list) else []
    for marker in reversed(markers):
        marker = str(marker or "")
        if marker.endswith(":data_quality"):
            return marker[:-len(":data_quality")]
    return ""


def _completeness_tier(percent):
    percent = _clamp_int(percent, 0, 100)
    if percent >= 85:
        return "rich"
    if percent >= 60:
        return "enhanced"
    if percent >= 35:
        return "basic"
    return "fragment"


def enhance_data_quality_files(operation, files):
    """Apply the durable E3 quality policy to finalized operation artifacts."""
    operation = operation if isinstance(operation, dict) else {}
    provenance = (
        operation.get("data_quality_provenance")
        if isinstance(operation.get("data_quality_provenance"), dict)
        else {}
    )
    ability_code = str(provenance.get("ability_code") or "").strip()
    window_id = _data_quality_window_id(operation)
    if not window_id or ability_code not in DATA_QUALITY_POLICIES:
        return []
    policy = data_quality_policy(ability_code)
    priority_categories = set(policy["priority_categories"])
    changed = []
    for item in list(files or [])[:policy["max_files"]]:
        if not isinstance(item, dict):
            continue
        markers = item.get("ability_application_keys")
        markers = list(markers) if isinstance(markers, list) else []
        marker = f"{window_id}:data_quality"
        if marker in markers:
            continue
        category = str(item.get("file_category") or "").strip().lower()
        bonus = (
            policy["priority_bonus"]
            if category in priority_categories
            else policy["base_bonus"]
        )
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        metadata = copy.deepcopy(metadata)
        quality = _clamp_int(
            _clamp_int(
                item.get("quality_score", metadata.get("quality_score", 0)), 0, 100,
            ) + bonus,
            0, 100,
        )
        completeness = _clamp_int(
            _clamp_int(
                item.get("completeness_percent", metadata.get("completeness_percent", 0)),
                0, 100,
            ) + bonus,
            0, 100,
        )
        tier = _completeness_tier(completeness)
        item["quality_score"] = quality
        item["completeness_percent"] = completeness
        item["completeness_tier"] = tier
        item["data_quality_boosted"] = True
        item["data_quality_bonus"] = bonus
        metadata["quality_score"] = quality
        metadata["completeness_percent"] = completeness
        metadata["completeness_tier"] = tier
        nested = metadata.get("completeness")
        if isinstance(nested, dict):
            nested = copy.deepcopy(nested)
            nested["quality_score"] = quality
            nested["percent"] = completeness
            nested["tier"] = tier
            metadata["completeness"] = nested
        summary = item.get("summary")
        if isinstance(summary, dict):
            summary = copy.deepcopy(summary)
            summary["quality_score"] = quality
            summary["completeness_percent"] = completeness
            summary["tier"] = tier
            item["summary"] = summary
        item["metadata"] = metadata
        markers.append(marker)
        item["ability_application_keys"] = markers
        changed.append(str(item.get("id") or item.get("file_id") or ""))
    return changed


def _file_yield(state, window):
    files = state.setdefault("files", [])
    operation = state.setdefault("operation", {
        "operation_id": str(state.get("operation_id") or ""),
        "ability_application_keys": [f'{window["window_id"]}:file_yield'],
        "file_yield_provenance": {"window_id": window["window_id"]},
    })
    added = replicate_file_yield_files(operation, files)
    files.extend(added)
    return {
        "changed": [item.get("id") for item in added],
        "copies_per_source": MAX_BONUS_FILES_PER_SOURCE,
    }


def _data_quality(state, window):
    marker = f'{window["window_id"]}:data_quality'
    changed = []
    for item in state.setdefault("files", [])[:MAX_QUALITY_FILES]:
        if not isinstance(item, dict) or item.get("file_category") not in QUALITY_CATEGORIES:
            continue
        markers = item.setdefault("ability_application_keys", [])
        if marker in markers:
            continue
        item["quality_score"] = _clamp_int(item.get("quality_score", 0) + 20, 0, 100)
        item["completeness_percent"] = _clamp_int(
            item.get("completeness_percent", 0) + 20, 0, 100,
        )
        markers.append(marker)
        changed.append(str(item.get("file_id") or ""))
    return {"changed": changed, "bounded_limit": MAX_QUALITY_FILES}


def _hack_actions(state, window):
    target = state.setdefault("target", {})
    before_security = copy.deepcopy(target.get("security") or {})
    actions = target.setdefault("actions_allowed", {})
    changed = []
    for key in ACTION_KEYS:
        if actions.get(key) is not True:
            actions[key] = True
            changed.append(key)
    return {
        "changed": changed,
        "security_unchanged": before_security == (target.get("security") or {}),
        "bounded_limit": len(ACTION_KEYS),
    }


def _change_security(state, enable):
    target = state.setdefault("target", {})
    security = target.setdefault("security", {})
    changed = []
    for key in sorted(security):
        if len(changed) >= MAX_SECURITY_CHANGES:
            break
        if isinstance(security.get(key), bool) and security[key] is not enable:
            security[key] = enable
            changed.append(key)
    target["security_version"] = int(target.get("security_version") or 0) + bool(changed)
    return {"changed": changed, "bounded_limit": MAX_SECURITY_CHANGES}


def _target_security(state, window):
    return _change_security(state, enable=False)


def _operation_risk(state, window):
    operation = state.setdefault("operation", {})
    heat = _clamp_int(operation.get("heat", 0), 0, 100)
    modifier = -15
    effective_heat = _clamp_int(heat + modifier, 0, 100)
    operation["ability_heat_modifier"] = modifier
    operation["risk_input_heat"] = effective_heat
    return {"changed": ["ability_heat_modifier"], "input_heat": heat, "effective_heat": effective_heat}


def _scan_range(state, window):
    capability = state.setdefault("capability", {})
    base = _clamp_int(capability.get("action_range", 300), 1, 4000)
    bonus = min(1500, max(150, int(window.get("level_snapshot") or 1) * 20))
    capability["scan_range"] = min(6000, base + bonus)
    capability["scan_distance_check_bypass"] = False
    return {"changed": ["scan_range"], "base": base, "effective": capability["scan_range"]}


def _map_zoom(state, window):
    capability = state.setdefault("capability", {})
    base = _clamp_int(capability.get("map_zoom", 18), 1, 20)
    capability["map_zoom"] = min(20, base + 2)
    return {"changed": ["map_zoom"], "base": base, "effective": capability["map_zoom"]}


def _territory_defense(state, window):
    result = _change_security(state, enable=True)
    result["owner_checked"] = bool(state.get("owner_checked"))
    result["cas_checked"] = bool(state.get("cas_checked"))
    return result


_HANDLERS = {
    "operation_speed": _operation_speed,
    "file_yield": _file_yield,
    "data_quality": _data_quality,
    "hack_actions": _hack_actions,
    "target_security": _target_security,
    "operation_risk": _operation_risk,
    "scan_range": _scan_range,
    "map_zoom": _map_zoom,
    "territory_defense": _territory_defense,
}


class GhostAbilityPilotHarness:
    """Server-injected fixture harness for the 138.getway.0.4 certification.

    It is deliberately not configured from request data and has no generic
    expression/parameter interpreter. Production services do not instantiate
    it. A test selects one static family when constructing the service.
    """

    def __init__(self, family, fixture):
        family = str(family or "").strip()
        if family not in ALLOWED_REALIZER_FAMILIES:
            raise ValueError("ghost_ability_pilot_realizer_not_allowed")
        self.family = family
        self.fixture = fixture if isinstance(fixture, dict) else {}
        self.calls = 0

    def apply(self, window):
        window = window if isinstance(window, dict) else {}
        if not window.get("window_id") or window.get("ability_code") != "insider_feed":
            raise ValueError("ghost_ability_pilot_window_invalid")
        self.calls += 1
        before = copy.deepcopy(self.fixture)
        evidence = _HANDLERS[self.family](self.fixture, window)
        return {
            "ok": True,
            "mode": "fixture_certification",
            "family": self.family,
            "window_id": window["window_id"],
            "before": before,
            "after": copy.deepcopy(self.fixture),
            "evidence": evidence,
        }


class GhostAbilityCanonicalPilotHarness:
    """Exercise one fixed family against narrow canonical stores on a test DB.

    Store objects and selection keys are injected by operator/test code. No
    environment switch or public request can construct this harness.
    """

    def __init__(self, family, username, stores, selection=None):
        family = str(family or "").strip()
        if family not in ALLOWED_REALIZER_FAMILIES:
            raise ValueError("ghost_ability_pilot_realizer_not_allowed")
        self.family = family
        self.username = str(username or "").strip()
        self.stores = dict(stores or {})
        self.selection = dict(selection or {})
        self.calls = 0

    def _store(self, key):
        store = self.stores.get(key)
        if store is None:
            raise ValueError(f"ghost_ability_pilot_store_missing:{key}")
        return store

    def _one_operation(self):
        operations = self._store("operations").list_active_operations(
            self.username, limit=MAX_ACTIVE_OPERATIONS,
        )
        selected = str(self.selection.get("operation_id") or "")
        if selected:
            operations = [
                operation for operation in operations
                if str(operation.get("operation_id") or "") == selected
            ]
        if not operations:
            raise ValueError("ghost_ability_pilot_operation_missing")
        return operations[0]

    def apply(self, window):
        window = window if isinstance(window, dict) else {}
        if not window.get("window_id") or window.get("ability_code") != "insider_feed":
            raise ValueError("ghost_ability_pilot_window_invalid")
        self.calls += 1
        handler = getattr(self, f"_apply_{self.family}")
        result = handler(window)
        return {
            "ok": True,
            "mode": "canonical_store_certification",
            "family": self.family,
            "window_id": window["window_id"],
            "evidence": result,
        }

    def _apply_operation_speed(self, window):
        store = self._store("operations")
        operations = store.list_active_operations(self.username, limit=MAX_ACTIVE_OPERATIONS)
        state = {"operations": operations}
        evidence = _operation_speed(state, window)
        accepted = store.compare_and_swap_runtime(
            self.username,
            operations,
            event_type="operation.ability_speed",
            record_event=True,
        )
        evidence["persisted"] = [item.get("operation_id") for item in accepted]
        return evidence


    def _apply_file_yield(self, window):
        operation = self._one_operation()
        operation_id = str(operation.get("operation_id") or "")
        state = {
            "operation_id": operation_id,
            "files": [{
                "file_id": f"pilot_source_{_stable_id(operation_id)}",
                "source_operation_id": operation_id,
                "file_category": "credentials",
                "quality_score": 50,
                "completeness_percent": 50,
                "sellable": True,
            }],
        }
        evidence = _file_yield(state, window)
        changed = set(evidence.get("changed") or [])
        bonus_files = [
            item for item in state["files"]
            if str(item.get("id") or item.get("file_id") or "") in changed
        ]
        persisted = self._store("inventory").append_data_files(
            self.username, bonus_files, operation_id=operation_id,
        )
        evidence["persisted"] = [item.get("id") for item in persisted]
        return evidence

    def _apply_data_quality(self, window):
        operation = self._one_operation()
        changed = self._store("inventory").apply_ability_data_quality(
            self.username,
            operation_id=str(operation.get("operation_id") or ""),
            activation_id=window["window_id"],
            limit=MAX_QUALITY_FILES,
        )
        return {
            "changed": [item.get("id") for item in changed],
            "bounded_limit": MAX_QUALITY_FILES,
        }

    def _target_row(self):
        row = self._store("targets").get(self.username)
        if not row:
            raise ValueError("ghost_ability_pilot_target_missing")
        selected = str(self.selection.get("target_key") or row.get("target_key") or "")
        if selected != str(row.get("target_key") or ""):
            raise ValueError("ghost_ability_pilot_target_changed")
        return row

    def _apply_hack_actions(self, window):
        row = self._target_row()
        before_security = copy.deepcopy(row.get("security") or {})
        result = self._store("targets").apply_ability_actions(
            self.username,
            target_key=row["target_key"],
            expected_version=row["version"],
            activation_id=window["window_id"],
        )
        after = self._store("targets").get(self.username) or {}
        result["security_unchanged"] = before_security == (after.get("security") or {})
        return result

    def _apply_target_security(self, window):
        row = self._target_row()
        return self._store("targets").apply_ability_security(
            self.username,
            target_key=row["target_key"],
            expected_version=row["version"],
            activation_id=window["window_id"],
        )

    def _apply_operation_risk(self, window):
        from response_network.operation_risk_meter import calculate_operation_risk

        store = self._store("operations")
        operation = self._one_operation()
        before = calculate_operation_risk(
            operation, now_ts=window.get("activated_at"),
        )
        after = calculate_operation_risk(
            operation,
            rules={"ability_heat_modifier": -15},
            now_ts=window.get("activated_at"),
        )
        operation["operation_risk_meter"] = after
        accepted = store.compare_and_swap_runtime(
            self.username, [operation], event_type="operation.ability_risk",
            record_event=True,
        )
        return {
            "before_heat": before.get("current_heat"),
            "after_heat": after.get("current_heat"),
            "modifier": after.get("ability_heat_modifier"),
            "persisted": bool(accepted),
        }

    def _capabilities(self):
        capability = self._store("capabilities").get_capabilities(self.username)
        if not capability:
            raise ValueError("ghost_ability_pilot_capability_missing")
        return capability

    def _apply_scan_range(self, window):
        state = {"capability": self._capabilities()}
        return _scan_range(state, window)

    def _apply_map_zoom(self, window):
        state = {"capability": self._capabilities()}
        return _map_zoom(state, window)

    def _apply_territory_defense(self, window):
        store = self._store("territory")
        target = store.get_captured_target(
            self.username,
            target_id=self.selection.get("captured_target_id"),
            lat=self.selection.get("captured_lat"),
            lng=self.selection.get("captured_lng"),
            label=self.selection.get("captured_label"),
        )
        if not target:
            raise ValueError("ghost_ability_pilot_captured_target_missing")
        state = {
            "target": copy.deepcopy(target),
            "owner_checked": True,
            "cas_checked": True,
        }
        evidence = _territory_defense(state, window)
        result = store.update_captured_target_security(
            self.username,
            target,
            state["target"].get("security") or {},
            expected_version=target.get("security_version") or 0,
        )
        evidence["persisted"] = bool(result.get("ok"))
        evidence["security_version"] = result.get("security_version")
        return evidence


class GhostAbilityProductionRealizer:
    """Frozen production mapping for implemented GhostNetwork abilities."""

    ABILITY_FAMILIES = {
        "insider_feed": "operation_speed",
        "operational_prediction": "operation_speed",
        "service_entrance": "hack_actions",
        "false_image": "operation_risk",
        "narrative_takeover": "operation_risk",
        "hostile_takeover": "file_yield",
        "full_disclosure": "data_quality",
        "expose": "target_security",
        "resistance_signal": "scan_range",
    }

    def __init__(self, operation_store, target_store=None):
        self.operation_store = operation_store
        self.target_store = target_store

    def resolve_activation_target(self, player_id, ability_code):
        """Remember the target present at activation for replay recovery.

        Target abilities remain valid without a selected target: their
        active window is also applied by the canonical aimed-target hook.
        """
        family = self.ABILITY_FAMILIES.get(str(ability_code or "").strip())
        if family not in {"hack_actions", "target_security"}:
            return {"required": False, "target_id": ""}
        if self.target_store is None:
            return {"required": False, "target_id": ""}
        row = self.target_store.get(str(player_id or "").strip())
        if (
            not row
            or str(row.get("status") or "").strip().lower()
            in getattr(self.target_store, "TERMINAL_STATUSES", set())
        ):
            return {"required": False, "target_id": ""}
        return {
            "required": False,
            "target_id": str(row.get("target_key") or "").strip(),
        }

    def _apply_operation_speed(self, player_id, window):
        if self.operation_store is None:
            return {"ok": False, "status": "realizer_unavailable"}
        changed_ids = set()
        persisted_ids = set()
        attempts = 0
        factor = calculate_operation_speed_factor(
            window.get("level_snapshot"), window.get("ability_code"),
        )
        pending = []
        for _attempt in range(2):
            attempts += 1
            operations = self.operation_store.list_active_operations(
                player_id, limit=MAX_ACTIVE_OPERATIONS,
            )
            state = {"operations": operations}
            evidence = _operation_speed(state, window)
            attempt_ids = set(evidence.get("changed") or [])
            changed_ids.update(attempt_ids)
            pending = [
                operation for operation in operations
                if str(operation.get("operation_id") or "") in attempt_ids
            ]
            if not pending:
                break
            accepted = self.operation_store.compare_and_swap_runtime(
                player_id,
                pending,
                event_type="operation.ability_speed",
                record_event=True,
            )
            persisted_ids.update(
                str(item.get("operation_id") or "") for item in accepted
            )
            if len(accepted) == len(pending):
                pending = []
                break
        return {
            "ok": not pending,
            "status": (
                "applied" if persisted_ids
                else "concurrent_change" if pending
                else "no_active_operations"
            ),
            "family": "operation_speed",
            "factor": factor,
            "changed": sorted(changed_ids),
            "persisted": sorted(persisted_ids),
            "attempts": attempts,
            "cas_retries": max(0, attempts - 1),
        }

    @staticmethod
    def _apply_file_yield_to_row(operation, window):
        if not isinstance(operation, dict):
            return False
        window_id = str(window.get("window_id") or "").strip()
        if not window_id:
            return False
        marker = f"{window_id}:file_yield"
        markers = operation.get("ability_application_keys")
        markers = list(markers) if isinstance(markers, list) else []
        if marker in markers:
            return False
        markers.append(marker)
        operation["ability_application_keys"] = markers
        operation["file_yield_provenance"] = {
            "window_id": window_id,
            "ability_code": "hostile_takeover",
            "family": "file_yield",
            "copies_per_source": MAX_BONUS_FILES_PER_SOURCE,
            "touched_at": window.get("activated_at"),
        }
        return True

    def _apply_file_yield(self, player_id, window):
        if self.operation_store is None:
            return {"ok": False, "status": "realizer_unavailable"}
        changed_ids = set()
        persisted_ids = set()
        attempts = 0
        pending = []
        for _attempt in range(2):
            attempts += 1
            operations = self.operation_store.list_active_operations(
                player_id, limit=MAX_ACTIVE_OPERATIONS,
            )
            pending = []
            for operation in operations:
                if self._apply_file_yield_to_row(operation, window):
                    operation_id = str(operation.get("operation_id") or "")
                    if operation_id:
                        changed_ids.add(operation_id)
                        pending.append(operation)
            if not pending:
                break
            accepted = self.operation_store.compare_and_swap_runtime(
                player_id,
                pending,
                event_type="operation.ability_file_yield",
                record_event=True,
            )
            persisted_ids.update(
                str(item.get("operation_id") or "") for item in accepted
            )
            if len(accepted) == len(pending):
                pending = []
                break
        return {
            "ok": not pending,
            "status": (
                "applied" if persisted_ids
                else "concurrent_change" if pending
                else "no_active_operations"
            ),
            "family": "file_yield",
            "copies_per_source": MAX_BONUS_FILES_PER_SOURCE,
            "changed": sorted(changed_ids),
            "persisted": sorted(persisted_ids),
            "attempts": attempts,
            "cas_retries": max(0, attempts - 1),
        }

    @staticmethod
    def _apply_data_quality_to_row(operation, window):
        if not isinstance(operation, dict):
            return False
        window_id = str(window.get("window_id") or "").strip()
        ability_code = str(window.get("ability_code") or "").strip()
        if not window_id or ability_code not in DATA_QUALITY_POLICIES:
            return False
        marker = f"{window_id}:data_quality"
        markers = operation.get("ability_application_keys")
        markers = list(markers) if isinstance(markers, list) else []
        if marker in markers:
            return False
        policy = data_quality_policy(ability_code)
        markers.append(marker)
        operation["ability_application_keys"] = markers
        operation["data_quality_provenance"] = {
            "window_id": window_id,
            "ability_code": ability_code,
            "family": "data_quality",
            "base_bonus": policy["base_bonus"],
            "priority_bonus": policy["priority_bonus"],
            "priority_categories": list(policy["priority_categories"]),
            "max_files": policy["max_files"],
            "touched_at": window.get("activated_at"),
        }
        return True

    def _apply_data_quality(self, player_id, window):
        if self.operation_store is None:
            return {"ok": False, "status": "realizer_unavailable"}
        changed_ids = set()
        persisted_ids = set()
        attempts = 0
        pending = []
        for _attempt in range(2):
            attempts += 1
            operations = self.operation_store.list_active_operations(
                player_id, limit=MAX_ACTIVE_OPERATIONS,
            )
            pending = []
            for operation in operations:
                if self._apply_data_quality_to_row(operation, window):
                    operation_id = str(operation.get("operation_id") or "")
                    if operation_id:
                        changed_ids.add(operation_id)
                        pending.append(operation)
            if not pending:
                break
            accepted = self.operation_store.compare_and_swap_runtime(
                player_id,
                pending,
                event_type="operation.ability_data_quality",
                record_event=True,
            )
            persisted_ids.update(
                str(item.get("operation_id") or "") for item in accepted
            )
            if len(accepted) == len(pending):
                pending = []
                break
        policy = data_quality_policy(window.get("ability_code"))
        return {
            "ok": not pending,
            "status": (
                "applied" if persisted_ids
                else "concurrent_change" if pending
                else "no_active_operations"
            ),
            "family": "data_quality",
            "base_bonus": policy["base_bonus"],
            "priority_bonus": policy["priority_bonus"],
            "changed": sorted(changed_ids),
            "persisted": sorted(persisted_ids),
            "attempts": attempts,
            "cas_retries": max(0, attempts - 1),
        }

    def _apply_hack_actions(self, player_id, window, target_id=None):
        target_id = str(
            window.get("target_id") if target_id is None else target_id
        ).strip()
        if self.target_store is None:
            return {"ok": False, "status": "target_unavailable"}
        if not target_id:
            return {
                "ok": True, "status": "no_selected_target",
                "family": "hack_actions", "changed": [],
                "target_applied": False, "attempts": 0, "cas_retries": 0,
            }
        attempts = 0
        for _attempt in range(2):
            attempts += 1
            row = self.target_store.get(player_id)
            if (
                not row
                or str(row.get("status") or "").strip().lower()
                in getattr(self.target_store, "TERMINAL_STATUSES", set())
            ):
                return {
                    "ok": False, "status": "target_unavailable",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
            if str(row.get("target_key") or "") != target_id:
                return {
                    "ok": False, "status": "target_changed",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
            result = self.target_store.apply_ability_actions(
                player_id,
                target_key=target_id,
                expected_version=row.get("version") or 0,
                activation_id=window.get("window_id") or "",
            )
            reason = str(result.get("reason") or "")
            if result.get("ok"):
                return {
                    "ok": True,
                    "status": "replayed" if reason == "replayed" else "applied",
                    "family": "hack_actions",
                    "changed": list(result.get("changed") or []),
                    "target_applied": True,
                    "target": dict(result.get("target") or {}),
                    "attempts": attempts,
                    "cas_retries": max(0, attempts - 1),
                }
            if reason != "stale_version":
                return {
                    "ok": False, "status": reason or "target_change_failed",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
        return {
            "ok": False, "status": "concurrent_change",
            "attempts": attempts, "cas_retries": max(0, attempts - 1),
        }

    def _apply_target_security(self, player_id, window, target_id=None):
        """Expose one exact target by disabling its complete security bar."""
        target_id = str(
            window.get("target_id") if target_id is None else target_id
        ).strip()
        if self.target_store is None:
            return {"ok": False, "status": "target_unavailable"}
        if not target_id:
            return {
                "ok": True, "status": "no_selected_target",
                "family": "target_security", "changed": [],
                "target_applied": False, "attempts": 0, "cas_retries": 0,
            }
        attempts = 0
        for _attempt in range(2):
            attempts += 1
            row = self.target_store.get(player_id)
            if (
                not row
                or str(row.get("status") or "").strip().lower()
                in getattr(self.target_store, "TERMINAL_STATUSES", set())
            ):
                return {
                    "ok": False, "status": "target_unavailable",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
            if str(row.get("target_key") or "") != target_id:
                return {
                    "ok": False, "status": "target_changed",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
            result = self.target_store.apply_ability_security(
                player_id,
                target_key=target_id,
                expected_version=row.get("version") or 0,
                activation_id=window.get("window_id") or "",
                max_changes=None,
            )
            reason = str(result.get("reason") or "")
            if result.get("ok"):
                return {
                    "ok": True,
                    "status": "replayed" if reason == "replayed" else "applied",
                    "family": "target_security",
                    "changed": list(result.get("changed") or []),
                    "target_applied": True,
                    "target": dict(result.get("target") or {}),
                    "attempts": attempts,
                    "cas_retries": max(0, attempts - 1),
                }
            if reason != "stale_version":
                return {
                    "ok": False, "status": reason or "target_change_failed",
                    "attempts": attempts, "cas_retries": max(0, attempts - 1),
                }
        return {
            "ok": False, "status": "concurrent_change",
            "attempts": attempts, "cas_retries": max(0, attempts - 1),
        }

    @staticmethod
    def _apply_operation_risk_to_row(operation, window, now=None):
        from response_network.operation_risk_meter import calculate_operation_risk

        if not isinstance(operation, dict):
            return False
        ability_code = str(window.get("ability_code") or "").strip()
        modifier = operation_risk_modifier(ability_code)
        marker = f"{window.get('window_id')}:operation_risk"
        markers = operation.get("ability_application_keys")
        markers = list(markers) if isinstance(markers, list) else []
        first_application = marker not in markers
        if first_application:
            markers.append(marker)
            operation["ability_application_keys"] = markers
        operation["ability_provenance"] = {
            "window_id": window.get("window_id"),
            "ability_code": window.get("ability_code"),
            "family": "operation_risk",
            "modifier": modifier,
            "expires_at": window.get("expires_at"),
        }
        operation["operation_risk_meter"] = calculate_operation_risk(
            operation,
            rules={"ability_heat_modifier": modifier},
            now_ts=now or window.get("activated_at"),
        )
        return first_application

    def _apply_operation_risk(self, player_id, window):
        if self.operation_store is None:
            return {"ok": False, "status": "realizer_unavailable"}
        changed_ids = set()
        persisted_ids = set()
        attempts = 0
        modifier = operation_risk_modifier(window.get("ability_code"))
        pending = []
        for _attempt in range(2):
            attempts += 1
            operations = self.operation_store.list_active_operations(
                player_id, limit=MAX_ACTIVE_OPERATIONS,
            )
            pending = []
            for operation in operations:
                previous_meter = operation.get("operation_risk_meter")
                previous_meter = previous_meter if isinstance(previous_meter, dict) else {}
                first_application = self._apply_operation_risk_to_row(operation, window)
                operation_id = str(operation.get("operation_id") or "")
                if operation_id and (
                    first_application
                    or int(previous_meter.get("ability_heat_modifier") or 0) != modifier
                ):
                    changed_ids.add(operation_id)
                    pending.append(operation)
            if not pending:
                break
            accepted = self.operation_store.compare_and_swap_runtime(
                player_id,
                pending,
                event_type="operation.ability_risk",
                record_event=True,
            )
            persisted_ids.update(
                str(item.get("operation_id") or "") for item in accepted
            )
            if len(accepted) == len(pending):
                pending = []
                break
        return {
            "ok": not pending,
            "status": (
                "applied" if persisted_ids
                else "concurrent_change" if pending
                else "no_active_operations"
            ),
            "family": "operation_risk",
            "modifier": modifier,
            "changed": sorted(changed_ids),
            "persisted": sorted(persisted_ids),
            "attempts": attempts,
            "cas_retries": max(0, attempts - 1),
        }

    def apply_activation(self, player_id, window):
        player_id = str(player_id or "").strip()
        window = window if isinstance(window, dict) else {}
        family = self.ABILITY_FAMILIES.get(window.get("ability_code"))
        if not player_id or not family:
            return {"ok": False, "status": "realizer_unavailable"}
        if family == "operation_speed":
            return self._apply_operation_speed(player_id, window)
        if family == "hack_actions":
            return self._apply_hack_actions(player_id, window)
        if family == "target_security":
            return self._apply_target_security(player_id, window)
        if family == "operation_risk":
            return self._apply_operation_risk(player_id, window)
        if family == "file_yield":
            return self._apply_file_yield(player_id, window)
        if family == "data_quality":
            return self._apply_data_quality(player_id, window)
        if family == "scan_range":
            return {
                "ok": True,
                "status": "applied",
                "family": "scan_range",
                "effective_range_m": calculate_scan_range_m(
                    window.get("level_snapshot"), window.get("ability_code"),
                ),
                "changed": [],
            }
        return {"ok": False, "status": "realizer_unavailable"}

    def apply_to_new_operation(self, operation, window):
        family = self.ABILITY_FAMILIES.get((window or {}).get("ability_code"))
        if family == "operation_speed":
            return apply_operation_speed_to_new_operation(operation, window)
        if family == "operation_risk":
            return self._apply_operation_risk_to_row(operation, window)
        if family == "file_yield":
            return self._apply_file_yield_to_row(operation, window)
        if family == "data_quality":
            return self._apply_data_quality_to_row(operation, window)
        return False

    def apply_to_aimed_target(self, player_id, target_id, window):
        """Apply an active target ability once to the exact newly aimed target."""
        window = window if isinstance(window, dict) else {}
        family = self.ABILITY_FAMILIES.get(window.get("ability_code"))
        if family not in {"hack_actions", "target_security"}:
            return {"ok": True, "status": "not_applicable", "target_applied": False}
        player_id = str(player_id or "").strip()
        if family == "target_security":
            return self._apply_target_security(player_id, window, target_id=target_id)
        return self._apply_hack_actions(player_id, window, target_id=target_id)
