"""Read-only GhostNetwork audit probe for the configured local runtime."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from ghostnetwork import GhostNetworkService


def main():
    service = GhostNetworkService()
    cycle = service.get_active_cycle()
    snapshot = (
        service.repository.build_internal_snapshot(cycle["cycle_id"])
        if cycle else {}
    )
    payload = {
        "drops_enabled": config.GHOSTNETWORK_DROPS_ENABLED,
        "drop_chance": config.GHOSTNETWORK_DROP_CHANCE,
        "reservation_ttl_seconds": config.GHOSTNETWORK_RESERVATION_TTL_SECONDS,
        "cycle": cycle,
        "parts_summary": (
            service.cycles.get_parts_summary(cycle["cycle_id"])
            if cycle else None
        ),
        "parts_count": len(snapshot.get("parts", [])),
        "active_reservations": len(snapshot.get("active_reservations", [])),
        "health": service.health_check(),
        "runtime_readiness": service.get_runtime_readiness(),
    }
    print(json.dumps(payload, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
