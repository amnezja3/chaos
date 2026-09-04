import os
import json
import random
import sqlite3
import sys
import time
import traceback


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import run  # noqa: E402


_consecutive_ghostnetwork_jobs = 0
_ghostnetwork_delivery_turn = True
_ghostnetwork_service = None
_next_operation_runtime_tick_at = 0.0
_next_blacknet_narrative_tick_at = 0.0
_next_ghostnetwork_endgame_tick_at = 0.0
_last_ghostnetwork_endgame_block_key = ""
_next_ghostnetwork_endgame_block_log_at = 0.0


def is_database_contention(error):
    return isinstance(error, sqlite3.OperationalError) and any(
        marker in str(error).lower() for marker in ("locked", "busy")
    )


def contention_backoff_seconds():
    return random.uniform(0.15, 0.65)


def process_operation_runtime_if_due():
    """Run the operation projection on its own cadence, independent of queue load."""
    global _next_operation_runtime_tick_at
    now = time.monotonic()
    if now < _next_operation_runtime_tick_at:
        return {"users": 0, "operations": 0, "incidents": 0, "warnings": 0}
    result = run.process_operation_runtime_tick(limit_users=4, min_age_seconds=1.0)
    if result.get("files"):
        print(
            f"[TERRITORY_WORKER] operation_files_finalized={result['files']} "
            f"users={result.get('users', 0)}",
            flush=True,
        )
    interval = max(
        1.0,
        float(os.environ.get("CHAOS_OPERATION_RUNTIME_TICK_SECONDS", "2")),
    )
    # Schedule from completion so a slow tick can never immediately retrigger
    # itself and turn the worker into a permanent busy loop.
    _next_operation_runtime_tick_at = time.monotonic() + interval
    return result


def process_blacknet_narrative_if_due():
    """Enqueue one bounded public digest per canonical time window."""
    global _next_blacknet_narrative_tick_at
    now = time.monotonic()
    if now < _next_blacknet_narrative_tick_at:
        return None
    interval = max(
        300.0,
        float(os.environ.get("CHAOS_BLACKNET_NARRATIVE_TICK_SECONDS", "900")),
    )
    result = run.enqueue_blacknet_world_narrative_digest()
    _next_blacknet_narrative_tick_at = time.monotonic() + interval
    print(
        "[TERRITORY_WORKER] blacknet_narrative "
        f"status={result.get('status')} receipt_id={result.get('receipt_id') or '-'} "
        f"task_id={((result.get('task') or {}).get('outbox_id') or '-')}",
        flush=True,
    )
    return result


