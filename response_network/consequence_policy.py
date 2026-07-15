from __future__ import annotations

import hashlib
from datetime import datetime, timezone


CONSEQUENCE_MODE_LIMITED = "limited_enforcement"
CONSEQUENCE_MODE_FULL = "full"
CONSEQUENCE_ACTION_CANCEL_OPERATION = "cancel_operation"


FULL_RESPONSE_FEATURES = {
    "operation_cancel",
    "tool_confiscation",
    "hc_confiscation",
    "judgment",
    "radio_hooks",
    "cyberner_hooks",
    "incident_history",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(value=None):
    if isinstance(value, datetime):
        dt = value
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _consequence_id(decision):
    key = ":".join([
        _clean(decision.get("validation_key"), "validation"),
        _clean(decision.get("operation_id"), "operation"),
        CONSEQUENCE_ACTION_CANCEL_OPERATION,
    ])
    return "consequence_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


class ConsequencePolicy:
    """Converts accepted detection decisions into Response Network intents."""

    def __init__(self, mode=CONSEQUENCE_MODE_LIMITED, kill_switch=False, feature_flags=None):
        self.mode = mode
        self._kill_switch = bool(kill_switch)
        self._feature_flags = {
            "operation_cancel": True,
            "tool_confiscation": False,
            "hc_confiscation": False,
            "judgment": False,
            "radio_hooks": False,
            "cyberner_hooks": False,
            "incident_history": False,
        }
        if isinstance(feature_flags, dict):
            for key, value in feature_flags.items():
                if key in self._feature_flags:
                    self._feature_flags[key] = bool(value)

    def set_kill_switch(self, enabled):
        self._kill_switch = bool(enabled)

    def kill_switch_active(self):
        return bool(self._kill_switch)

    def set_feature_enabled(self, feature, enabled):
        feature = _clean(feature)
        if feature in self._feature_flags:
            self._feature_flags[feature] = bool(enabled)

    def feature_enabled(self, feature):
        feature = _clean(feature)
        return bool(self._feature_flags.get(feature))

    def feature_flags(self):
        return dict(self._feature_flags)

    def prepare_intent(self, decision, now=None):
        decision = decision if isinstance(decision, dict) else {}
        now_iso = _iso(now)
        if self._kill_switch:
            return {
                "status": "disabled",
                "reason": "consequence_kill_switch",
                "mode": self.mode,
                "created_at": now_iso,
            }
        if self.mode not in {CONSEQUENCE_MODE_LIMITED, CONSEQUENCE_MODE_FULL}:
            return {
                "status": "disabled",
                "reason": "consequence_mode_disabled",
                "mode": self.mode,
                "created_at": now_iso,
            }
        if _clean(decision.get("status") or decision.get("result")) != "accepted":
            return {
                "status": "rejected",
                "reason": "detection_not_accepted",
                "mode": self.mode,
                "created_at": now_iso,
            }

        operation_id = _clean(decision.get("operation_id"))
        actor_id = _clean(decision.get("actor_id"))
        if not operation_id or not actor_id:
            return {
                "status": "rejected",
                "reason": "missing_operation_or_actor",
                "mode": self.mode,
                "created_at": now_iso,
            }

        full_mode = self.mode == CONSEQUENCE_MODE_FULL
        features = self.feature_flags()
        confiscate_tools = bool(full_mode and features.get("tool_confiscation"))
        confiscate_hc = bool(full_mode and features.get("hc_confiscation"))
        judgment = bool(full_mode and features.get("judgment"))
        reason = "full_response_network_detection" if full_mode else "limited_enforcement_detection"

        return {
            "schema": 1,
            "status": "prepared",
            "mode": self.mode,
            "action": CONSEQUENCE_ACTION_CANCEL_OPERATION,
            "consequence_id": _consequence_id(decision),
            "actor_id": actor_id,
            "operation_id": operation_id,
            "incident_id": _clean(decision.get("incident_id")),
            "capsule_id": _clean(decision.get("capsule_id")),
            "candidate_id": _clean(decision.get("candidate_id")),
            "validation_key": _clean(decision.get("validation_key")),
            "reason": reason,
            "created_at": now_iso,
            "confiscate_tools": confiscate_tools,
            "confiscate_hc": confiscate_hc,
            "judgment": judgment,
            "radio_hooks": bool(full_mode and features.get("radio_hooks")),
            "cyberner_hooks": bool(full_mode and features.get("cyberner_hooks")),
            "incident_history": bool(full_mode and features.get("incident_history")),
            "softlock_protection": True,
            "feature_flags": features,
            "remove_operation_progress": True,
            "cancel_related_operation_only": True,
        }
