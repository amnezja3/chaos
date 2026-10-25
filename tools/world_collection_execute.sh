#!/usr/bin/env bash
# One operator-triggered acceptance, not a persistent PM2/environment change.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if [[ $# -ne 1 || "$1" != --execute ]]; then
  .venv/bin/python tools/world_collection_prepare.py
  exit 0
fi
.venv/bin/python tools/world_runtime_check.py
.venv/bin/python tools/world_collection_prepare.py --apply
(
  if [[ -z "${CHAOS_MAPLARK_API_KEY:-}" ]]; then
    read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
    printf '\n'
    export CHAOS_MAPLARK_API_KEY
  fi
  export CHAOS_POI_DISCOVERY_WORKER_ENABLED=1
  export CHAOS_POI_PRIORITY_ENABLED=1
  export CHAOS_POI_ROUTING_ENABLED=0
  export CHAOS_MAPLARK_ACCEPT_VARIABLE_COST=1
  .venv/bin/python tools/world_collection_run.py
)
.venv/bin/python tools/world_discovery_worker.py --permit data/collection-sector-2036-5153-v1/permit.json
.venv/bin/python tools/world_release_check.py --require-metrics --require-collection
.venv/bin/python tools/world_runtime_check.py