def process_ghostnetwork_endgame_if_due():
    """Run one bounded endgame recovery step independently of queue traffic."""
    global _ghostnetwork_service, _next_ghostnetwork_endgame_tick_at
    global _last_ghostnetwork_endgame_block_key, _next_ghostnetwork_endgame_block_log_at
    now = time.monotonic()
    if now < _next_ghostnetwork_endgame_tick_at:
        return None
    interval = max(
        1.0,
        float(os.environ.get("CHAOS_GHOSTNETWORK_ENDGAME_TICK_SECONDS", "2")),
    )
    if _ghostnetwork_service is None:
        _ghostnetwork_service = run.GhostNetworkService()
    try:
        result = run.advance_ghostnetwork_endgame_once(service=_ghostnetwork_service)
    finally:
        # Completion-based cadence prevents a slow SQLite or narrative tail
        # from immediately retriggering and monopolizing PM2 14.
        _next_ghostnetwork_endgame_tick_at = time.monotonic() + interval
    status = str((result or {}).get("status") or "")
    should_log = status in {"sent", "resumed", "rolled_over"}
    if status in {"blocked", "postcommit_retry", "settlement_blocked"}:
        block_key = json.dumps(
            {
                "cycle_id": (result or {}).get("cycle_id") or "",
                "phase": (result or {}).get("phase") or "",
                "reasons": (result or {}).get("reasons") or [],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        log_now = time.monotonic()
        should_log = (
            block_key != _last_ghostnetwork_endgame_block_key
            or log_now >= _next_ghostnetwork_endgame_block_log_at
        )
        if should_log:
            _last_ghostnetwork_endgame_block_key = block_key
            _next_ghostnetwork_endgame_block_log_at = log_now + 60.0
    if should_log:
        print(
            "[TERRITORY_WORKER] ghost_endgame "
            f"status={status} ok={bool((result or {}).get('ok'))} "
            f"cycle_id={(result or {}).get('cycle_id') or '-'} "
            f"phase={(result or {}).get('phase') or '-'} "
            f"recovered={bool((result or {}).get('recovered'))} "
            f"postcommit_pending={bool((result or {}).get('postcommit_pending'))} "
            f"reasons={(result or {}).get('reasons') or []}",
            flush=True,
        )
    return result


def process_ghostnetwork_once():
    global _ghostnetwork_delivery_turn, _ghostnetwork_service

    def process_delivery():
        delivery = run.process_ghostnetwork_delta_delivery_job(
            lease_owner=f"ghost-delta-worker:{os.getpid()}",
            lease_seconds=300,
        )
        if delivery is None:
            return False
        print(
            "[TERRITORY_WORKER] "
            f"ghost_delta_job_id={delivery.get('job_id')} "
            f"event_id={delivery.get('event_id')} ok={bool(delivery.get('ok'))} "
            f"complete={bool(delivery.get('complete'))} "
            f"recipients={delivery.get('batch_recipients')} "
            f"published={delivery.get('published')} skipped={delivery.get('skipped')} "
            f"elapsed_ms={delivery.get('elapsed_ms')} "
            f"queue={delivery.get('queue') or {}} error={delivery.get('error')}",
            flush=True,
        )
        return True

    def process_territory():
        global _ghostnetwork_service
        if _ghostnetwork_service is None:
            _ghostnetwork_service = run.GhostNetworkService()
        ghostnetwork_job = run.process_ghostnetwork_territory_job(
            lease_owner=f"ghost-territory-worker:{os.getpid()}",
            lease_seconds=300,
            service=_ghostnetwork_service,
        )
        if ghostnetwork_job is None:
            return False
        print(
            "[TERRITORY_WORKER] "
            f"ghost_job_id={ghostnetwork_job.get('job_id')} "
            f"kind={ghostnetwork_job.get('job_kind')} "
            f"reference={ghostnetwork_job.get('reference_id')} "
            f"ok={bool(ghostnetwork_job.get('ok'))} "
            f"elapsed_ms={ghostnetwork_job.get('elapsed_ms')} "
            f"timings_ms={ghostnetwork_job.get('timings_ms') or {}} "
            f"coalesced={ghostnetwork_job.get('coalesced_jobs') or 0} "
            f"queue={ghostnetwork_job.get('queue') or {}} "
            f"error={ghostnetwork_job.get('error')}",
            flush=True,
        )
        return True

    if _ghostnetwork_delivery_turn:
        if process_delivery():
            _ghostnetwork_delivery_turn = False
            return True
        if process_territory():
            _ghostnetwork_delivery_turn = True
            return True
    else:
        if process_territory():
            _ghostnetwork_delivery_turn = True
            return True
        if process_delivery():
            _ghostnetwork_delivery_turn = False
            return True
    return False


def compact_multi_audit_report(report):
    """Keep periodic logs useful without dumping full polygon coordinates."""
    publication = report.get("publication") or {}
    return {
        "metrics": report.get("metrics") or {},
        "mutations": int(report.get("mutations") or 0),
        "publication": {
            "ok": publication.get("ok"),
            "reason": publication.get("reason"),
            "candidates": publication.get("candidates"),
            "changed": [
                {
                    "engagement_id": item.get("engagement_id"),
                    "status": item.get("status"),
                    "engagement_version": item.get("engagement_version"),
                    "geometry_version": item.get("geometry_version"),
                    "snapshot_version": item.get("snapshot_version"),
                }
                for item in (publication.get("changed") or [])
            ],
        },
        "candidates": [
            {
                key: candidate.get(key)
                for key in (
                    "member_conflict_ids", "member_front_ids",
                    "participant_usernames", "participant_clans",
                    "hostile_clan_groups", "overlap_area", "overlap_bbox",
                    "candidate_status", "detection_reason",
                    "source_snapshot_versions",
                )
            }
            for candidate in (report.get("candidates") or [])
        ],
        "legacy_multi_participant_conflicts":
            report.get("legacy_multi_participant_conflicts") or [],
        "skipped_snapshots": report.get("skipped_snapshots") or [],
    }


def process_once():
    global _consecutive_ghostnetwork_jobs
    process_operation_runtime_if_due()
    process_blacknet_narrative_if_due()
    endgame = process_ghostnetwork_endgame_if_due()
    if str((endgame or {}).get("status") or "") in {"sent", "resumed"}:
        return True
    reward_projection = run.process_ghostnetwork_pending_reward_projection(
        service=_ghostnetwork_service,
        worker_id=f"ghost-reward-worker:{os.getpid()}",
        lease_seconds=60,
    )
    if int((reward_projection or {}).get("processed") or 0):
        print(
            "[TERRITORY_WORKER] ghost_reward_projection "
            f"status={reward_projection.get('status')} "
            f"reward_id={reward_projection.get('reward_id') or '-'} "
            f"player_id={reward_projection.get('player_id') or '-'} "
            f"profile_changed={bool(reward_projection.get('profile_changed'))}",
            flush=True,
        )
    elif str((reward_projection or {}).get("status") or "") == "blocked":
        print(
            "[TERRITORY_WORKER] ghost_reward_projection "
            f"status=blocked reward_id={reward_projection.get('reward_id') or '-'} "
            f"player_id={reward_projection.get('player_id') or '-'} "
            f"reason={reward_projection.get('reason') or 'unknown'}",
            flush=True,
        )
    strategic_rewards = run.retry_pending_strategic_progression(limit=1)
    if strategic_rewards:
        print(
            f"[TERRITORY_WORKER] strategic_reward={strategic_rewards[0]}",
            flush=True,
        )
        return True
    rebuild_job = run.process_territory_rebuild_job(
        lease_owner=f"territory-rebuild-worker:{os.getpid()}",
        lease_seconds=300,
    )
    if rebuild_job is not None:
        print(
            "[TERRITORY_WORKER] "
            f"job_id={rebuild_job.get('job_id')} ok={bool(rebuild_job.get('ok'))} "
            f"owner={rebuild_job.get('owner_username')} reason={rebuild_job.get('reason')} "
            f"areas={rebuild_job.get('areas')} conflicts={rebuild_job.get('conflicts')} "
            f"error={rebuild_job.get('error')}",
            flush=True,
        )
        return True
    reconciliation = run.process_territory_reconciliation_set(
        lease_owner=f"territory-set-worker:{os.getpid()}",
        lease_seconds=300,
    )
    if reconciliation is not None:
        print(
            "[TERRITORY_WORKER] "
            f"set_id={reconciliation.get('set_id')} ok={bool(reconciliation.get('ok'))} "
            f"target_id={reconciliation.get('target_id')} "
            f"winner={reconciliation.get('winner_username')} "
            f"conflict_ids={reconciliation.get('conflict_ids') or []} "
            f"engagement_ids={reconciliation.get('engagement_ids') or []}",
            flush=True,
        )
        return True
    max_consecutive_ghost_jobs = max(
        1, int(os.environ.get("CHAOS_GHOSTNETWORK_WORKER_MAX_CONSECUTIVE", "1"))
    )
    if _consecutive_ghostnetwork_jobs < max_consecutive_ghost_jobs:
        if process_ghostnetwork_once():
            _consecutive_ghostnetwork_jobs += 1
            return True
    settle_seconds = max(
        1.0,
        float(os.environ.get("CHAOS_TERRITORY_WORKER_SETTLE_SECONDS", "3")),
    )
    candidates = run.territory_conflict_store.list_rebuild_candidates(
        limit=1,
        min_age_seconds=settle_seconds,
    )
    if not candidates:
        if process_ghostnetwork_once():
            _consecutive_ghostnetwork_jobs = min(
                max_consecutive_ghost_jobs, _consecutive_ghostnetwork_jobs + 1
            )
            return True
        _consecutive_ghostnetwork_jobs = 0
        return False
    conflict_id = candidates[0]["conflict_id"]
    result = run.consolidate_conflict_rebuild(
        conflict_id,
        rebuild_participants=True,
        run_encirclement=True,
        lease_seconds=300,
    )
    finalized_profiles = []
    if result.get("ok"):
        finalized_profiles = run.finalize_conflict_rebuild_profiles(conflict_id)
    print(
        "[TERRITORY_WORKER] "
        f"conflict_id={conflict_id} ok={bool(result.get('ok'))} "
        f"changed={bool(result.get('changed'))} reason={result.get('reason')} "
        f"elapsed_ms={result.get('elapsed_ms')} profiles={finalized_profiles}",
        flush=True,
    )
    _consecutive_ghostnetwork_jobs = 0
    return True


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--audit-multi":
        report = run.audit_active_multi_conflict_candidates()
        print(f"[TERRITORY_MULTI_AUDIT] {json.dumps(report, ensure_ascii=False)}", flush=True)
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--discover":
        actor_username = sys.argv[2]
        conflicts = run.discover_and_queue_new_territory_conflicts(actor_username)
        print(
            f"[TERRITORY_WORKER] discovery actor={actor_username} "
            f"conflicts={[item.get('conflict_id') or item.get('id') for item in conflicts]}",
            flush=True,
        )
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--enqueue":
        conflict_id = sys.argv[2]
        conflict = run.territory_conflict_store.get_by_key(conflict_id)
        if not conflict:
            print(f"[TERRITORY_WORKER] enqueue failed conflict_id={conflict_id} reason=not_found", flush=True)
            raise SystemExit(1)
        queued = run.request_conflict_rebuild(
            conflict.get("conflict_id") or conflict_id,
            reason="manual_recovery",
            requested_version=conflict.get("conflict_version"),
        )
        print(f"[TERRITORY_WORKER] enqueued conflict_id={conflict_id} result={queued}", flush=True)
        return
    idle_seconds = max(1.0, float(os.environ.get("CHAOS_TERRITORY_WORKER_IDLE_SECONDS", "2")))
    reconcile_seconds = max(
        60.0,
        float(os.environ.get("CHAOS_TERRITORY_RECONCILE_SECONDS", "180")),
    )
    multi_audit_seconds = max(
        60.0,
        float(os.environ.get("CHAOS_TERRITORY_MULTI_AUDIT_SECONDS", "180")),
    )
    next_reconcile_at = time.monotonic()
    next_multi_audit_at = time.monotonic()
    while True:
        try:
            restored = run.restore_territory_reconcile_targets()
            delta_diagnostics = run.ghostnetwork_delta_delivery_job_store.diagnostics()
            break
        except Exception as exc:
            if not is_database_contention(exc):
                raise
            delay = contention_backoff_seconds()
            print(
                "[TERRITORY_WORKER] startup database_contended "
                f"retry_in_ms={int(delay * 1000)} error={exc}",
                flush=True,
            )
            time.sleep(delay)
    print(
        f"[TERRITORY_WORKER] started reconcile_rollback={restored} "
        f"ghost_delta_queue={delta_diagnostics}",
        flush=True,
    )
    while True:
        try:
            now = time.monotonic()
            if now >= next_reconcile_at:
                started = time.perf_counter()
                reports = run.reconcile_active_territory_conflicts(reduce_unlinkable=False)
                print(
                    f"[TERRITORY_WORKER] reconcile conflicts={len(reports)} "
                    f"elapsed_ms={int((time.perf_counter() - started) * 1000)}",
                    flush=True,
                )
                next_reconcile_at = now + reconcile_seconds
            if now >= next_multi_audit_at:
                started = time.perf_counter()
                batch = run.reconcile_active_multi_conflict_engagements(
                    lease_owner=f"territory-worker:{os.getpid()}"
                )
                report = batch["audit"]
                report["metrics"]["elapsed_ms"] = int(
                    (time.perf_counter() - started) * 1000
                )
                report["publication"] = batch["publication"]
                print(
                    "[TERRITORY_MULTI_AUDIT] "
                    f"{json.dumps(compact_multi_audit_report(report), ensure_ascii=False)}",
                    flush=True,
                )
                next_multi_audit_at = now + multi_audit_seconds
            if not process_once():
                time.sleep(idle_seconds)
        except KeyboardInterrupt:
            return
        except Exception as exc:
            if is_database_contention(exc):
                delay = contention_backoff_seconds()
                print(
                    "[TERRITORY_WORKER] database_contended "
                    f"retry_in_ms={int(delay * 1000)} error={exc}",
                    flush=True,
                )
                time.sleep(delay)
                continue
            traceback.print_exc()
            time.sleep(idle_seconds)


if __name__ == "__main__":
    main()
