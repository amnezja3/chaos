#!/usr/bin/env bash
# Isolated regression tests + read-only production inspection; no provider HTTP.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
REPORT_DIR=$(mktemp -d "$HOME/chaos-maplark-region-acceptance-XXXXXX")
git rev-parse HEAD > "$REPORT_DIR/commit.txt"
for suite in test_world_maplark_region.py test_world_paris_region_acceptance.py test_world_poi_radius_compare.py test_world_shadow.py test_world_read.py test_world_routing.py; do
  .venv/bin/python -m unittest discover -s tests -p "$suite"
done
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics --require-collection > "$REPORT_DIR/storage.json"
cat "$REPORT_DIR/storage.json"
printf '\nOffline checks complete. No activation or provider requests. Reports: %s\n' "$REPORT_DIR"
