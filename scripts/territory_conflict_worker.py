import os
import json
import sys
import time
import traceback


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import run  # noqa: E402


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
    settle_seconds = max(
        1.0,
        float(os.environ.get("CHAOS_TERRITORY_WORKER_SETTLE_SECONDS", "3")),
    )
    candidates = run.territory_conflict_store.list_rebuild_candidates(
        limit=1,
        min_age_seconds=settle_seconds,
    )
    if not candidates:
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
    restored = run.restore_territory_reconcile_targets()
    print(
        f"[TERRITORY_WORKER] started reconcile_rollback={restored}",
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
        except Exception:
            traceback.print_exc()
            time.sleep(idle_seconds)


if __name__ == "__main__":
    main()
