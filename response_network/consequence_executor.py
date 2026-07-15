from __future__ import annotations

import copy
from datetime import datetime, timezone

from database import DB_PATH, db_connect, dumps_json, loads_json


EXECUTED_STATUSES = {"executed", "superseded", "rejected", "disabled"}


def _utc_now():
    return datetime.now(timezone.utc)


def _coerce_datetime(value=None):
    if isinstance(value, datetime):
        dt = value
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(value=None):
    return _coerce_datetime(value).isoformat()


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _row_to_item(row):
    if not row:
        return None
    intent = loads_json(row["intent_json"], {}) or {}
    result = loads_json(row["result_json"], {}) or {}
    item = {
        "consequence_id": row["consequence_id"],
        "status": row["status"],
        "actor_id": row["actor_id"],
        "operation_id": row["operation_id"],
        "incident_id": row["incident_id"],
        "candidate_id": row["candidate_id"],
        "validation_key": row["validation_key"],
        "intent": intent,
        "result": result,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    item.update(result)
    return item


class ConsequenceExecutor:
    """Idempotent executor for Response Network consequences."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_consequences (
                    consequence_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    actor_id TEXT NOT NULL DEFAULT '',
                    operation_id TEXT NOT NULL DEFAULT '',
                    incident_id TEXT NOT NULL DEFAULT '',
                    candidate_id TEXT NOT NULL DEFAULT '',
                    validation_key TEXT NOT NULL DEFAULT '',
                    intent_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_consequence_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    consequence_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_consequences_operation ON response_consequences(operation_id, status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_consequences_validation ON response_consequences(validation_key)"
            )

    def _audit(self, conn, consequence_id, event_type, payload=None, now=None):
        conn.execute(
            """
            INSERT INTO response_consequence_audit (consequence_id, event_type, event_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _clean(consequence_id),
                _clean(event_type, "consequence.audit"),
                dumps_json(payload if isinstance(payload, dict) else {}),
                _iso(now),
            ),
        )

    def get(self, consequence_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_consequences WHERE consequence_id = ?",
                (_clean(consequence_id),),
            ).fetchone()
            return _row_to_item(row)

    @staticmethod
    def _remove_operation_progress(operation, now_iso):
        if not isinstance(operation, dict):
            return False
        resource_buffer = operation.setdefault("resource_buffer", {})
        if not isinstance(resource_buffer, dict):
            resource_buffer = {}
            operation["resource_buffer"] = resource_buffer
        resource_buffer["cancelled"] = True
        resource_buffer["progress_removed"] = True
        resource_buffer["reward_blocked"] = True
        resource_buffer["files"] = []
        resource_buffer["items"] = []
        for key in list(resource_buffer.keys()):
            if key.endswith("_file_created") or key.endswith("_files_created") or key.endswith("_fragments_created"):
                resource_buffer[key] = False if key.endswith("_created") else 0
        operation["fragments"] = []
        operation["reward_blocked"] = True
        operation["progress_removed_at"] = now_iso
        operation["no_reward_reason"] = "response_network_detected"
        return True

    @staticmethod
    def _operation_tool_ref(operation):
        operation = operation if isinstance(operation, dict) else {}
        app_id = _clean(
            operation.get("source_app_id")
            or operation.get("app_id")
            or operation.get("tool_id")
        )
        app_name = _clean(
            operation.get("source_app_name")
            or operation.get("app_name")
            or operation.get("tool_name")
        )
        return {
            "app_id": app_id,
            "app_name": app_name,
        }

    @staticmethod
    def _app_id(app):
        app = app if isinstance(app, dict) else {}
        return _clean(app.get("id") or app.get("app_id") or app.get("tool_id"))

    @staticmethod
    def _app_name(app):
        app = app if isinstance(app, dict) else {}
        return _clean(app.get("name") or app.get("app_name") or app.get("title"))

    @staticmethod
    def _is_operation_tool(app):
        if not isinstance(app, dict):
            return False
        operation_types = app.get("operation_types")
        if isinstance(operation_types, list) and operation_types:
            return True
        if _clean(app.get("map_action_id") or app.get("operation_type")):
            return True
        category = _clean(app.get("category") or app.get("family")).lower()
        product_type = _clean(app.get("product_type") or app.get("type")).lower()
        return category in {"tool", "tools", "pro_tool", "hack_tool"} or product_type in {"app", "tool"}

    @staticmethod
    def _matches_tool(app, tool_ref):
        app_id = ConsequenceExecutor._app_id(app).lower()
        app_name = ConsequenceExecutor._app_name(app).lower()
        wanted_id = _clean((tool_ref or {}).get("app_id")).lower()
        wanted_name = _clean((tool_ref or {}).get("app_name")).lower()
        return bool(
            (wanted_id and app_id == wanted_id)
            or (wanted_name and app_name == wanted_name)
            or (wanted_id and app_name == wanted_id)
            or (wanted_name and app_id == wanted_name)
        )

    @staticmethod
    def _remove_tool_files(files, tool_ref):
        if not isinstance(files, dict):
            return 0
        tools = files.get("tools")
        if not isinstance(tools, list):
            return 0
        wanted = {
            _clean((tool_ref or {}).get("app_id")).lower(),
            _clean((tool_ref or {}).get("app_name")).lower(),
        }
        wanted.discard("")
        if not wanted:
            return 0

        kept = []
        removed = 0
        for item in tools:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            values = {
                _clean(item.get("id")).lower(),
                _clean(item.get("app_id")).lower(),
                _clean(item.get("tool_id")).lower(),
                _clean(item.get("name")).lower(),
                _clean(item.get("app_name")).lower(),
                _clean(item.get("filename")).lower(),
            }
            values.discard("")
            if values & wanted:
                removed += 1
                continue
            kept.append(item)
        files["tools"] = kept
        return removed

    def _confiscate_tool(self, profile, operation, intent, now_iso):
        result = {
            "attempted": bool(intent.get("confiscate_tools")),
            "confiscated": False,
            "reason": "disabled",
            "softlock_protection": bool(intent.get("softlock_protection", True)),
        }
        if not intent.get("confiscate_tools"):
            return result

        tool_ref = self._operation_tool_ref(operation)
        result.update(tool_ref)
        apps = profile.get("apps") if isinstance(profile, dict) else []
        if not isinstance(apps, list):
            apps = []
            profile["apps"] = apps

        match_index = None
        for index, app in enumerate(apps):
            if self._matches_tool(app, tool_ref):
                match_index = index
                break
        if match_index is None:
            result["reason"] = "tool_not_found"
            return result

        operation_capable_after = [
            app for index, app in enumerate(apps)
            if index != match_index and self._is_operation_tool(app)
        ]
        if intent.get("softlock_protection", True) and not operation_capable_after:
            result["reason"] = "softlock_protection"
            return result

        removed_app = apps.pop(match_index)
        files_removed = self._remove_tool_files(profile.get("files"), {
            "app_id": self._app_id(removed_app) or tool_ref.get("app_id"),
            "app_name": self._app_name(removed_app) or tool_ref.get("app_name"),
        })
        history = profile.setdefault("confiscation_history", [])
        if isinstance(history, list):
            history.append({
                "type": "tool",
                "app_id": self._app_id(removed_app),
                "app_name": self._app_name(removed_app),
                "operation_id": _clean(intent.get("operation_id")),
                "incident_id": _clean(intent.get("incident_id")),
                "consequence_id": _clean(intent.get("consequence_id")),
                "created_at": now_iso,
            })
        result.update({
            "confiscated": True,
            "reason": "tool_confiscated",
            "app_id": self._app_id(removed_app),
            "app_name": self._app_name(removed_app),
            "files_removed": files_removed,
        })
        return result

    @staticmethod
    def _risk_score(operation):
        operation = operation if isinstance(operation, dict) else {}
        meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
        for key in ("current_heat", "risk_score", "score", "active_contribution"):
            try:
                return max(0, int(meter.get(key) or 0))
            except (TypeError, ValueError):
                continue
        return 0

    def _confiscate_hc(self, profile, operation, intent, now_iso):
        result = {
            "attempted": bool(intent.get("confiscate_hc")),
            "confiscated": False,
            "reason": "disabled",
            "currency": "HC",
        }
        if not intent.get("confiscate_hc"):
            return result

        try:
            balance = int(profile.get("hackcoins", profile.get("wallet", 0)) or 0)
        except (TypeError, ValueError):
            balance = 0
        if balance <= 0:
            result.update({"reason": "empty_wallet", "balance_before": balance, "amount": 0})
            return result

        risk = self._risk_score(operation)
        base = max(10, risk // 2)
        percentage_cap = max(1, int(balance * 0.18))
        reserve = min(50, max(0, balance // 10))
        max_available = max(0, balance - reserve)
        amount = min(base, percentage_cap, max_available)
        if amount <= 0:
            result.update({"reason": "softlock_hc_reserve", "balance_before": balance, "amount": 0})
            return result

        after = max(0, balance - amount)
        profile["hackcoins"] = after
        if "wallet" in profile:
            profile["wallet"] = after
        history = profile.setdefault("confiscation_history", [])
        if isinstance(history, list):
            history.append({
                "type": "hc",
                "amount": amount,
                "balance_before": balance,
                "balance_after": after,
                "operation_id": _clean(intent.get("operation_id")),
                "incident_id": _clean(intent.get("incident_id")),
                "consequence_id": _clean(intent.get("consequence_id")),
                "created_at": now_iso,
            })
        result.update({
            "confiscated": True,
            "reason": "hc_confiscated",
            "amount": amount,
            "balance_before": balance,
            "balance_after": after,
            "risk_score": risk,
        })
        return result

    def _apply_judgment(self, profile, operation, intent, now_iso):
        result = {
            "attempted": bool(intent.get("judgment")),
            "applied": False,
            "reason": "disabled",
        }
        if not intent.get("judgment"):
            return result
        risk = self._risk_score(operation)
        judgment = profile.setdefault("judgment", {})
        if not isinstance(judgment, dict):
            judgment = {}
            profile["judgment"] = judgment
        points = int(judgment.get("points") or 0) + max(1, risk // 25)
        level = "high" if points >= 6 else "medium" if points >= 3 else "low"
        judgment.update({
            "status": "active",
            "points": points,
            "level": level,
            "last_operation_id": _clean(intent.get("operation_id")),
            "last_incident_id": _clean(intent.get("incident_id")),
            "updated_at": now_iso,
        })
        history = profile.setdefault("judgment_history", [])
        if isinstance(history, list):
            history.append({
                "operation_id": _clean(intent.get("operation_id")),
                "incident_id": _clean(intent.get("incident_id")),
                "consequence_id": _clean(intent.get("consequence_id")),
                "points_added": max(1, risk // 25),
                "points_total": points,
                "level": level,
                "created_at": now_iso,
            })
        result.update({
            "applied": True,
            "reason": "judgment_applied",
            "points": points,
            "level": level,
        })
        return result

    @staticmethod
    def _next_message_id(messages):
        numeric = []
        for item in messages:
            if isinstance(item, dict):
                try:
                    numeric.append(int(item.get("id") or 0))
                except (TypeError, ValueError):
                    pass
        return max(numeric, default=0) + 1

    def _emit_hooks(self, profile, operation, intent, result, now_iso):
        hook_result = {
            "cyberner": False,
            "radio": False,
        }
        app_name = _clean(result.get("confiscated_tool", {}).get("app_name") or operation.get("source_app_name"), "narzedzie")
        if intent.get("cyberner_hooks"):
            messages = profile.setdefault("system_messages", [])
            if not isinstance(messages, list):
                messages = []
                profile["system_messages"] = messages
            messages.append({
                "id": self._next_message_id(messages),
                "type": "warning",
                "notification_type": "cyberner",
                "source": "response_network",
                "title": "Response Network",
                "text": f"Operacja {intent.get('operation_id')} zostala przerwana. Uzyte narzedzie: {app_name}.",
                "status": "new",
                "created_at": now_iso,
            })
            hook_result["cyberner"] = True
        if intent.get("radio_hooks"):
            radio_events = profile.setdefault("radio_events", [])
            if isinstance(radio_events, list):
                radio_events.append({
                    "type": "response_network_consequence",
                    "operation_id": _clean(intent.get("operation_id")),
                    "incident_id": _clean(intent.get("incident_id")),
                    "consequence_id": _clean(intent.get("consequence_id")),
                    "severity": result.get("judgment_result", {}).get("level") or "low",
                    "created_at": now_iso,
                })
                hook_result["radio"] = True
        return hook_result

    def _record_incident_history(self, profile, intent, result, now_iso):
        if not intent.get("incident_history"):
            return False
        history = profile.setdefault("incident_history", [])
        if not isinstance(history, list):
            history = []
            profile["incident_history"] = history
        history.append({
            "incident_id": _clean(intent.get("incident_id")),
            "operation_id": _clean(intent.get("operation_id")),
            "consequence_id": _clean(intent.get("consequence_id")),
            "status": "closed_by_response_network",
            "confiscated_tools": bool(result.get("confiscated_tools")),
            "confiscated_hc": bool(result.get("confiscated_hc")),
            "judgment": bool(result.get("judgment")),
            "created_at": now_iso,
        })
        return True

    def execute(
        self,
        intent,
        profile,
        cancel_operation,
        refresh_operations,
        kill_switch_active=None,
        now=None,
    ):
        intent = copy.deepcopy(intent if isinstance(intent, dict) else {})
        consequence_id = _clean(intent.get("consequence_id"))
        actor_id = _clean(intent.get("actor_id"))
        operation_id = _clean(intent.get("operation_id"))
        now_iso = _iso(now)
        if not consequence_id or not actor_id or not operation_id:
            return {
                "status": "rejected",
                "reason": "invalid_intent",
                "consequence_executed": False,
                "penalty_executed": False,
            }

        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM response_consequences WHERE consequence_id = ?",
                (consequence_id,),
            ).fetchone()
            if existing:
                item = _row_to_item(existing)
                item["duplicate"] = True
                return item

            conn.execute(
                """
                INSERT INTO response_consequences (
                    consequence_id, status, actor_id, operation_id, incident_id,
                    candidate_id, validation_key, intent_json, result_json,
                    created_at, updated_at
                )
                VALUES (?, 'prepared', ?, ?, ?, ?, ?, ?, '{}', ?, ?)
                """,
                (
                    consequence_id,
                    actor_id,
                    operation_id,
                    _clean(intent.get("incident_id")),
                    _clean(intent.get("candidate_id")),
                    _clean(intent.get("validation_key")),
                    dumps_json(intent),
                    now_iso,
                    now_iso,
                ),
            )
            self._audit(conn, consequence_id, "consequence.prepared", intent, now=now_iso)

        if kill_switch_active and kill_switch_active():
            result = {
                "status": "disabled",
                "reason": "consequence_kill_switch",
                "consequence_executed": False,
                "penalty_executed": False,
            }
            self._finish(consequence_id, result, event_type="consequence.disabled", now=now_iso)
            return self.get(consequence_id)

        operation, cancel_result = cancel_operation(profile, operation_id)
        if cancel_result != "cancelled":
            status = "superseded" if cancel_result in {"already_terminal", "not_active"} else "rejected"
            result = {
                "status": status,
                "reason": cancel_result,
                "consequence_executed": False,
                "penalty_executed": False,
                "operation_id": operation_id,
            }
            self._finish(consequence_id, result, event_type=f"consequence.{status}", now=now_iso)
            return self.get(consequence_id)

        self._remove_operation_progress(operation, now_iso)
        tool_result = self._confiscate_tool(profile, operation, intent, now_iso)
        hc_result = self._confiscate_hc(profile, operation, intent, now_iso)
        judgment_result = self._apply_judgment(profile, operation, intent, now_iso)
        refreshed_operations = refresh_operations(profile)
        result = {
            "status": "executed",
            "reason": "operation_cancelled_by_response_network",
            "consequence_executed": True,
            "penalty_executed": False,
            "operation_id": operation_id,
            "operation_status": operation.get("status"),
            "progress_removed": True,
            "reward_blocked": True,
            "confiscated_tools": bool(tool_result.get("confiscated")),
            "confiscated_tool": tool_result,
            "confiscated_hc": bool(hc_result.get("confiscated")),
            "hc_confiscation": hc_result,
            "judgment": bool(judgment_result.get("applied")),
            "judgment_result": judgment_result,
            "softlock_protection": bool(intent.get("softlock_protection", True)),
            "feature_flags": copy.deepcopy(intent.get("feature_flags") or {}),
            "active_operations_after": [
                item.get("operation_id")
                for item in (refreshed_operations or [])
                if isinstance(item, dict) and item.get("status") in {"start", "running"}
            ],
        }
        result["penalty_executed"] = bool(
            result["confiscated_tools"]
            or result["confiscated_hc"]
            or result["judgment"]
        )
        hook_result = self._emit_hooks(profile, operation, intent, result, now_iso)
        result["cyberner_hook"] = bool(hook_result.get("cyberner"))
        result["radio_hook"] = bool(hook_result.get("radio"))
        result["incident_history_recorded"] = self._record_incident_history(profile, intent, result, now_iso)
        self._finish(consequence_id, result, event_type="consequence.executed", now=now_iso)
        return self.get(consequence_id)

    def _finish(self, consequence_id, result, event_type, now=None):
        now_iso = _iso(now)
        result = copy.deepcopy(result if isinstance(result, dict) else {})
        status = _clean(result.get("status"), "rejected")
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE response_consequences
                SET status = ?, result_json = ?, updated_at = ?
                WHERE consequence_id = ?
                """,
                (status, dumps_json(result), now_iso, consequence_id),
            )
            self._audit(conn, consequence_id, event_type, result, now=now_iso)
