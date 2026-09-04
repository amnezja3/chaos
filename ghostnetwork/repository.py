from __future__ import annotations

import copy
import hashlib
import math
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from sqlite3 import IntegrityError

import Haversine
from config import GHOSTNETWORK_MIN_PART_DISTANCE_KM
from database import DB_PATH, db_connect, dumps_json, loads_json

from .catalog import CATALOG_VERSION, get_catalog, get_catalog_checksum
from .enums import (
    AUDIENCE_SCOPES,
    BLOCKING_CYCLE_STATUSES,
    CYCLE_STATUSES,
    PART_CONFLICT_STATES,
    PART_STATUSES,
    RESERVATION_STATUSES,
)
from .errors import (
    CycleAlreadyActive,
    CycleNotFound,
    InvalidStateTransition,
    PartNotFound,
    RepositoryIntegrityError,
    ReservationConflict,
    ReservationExpired,
    SpatialSeparationConflict,
)
from .llm.semantic_input import normalize_location
from .publication_lifecycle import build_publication_lifecycle


def narrative_task_retry_backoff_seconds(attempt_count):
    attempt = max(1, int(attempt_count or 1))
    return min(300, 5 * (2 ** (attempt - 1)))


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(value=None):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _utc_datetime(value=None):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _hash_id(prefix, *parts):
    raw = ":".join(str(part or "") for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


NARRATIVE_TASK_SCHEMA_VERSION = "ghost-narrative-task-v1"
NARRATIVE_TASK_PROCESSOR = "ollama"
NARRATIVE_TASK_READY_STATUSES = {"ready", "retry_wait"}
NARRATIVE_TASK_ACTIVE_STATUSES = {"claimed", "processing"}
NARRATIVE_TASK_TERMINAL_STATUSES = {"completed", "dead_letter"}
NARRATIVE_TASK_LEGACY_STATUS_MAP = {
    "": "ready",
    "pending": "ready",
    "created": "ready",
    "processed": "completed",
    "failed": "retry_wait",
    "expired": "retry_wait",
    "archived": "completed",
}


def _narrative_policy_rows(policies):
    rows = []
    for item in policies or []:
        if hasattr(item, "eligibility_tuple"):
            item = item.eligibility_tuple()
        elif isinstance(item, dict):
            item = (
                item.get("source_scope"),
                item.get("task_variant"),
                item.get("target_medium"),
                item.get("prompt_version"),
                item.get("output_schema_version"),
                item.get("model_policy_version"),
            )
        if not isinstance(item, (list, tuple)) or len(item) != 6:
            continue
        row = tuple(_clean(value) for value in item)
        if all(row) and "unassigned" not in row:
            rows.append(row)
    return tuple(dict.fromkeys(rows))


def _narrative_policy_sql(policies):
    rows = _narrative_policy_rows(policies)
    if not rows:
        return "0 = 1", []
    predicate = "(" + " OR ".join(
        "(source_scope = ? AND task_variant = ? AND target_medium = ? "
        "AND prompt_version = ? AND output_schema_version = ? "
        "AND model_policy_version = ?)"
        for _item in rows
    ) + ")"
    return predicate, [value for row in rows for value in row]


def canonical_narrative_task_dedupe_key(item):
    item = item if isinstance(item, dict) else {}
    source_scope = _clean(item.get("source_scope"), "ghostnetwork")
    source_identity = _clean(
        item.get("source_event_id")
        or item.get("source_receipt_id")
        or item.get("event_id")
    )
    if not source_identity:
        raise ValueError("Narrative task requires source event or receipt identity")
    target_medium = _clean(item.get("target_medium") or item.get("medium"))
    if not target_medium:
        raise ValueError("Narrative task requires target_medium")
    return _hash_id(
        "llm_task",
        source_scope,
        source_identity,
        _clean(item.get("audience_scope"), "public"),
        _clean(item.get("audience_clan")),
        _clean(item.get("audience_owner")),
        target_medium,
    )


def haversine_distance_km(lat_a, lng_a, lat_b, lng_b):
    """Return the project's canonical Haversine result converted to kilometres."""
    return Haversine.haversine_distance(
        float(lat_a), float(lng_a), float(lat_b), float(lng_b)
    ) / 1000.0


class GhostNetworkRepository:
    """SQLite repository for GhostNetwork state.

    This repository is the Sprint 111 foundation only. It stores cycles, parts,
    reservations, connections and append-only events without touching player
    profiles, map layers or gameplay endpoints.
    """

    def __init__(self, db_path=DB_PATH, clock=None):
        self.db_path = db_path
        self.clock = clock
        self._transaction_conn = None
        self._ensure_schema()

    def now(self):
        if self.clock:
            value = self.clock() if callable(self.clock) else self.clock.now()
            return _iso(value)
        return _iso()

    @contextmanager
    def transaction(self):
        if self._transaction_conn is not None:
            yield self
            return
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._transaction_conn = conn
            try:
                yield self
            finally:
                self._transaction_conn = None

    @contextmanager
    def _conn(self):
        if self._transaction_conn is not None:
            yield self._transaction_conn
        else:
            with db_connect(self.db_path) as conn:
                yield conn

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    signal_number INTEGER NOT NULL,
                    ghostsystem_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    topology_seed TEXT NOT NULL DEFAULT '',
                    topology_checksum TEXT NOT NULL DEFAULT '',
                    state_version INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL DEFAULT '',
                    locked_at TEXT NOT NULL DEFAULT '',
                    transmitted_at TEXT NOT NULL DEFAULT '',
                    stabilization_until TEXT NOT NULL DEFAULT '',
                    closed_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "ghost_cycles", "catalog_version", "catalog_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "topology_checksum", "topology_checksum TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "catalog_checksum", "catalog_checksum TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "source_version", "source_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "next_version", "next_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "lock_event_id", "lock_event_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "closing_part_id", "closing_part_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "restart_required", "restart_required INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_cycles", "restart_reason", "restart_reason TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "restart_signal_id", "restart_signal_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "restart_from_version", "restart_from_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "restart_to_version", "restart_to_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_cycles", "restart_required_at", "restart_required_at TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_parts (
                    part_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_code TEXT NOT NULL,
                    clan_code TEXT NOT NULL,
                    machine_code TEXT NOT NULL,
                    profession_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_id TEXT NOT NULL DEFAULT '',
                    latitude REAL,
                    longitude REAL,
                    discovered_by TEXT NOT NULL DEFAULT '',
                    discovered_at TEXT NOT NULL DEFAULT '',
                    territory_id TEXT NOT NULL DEFAULT '',
                    territory_owner_id TEXT NOT NULL DEFAULT '',
                    territory_clan TEXT NOT NULL DEFAULT '',
                    activated_at TEXT NOT NULL DEFAULT '',
                    deactivated_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(cycle_id, part_code),
                    FOREIGN KEY(cycle_id) REFERENCES ghost_cycles(cycle_id)
                )
                """
            )
            self._ensure_column(conn, "ghost_parts", "catalog_version", "catalog_version TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "discovered_clan", "discovered_clan TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "discovery_operation_id", "discovery_operation_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "anchor_snapshot_json", "anchor_snapshot_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "ghost_parts", "source_state", "source_state TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "conflict_state", "conflict_state TEXT NOT NULL DEFAULT 'none'")
            self._ensure_column(conn, "ghost_parts", "frozen_status", "frozen_status TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "conflict_id", "conflict_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "territory_state_version", "territory_state_version INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_parts", "contained_at", "contained_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "revealed_at", "revealed_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "contested_at", "contested_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "conflict_resolved_at", "conflict_resolved_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "consumed_at", "consumed_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "last_activated_at", "last_activated_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "last_deactivated_at", "last_deactivated_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_parts", "consumed_signal_id", "consumed_signal_id TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_parts_cycle_target
                ON ghost_parts(cycle_id, target_id)
                WHERE target_id IS NOT NULL AND target_id != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_part_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    player_clan TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    reserved_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    committed_at TEXT NOT NULL DEFAULT '',
                    released_at TEXT NOT NULL DEFAULT '',
                    operation_id TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(cycle_id) REFERENCES ghost_cycles(cycle_id),
                    FOREIGN KEY(part_id) REFERENCES ghost_parts(part_id)
                )
                """
            )
            self._ensure_column(conn, "ghost_part_reservations", "release_reason", "release_reason TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_res_active_part
                ON ghost_part_reservations(cycle_id, part_id)
                WHERE status = 'active'
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_res_active_target
                ON ghost_part_reservations(cycle_id, target_id)
                WHERE status = 'active'
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_connections (
                    connection_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_a_id TEXT NOT NULL,
                    part_b_id TEXT NOT NULL,
                    position_in_ring INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(cycle_id, part_a_id, part_b_id),
                    FOREIGN KEY(cycle_id) REFERENCES ghost_cycles(cycle_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_part_events (
                    event_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    player_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    territory_id TEXT NOT NULL DEFAULT '',
                    state_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    audience_scope TEXT NOT NULL DEFAULT 'system',
                    audience_clan TEXT NOT NULL DEFAULT '',
                    entity_id TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(cycle_id) REFERENCES ghost_cycles(cycle_id)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_event_dedupe
                ON ghost_part_events(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_pipeline_telemetry (
                    cycle_id TEXT NOT NULL DEFAULT '',
                    phase TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    outcome_count INTEGER NOT NULL DEFAULT 0,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(cycle_id, phase, outcome)
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(ghost_pipeline_telemetry)").fetchall()
            }
            if "outcome_count" not in columns or "last_seen_at" not in columns:
                if not {"cycle_id", "phase", "outcome"}.issubset(columns):
                    raise RepositoryIntegrityError("Unsupported ghost_pipeline_telemetry schema")
                conn.execute(
                    """
                    CREATE TABLE ghost_pipeline_telemetry_v2 (
                        cycle_id TEXT NOT NULL DEFAULT '',
                        phase TEXT NOT NULL,
                        outcome TEXT NOT NULL,
                        outcome_count INTEGER NOT NULL DEFAULT 0,
                        last_seen_at TEXT NOT NULL,
                        PRIMARY KEY(cycle_id, phase, outcome)
                    )
                    """
                )
                timestamp_column = "created_at" if "created_at" in columns else "''"
                conn.execute(
                    f"""
                    INSERT INTO ghost_pipeline_telemetry_v2(
                        cycle_id, phase, outcome, outcome_count, last_seen_at
                    )
                    SELECT cycle_id, phase, outcome, COUNT(*), MAX({timestamp_column})
                    FROM ghost_pipeline_telemetry
                    GROUP BY cycle_id, phase, outcome
                    """
                )
                conn.execute("DROP TABLE ghost_pipeline_telemetry")
                conn.execute(
                    "ALTER TABLE ghost_pipeline_telemetry_v2 RENAME TO ghost_pipeline_telemetry"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_capture_effects (
                    effect_id TEXT PRIMARY KEY,
                    capture_key TEXT NOT NULL UNIQUE,
                    cycle_id TEXT NOT NULL DEFAULT '',
                    reservation_id TEXT NOT NULL DEFAULT '',
                    player_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    player_json TEXT NOT NULL DEFAULT '{}',
                    target_json TEXT NOT NULL DEFAULT '{}',
                    operation_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_outcome TEXT NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    acknowledged_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_capture_effects_pending
                ON ghost_capture_effects(status, updated_at, effect_id)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_signals (
                    signal_id TEXT PRIMARY KEY,
                    signal_number INTEGER NOT NULL,
                    cycle_id TEXT NOT NULL,
                    source_version INTEGER NOT NULL DEFAULT 0,
                    target_year INTEGER NOT NULL DEFAULT 2108,
                    status TEXT NOT NULL DEFAULT 'sent',
                    outcome TEXT NOT NULL DEFAULT 'pending',
                    integrity INTEGER NOT NULL DEFAULT 100,
                    recipient TEXT NOT NULL DEFAULT '',
                    sent_at TEXT NOT NULL DEFAULT '',
                    resolved_at TEXT NOT NULL DEFAULT '',
                    next_version INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._ensure_column(conn, "ghost_signals", "lock_snapshot_id", "lock_snapshot_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_signals", "signal_checksum", "signal_checksum TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_signals", "created_at", "created_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_signals", "payload_json", "payload_json TEXT NOT NULL DEFAULT '{}'")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_signals_cycle
                ON ghost_signals(cycle_id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_cycle_lock_snapshots (
                    lock_snapshot_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL UNIQUE,
                    signal_number INTEGER NOT NULL,
                    ghostsystem_version INTEGER NOT NULL,
                    state_version INTEGER NOT NULL,
                    locked_at TEXT NOT NULL,
                    lock_event_id TEXT NOT NULL DEFAULT '',
                    closing_part_id TEXT NOT NULL DEFAULT '',
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
                    snapshot_checksum TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(cycle_id) REFERENCES ghost_cycles(cycle_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_historical_nodes (
                    historical_node_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    part_code TEXT NOT NULL DEFAULT '',
                    latitude REAL,
                    longitude REAL,
                    discovered_by TEXT NOT NULL DEFAULT '',
                    owner_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    machine_code TEXT NOT NULL DEFAULT '',
                    profession_code TEXT NOT NULL DEFAULT '',
                    active_since TEXT NOT NULL DEFAULT '',
                    active_until TEXT NOT NULL DEFAULT '',
                    defense_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'spent',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(signal_id, part_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_contributions (
                    contribution_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL DEFAULT '',
                    player_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    contribution_type TEXT NOT NULL,
                    part_id TEXT NOT NULL DEFAULT '',
                    territory_id TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "ghost_contributions", "profession_code", "profession_code TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_contributions", "operation_id", "operation_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_contributions", "weight", "weight REAL NOT NULL DEFAULT 1.0")
            self._ensure_column(conn, "ghost_contributions", "source_event_id", "source_event_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_contributions", "dedupe_key", "dedupe_key TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_contributions", "metadata_json", "metadata_json TEXT NOT NULL DEFAULT '{}'")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_contribution_dedupe
                ON ghost_contributions(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_reward_ledger (
                    reward_id TEXT PRIMARY KEY,
                    reward_key TEXT NOT NULL UNIQUE,
                    cycle_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    reward_type TEXT NOT NULL,
                    rsp_amount INTEGER NOT NULL DEFAULT 0,
                    level_progress INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_column(conn, "ghost_reward_ledger", "signal_id", "signal_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "clan_code", "clan_code TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "source_event_id", "source_event_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "base_rsp", "base_rsp INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_reward_ledger", "multiplier", "multiplier REAL NOT NULL DEFAULT 1.0")
            self._ensure_column(conn, "ghost_reward_ledger", "final_rsp", "final_rsp INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_reward_ledger", "failure_reason", "failure_reason TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "metadata_json", "metadata_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_attempt_count", "projection_attempt_count INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_claimed_by", "projection_claimed_by TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_claimed_at", "projection_claimed_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_lease_until", "projection_lease_until TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_next_attempt_at", "projection_next_attempt_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_reward_ledger", "projection_last_error_at", "projection_last_error_at TEXT NOT NULL DEFAULT ''")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ghost_reward_projection_ready "
                "ON ghost_reward_ledger(status, projection_next_attempt_at, projection_lease_until, created_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_clan_reputation (
                    clan_code TEXT PRIMARY KEY,
                    total_reputation INTEGER NOT NULL DEFAULT 0,
                    signals_participated INTEGER NOT NULL DEFAULT 0,
                    parts_discovered INTEGER NOT NULL DEFAULT 0,
                    parts_activated INTEGER NOT NULL DEFAULT 0,
                    parts_recovered INTEGER NOT NULL DEFAULT 0,
                    territories_defended INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "ghost_clan_reputation", "parts_first_contained", "parts_first_contained INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_clan_reputation", "active_node_seconds", "active_node_seconds INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_clan_reputation", "transmission_nodes_held", "transmission_nodes_held INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_clan_reputation", "networks_closed", "networks_closed INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "ghost_clan_reputation", "metadata_json", "metadata_json TEXT NOT NULL DEFAULT '{}'")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_strategic_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    territory_id TEXT NOT NULL DEFAULT '',
                    initial_owner_id TEXT NOT NULL DEFAULT '',
                    initial_clan TEXT NOT NULL DEFAULT '',
                    initial_status TEXT NOT NULL DEFAULT '',
                    initial_integrity INTEGER NOT NULL DEFAULT 100,
                    initial_security_score INTEGER NOT NULL DEFAULT 0,
                    active_offensive_operations INTEGER NOT NULL DEFAULT 0,
                    initial_participants_json TEXT NOT NULL DEFAULT '[]',
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'active',
                    outcome TEXT NOT NULL DEFAULT '',
                    max_attack_progress INTEGER NOT NULL DEFAULT 0,
                    offensive_score INTEGER NOT NULL DEFAULT 0,
                    defensive_score INTEGER NOT NULL DEFAULT 0,
                    offensive_actors_json TEXT NOT NULL DEFAULT '[]',
                    defensive_actors_json TEXT NOT NULL DEFAULT '[]',
                    assessment_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    resolved_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_strategic_conflict_dedupe
                ON ghost_strategic_conflicts(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_conflict_actions (
                    action_id TEXT PRIMARY KEY,
                    conflict_id TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    player_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    profession_code TEXT NOT NULL DEFAULT '',
                    target_id TEXT NOT NULL DEFAULT '',
                    operation_id TEXT NOT NULL DEFAULT '',
                    mechanical_value INTEGER NOT NULL DEFAULT 0,
                    weight REAL NOT NULL DEFAULT 1.0,
                    source_event_id TEXT NOT NULL DEFAULT '',
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_conflict_action_dedupe
                ON ghost_conflict_actions(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_control_periods (
                    period_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    territory_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL DEFAULT '',
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    end_reason TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_control_period_dedupe
                ON ghost_control_periods(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_part_transfer_history (
                    transfer_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    part_id TEXT NOT NULL,
                    previous_owner_id TEXT NOT NULL DEFAULT '',
                    new_owner_id TEXT NOT NULL DEFAULT '',
                    previous_clan TEXT NOT NULL DEFAULT '',
                    new_clan TEXT NOT NULL DEFAULT '',
                    conflict_id TEXT NOT NULL DEFAULT '',
                    reward_status TEXT NOT NULL DEFAULT '',
                    reward_amount INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_transfer_history_dedupe
                ON ghost_part_transfer_history(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_outbox (
                    outbox_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    cycle_id TEXT NOT NULL DEFAULT '',
                    signal_id TEXT NOT NULL DEFAULT '',
                    audience_scope TEXT NOT NULL,
                    audience_clan TEXT NOT NULL DEFAULT '',
                    audience_owner TEXT NOT NULL DEFAULT '',
                    medium TEXT NOT NULL,
                    truth_class TEXT NOT NULL,
                    facts_json TEXT NOT NULL DEFAULT '[]',
                    allowed_actions_json TEXT NOT NULL DEFAULT '[]',
                    canon_version TEXT NOT NULL DEFAULT '',
                    ghostsystem_version TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ready',
                    created_at TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT '',
                    validation_json TEXT NOT NULL DEFAULT '{}',
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    schema_version TEXT NOT NULL DEFAULT 'ghost-narrative-task-v1',
                    source_scope TEXT NOT NULL DEFAULT 'ghostnetwork',
                    source_event_id TEXT NOT NULL DEFAULT '',
                    source_receipt_id TEXT NOT NULL DEFAULT '',
                    source_app_id TEXT NOT NULL DEFAULT '',
                    processor TEXT NOT NULL DEFAULT 'ollama',
                    target_medium TEXT NOT NULL DEFAULT '',
                    world_state_version TEXT NOT NULL DEFAULT '',
                    prompt_version TEXT NOT NULL DEFAULT 'unassigned',
                    output_schema_version TEXT NOT NULL DEFAULT 'unassigned',
                    model_policy_version TEXT NOT NULL DEFAULT 'unassigned',
                    truth_class_policy TEXT NOT NULL DEFAULT '',
                    task_variant TEXT NOT NULL DEFAULT 'default',
                    narrative_intent TEXT NOT NULL DEFAULT '',
                    narrative_thread_id TEXT NOT NULL DEFAULT '',
                    content_kind TEXT NOT NULL DEFAULT '',
                    presentation_slot TEXT NOT NULL DEFAULT '',
                    selected_source_ref TEXT NOT NULL DEFAULT '',
                    selected_source_version TEXT NOT NULL DEFAULT '',
                    expected_slot_version INTEGER NOT NULL DEFAULT 0,
                    fixed_action_json TEXT NOT NULL DEFAULT '{}',
                    creative_epoch INTEGER NOT NULL DEFAULT 0,
                    editorial_contract_json TEXT NOT NULL DEFAULT '{}',
                    allowed_asset_roles_json TEXT NOT NULL DEFAULT '[]',
                    priority INTEGER NOT NULL DEFAULT 0,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    claimed_by TEXT NOT NULL DEFAULT '',
                    claimed_at TEXT NOT NULL DEFAULT '',
                    lease_until TEXT NOT NULL DEFAULT '',
                    next_attempt_at TEXT NOT NULL DEFAULT '',
                    last_error_code TEXT NOT NULL DEFAULT '',
                    last_error_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    completed_at TEXT NOT NULL DEFAULT '',
                    dead_lettered_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_column(conn, "ghost_narrative_outbox", "cycle_id", "cycle_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_narrative_outbox", "signal_id", "signal_id TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "ghost_narrative_outbox", "audience_owner", "audience_owner TEXT NOT NULL DEFAULT ''")
            self._ensure_column(
                conn,
                "ghost_narrative_outbox",
                "allowed_actions_json",
                "allowed_actions_json TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                conn,
                "ghost_narrative_outbox",
                "canon_version",
                "canon_version TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn,
                "ghost_narrative_outbox",
                "ghostsystem_version",
                "ghostsystem_version TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn,
                "ghost_narrative_outbox",
                "validation_json",
                "validation_json TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(conn, "ghost_narrative_outbox", "dedupe_key", "dedupe_key TEXT NOT NULL DEFAULT ''")
            narrative_task_columns = (
                ("schema_version", "schema_version TEXT NOT NULL DEFAULT 'ghost-narrative-task-v1'"),
                ("source_scope", "source_scope TEXT NOT NULL DEFAULT 'ghostnetwork'"),
                ("source_event_id", "source_event_id TEXT NOT NULL DEFAULT ''"),
                ("source_receipt_id", "source_receipt_id TEXT NOT NULL DEFAULT ''"),
                ("source_app_id", "source_app_id TEXT NOT NULL DEFAULT ''"),
                ("processor", "processor TEXT NOT NULL DEFAULT 'ollama'"),
                ("target_medium", "target_medium TEXT NOT NULL DEFAULT ''"),
                ("world_state_version", "world_state_version TEXT NOT NULL DEFAULT ''"),
                ("prompt_version", "prompt_version TEXT NOT NULL DEFAULT 'unassigned'"),
                ("output_schema_version", "output_schema_version TEXT NOT NULL DEFAULT 'unassigned'"),
                ("model_policy_version", "model_policy_version TEXT NOT NULL DEFAULT 'unassigned'"),
                ("truth_class_policy", "truth_class_policy TEXT NOT NULL DEFAULT ''"),
                ("task_variant", "task_variant TEXT NOT NULL DEFAULT 'default'"),
                ("narrative_intent", "narrative_intent TEXT NOT NULL DEFAULT ''"),
                ("narrative_thread_id", "narrative_thread_id TEXT NOT NULL DEFAULT ''"),
                ("content_kind", "content_kind TEXT NOT NULL DEFAULT ''"),
                ("presentation_slot", "presentation_slot TEXT NOT NULL DEFAULT ''"),
                ("selected_source_ref", "selected_source_ref TEXT NOT NULL DEFAULT ''"),
                ("selected_source_version", "selected_source_version TEXT NOT NULL DEFAULT ''"),
                ("expected_slot_version", "expected_slot_version INTEGER NOT NULL DEFAULT 0"),
                ("fixed_action_json", "fixed_action_json TEXT NOT NULL DEFAULT '{}'"),
                ("creative_epoch", "creative_epoch INTEGER NOT NULL DEFAULT 0"),
                ("editorial_contract_json", "editorial_contract_json TEXT NOT NULL DEFAULT '{}'"),
                ("allowed_asset_roles_json", "allowed_asset_roles_json TEXT NOT NULL DEFAULT '[]'"),
                ("priority", "priority INTEGER NOT NULL DEFAULT 0"),
                ("attempt_count", "attempt_count INTEGER NOT NULL DEFAULT 0"),
                ("max_attempts", "max_attempts INTEGER NOT NULL DEFAULT 5"),
                ("claimed_by", "claimed_by TEXT NOT NULL DEFAULT ''"),
                ("claimed_at", "claimed_at TEXT NOT NULL DEFAULT ''"),
                ("lease_until", "lease_until TEXT NOT NULL DEFAULT ''"),
                ("next_attempt_at", "next_attempt_at TEXT NOT NULL DEFAULT ''"),
                ("last_error_code", "last_error_code TEXT NOT NULL DEFAULT ''"),
                ("last_error_at", "last_error_at TEXT NOT NULL DEFAULT ''"),
                ("updated_at", "updated_at TEXT NOT NULL DEFAULT ''"),
                ("completed_at", "completed_at TEXT NOT NULL DEFAULT ''"),
                ("dead_lettered_at", "dead_lettered_at TEXT NOT NULL DEFAULT ''"),
            )
            for column, ddl in narrative_task_columns:
                self._ensure_column(conn, "ghost_narrative_outbox", column, ddl)
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET source_event_id = event_id
                WHERE source_event_id = '' AND event_id != ''
                """
            )
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET target_medium = CASE
                        WHEN medium = 'ollama_outbox' THEN 'blacknet'
                        ELSE medium
                    END
                WHERE target_medium = ''
                """
            )
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = CASE status
                        WHEN 'pending' THEN 'ready'
                        WHEN 'created' THEN 'ready'
                        WHEN 'processed' THEN 'completed'
                        WHEN 'failed' THEN 'retry_wait'
                        WHEN 'expired' THEN 'retry_wait'
                        WHEN 'archived' THEN 'completed'
                        ELSE status
                    END
                WHERE status IN ('pending', 'created', 'processed', 'failed', 'expired', 'archived')
                """
            )
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'completed',
                    completed_at = CASE WHEN completed_at = '' THEN created_at ELSE completed_at END,
                    processed_at = CASE WHEN processed_at = '' THEN created_at ELSE processed_at END,
                    last_error_code = CASE
                        WHEN last_error_code = '' THEN 'legacy_diagnostic_medium_retired'
                        ELSE last_error_code
                    END
                WHERE medium = 'ollama_outbox' AND status != 'completed'
                """
            )
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET updated_at = CASE WHEN updated_at = '' THEN created_at ELSE updated_at END,
                    next_attempt_at = CASE
                        WHEN next_attempt_at = '' AND status IN ('ready', 'retry_wait') THEN created_at
                        ELSE next_attempt_at
                    END
                WHERE updated_at = ''
                   OR (next_attempt_at = '' AND status IN ('ready', 'retry_wait'))
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_task_sources (
                    outbox_id TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    PRIMARY KEY(outbox_id, source_event_id),
                    FOREIGN KEY(outbox_id) REFERENCES ghost_narrative_outbox(outbox_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_source_event
                ON ghost_narrative_task_sources(source_event_id, outbox_id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_bridge_telemetry (
                    cycle_id TEXT NOT NULL DEFAULT '',
                    metric_key TEXT NOT NULL,
                    metric_count INTEGER NOT NULL DEFAULT 0,
                    value_total REAL NOT NULL DEFAULT 0,
                    value_max REAL NOT NULL DEFAULT 0,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(cycle_id, metric_key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_repository_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            source_link_migration_id = "narrative_task_sources_v1"
            source_links_migrated = conn.execute(
                """
                SELECT migration_id FROM ghost_repository_migrations
                WHERE migration_id = ? LIMIT 1
                """,
                (source_link_migration_id,),
            ).fetchone()
            if not source_links_migrated:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ghost_narrative_task_sources(
                        outbox_id, source_event_id, linked_at
                    )
                    SELECT outbox_id, source_event_id, created_at
                    FROM ghost_narrative_outbox
                    WHERE source_scope = 'ghostnetwork' AND source_event_id != ''
                    """
                )
                conn.execute(
                    """
                    INSERT INTO ghost_repository_migrations(migration_id, applied_at)
                    VALUES (?, ?)
                    """,
                    (source_link_migration_id, self.now()),
                )
            dedupe_migration_id = "narrative_task_canonical_dedupe_v1"
            dedupe_migrated = conn.execute(
                """
                SELECT migration_id FROM ghost_repository_migrations
                WHERE migration_id = ? LIMIT 1
                """,
                (dedupe_migration_id,),
            ).fetchone()
            if not dedupe_migrated:
                legacy_tasks = conn.execute(
                    """
                    SELECT outbox_id, event_id, source_scope, source_event_id,
                           source_receipt_id, audience_scope, audience_clan,
                           audience_owner, medium, target_medium, dedupe_key,
                           created_at
                    FROM ghost_narrative_outbox
                    WHERE medium != 'ollama_outbox'
                    ORDER BY created_at ASC, outbox_id ASC
                    """
                ).fetchall()
                for legacy_task in legacy_tasks:
                    source_identity = (
                        legacy_task["source_event_id"]
                        or legacy_task["event_id"]
                        or legacy_task["source_receipt_id"]
                    )
                    target_medium = legacy_task["target_medium"] or legacy_task["medium"]
                    if not source_identity or not target_medium:
                        continue
                    canonical_key = canonical_narrative_task_dedupe_key({
                        "source_scope": legacy_task["source_scope"],
                        "source_event_id": legacy_task["source_event_id"] or legacy_task["event_id"],
                        "source_receipt_id": legacy_task["source_receipt_id"],
                        "audience_scope": legacy_task["audience_scope"],
                        "audience_clan": legacy_task["audience_clan"],
                        "audience_owner": legacy_task["audience_owner"],
                        "target_medium": target_medium,
                    })
                    if legacy_task["dedupe_key"] == canonical_key:
                        continue
                    duplicate = conn.execute(
                        """
                        SELECT outbox_id
                        FROM ghost_narrative_outbox
                        WHERE dedupe_key = ? AND outbox_id != ?
                        LIMIT 1
                        """,
                        (canonical_key, legacy_task["outbox_id"]),
                    ).fetchone()
                    if duplicate:
                        conn.execute(
                            """
                            UPDATE ghost_narrative_outbox
                            SET status = 'completed',
                                completed_at = CASE
                                    WHEN completed_at = '' THEN created_at ELSE completed_at
                                END,
                                processed_at = CASE
                                    WHEN processed_at = '' THEN created_at ELSE processed_at
                                END,
                                last_error_code = 'legacy_duplicate_retired',
                                updated_at = CASE
                                    WHEN updated_at = '' THEN created_at ELSE updated_at
                                END
                            WHERE outbox_id = ?
                            """,
                            (legacy_task["outbox_id"],),
                        )
                        continue
                    conn.execute(
                        "UPDATE ghost_narrative_outbox SET dedupe_key = ? WHERE outbox_id = ?",
                        (canonical_key, legacy_task["outbox_id"]),
                    )
                conn.execute(
                    """
                    INSERT INTO ghost_repository_migrations (migration_id, applied_at)
                    VALUES (?, ?)
                    """,
                    (dedupe_migration_id, self.now()),
                )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_narrative_outbox_dedupe
                ON ghost_narrative_outbox(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_ready
                ON ghost_narrative_outbox(
                    processor, status, next_attempt_at, priority DESC, created_at, outbox_id
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_lease
                ON ghost_narrative_outbox(status, lease_until)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_source_event
                ON ghost_narrative_outbox(source_scope, source_event_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_source_receipt
                ON ghost_narrative_outbox(source_scope, source_receipt_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_status_updated
                ON ghost_narrative_outbox(status, updated_at, outbox_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_assignment
                ON ghost_narrative_outbox(
                    target_medium, presentation_slot, selected_source_ref,
                    selected_source_version, status
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_task_app_owner_created
                ON ghost_narrative_outbox(
                    source_scope, source_app_id, audience_owner, created_at
                )
                """
            )
            # Eligibility is an explicit, small OR-registry layered over the
            # canonical ready queue. A second wide prefix index makes SQLite
            # abandon the bounded scheduling index for ordinary claims.
            conn.execute("DROP INDEX IF EXISTS idx_ghost_narrative_task_policy_ready")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_registered_ready
                ON ghost_narrative_outbox(
                    priority DESC, next_attempt_at, created_at, outbox_id
                )
                WHERE processor = 'ollama'
                  AND status IN ('ready', 'retry_wait')
                  AND prompt_version != 'unassigned'
                  AND output_schema_version != 'unassigned'
                  AND model_policy_version != 'unassigned'
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_inbox_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    worker_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_digest TEXT NOT NULL,
                    ollama_runtime_version TEXT NOT NULL DEFAULT '',
                    prompt_version TEXT NOT NULL,
                    output_schema_version TEXT NOT NULL,
                    model_policy_version TEXT NOT NULL,
                    request_hash TEXT NOT NULL DEFAULT '',
                    input_bytes INTEGER NOT NULL DEFAULT 0,
                    fact_count INTEGER NOT NULL DEFAULT 0,
                    response_hash TEXT NOT NULL DEFAULT '',
                    total_duration_ns INTEGER NOT NULL DEFAULT 0,
                    load_duration_ns INTEGER NOT NULL DEFAULT 0,
                    prompt_eval_count INTEGER NOT NULL DEFAULT 0,
                    eval_count INTEGER NOT NULL DEFAULT 0,
                    result TEXT NOT NULL DEFAULT '',
                    error_code TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    retryable INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(task_id, attempt_number)
                )
                """
            )
            self._ensure_column(
                conn,
                "ghost_narrative_inbox_attempts",
                "input_bytes",
                "input_bytes INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                conn,
                "ghost_narrative_inbox_attempts",
                "fact_count",
                "fact_count INTEGER NOT NULL DEFAULT 0",
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_attempt_task
                ON ghost_narrative_inbox_attempts(task_id, attempt_number DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_attempt_status
                ON ghost_narrative_inbox_attempts(status, updated_at, attempt_id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_inbox_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL UNIQUE,
                    source_scope TEXT NOT NULL,
                    source_event_id TEXT NOT NULL DEFAULT '',
                    source_receipt_id TEXT NOT NULL DEFAULT '',
                    output_schema_version TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    model_policy_version TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_digest TEXT NOT NULL,
                    ollama_runtime_version TEXT NOT NULL DEFAULT '',
                    target_medium TEXT NOT NULL,
                    audience_scope TEXT NOT NULL,
                    audience_clan TEXT NOT NULL DEFAULT '',
                    audience_owner TEXT NOT NULL DEFAULT '',
                    truth_class TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    body TEXT NOT NULL DEFAULT '',
                    tone TEXT NOT NULL DEFAULT '',
                    fact_refs_json TEXT NOT NULL DEFAULT '[]',
                    cta_ref TEXT NOT NULL DEFAULT '',
                    cta_action TEXT NOT NULL DEFAULT '',
                    cta_payload_json TEXT NOT NULL DEFAULT '{}',
                    asset_ref TEXT NOT NULL DEFAULT '',
                    bounded_raw_output TEXT NOT NULL DEFAULT '',
                    output_hash TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    validation_errors_json TEXT NOT NULL DEFAULT '[]',
                    quarantine_reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    validated_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(
                conn, "ghost_narrative_inbox_candidates", "asset_ref",
                "asset_ref TEXT NOT NULL DEFAULT ''",
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_narrative_one_accepted
                ON ghost_narrative_inbox_candidates(task_id)
                WHERE validation_status = 'accepted'
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_candidate_task
                ON ghost_narrative_inbox_candidates(task_id, created_at, candidate_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_candidate_status
                ON ghost_narrative_inbox_candidates(
                    validation_status, created_at, candidate_id
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_publication_receipts (
                    publication_receipt_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    target_medium TEXT NOT NULL,
                    audience_scope TEXT NOT NULL,
                    audience_clan TEXT NOT NULL DEFAULT '',
                    audience_owner TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ready',
                    medium_record_id TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    claimed_by TEXT NOT NULL DEFAULT '',
                    claimed_at TEXT NOT NULL DEFAULT '',
                    lease_until TEXT NOT NULL DEFAULT '',
                    next_attempt_at TEXT NOT NULL DEFAULT '',
                    last_error_code TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_at TEXT NOT NULL DEFAULT '',
                    dead_lettered_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_narrative_publication_identity
                ON ghost_narrative_publication_receipts(
                    candidate_id, target_medium, audience_scope,
                    audience_clan, audience_owner
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_publication_ready
                ON ghost_narrative_publication_receipts(
                    status, next_attempt_at, created_at, publication_receipt_id
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_medium_records (
                    medium_record_id TEXT PRIMARY KEY,
                    publication_receipt_id TEXT NOT NULL UNIQUE,
                    candidate_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    target_medium TEXT NOT NULL,
                    audience_scope TEXT NOT NULL,
                    audience_clan TEXT NOT NULL DEFAULT '',
                    audience_owner TEXT NOT NULL DEFAULT '',
                    source_scope TEXT NOT NULL,
                    source_event_id TEXT NOT NULL DEFAULT '',
                    source_receipt_id TEXT NOT NULL DEFAULT '',
                    truth_class TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tone TEXT NOT NULL DEFAULT '',
                    fact_refs_json TEXT NOT NULL DEFAULT '[]',
                    cta_ref TEXT NOT NULL DEFAULT '',
                    cta_action TEXT NOT NULL DEFAULT '',
                    cta_payload_json TEXT NOT NULL DEFAULT '{}',
                    asset_ref TEXT NOT NULL DEFAULT '',
                    presentation_slot TEXT NOT NULL DEFAULT '',
                    content_kind TEXT NOT NULL DEFAULT '',
                    narrative_intent TEXT NOT NULL DEFAULT '',
                    selected_source_ref TEXT NOT NULL DEFAULT '',
                    selected_source_version TEXT NOT NULL DEFAULT '',
                    narrative_thread_id TEXT NOT NULL DEFAULT '',
                    event_family TEXT NOT NULL DEFAULT '',
                    significance TEXT NOT NULL DEFAULT '',
                    priority INTEGER NOT NULL DEFAULT 0,
                    active_state TEXT NOT NULL DEFAULT 'legacy',
                    valid_from TEXT NOT NULL DEFAULT '',
                    valid_until TEXT NOT NULL DEFAULT '',
                    supersedes_medium_record_id TEXT NOT NULL DEFAULT '',
                    invalidated_by_event_id TEXT NOT NULL DEFAULT '',
                    invalidation_reason TEXT NOT NULL DEFAULT '',
                    semantic_contract_version TEXT NOT NULL DEFAULT '',
                    lifecycle_contract_version TEXT NOT NULL DEFAULT '',
                    source_state_version INTEGER NOT NULL DEFAULT 0,
                    presentation_family TEXT NOT NULL DEFAULT '',
                    publication_mode TEXT NOT NULL DEFAULT 'model',
                    created_at TEXT NOT NULL,
                    published_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "asset_ref",
                "asset_ref TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "presentation_slot",
                "presentation_slot TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "content_kind",
                "content_kind TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "narrative_intent",
                "narrative_intent TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "selected_source_ref",
                "selected_source_ref TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                conn, "ghost_narrative_medium_records", "selected_source_version",
                "selected_source_version TEXT NOT NULL DEFAULT ''",
            )
            for column, ddl in (
                ("narrative_thread_id", "narrative_thread_id TEXT NOT NULL DEFAULT ''"),
                ("event_family", "event_family TEXT NOT NULL DEFAULT ''"),
                ("significance", "significance TEXT NOT NULL DEFAULT ''"),
                ("priority", "priority INTEGER NOT NULL DEFAULT 0"),
                ("active_state", "active_state TEXT NOT NULL DEFAULT 'legacy'"),
                ("valid_from", "valid_from TEXT NOT NULL DEFAULT ''"),
                ("valid_until", "valid_until TEXT NOT NULL DEFAULT ''"),
                ("supersedes_medium_record_id", "supersedes_medium_record_id TEXT NOT NULL DEFAULT ''"),
                ("invalidated_by_event_id", "invalidated_by_event_id TEXT NOT NULL DEFAULT ''"),
                ("invalidation_reason", "invalidation_reason TEXT NOT NULL DEFAULT ''"),
                ("semantic_contract_version", "semantic_contract_version TEXT NOT NULL DEFAULT ''"),
                ("lifecycle_contract_version", "lifecycle_contract_version TEXT NOT NULL DEFAULT ''"),
                ("source_state_version", "source_state_version INTEGER NOT NULL DEFAULT 0"),
                ("presentation_family", "presentation_family TEXT NOT NULL DEFAULT ''"),
                ("publication_mode", "publication_mode TEXT NOT NULL DEFAULT 'model'"),
            ):
                self._ensure_column(conn, "ghost_narrative_medium_records", column, ddl)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_medium_audience
                ON ghost_narrative_medium_records(
                    target_medium, audience_scope, audience_clan,
                    audience_owner, published_at DESC, medium_record_id DESC
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ghost_narrative_medium_active_thread
                ON ghost_narrative_medium_records(
                    target_medium, audience_scope, audience_clan, audience_owner,
                    narrative_thread_id, active_state, source_state_version DESC,
                    published_at DESC
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_narrative_slot_state (
                    target_medium TEXT NOT NULL,
                    slot_id TEXT NOT NULL,
                    content_kind TEXT NOT NULL DEFAULT '',
                    active_medium_record_id TEXT NOT NULL DEFAULT '',
                    active_source_ref TEXT NOT NULL DEFAULT '',
                    active_source_version TEXT NOT NULL DEFAULT '',
                    active_content_hash TEXT NOT NULL DEFAULT '',
                    creative_epoch INTEGER NOT NULL DEFAULT 0,
                    last_refreshed_at TEXT NOT NULL DEFAULT '',
                    next_refresh_at TEXT NOT NULL DEFAULT '',
                    version INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(target_medium, slot_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ghost_achievements (
                    achievement_id TEXT PRIMARY KEY,
                    player_id TEXT NOT NULL DEFAULT '',
                    clan_code TEXT NOT NULL DEFAULT '',
                    achievement_code TEXT NOT NULL,
                    cycle_id TEXT NOT NULL DEFAULT '',
                    signal_id TEXT NOT NULL DEFAULT '',
                    source_id TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    awarded_at TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ghost_achievement_dedupe
                ON ghost_achievements(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key != ''
                """
            )

    @staticmethod
    def _ensure_column(conn, table, column, ddl):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if column not in {row["name"] for row in rows}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    @staticmethod
    def _cycle(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "cycle_id": row["cycle_id"],
            "signal_number": int(row["signal_number"] or 0),
            "ghostsystem_version": int(row["ghostsystem_version"] or 0),
            "status": row["status"],
            "topology_seed": row["topology_seed"],
            "topology_checksum": row["topology_checksum"],
            "catalog_version": row["catalog_version"],
            "catalog_checksum": row["catalog_checksum"],
            "source_version": row["source_version"],
            "next_version": row["next_version"],
            "state_version": int(row["state_version"] or 0),
            "started_at": row["started_at"],
            "locked_at": row["locked_at"],
            "lock_event_id": row["lock_event_id"] if "lock_event_id" in keys else "",
            "closing_part_id": row["closing_part_id"] if "closing_part_id" in keys else "",
            "transmitted_at": row["transmitted_at"],
            "stabilization_until": row["stabilization_until"],
            "restart_required": bool(row["restart_required"]) if "restart_required" in keys else False,
            "restart_reason": row["restart_reason"] if "restart_reason" in keys else "",
            "restart_signal_id": row["restart_signal_id"] if "restart_signal_id" in keys else "",
            "restart_from_version": row["restart_from_version"] if "restart_from_version" in keys else "",
            "restart_to_version": row["restart_to_version"] if "restart_to_version" in keys else "",
            "restart_required_at": row["restart_required_at"] if "restart_required_at" in keys else "",
            "closed_at": row["closed_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _signal(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "signal_id": row["signal_id"],
            "signal_number": int(row["signal_number"] or 0),
            "cycle_id": row["cycle_id"],
            "source_version": int(row["source_version"] or 0),
            "target_year": int(row["target_year"] or 2108),
            "status": row["status"],
            "outcome": row["outcome"],
            "integrity": row["integrity"] if "integrity" in keys else None,
            "recipient": row["recipient"] if "recipient" in keys else "",
            "sent_at": row["sent_at"],
            "resolved_at": row["resolved_at"],
            "next_version": int(row["next_version"] or 0),
            "lock_snapshot_id": row["lock_snapshot_id"] if "lock_snapshot_id" in keys else "",
            "signal_checksum": row["signal_checksum"] if "signal_checksum" in keys else "",
            "payload": loads_json(row["payload_json"], {}) if "payload_json" in keys else {},
            "created_at": row["created_at"] if "created_at" in keys else "",
        }

    @staticmethod
    def _cycle_lock_snapshot(row):
        if not row:
            return None
        return {
            "lock_snapshot_id": row["lock_snapshot_id"],
            "cycle_id": row["cycle_id"],
            "signal_number": int(row["signal_number"] or 0),
            "ghostsystem_version": int(row["ghostsystem_version"] or 0),
            "state_version": int(row["state_version"] or 0),
            "locked_at": row["locked_at"],
            "lock_event_id": row["lock_event_id"],
            "closing_part_id": row["closing_part_id"],
            "snapshot": loads_json(row["snapshot_json"], {}),
            "snapshot_checksum": row["snapshot_checksum"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _part(row):
        if not row:
            return None
        keys = set(row.keys())
        anchor_snapshot_json = row["anchor_snapshot_json"] if "anchor_snapshot_json" in keys else "{}"
        return {
            "part_id": row["part_id"],
            "cycle_id": row["cycle_id"],
            "part_code": row["part_code"],
            "clan_code": row["clan_code"],
            "machine_code": row["machine_code"],
            "profession_code": row["profession_code"],
            "status": row["status"],
            "catalog_version": row["catalog_version"],
            "target_id": row["target_id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "discovered_by": row["discovered_by"],
            "discovered_clan": row["discovered_clan"] if "discovered_clan" in keys else "",
            "discovered_at": row["discovered_at"],
            "discovery_operation_id": row["discovery_operation_id"] if "discovery_operation_id" in keys else "",
            "anchor_snapshot": loads_json(anchor_snapshot_json, {}),
            "anchor_snapshot_json": anchor_snapshot_json,
            "source_state": row["source_state"] if "source_state" in keys else "",
            "conflict_state": row["conflict_state"] if "conflict_state" in keys else "none",
            "frozen_status": row["frozen_status"] if "frozen_status" in keys else "",
            "conflict_id": row["conflict_id"] if "conflict_id" in keys else "",
            "territory_id": row["territory_id"],
            "territory_owner_id": row["territory_owner_id"],
            "territory_clan": row["territory_clan"],
            "territory_state_version": int(row["territory_state_version"] or 0) if "territory_state_version" in keys else 0,
            "contained_at": row["contained_at"] if "contained_at" in keys else "",
            "activated_at": row["activated_at"],
            "deactivated_at": row["deactivated_at"],
            "revealed_at": row["revealed_at"] if "revealed_at" in keys else "",
            "contested_at": row["contested_at"] if "contested_at" in keys else "",
            "conflict_resolved_at": row["conflict_resolved_at"] if "conflict_resolved_at" in keys else "",
            "consumed_at": row["consumed_at"] if "consumed_at" in keys else "",
            "last_activated_at": row["last_activated_at"] if "last_activated_at" in keys else "",
            "last_deactivated_at": row["last_deactivated_at"] if "last_deactivated_at" in keys else "",
            "consumed_signal_id": row["consumed_signal_id"] if "consumed_signal_id" in keys else "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _reservation(row):
        if not row:
            return None
        return {
            "reservation_id": row["reservation_id"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "target_id": row["target_id"],
            "player_id": row["player_id"],
            "player_clan": row["player_clan"],
            "status": row["status"],
            "reserved_at": row["reserved_at"],
            "expires_at": row["expires_at"],
            "committed_at": row["committed_at"],
            "released_at": row["released_at"],
            "operation_id": row["operation_id"],
            "release_reason": row["release_reason"] if "release_reason" in row.keys() else "",
        }

    @staticmethod
    def _connection(row):
        if not row:
            return None
        return {
            "connection_id": row["connection_id"],
            "cycle_id": row["cycle_id"],
            "part_a_id": row["part_a_id"],
            "part_b_id": row["part_b_id"],
            "position_in_ring": int(row["position_in_ring"] or 0),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _event(row):
        if not row:
            return None
        return {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "entity_id": row["entity_id"],
            "state_version": int(row["state_version"] or 0),
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "payload": loads_json(row["payload_json"], {}),
            "created_at": row["created_at"],
            "dedupe_key": row["dedupe_key"],
            "player_id": row["player_id"],
            "clan_code": row["clan_code"],
            "territory_id": row["territory_id"],
        }

    @staticmethod
    def _narrative_outbox(row):
        if not row:
            return None
        keys = set(row.keys())
        medium = row["medium"]
        target_medium = row["target_medium"] if "target_medium" in keys else medium
        facts = loads_json(row["facts_json"], [])
        if not isinstance(facts, list):
            facts = []
        allowed_actions = (
            loads_json(row["allowed_actions_json"], [])
            if "allowed_actions_json" in keys
            else []
        )
        if not isinstance(allowed_actions, list):
            allowed_actions = []
        validation = loads_json(row["validation_json"], {}) if "validation_json" in keys else {}
        if not isinstance(validation, dict):
            validation = {}
        fixed_action = loads_json(row["fixed_action_json"], {}) if "fixed_action_json" in keys else {}
        if not isinstance(fixed_action, dict):
            fixed_action = {}
        editorial_contract = loads_json(row["editorial_contract_json"], {}) if "editorial_contract_json" in keys else {}
        if not isinstance(editorial_contract, dict):
            editorial_contract = {}
        allowed_asset_roles = loads_json(row["allowed_asset_roles_json"], []) if "allowed_asset_roles_json" in keys else []
        if not isinstance(allowed_asset_roles, list):
            allowed_asset_roles = []
        return {
            "outbox_id": row["outbox_id"],
            "task_id": row["outbox_id"],
            "schema_version": row["schema_version"] if "schema_version" in keys else NARRATIVE_TASK_SCHEMA_VERSION,
            "event_id": row["event_id"],
            "source_scope": row["source_scope"] if "source_scope" in keys else "ghostnetwork",
            "source_event_id": row["source_event_id"] if "source_event_id" in keys else row["event_id"],
            "source_receipt_id": row["source_receipt_id"] if "source_receipt_id" in keys else "",
            "source_app_id": row["source_app_id"] if "source_app_id" in keys else "",
            "cycle_id": row["cycle_id"] if "cycle_id" in keys else "",
            "signal_id": row["signal_id"] if "signal_id" in keys else "",
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "audience_owner": row["audience_owner"] if "audience_owner" in keys else "",
            "processor": row["processor"] if "processor" in keys else NARRATIVE_TASK_PROCESSOR,
            "medium": target_medium,
            "target_medium": target_medium,
            "truth_class": row["truth_class"],
            "truth_class_policy": row["truth_class_policy"] if "truth_class_policy" in keys else "",
            "facts": facts,
            "allowed_actions": allowed_actions,
            "canon_version": row["canon_version"] if "canon_version" in keys else "",
            "ghostsystem_version": row["ghostsystem_version"] if "ghostsystem_version" in keys else "",
            "world_state_version": row["world_state_version"] if "world_state_version" in keys else "",
            "prompt_version": row["prompt_version"] if "prompt_version" in keys else "unassigned",
            "output_schema_version": row["output_schema_version"] if "output_schema_version" in keys else "unassigned",
            "model_policy_version": row["model_policy_version"] if "model_policy_version" in keys else "unassigned",
            "task_variant": row["task_variant"] if "task_variant" in keys else "default",
            "narrative_intent": row["narrative_intent"] if "narrative_intent" in keys else "",
            "narrative_thread_id": row["narrative_thread_id"] if "narrative_thread_id" in keys else "",
            "presentation_slot": row["presentation_slot"] if "presentation_slot" in keys else "",
            "content_kind": row["content_kind"] if "content_kind" in keys else "",
            "selected_source_ref": row["selected_source_ref"] if "selected_source_ref" in keys else "",
            "selected_source_version": row["selected_source_version"] if "selected_source_version" in keys else "",
            "expected_slot_version": int(row["expected_slot_version"] or 0) if "expected_slot_version" in keys else 0,
            "fixed_action": fixed_action,
            "creative_epoch": int(row["creative_epoch"] or 0) if "creative_epoch" in keys else 0,
            "editorial_contract": editorial_contract,
            "allowed_asset_roles": allowed_asset_roles,
            "priority": int(row["priority"] or 0) if "priority" in keys else 0,
            "status": row["status"],
            "attempt_count": int(row["attempt_count"] or 0) if "attempt_count" in keys else 0,
            "max_attempts": int(row["max_attempts"] or 5) if "max_attempts" in keys else 5,
            "claimed_by": row["claimed_by"] if "claimed_by" in keys else "",
            "claimed_at": row["claimed_at"] if "claimed_at" in keys else "",
            "lease_until": row["lease_until"] if "lease_until" in keys else "",
            "next_attempt_at": row["next_attempt_at"] if "next_attempt_at" in keys else "",
            "last_error_code": row["last_error_code"] if "last_error_code" in keys else "",
            "last_error_at": row["last_error_at"] if "last_error_at" in keys else "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"] if "updated_at" in keys else row["created_at"],
            "processed_at": row["processed_at"],
            "completed_at": row["completed_at"] if "completed_at" in keys else "",
            "dead_lettered_at": row["dead_lettered_at"] if "dead_lettered_at" in keys else "",
            "validation": validation,
            "dedupe_key": row["dedupe_key"] if "dedupe_key" in keys else "",
        }

    @staticmethod
    def _narrative_attempt(row):
        if not row:
            return None
        return {
            "attempt_id": row["attempt_id"],
            "task_id": row["task_id"],
            "attempt_number": int(row["attempt_number"] or 0),
            "worker_id": row["worker_id"],
            "status": row["status"],
            "model_name": row["model_name"],
            "model_digest": row["model_digest"],
            "ollama_runtime_version": row["ollama_runtime_version"],
            "prompt_version": row["prompt_version"],
            "output_schema_version": row["output_schema_version"],
            "model_policy_version": row["model_policy_version"],
            "request_hash": row["request_hash"],
            "input_bytes": int(row["input_bytes"] or 0),
            "fact_count": int(row["fact_count"] or 0),
            "response_hash": row["response_hash"],
            "total_duration_ns": int(row["total_duration_ns"] or 0),
            "load_duration_ns": int(row["load_duration_ns"] or 0),
            "prompt_eval_count": int(row["prompt_eval_count"] or 0),
            "eval_count": int(row["eval_count"] or 0),
            "result": row["result"],
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "retryable": bool(row["retryable"]),
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _narrative_candidate(row):
        if not row:
            return None
        fact_refs = loads_json(row["fact_refs_json"], [])
        validation_errors = loads_json(row["validation_errors_json"], [])
        cta_payload = loads_json(row["cta_payload_json"], {})
        return {
            "candidate_id": row["candidate_id"],
            "task_id": row["task_id"],
            "attempt_id": row["attempt_id"],
            "source_scope": row["source_scope"],
            "source_event_id": row["source_event_id"],
            "source_receipt_id": row["source_receipt_id"],
            "output_schema_version": row["output_schema_version"],
            "prompt_version": row["prompt_version"],
            "model_policy_version": row["model_policy_version"],
            "model_name": row["model_name"],
            "model_digest": row["model_digest"],
            "ollama_runtime_version": row["ollama_runtime_version"],
            "target_medium": row["target_medium"],
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "audience_owner": row["audience_owner"],
            "truth_class": row["truth_class"],
            "title": row["title"],
            "body": row["body"],
            "tone": row["tone"],
            "fact_refs": fact_refs if isinstance(fact_refs, list) else [],
            "cta_ref": row["cta_ref"],
            "cta_action": row["cta_action"],
            "cta_payload": cta_payload if isinstance(cta_payload, dict) else {},
            "asset_ref": row["asset_ref"] if "asset_ref" in set(row.keys()) else "",
            "bounded_raw_output": row["bounded_raw_output"],
            "output_hash": row["output_hash"],
            "validation_status": row["validation_status"],
            "validation_errors": (
                validation_errors if isinstance(validation_errors, list) else []
            ),
            "quarantine_reason": row["quarantine_reason"],
            "created_at": row["created_at"],
            "validated_at": row["validated_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _narrative_publication_receipt(row):
        if not row:
            return None
        return {
            "publication_receipt_id": row["publication_receipt_id"],
            "candidate_id": row["candidate_id"],
            "task_id": row["task_id"],
            "target_medium": row["target_medium"],
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "audience_owner": row["audience_owner"],
            "status": row["status"],
            "medium_record_id": row["medium_record_id"],
            "attempt_count": int(row["attempt_count"] or 0),
            "claimed_by": row["claimed_by"],
            "claimed_at": row["claimed_at"],
            "lease_until": row["lease_until"],
            "next_attempt_at": row["next_attempt_at"],
            "last_error_code": row["last_error_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "published_at": row["published_at"],
            "dead_lettered_at": row["dead_lettered_at"],
        }

    @staticmethod
    def _narrative_medium_record(row):
        if not row:
            return None
        fact_refs = loads_json(row["fact_refs_json"], [])
        cta_payload = loads_json(row["cta_payload_json"], {})
        keys = set(row.keys())
        return {
            "publication_ordinal": int(row["publication_ordinal"] or 0) if "publication_ordinal" in keys else 0,
            "medium_record_id": row["medium_record_id"],
            "publication_receipt_id": row["publication_receipt_id"],
            "candidate_id": row["candidate_id"],
            "task_id": row["task_id"],
            "target_medium": row["target_medium"],
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "audience_owner": row["audience_owner"],
            "source_scope": row["source_scope"],
            "source_event_id": row["source_event_id"],
            "source_receipt_id": row["source_receipt_id"],
            "truth_class": row["truth_class"],
            "title": row["title"],
            "body": row["body"],
            "tone": row["tone"],
            "fact_refs": fact_refs if isinstance(fact_refs, list) else [],
            "cta_ref": row["cta_ref"],
            "cta_action": row["cta_action"],
            "cta_payload": cta_payload if isinstance(cta_payload, dict) else {},
            "asset_ref": row["asset_ref"] if "asset_ref" in keys else "",
            "presentation_slot": row["presentation_slot"] if "presentation_slot" in keys else "",
            "content_kind": row["content_kind"] if "content_kind" in keys else "",
            "narrative_intent": row["narrative_intent"] if "narrative_intent" in keys else "",
            "selected_source_ref": row["selected_source_ref"] if "selected_source_ref" in keys else "",
            "selected_source_version": row["selected_source_version"] if "selected_source_version" in keys else "",
            "narrative_thread_id": row["narrative_thread_id"] if "narrative_thread_id" in keys else "",
            "event_family": row["event_family"] if "event_family" in keys else "",
            "significance": row["significance"] if "significance" in keys else "",
            "priority": int(row["priority"] or 0) if "priority" in keys else 0,
            "active_state": row["active_state"] if "active_state" in keys else "legacy",
            "valid_from": row["valid_from"] if "valid_from" in keys else "",
            "valid_until": row["valid_until"] if "valid_until" in keys else "",
            "supersedes_medium_record_id": row["supersedes_medium_record_id"] if "supersedes_medium_record_id" in keys else "",
            "invalidated_by_event_id": row["invalidated_by_event_id"] if "invalidated_by_event_id" in keys else "",
            "invalidation_reason": row["invalidation_reason"] if "invalidation_reason" in keys else "",
            "semantic_contract_version": row["semantic_contract_version"] if "semantic_contract_version" in keys else "",
            "lifecycle_contract_version": row["lifecycle_contract_version"] if "lifecycle_contract_version" in keys else "",
            "source_state_version": int(row["source_state_version"] or 0) if "source_state_version" in keys else 0,
            "presentation_family": row["presentation_family"] if "presentation_family" in keys else "",
            "publication_mode": row["publication_mode"] if "publication_mode" in keys else "model",
            "created_at": row["created_at"],
            "published_at": row["published_at"],
        }

    @staticmethod
    def _contribution(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "contribution_id": row["contribution_id"],
            "cycle_id": row["cycle_id"],
            "signal_id": row["signal_id"],
            "player_id": row["player_id"],
            "clan_code": row["clan_code"],
            "profession_code": row["profession_code"] if "profession_code" in keys else "",
            "contribution_type": row["contribution_type"],
            "part_id": row["part_id"],
            "territory_id": row["territory_id"],
            "operation_id": row["operation_id"] if "operation_id" in keys else "",
            "score": int(row["score"] or 0),
            "weight": float(row["weight"] or 1.0) if "weight" in keys else 1.0,
            "source_event_id": row["source_event_id"] if "source_event_id" in keys else "",
            "dedupe_key": row["dedupe_key"] if "dedupe_key" in keys else "",
            "metadata": loads_json(row["metadata_json"], {}) if "metadata_json" in keys else {},
            "created_at": row["created_at"],
        }

    @staticmethod
    def _reward(row):
        if not row:
            return None
        keys = set(row.keys())
        final_rsp = int(row["final_rsp"] or row["rsp_amount"] or 0) if "final_rsp" in keys else int(row["rsp_amount"] or 0)
        base_rsp = int(row["base_rsp"] or final_rsp or 0) if "base_rsp" in keys else final_rsp
        return {
            "reward_id": row["reward_id"],
            "reward_key": row["reward_key"],
            "cycle_id": row["cycle_id"],
            "signal_id": row["signal_id"] if "signal_id" in keys else "",
            "player_id": row["player_id"],
            "clan_code": row["clan_code"] if "clan_code" in keys else "",
            "reward_type": row["reward_type"],
            "source_event_id": row["source_event_id"] if "source_event_id" in keys else "",
            "base_rsp": base_rsp,
            "multiplier": float(row["multiplier"] or 1.0) if "multiplier" in keys else 1.0,
            "final_rsp": final_rsp,
            "rsp_amount": int(row["rsp_amount"] or final_rsp or 0),
            "level_progress": int(row["level_progress"] or 0),
            "status": row["status"],
            "failure_reason": row["failure_reason"] if "failure_reason" in keys else "",
            "projection_attempt_count": int(row["projection_attempt_count"] or 0) if "projection_attempt_count" in keys else 0,
            "projection_claimed_by": row["projection_claimed_by"] if "projection_claimed_by" in keys else "",
            "projection_claimed_at": row["projection_claimed_at"] if "projection_claimed_at" in keys else "",
            "projection_lease_until": row["projection_lease_until"] if "projection_lease_until" in keys else "",
            "projection_next_attempt_at": row["projection_next_attempt_at"] if "projection_next_attempt_at" in keys else "",
            "projection_last_error_at": row["projection_last_error_at"] if "projection_last_error_at" in keys else "",
            "metadata": loads_json(row["metadata_json"], {}) if "metadata_json" in keys else {},
            "created_at": row["created_at"],
            "applied_at": row["applied_at"],
        }

    @staticmethod
    def _clan_reputation(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "clan_code": row["clan_code"],
            "total_reputation": int(row["total_reputation"] or 0),
            "signals_participated": int(row["signals_participated"] or 0),
            "parts_discovered": int(row["parts_discovered"] or 0),
            "parts_first_contained": int(row["parts_first_contained"] or 0) if "parts_first_contained" in keys else 0,
            "parts_activated": int(row["parts_activated"] or 0),
            "parts_recovered": int(row["parts_recovered"] or 0),
            "territories_defended": int(row["territories_defended"] or 0),
            "active_node_seconds": int(row["active_node_seconds"] or 0) if "active_node_seconds" in keys else 0,
            "transmission_nodes_held": int(row["transmission_nodes_held"] or 0) if "transmission_nodes_held" in keys else 0,
            "networks_closed": int(row["networks_closed"] or 0) if "networks_closed" in keys else 0,
            "metadata": loads_json(row["metadata_json"], {}) if "metadata_json" in keys else {},
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _achievement(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "achievement_id": row["achievement_id"],
            "player_id": row["player_id"],
            "clan_code": row["clan_code"] if "clan_code" in keys else "",
            "achievement_code": row["achievement_code"],
            "cycle_id": row["cycle_id"] if "cycle_id" in keys else "",
            "signal_id": row["signal_id"] if "signal_id" in keys else "",
            "source_id": row["source_id"] if "source_id" in keys else "",
            "metadata": loads_json(row["metadata_json"], {}) if "metadata_json" in keys else {},
            "awarded_at": row["awarded_at"],
            "dedupe_key": row["dedupe_key"] if "dedupe_key" in keys else "",
        }

    @staticmethod
    def _strategic_conflict(row):
        if not row:
            return None
        keys = set(row.keys())
        return {
            "conflict_id": row["conflict_id"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "territory_id": row["territory_id"],
            "initial_owner_id": row["initial_owner_id"],
            "initial_clan": row["initial_clan"],
            "initial_status": row["initial_status"],
            "initial_integrity": int(row["initial_integrity"] or 0),
            "initial_security_score": int(row["initial_security_score"] or 0),
            "active_offensive_operations": int(row["active_offensive_operations"] or 0),
            "initial_participants": loads_json(row["initial_participants_json"], []),
            "snapshot": loads_json(row["snapshot_json"], {}),
            "status": row["status"],
            "outcome": row["outcome"],
            "max_attack_progress": int(row["max_attack_progress"] or 0),
            "offensive_score": int(row["offensive_score"] or 0),
            "defensive_score": int(row["defensive_score"] or 0),
            "offensive_actors": loads_json(row["offensive_actors_json"], []),
            "defensive_actors": loads_json(row["defensive_actors_json"], []),
            "assessment": loads_json(row["assessment_json"], {}),
            "dedupe_key": row["dedupe_key"] if "dedupe_key" in keys else "",
            "started_at": row["started_at"],
            "resolved_at": row["resolved_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _conflict_action(row):
        if not row:
            return None
        return {
            "action_id": row["action_id"],
            "conflict_id": row["conflict_id"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "side": row["side"],
            "action_type": row["action_type"],
            "player_id": row["player_id"],
            "clan_code": row["clan_code"],
            "profession_code": row["profession_code"],
            "target_id": row["target_id"],
            "operation_id": row["operation_id"],
            "mechanical_value": int(row["mechanical_value"] or 0),
            "weight": float(row["weight"] or 1.0),
            "source_event_id": row["source_event_id"],
            "dedupe_key": row["dedupe_key"],
            "metadata": loads_json(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _control_period(row):
        if not row:
            return None
        return {
            "period_id": row["period_id"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "owner_id": row["owner_id"],
            "clan_code": row["clan_code"],
            "territory_id": row["territory_id"],
            "status": row["status"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "duration_seconds": int(row["duration_seconds"] or 0),
            "end_reason": row["end_reason"],
            "metadata": loads_json(row["metadata_json"], {}),
            "dedupe_key": row["dedupe_key"],
        }

    @staticmethod
    def _transfer_history(row):
        if not row:
            return None
        return {
            "transfer_id": row["transfer_id"],
            "cycle_id": row["cycle_id"],
            "part_id": row["part_id"],
            "previous_owner_id": row["previous_owner_id"],
            "new_owner_id": row["new_owner_id"],
            "previous_clan": row["previous_clan"],
            "new_clan": row["new_clan"],
            "conflict_id": row["conflict_id"],
            "reward_status": row["reward_status"],
            "reward_amount": int(row["reward_amount"] or 0),
            "metadata": loads_json(row["metadata_json"], {}),
            "dedupe_key": row["dedupe_key"],
            "created_at": row["created_at"],
        }

    def _require_cycle(self, conn, cycle_id):
        row = conn.execute("SELECT * FROM ghost_cycles WHERE cycle_id = ?", (_clean(cycle_id),)).fetchone()
        cycle = self._cycle(row)
        if not cycle:
            raise CycleNotFound(f"Cycle not found: {cycle_id}")
        return cycle

    def _active_cycle_id(self, conn):
        row = conn.execute(
            """
            SELECT cycle_id FROM ghost_cycles
            WHERE status IN ('preparing', 'active', 'transmitting', 'stabilizing')
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
        return row["cycle_id"] if row else ""

    def _bump_version(self, conn, cycle_id):
        cycle = self._require_cycle(conn, cycle_id)
        version = int(cycle.get("state_version") or 0) + 1
        conn.execute(
            "UPDATE ghost_cycles SET state_version = ?, updated_at = ? WHERE cycle_id = ?",
            (version, self.now(), cycle_id),
        )
        return version

    def get_active_cycle(self):
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM ghost_cycles
                WHERE status IN ('preparing', 'active', 'transmitting', 'stabilizing')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            return self._cycle(row)

    def get_cycle(self, cycle_id):
        with self._conn() as conn:
            return self._cycle(conn.execute("SELECT * FROM ghost_cycles WHERE cycle_id = ?", (_clean(cycle_id),)).fetchone())

    def list_cycles(self, limit=100):
        limit = max(1, min(int(limit or 100), 500))
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM ghost_cycles ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [self._cycle(row) for row in rows]

    def create_cycle(
        self,
        cycle_id=None,
        signal_number=1,
        ghostsystem_version=1,
        status="preparing",
        topology_seed="",
        topology_checksum="",
        started_at="",
        catalog_version="",
        catalog_checksum="",
        source_version="",
        next_version="",
    ):
        status = _clean(status, "preparing")
        if status not in CYCLE_STATUSES:
            raise InvalidStateTransition(f"Invalid cycle status: {status}")
        with self.transaction():
            conn = self._transaction_conn
            if status in BLOCKING_CYCLE_STATUSES and self._active_cycle_id(conn):
                raise CycleAlreadyActive("GhostNetwork already has an active or transitional cycle.")
            now = self.now()
            if not cycle_id:
                cycle_id = f"ghostnetwork_{int(signal_number or 1):04d}"
            conn.execute(
                """
                INSERT INTO ghost_cycles (
                    cycle_id, signal_number, ghostsystem_version, status,
                    topology_seed, topology_checksum, catalog_version, catalog_checksum,
                    source_version, next_version, state_version,
                    started_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    _clean(cycle_id),
                    int(signal_number or 1),
                    int(ghostsystem_version or 1),
                    status,
                    _clean(topology_seed or cycle_id),
                    _clean(topology_checksum),
                    _clean(catalog_version),
                    _clean(catalog_checksum),
                    _clean(source_version),
                    _clean(next_version),
                    _clean(started_at or now),
                    now,
                    now,
                ),
            )
            self.append_event(
                "ghost.cycle_created",
                cycle_id=cycle_id,
                entity_id=cycle_id,
                dedupe_key=f"ghost:cycle_created:{cycle_id}",
                payload={
                    "status": status,
                    "signal_number": int(signal_number or 1),
                    "ghostsystem_version": int(ghostsystem_version or 1),
                    "catalog_version": _clean(catalog_version),
                },
            )
            return self.get_cycle(cycle_id)

    def update_cycle(self, cycle_id, **fields):
        allowed = {
            "status",
            "ghostsystem_version",
            "topology_seed",
            "topology_checksum",
            "started_at",
            "locked_at",
            "transmitted_at",
            "stabilization_until",
            "closed_at",
            "catalog_version",
            "catalog_checksum",
            "source_version",
            "next_version",
            "lock_event_id",
            "closing_part_id",
            "restart_required",
            "restart_reason",
            "restart_signal_id",
            "restart_from_version",
            "restart_to_version",
            "restart_required_at",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if "status" in updates and updates["status"] not in CYCLE_STATUSES:
            raise InvalidStateTransition(f"Invalid cycle status: {updates['status']}")
        if not updates:
            return self.get_cycle(cycle_id)
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = [_clean(value) for value in updates.values()]
            version = self._bump_version(conn, cycle_id)
            conn.execute(
                f"UPDATE ghost_cycles SET {assignments}, updated_at = ? WHERE cycle_id = ?",
                [*values, self.now(), cycle_id],
            )
            self.append_event(
                "ghost.cycle_state_changed",
                cycle_id=cycle_id,
                entity_id=cycle_id,
                state_version=version,
                dedupe_key=f"ghost:cycle_update:{cycle_id}:{version}",
                payload=updates,
            )
            return self.get_cycle(cycle_id)

    def lock_cycle(self, cycle_id):
        return self.update_cycle(cycle_id, status="transmitting", locked_at=self.now())

    def create_cycle_lock_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        cycle_id = _clean(snapshot.get("cycle_id"))
        lock_snapshot_id = _clean(snapshot.get("lock_snapshot_id"))
        with self.transaction():
            conn = self._transaction_conn
            cycle = self._require_cycle(conn, cycle_id)
            existing = conn.execute(
                "SELECT * FROM ghost_cycle_lock_snapshots WHERE cycle_id = ? LIMIT 1",
                (cycle_id,),
            ).fetchone()
            if existing:
                existing_snapshot = self._cycle_lock_snapshot(existing)
                existing_snapshot["idempotent"] = True
                return existing_snapshot
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_cycle_lock_snapshots (
                        lock_snapshot_id, cycle_id, signal_number, ghostsystem_version,
                        state_version, locked_at, lock_event_id, closing_part_id,
                        snapshot_json, snapshot_checksum, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lock_snapshot_id or _hash_id("lock", cycle_id, snapshot.get("snapshot_checksum")),
                        cycle_id,
                        int(snapshot.get("signal_number") or cycle.get("signal_number") or 0),
                        int(snapshot.get("ghostsystem_version") or cycle.get("ghostsystem_version") or 0),
                        int(snapshot.get("state_version") or cycle.get("state_version") or 0),
                        _clean(snapshot.get("locked_at") or self.now()),
                        _clean(snapshot.get("lock_event_id")),
                        _clean(snapshot.get("closing_part_id")),
                        dumps_json(snapshot.get("snapshot") if isinstance(snapshot.get("snapshot"), dict) else {}),
                        _clean(snapshot.get("snapshot_checksum")),
                        _clean(snapshot.get("created_at") or self.now()),
                    ),
                )
            except IntegrityError:
                existing = conn.execute(
                    "SELECT * FROM ghost_cycle_lock_snapshots WHERE cycle_id = ? LIMIT 1",
                    (cycle_id,),
                ).fetchone()
                if existing:
                    existing_snapshot = self._cycle_lock_snapshot(existing)
                    existing_snapshot["idempotent"] = True
                    return existing_snapshot
                raise
            row = conn.execute(
                "SELECT * FROM ghost_cycle_lock_snapshots WHERE cycle_id = ? LIMIT 1",
                (cycle_id,),
            ).fetchone()
            return self._cycle_lock_snapshot(row)

    def get_cycle_lock_snapshot(self, cycle_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_cycle_lock_snapshots WHERE cycle_id = ? LIMIT 1",
                (_clean(cycle_id),),
            ).fetchone()
            return self._cycle_lock_snapshot(row)

    def list_cycle_lock_snapshots(self, cycle_id):
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_cycle_lock_snapshots
                WHERE cycle_id = ?
                ORDER BY locked_at ASC, lock_snapshot_id ASC
                """,
                (_clean(cycle_id),),
            ).fetchall()
            return [self._cycle_lock_snapshot(row) for row in rows]

    def list_signals_for_cycle(self, cycle_id, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_signals
                WHERE cycle_id = ?
                ORDER BY sent_at ASC, signal_id ASC
                LIMIT ?
                """,
                (_clean(cycle_id), limit),
            ).fetchall()
            return [self._signal(row) for row in rows]

    def list_signals(self, limit=100, status=None):
        limit = max(1, min(int(limit or 100), 1000))
        clauses = []
        params = []
        if status:
            clauses.append("status = ?")
            params.append(_clean(status))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_signals
                {where}
                ORDER BY sent_at DESC, signal_number DESC, signal_id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._signal(row) for row in rows]

    def get_signal(self, signal_id):
        with self._conn() as conn:
            return self._signal(
                conn.execute(
                    "SELECT * FROM ghost_signals WHERE signal_id = ? LIMIT 1",
                    (_clean(signal_id),),
                ).fetchone()
            )

    def get_signal_for_cycle(self, cycle_id):
        with self._conn() as conn:
            return self._signal(
                conn.execute(
                    "SELECT * FROM ghost_signals WHERE cycle_id = ? LIMIT 1",
                    (_clean(cycle_id),),
                ).fetchone()
            )

    def create_signal(self, signal):
        signal = signal if isinstance(signal, dict) else {}
        cycle_id = _clean(signal.get("cycle_id"))
        existing = self.get_signal_for_cycle(cycle_id)
        if existing:
            existing["idempotent"] = True
            return existing
        now = self.now()
        signal_id = _clean(signal.get("signal_id") or _hash_id("signal", cycle_id, signal.get("signal_number"), signal.get("lock_snapshot_id")))
        with self.transaction():
            conn = self._transaction_conn
            cycle = self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_signals (
                        signal_id, signal_number, cycle_id, source_version, target_year,
                        status, outcome, integrity, recipient, sent_at, resolved_at,
                        next_version, lock_snapshot_id, signal_checksum, created_at, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal_id,
                        int(signal.get("signal_number") or cycle.get("signal_number") or 0),
                        cycle_id,
                        int(signal.get("source_version") or cycle.get("ghostsystem_version") or 0),
                        int(signal.get("target_year") or 2108),
                        _clean(signal.get("status"), "sent"),
                        _clean(signal.get("outcome"), "pending"),
                        int(signal.get("integrity") if signal.get("integrity") is not None else 0),
                        _clean(signal.get("recipient")),
                        _clean(signal.get("sent_at") or now),
                        _clean(signal.get("resolved_at")),
                        int(signal.get("next_version") or 0),
                        _clean(signal.get("lock_snapshot_id")),
                        _clean(signal.get("signal_checksum")),
                        _clean(signal.get("created_at") or now),
                        dumps_json(signal.get("payload") if isinstance(signal.get("payload"), dict) else {}),
                    ),
                )
            except IntegrityError:
                existing = self.get_signal_for_cycle(cycle_id)
                if existing:
                    existing["idempotent"] = True
                    return existing
                raise
            return self.get_signal(signal_id)

    def get_state_version(self, cycle_id=None):
        with self._conn() as conn:
            if not cycle_id:
                cycle_id = self._active_cycle_id(conn)
            if not cycle_id:
                return 0
            cycle = self._require_cycle(conn, cycle_id)
            return int(cycle.get("state_version") or 0)

    def increment_state_version(self, cycle_id=None):
        with self.transaction():
            conn = self._transaction_conn
            if not cycle_id:
                cycle_id = self._active_cycle_id(conn)
            if not cycle_id:
                raise CycleNotFound("No active GhostNetwork cycle.")
            return self._bump_version(conn, cycle_id)

    def create_parts(self, parts):
        parts = list(parts or [])
        saved = []
        with self.transaction():
            conn = self._transaction_conn
            for part in parts:
                part = copy.deepcopy(part if isinstance(part, dict) else {})
                cycle_id = _clean(part.get("cycle_id"))
                self._require_cycle(conn, cycle_id)
                status = _clean(part.get("status"), "pooled")
                if status not in PART_STATUSES:
                    raise InvalidStateTransition(f"Invalid part status: {status}")
                now = self.now()
                part_id = _clean(part.get("part_id") or _hash_id("part", cycle_id, part.get("part_code")))
                try:
                    conn.execute(
                        """
                        INSERT INTO ghost_parts (
                            part_id, cycle_id, part_code, clan_code, machine_code,
                            profession_code, status, catalog_version, target_id, latitude, longitude,
                            discovered_by, discovered_at, territory_id,
                            territory_owner_id, territory_clan, activated_at,
                            deactivated_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            part_id,
                            cycle_id,
                            _clean(part.get("part_code")),
                            _clean(part.get("clan_code")),
                            _clean(part.get("machine_code")),
                            _clean(part.get("profession_code")),
                            status,
                            _clean(part.get("catalog_version")),
                            _clean(part.get("target_id")),
                            part.get("latitude"),
                            part.get("longitude"),
                            _clean(part.get("discovered_by")),
                            _clean(part.get("discovered_at")),
                            _clean(part.get("territory_id")),
                            _clean(part.get("territory_owner_id")),
                            _clean(part.get("territory_clan")),
                            _clean(part.get("activated_at")),
                            _clean(part.get("deactivated_at")),
                            now,
                            now,
                        ),
                    )
                except IntegrityError as exc:
                    raise RepositoryIntegrityError(str(exc)) from exc
                saved.append(self.get_part(part_id))
            if saved:
                cycle_id = saved[0]["cycle_id"]
                version = self._bump_version(conn, cycle_id)
                self.append_event(
                    "ghost.parts_created",
                    cycle_id=cycle_id,
                    entity_id=cycle_id,
                    state_version=version,
                    dedupe_key=f"ghost:parts_created:{cycle_id}:{version}",
                    payload={"count": len(saved)},
                )
        return saved

    def get_part(self, part_id):
        with self._conn() as conn:
            return self._part(conn.execute("SELECT * FROM ghost_parts WHERE part_id = ?", (_clean(part_id),)).fetchone())

    def list_parts(self, cycle_id):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM ghost_parts WHERE cycle_id = ? ORDER BY part_code ASC",
                (_clean(cycle_id),),
            ).fetchall()
            return [self._part(row) for row in rows]

    def list_discovered_parts_in_bounds(self, cycle_id, min_lat, min_lng, max_lat, max_lng):
        min_lat, max_lat = sorted((float(min_lat), float(max_lat)))
        min_lng, max_lng = sorted((float(min_lng), float(max_lng)))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM ghost_parts
                WHERE cycle_id = ?
                  AND status IN ('public', 'contained', 'active')
                  AND latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
                ORDER BY part_code ASC
                """,
                (_clean(cycle_id), min_lat, max_lat, min_lng, max_lng),
            ).fetchall()
            return [self._part(row) for row in rows]

    def list_parts_by_territory(self, cycle_id, territory_id):
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM ghost_parts
                WHERE cycle_id = ?
                  AND territory_id = ?
                  AND status IN ('public', 'contained', 'active')
                ORDER BY part_code ASC
                """,
                (_clean(cycle_id), _clean(territory_id)),
            ).fetchall()
            return [self._part(row) for row in rows]

    def find_part_by_target(self, cycle_id, target_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_parts WHERE cycle_id = ? AND target_id = ?",
                (_clean(cycle_id), _clean(target_id)),
            ).fetchone()
            return self._part(row)

    def update_part(self, part_id, **fields):
        allowed = {
            "status",
            "target_id",
            "latitude",
            "longitude",
            "discovered_by",
            "discovered_clan",
            "discovered_at",
            "discovery_operation_id",
            "anchor_snapshot_json",
            "source_state",
            "conflict_state",
            "frozen_status",
            "conflict_id",
            "territory_id",
            "territory_owner_id",
            "territory_clan",
            "territory_state_version",
            "contained_at",
            "activated_at",
            "deactivated_at",
            "revealed_at",
            "contested_at",
            "conflict_resolved_at",
            "consumed_at",
            "last_activated_at",
            "last_deactivated_at",
            "consumed_signal_id",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if "status" in updates and updates["status"] not in PART_STATUSES:
            raise InvalidStateTransition(f"Invalid part status: {updates['status']}")
        if "conflict_state" in updates and updates["conflict_state"] not in PART_CONFLICT_STATES:
            raise InvalidStateTransition(f"Invalid part conflict state: {updates['conflict_state']}")
        with self.transaction():
            conn = self._transaction_conn
            part = self.get_part(part_id)
            if not part:
                raise PartNotFound(f"Part not found: {part_id}")
            if not updates:
                return part
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = [
                value if key in {"latitude", "longitude", "territory_state_version"} else _clean(value)
                for key, value in updates.items()
            ]
            version = self._bump_version(conn, part["cycle_id"])
            try:
                conn.execute(
                    f"UPDATE ghost_parts SET {assignments}, updated_at = ? WHERE part_id = ?",
                    [*values, self.now(), part_id],
                )
            except IntegrityError as exc:
                raise RepositoryIntegrityError(str(exc)) from exc
            self.append_event(
                "ghost.part_updated",
                cycle_id=part["cycle_id"],
                part_id=part_id,
                entity_id=part_id,
                state_version=version,
                dedupe_key=f"ghost:part_update:{part_id}:{version}",
                payload=updates,
            )
            return self.get_part(part_id)

    def get_event_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            return self._event(
                conn.execute(
                    "SELECT * FROM ghost_part_events WHERE dedupe_key = ? LIMIT 1",
                    (dedupe_key,),
                ).fetchone()
            )

    def patch_part_lifecycle(self, part_id, updates, *, event_type, payload=None,
                             dedupe_key="", player_id="", clan_code="", territory_id="",
                             audience_scope="internal", audience_clan="", entity_id=""):
        updates = updates if isinstance(updates, dict) else {}
        if not updates:
            part = self.get_part(part_id)
            if not part:
                raise PartNotFound(f"Part not found: {part_id}")
            return {"part": part, "event": None, "state_version": int(part.get("state_version") or 0)}
        if dedupe_key:
            existing = self.get_event_by_dedupe_key(dedupe_key)
            if existing:
                part = self.get_part(part_id)
                return {
                    "part": part,
                    "event": existing,
                    "state_version": int(existing.get("state_version") or 0),
                    "idempotent": True,
                }
        with self.transaction():
            conn = self._transaction_conn
            part = self.get_part(part_id)
            if not part:
                raise PartNotFound(f"Part not found: {part_id}")
            allowed = {
                "status",
                "target_id",
                "latitude",
                "longitude",
                "discovered_by",
                "discovered_clan",
                "discovered_at",
                "discovery_operation_id",
                "anchor_snapshot_json",
                "source_state",
                "conflict_state",
                "frozen_status",
                "conflict_id",
                "territory_id",
                "territory_owner_id",
                "territory_clan",
                "territory_state_version",
                "contained_at",
                "activated_at",
                "deactivated_at",
                "revealed_at",
                "contested_at",
                "conflict_resolved_at",
                "consumed_at",
                "last_activated_at",
                "last_deactivated_at",
                "consumed_signal_id",
            }
            clean_updates = {key: value for key, value in updates.items() if key in allowed}
            if "status" in clean_updates and clean_updates["status"] not in PART_STATUSES:
                raise InvalidStateTransition(f"Invalid part status: {clean_updates['status']}")
            if "conflict_state" in clean_updates and clean_updates["conflict_state"] not in PART_CONFLICT_STATES:
                raise InvalidStateTransition(f"Invalid part conflict state: {clean_updates['conflict_state']}")
            assignments = ", ".join(f"{key} = ?" for key in clean_updates)
            values = [
                value if key in {"latitude", "longitude", "territory_state_version"} else _clean(value)
                for key, value in clean_updates.items()
            ]
            version = self._bump_version(conn, part["cycle_id"])
            event_id = _hash_id(
                "event",
                part["cycle_id"],
                event_type,
                entity_id or part_id,
                version,
                dedupe_key,
            )
            event_payload = copy.deepcopy(payload if isinstance(payload, dict) else {})
            event_payload.setdefault("event_id", event_id)
            event_payload.setdefault("state_version", version)
            event_payload.setdefault("dedupe_key", _clean(dedupe_key))
            try:
                conn.execute(
                    f"UPDATE ghost_parts SET {assignments}, updated_at = ? WHERE part_id = ?",
                    [*values, self.now(), part_id],
                )
            except IntegrityError as exc:
                raise RepositoryIntegrityError(str(exc)) from exc
            event = self.append_event(
                event_type,
                cycle_id=part["cycle_id"],
                part_id=part_id,
                entity_id=entity_id or part_id,
                player_id=player_id,
                clan_code=clan_code,
                territory_id=territory_id,
                state_version=version,
                audience_scope=audience_scope,
                audience_clan=audience_clan,
                dedupe_key=dedupe_key,
                event_id=event_id,
                payload=event_payload,
            )
            return {"part": self.get_part(part_id), "event": event, "state_version": version}

    def create_reservation(
        self,
        cycle_id,
        part_id,
        target_id,
        player_id,
        player_clan="",
        reservation_id=None,
        expires_at=None,
        latitude=None,
        longitude=None,
        min_distance_km=None,
    ):
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            part = self.get_part(part_id)
            if not part:
                raise PartNotFound(f"Part not found: {part_id}")
            if part.get("status") != "pooled":
                raise ReservationConflict(f"Part is not reservable: {part.get('status')}")
            if part.get("target_id") or part.get("latitude") is not None or part.get("longitude") is not None:
                raise ReservationConflict("Part is already anchored.")
            if latitude is not None or longitude is not None:
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                except (TypeError, ValueError) as exc:
                    raise ReservationConflict("Invalid reservation coordinates.") from exc
                if not (
                    math.isfinite(latitude)
                    and math.isfinite(longitude)
                    and -90 <= latitude <= 90
                    and -180 <= longitude <= 180
                ):
                    raise ReservationConflict("Invalid reservation coordinates.")
                distance_limit = float(
                    GHOSTNETWORK_MIN_PART_DISTANCE_KM
                    if min_distance_km is None
                    else min_distance_km
                )
                anchors = conn.execute(
                    """
                    SELECT latitude, longitude
                    FROM ghost_parts
                    WHERE cycle_id = ?
                      AND status IN ('reserved', 'public', 'contained', 'active')
                      AND latitude IS NOT NULL
                      AND longitude IS NOT NULL
                    """,
                    (_clean(cycle_id),),
                ).fetchall()
                if distance_limit > 0 and any(
                    haversine_distance_km(latitude, longitude, row["latitude"], row["longitude"])
                    + 0.000001 < distance_limit
                    for row in anchors
                ):
                    raise SpatialSeparationConflict("part_too_close")
            reservation_id = _clean(reservation_id or _hash_id("reservation", cycle_id, part_id, target_id, player_id))
            now = self.now()
            expires_at = _clean(expires_at or now)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_part_reservations (
                        reservation_id, cycle_id, part_id, target_id, player_id,
                        player_clan, status, reserved_at, expires_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        reservation_id,
                        _clean(cycle_id),
                        _clean(part_id),
                        _clean(target_id),
                        _clean(player_id),
                        _clean(player_clan),
                        now,
                        expires_at,
                    ),
                )
                updated = conn.execute(
                    """
                    UPDATE ghost_parts
                    SET status = 'reserved', target_id = ?, latitude = ?, longitude = ?, updated_at = ?
                    WHERE part_id = ? AND cycle_id = ? AND status = 'pooled'
                    """,
                    (_clean(target_id), latitude, longitude, now, _clean(part_id), _clean(cycle_id)),
                ).rowcount
                if updated != 1:
                    raise ReservationConflict("Part reservation race.")
            except IntegrityError as exc:
                raise ReservationConflict(str(exc)) from exc
            version = self._bump_version(conn, cycle_id)
            self.append_event(
                "ghost.part_reserved",
                cycle_id=cycle_id,
                part_id=part_id,
                entity_id=part_id,
                player_id=player_id,
                clan_code=player_clan,
                state_version=version,
                dedupe_key=f"ghost:reservation:{reservation_id}",
                payload={"reservation_id": reservation_id, "target_id": target_id},
            )
            return self.get_reservation(reservation_id)

    def list_reservable_parts(self, cycle_id, excluded_clan=""):
        params = [_clean(cycle_id)]
        clan_filter = ""
        excluded_clan = _clean(excluded_clan)
        if excluded_clan:
            clan_filter = "AND clan_code != ?"
            params.append(excluded_clan)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM ghost_parts
                WHERE cycle_id = ?
                  AND status = 'pooled'
                  AND target_id = ''
                  AND latitude IS NULL
                  AND longitude IS NULL
                  {clan_filter}
                ORDER BY part_code ASC
                """,
                params,
            ).fetchall()
            return [self._part(row) for row in rows]

    def get_active_reservation(self, cycle_id, part_id=None, target_id=None):
        clauses = ["cycle_id = ?", "status = 'active'"]
        params = [_clean(cycle_id)]
        if part_id:
            clauses.append("part_id = ?")
            params.append(_clean(part_id))
        if target_id:
            clauses.append("target_id = ?")
            params.append(_clean(target_id))
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_part_reservations WHERE " + " AND ".join(clauses) + " LIMIT 1",
                params,
            ).fetchone()
            return self._reservation(row)

    def list_active_reservations(self, cycle_id=None, limit=1000):
        clauses = ["status = 'active'"]
        params = []
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        params.append(max(1, min(int(limit or 1000), 5000)))
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM ghost_part_reservations WHERE "
                + " AND ".join(clauses)
                + " ORDER BY reserved_at, reservation_id LIMIT ?",
                tuple(params),
            ).fetchall()
            return [self._reservation(row) for row in rows]

    def find_active_reservation_for_discovery(self, cycle_id, player_id, target_id, operation_id=""):
        cycle_id = _clean(cycle_id)
        player_id = _clean(player_id)
        target_id = _clean(target_id)
        operation_id = _clean(operation_id)
        with self._conn() as conn:
            if operation_id:
                row = conn.execute(
                    """
                    SELECT *
                    FROM ghost_part_reservations
                    WHERE cycle_id = ?
                      AND player_id = ?
                      AND target_id = ?
                      AND operation_id = ?
                      AND status = 'active'
                    ORDER BY reserved_at ASC
                    LIMIT 1
                    """,
                    (cycle_id, player_id, target_id, operation_id),
                ).fetchone()
                if row:
                    return self._reservation(row)
            row = conn.execute(
                """
                SELECT *
                FROM ghost_part_reservations
                WHERE cycle_id = ?
                  AND player_id = ?
                  AND target_id = ?
                  AND status = 'active'
                ORDER BY
                  CASE WHEN operation_id = '' THEN 0 ELSE 1 END,
                  reserved_at ASC
                LIMIT 1
                """,
                (cycle_id, player_id, target_id),
            ).fetchone()
            return self._reservation(row)

    def get_reservation(self, reservation_id):
        with self._conn() as conn:
            return self._reservation(
                conn.execute(
                    "SELECT * FROM ghost_part_reservations WHERE reservation_id = ?",
                    (_clean(reservation_id),),
                ).fetchone()
            )

    def attach_reservation_to_operation(self, reservation_id, operation_id):
        with self.transaction():
            conn = self._transaction_conn
            reservation = self.get_reservation(reservation_id)
            if not reservation:
                raise ReservationConflict(f"Reservation not found: {reservation_id}")
            if reservation["status"] != "active":
                raise InvalidStateTransition(f"Reservation is not active: {reservation['status']}")
            operation_id = _clean(operation_id)
            if reservation.get("operation_id") == operation_id:
                return reservation
            conn.execute(
                """
                UPDATE ghost_part_reservations
                SET operation_id = ?
                WHERE reservation_id = ? AND status = 'active'
                """,
                (operation_id, reservation_id),
            )
            version = self._bump_version(conn, reservation["cycle_id"])
            self.append_event(
                "ghost.part_reservation_attached",
                cycle_id=reservation["cycle_id"],
                part_id=reservation["part_id"],
                entity_id=reservation["part_id"],
                player_id=reservation["player_id"],
                clan_code=reservation["player_clan"],
                state_version=version,
                dedupe_key=f"ghost:reservation_attached:{reservation_id}:{operation_id}",
                payload={"reservation_id": reservation_id, "operation_id": operation_id},
            )
            return self.get_reservation(reservation_id)

    def commit_reservation(self, reservation_id, operation_id=""):
        with self.transaction():
            conn = self._transaction_conn
            reservation = self.get_reservation(reservation_id)
            if not reservation:
                raise ReservationConflict(f"Reservation not found: {reservation_id}")
            if reservation["status"] == "committed":
                raise InvalidStateTransition("Reservation already committed.")
            if reservation["status"] != "active":
                raise InvalidStateTransition(f"Reservation is not active: {reservation['status']}")
            if reservation["expires_at"] and _iso(reservation["expires_at"]) < self.now():
                conn.execute(
                    "UPDATE ghost_part_reservations SET status = 'expired' WHERE reservation_id = ?",
                    (reservation_id,),
                )
                raise ReservationExpired("Reservation expired.")
            now = self.now()
            conn.execute(
                """
                UPDATE ghost_part_reservations
                SET status = 'committed', committed_at = ?, operation_id = ?
                WHERE reservation_id = ?
                """,
                (now, _clean(operation_id), reservation_id),
            )
            version = self._bump_version(conn, reservation["cycle_id"])
            self.append_event(
                "ghost.reservation_committed",
                cycle_id=reservation["cycle_id"],
                part_id=reservation["part_id"],
                entity_id=reservation["part_id"],
                player_id=reservation["player_id"],
                clan_code=reservation["player_clan"],
                state_version=version,
                dedupe_key=f"ghost:reservation_committed:{reservation_id}",
                payload={"reservation_id": reservation_id, "operation_id": _clean(operation_id)},
            )
            return self.get_reservation(reservation_id)

    @staticmethod
    def _coerce_coordinate(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(numeric):
            return None
        return numeric

    @staticmethod
    def _target_anchor_snapshot(target):
        target = target if isinstance(target, dict) else {}
        lat_value = target.get("lat") if target.get("lat") is not None else target.get("latitude")
        lng_value = target.get("lng")
        if lng_value is None:
            lng_value = target.get("lon")
        if lng_value is None:
            lng_value = target.get("longitude")
        lat = GhostNetworkRepository._coerce_coordinate(lat_value)
        lng = GhostNetworkRepository._coerce_coordinate(
            lng_value
        )
        label = (
            target.get("display_label")
            or target.get("label")
            or target.get("name")
            or target.get("title")
            or target.get("target_id")
            or target.get("id")
            or "unknown"
        )
        anchor = {
            "target_id": _clean(target.get("target_id") or target.get("id")),
            "label": _clean(label, "unknown"),
            "target_type": _clean(target.get("target_type") or target.get("type") or target.get("target_mode") or "standard"),
            "source_type": _clean(target.get("source_type") or target.get("category") or "unknown"),
            "icon_key": _clean(target.get("icon_key") or target.get("icon") or target.get("source_type") or "target"),
            "latitude": lat,
            "longitude": lng,
            "osm_id": _clean(target.get("osm_id")),
            "node_id": _clean(target.get("node_id")),
            "procedural_seed": _clean(target.get("procedural_seed") or target.get("seed")),
            "original_source": _clean(target.get("original_source") or target.get("source") or "map_target"),
        }
        location = normalize_location(target.get("location"))
        if location:
            anchor["location"] = location
        return anchor

    def discover_reserved_part(
        self,
        reservation_id,
        player=None,
        target=None,
        operation_id="",
        result=None,
        context=None,
    ):
        player = player if isinstance(player, dict) else {}
        target = target if isinstance(target, dict) else {}
        result = result if isinstance(result, dict) else {}
        context = context if isinstance(context, dict) else {}
        player_id = _clean(player.get("player_id") or player.get("username") or player.get("login"))
        player_clan = _clean(player.get("clan_code") or player.get("clan"))
        target_id = _clean(target.get("target_id") or target.get("id"))
        operation_id = _clean(operation_id)
        if not target_id:
            return {"ok": False, "status": "invalid_target", "reason": "missing_target_id"}
        anchor = self._target_anchor_snapshot({**target, "target_id": target_id})
        lat = self._coerce_coordinate(anchor.get("latitude"))
        lng = self._coerce_coordinate(anchor.get("longitude"))
        if lat is None or lng is None:
            return {"ok": False, "status": "invalid_target", "reason": "missing_coordinates"}

        with self.transaction():
            conn = self._transaction_conn
            reservation = self.get_reservation(reservation_id)
            if not reservation:
                return {"ok": False, "status": "no_matching_reservation"}
            part = self.get_part(reservation["part_id"])
            if not part:
                raise PartNotFound(f"Part not found: {reservation['part_id']}")

            # Reservation is the spatial decision point.  Discovery must not
            # move that anchor if a later payload contains changed coordinates.
            if part.get("latitude") is not None and part.get("longitude") is not None:
                lat = float(part["latitude"])
                lng = float(part["longitude"])
                anchor["latitude"] = lat
                anchor["longitude"] = lng

            if reservation["target_id"] != target_id:
                return {"ok": False, "status": "target_mismatch"}
            if player_id and reservation["player_id"] != player_id:
                return {"ok": False, "status": "player_mismatch"}

            discover_operation_id = operation_id or reservation.get("operation_id") or ""
            dedupe_key = (
                f"discover:{reservation['cycle_id']}:{reservation['part_id']}:{discover_operation_id}"
                if discover_operation_id
                else f"discover:{reservation['cycle_id']}:{target_id}"
            )
            existing_event = conn.execute(
                "SELECT * FROM ghost_part_events WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            if existing_event:
                return {
                    "ok": True,
                    "status": "already_discovered",
                    "part": self.get_part(reservation["part_id"]),
                    "reservation": reservation,
                    "event": self._event(existing_event),
                }

            if reservation["status"] == "committed" and part.get("status") == "public":
                return {
                    "ok": True,
                    "status": "already_discovered",
                    "part": part,
                    "reservation": reservation,
                    "event": None,
                }
            if reservation["status"] != "active":
                return {"ok": False, "status": f"reservation_{reservation['status']}"}
            if reservation["expires_at"] and _iso(reservation["expires_at"]) < self.now():
                now = self.now()
                conn.execute(
                    """
                    UPDATE ghost_part_reservations
                    SET status = 'expired', released_at = ?, release_reason = 'reservation_expired'
                    WHERE reservation_id = ?
                    """,
                    (now, reservation["reservation_id"]),
                )
                conn.execute(
                    """
                    UPDATE ghost_parts
                    SET status = 'pooled', target_id = '', latitude = NULL, longitude = NULL, updated_at = ?
                    WHERE part_id = ? AND status = 'reserved'
                    """,
                    (now, reservation["part_id"]),
                )
                return {"ok": True, "status": "reservation_expired"}

            cycle = self._require_cycle(conn, reservation["cycle_id"])
            if cycle.get("status") != "active":
                return {"ok": False, "status": "cycle_not_active"}
            if part.get("status") != "reserved":
                return {"ok": False, "status": "part_not_reserved"}
            if part.get("cycle_id") != cycle["cycle_id"]:
                return {"ok": False, "status": "cycle_mismatch"}
            if part.get("clan_code") and player_clan and part.get("clan_code") == player_clan:
                return {"ok": False, "status": "own_clan_part_blocked"}
            if part.get("target_id") and part.get("target_id") != target_id:
                return {"ok": False, "status": "part_target_mismatch"}

            duplicate_target = conn.execute(
                """
                SELECT part_id
                FROM ghost_parts
                WHERE cycle_id = ? AND target_id = ? AND part_id != ?
                LIMIT 1
                """,
                (cycle["cycle_id"], target_id, part["part_id"]),
            ).fetchone()
            if duplicate_target:
                return {"ok": False, "status": "target_already_emitted", "part_id": duplicate_target["part_id"]}

            now = self.now()
            anchor_json = dumps_json(anchor)
            conn.execute(
                """
                UPDATE ghost_part_reservations
                SET status = 'committed', committed_at = ?, operation_id = ?
                WHERE reservation_id = ? AND status = 'active'
                """,
                (now, discover_operation_id, reservation["reservation_id"]),
            )
            updated = conn.execute(
                """
                UPDATE ghost_parts
                SET status = 'public',
                    target_id = ?,
                    latitude = ?,
                    longitude = ?,
                    discovered_by = ?,
                    discovered_clan = ?,
                    discovered_at = ?,
                    discovery_operation_id = ?,
                    anchor_snapshot_json = ?,
                    source_state = 'present',
                    updated_at = ?
                WHERE part_id = ? AND cycle_id = ? AND status = 'reserved'
                """,
                (
                    target_id,
                    lat,
                    lng,
                    player_id or reservation["player_id"],
                    player_clan or reservation.get("player_clan") or "",
                    now,
                    discover_operation_id,
                    anchor_json,
                    now,
                    part["part_id"],
                    cycle["cycle_id"],
                ),
            ).rowcount
            if updated != 1:
                return {"ok": False, "status": "part_update_race"}

            version = self._bump_version(conn, cycle["cycle_id"])
            event = self.append_event(
                "ghost.part_discovered",
                cycle_id=cycle["cycle_id"],
                part_id=part["part_id"],
                entity_id=part["part_id"],
                player_id=player_id or reservation["player_id"],
                clan_code=player_clan or reservation.get("player_clan") or "",
                state_version=version,
                dedupe_key=dedupe_key,
                audience_scope="player",
                payload={
                    "reservation_id": reservation["reservation_id"],
                    "target_id": target_id,
                    "operation_id": discover_operation_id,
                    "anchor": anchor,
                    "result": result,
                    "context": context,
                },
            )
            return {
                "ok": True,
                "status": "discovered",
                "part": self.get_part(part["part_id"]),
                "reservation": self.get_reservation(reservation["reservation_id"]),
                "event": event,
                "state_version": version,
            }

    def release_reservation(self, reservation_id, status="released", reason=""):
        status = _clean(status, "released")
        if status not in {"released", "cancelled"}:
            raise InvalidStateTransition(f"Invalid release status: {status}")
        with self.transaction():
            conn = self._transaction_conn
            reservation = self.get_reservation(reservation_id)
            if not reservation:
                raise ReservationConflict(f"Reservation not found: {reservation_id}")
            if reservation["status"] != "active":
                return reservation
            now = self.now()
            conn.execute(
                """
                UPDATE ghost_part_reservations
                SET status = ?, released_at = ?, release_reason = ?
                WHERE reservation_id = ?
                """,
                (status, now, _clean(reason), reservation_id),
            )
            conn.execute(
                """
                UPDATE ghost_parts
                SET status = 'pooled', target_id = '', latitude = NULL, longitude = NULL, updated_at = ?
                WHERE part_id = ? AND status = 'reserved'
                """,
                (now, reservation["part_id"]),
            )
            version = self._bump_version(conn, reservation["cycle_id"])
            self.append_event(
                "ghost.part_reservation_released",
                cycle_id=reservation["cycle_id"],
                part_id=reservation["part_id"],
                entity_id=reservation["part_id"],
                state_version=version,
                dedupe_key=f"ghost:reservation_released:{reservation_id}:{status}:{_clean(reason)}",
                payload={"reservation_id": reservation_id, "status": status, "reason": _clean(reason)},
            )
            return self.get_reservation(reservation_id)

    def expire_reservations(self, now=None):
        now_iso = _iso(now or self.now())
        expired = []
        with self.transaction():
            conn = self._transaction_conn
            rows = conn.execute(
                """
                SELECT * FROM ghost_part_reservations
                WHERE status = 'active' AND expires_at != '' AND expires_at < ?
                """,
                (now_iso,),
            ).fetchall()
            for row in rows:
                reservation = self._reservation(row)
                conn.execute(
                    """
                    UPDATE ghost_part_reservations
                    SET status = 'expired', released_at = ?, release_reason = 'reservation_expired'
                    WHERE reservation_id = ?
                    """,
                    (now_iso, reservation["reservation_id"]),
                )
                conn.execute(
                    """
                    UPDATE ghost_parts
                    SET status = 'pooled', target_id = '', latitude = NULL, longitude = NULL, updated_at = ?
                    WHERE part_id = ? AND status = 'reserved'
                    """,
                    (now_iso, reservation["part_id"]),
                )
                version = self._bump_version(conn, reservation["cycle_id"])
                self.append_event(
                    "ghost.part_reservation_expired",
                    cycle_id=reservation["cycle_id"],
                    part_id=reservation["part_id"],
                    entity_id=reservation["part_id"],
                    state_version=version,
                    dedupe_key=f"ghost:reservation_expired:{reservation['reservation_id']}",
                    payload={"reservation_id": reservation["reservation_id"], "reason": "reservation_expired"},
                )
                expired.append(self.get_reservation(reservation["reservation_id"]))
        return expired

    def release_inactive_cycle_reservations(self, reason="cycle_locked"):
        released = []
        with self.transaction():
            conn = self._transaction_conn
            rows = conn.execute(
                """
                SELECT r.*
                FROM ghost_part_reservations r
                LEFT JOIN ghost_cycles c ON c.cycle_id = r.cycle_id
                WHERE r.status = 'active'
                  AND (c.cycle_id IS NULL OR c.status != 'active')
                """
            ).fetchall()
            now = self.now()
            for row in rows:
                reservation = self._reservation(row)
                conn.execute(
                    """
                    UPDATE ghost_part_reservations
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE reservation_id = ?
                    """,
                    (now, _clean(reason), reservation["reservation_id"]),
                )
                conn.execute(
                    """
                    UPDATE ghost_parts
                    SET status = 'pooled', target_id = '', latitude = NULL, longitude = NULL, updated_at = ?
                    WHERE part_id = ? AND status = 'reserved'
                    """,
                    (now, reservation["part_id"]),
                )
                version = self._bump_version(conn, reservation["cycle_id"])
                self.append_event(
                    "ghost.part_reservation_released",
                    cycle_id=reservation["cycle_id"],
                    part_id=reservation["part_id"],
                    entity_id=reservation["part_id"],
                    state_version=version,
                    dedupe_key=f"ghost:reservation_released:{reservation['reservation_id']}:cycle_locked",
                    payload={"reservation_id": reservation["reservation_id"], "reason": _clean(reason)},
                )
                released.append(self.get_reservation(reservation["reservation_id"]))
        return released

    def get_reservation_status(self, cycle_id=None):
        params = []
        where = ""
        if cycle_id:
            where = "WHERE cycle_id = ?"
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            status_rows = conn.execute(
                f"""
                SELECT status, COUNT(*) AS c
                FROM ghost_part_reservations
                {where}
                GROUP BY status
                """,
                params,
            ).fetchall()
            counts = {row["status"]: int(row["c"] or 0) for row in status_rows}

            active_params = []
            active_where = "WHERE r.status = 'active'"
            if cycle_id:
                active_where += " AND r.cycle_id = ?"
                active_params.append(_clean(cycle_id))

            oldest = conn.execute(
                f"""
                SELECT MIN(r.reserved_at) AS oldest
                FROM ghost_part_reservations r
                {active_where}
                """,
                active_params,
            ).fetchone()["oldest"]
            oldest_age = 0
            if oldest:
                try:
                    oldest_dt = datetime.fromisoformat(str(oldest).replace("Z", "+00:00"))
                    now_dt = datetime.fromisoformat(self.now().replace("Z", "+00:00"))
                    oldest_age = max(0, int((now_dt - oldest_dt).total_seconds()))
                except (TypeError, ValueError):
                    oldest_age = 0

            parts_params = []
            parts_where = "WHERE status = 'reserved'"
            if cycle_id:
                parts_where += " AND cycle_id = ?"
                parts_params.append(_clean(cycle_id))
            parts_reserved = conn.execute(
                f"SELECT COUNT(*) AS c FROM ghost_parts {parts_where}",
                parts_params,
            ).fetchone()["c"]

            targets_reserved = conn.execute(
                f"""
                SELECT COUNT(DISTINCT r.target_id) AS c
                FROM ghost_part_reservations r
                {active_where}
                """,
                active_params,
            ).fetchone()["c"]

            integrity_errors = []
            reserved_without_res = conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM ghost_parts p
                LEFT JOIN ghost_part_reservations r
                  ON r.part_id = p.part_id AND r.cycle_id = p.cycle_id AND r.status = 'active'
                WHERE p.status = 'reserved'
                  {"AND p.cycle_id = ?" if cycle_id else ""}
                  AND r.reservation_id IS NULL
                """,
                [_clean(cycle_id)] if cycle_id else [],
            ).fetchone()["c"]
            if reserved_without_res:
                integrity_errors.append("reserved_part_without_active_reservation")

            active_part_not_reserved = conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM ghost_part_reservations r
                LEFT JOIN ghost_parts p ON p.part_id = r.part_id AND p.cycle_id = r.cycle_id
                {active_where}
                  AND (p.part_id IS NULL OR p.status != 'reserved')
                """,
                active_params,
            ).fetchone()["c"]
            if active_part_not_reserved:
                integrity_errors.append("active_reservation_part_not_reserved")

            closed_active = conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM ghost_part_reservations r
                LEFT JOIN ghost_cycles c ON c.cycle_id = r.cycle_id
                {active_where}
                  AND (c.cycle_id IS NULL OR c.status != 'active')
                """,
                active_params,
            ).fetchone()["c"]
            if closed_active:
                integrity_errors.append("active_reservation_not_in_active_cycle")

            return {
                "cycle_id": _clean(cycle_id),
                "active": counts.get("active", 0),
                "expired": counts.get("expired", 0),
                "committed": counts.get("committed", 0),
                "released": counts.get("released", 0),
                "cancelled": counts.get("cancelled", 0),
                "oldest_active_age": oldest_age,
                "parts_reserved": int(parts_reserved or 0),
                "targets_reserved": int(targets_reserved or 0),
                "integrity_errors": integrity_errors,
            }

    def create_connection(self, cycle_id, part_a_id, part_b_id, position_in_ring=0, connection_id=None):
        part_a_id = _clean(part_a_id)
        part_b_id = _clean(part_b_id)
        if not part_a_id or not part_b_id or part_a_id == part_b_id:
            raise RepositoryIntegrityError("Invalid GhostNetwork connection.")
        a_id, b_id = sorted([part_a_id, part_b_id])
        connection_id = _clean(connection_id or _hash_id("connection", cycle_id, a_id, b_id))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            for part_id in (a_id, b_id):
                if not self.get_part(part_id):
                    raise PartNotFound(f"Part not found: {part_id}")
                count = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM ghost_connections
                    WHERE cycle_id = ? AND (part_a_id = ? OR part_b_id = ?)
                    """,
                    (cycle_id, part_id, part_id),
                ).fetchone()["c"]
                if int(count or 0) >= 2:
                    raise RepositoryIntegrityError("Part already has two connections.")
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_connections (
                        connection_id, cycle_id, part_a_id, part_b_id, position_in_ring, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (connection_id, cycle_id, a_id, b_id, int(position_in_ring or 0), self.now()),
                )
            except IntegrityError as exc:
                raise RepositoryIntegrityError(str(exc)) from exc
            version = self._bump_version(conn, cycle_id)
            self.append_event(
                "ghost.connection_created",
                cycle_id=cycle_id,
                entity_id=connection_id,
                state_version=version,
                dedupe_key=f"ghost:connection:{connection_id}",
                payload={"part_a_id": a_id, "part_b_id": b_id},
            )
            return self._connection(
                conn.execute("SELECT * FROM ghost_connections WHERE connection_id = ?", (connection_id,)).fetchone()
            )

    def list_connections(self, cycle_id):
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_connections
                WHERE cycle_id = ?
                ORDER BY position_in_ring ASC, connection_id ASC
                """,
                (_clean(cycle_id),),
            ).fetchall()
            return [self._connection(row) for row in rows]

    def remove_connections_for_cycle(self, cycle_id, signal_id="", reason="ghostsignal_transmission"):
        cycle_id = _clean(cycle_id)
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            count = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM ghost_connections WHERE cycle_id = ?",
                    (cycle_id,),
                ).fetchone()["c"]
                or 0
            )
            if count:
                conn.execute("DELETE FROM ghost_connections WHERE cycle_id = ?", (cycle_id,))
                version = self._bump_version(conn, cycle_id)
                self.append_event(
                    "ghost.connections_closed",
                    cycle_id=cycle_id,
                    entity_id=cycle_id,
                    state_version=version,
                    audience_scope="internal",
                    dedupe_key=f"ghost:connections_closed:{cycle_id}:{_clean(signal_id) or version}",
                    payload={"signal_id": _clean(signal_id), "count": count, "reason": _clean(reason)},
                )
            return {"cycle_id": cycle_id, "removed": count}

    def insert_historical_node(self, node):
        node = node if isinstance(node, dict) else {}
        signal_id = _clean(node.get("signal_id"))
        part_id = _clean(node.get("part_id"))
        cycle_id = _clean(node.get("cycle_id"))
        historical_node_id = _clean(node.get("historical_node_id") or _hash_id("histnode", signal_id, part_id))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_historical_nodes (
                        historical_node_id, signal_id, cycle_id, part_id, part_code,
                        latitude, longitude, discovered_by, owner_id, clan_code,
                        machine_code, profession_code, active_since, active_until,
                        defense_count, status, metadata_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        historical_node_id,
                        signal_id,
                        cycle_id,
                        part_id,
                        _clean(node.get("part_code")),
                        node.get("latitude"),
                        node.get("longitude"),
                        _clean(node.get("discovered_by")),
                        _clean(node.get("owner_id")),
                        _clean(node.get("clan_code")),
                        _clean(node.get("machine_code")),
                        _clean(node.get("profession_code")),
                        _clean(node.get("active_since")),
                        _clean(node.get("active_until")),
                        int(node.get("defense_count") or 0),
                        _clean(node.get("status"), "spent"),
                        dumps_json(node.get("metadata") if isinstance(node.get("metadata"), dict) else {}),
                        _clean(node.get("created_at") or self.now()),
                    ),
                )
            except IntegrityError:
                pass
            row = conn.execute(
                "SELECT * FROM ghost_historical_nodes WHERE signal_id = ? AND part_id = ? LIMIT 1",
                (signal_id, part_id),
            ).fetchone()
            return dict(row) if row else None

    def list_historical_nodes_for_signal(self, signal_id):
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_historical_nodes
                WHERE signal_id = ?
                ORDER BY part_code ASC, part_id ASC
                """,
                (_clean(signal_id),),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_historical_nodes(self, signal_id=None, cycle_id=None, player_id=None, clan_code=None, limit=1000):
        limit = max(1, min(int(limit or 1000), 5000))
        clauses = []
        params = []
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(_clean(signal_id))
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if player_id:
            clauses.append("(discovered_by = ? OR owner_id = ?)")
            params.extend([_clean(player_id), _clean(player_id)])
        if clan_code:
            clauses.append("clan_code = ?")
            params.append(_clean(clan_code))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_historical_nodes
                {where}
                ORDER BY created_at DESC, signal_id DESC, part_code ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [dict(row) for row in rows]

    def append_event(
        self,
        event_type,
        cycle_id=None,
        part_id="",
        entity_id="",
        player_id="",
        clan_code="",
        territory_id="",
        state_version=None,
        audience_scope="system",
        audience_clan="",
        payload=None,
        dedupe_key="",
        event_id=None,
    ):
        payload = payload if isinstance(payload, dict) else {}
        audience_scope = _clean(audience_scope, "system")
        if audience_scope not in AUDIENCE_SCOPES:
            raise RepositoryIntegrityError(f"Invalid audience scope: {audience_scope}")
        with self._conn() as conn:
            cycle_id = _clean(cycle_id or self._active_cycle_id(conn))
            self._require_cycle(conn, cycle_id)
            if dedupe_key:
                existing = conn.execute(
                    "SELECT * FROM ghost_part_events WHERE dedupe_key = ?",
                    (_clean(dedupe_key),),
                ).fetchone()
                if existing:
                    raise RepositoryIntegrityError(f"Duplicate GhostNetwork event: {dedupe_key}")
            if state_version is None:
                state_version = self._bump_version(conn, cycle_id)
            now = self.now()
            event_id = _clean(event_id or _hash_id("event", cycle_id, event_type, entity_id or part_id, state_version, dedupe_key))
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_part_events (
                        event_id, cycle_id, part_id, event_type, player_id,
                        clan_code, territory_id, state_version, created_at,
                        payload_json, dedupe_key, audience_scope, audience_clan, entity_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        cycle_id,
                        _clean(part_id),
                        _clean(event_type),
                        _clean(player_id),
                        _clean(clan_code),
                        _clean(territory_id),
                        int(state_version or 0),
                        now,
                        dumps_json(payload),
                        _clean(dedupe_key),
                        audience_scope,
                        _clean(audience_clan),
                        _clean(entity_id),
                    ),
                )
            except IntegrityError as exc:
                raise RepositoryIntegrityError(str(exc)) from exc
            return self._event(
                conn.execute("SELECT * FROM ghost_part_events WHERE event_id = ?", (event_id,)).fetchone()
            )

    def list_events(self, cycle_id=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        with self._conn() as conn:
            if cycle_id:
                rows = conn.execute(
                    """
                    SELECT * FROM ghost_part_events
                    WHERE cycle_id = ?
                    ORDER BY state_version ASC, created_at ASC
                    LIMIT ?
                    """,
                    (_clean(cycle_id), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ghost_part_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._event(row) for row in rows]

    def get_event(self, event_id):
        event_id = _clean(event_id)
        if not event_id:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_part_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            return self._event(row)

    def list_events_after(self, cycle_id, state_version=0, limit=250):
        cycle_id = _clean(cycle_id)
        if not cycle_id:
            return []
        limit = max(1, min(int(limit or 250), 1000))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_part_events
                WHERE cycle_id = ? AND state_version > ?
                ORDER BY state_version ASC, created_at ASC, event_id ASC
                LIMIT ?
                """,
                (cycle_id, max(0, int(state_version or 0)), limit),
            ).fetchall()
            return [self._event(row) for row in rows]

    def get_last_event(self, cycle_id):
        with self._conn() as conn:
            return self._event(
                conn.execute(
                    """
                    SELECT * FROM ghost_part_events
                    WHERE cycle_id = ?
                    ORDER BY state_version DESC, created_at DESC
                    LIMIT 1
                    """,
                    (_clean(cycle_id),),
                ).fetchone()
            )

    def record_pipeline_outcome(self, phase, outcome, cycle_id=""):
        self.record_pipeline_outcomes([(phase, outcome, cycle_id)])

    def record_pipeline_outcomes(self, outcomes):
        grouped = {}
        for phase, outcome, cycle_id in outcomes or []:
            phase = _clean(phase)
            outcome = _clean(outcome)
            cycle_id = _clean(cycle_id)
            if phase not in {"aim", "capture", "lifecycle"} or not outcome:
                raise ValueError("Invalid GhostNetwork pipeline telemetry outcome.")
            key = (cycle_id, phase, outcome)
            grouped[key] = grouped.get(key, 0) + 1
        if not grouped:
            return
        now = self.now()
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO ghost_pipeline_telemetry(
                    cycle_id, phase, outcome, outcome_count, last_seen_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cycle_id, phase, outcome) DO UPDATE SET
                    outcome_count = outcome_count + excluded.outcome_count,
                    last_seen_at = excluded.last_seen_at
                """,
                [(*key, count, now) for key, count in grouped.items()],
            )

    def get_pipeline_telemetry_summary(self, cycle_id=None):
        params = []
        where = ""
        if cycle_id is not None:
            where = "WHERE cycle_id = ?"
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT phase, outcome, outcome_count AS count
                FROM ghost_pipeline_telemetry
                {where}
                ORDER BY phase, outcome
                """,
                tuple(params),
            ).fetchall()
        phases = {"aim": {}, "capture": {}, "lifecycle": {}}
        for row in rows:
            phases.setdefault(row["phase"], {})[row["outcome"]] = int(row["count"] or 0)
        return {
            "aim": phases.get("aim", {}),
            "capture": phases.get("capture", {}),
            "lifecycle": phases.get("lifecycle", {}),
            "total": sum(int(row["count"] or 0) for row in rows),
        }

    def record_narrative_bridge_metric(self, metric_key, cycle_id="", value=0):
        metric_key = _clean(metric_key)
        if not metric_key or len(metric_key) > 180:
            raise ValueError("Invalid narrative bridge metric key.")
        numeric = max(0.0, float(value or 0))
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ghost_narrative_bridge_telemetry(
                    cycle_id, metric_key, metric_count, value_total, value_max,
                    last_seen_at
                ) VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(cycle_id, metric_key) DO UPDATE SET
                    metric_count = metric_count + 1,
                    value_total = value_total + excluded.value_total,
                    value_max = MAX(value_max, excluded.value_max),
                    last_seen_at = excluded.last_seen_at
                """,
                (_clean(cycle_id), metric_key, numeric, numeric, self.now()),
            )

    def narrative_bridge_metrics(self, cycle_id=None):
        where = ""
        params = []
        if cycle_id is not None:
            where = "WHERE cycle_id = ?"
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT metric_key, SUM(metric_count) AS metric_count,
                       SUM(value_total) AS value_total, MAX(value_max) AS value_max
                FROM ghost_narrative_bridge_telemetry
                {where}
                GROUP BY metric_key ORDER BY metric_key
                """,
                tuple(params),
            ).fetchall()
        metrics = {}
        for row in rows:
            count = int(row["metric_count"] or 0)
            metrics[row["metric_key"]] = {
                "count": count,
                "value_total": round(float(row["value_total"] or 0), 3),
                "value_max": round(float(row["value_max"] or 0), 3),
                "value_avg": round(float(row["value_total"] or 0) / count, 3) if count else 0,
            }
        count_of = lambda key: int((metrics.get(key) or {}).get("count") or 0)
        latency = metrics.get("bridge_latency_ms") or {}
        return {
            "events_seen": count_of("events_seen"),
            "events_eligible": count_of("events_eligible"),
            "events_ignored_by_reason": {
                key.split(":", 1)[1]: value["count"]
                for key, value in metrics.items() if key.startswith("events_ignored:")
            },
            "tasks_by_event_type_audience_medium": {
                key.split(":", 1)[1]: value["count"]
                for key, value in metrics.items() if key.startswith("tasks:")
            },
            "aggregation_input": {
                key.split(":", 1)[1]: value["count"]
                for key, value in metrics.items() if key.startswith("aggregation_input:")
            },
            "aggregation_output": {
                key.split(":", 1)[1]: value["count"]
                for key, value in metrics.items() if key.startswith("aggregation_output:")
            },
            "deduplicated_tasks": count_of("deduplicated_tasks"),
            "task_errors": count_of("task_errors"),
            "bridge_latency_ms": {
                "samples": int(latency.get("count") or 0),
                "average": float(latency.get("value_avg") or 0),
                "maximum": float(latency.get("value_max") or 0),
            },
            "raw": metrics,
        }

    @staticmethod
    def _capture_effect(row):
        if not row:
            return None
        return {
            "effect_id": row["effect_id"],
            "capture_key": row["capture_key"],
            "cycle_id": row["cycle_id"],
            "reservation_id": row["reservation_id"],
            "player_id": row["player_id"],
            "target_id": row["target_id"],
            "player": loads_json(row["player_json"], {}),
            "target": loads_json(row["target_json"], {}),
            "operation": loads_json(row["operation_json"], {}),
            "result": loads_json(row["result_json"], {}),
            "status": row["status"],
            "attempts": int(row["attempts"] or 0),
            "last_outcome": row["last_outcome"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "acknowledged_at": row["acknowledged_at"],
        }

    def enqueue_capture_effect(self, capture_key, player, target, operation=None, result=None,
                               cycle_id="", reservation_id=""):
        capture_key = _clean(capture_key)
        player = player if isinstance(player, dict) else {}
        target = target if isinstance(target, dict) else {}
        player_id = _clean(player.get("player_id") or player.get("username"))
        target_id = _clean(target.get("target_id") or target.get("id"))
        if not capture_key or not player_id or not target_id:
            raise ValueError("capture_key, player_id and target_id are required")
        effect_id = _hash_id("ghost-capture-effect", capture_key)
        now = self.now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ghost_capture_effects(
                    effect_id, capture_key, cycle_id, reservation_id, player_id,
                    target_id, player_json, target_json, operation_json,
                    result_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(capture_key) DO NOTHING
                """,
                (
                    effect_id, capture_key, _clean(cycle_id), _clean(reservation_id),
                    player_id, target_id, dumps_json(player), dumps_json(target),
                    dumps_json(operation or {}), dumps_json(result or {}), now, now,
                ),
            )
            return self._capture_effect(conn.execute(
                "SELECT * FROM ghost_capture_effects WHERE capture_key = ?", (capture_key,)
            ).fetchone())

    def get_capture_effect(self, capture_key):
        with self._conn() as conn:
            return self._capture_effect(conn.execute(
                "SELECT * FROM ghost_capture_effects WHERE capture_key = ?", (_clean(capture_key),)
            ).fetchone())

    def list_capture_effects(self, statuses=None, limit=100):
        statuses = sorted({_clean(value) for value in (statuses or []) if _clean(value)})
        where = ""
        params = []
        if statuses:
            where = "WHERE status IN ({})".format(",".join("?" for _ in statuses))
            params.extend(statuses)
        params.append(max(1, min(int(limit or 100), 1000)))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM ghost_capture_effects {where} ORDER BY updated_at, effect_id LIMIT ?",
                tuple(params),
            ).fetchall()
            return [self._capture_effect(row) for row in rows]

    def mark_capture_effect_attempt(self, effect_id):
        now = self.now()
        with self._conn() as conn:
            conn.execute(
                "UPDATE ghost_capture_effects SET attempts = attempts + 1, updated_at = ? WHERE effect_id = ?",
                (now, _clean(effect_id)),
            )

    def finish_capture_effect(self, effect_id, status, outcome="", error=""):
        if status not in {"pending", "applied", "failed"}:
            raise ValueError("Invalid GhostNetwork capture effect status")
        now = self.now()
        acknowledged_at = now if status == "applied" else ""
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE ghost_capture_effects
                SET status = ?, last_outcome = ?, last_error = ?, updated_at = ?,
                    acknowledged_at = ?
                WHERE effect_id = ?
                """,
                (status, _clean(outcome), str(error or "")[:500], now,
                 acknowledged_at, _clean(effect_id)),
            )
            return self._capture_effect(conn.execute(
                "SELECT * FROM ghost_capture_effects WHERE effect_id = ?", (_clean(effect_id),)
            ).fetchone())

    def get_capture_effect_summary(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM ghost_capture_effects GROUP BY status"
            ).fetchall()
        counts = {row["status"]: int(row["count"] or 0) for row in rows}
        return {
            "pending": counts.get("pending", 0),
            "failed": counts.get("failed", 0),
            "applied": counts.get("applied", 0),
            "total": sum(counts.values()),
        }

    def get_narrative_outbox(self, outbox_id):
        with self._conn() as conn:
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def get_narrative_outbox_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            return self._narrative_outbox(
                conn.execute(
                    """
                    SELECT * FROM ghost_narrative_outbox
                    WHERE dedupe_key = ? AND dedupe_key IS NOT NULL AND dedupe_key != ''
                    LIMIT 1
                    """,
                    (dedupe_key,),
                ).fetchone()
            )

    def enqueue_narrative_task(self, item):
        item = item if isinstance(item, dict) else {}
        now = _iso(item.get("created_at") or self.now())
        target_medium = _clean(item.get("target_medium") or item.get("medium"))
        if not target_medium:
            raise ValueError("Narrative task requires target_medium")
        source_scope = _clean(item.get("source_scope"), "ghostnetwork")
        source_event_id = _clean(item.get("source_event_id") or item.get("event_id"))
        source_receipt_id = _clean(item.get("source_receipt_id"))
        if not source_event_id and not source_receipt_id:
            raise ValueError("Narrative task requires source event or receipt identity")
        processor = _clean(item.get("processor"), NARRATIVE_TASK_PROCESSOR)
        if processor != NARRATIVE_TASK_PROCESSOR:
            raise ValueError("Narrative task processor must be ollama")
        dedupe_item = {
            **item,
            "source_scope": source_scope,
            "source_event_id": source_event_id,
            "source_receipt_id": source_receipt_id,
            "target_medium": target_medium,
        }
        dedupe_key = canonical_narrative_task_dedupe_key(dedupe_item)
        supplied_dedupe_key = _clean(item.get("dedupe_key"))
        if supplied_dedupe_key and supplied_dedupe_key != dedupe_key:
            raise ValueError("Narrative task dedupe_key does not match canonical identity")
        status = _clean(item.get("status"), "ready")
        status = NARRATIVE_TASK_LEGACY_STATUS_MAP.get(status, status)
        if status not in NARRATIVE_TASK_READY_STATUSES:
            raise ValueError("Narrative task enqueue must start ready or retry_wait")
        max_attempts = max(1, min(int(item.get("max_attempts") or 5), 100))
        attempt_count = 0
        completed_at = ""
        dead_lettered_at = ""
        processed_at = ""
        next_attempt_at = _clean(item.get("next_attempt_at"))
        if status in NARRATIVE_TASK_READY_STATUSES and not next_attempt_at:
            next_attempt_at = now
        outbox_id = _hash_id("narrative_task", dedupe_key)
        supplied_outbox_id = _clean(item.get("outbox_id"))
        if supplied_outbox_id and supplied_outbox_id != outbox_id:
            raise ValueError("Narrative task outbox_id does not match canonical identity")
        record = {
            "outbox_id": outbox_id,
            "event_id": _clean(item.get("event_id") or source_event_id or source_receipt_id),
            "cycle_id": _clean(item.get("cycle_id")),
            "signal_id": _clean(item.get("signal_id")),
            "audience_scope": _clean(item.get("audience_scope"), "public"),
            "audience_clan": _clean(item.get("audience_clan")),
            "audience_owner": _clean(item.get("audience_owner")),
            "medium": target_medium,
            "truth_class": _clean(item.get("truth_class"), "canonical"),
            "facts_json": dumps_json(item.get("facts") if isinstance(item.get("facts"), list) else []),
            "allowed_actions_json": dumps_json(
                item.get("allowed_actions") if isinstance(item.get("allowed_actions"), list) else []
            ),
            "canon_version": _clean(item.get("canon_version")),
            "ghostsystem_version": _clean(item.get("ghostsystem_version")),
            "status": status,
            "created_at": now,
            "processed_at": processed_at,
            "validation_json": dumps_json(
                item.get("validation") if isinstance(item.get("validation"), dict) else {}
            ),
            "dedupe_key": dedupe_key,
            "schema_version": _clean(item.get("schema_version"), NARRATIVE_TASK_SCHEMA_VERSION),
            "source_scope": source_scope,
            "source_event_id": source_event_id,
            "source_receipt_id": source_receipt_id,
            "source_app_id": _clean(item.get("source_app_id")),
            "processor": processor,
            "target_medium": target_medium,
            "world_state_version": _clean(item.get("world_state_version")),
            "prompt_version": _clean(item.get("prompt_version"), "unassigned"),
            "output_schema_version": _clean(item.get("output_schema_version"), "unassigned"),
            "model_policy_version": _clean(item.get("model_policy_version"), "unassigned"),
            "truth_class_policy": _clean(item.get("truth_class_policy")),
            "task_variant": _clean(item.get("task_variant"), "default"),
            "narrative_intent": _clean(item.get("narrative_intent")),
            "narrative_thread_id": _clean(item.get("narrative_thread_id")),
            "content_kind": _clean(item.get("content_kind")),
            "presentation_slot": _clean(item.get("presentation_slot")),
            "selected_source_ref": _clean(item.get("selected_source_ref")),
            "selected_source_version": _clean(item.get("selected_source_version")),
            "expected_slot_version": max(0, int(item.get("expected_slot_version") or 0)),
            "fixed_action_json": dumps_json(
                item.get("fixed_action") if isinstance(item.get("fixed_action"), dict) else {}
            ),
            "creative_epoch": max(0, int(item.get("creative_epoch") or 0)),
            "editorial_contract_json": dumps_json(
                item.get("editorial_contract") if isinstance(item.get("editorial_contract"), dict) else {}
            ),
            "allowed_asset_roles_json": dumps_json(
                item.get("allowed_asset_roles") if isinstance(item.get("allowed_asset_roles"), list) else []
            ),
            "priority": int(item.get("priority") or 0),
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "claimed_by": "",
            "claimed_at": "",
            "lease_until": "",
            "next_attempt_at": next_attempt_at,
            "last_error_code": _clean(item.get("last_error_code")),
            "last_error_at": _clean(item.get("last_error_at")),
            "updated_at": _clean(item.get("updated_at") or now),
            "completed_at": completed_at,
            "dead_lettered_at": dead_lettered_at,
        }
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO ghost_narrative_outbox (
                    outbox_id, event_id, cycle_id, signal_id,
                    audience_scope, audience_clan, audience_owner, medium,
                    truth_class, facts_json, allowed_actions_json,
                    canon_version, ghostsystem_version, status,
                    created_at, processed_at, validation_json, dedupe_key,
                    schema_version, source_scope, source_event_id,
                    source_receipt_id, source_app_id, processor, target_medium,
                    world_state_version, prompt_version, output_schema_version,
                    model_policy_version, truth_class_policy, task_variant,
                    narrative_intent, narrative_thread_id, content_kind, presentation_slot, selected_source_ref,
                    selected_source_version, expected_slot_version, fixed_action_json,
                    creative_epoch, editorial_contract_json, allowed_asset_roles_json,
                    priority, attempt_count, max_attempts, claimed_by, claimed_at,
                    lease_until, next_attempt_at, last_error_code, last_error_at,
                    updated_at, completed_at, dead_lettered_at
                )
                VALUES (
                    :outbox_id, :event_id, :cycle_id, :signal_id,
                    :audience_scope, :audience_clan, :audience_owner, :medium,
                    :truth_class, :facts_json, :allowed_actions_json,
                    :canon_version, :ghostsystem_version, :status,
                    :created_at, :processed_at, :validation_json, :dedupe_key,
                    :schema_version, :source_scope, :source_event_id,
                    :source_receipt_id, :source_app_id, :processor, :target_medium,
                    :world_state_version, :prompt_version, :output_schema_version,
                    :model_policy_version, :truth_class_policy, :task_variant,
                    :narrative_intent, :narrative_thread_id, :content_kind, :presentation_slot, :selected_source_ref,
                    :selected_source_version, :expected_slot_version, :fixed_action_json,
                    :creative_epoch, :editorial_contract_json, :allowed_asset_roles_json,
                    :priority, :attempt_count, :max_attempts, :claimed_by, :claimed_at,
                    :lease_until, :next_attempt_at, :last_error_code, :last_error_at,
                    :updated_at, :completed_at, :dead_lettered_at
                )
                """,
                record,
            )
            if cursor.rowcount == 0:
                existing = conn.execute(
                    """
                    SELECT * FROM ghost_narrative_outbox
                    WHERE dedupe_key = ? AND dedupe_key IS NOT NULL AND dedupe_key != ''
                    LIMIT 1
                    """,
                    (dedupe_key,),
                ).fetchone()
                if existing:
                    result = self._narrative_outbox(existing)
                    result["idempotent"] = True
                    if source_scope == "ghostnetwork" and source_event_id:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO ghost_narrative_task_sources(
                                outbox_id, source_event_id, linked_at
                            ) VALUES (?, ?, ?)
                            """,
                            (result["outbox_id"], source_event_id, now),
                        )
                        self._invalidate_active_narrative_thread_for_task(
                            conn, result, invalidating_event_id=source_event_id
                        )
                    return result
                raise RepositoryIntegrityError("Narrative task identity conflict")
            result = self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (outbox_id,),
                ).fetchone()
            )
            if source_scope == "ghostnetwork" and source_event_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ghost_narrative_task_sources(
                        outbox_id, source_event_id, linked_at
                    ) VALUES (?, ?, ?)
                    """,
                    (outbox_id, source_event_id, now),
                )
                self._invalidate_active_narrative_thread_for_task(
                    conn, result, invalidating_event_id=source_event_id
                )
            return result

    @staticmethod
    def _invalidate_active_narrative_thread_for_task(
        conn, task, *, invalidating_event_id
    ):
        """Hide a stale publication as soon as newer canonical state is observed."""
        task = task if isinstance(task, dict) else {}
        lifecycle = build_publication_lifecycle(task)
        thread_id = _clean(lifecycle.get("narrative_thread_id"))
        state_version = int(lifecycle.get("source_state_version") or 0)
        if (
            _clean(task.get("source_scope")) != "ghostnetwork"
            or not thread_id
            or state_version <= 0
            or not _clean(invalidating_event_id)
        ):
            return 0
        cursor = conn.execute(
            """
            UPDATE ghost_narrative_medium_records
            SET active_state = 'invalidated', invalidated_by_event_id = ?,
                invalidation_reason = 'canonical_state_observed'
            WHERE target_medium = ? AND audience_scope = ?
              AND audience_clan = ? AND audience_owner = ?
              AND narrative_thread_id = ? AND active_state = 'active'
              AND source_event_id != ? AND source_state_version <= ?
            """,
            (
                _clean(invalidating_event_id), _clean(task.get("target_medium")),
                _clean(task.get("audience_scope")), _clean(task.get("audience_clan")),
                _clean(task.get("audience_owner")), thread_id,
                _clean(invalidating_event_id), state_version,
            ),
        )
        return cursor.rowcount

    def find_open_narrative_aggregate(
        self, *, cycle_id, task_variant, narrative_thread_id, target_medium,
        audience_scope, audience_clan="", audience_owner="", created_after="",
    ):
        with self._conn() as conn:
            return self._narrative_outbox(conn.execute(
                """
                SELECT * FROM ghost_narrative_outbox
                WHERE source_scope = 'ghostnetwork'
                  AND cycle_id = ? AND task_variant = ?
                  AND narrative_thread_id = ? AND target_medium = ?
                  AND audience_scope = ? AND audience_clan = ? AND audience_owner = ?
                  AND status IN ('ready', 'retry_wait')
                  AND attempt_count = 0 AND claimed_by = ''
                  AND created_at >= ?
                ORDER BY created_at DESC, outbox_id DESC
                LIMIT 1
                """,
                (
                    _clean(cycle_id), _clean(task_variant), _clean(narrative_thread_id),
                    _clean(target_medium), _clean(audience_scope), _clean(audience_clan),
                    _clean(audience_owner), _clean(created_after),
                ),
            ).fetchone())

    def merge_narrative_aggregate(
        self, outbox_id, source_event_id, *, facts, validation,
        world_state_version="", selected_source_version="",
    ):
        now = self.now()
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET facts_json = ?, validation_json = ?, world_state_version = ?,
                    selected_source_version = ?, updated_at = ?
                WHERE outbox_id = ? AND status IN ('ready', 'retry_wait')
                  AND attempt_count = 0 AND claimed_by = ''
                """,
                (
                    dumps_json(facts if isinstance(facts, list) else []),
                    dumps_json(validation if isinstance(validation, dict) else {}),
                    _clean(world_state_version), _clean(selected_source_version), now,
                    _clean(outbox_id),
                ),
            )
            if cursor.rowcount != 1:
                return None
            conn.execute(
                """
                INSERT OR IGNORE INTO ghost_narrative_task_sources(
                    outbox_id, source_event_id, linked_at
                ) VALUES (?, ?, ?)
                """,
                (_clean(outbox_id), _clean(source_event_id), now),
            )
            result = self._narrative_outbox(conn.execute(
                "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                (_clean(outbox_id),),
            ).fetchone())
            self._invalidate_active_narrative_thread_for_task(
                conn, result, invalidating_event_id=source_event_id
            )
            return result

    def list_narrative_task_sources(self, outbox_id):
        with self._conn() as conn:
            return [row["source_event_id"] for row in conn.execute(
                """
                SELECT source_event_id FROM ghost_narrative_task_sources
                WHERE outbox_id = ? ORDER BY linked_at, source_event_id
                """,
                (_clean(outbox_id),),
            ).fetchall()]

    def insert_narrative_outbox(self, item):
        """Compatibility alias for Sprint 129 callers."""
        return self.enqueue_narrative_task(item)

    def list_narrative_outbox(
        self,
        cycle_id=None,
        signal_id=None,
        medium=None,
        status=None,
        limit=100,
        processor=None,
        source_scope=None,
        source_event_id=None,
        source_receipt_id=None,
        cursor=None,
    ):
        limit = max(1, min(int(limit or 100), 1000))
        clauses = []
        params = []
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(_clean(signal_id))
        if medium:
            clauses.append("target_medium = ?")
            params.append(_clean(medium))
        if status:
            clauses.append("status = ?")
            normalized_status = NARRATIVE_TASK_LEGACY_STATUS_MAP.get(_clean(status), _clean(status))
            params.append(normalized_status)
        if processor:
            clauses.append("processor = ?")
            params.append(_clean(processor))
        if source_scope:
            clauses.append("source_scope = ?")
            params.append(_clean(source_scope))
        if source_event_id:
            clauses.append(
                "(source_event_id = ? OR outbox_id IN ("
                "SELECT outbox_id FROM ghost_narrative_task_sources WHERE source_event_id = ?))"
            )
            params.extend([_clean(source_event_id), _clean(source_event_id)])
        if source_receipt_id:
            clauses.append("source_receipt_id = ?")
            params.append(_clean(source_receipt_id))
        if cursor:
            clauses.append(
                "(created_at, outbox_id) > ("
                "SELECT created_at, outbox_id FROM ghost_narrative_outbox WHERE outbox_id = ?"
                ")"
            )
            params.append(_clean(cursor))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_narrative_outbox
                {where}
                ORDER BY created_at ASC, outbox_id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._narrative_outbox(row) for row in rows]

    def count_recent_narrative_tasks(
        self,
        *,
        source_scope,
        source_app_id,
        audience_owner,
        created_after,
    ):
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM ghost_narrative_outbox
                WHERE source_scope = ? AND source_app_id = ?
                  AND audience_owner = ? AND created_at >= ?
                """,
                (
                    _clean(source_scope),
                    _clean(source_app_id),
                    _clean(audience_owner),
                    _clean(created_after),
                ),
            ).fetchone()
            return int(row["count"] or 0) if row else 0

    def narrative_task_queue_counts(self, eligible_policies=None, now=None):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM ghost_narrative_outbox
                WHERE processor = ?
                GROUP BY status
                """,
                (NARRATIVE_TASK_PROCESSOR,),
            ).fetchall()
            counts = {str(row["status"]): int(row["count"] or 0) for row in rows}
            version_rows = conn.execute(
                """
                SELECT prompt_version, COUNT(*) AS count
                FROM ghost_narrative_outbox
                WHERE processor = ? AND status IN ('ready', 'retry_wait')
                GROUP BY prompt_version
                ORDER BY prompt_version
                """,
                (NARRATIVE_TASK_PROCESSOR,),
            ).fetchall()
            ready_by_prompt_version = {
                str(row["prompt_version"]): int(row["count"] or 0)
                for row in version_rows
            }
            policy_clause, policy_params = _narrative_policy_sql(eligible_policies)
            eligibility = conn.execute(
                f"""
                SELECT
                    SUM(CASE WHEN {policy_clause}
                        AND ((audience_scope = 'public' AND audience_clan = '' AND audience_owner = '')
                          OR (audience_scope = 'clan' AND audience_clan != '' AND audience_owner = '')
                          OR (audience_scope = 'owner' AND audience_owner != ''))
                        THEN 1 ELSE 0 END) AS eligible,
                    SUM(CASE WHEN NOT ({policy_clause})
                        OR NOT ((audience_scope = 'public' AND audience_clan = '' AND audience_owner = '')
                          OR (audience_scope = 'clan' AND audience_clan != '' AND audience_owner = '')
                          OR (audience_scope = 'owner' AND audience_owner != ''))
                        THEN 1 ELSE 0 END) AS ineligible,
                    MIN(CASE WHEN {policy_clause}
                        AND status IN ('ready', 'retry_wait')
                        AND (next_attempt_at = '' OR next_attempt_at <= ?)
                        THEN created_at ELSE NULL END) AS oldest_eligible_ready
                FROM ghost_narrative_outbox
                WHERE processor = ? AND status IN ('ready', 'retry_wait')
                """,
                tuple(
                    policy_params
                    + policy_params
                    + policy_params
                    + [now_iso, NARRATIVE_TASK_PROCESSOR]
                ),
            ).fetchone()
            runtime = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status IN ('claimed', 'processing')
                        AND lease_until != '' AND lease_until <= ?
                        THEN 1 ELSE 0 END) AS expired_leases,
                    SUM(CASE WHEN medium = 'ollama_outbox'
                        AND status NOT IN ('completed', 'dead_letter')
                        THEN 1 ELSE 0 END) AS active_legacy_file_tasks
                FROM ghost_narrative_outbox
                WHERE processor = ?
                """,
                (now_iso, NARRATIVE_TASK_PROCESSOR),
            ).fetchone()
        return {
            "statuses": counts,
            "eligible_ready": int((eligibility or {})["eligible"] or 0),
            "ineligible_ready": int((eligibility or {})["ineligible"] or 0),
            "ready_by_prompt_version": ready_by_prompt_version,
            "oldest_eligible_ready": (
                str((eligibility or {})["oldest_eligible_ready"] or "")
            ),
            "expired_leases": int((runtime or {})["expired_leases"] or 0),
            "active_legacy_file_tasks": int(
                (runtime or {})["active_legacy_file_tasks"] or 0
            ),
        }

    def narrative_runtime_health(self, eligible_policies=None, now=None, sample_limit=25):
        """Bounded operational invariants for the canonical Ollama queue."""
        now_iso = _iso(now if now is not None else self.now())
        sample_limit = max(1, min(int(sample_limit or 25), 100))
        queue = self.narrative_task_queue_counts(eligible_policies, now=now_iso)
        with self._conn() as conn:
            active_invalid = conn.execute(
                """
                SELECT outbox_id FROM ghost_narrative_outbox
                WHERE processor = ? AND status IN ('claimed', 'processing')
                  AND (claimed_by = '' OR lease_until = '')
                ORDER BY updated_at ASC LIMIT ?
                """,
                (NARRATIVE_TASK_PROCESSOR, sample_limit),
            ).fetchall()
            exhausted = conn.execute(
                """
                SELECT outbox_id FROM ghost_narrative_outbox
                WHERE processor = ? AND status IN ('ready', 'retry_wait')
                  AND attempt_count >= max_attempts
                ORDER BY updated_at ASC LIMIT ?
                """,
                (NARRATIVE_TASK_PROCESSOR, sample_limit),
            ).fetchall()
            retry_rows = conn.execute(
                """
                SELECT outbox_id, attempt_count, next_attempt_at, last_error_at
                FROM ghost_narrative_outbox
                WHERE processor = ? AND status = 'retry_wait'
                ORDER BY updated_at DESC LIMIT 1000
                """,
                (NARRATIVE_TASK_PROCESSOR,),
            ).fetchall()
            incomplete_attempts = conn.execute(
                """
                SELECT a.attempt_id
                FROM ghost_narrative_inbox_attempts a
                LEFT JOIN ghost_narrative_outbox o ON o.outbox_id = a.task_id
                WHERE a.status = 'started'
                  AND (
                    o.outbox_id IS NULL
                    OR o.status NOT IN ('claimed', 'processing')
                    OR o.lease_until = ''
                    OR o.lease_until <= ?
                  )
                ORDER BY a.created_at DESC LIMIT ?
                """,
                (now_iso, sample_limit),
            ).fetchall()
            attempt_status_rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM ghost_narrative_inbox_attempts
                GROUP BY status ORDER BY status
                """
            ).fetchall()
            retry_error_rows = conn.execute(
                """
                SELECT error_code, COUNT(*) AS count
                FROM ghost_narrative_inbox_attempts
                WHERE retryable = 1 AND error_code != ''
                GROUP BY error_code ORDER BY count DESC, error_code
                LIMIT 25
                """
            ).fetchall()
            recovered = conn.execute(
                """
                SELECT COUNT(*) AS count FROM ghost_narrative_inbox_attempts
                WHERE result = 'candidate_recovered'
                """
            ).fetchone()

        schedule_violations = []
        for row in retry_rows:
            try:
                expected = _utc_datetime(row["last_error_at"]) + timedelta(
                    seconds=narrative_task_retry_backoff_seconds(row["attempt_count"])
                )
                actual = _utc_datetime(row["next_attempt_at"])
            except (TypeError, ValueError):
                schedule_violations.append(str(row["outbox_id"]))
                continue
            if abs((actual - expected).total_seconds()) > 1:
                schedule_violations.append(str(row["outbox_id"]))
            if len(schedule_violations) >= sample_limit:
                break

        return {
            "queue": queue,
            "active_without_lease": len(active_invalid),
            "active_without_lease_samples": [str(row["outbox_id"]) for row in active_invalid],
            "exhausted_nonterminal": len(exhausted),
            "exhausted_nonterminal_samples": [str(row["outbox_id"]) for row in exhausted],
            "retry_schedule_violations": len(schedule_violations),
            "retry_schedule_violation_samples": schedule_violations,
            "incomplete_attempts": len(incomplete_attempts),
            "incomplete_attempt_samples": [str(row["attempt_id"]) for row in incomplete_attempts],
            "attempt_statuses": {
                str(row["status"]): int(row["count"] or 0) for row in attempt_status_rows
            },
            "retryable_errors": {
                str(row["error_code"]): int(row["count"] or 0) for row in retry_error_rows
            },
            "candidate_recoveries": int((recovered or {})["count"] or 0),
        }

    def retire_ineligible_narrative_tasks(
        self, eligible_policies, *, reason_code="policy_superseded_cutover",
        limit=500, now=None,
    ):
        """Terminally retire bounded queued work no active worker can claim."""
        policy_clause, policy_params = _narrative_policy_sql(eligible_policies)
        if not policy_params:
            raise ValueError("Narrative cutover requires at least one eligible policy")
        bounded_limit = max(1, min(int(limit or 500), 500))
        now_iso = _iso(now if now is not None else self.now())
        valid_audience = (
            "((audience_scope = 'public' AND audience_clan = '' AND audience_owner = '') "
            "OR (audience_scope = 'clan' AND audience_clan != '' AND audience_owner = '') "
            "OR (audience_scope = 'owner' AND audience_owner != ''))"
        )
        with self.transaction():
            conn = self._transaction_conn
            rows = conn.execute(
                f"""
                SELECT outbox_id
                FROM ghost_narrative_outbox
                WHERE processor = ? AND status IN ('ready', 'retry_wait')
                  AND (NOT ({policy_clause}) OR NOT ({valid_audience}))
                ORDER BY created_at ASC, outbox_id ASC
                LIMIT ?
                """,
                tuple([NARRATIVE_TASK_PROCESSOR] + policy_params + [bounded_limit]),
            ).fetchall()
            task_ids = [str(row["outbox_id"]) for row in rows]
            if not task_ids:
                return []
            placeholders = ",".join("?" for _item in task_ids)
            conn.execute(
                f"""
                UPDATE ghost_narrative_outbox
                SET status = 'dead_letter', last_error_code = ?,
                    dead_lettered_at = ?, processed_at = ?, updated_at = ?,
                    claimed_by = '', claimed_at = '', lease_until = '',
                    next_attempt_at = ''
                WHERE outbox_id IN ({placeholders})
                  AND status IN ('ready', 'retry_wait')
                """,
                tuple([_clean(reason_code, "policy_superseded_cutover"), now_iso,
                       now_iso, now_iso] + task_ids),
            )
            return task_ids

    def get_latest_narrative_task(
        self,
        target_medium=None,
        status=None,
        processor=NARRATIVE_TASK_PROCESSOR,
    ):
        clauses = ["processor = ?"]
        params = [_clean(processor, NARRATIVE_TASK_PROCESSOR)]
        if target_medium:
            clauses.append("target_medium = ?")
            params.append(_clean(target_medium))
        if status:
            normalized_status = NARRATIVE_TASK_LEGACY_STATUS_MAP.get(_clean(status), _clean(status))
            clauses.append("status = ?")
            params.append(normalized_status)
        with self._conn() as conn:
            return self._narrative_outbox(
                conn.execute(
                    f"""
                    SELECT * FROM ghost_narrative_outbox
                    WHERE {' AND '.join(clauses)}
                    ORDER BY updated_at DESC, created_at DESC, outbox_id DESC
                    LIMIT 1
                    """,
                    tuple(params),
                ).fetchone()
            )

    def _recover_expired_narrative_leases_conn(self, conn, now, limit):
        rows = conn.execute(
            """
            SELECT outbox_id, status, lease_until, attempt_count, max_attempts
            FROM ghost_narrative_outbox
            WHERE status IN ('claimed', 'processing')
              AND lease_until != ''
              AND lease_until <= ?
            ORDER BY lease_until ASC, outbox_id ASC
            LIMIT ?
            """,
            (now, max(1, min(int(limit or 100), 1000))),
        ).fetchall()
        recovered = []
        for row in rows:
            exhausted = int(row["attempt_count"] or 0) >= max(1, int(row["max_attempts"] or 5))
            next_status = "dead_letter" if exhausted else "ready"
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = ?, claimed_by = '', claimed_at = '', lease_until = '',
                    next_attempt_at = ?, last_error_code = 'lease_expired',
                    last_error_at = ?, updated_at = ?,
                    dead_lettered_at = CASE WHEN ? = 'dead_letter' THEN ? ELSE dead_lettered_at END,
                    processed_at = CASE WHEN ? = 'dead_letter' THEN ? ELSE processed_at END
                WHERE outbox_id = ? AND status = ? AND lease_until = ?
                """,
                (
                    next_status,
                    "" if exhausted else now,
                    now,
                    now,
                    next_status,
                    now,
                    next_status,
                    now,
                    row["outbox_id"],
                    row["status"],
                    row["lease_until"],
                ),
            )
            if cursor.rowcount == 1:
                recovered.append(row["outbox_id"])
        return recovered

    def recover_expired_narrative_leases(self, now=None, limit=100):
        now_iso = _iso(now if now is not None else self.now())
        with self.transaction():
            conn = self._transaction_conn
            recovered_ids = self._recover_expired_narrative_leases_conn(conn, now_iso, limit)
            return [
                self._narrative_outbox(
                    conn.execute(
                        "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                        (outbox_id,),
                    ).fetchone()
                )
                for outbox_id in recovered_ids
            ]

    def claim_next_narrative_task(
        self,
        worker_id,
        lease_seconds=60,
        processor=NARRATIVE_TASK_PROCESSOR,
        target_medium=None,
        eligible_policies=None,
        now=None,
        recovery_limit=100,
    ):
        worker_id = _clean(worker_id)
        if not worker_id:
            raise ValueError("Narrative task claim requires worker_id")
        lease_seconds = max(1, min(int(lease_seconds or 60), 3600))
        now_iso = _iso(now if now is not None else self.now())
        lease_until = _iso(_utc_datetime(now_iso) + timedelta(seconds=lease_seconds))
        with self.transaction():
            conn = self._transaction_conn
            self._recover_expired_narrative_leases_conn(conn, now_iso, recovery_limit)
            normalized_processor = _clean(processor, NARRATIVE_TASK_PROCESSOR)
            if eligible_policies is not None and normalized_processor != NARRATIVE_TASK_PROCESSOR:
                return None
            clauses = [
                (
                    "processor = 'ollama'"
                    if eligible_policies is not None
                    else "processor = ?"
                ),
                "status IN ('ready', 'retry_wait')",
                "attempt_count < max_attempts",
                "(next_attempt_at = '' OR next_attempt_at <= ?)",
            ]
            params = (
                [now_iso]
                if eligible_policies is not None
                else [normalized_processor, now_iso]
            )
            if target_medium:
                clauses.append("target_medium = ?")
                params.append(_clean(target_medium))
            if eligible_policies is not None:
                clauses.extend((
                    "prompt_version != 'unassigned'",
                    "output_schema_version != 'unassigned'",
                    "model_policy_version != 'unassigned'",
                ))
                policy_clause, policy_params = _narrative_policy_sql(eligible_policies)
                clauses.append(policy_clause)
                params.extend(policy_params)
                clauses.append(
                    "((audience_scope = 'public' AND audience_clan = '' AND audience_owner = '') "
                    "OR (audience_scope = 'clan' AND audience_clan != '' AND audience_owner = '') "
                    "OR (audience_scope = 'owner' AND audience_owner != ''))"
                )
            index_hint = (
                "INDEXED BY idx_ghost_narrative_registered_ready"
                if eligible_policies is not None
                else ""
            )
            row = conn.execute(
                f"""
                SELECT * FROM ghost_narrative_outbox {index_hint}
                WHERE {' AND '.join(clauses)}
                ORDER BY priority DESC, next_attempt_at ASC, created_at ASC, outbox_id ASC
                LIMIT 1
                """,
                tuple(params),
            ).fetchone()
            if not row:
                return None
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'claimed', claimed_by = ?, claimed_at = ?, lease_until = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE outbox_id = ? AND status = ?
                  AND attempt_count < max_attempts
                  AND (next_attempt_at = '' OR next_attempt_at <= ?)
                """,
                (
                    worker_id,
                    now_iso,
                    lease_until,
                    now_iso,
                    row["outbox_id"],
                    row["status"],
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (row["outbox_id"],),
                ).fetchone()
            )

    def renew_narrative_task_lease(
        self,
        outbox_id,
        worker_id,
        expected_lease_until,
        lease_seconds=60,
        now=None,
    ):
        now_iso = _iso(now if now is not None else self.now())
        expected_lease_until = _clean(expected_lease_until)
        if not _clean(worker_id) or not expected_lease_until:
            return None
        base = max(_utc_datetime(now_iso), _utc_datetime(expected_lease_until))
        next_lease_until = _iso(base + timedelta(seconds=max(1, min(int(lease_seconds or 60), 3600))))
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET lease_until = ?, updated_at = ?
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                """,
                (
                    next_lease_until,
                    now_iso,
                    _clean(outbox_id),
                    _clean(worker_id),
                    expected_lease_until,
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def mark_narrative_task_processing(self, outbox_id, worker_id, expected_lease_until, now=None):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'processing', updated_at = ?
                WHERE outbox_id = ? AND status = 'claimed' AND claimed_by = ?
                  AND lease_until = ? AND lease_until > ?
                """,
                (
                    now_iso,
                    _clean(outbox_id),
                    _clean(worker_id),
                    _clean(expected_lease_until),
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def complete_narrative_task(self, outbox_id, worker_id, expected_lease_until, now=None):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'completed', completed_at = ?, processed_at = ?,
                    updated_at = ?, next_attempt_at = '', last_error_code = ''
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                """,
                (
                    now_iso,
                    now_iso,
                    now_iso,
                    _clean(outbox_id),
                    _clean(worker_id),
                    _clean(expected_lease_until),
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def retry_narrative_task(
        self,
        outbox_id,
        worker_id,
        expected_lease_until,
        reason_code,
        backoff_seconds=None,
        now=None,
    ):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                (_clean(outbox_id),),
            ).fetchone()
            current = self._narrative_outbox(row)
            if not current:
                return None
            exhausted = current["attempt_count"] >= current["max_attempts"]
            next_status = "dead_letter" if exhausted else "retry_wait"
            if backoff_seconds is None:
                backoff_seconds = narrative_task_retry_backoff_seconds(current["attempt_count"])
            backoff_seconds = max(0, min(int(backoff_seconds or 0), 86400))
            next_attempt_at = "" if exhausted else _iso(
                _utc_datetime(now_iso) + timedelta(seconds=backoff_seconds)
            )
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = ?, claimed_by = '', claimed_at = '', lease_until = '',
                    next_attempt_at = ?, last_error_code = ?, last_error_at = ?,
                    updated_at = ?, dead_lettered_at = CASE
                        WHEN ? = 'dead_letter' THEN ? ELSE dead_lettered_at END,
                    processed_at = CASE WHEN ? = 'dead_letter' THEN ? ELSE processed_at END
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                """,
                (
                    next_status,
                    next_attempt_at,
                    _clean(reason_code, "worker_retry"),
                    now_iso,
                    now_iso,
                    next_status,
                    now_iso,
                    next_status,
                    now_iso,
                    _clean(outbox_id),
                    _clean(worker_id),
                    _clean(expected_lease_until),
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def dead_letter_narrative_task(
        self,
        outbox_id,
        worker_id,
        expected_lease_until,
        reason_code,
        now=None,
    ):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'dead_letter', dead_lettered_at = ?, processed_at = ?,
                    updated_at = ?, next_attempt_at = '', last_error_code = ?,
                    last_error_at = ?
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                """,
                (
                    now_iso,
                    now_iso,
                    now_iso,
                    _clean(reason_code, "worker_dead_letter"),
                    now_iso,
                    _clean(outbox_id),
                    _clean(worker_id),
                    _clean(expected_lease_until),
                    now_iso,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def begin_narrative_attempt(
        self,
        task,
        worker_id,
        expected_lease_until,
        model_name,
        model_digest,
        request_hash="",
        input_bytes=0,
        fact_count=0,
        now=None,
    ):
        task = task if isinstance(task, dict) else {}
        task_id = _clean(task.get("outbox_id") or task.get("task_id"))
        attempt_number = max(1, int(task.get("attempt_count") or 1))
        worker_id = _clean(worker_id)
        expected_lease_until = _clean(expected_lease_until)
        if not task_id or not worker_id or not expected_lease_until:
            return None
        attempt_id = _hash_id("narrative_attempt", task_id, attempt_number)
        now_iso = _iso(now if now is not None else self.now())
        with self.transaction():
            conn = self._transaction_conn
            owned = conn.execute(
                """
                SELECT 1 FROM ghost_narrative_outbox
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                LIMIT 1
                """,
                (task_id, worker_id, expected_lease_until, now_iso),
            ).fetchone()
            if not owned:
                return None
            conn.execute(
                """
                INSERT OR IGNORE INTO ghost_narrative_inbox_attempts (
                    attempt_id, task_id, attempt_number, worker_id, status,
                    model_name, model_digest, ollama_runtime_version,
                    prompt_version, output_schema_version, model_policy_version,
                    request_hash, input_bytes, fact_count,
                    started_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'started', ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    task_id,
                    attempt_number,
                    worker_id,
                    _clean(model_name),
                    _clean(model_digest),
                    _clean(task.get("prompt_version")),
                    _clean(task.get("output_schema_version")),
                    _clean(task.get("model_policy_version")),
                    _clean(request_hash),
                    max(0, int(input_bytes or 0)),
                    max(0, int(fact_count or 0)),
                    now_iso,
                    now_iso,
                    now_iso,
                ),
            )
            return self._narrative_attempt(conn.execute(
                "SELECT * FROM ghost_narrative_inbox_attempts WHERE attempt_id = ? LIMIT 1",
                (attempt_id,),
            ).fetchone())

    def finish_narrative_attempt(
        self,
        attempt_id,
        *,
        status,
        result="",
        error_code="",
        error_message="",
        retryable=False,
        generation=None,
        now=None,
    ):
        allowed_statuses = {
            "model_completed", "candidate_recorded", "completed", "retry",
            "failed", "lease_lost",
        }
        status = _clean(status)
        if status not in allowed_statuses:
            raise ValueError("Invalid narrative attempt status")
        generation = generation if isinstance(generation, dict) else {}
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_inbox_attempts
                SET status = ?, result = ?, error_code = ?, error_message = ?,
                    retryable = ?, response_hash = ?, ollama_runtime_version = ?,
                    total_duration_ns = ?, load_duration_ns = ?,
                    prompt_eval_count = ?, eval_count = ?,
                    completed_at = ?, updated_at = ?
                WHERE attempt_id = ?
                """,
                (
                    status,
                    _clean(result),
                    _clean(error_code),
                    _clean(error_message)[:240],
                    1 if retryable else 0,
                    _clean(generation.get("raw_response_hash")),
                    _clean(generation.get("runtime_version")),
                    int(generation.get("total_duration_ns") or 0),
                    int(generation.get("load_duration_ns") or 0),
                    int(generation.get("prompt_eval_count") or 0),
                    int(generation.get("eval_count") or 0),
                    now_iso,
                    now_iso,
                    _clean(attempt_id),
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_attempt(conn.execute(
                "SELECT * FROM ghost_narrative_inbox_attempts WHERE attempt_id = ? LIMIT 1",
                (_clean(attempt_id),),
            ).fetchone())

    def record_narrative_candidate(
        self,
        task,
        attempt_id,
        worker_id,
        expected_lease_until,
        validation,
        raw_output,
        generation,
        now=None,
    ):
        task = task if isinstance(task, dict) else {}
        validation = validation if isinstance(validation, dict) else {}
        generation = generation if isinstance(generation, dict) else {}
        task_id = _clean(task.get("outbox_id") or task.get("task_id"))
        validation_status = _clean(validation.get("status"))
        if validation_status not in {"accepted", "quarantined", "rejected"}:
            raise ValueError("Narrative candidate requires terminal validation")
        output = validation.get("output") if isinstance(validation.get("output"), dict) else {}
        resolved_cta = (
            validation.get("resolved_cta")
            if isinstance(validation.get("resolved_cta"), dict)
            else {}
        )
        resolved_asset_ref = _clean(validation.get("resolved_asset_ref"))
        raw_output = str(raw_output or "")
        raw_bytes = raw_output.encode("utf-8")[:16 * 1024]
        bounded_raw = raw_bytes.decode("utf-8", errors="ignore")
        now_iso = _iso(now if now is not None else self.now())
        candidate_id = _hash_id("narrative_candidate", task_id, attempt_id)
        with self.transaction():
            conn = self._transaction_conn
            owned = conn.execute(
                """
                SELECT 1 FROM ghost_narrative_outbox
                WHERE outbox_id = ? AND claimed_by = ?
                  AND status IN ('claimed', 'processing')
                  AND lease_until = ? AND lease_until > ?
                LIMIT 1
                """,
                (
                    task_id,
                    _clean(worker_id),
                    _clean(expected_lease_until),
                    now_iso,
                ),
            ).fetchone()
            attempt = conn.execute(
                """
                SELECT 1 FROM ghost_narrative_inbox_attempts
                WHERE attempt_id = ? AND task_id = ? LIMIT 1
                """,
                (_clean(attempt_id), task_id),
            ).fetchone()
            if not owned or not attempt:
                return None
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_narrative_inbox_candidates (
                        candidate_id, task_id, attempt_id, source_scope,
                        source_event_id, source_receipt_id, output_schema_version,
                        prompt_version, model_policy_version, model_name,
                        model_digest, ollama_runtime_version, target_medium,
                        audience_scope, audience_clan, audience_owner, truth_class,
                        title, body, tone, fact_refs_json, cta_ref, cta_action,
                        cta_payload_json, asset_ref, bounded_raw_output, output_hash,
                        validation_status, validation_errors_json,
                        quarantine_reason, created_at, validated_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        candidate_id,
                        task_id,
                        _clean(attempt_id),
                        _clean(task.get("source_scope")),
                        _clean(task.get("source_event_id")),
                        _clean(task.get("source_receipt_id")),
                        _clean(task.get("output_schema_version")),
                        _clean(task.get("prompt_version")),
                        _clean(task.get("model_policy_version")),
                        _clean(generation.get("model")),
                        _clean(generation.get("model_digest")),
                        _clean(generation.get("runtime_version")),
                        _clean(task.get("target_medium") or task.get("medium")),
                        _clean(task.get("audience_scope")),
                        _clean(task.get("audience_clan")),
                        _clean(task.get("audience_owner")),
                        _clean(task.get("truth_class")),
                        str(output.get("title") or "")[:96],
                        str(output.get("body") or "")[:800],
                        _clean(output.get("tone")),
                        dumps_json(output.get("fact_refs") if isinstance(output.get("fact_refs"), list) else []),
                        _clean(output.get("cta_ref")),
                        _clean(resolved_cta.get("cta_action")),
                        dumps_json(
                            resolved_cta.get("payload")
                            if isinstance(resolved_cta.get("payload"), dict)
                            else {}
                        ),
                        resolved_asset_ref,
                        bounded_raw,
                        hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
                        validation_status,
                        dumps_json(validation.get("errors") if isinstance(validation.get("errors"), list) else []),
                        _clean((validation.get("errors") or [""])[0]) if validation_status == "quarantined" else "",
                        now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
            except IntegrityError:
                existing = conn.execute(
                    """
                    SELECT * FROM ghost_narrative_inbox_candidates
                    WHERE attempt_id = ?
                       OR (task_id = ? AND validation_status = 'accepted')
                    ORDER BY CASE WHEN attempt_id = ? THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (_clean(attempt_id), task_id, _clean(attempt_id)),
                ).fetchone()
                return self._narrative_candidate(existing)
            return self._narrative_candidate(conn.execute(
                "SELECT * FROM ghost_narrative_inbox_candidates WHERE attempt_id = ? LIMIT 1",
                (_clean(attempt_id),),
            ).fetchone())

    def get_narrative_candidate_for_task(self, task_id):
        with self._conn() as conn:
            return self._narrative_candidate(conn.execute(
                """
                SELECT * FROM ghost_narrative_inbox_candidates
                WHERE task_id = ?
                ORDER BY CASE validation_status WHEN 'accepted' THEN 0 ELSE 1 END,
                         created_at ASC, candidate_id ASC
                LIMIT 1
                """,
                (_clean(task_id),),
            ).fetchone())

    def get_narrative_candidate(self, candidate_id):
        with self._conn() as conn:
            return self._narrative_candidate(conn.execute(
                "SELECT * FROM ghost_narrative_inbox_candidates WHERE candidate_id = ? LIMIT 1",
                (_clean(candidate_id),),
            ).fetchone())

    def list_narrative_candidates(self, validation_status=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        clauses = []
        params = []
        if validation_status:
            clauses.append("validation_status = ?")
            params.append(_clean(validation_status))
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_narrative_inbox_candidates
                {where}
                ORDER BY created_at ASC, candidate_id ASC LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._narrative_candidate(row) for row in rows]

    def list_unstaged_narrative_candidates(self, validation_status="accepted", limit=100):
        """Return bounded candidates that do not have a publication identity yet."""
        limit = max(1, min(int(limit or 100), 1000))
        clauses = ["r.publication_receipt_id IS NULL"]
        params = []
        if validation_status:
            clauses.append("c.validation_status = ?")
            params.append(_clean(validation_status))
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT c.*
                FROM ghost_narrative_inbox_candidates c
                LEFT JOIN ghost_narrative_publication_receipts r
                  ON r.candidate_id = c.candidate_id
                WHERE {' AND '.join(clauses)}
                ORDER BY c.created_at DESC, c.candidate_id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._narrative_candidate(row) for row in rows]

    def ensure_narrative_publication(self, candidate_id, now=None):
        """Create the one canonical publication identity for an accepted candidate."""
        now_iso = _iso(now if now is not None else self.now())
        with self.transaction():
            conn = self._transaction_conn
            row = conn.execute(
                """
                SELECT c.*, o.target_medium AS task_medium,
                       o.audience_scope AS task_audience_scope,
                       o.audience_clan AS task_audience_clan,
                       o.audience_owner AS task_audience_owner
                FROM ghost_narrative_inbox_candidates c
                JOIN ghost_narrative_outbox o ON o.outbox_id = c.task_id
                WHERE c.candidate_id = ? LIMIT 1
                """,
                (_clean(candidate_id),),
            ).fetchone()
            if not row or row["validation_status"] != "accepted":
                return None
            target_medium = _clean(row["target_medium"])
            audience = (
                _clean(row["audience_scope"]),
                _clean(row["audience_clan"]),
                _clean(row["audience_owner"]),
            )
            if target_medium not in {"blacknet", "googleplex_news", "cyberner", "radio"}:
                return None
            if target_medium != _clean(row["task_medium"]) or audience != (
                _clean(row["task_audience_scope"]),
                _clean(row["task_audience_clan"]),
                _clean(row["task_audience_owner"]),
            ):
                return None
            receipt_id = _hash_id("narrative_publication", row["candidate_id"], target_medium, *audience)
            record_id = _hash_id("narrative_medium", receipt_id)
            conn.execute(
                """
                INSERT INTO ghost_narrative_publication_receipts (
                    publication_receipt_id, candidate_id, task_id, target_medium,
                    audience_scope, audience_clan, audience_owner, status,
                    medium_record_id, next_attempt_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?)
                ON CONFLICT(candidate_id, target_medium, audience_scope,
                            audience_clan, audience_owner) DO NOTHING
                """,
                (
                    receipt_id, row["candidate_id"], row["task_id"], target_medium,
                    *audience, record_id, now_iso, now_iso, now_iso,
                ),
            )
            return self._narrative_publication_receipt(conn.execute(
                """
                SELECT * FROM ghost_narrative_publication_receipts
                WHERE candidate_id = ? AND target_medium = ?
                  AND audience_scope = ? AND audience_clan = ? AND audience_owner = ?
                LIMIT 1
                """,
                (row["candidate_id"], target_medium, *audience),
            ).fetchone())

    def narrative_publication_queue_counts(self, now=None):
        """Return bounded operational counts without loading candidates or profiles."""
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM ghost_narrative_publication_receipts
                GROUP BY status
                """
            ).fetchall()
            medium_rows = conn.execute(
                """
                SELECT target_medium, COUNT(*) AS count
                FROM ghost_narrative_medium_records
                GROUP BY target_medium
                """
            ).fetchall()
            runtime = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status IN ('ready', 'retry_wait')
                        AND (next_attempt_at = '' OR next_attempt_at <= ?)
                        THEN 1 ELSE 0 END) AS ready_now,
                    MIN(CASE WHEN status IN ('ready', 'retry_wait')
                        AND (next_attempt_at = '' OR next_attempt_at <= ?)
                        THEN created_at ELSE NULL END) AS oldest_ready,
                    SUM(CASE WHEN status = 'claimed' AND lease_until != ''
                        AND lease_until <= ? THEN 1 ELSE 0 END) AS expired_claims
                FROM ghost_narrative_publication_receipts
                """,
                (now_iso, now_iso, now_iso),
            ).fetchone()
            unstaged = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM ghost_narrative_inbox_candidates c
                LEFT JOIN ghost_narrative_publication_receipts r
                  ON r.candidate_id = c.candidate_id
                 AND r.target_medium = c.target_medium
                 AND r.audience_scope = c.audience_scope
                 AND r.audience_clan = c.audience_clan
                 AND r.audience_owner = c.audience_owner
                WHERE c.validation_status = 'accepted'
                  AND r.publication_receipt_id IS NULL
                """
            ).fetchone()
        return {
            "statuses": {str(row["status"]): int(row["count"] or 0) for row in rows},
            "published_by_medium": {
                str(row["target_medium"]): int(row["count"] or 0)
                for row in medium_rows
            },
            "ready_now": int((runtime or {})["ready_now"] or 0),
            "oldest_ready": str((runtime or {})["oldest_ready"] or ""),
            "expired_claims": int((runtime or {})["expired_claims"] or 0),
            "unstaged_accepted": int((unstaged or {})["count"] or 0),
        }

    def claim_next_narrative_publication(self, worker_id, lease_seconds=60, now=None):
        worker_id = _clean(worker_id)
        if not worker_id:
            raise ValueError("Publication worker_id is required")
        now_dt = _utc_datetime(now if now is not None else self.now())
        now_iso = _iso(now_dt)
        lease_until = _iso(now_dt + timedelta(seconds=max(10, int(lease_seconds or 60))))
        with self.transaction():
            conn = self._transaction_conn
            conn.execute(
                """
                UPDATE ghost_narrative_publication_receipts
                SET status = 'ready', claimed_by = '', claimed_at = '', lease_until = '',
                    next_attempt_at = ?, updated_at = ?, last_error_code = 'lease_expired'
                WHERE status = 'claimed' AND lease_until != '' AND lease_until <= ?
                """,
                (now_iso, now_iso, now_iso),
            )
            row = conn.execute(
                """
                SELECT * FROM ghost_narrative_publication_receipts
                WHERE status IN ('ready', 'retry_wait') AND next_attempt_at <= ?
                ORDER BY created_at, publication_receipt_id LIMIT 1
                """,
                (now_iso,),
            ).fetchone()
            if not row:
                return None
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_publication_receipts
                SET status = 'claimed', claimed_by = ?, claimed_at = ?, lease_until = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE publication_receipt_id = ? AND status IN ('ready', 'retry_wait')
                """,
                (worker_id, now_iso, lease_until, now_iso, row["publication_receipt_id"]),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_publication_receipt(conn.execute(
                "SELECT * FROM ghost_narrative_publication_receipts WHERE publication_receipt_id = ?",
                (row["publication_receipt_id"],),
            ).fetchone())

    def publish_claimed_narrative_candidate(
        self, publication_receipt_id, worker_id, expected_lease_until, now=None
    ):
        """Atomically materialize a medium record and acknowledge its receipt."""
        now_iso = _iso(now if now is not None else self.now())
        with self.transaction():
            conn = self._transaction_conn
            row = conn.execute(
                """
                SELECT r.*, c.validation_status, c.source_scope, c.source_event_id,
                       c.source_receipt_id, c.truth_class, c.title, c.body, c.tone,
                       c.fact_refs_json, c.cta_ref, c.cta_action, c.cta_payload_json,
                       c.asset_ref, o.validation_json AS task_validation_json,
                       o.content_kind, o.presentation_slot, o.narrative_intent,
                       o.narrative_thread_id, o.priority, o.world_state_version,
                       o.created_at AS task_created_at,
                       o.selected_source_ref, o.selected_source_version,
                       o.expected_slot_version, o.creative_epoch,
                       o.editorial_contract_json,
                       c.target_medium AS candidate_medium,
                       c.audience_scope AS candidate_audience_scope,
                       c.audience_clan AS candidate_audience_clan,
                       c.audience_owner AS candidate_audience_owner
                FROM ghost_narrative_publication_receipts r
                JOIN ghost_narrative_inbox_candidates c ON c.candidate_id = r.candidate_id
                JOIN ghost_narrative_outbox o ON o.outbox_id = r.task_id
                WHERE r.publication_receipt_id = ? LIMIT 1
                """,
                (_clean(publication_receipt_id),),
            ).fetchone()
            if not row:
                return None
            if row["status"] == "published":
                return {
                    "receipt": self._narrative_publication_receipt(row),
                    "record": self._narrative_medium_record(conn.execute(
                        "SELECT * FROM ghost_narrative_medium_records WHERE publication_receipt_id = ?",
                        (row["publication_receipt_id"],),
                    ).fetchone()),
                    "duplicate": True,
                }
            if (
                row["status"] != "claimed"
                or _clean(row["claimed_by"]) != _clean(worker_id)
                or _clean(row["lease_until"]) != _clean(expected_lease_until)
                or row["lease_until"] <= now_iso
                or row["validation_status"] != "accepted"
            ):
                return None
            if (
                _clean(row["target_medium"]) != _clean(row["candidate_medium"])
                or (_clean(row["audience_scope"]), _clean(row["audience_clan"]), _clean(row["audience_owner"]))
                != (_clean(row["candidate_audience_scope"]), _clean(row["candidate_audience_clan"]), _clean(row["candidate_audience_owner"]))
            ):
                return None
            assignment = loads_json(row["task_validation_json"], {}) or {}
            editorial_contract = loads_json(row["editorial_contract_json"], {}) or {}
            if not isinstance(editorial_contract, dict):
                editorial_contract = {}
            if not editorial_contract and isinstance(assignment.get("editorial_contract"), dict):
                editorial_contract = assignment.get("editorial_contract")
            narrative_intent = _clean(
                row["narrative_intent"] or assignment.get("narrative_intent")
            )
            if not narrative_intent and row["source_scope"] == "googleplex_editorial":
                narrative_intent = (
                    "product_benefit_promo"
                    if _clean(row["content_kind"] or assignment.get("content_kind")) == "product_promo"
                    else "capability_invitation"
                )
            lifecycle = build_publication_lifecycle({
                "source_scope": row["source_scope"],
                "narrative_thread_id": row["narrative_thread_id"],
                "task_variant": row["content_kind"],
                "priority": row["priority"],
                "world_state_version": row["world_state_version"],
                "validation": assignment,
            }, now=datetime.fromisoformat(now_iso.replace("Z", "+00:00")))
            thread_id = _clean(lifecycle.get("narrative_thread_id"))
            if thread_id and lifecycle.get("lifecycle_contract_version"):
                newer_task = conn.execute(
                    """
                    SELECT outbox_id
                    FROM ghost_narrative_outbox
                    WHERE source_scope = 'ghostnetwork' AND outbox_id != ?
                      AND target_medium = ? AND audience_scope = ?
                      AND audience_clan = ? AND audience_owner = ?
                      AND narrative_thread_id = ?
                      AND (
                        CAST(world_state_version AS INTEGER) > ?
                        OR (
                          CAST(world_state_version AS INTEGER) = ?
                          AND created_at > ?
                        )
                      )
                    ORDER BY CAST(world_state_version AS INTEGER) DESC, created_at DESC
                    LIMIT 1
                    """,
                    (
                        row["task_id"], row["target_medium"], row["audience_scope"],
                        row["audience_clan"], row["audience_owner"], thread_id,
                        int(lifecycle.get("source_state_version") or 0),
                        int(lifecycle.get("source_state_version") or 0),
                        row["task_created_at"],
                    ),
                ).fetchone()
                if newer_task:
                    return {
                        "lifecycle_superseded": True,
                        "newer_task_id": newer_task["outbox_id"],
                    }
                newer = conn.execute(
                    """
                    SELECT medium_record_id, source_state_version
                    FROM ghost_narrative_medium_records
                    WHERE target_medium = ? AND audience_scope = ?
                      AND audience_clan = ? AND audience_owner = ?
                      AND narrative_thread_id = ? AND active_state = 'active'
                      AND (
                        source_state_version > ?
                        OR (source_state_version = ? AND created_at >= ?)
                      )
                    ORDER BY source_state_version DESC, published_at DESC
                    LIMIT 1
                    """,
                    (
                        row["target_medium"], row["audience_scope"],
                        row["audience_clan"], row["audience_owner"], thread_id,
                        int(lifecycle.get("source_state_version") or 0),
                        int(lifecycle.get("source_state_version") or 0),
                        row["created_at"],
                    ),
                ).fetchone()
                if newer:
                    return {
                        "lifecycle_superseded": True,
                        "active_medium_record_id": newer["medium_record_id"],
                    }
                previous = conn.execute(
                    """
                    SELECT medium_record_id
                    FROM ghost_narrative_medium_records
                    WHERE target_medium = ? AND audience_scope = ?
                      AND audience_clan = ? AND audience_owner = ?
                      AND narrative_thread_id = ?
                      AND active_state IN ('active', 'invalidated')
                      AND source_event_id != ? AND source_state_version <= ?
                    ORDER BY source_state_version DESC, published_at DESC
                    LIMIT 1
                    """,
                    (
                        row["target_medium"], row["audience_scope"],
                        row["audience_clan"], row["audience_owner"], thread_id,
                        row["source_event_id"],
                        int(lifecycle.get("source_state_version") or 0),
                    ),
                ).fetchone()
                if previous:
                    lifecycle["supersedes_medium_record_id"] = previous["medium_record_id"]
            explicit_assignment = bool(_clean(row["presentation_slot"]))
            presentation_slot = _clean(
                row["presentation_slot"] or assignment.get("presentation_slot")
            )
            if presentation_slot:
                try:
                    expected_slot_version = int(
                        row["expected_slot_version"]
                        if explicit_assignment
                        else assignment.get("expected_slot_version") or 0
                    )
                except (TypeError, ValueError):
                    expected_slot_version = -1
                source_ref = _clean(
                    row["selected_source_ref"] or assignment.get("selected_source_ref")
                )
                source_version = _clean(
                    row["selected_source_version"] or assignment.get("selected_source_version")
                )
                content_hash = hashlib.sha256(
                    (str(row["title"]) + "\n" + str(row["body"])).encode("utf-8")
                ).hexdigest()
                creative_epoch = max(0, int(row["creative_epoch"] or assignment.get("creative_epoch") or 0))
                refresh_seconds = max(0, min(
                    int(editorial_contract.get("minimum_refresh_seconds") or 0),
                    31 * 86400,
                ))
                next_refresh_at = _iso(
                    datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
                    + timedelta(seconds=refresh_seconds)
                ) if refresh_seconds else ""
                if expected_slot_version == 0:
                    slot_cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO ghost_narrative_slot_state (
                            target_medium, slot_id, content_kind,
                            active_medium_record_id, active_source_ref,
                            active_source_version, active_content_hash,
                            creative_epoch, last_refreshed_at, next_refresh_at,
                            version, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            row["target_medium"], presentation_slot,
                            _clean(row["content_kind"] or assignment.get("content_kind")),
                            row["medium_record_id"], source_ref, source_version,
                            content_hash, creative_epoch, now_iso, next_refresh_at, now_iso,
                        ),
                    )
                else:
                    slot_cursor = conn.execute(
                        """
                        UPDATE ghost_narrative_slot_state
                        SET content_kind = ?, active_medium_record_id = ?,
                            active_source_ref = ?, active_source_version = ?,
                            active_content_hash = ?, last_refreshed_at = ?,
                            creative_epoch = ?, next_refresh_at = ?,
                            version = version + 1, updated_at = ?
                        WHERE target_medium = ? AND slot_id = ? AND version = ?
                        """,
                        (
                            _clean(row["content_kind"] or assignment.get("content_kind")),
                            row["medium_record_id"], source_ref, source_version,
                            content_hash, now_iso, creative_epoch, next_refresh_at,
                            now_iso, row["target_medium"],
                            presentation_slot, expected_slot_version,
                        ),
                    )
                if expected_slot_version < 0 or slot_cursor.rowcount != 1:
                    return {"slot_superseded": True}
            conn.execute(
                # Slot assignment is code-owned task metadata. The model never
                # sees or chooses it.
                """
                INSERT INTO ghost_narrative_medium_records (
                    medium_record_id, publication_receipt_id, candidate_id, task_id,
                    target_medium, audience_scope, audience_clan, audience_owner,
                    source_scope, source_event_id, source_receipt_id, truth_class,
                    title, body, tone, fact_refs_json, cta_ref, cta_action,
                    cta_payload_json, asset_ref, presentation_slot, content_kind,
                    narrative_intent, selected_source_ref, selected_source_version,
                    narrative_thread_id, event_family, significance, priority,
                    active_state, valid_from, valid_until,
                    supersedes_medium_record_id, invalidated_by_event_id,
                    invalidation_reason, semantic_contract_version,
                    lifecycle_contract_version, source_state_version,
                    presentation_family, publication_mode, created_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(publication_receipt_id) DO NOTHING
                """,
                (
                    row["medium_record_id"], row["publication_receipt_id"],
                    row["candidate_id"], row["task_id"], row["target_medium"],
                    row["audience_scope"], row["audience_clan"], row["audience_owner"],
                    row["source_scope"], row["source_event_id"], row["source_receipt_id"],
                    row["truth_class"], row["title"], row["body"], row["tone"],
                    row["fact_refs_json"], row["cta_ref"], row["cta_action"],
                    row["cta_payload_json"], row["asset_ref"],
                    presentation_slot,
                    _clean(row["content_kind"] or assignment.get("content_kind")),
                    narrative_intent,
                    _clean(row["selected_source_ref"] or assignment.get("selected_source_ref")),
                    _clean(row["selected_source_version"] or assignment.get("selected_source_version")),
                    lifecycle["narrative_thread_id"], lifecycle["event_family"],
                    lifecycle["significance"], lifecycle["priority"],
                    lifecycle["active_state"], lifecycle["valid_from"],
                    lifecycle["valid_until"], lifecycle["supersedes_medium_record_id"],
                    lifecycle["invalidated_by_event_id"], lifecycle["invalidation_reason"],
                    lifecycle["semantic_contract_version"], lifecycle["lifecycle_contract_version"],
                    lifecycle["source_state_version"], lifecycle["presentation_family"],
                    lifecycle["publication_mode"],
                    row["created_at"], now_iso,
                ),
            )
            if lifecycle["supersedes_medium_record_id"]:
                conn.execute(
                    """
                    UPDATE ghost_narrative_medium_records
                    SET active_state = 'invalidated', invalidated_by_event_id = ?,
                        invalidation_reason = 'canonical_thread_advanced'
                    WHERE target_medium = ? AND audience_scope = ?
                      AND audience_clan = ? AND audience_owner = ?
                      AND narrative_thread_id = ? AND active_state = 'active'
                      AND medium_record_id != ? AND source_state_version <= ?
                    """,
                    (
                        row["source_event_id"], row["target_medium"],
                        row["audience_scope"], row["audience_clan"],
                        row["audience_owner"], thread_id, row["medium_record_id"],
                        lifecycle["source_state_version"],
                    ),
                )
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_publication_receipts
                SET status = 'published', published_at = ?, updated_at = ?,
                    claimed_by = '', claimed_at = '', lease_until = '', last_error_code = ''
                WHERE publication_receipt_id = ? AND status = 'claimed'
                  AND claimed_by = ? AND lease_until = ?
                """,
                (now_iso, now_iso, row["publication_receipt_id"], _clean(worker_id), _clean(expected_lease_until)),
            )
            if cursor.rowcount != 1:
                raise RepositoryIntegrityError("Publication acknowledgement CAS failed")
            return {
                "receipt": self._narrative_publication_receipt(conn.execute(
                    "SELECT * FROM ghost_narrative_publication_receipts WHERE publication_receipt_id = ?",
                    (row["publication_receipt_id"],),
                ).fetchone()),
                "record": self._narrative_medium_record(conn.execute(
                    "SELECT * FROM ghost_narrative_medium_records WHERE publication_receipt_id = ?",
                    (row["publication_receipt_id"],),
                ).fetchone()),
                "duplicate": False,
            }

    def narrative_publication_lifecycle_health(self, now=None, limit=50):
        """Return bounded lifecycle integrity diagnostics without loading profiles."""
        now_iso = _iso(now if now is not None else self.now())
        bounded_limit = max(1, min(int(limit or 50), 100))
        with self._conn() as conn:
            states = {
                row["active_state"]: int(row["count"] or 0)
                for row in conn.execute(
                    """
                    SELECT active_state, COUNT(*) AS count
                    FROM ghost_narrative_medium_records GROUP BY active_state
                    """
                ).fetchall()
            }
            active_expired = int(conn.execute(
                """
                SELECT COUNT(*) AS count FROM ghost_narrative_medium_records
                WHERE active_state = 'active' AND valid_until != '' AND valid_until <= ?
                """,
                (now_iso,),
            ).fetchone()["count"] or 0)
            active_missing_contract = int(conn.execute(
                """
                SELECT COUNT(*) AS count FROM ghost_narrative_medium_records
                WHERE source_scope = 'ghostnetwork' AND active_state = 'active'
                  AND (narrative_thread_id = '' OR event_family = ''
                    OR significance NOT IN ('low', 'normal', 'high', 'critical')
                    OR valid_from = '' OR valid_until = ''
                    OR semantic_contract_version = ''
                    OR lifecycle_contract_version = '')
                """
            ).fetchone()["count"] or 0)
            invalidated_missing_lineage = int(conn.execute(
                """
                SELECT COUNT(*) AS count FROM ghost_narrative_medium_records
                WHERE active_state = 'invalidated'
                  AND (invalidated_by_event_id = '' OR invalidation_reason = '')
                """
            ).fetchone()["count"] or 0)
            duplicate_rows = conn.execute(
                """
                SELECT target_medium, audience_scope, audience_clan, audience_owner,
                       narrative_thread_id, COUNT(*) AS count
                FROM ghost_narrative_medium_records
                WHERE active_state = 'active' AND narrative_thread_id != ''
                  AND (valid_until = '' OR valid_until > ?)
                GROUP BY target_medium, audience_scope, audience_clan,
                         audience_owner, narrative_thread_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC, narrative_thread_id ASC LIMIT ?
                """,
                (now_iso, bounded_limit),
            ).fetchall()
        return {
            "contract_version": "ghostnetwork-publication-lifecycle-v1",
            "states": states,
            "active_expired": active_expired,
            "active_missing_contract": active_missing_contract,
            "invalidated_missing_lineage": invalidated_missing_lineage,
            "duplicate_active_heads": len(duplicate_rows),
            "duplicate_active_head_samples": [dict(row) for row in duplicate_rows],
            "checked_at": now_iso,
            "limit": bounded_limit,
        }

    def reject_claimed_narrative_publication(
        self, publication_receipt_id, worker_id, expected_lease_until,
        error_code, now=None
    ):
        now_iso = _iso(now if now is not None else self.now())
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_publication_receipts
                SET status = 'dead_letter', last_error_code = ?,
                    dead_lettered_at = ?, updated_at = ?, claimed_by = '',
                    claimed_at = '', lease_until = ''
                WHERE publication_receipt_id = ? AND status = 'claimed'
                  AND claimed_by = ? AND lease_until = ?
                """,
                (
                    _clean(error_code, "prepublish_guard_rejected"), now_iso, now_iso,
                    _clean(publication_receipt_id), _clean(worker_id),
                    _clean(expected_lease_until),
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_publication_receipt(conn.execute(
                "SELECT * FROM ghost_narrative_publication_receipts WHERE publication_receipt_id = ?",
                (_clean(publication_receipt_id),),
            ).fetchone())

    def expire_narrative_medium_records(self, now=None, limit=100):
        """Materialize bounded TTL expiry; legacy/history rows are untouched."""
        now_iso = _iso(now if now is not None else self.now())
        bounded_limit = max(1, min(int(limit or 100), 500))
        with self.transaction():
            conn = self._transaction_conn
            rows = conn.execute(
                """
                SELECT medium_record_id
                FROM ghost_narrative_medium_records
                WHERE active_state = 'active' AND valid_until != ''
                  AND valid_until <= ?
                ORDER BY valid_until ASC, medium_record_id ASC LIMIT ?
                """,
                (now_iso, bounded_limit),
            ).fetchall()
            ids = [row["medium_record_id"] for row in rows]
            if not ids:
                return 0
            placeholders = ",".join("?" for _ in ids)
            cursor = conn.execute(
                f"""
                UPDATE ghost_narrative_medium_records
                SET active_state = 'expired', invalidation_reason = 'ttl_expired'
                WHERE active_state = 'active' AND medium_record_id IN ({placeholders})
                """,
                tuple(ids),
            )
            return int(cursor.rowcount or 0)

    def list_narrative_medium_records(
        self, target_medium, audience_scope=None, audience_clan=None,
        audience_owner=None, limit=100, active_only=False
    ):
        clauses = ["target_medium = ?"]
        params = [_clean(target_medium)]
        if active_only:
            clauses.extend([
                "active_state = 'active'",
                "(valid_until = '' OR valid_until > ?)",
            ])
            params.append(_iso(self.now()))
        for column, value in (
            ("audience_scope", audience_scope),
            ("audience_clan", audience_clan),
            ("audience_owner", audience_owner),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(_clean(value))
        params.append(max(1, min(int(limit or 100), 500)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT rowid AS publication_ordinal, * FROM ghost_narrative_medium_records
                WHERE {' AND '.join(clauses)}
                ORDER BY published_at DESC, medium_record_id DESC LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._narrative_medium_record(row) for row in rows]

    def has_recent_narrative_content(
        self, target_medium, title, body, *, audience_scope="public",
        audience_clan="", audience_owner="", limit=100
    ):
        """Bounded duplicate guard over the publication read model."""
        normalize = lambda value: " ".join(str(value or "").split()).casefold()
        wanted = (normalize(title), normalize(body))
        if not all(wanted):
            return False
        records = self.list_narrative_medium_records(
            target_medium,
            audience_scope=audience_scope,
            audience_clan=audience_clan,
            audience_owner=audience_owner,
            limit=max(1, min(int(limit or 100), 100)), active_only=True,
        )
        return any(
            (normalize(record.get("title")), normalize(record.get("body"))) == wanted
            for record in records
        )

    def get_narrative_slot_state(self, target_medium, slot_id):
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM ghost_narrative_slot_state
                WHERE target_medium = ? AND slot_id = ? LIMIT 1
                """,
                (_clean(target_medium), _clean(slot_id)),
            ).fetchone()
        if not row:
            return None
        return {
            "target_medium": row["target_medium"],
            "slot_id": row["slot_id"],
            "content_kind": row["content_kind"],
            "active_medium_record_id": row["active_medium_record_id"],
            "active_source_ref": row["active_source_ref"],
            "active_source_version": row["active_source_version"],
            "active_content_hash": row["active_content_hash"],
            "creative_epoch": int(row["creative_epoch"] or 0),
            "last_refreshed_at": row["last_refreshed_at"],
            "next_refresh_at": row["next_refresh_at"],
            "version": int(row["version"] or 0),
            "updated_at": row["updated_at"],
        }

    def has_open_narrative_slot_assignment(self, target_medium, slot_id):
        """True while a slot assignment can still produce a publication."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM ghost_narrative_outbox o
                WHERE o.target_medium = ?
                  AND o.presentation_slot = ?
                  AND (
                    o.status IN ('ready', 'retry_wait', 'claimed', 'processing')
                    OR (
                        o.status = 'completed'
                        AND EXISTS (
                            SELECT 1
                            FROM ghost_narrative_inbox_candidates c
                            WHERE c.task_id = o.outbox_id
                              AND c.validation_status = 'accepted'
                        )
                        AND NOT EXISTS (
                            SELECT 1
                            FROM ghost_narrative_publication_receipts r
                            WHERE r.task_id = o.outbox_id
                              AND r.status IN ('published', 'dead_letter')
                        )
                    )
                  )
                LIMIT 1
                """,
                (_clean(target_medium), _clean(slot_id)),
            ).fetchone()
        return bool(row)

    def list_active_narrative_slot_records_for_viewer(
        self, target_medium, owner="", clan="", limit=20
    ):
        owner = _clean(owner)
        clan = _clean(clan)
        audience = ["m.audience_scope = 'public'"]
        params = [_clean(target_medium)]
        if owner:
            audience.append("(m.audience_scope = 'owner' AND m.audience_owner = ?)")
            params.append(owner)
        if clan:
            audience.append("(m.audience_scope = 'clan' AND m.audience_clan = ?)")
            params.append(clan)
        params.append(max(1, min(int(limit or 20), 50)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT m.rowid AS publication_ordinal, m.*
                FROM ghost_narrative_slot_state s
                JOIN ghost_narrative_medium_records m
                  ON m.medium_record_id = s.active_medium_record_id
                WHERE s.target_medium = ? AND m.active_state = 'active'
                  AND (m.valid_until = '' OR m.valid_until > ?)
                  AND ({' OR '.join(audience)})
                ORDER BY s.slot_id ASC LIMIT ?
                """,
                tuple([params[0], _iso(self.now()), *params[1:]]),
            ).fetchall()
        return [self._narrative_medium_record(row) for row in rows]

    def list_narrative_medium_records_for_viewer(
        self, target_medium, owner="", clan="", limit=100
    ):
        owner = _clean(owner)
        clan = _clean(clan)
        audience = ["audience_scope = 'public'"]
        params = [_clean(target_medium)]
        if owner:
            audience.append("(audience_scope = 'owner' AND audience_owner = ?)")
            params.append(owner)
        if clan:
            audience.append("(audience_scope = 'clan' AND audience_clan = ?)")
            params.append(clan)
        params.insert(1, _iso(self.now()))
        params.append(max(1, min(int(limit or 100), 500)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT rowid AS publication_ordinal, * FROM ghost_narrative_medium_records
                WHERE target_medium = ? AND active_state = 'active'
                  AND (valid_until = '' OR valid_until > ?)
                  AND ({' OR '.join(audience)})
                ORDER BY priority DESC, published_at DESC, medium_record_id DESC LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._narrative_medium_record(row) for row in rows]

    def count_narrative_medium_records_for_viewer_after(
        self, target_medium, *, owner="", clan="", after_ordinal=0,
        audience_scope="",
    ):
        """Count unread bounded projections using SQLite's monotonic local row identity."""
        owner = _clean(owner)
        clan = _clean(clan)
        audience_scope = _clean(audience_scope)
        params = [
            _clean(target_medium), max(0, int(after_ordinal or 0)),
            _iso(self.now()),
        ]
        if audience_scope == "owner":
            audience = ["(audience_scope = 'owner' AND audience_owner = ?)"]
            params.append(owner)
        elif audience_scope == "clan":
            audience = ["(audience_scope = 'clan' AND audience_clan = ?)"]
            params.append(clan)
        elif audience_scope == "public":
            audience = ["audience_scope = 'public'"]
        else:
            audience = ["audience_scope = 'public'"]
        if not audience_scope and owner:
            audience.append("(audience_scope = 'owner' AND audience_owner = ?)")
            params.append(owner)
        if not audience_scope and clan:
            audience.append("(audience_scope = 'clan' AND audience_clan = ?)")
            params.append(clan)
        with self._conn() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ghost_narrative_medium_records
                WHERE target_medium = ? AND rowid > ?
                  AND active_state = 'active'
                  AND (valid_until = '' OR valid_until > ?)
                  AND ({' OR '.join(audience)})
                """,
                tuple(params),
            ).fetchone()
        return int(row["count"] or 0) if row else 0

    def get_narrative_publication_for_source_receipt(self, source_receipt_id, owner=""):
        clauses = [
            "m.source_receipt_id = ?", "m.active_state = 'active'",
            "(m.valid_until = '' OR m.valid_until > ?)",
        ]
        params = [_clean(source_receipt_id), _iso(self.now())]
        if owner:
            clauses.extend(["m.audience_scope = 'owner'", "m.audience_owner = ?"])
            params.append(_clean(owner))
        with self._conn() as conn:
            row = conn.execute(
                f"""
                SELECT m.rowid AS publication_ordinal, m.* FROM ghost_narrative_medium_records m
                WHERE {' AND '.join(clauses)}
                ORDER BY m.published_at DESC LIMIT 1
                """,
                tuple(params),
            ).fetchone()
            return self._narrative_medium_record(row)

    def list_narrative_attempts(self, task_id=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        with self._conn() as conn:
            if task_id:
                rows = conn.execute(
                    """
                    SELECT * FROM ghost_narrative_inbox_attempts
                    WHERE task_id = ? ORDER BY attempt_number ASC LIMIT ?
                    """,
                    (_clean(task_id), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM ghost_narrative_inbox_attempts
                    ORDER BY created_at ASC, attempt_id ASC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self._narrative_attempt(row) for row in rows]

    def list_narrative_publication_lineage(self, task_ids, limit=500):
        """Return bounded receipt/medium lineage for an explicit task set."""
        task_ids = tuple(dict.fromkeys(
            _clean(task_id) for task_id in (task_ids or ()) if _clean(task_id)
        ))
        if not task_ids:
            return []
        task_ids = task_ids[:500]
        limit = max(1, min(int(limit or 500), 500))
        placeholders = ",".join("?" for _ in task_ids)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    r.publication_receipt_id, r.candidate_id,
                    r.task_id, r.target_medium, r.audience_scope,
                    r.audience_clan, r.audience_owner,
                    r.status AS receipt_status, r.last_error_code,
                    r.created_at AS receipt_created_at,
                    r.published_at AS receipt_published_at,
                    o.presentation_slot,
                    m.medium_record_id, m.source_event_id,
                    m.target_medium AS record_medium,
                    m.audience_scope AS record_audience_scope,
                    m.audience_clan AS record_audience_clan,
                    m.audience_owner AS record_audience_owner,
                    m.fact_refs_json AS record_fact_refs_json,
                    m.narrative_thread_id, m.event_family,
                    m.active_state, m.lifecycle_contract_version,
                    m.semantic_contract_version, m.source_state_version,
                    m.publication_mode, m.published_at AS record_published_at,
                    s.active_medium_record_id AS slot_active_medium_record_id,
                    sm.source_event_id AS slot_active_source_event_id,
                    sm.active_state AS slot_active_state,
                    sm.source_state_version AS slot_active_source_state_version
                FROM ghost_narrative_publication_receipts r
                JOIN ghost_narrative_outbox o
                  ON o.outbox_id = r.task_id
                LEFT JOIN ghost_narrative_medium_records m
                  ON m.publication_receipt_id = r.publication_receipt_id
                LEFT JOIN ghost_narrative_slot_state s
                  ON s.target_medium = r.target_medium
                 AND s.slot_id = o.presentation_slot
                LEFT JOIN ghost_narrative_medium_records sm
                  ON sm.medium_record_id = s.active_medium_record_id
                WHERE r.task_id IN ({placeholders})
                ORDER BY r.created_at, r.publication_receipt_id
                LIMIT ?
                """,
                (*task_ids, limit),
            ).fetchall()
        return [{
            "publication_receipt_id": row["publication_receipt_id"],
            "candidate_id": row["candidate_id"],
            "task_id": row["task_id"],
            "target_medium": row["target_medium"],
            "audience_scope": row["audience_scope"],
            "audience_clan": row["audience_clan"],
            "audience_owner": row["audience_owner"],
            "receipt_status": row["receipt_status"],
            "last_error_code": row["last_error_code"],
            "receipt_created_at": row["receipt_created_at"],
            "receipt_published_at": row["receipt_published_at"],
            "presentation_slot": row["presentation_slot"] or "",
            "medium_record_id": row["medium_record_id"] or "",
            "source_event_id": row["source_event_id"] or "",
            "record_medium": row["record_medium"] or "",
            "record_audience_scope": row["record_audience_scope"] or "",
            "record_audience_clan": row["record_audience_clan"] or "",
            "record_audience_owner": row["record_audience_owner"] or "",
            "record_fact_refs": loads_json(row["record_fact_refs_json"], []) or [],
            "narrative_thread_id": row["narrative_thread_id"] or "",
            "event_family": row["event_family"] or "",
            "active_state": row["active_state"] or "",
            "lifecycle_contract_version": row["lifecycle_contract_version"] or "",
            "semantic_contract_version": row["semantic_contract_version"] or "",
            "source_state_version": int(row["source_state_version"] or 0),
            "publication_mode": row["publication_mode"] or "",
            "record_published_at": row["record_published_at"] or "",
            "slot_active_medium_record_id": row["slot_active_medium_record_id"] or "",
            "slot_active_source_event_id": row["slot_active_source_event_id"] or "",
            "slot_active_state": row["slot_active_state"] or "",
            "slot_active_source_state_version": int(
                row["slot_active_source_state_version"] or 0
            ),
        } for row in rows]

    def requeue_narrative_task(self, outbox_id, now=None, validation=None):
        now_iso = _iso(now if now is not None else self.now())
        validation = validation if isinstance(validation, dict) else None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                (_clean(outbox_id),),
            ).fetchone()
            current = self._narrative_outbox(row)
            if not current or current["status"] != "retry_wait":
                return None
            next_validation = validation if validation is not None else current.get("validation") or {}
            cursor = conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = 'ready', next_attempt_at = ?, updated_at = ?,
                    validation_json = ?
                WHERE outbox_id = ? AND status = 'retry_wait'
                """,
                (now_iso, now_iso, dumps_json(next_validation), _clean(outbox_id)),
            )
            if cursor.rowcount != 1:
                return None
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def update_narrative_outbox_status(self, outbox_id, status, processed_at=None, validation=None):
        """Bounded Sprint 129 compatibility transition; worker paths require lease CAS."""
        requested = _clean(status)
        next_status = NARRATIVE_TASK_LEGACY_STATUS_MAP.get(requested, requested)
        if next_status not in {"ready", "retry_wait", "completed", "dead_letter"}:
            raise ValueError("Narrative task status requires canonical lifecycle method")
        validation = validation if isinstance(validation, dict) else None
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                (_clean(outbox_id),),
            ).fetchone()
            if not existing:
                return None
            current = self._narrative_outbox(existing)
            if current["status"] in NARRATIVE_TASK_ACTIVE_STATUSES:
                raise ValueError("Active narrative task status requires lease owner")
            allowed = {
                "ready": {"ready", "retry_wait"},
                "retry_wait": {"ready", "retry_wait"},
                "completed": {"completed"},
                "dead_letter": {"dead_letter"},
            }
            if next_status not in allowed.get(current["status"], set()):
                raise ValueError(
                    f"Invalid narrative task transition: {current['status']} -> {next_status}"
                )
            next_validation = validation if validation is not None else current.get("validation") or {}
            now = self.now()
            terminal_at = _clean(processed_at or now) if next_status in NARRATIVE_TASK_TERMINAL_STATUSES else ""
            conn.execute(
                """
                UPDATE ghost_narrative_outbox
                SET status = ?, processed_at = ?, validation_json = ?, updated_at = ?,
                    next_attempt_at = CASE
                        WHEN ? = 'ready' THEN ?
                        WHEN ? = 'retry_wait' THEN ?
                        ELSE ''
                    END,
                    completed_at = CASE WHEN ? = 'completed' THEN ? ELSE completed_at END,
                    dead_lettered_at = CASE WHEN ? = 'dead_letter' THEN ? ELSE dead_lettered_at END
                WHERE outbox_id = ?
                """,
                (
                    next_status,
                    terminal_at,
                    dumps_json(next_validation),
                    now,
                    next_status,
                    now,
                    next_status,
                    now,
                    next_status,
                    terminal_at,
                    next_status,
                    terminal_at,
                    _clean(outbox_id),
                ),
            )
            return self._narrative_outbox(
                conn.execute(
                    "SELECT * FROM ghost_narrative_outbox WHERE outbox_id = ? LIMIT 1",
                    (_clean(outbox_id),),
                ).fetchone()
            )

    def get_contribution_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_contributions WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            return self._contribution(row)

    def insert_contribution(self, contribution):
        contribution = contribution if isinstance(contribution, dict) else {}
        dedupe_key = _clean(contribution.get("dedupe_key"))
        if dedupe_key:
            existing = self.get_contribution_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        cycle_id = _clean(contribution.get("cycle_id"))
        contribution_type = _clean(contribution.get("contribution_type"))
        player_id = _clean(contribution.get("player_id"))
        now = self.now()
        contribution_id = _clean(
            contribution.get("contribution_id")
            or _hash_id("contribution", cycle_id, contribution_type, player_id, contribution.get("part_id"), dedupe_key, now)
        )
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_contributions (
                        contribution_id, cycle_id, signal_id, player_id, clan_code,
                        profession_code, contribution_type, part_id, territory_id,
                        operation_id, score, weight, source_event_id, dedupe_key,
                        metadata_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contribution_id,
                        cycle_id,
                        _clean(contribution.get("signal_id")),
                        player_id,
                        _clean(contribution.get("clan_code")),
                        _clean(contribution.get("profession_code")),
                        contribution_type,
                        _clean(contribution.get("part_id")),
                        _clean(contribution.get("territory_id")),
                        _clean(contribution.get("operation_id")),
                        int(contribution.get("score") or 0),
                        float(contribution.get("weight") or 1.0),
                        _clean(contribution.get("source_event_id")),
                        dedupe_key,
                        dumps_json(contribution.get("metadata") if isinstance(contribution.get("metadata"), dict) else {}),
                        _clean(contribution.get("created_at") or now),
                    ),
                )
            except IntegrityError:
                if dedupe_key:
                    existing = self.get_contribution_by_dedupe_key(dedupe_key)
                    if existing:
                        existing["idempotent"] = True
                        return existing
                raise
            return self._contribution(
                conn.execute(
                    "SELECT * FROM ghost_contributions WHERE contribution_id = ?",
                    (contribution_id,),
                ).fetchone()
            )

    def list_player_contributions(self, player_id, cycle_id=None, limit=500):
        limit = max(1, min(int(limit or 500), 2000))
        with self._conn() as conn:
            if cycle_id:
                rows = conn.execute(
                    """
                    SELECT * FROM ghost_contributions
                    WHERE player_id = ? AND cycle_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (_clean(player_id), _clean(cycle_id), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM ghost_contributions
                    WHERE player_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (_clean(player_id), limit),
                ).fetchall()
            return [self._contribution(row) for row in rows]

    def list_cycle_contributions(self, cycle_id, limit=1000):
        limit = max(1, min(int(limit or 1000), 5000))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_contributions
                WHERE cycle_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (_clean(cycle_id), limit),
            ).fetchall()
            return [self._contribution(row) for row in rows]

    def list_contributions(self, signal_id=None, cycle_id=None, player_id=None, clan_code=None, limit=1000):
        limit = max(1, min(int(limit or 1000), 5000))
        clauses = []
        params = []
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(_clean(signal_id))
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if player_id:
            clauses.append("player_id = ?")
            params.append(_clean(player_id))
        if clan_code:
            clauses.append("clan_code = ?")
            params.append(_clean(clan_code))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_contributions
                {where}
                ORDER BY created_at DESC, contribution_id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._contribution(row) for row in rows]

    def aggregate_player_contribution(self, player_id, cycle_id=None):
        where = ["player_id = ?"]
        params = [_clean(player_id)]
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT contribution_type, COUNT(*) AS count, SUM(score) AS score, SUM(score * weight) AS weighted_score
                FROM ghost_contributions
                WHERE {' AND '.join(where)}
                GROUP BY contribution_type
                ORDER BY contribution_type ASC
                """,
                params,
            ).fetchall()
            totals = {
                "player_id": _clean(player_id),
                "cycle_id": _clean(cycle_id),
                "count": 0,
                "score": 0,
                "weighted_score": 0.0,
                "by_type": {},
            }
            for row in rows:
                item = {
                    "count": int(row["count"] or 0),
                    "score": int(row["score"] or 0),
                    "weighted_score": float(row["weighted_score"] or 0.0),
                }
                totals["by_type"][row["contribution_type"]] = item
                totals["count"] += item["count"]
                totals["score"] += item["score"]
                totals["weighted_score"] += item["weighted_score"]
            return totals

    def aggregate_clan_contribution(self, clan_code, cycle_id=None):
        where = ["clan_code = ?"]
        params = [_clean(clan_code)]
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT contribution_type, COUNT(*) AS count, SUM(score) AS score, SUM(score * weight) AS weighted_score
                FROM ghost_contributions
                WHERE {' AND '.join(where)}
                GROUP BY contribution_type
                ORDER BY contribution_type ASC
                """,
                params,
            ).fetchall()
            totals = {
                "clan_code": _clean(clan_code),
                "cycle_id": _clean(cycle_id),
                "count": 0,
                "score": 0,
                "weighted_score": 0.0,
                "by_type": {},
            }
            for row in rows:
                item = {
                    "count": int(row["count"] or 0),
                    "score": int(row["score"] or 0),
                    "weighted_score": float(row["weighted_score"] or 0.0),
                }
                totals["by_type"][row["contribution_type"]] = item
                totals["count"] += item["count"]
                totals["score"] += item["score"]
                totals["weighted_score"] += item["weighted_score"]
            return totals

    def get_reward_by_key(self, reward_key):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_reward_ledger WHERE reward_key = ? LIMIT 1",
                (_clean(reward_key),),
            ).fetchone()
            return self._reward(row)

    def get_reward(self, reward_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_reward_ledger WHERE reward_id = ? LIMIT 1",
                (_clean(reward_id),),
            ).fetchone()
            return self._reward(row)

    def insert_reward(self, reward):
        reward = reward if isinstance(reward, dict) else {}
        reward_key = _clean(reward.get("reward_key"))
        existing = self.get_reward_by_key(reward_key)
        if existing:
            existing["idempotent"] = True
            return existing
        cycle_id = _clean(reward.get("cycle_id"))
        reward_type = _clean(reward.get("reward_type"))
        player_id = _clean(reward.get("player_id"))
        final_rsp = int(reward.get("final_rsp") or reward.get("rsp_amount") or 0)
        now = self.now()
        reward_id = _clean(reward.get("reward_id") or _hash_id("reward", reward_key, cycle_id, player_id, reward_type))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_reward_ledger (
                        reward_id, reward_key, cycle_id, signal_id, player_id, clan_code,
                        reward_type, source_event_id, base_rsp, multiplier, final_rsp,
                        rsp_amount, level_progress, status, failure_reason, metadata_json,
                        created_at, applied_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reward_id,
                        reward_key,
                        cycle_id,
                        _clean(reward.get("signal_id")),
                        player_id,
                        _clean(reward.get("clan_code")),
                        reward_type,
                        _clean(reward.get("source_event_id")),
                        int(reward.get("base_rsp") or final_rsp or 0),
                        float(reward.get("multiplier") or 1.0),
                        final_rsp,
                        final_rsp,
                        int(reward.get("level_progress") or 0),
                        _clean(reward.get("status"), "pending"),
                        _clean(reward.get("failure_reason")),
                        dumps_json(reward.get("metadata") if isinstance(reward.get("metadata"), dict) else {}),
                        _clean(reward.get("created_at") or now),
                        _clean(reward.get("applied_at")),
                    ),
                )
            except IntegrityError:
                existing = self.get_reward_by_key(reward_key)
                if existing:
                    existing["idempotent"] = True
                    return existing
                raise
            return self.get_reward(reward_id)

    def list_pending_rewards(self, player_id=None, cycle_id=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        where = ["status = 'pending'"]
        params = []
        if player_id:
            where.append("player_id = ?")
            params.append(_clean(player_id))
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_reward_ledger
                WHERE {' AND '.join(where)}
                ORDER BY created_at ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._reward(row) for row in rows]

    def claim_pending_reward_projection(self, worker_id, lease_seconds=60, now=None):
        worker_id = _clean(worker_id)
        if not worker_id:
            raise ValueError("reward projection worker_id is required")
        now_iso = _iso(now)
        lease_until = _iso(_utc_datetime(now_iso) + timedelta(seconds=max(10, int(lease_seconds or 60))))
        with self.transaction():
            conn = self._transaction_conn
            row = conn.execute(
                """
                SELECT * FROM ghost_reward_ledger
                WHERE status = 'pending'
                  AND (projection_next_attempt_at = '' OR projection_next_attempt_at <= ?)
                  AND (projection_claimed_by = '' OR projection_lease_until = '' OR projection_lease_until <= ?)
                ORDER BY created_at ASC, reward_id ASC
                LIMIT 1
                """,
                (now_iso, now_iso),
            ).fetchone()
            if not row:
                return None
            updated = conn.execute(
                """
                UPDATE ghost_reward_ledger
                SET projection_claimed_by = ?, projection_claimed_at = ?,
                    projection_lease_until = ?, projection_attempt_count = projection_attempt_count + 1,
                    failure_reason = ''
                WHERE reward_id = ? AND status = 'pending'
                  AND (projection_claimed_by = '' OR projection_lease_until = '' OR projection_lease_until <= ?)
                """,
                (worker_id, now_iso, lease_until, row["reward_id"], now_iso),
            )
            if updated.rowcount != 1:
                return None
            return self._reward(conn.execute(
                "SELECT * FROM ghost_reward_ledger WHERE reward_id = ?",
                (row["reward_id"],),
            ).fetchone())

    def retry_reward_projection(self, reward_id, worker_id, expected_lease_until, error="", now=None,
                                backoff_seconds=None):
        now_iso = _iso(now)
        with self.transaction():
            conn = self._transaction_conn
            row = conn.execute(
                "SELECT projection_attempt_count FROM ghost_reward_ledger WHERE reward_id = ?",
                (_clean(reward_id),),
            ).fetchone()
            attempts = int(row["projection_attempt_count"] or 1) if row else 1
            delay = (
                min(300, 2 ** min(attempts, 8))
                if backoff_seconds is None else max(0, int(backoff_seconds))
            )
            next_attempt = _iso(_utc_datetime(now_iso) + timedelta(seconds=delay))
            updated = conn.execute(
                """
                UPDATE ghost_reward_ledger
                SET projection_claimed_by = '', projection_claimed_at = '',
                    projection_lease_until = '', projection_next_attempt_at = ?,
                    projection_last_error_at = ?, failure_reason = ?
                WHERE reward_id = ? AND status = 'pending'
                  AND projection_claimed_by = ? AND projection_lease_until = ?
                """,
                (next_attempt, now_iso, _clean(error)[:500], _clean(reward_id),
                 _clean(worker_id), _clean(expected_lease_until)),
            )
            return updated.rowcount == 1

    def reward_projection_diagnostics(self, now=None):
        now_iso = _iso(now)
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status = 'pending' AND projection_claimed_by != ''
                        AND projection_lease_until > ? THEN 1 ELSE 0 END) AS processing,
                    SUM(CASE WHEN status = 'pending' AND projection_claimed_by != ''
                        AND projection_lease_until != '' AND projection_lease_until <= ? THEN 1 ELSE 0 END) AS expired_claims,
                    SUM(CASE WHEN status = 'pending'
                        AND (projection_next_attempt_at = '' OR projection_next_attempt_at <= ?)
                        AND (projection_claimed_by = '' OR projection_lease_until = '' OR projection_lease_until <= ?)
                        THEN 1 ELSE 0 END) AS ready_now,
                    SUM(CASE WHEN status = 'pending' AND projection_next_attempt_at > ?
                        THEN 1 ELSE 0 END) AS retry_wait,
                    SUM(CASE WHEN status = 'pending' AND failure_reason != ''
                        THEN 1 ELSE 0 END) AS pending_with_error,
                    MIN(CASE WHEN status = 'pending' THEN created_at END) AS oldest_pending,
                    MIN(CASE WHEN status = 'pending'
                        AND (projection_next_attempt_at = '' OR projection_next_attempt_at <= ?)
                        AND (projection_claimed_by = '' OR projection_lease_until = '' OR projection_lease_until <= ?)
                        THEN created_at END) AS oldest_ready,
                    MAX(projection_attempt_count) AS maximum_attempts
                FROM ghost_reward_ledger
                """,
                (now_iso, now_iso, now_iso, now_iso, now_iso, now_iso, now_iso),
            ).fetchone()
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM ghost_reward_ledger GROUP BY status"
            ).fetchall()
        return {
            "pending": int(row["pending"] or 0),
            "processing": int(row["processing"] or 0),
            "expired_claims": int(row["expired_claims"] or 0),
            "ready_now": int(row["ready_now"] or 0),
            "retry_wait": int(row["retry_wait"] or 0),
            "pending_with_error": int(row["pending_with_error"] or 0),
            "oldest_pending": row["oldest_pending"] or "",
            "oldest_ready": row["oldest_ready"] or "",
            "maximum_attempts": int(row["maximum_attempts"] or 0),
            "statuses": {
                item["status"]: int(item["count"] or 0) for item in status_rows
            },
        }

    def list_rewards(self, signal_id=None, cycle_id=None, player_id=None, clan_code=None, status=None, limit=1000):
        limit = max(1, min(int(limit or 1000), 5000))
        clauses = []
        params = []
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(_clean(signal_id))
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if player_id:
            clauses.append("player_id = ?")
            params.append(_clean(player_id))
        if clan_code:
            clauses.append("clan_code = ?")
            params.append(_clean(clan_code))
        if status:
            clauses.append("status = ?")
            params.append(_clean(status))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_reward_ledger
                {where}
                ORDER BY created_at DESC, reward_id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._reward(row) for row in rows]

    def update_reward_status(self, reward_id, status, *, failure_reason="", applied_at=None):
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE ghost_reward_ledger
                SET status = ?, failure_reason = ?, applied_at = ?,
                    projection_claimed_by = CASE WHEN ? = 'applied' THEN '' ELSE projection_claimed_by END,
                    projection_claimed_at = CASE WHEN ? = 'applied' THEN '' ELSE projection_claimed_at END,
                    projection_lease_until = CASE WHEN ? = 'applied' THEN '' ELSE projection_lease_until END,
                    projection_next_attempt_at = CASE WHEN ? = 'applied' THEN '' ELSE projection_next_attempt_at END
                WHERE reward_id = ?
                """,
                (
                    _clean(status),
                    _clean(failure_reason),
                    _clean(applied_at if applied_at is not None else (self.now() if status == "applied" else "")),
                    _clean(status), _clean(status), _clean(status), _clean(status),
                    _clean(reward_id),
                ),
            )
            row = conn.execute(
                "SELECT * FROM ghost_reward_ledger WHERE reward_id = ? LIMIT 1",
                (_clean(reward_id),),
            ).fetchone()
            return self._reward(row)

    def get_player_reward_summary(self, player_id, cycle_id=None):
        where = ["player_id = ?"]
        params = [_clean(player_id)]
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT status, reward_type, COUNT(*) AS count, SUM(final_rsp) AS rsp
                FROM ghost_reward_ledger
                WHERE {' AND '.join(where)}
                GROUP BY status, reward_type
                """,
                params,
            ).fetchall()
            summary = {
                "player_id": _clean(player_id),
                "cycle_id": _clean(cycle_id),
                "total_rewards": 0,
                "pending_rsp": 0,
                "applied_rsp": 0,
                "by_status": {},
                "by_type": {},
            }
            for row in rows:
                status = row["status"]
                reward_type = row["reward_type"]
                count = int(row["count"] or 0)
                rsp = int(row["rsp"] or 0)
                summary["total_rewards"] += count
                summary["by_status"].setdefault(status, {"count": 0, "rsp": 0})
                summary["by_status"][status]["count"] += count
                summary["by_status"][status]["rsp"] += rsp
                summary["by_type"].setdefault(reward_type, {"count": 0, "rsp": 0})
                summary["by_type"][reward_type]["count"] += count
                summary["by_type"][reward_type]["rsp"] += rsp
                if status == "pending":
                    summary["pending_rsp"] += rsp
                if status == "applied":
                    summary["applied_rsp"] += rsp
            return summary

    def get_clan_reputation(self, clan_code):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_clan_reputation WHERE clan_code = ? LIMIT 1",
                (_clean(clan_code),),
            ).fetchone()
            return self._clan_reputation(row)

    def increment_clan_reputation(self, clan_code, increments=None, metadata=None):
        clan_code = _clean(clan_code)
        if not clan_code:
            return None
        increments = increments if isinstance(increments, dict) else {}
        allowed = {
            "total_reputation",
            "signals_participated",
            "parts_discovered",
            "parts_first_contained",
            "parts_activated",
            "parts_recovered",
            "territories_defended",
            "active_node_seconds",
            "transmission_nodes_held",
            "networks_closed",
        }
        clean_increments = {key: int(value or 0) for key, value in increments.items() if key in allowed}
        now = self.now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO ghost_clan_reputation (clan_code, updated_at)
                VALUES (?, ?)
                """,
                (clan_code, now),
            )
            if clean_increments:
                assignments = ", ".join(f"{key} = {key} + ?" for key in clean_increments)
                values = list(clean_increments.values())
                conn.execute(
                    f"""
                    UPDATE ghost_clan_reputation
                    SET {assignments}, metadata_json = ?, updated_at = ?
                    WHERE clan_code = ?
                    """,
                    [
                        *values,
                        dumps_json(metadata if isinstance(metadata, dict) else {}),
                        now,
                        clan_code,
                    ],
                )
            row = conn.execute(
                "SELECT * FROM ghost_clan_reputation WHERE clan_code = ? LIMIT 1",
                (clan_code,),
            ).fetchone()
            return self._clan_reputation(row)

    def list_clan_reputation(self, limit=100):
        limit = max(1, min(int(limit or 100), 500))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ghost_clan_reputation
                ORDER BY total_reputation DESC, clan_code ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._clan_reputation(row) for row in rows]

    def get_achievement_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            return self._achievement(
                conn.execute(
                    "SELECT * FROM ghost_achievements WHERE dedupe_key = ? LIMIT 1",
                    (dedupe_key,),
                ).fetchone()
            )

    def insert_achievement(self, achievement):
        achievement = achievement if isinstance(achievement, dict) else {}
        player_id = _clean(achievement.get("player_id"))
        achievement_code = _clean(achievement.get("achievement_code"))
        source_id = _clean(achievement.get("source_id"))
        dedupe_key = _clean(
            achievement.get("dedupe_key")
            or f"achievement:{player_id}:{achievement_code}:{source_id}"
        )
        if dedupe_key:
            existing = self.get_achievement_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        now = self.now()
        achievement_id = _clean(
            achievement.get("achievement_id")
            or _hash_id("achievement", player_id, achievement_code, source_id, dedupe_key)
        )
        with self._conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_achievements (
                        achievement_id, player_id, clan_code, achievement_code,
                        cycle_id, signal_id, source_id, metadata_json,
                        awarded_at, dedupe_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        achievement_id,
                        player_id,
                        _clean(achievement.get("clan_code")),
                        achievement_code,
                        _clean(achievement.get("cycle_id")),
                        _clean(achievement.get("signal_id")),
                        source_id,
                        dumps_json(achievement.get("metadata") if isinstance(achievement.get("metadata"), dict) else {}),
                        _clean(achievement.get("awarded_at") or now),
                        dedupe_key,
                    ),
                )
            except IntegrityError:
                existing = self.get_achievement_by_dedupe_key(dedupe_key)
                if existing:
                    existing["idempotent"] = True
                    return existing
                raise
            return self._achievement(
                conn.execute(
                    "SELECT * FROM ghost_achievements WHERE achievement_id = ? LIMIT 1",
                    (achievement_id,),
                ).fetchone()
            )

    def list_achievements(self, player_id=None, signal_id=None, cycle_id=None, limit=500):
        limit = max(1, min(int(limit or 500), 2000))
        clauses = []
        params = []
        if player_id:
            clauses.append("player_id = ?")
            params.append(_clean(player_id))
        if signal_id:
            clauses.append("signal_id = ?")
            params.append(_clean(signal_id))
        if cycle_id:
            clauses.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_achievements
                {where}
                ORDER BY awarded_at DESC, achievement_code ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [self._achievement(row) for row in rows]

    def get_strategic_conflict(self, conflict_id):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_strategic_conflicts WHERE conflict_id = ? LIMIT 1",
                (_clean(conflict_id),),
            ).fetchone()
            return self._strategic_conflict(row)

    def get_strategic_conflict_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_strategic_conflicts WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            return self._strategic_conflict(row)

    def list_strategic_conflicts(self, cycle_id=None, part_id=None, statuses=None, limit=500):
        limit = max(1, min(int(limit or 500), 5000))
        where = []
        params = []
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if part_id:
            where.append("part_id = ?")
            params.append(_clean(part_id))
        statuses = [str(status).strip() for status in (statuses or []) if str(status or "").strip()]
        if statuses:
            where.append(f"status IN ({', '.join('?' for _ in statuses)})")
            params.extend(statuses)
        sql_where = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_strategic_conflicts
                {sql_where}
                ORDER BY started_at DESC, conflict_id ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._strategic_conflict(row) for row in rows]

    def insert_strategic_conflict(self, conflict):
        conflict = conflict if isinstance(conflict, dict) else {}
        dedupe_key = _clean(conflict.get("dedupe_key"))
        if dedupe_key:
            existing = self.get_strategic_conflict_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        cycle_id = _clean(conflict.get("cycle_id"))
        part_id = _clean(conflict.get("part_id"))
        now = _clean(conflict.get("started_at") or self.now())
        conflict_id = _clean(conflict.get("conflict_id") or _hash_id("ghost_conflict", cycle_id, part_id, now, dedupe_key))
        snapshot = conflict.get("snapshot") if isinstance(conflict.get("snapshot"), dict) else {}
        participants = conflict.get("initial_participants") if isinstance(conflict.get("initial_participants"), list) else []
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_strategic_conflicts (
                        conflict_id, cycle_id, part_id, territory_id, initial_owner_id,
                        initial_clan, initial_status, initial_integrity, initial_security_score,
                        active_offensive_operations, initial_participants_json, snapshot_json,
                        status, outcome, max_attack_progress, offensive_score, defensive_score,
                        offensive_actors_json, defensive_actors_json, assessment_json, dedupe_key,
                        started_at, resolved_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conflict_id,
                        cycle_id,
                        part_id,
                        _clean(conflict.get("territory_id")),
                        _clean(conflict.get("initial_owner_id")),
                        _clean(conflict.get("initial_clan")),
                        _clean(conflict.get("initial_status")),
                        int(conflict.get("initial_integrity") or 100),
                        int(conflict.get("initial_security_score") or 0),
                        int(conflict.get("active_offensive_operations") or 0),
                        dumps_json(participants),
                        dumps_json(snapshot),
                        _clean(conflict.get("status"), "active"),
                        _clean(conflict.get("outcome")),
                        int(conflict.get("max_attack_progress") or 0),
                        int(conflict.get("offensive_score") or 0),
                        int(conflict.get("defensive_score") or 0),
                        dumps_json(conflict.get("offensive_actors") if isinstance(conflict.get("offensive_actors"), list) else []),
                        dumps_json(conflict.get("defensive_actors") if isinstance(conflict.get("defensive_actors"), list) else []),
                        dumps_json(conflict.get("assessment") if isinstance(conflict.get("assessment"), dict) else {}),
                        dedupe_key,
                        now,
                        _clean(conflict.get("resolved_at")),
                        _clean(conflict.get("updated_at") or now),
                    ),
                )
            except IntegrityError:
                if dedupe_key:
                    existing = self.get_strategic_conflict_by_dedupe_key(dedupe_key)
                    if existing:
                        existing["idempotent"] = True
                        return existing
                raise
            return self.get_strategic_conflict(conflict_id)

    def update_strategic_conflict(self, conflict_id, **changes):
        allowed = {
            "status",
            "outcome",
            "max_attack_progress",
            "offensive_score",
            "defensive_score",
            "offensive_actors_json",
            "defensive_actors_json",
            "assessment_json",
            "resolved_at",
            "updated_at",
        }
        assignments = []
        values = []
        for key, value in changes.items():
            if key not in allowed:
                continue
            if key in {"offensive_actors_json", "defensive_actors_json"}:
                value = dumps_json(value if isinstance(value, list) else [])
            if key == "assessment_json":
                value = dumps_json(value if isinstance(value, dict) else {})
            assignments.append(f"{key} = ?")
            values.append(value)
        if not assignments:
            return self.get_strategic_conflict(conflict_id)
        if "updated_at" not in changes:
            assignments.append("updated_at = ?")
            values.append(self.now())
        values.append(_clean(conflict_id))
        with self._conn() as conn:
            conn.execute(
                f"UPDATE ghost_strategic_conflicts SET {', '.join(assignments)} WHERE conflict_id = ?",
                values,
            )
            row = conn.execute(
                "SELECT * FROM ghost_strategic_conflicts WHERE conflict_id = ? LIMIT 1",
                (_clean(conflict_id),),
            ).fetchone()
            return self._strategic_conflict(row)

    def insert_conflict_action(self, action):
        action = action if isinstance(action, dict) else {}
        dedupe_key = _clean(action.get("dedupe_key"))
        if dedupe_key:
            existing = self.get_conflict_action_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        cycle_id = _clean(action.get("cycle_id"))
        conflict_id = _clean(action.get("conflict_id"))
        part_id = _clean(action.get("part_id"))
        now = _clean(action.get("created_at") or self.now())
        action_id = _clean(action.get("action_id") or _hash_id("ghost_action", cycle_id, conflict_id, action.get("side"), action.get("action_type"), action.get("player_id"), dedupe_key, now))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_conflict_actions (
                        action_id, conflict_id, cycle_id, part_id, side, action_type,
                        player_id, clan_code, profession_code, target_id, operation_id,
                        mechanical_value, weight, source_event_id, dedupe_key,
                        metadata_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        conflict_id,
                        cycle_id,
                        part_id,
                        _clean(action.get("side")),
                        _clean(action.get("action_type")),
                        _clean(action.get("player_id")),
                        _clean(action.get("clan_code")),
                        _clean(action.get("profession_code")),
                        _clean(action.get("target_id")),
                        _clean(action.get("operation_id")),
                        int(action.get("mechanical_value") or 0),
                        float(action.get("weight") or 1.0),
                        _clean(action.get("source_event_id")),
                        dedupe_key,
                        dumps_json(action.get("metadata") if isinstance(action.get("metadata"), dict) else {}),
                        now,
                    ),
                )
            except IntegrityError:
                if dedupe_key:
                    existing = self.get_conflict_action_by_dedupe_key(dedupe_key)
                    if existing:
                        existing["idempotent"] = True
                        return existing
                raise
            row = conn.execute(
                "SELECT * FROM ghost_conflict_actions WHERE action_id = ? LIMIT 1",
                (action_id,),
            ).fetchone()
            return self._conflict_action(row)

    def get_conflict_action_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_conflict_actions WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            return self._conflict_action(row)

    def list_conflict_actions(self, conflict_id, side=None, limit=500):
        limit = max(1, min(int(limit or 500), 5000))
        where = ["conflict_id = ?"]
        params = [_clean(conflict_id)]
        if side:
            where.append("side = ?")
            params.append(_clean(side))
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_conflict_actions
                WHERE {' AND '.join(where)}
                ORDER BY created_at ASC, action_id ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._conflict_action(row) for row in rows]

    def insert_control_period(self, period):
        period = period if isinstance(period, dict) else {}
        dedupe_key = _clean(period.get("dedupe_key"))
        if dedupe_key:
            existing = self.get_control_period_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        cycle_id = _clean(period.get("cycle_id"))
        part_id = _clean(period.get("part_id"))
        started_at = _clean(period.get("started_at") or self.now())
        period_id = _clean(period.get("period_id") or _hash_id("ghost_period", cycle_id, part_id, period.get("owner_id"), period.get("clan_code"), started_at, dedupe_key))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_control_periods (
                        period_id, cycle_id, part_id, owner_id, clan_code, territory_id,
                        status, started_at, ended_at, duration_seconds, end_reason,
                        metadata_json, dedupe_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        period_id,
                        cycle_id,
                        part_id,
                        _clean(period.get("owner_id")),
                        _clean(period.get("clan_code")),
                        _clean(period.get("territory_id")),
                        _clean(period.get("status")),
                        started_at,
                        _clean(period.get("ended_at")),
                        int(period.get("duration_seconds") or 0),
                        _clean(period.get("end_reason")),
                        dumps_json(period.get("metadata") if isinstance(period.get("metadata"), dict) else {}),
                        dedupe_key,
                    ),
                )
            except IntegrityError:
                if dedupe_key:
                    existing = self.get_control_period_by_dedupe_key(dedupe_key)
                    if existing:
                        existing["idempotent"] = True
                        return existing
                raise
            row = conn.execute("SELECT * FROM ghost_control_periods WHERE period_id = ?", (period_id,)).fetchone()
            return self._control_period(row)

    def get_control_period_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_control_periods WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            return self._control_period(row)

    def list_control_periods(self, part_id, cycle_id=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        where = ["part_id = ?"]
        params = [_clean(part_id)]
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_control_periods
                WHERE {' AND '.join(where)}
                ORDER BY started_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._control_period(row) for row in rows]

    def insert_transfer_history(self, transfer):
        transfer = transfer if isinstance(transfer, dict) else {}
        dedupe_key = _clean(transfer.get("dedupe_key"))
        if dedupe_key:
            existing = self.get_transfer_history_by_dedupe_key(dedupe_key)
            if existing:
                existing["idempotent"] = True
                return existing
        cycle_id = _clean(transfer.get("cycle_id"))
        part_id = _clean(transfer.get("part_id"))
        now = _clean(transfer.get("created_at") or self.now())
        transfer_id = _clean(transfer.get("transfer_id") or _hash_id("ghost_transfer", cycle_id, part_id, transfer.get("previous_owner_id"), transfer.get("new_owner_id"), transfer.get("conflict_id"), now, dedupe_key))
        with self.transaction():
            conn = self._transaction_conn
            self._require_cycle(conn, cycle_id)
            try:
                conn.execute(
                    """
                    INSERT INTO ghost_part_transfer_history (
                        transfer_id, cycle_id, part_id, previous_owner_id, new_owner_id,
                        previous_clan, new_clan, conflict_id, reward_status, reward_amount,
                        metadata_json, dedupe_key, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transfer_id,
                        cycle_id,
                        part_id,
                        _clean(transfer.get("previous_owner_id")),
                        _clean(transfer.get("new_owner_id")),
                        _clean(transfer.get("previous_clan")),
                        _clean(transfer.get("new_clan")),
                        _clean(transfer.get("conflict_id")),
                        _clean(transfer.get("reward_status")),
                        int(transfer.get("reward_amount") or 0),
                        dumps_json(transfer.get("metadata") if isinstance(transfer.get("metadata"), dict) else {}),
                        dedupe_key,
                        now,
                    ),
                )
            except IntegrityError:
                if dedupe_key:
                    existing = self.get_transfer_history_by_dedupe_key(dedupe_key)
                    if existing:
                        existing["idempotent"] = True
                        return existing
                raise
            row = conn.execute("SELECT * FROM ghost_part_transfer_history WHERE transfer_id = ?", (transfer_id,)).fetchone()
            return self._transfer_history(row)

    def get_transfer_history_by_dedupe_key(self, dedupe_key):
        dedupe_key = _clean(dedupe_key)
        if not dedupe_key:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ghost_part_transfer_history WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            return self._transfer_history(row)

    def list_transfer_history(self, part_id=None, cycle_id=None, previous_owner_id=None, new_owner_id=None, limit=100):
        limit = max(1, min(int(limit or 100), 1000))
        where = []
        params = []
        if part_id:
            where.append("part_id = ?")
            params.append(_clean(part_id))
        if cycle_id:
            where.append("cycle_id = ?")
            params.append(_clean(cycle_id))
        if previous_owner_id:
            where.append("previous_owner_id = ?")
            params.append(_clean(previous_owner_id))
        if new_owner_id:
            where.append("new_owner_id = ?")
            params.append(_clean(new_owner_id))
        params.append(limit)
        query_where = f"WHERE {' AND '.join(where)}" if where else ""
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM ghost_part_transfer_history
                {query_where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._transfer_history(row) for row in rows]

    def build_internal_snapshot(self, cycle_id):
        with self._conn() as conn:
            cycle = self._require_cycle(conn, cycle_id)
            parts = [
                self._part(row)
                for row in conn.execute(
                    "SELECT * FROM ghost_parts WHERE cycle_id = ? ORDER BY part_code ASC",
                    (cycle_id,),
                ).fetchall()
            ]
            connections = [
                self._connection(row)
                for row in conn.execute(
                    "SELECT * FROM ghost_connections WHERE cycle_id = ? ORDER BY position_in_ring ASC",
                    (cycle_id,),
                ).fetchall()
            ]
            reservations = [
                self._reservation(row)
                for row in conn.execute(
                    """
                    SELECT * FROM ghost_part_reservations
                    WHERE cycle_id = ? AND status = 'active'
                    ORDER BY reserved_at ASC
                    """,
                    (cycle_id,),
                ).fetchall()
            ]
            return {
                "cycle": cycle,
                "parts": parts,
                "connections": connections,
                "topology": {
                    "seed": cycle.get("topology_seed") or "",
                    "checksum": cycle.get("topology_checksum") or "",
                    "ring_order": [],
                    "connections": connections,
                    "validation": {"ok": False, "reason": "not_validated_by_repository"},
                },
                "active_reservations": reservations,
                "state_version": int(cycle.get("state_version") or 0),
            }

    def health_check(self):
        warnings = []
        errors = []
        metrics = {}
        with self._conn() as conn:
            active_count = conn.execute(
                """
                SELECT COUNT(*) AS c FROM ghost_cycles
                WHERE status IN ('preparing', 'active', 'transmitting', 'stabilizing')
                """
            ).fetchone()["c"]
            metrics["blocking_cycles"] = int(active_count or 0)
            if int(active_count or 0) > 1:
                errors.append("more_than_one_active_or_transitional_cycle")

            invalid_cycles = conn.execute(
                "SELECT COUNT(*) AS c FROM ghost_cycles WHERE status NOT IN ('preparing','active','transmitting','stabilizing','closed')"
            ).fetchone()["c"]
            invalid_parts = conn.execute(
                "SELECT COUNT(*) AS c FROM ghost_parts WHERE status NOT IN ('pooled','reserved','public','contained','active','consumed')"
            ).fetchone()["c"]
            invalid_reservations = conn.execute(
                "SELECT COUNT(*) AS c FROM ghost_part_reservations WHERE status NOT IN ('active','committed','released','expired','cancelled')"
            ).fetchone()["c"]
            metrics["invalid_cycles"] = int(invalid_cycles or 0)
            metrics["invalid_parts"] = int(invalid_parts or 0)
            metrics["invalid_reservations"] = int(invalid_reservations or 0)
            if invalid_cycles:
                errors.append("invalid_cycle_status")
            if invalid_parts:
                errors.append("invalid_part_status")
            if invalid_reservations:
                errors.append("invalid_reservation_status")

            parts_without_cycle = conn.execute(
                """
                SELECT COUNT(*) AS c FROM ghost_parts p
                LEFT JOIN ghost_cycles c ON c.cycle_id = p.cycle_id
                WHERE c.cycle_id IS NULL
                """
            ).fetchone()["c"]
            metrics["parts_without_cycle"] = int(parts_without_cycle or 0)
            if parts_without_cycle:
                errors.append("parts_without_cycle")

            duplicate_part_codes = conn.execute(
                """
                SELECT COUNT(*) AS c FROM (
                    SELECT cycle_id, part_code FROM ghost_parts
                    GROUP BY cycle_id, part_code HAVING COUNT(*) > 1
                )
                """
            ).fetchone()["c"]
            duplicate_targets = conn.execute(
                """
                SELECT COUNT(*) AS c FROM (
                    SELECT cycle_id, target_id FROM ghost_parts
                    WHERE target_id != ''
                    GROUP BY cycle_id, target_id HAVING COUNT(*) > 1
                )
                """
            ).fetchone()["c"]
            metrics["duplicate_part_codes"] = int(duplicate_part_codes or 0)
            metrics["duplicate_targets"] = int(duplicate_targets or 0)
            if duplicate_part_codes:
                errors.append("duplicate_part_code")
            if duplicate_targets:
                errors.append("duplicate_target_id")

            now = self.now()
            overdue_reservations = conn.execute(
                """
                SELECT COUNT(*) AS c FROM ghost_part_reservations
                WHERE status = 'active' AND expires_at != '' AND expires_at < ?
                """,
                (now,),
            ).fetchone()["c"]
            metrics["overdue_active_reservations"] = int(overdue_reservations or 0)
            if overdue_reservations:
                warnings.append("active_reservations_after_expires_at")

            reserved_without_reservation = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts p
                LEFT JOIN ghost_part_reservations r
                  ON r.part_id = p.part_id AND r.cycle_id = p.cycle_id AND r.status = 'active'
                WHERE p.status = 'reserved' AND r.reservation_id IS NULL
                """
            ).fetchone()["c"]
            active_reservation_part_not_reserved = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_part_reservations r
                LEFT JOIN ghost_parts p ON p.part_id = r.part_id AND p.cycle_id = r.cycle_id
                WHERE r.status = 'active'
                  AND (p.part_id IS NULL OR p.status != 'reserved')
                """
            ).fetchone()["c"]
            metrics["reserved_parts_without_active_reservation"] = int(reserved_without_reservation or 0)
            metrics["active_reservations_with_unreserved_part"] = int(active_reservation_part_not_reserved or 0)
            if reserved_without_reservation:
                errors.append("reserved_part_without_active_reservation")
            if active_reservation_part_not_reserved:
                errors.append("active_reservation_part_not_reserved")

            public_without_anchor = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status IN ('public','contained','active','consumed')
                  AND (
                    target_id = ''
                    OR latitude IS NULL
                    OR longitude IS NULL
                    OR discovered_by = ''
                    OR discovered_at = ''
                  )
                """
            ).fetchone()["c"]
            committed_reserved = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_part_reservations r
                JOIN ghost_parts p ON p.part_id = r.part_id AND p.cycle_id = r.cycle_id
                WHERE r.status = 'committed' AND p.status = 'reserved'
                """
            ).fetchone()["c"]
            anchored_without_committed = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts p
                LEFT JOIN ghost_part_reservations r
                  ON r.part_id = p.part_id
                 AND r.cycle_id = p.cycle_id
                 AND r.target_id = p.target_id
                 AND r.status = 'committed'
                WHERE p.status IN ('public','contained','active','consumed')
                  AND p.target_id != ''
                  AND r.reservation_id IS NULL
                """
            ).fetchone()["c"]
            public_missing_event = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts p
                LEFT JOIN ghost_part_events e
                  ON e.part_id = p.part_id
                 AND e.cycle_id = p.cycle_id
                 AND e.event_type = 'ghost.part_discovered'
                WHERE p.status IN ('public','contained','active','consumed')
                  AND p.target_id != ''
                  AND e.event_id IS NULL
                """
            ).fetchone()["c"]
            metrics["public_parts_without_anchor"] = int(public_without_anchor or 0)
            metrics["committed_reservations_with_reserved_part"] = int(committed_reserved or 0)
            metrics["anchored_parts_without_committed_reservation"] = int(anchored_without_committed or 0)
            metrics["public_parts_missing_discovery_event"] = int(public_missing_event or 0)
            if public_without_anchor:
                errors.append("public_part_without_anchor")
            if committed_reserved:
                errors.append("committed_reservation_with_reserved_part")
            if anchored_without_committed:
                errors.append("anchored_part_without_committed_reservation")
            if public_missing_event:
                errors.append("public_part_missing_discovery_event")

            active_without_territory_clan = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'active' AND territory_clan = ''
                """
            ).fetchone()["c"]
            active_wrong_territory_clan = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'active'
                  AND territory_clan != ''
                  AND clan_code != territory_clan
                """
            ).fetchone()["c"]
            contained_without_owner = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'contained' AND territory_owner_id = ''
                """
            ).fetchone()["c"]
            public_with_owner = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'public'
                  AND (territory_id != '' OR territory_owner_id != '' OR territory_clan != '')
                """
            ).fetchone()["c"]
            consumed_without_signal = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'consumed' AND consumed_signal_id = ''
                """
            ).fetchone()["c"]
            conflict_without_frozen = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE conflict_state = 'contested' AND frozen_status = ''
                """
            ).fetchone()["c"]
            legacy_contested_status = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_parts
                WHERE status = 'contested'
                """
            ).fetchone()["c"]
            metrics["active_parts_without_territory_clan"] = int(active_without_territory_clan or 0)
            metrics["active_parts_wrong_territory_clan"] = int(active_wrong_territory_clan or 0)
            metrics["contained_parts_without_owner"] = int(contained_without_owner or 0)
            metrics["public_parts_with_owner"] = int(public_with_owner or 0)
            metrics["consumed_parts_without_signal"] = int(consumed_without_signal or 0)
            metrics["contested_parts_without_frozen_status"] = int(conflict_without_frozen or 0)
            metrics["legacy_contested_status_parts"] = int(legacy_contested_status or 0)
            if active_without_territory_clan:
                errors.append("active_part_without_territory_clan")
            if active_wrong_territory_clan:
                errors.append("active_part_wrong_territory_clan")
            if contained_without_owner:
                errors.append("contained_part_without_owner")
            if public_with_owner:
                errors.append("public_part_with_owner")
            if consumed_without_signal:
                errors.append("consumed_part_without_signal")
            if conflict_without_frozen:
                errors.append("contested_part_without_frozen_status")
            if legacy_contested_status:
                errors.append("legacy_contested_status")

            duplicate_signals = conn.execute(
                """
                SELECT COUNT(*) AS c FROM (
                    SELECT cycle_id FROM ghost_signals
                    GROUP BY cycle_id HAVING COUNT(*) > 1
                )
                """
            ).fetchone()["c"]
            signal_without_lock = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_signals s
                LEFT JOIN ghost_cycle_lock_snapshots l
                  ON l.lock_snapshot_id = s.lock_snapshot_id
                 AND l.cycle_id = s.cycle_id
                WHERE s.lock_snapshot_id = ''
                   OR l.lock_snapshot_id IS NULL
                """
            ).fetchone()["c"]
            signal_with_active_parts = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_signals s
                JOIN ghost_parts p ON p.cycle_id = s.cycle_id
                WHERE p.status = 'active'
                """
            ).fetchone()["c"]
            sent_signal_without_history = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_signals s
                LEFT JOIN ghost_historical_nodes h ON h.signal_id = s.signal_id
                GROUP BY s.signal_id
                HAVING COUNT(h.historical_node_id) != 20
                """
            ).fetchall()
            metrics["duplicate_signals_per_cycle"] = int(duplicate_signals or 0)
            metrics["signals_without_lock_snapshot"] = int(signal_without_lock or 0)
            metrics["signals_with_active_parts"] = int(signal_with_active_parts or 0)
            metrics["signals_without_20_historical_nodes"] = len(sent_signal_without_history)
            if duplicate_signals:
                errors.append("duplicate_signal_for_cycle")
            if signal_without_lock:
                errors.append("signal_without_lock_snapshot")
            if signal_with_active_parts:
                errors.append("signal_with_active_parts")
            if sent_signal_without_history:
                errors.append("signal_without_20_historical_nodes")

            broken_connections = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM ghost_connections gc
                LEFT JOIN ghost_parts a ON a.part_id = gc.part_a_id
                LEFT JOIN ghost_parts b ON b.part_id = gc.part_b_id
                WHERE a.part_id IS NULL OR b.part_id IS NULL OR gc.part_a_id = gc.part_b_id
                """
            ).fetchone()["c"]
            metrics["broken_connections"] = int(broken_connections or 0)
            if broken_connections:
                errors.append("broken_connections")

            negative_versions = conn.execute(
                "SELECT COUNT(*) AS c FROM ghost_cycles WHERE state_version < 0"
            ).fetchone()["c"]
            metrics["negative_state_versions"] = int(negative_versions or 0)
            if negative_versions:
                errors.append("negative_state_version")

            if int(active_count or 0) == 0:
                warnings.append("no_active_cycle")

            current_checksum = get_catalog_checksum(get_catalog())
            blocking_cycles = [
                self._cycle(row)
                for row in conn.execute(
                    """
                    SELECT * FROM ghost_cycles
                    WHERE status IN ('preparing', 'active', 'transmitting', 'stabilizing')
                    ORDER BY created_at ASC
                    """
                ).fetchall()
            ]
            for cycle in blocking_cycles:
                cycle_id = cycle["cycle_id"]
                ghostsystem_version = int(cycle.get("ghostsystem_version") or 0)
                if ghostsystem_version <= 0:
                    errors.append("invalid_ghostsystem_version")
                event_version = conn.execute(
                    """
                    SELECT COALESCE(MAX(state_version), 0) AS version
                    FROM ghost_part_events
                    WHERE cycle_id = ?
                    """,
                    (cycle_id,),
                ).fetchone()["version"]
                if int(event_version or 0) > int(cycle.get("state_version") or 0):
                    errors.append("state_version_mismatch")

                part_rows = [
                    self._part(row)
                    for row in conn.execute(
                        "SELECT * FROM ghost_parts WHERE cycle_id = ? ORDER BY part_code ASC",
                        (cycle_id,),
                    ).fetchall()
                ]
                metrics[f"{cycle_id}:parts_total"] = len(part_rows)
                if not cycle.get("catalog_version"):
                    warnings.append(f"{cycle_id}:cycle_missing_catalog_version")
                    continue
                if cycle.get("catalog_version") != CATALOG_VERSION:
                    warnings.append(f"{cycle_id}:catalog_version_differs_from_runtime")
                if cycle.get("catalog_checksum") and cycle.get("catalog_checksum") != current_checksum:
                    warnings.append(f"{cycle_id}:catalog_checksum_differs_from_runtime")
                if len(part_rows) != 20:
                    errors.append("active_cycle_without_20_parts")
                connection_count = conn.execute(
                    "SELECT COUNT(*) AS c FROM ghost_connections WHERE cycle_id = ?",
                    (cycle_id,),
                ).fetchone()["c"]
                metrics[f"{cycle_id}:connections_total"] = int(connection_count or 0)
                if cycle.get("status") == "stabilizing":
                    if int(connection_count or 0) != 0:
                        errors.append("stabilizing_cycle_with_active_connections")
                    if not cycle.get("restart_required") or not cycle.get("restart_signal_id"):
                        errors.append("stabilizing_cycle_without_restart_signal")
                    if not cycle.get("stabilization_until"):
                        errors.append("stabilizing_cycle_without_until")
                elif len(part_rows) == 20 and int(connection_count or 0) != 20:
                    errors.append("active_cycle_without_20_connections")
                if (
                    cycle.get("status") != "stabilizing"
                    and len(part_rows) == 20
                    and int(connection_count or 0) == 20
                    and not cycle.get("topology_checksum")
                ):
                    errors.append("active_cycle_missing_topology_checksum")
                clans = {}
                machines = {}
                codes = set()
                for part in part_rows:
                    clans[part["clan_code"]] = clans.get(part["clan_code"], 0) + 1
                    machines[part["machine_code"]] = machines.get(part["machine_code"], 0) + 1
                    codes.add(part["part_code"])
                    if part.get("catalog_version") != cycle.get("catalog_version"):
                        errors.append("part_catalog_version_mismatch")
                    if part.get("status") == "pooled":
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
                if len(codes) != len(part_rows):
                    errors.append("duplicate_part_code")
                if part_rows and (set(clans.values()) != {5} or set(machines.values()) != {5}):
                    errors.append("invalid_part_distribution")

        return {
            "ok": not errors,
            "warnings": warnings,
            "errors": errors,
            "metrics": metrics,
        }
