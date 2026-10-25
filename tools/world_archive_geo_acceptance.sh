#!/usr/bin/env bash
# Grouped offline verification and read-only production readiness. No API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if [[ $# -ne 0 ]]; then
  printf 'Usage: bash tools/world_archive_geo_acceptance.sh\n' >&2
  exit 2
fi
.venv/bin/python tools/world_runtime_check.py
for pattern in 'test_world*retention.py' 'test_world_activation_readiness.py' \
               'test_world_discovery_geoapify.py' 'test_world_routing.py' \
               'test_world_discovery_sector.py'; do
  .venv/bin/python -m unittest discover -s tests -p "$pattern"
done
.venv/bin/python tools/world_activation_readiness.py --db data/poi_cache.sqlite3 --retention-seconds 604800
.venv/bin/python tools/world_runtime_check.py
printf 'PASS: offline checks and read-only readiness report. No activation, migration or API calls.\n'
