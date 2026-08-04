import os
import sys
import time
import traceback


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

import run  # noqa: E402


def process_once():
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
    idle_seconds = max(1.0, float(os.environ.get("CHAOS_TERRITORY_WORKER_IDLE_SECONDS", "2")))
    print("[TERRITORY_WORKER] started", flush=True)
    while True:
        try:
            if not process_once():
                time.sleep(idle_seconds)
        except KeyboardInterrupt:
            return
        except Exception:
            traceback.print_exc()
            time.sleep(idle_seconds)


if __name__ == "__main__":
    main()
