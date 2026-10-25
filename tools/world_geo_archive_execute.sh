#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mode=${1:---plan}
if [[ $# -gt 1 || ( "$mode" != --plan && "$mode" != --execute ) ]]; then
  printf 'Usage: bash tools/world_geo_archive_execute.sh [--plan|--execute]\n' >&2
  exit 2
fi
.venv/bin/python tools/world_geo_archive_once.py
if [[ "$mode" == --plan ]]; then exit 0; fi
.venv/bin/python tools/world_runtime_check.py
for pattern in 'test_world_geo_archive_once.py' 'test_world*budget.py' \
               'test_world_acquisition.py' 'test_world_activation_readiness.py'; do
  .venv/bin/python -m unittest discover -s tests -p "$pattern"
done
(
  if [[ -z "${CHAOS_GEOAPIFY_API_KEY:-}" ]]; then
    read -r -s -p 'Klucz API Geoapify: ' CHAOS_GEOAPIFY_API_KEY
    printf '\n'
  fi
  export CHAOS_GEOAPIFY_API_KEY
  CHAOS_POI_PRIORITY_ENABLED=1 .venv/bin/python tools/world_geo_archive_once.py --execute
)
.venv/bin/python tools/world_activation_readiness.py
.venv/bin/python tools/world_runtime_check.py
printf 'Completed. Inspect archived_observations or saved report; no PM2 changes or automatic retries.\n'
