from __future__ import annotations

from .service import GhostNetworkService


class GhostRuntimeCoordinator:
    """Durable runtime orchestration around existing GhostNetwork services."""

    TERMINAL_OUTCOMES = {"discovered", "already_discovered"}

    def __init__(self, service=None, profile_loader=None, profile_saver=None,
                 delta_publisher=None, captured_target_reader=None):
        self.service = service or GhostNetworkService()
        self.repository = self.service.repository
        self.profile_loader = profile_loader
        self.profile_saver = profile_saver
        self.delta_publisher = delta_publisher
        self.captured_target_reader = captured_target_reader

    def enqueue_capture(self, capture_key, player, target, operation=None, result=None,
                        reservation_id=""):
        active = self.repository.get_active_cycle()
        return self.repository.enqueue_capture_effect(
            capture_key, player, target, operation=operation, result=result,
            cycle_id=(active or {}).get("cycle_id") or "",
            reservation_id=reservation_id,
        )

    def reconcile_missing_effects(self, limit=500):
        active = self.repository.get_active_cycle()
        if not active or not self.captured_target_reader:
            return {"ok": True, "scanned": 0, "enqueued": 0}
        scanned = 0
        enqueued = 0
        for reservation in self.repository.list_active_reservations(active["cycle_id"], limit=limit):
            scanned += 1
            target = self.captured_target_reader(
                reservation.get("player_id"), reservation.get("target_id")
            )
            if not isinstance(target, dict) or not target:
                continue
            key = f"reconcile:{active['cycle_id']}:{reservation['reservation_id']}"
            existing = self.repository.get_capture_effect(key)
            if existing:
                continue
            self.enqueue_capture(
                key,
                {"player_id": reservation.get("player_id"), "clan_code": reservation.get("player_clan")},
                target,
                operation={"operation_id": reservation.get("operation_id") or ""},
                result={"target_captured": True, "source": "ghostnetwork_reconciliation"},
                reservation_id=reservation.get("reservation_id") or "",
            )
            enqueued += 1
        return {"ok": True, "scanned": scanned, "enqueued": enqueued}

    def process_effect(self, effect):
        if not effect or effect.get("status") == "applied":
            return {"ok": True, "status": "already_applied", "effect": effect}
        self.repository.mark_capture_effect_attempt(effect["effect_id"])
        try:
            outcome = self.service.on_target_hacked(
                effect.get("player") or {}, effect.get("target") or {},
                operation=effect.get("operation") or {},
                result={**(effect.get("result") or {}), "target_captured": True},
                context={"target_captured": True, "reason": "durable_capture_effect"},
            )
            status = outcome.get("status") or "unknown"
            if status not in self.TERMINAL_OUTCOMES:
                saved = self.repository.finish_capture_effect(
                    effect["effect_id"], "failed", outcome=status
                )
                return {"ok": False, "status": status, "effect": saved, "outcome": outcome}
            rewards = self._handle_result_rewards(outcome, effect)
            if self.delta_publisher:
                try:
                    self.delta_publisher(effect, outcome)
                except Exception:
                    # Snapshot recovery is authoritative for delivery; a delta
                    # transport failure must not replay an applied discovery.
                    pass
            saved = self.repository.finish_capture_effect(
                effect["effect_id"], "applied", outcome=status
            )
            return {"ok": True, "status": status, "effect": saved, "outcome": outcome, "rewards": rewards}
        except Exception as exc:
            saved = self.repository.finish_capture_effect(
                effect["effect_id"], "failed", outcome="exception", error=str(exc)
            )
            return {"ok": False, "status": "failed", "effect": saved, "error": str(exc)}

    def _handle_result_rewards(self, outcome, effect):
        events = []
        stack = [outcome]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                if value.get("event_id") and value.get("event_type"):
                    events.append(value)
                stack.extend(value.values())
            elif isinstance(value, (list, tuple)):
                stack.extend(value)
        if not events and outcome.get("status") == "already_discovered":
            active = self.repository.get_active_cycle()
            part = self.repository.find_part_by_target(
                (active or {}).get("cycle_id") or "", effect.get("target_id") or ""
            )
            if part:
                events = [
                    event for event in self.repository.list_events(part["cycle_id"], limit=1000)
                    if event.get("event_type") == "ghost.part_discovered"
                    and event.get("part_id") == part.get("part_id")
                ][-1:]
        player_id = effect.get("player_id") or ""
        profile = self.profile_loader(player_id) if self.profile_loader else dict(effect.get("player") or {})
        profile = profile if isinstance(profile, dict) else {}
        results = []
        pending_finalizations = []
        profile_changed = False
        for event in events:
            result = self.service.handle_reward_event(
                event,
                profile=profile,
                apply=False,
            )
            created = result.get("created") if isinstance(result, dict) else None
            reward = created.get("reward") if isinstance(created, dict) else None
            if isinstance(reward, dict):
                projection = self.service.project_reward_to_profile(
                    profile,
                    reward_id=reward.get("reward_id"),
                )
                result["projection"] = projection
                if not projection.get("ok"):
                    raise RuntimeError(
                        "GhostNetwork reward profile projection was rejected: "
                        + str(projection.get("status") or "unknown")
                    )
                profile_changed = profile_changed or bool(
                    projection.get("profile_changed")
                )
                if projection.get("requires_finalize"):
                    pending_finalizations.append((reward["reward_id"], result))
            results.append(result)

        if profile_changed:
            if not self.profile_saver:
                raise RuntimeError(
                    "GhostNetwork reward projection requires a durable profile saver."
                )
            self.profile_saver(profile)

        for reward_id, result in pending_finalizations:
            finalized = self.service.finalize_projected_reward(
                profile,
                reward_id=reward_id,
            )
            if not finalized.get("ok"):
                raise RuntimeError(
                    "GhostNetwork reward finalization was rejected: "
                    + str(finalized.get("status") or "unknown")
                )
            result["applied"] = finalized
        return results

    def drain(self, limit=100, reconcile=True):
        reconciliation = self.reconcile_missing_effects(limit=limit) if reconcile else {
            "ok": True, "scanned": 0, "enqueued": 0
        }
        results = [
            self.process_effect(effect)
            for effect in self.repository.list_capture_effects(statuses={"pending", "failed"}, limit=limit)
        ]
        return {
            "ok": all(item.get("ok") for item in results),
            "reconciliation": reconciliation,
            "processed": len(results),
            "results": results,
            "summary": self.repository.get_capture_effect_summary(),
        }
