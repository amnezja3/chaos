#!/usr/bin/env bash
# Final grouped checks. Only deploy writes/imports/reloads; no diagnostic API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
stage=${1:-preflight}
case "$stage" in preflight|deploy|post) ;; *) printf 'Use preflight|deploy|post\n' >&2; exit 2;; esac
umask 077
REPORT_DIR=$(mktemp -d "$HOME/chaos-world-completion-XXXXXX")
printf 'Reports: %s\n' "$REPORT_DIR"
git rev-parse HEAD > "$REPORT_DIR/commit.txt"
if [ "$stage" = preflight ]; then
  if ! .venv/bin/python tools/world_completion_tests.py > "$REPORT_DIR/tests.log" 2>&1; then
    tail -n 70 "$REPORT_DIR/tests.log"; exit 1
  fi
  tail -n 6 "$REPORT_DIR/tests.log"
  .venv/bin/python tools/world_land_water_import.py > "$REPORT_DIR/land-water-plan.json"
  cat "$REPORT_DIR/land-water-plan.json"
fi
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics --require-collection --require-visits > "$REPORT_DIR/storage.json"
cat "$REPORT_DIR/storage.json"
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online --world-stage regional --halo 1
if [ "$stage" = deploy ]; then
  # The import makes its own consistent backup before registry/storage writes.
  .venv/bin/python tools/world_land_water_import.py --db data/poi_cache.sqlite3 --apply --backup "$REPORT_DIR/poi_cache.sqlite3" > "$REPORT_DIR/land-water-import.json"
  cat "$REPORT_DIR/land-water-import.json"
  pm2 startOrReload ecosystem.web.config.js --only chaos --env world_maplark_region --update-env
  pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --env regular_halo --update-env
  .venv/bin/python tools/world_runtime_check.py --routing 1 --worker online --world-stage regional --halo 1
fi
.venv/bin/python tools/world_collection_monitor.py > "$REPORT_DIR/collection.json"
cat "$REPORT_DIR/collection.json"
if [ "$stage" != preflight ]; then
  code=000
  for attempt in {1..12}; do
    code=$(curl --silent --show-error --connect-timeout 3 --max-time 10 -o /dev/null -w '%{http_code}' https://chaos.re/launch) || code=000
    printf 'Launch HTTP: %s\n' "$code"
    [ "$code" = 200 ] && break
    sleep 2
  done
  [ "$code" = 200 ] || exit 1
fi
printf 'PASS: %s. No diagnostic provider request. Existing collector may run concurrently. Reports: %s\n' "$stage" "$REPORT_DIR"
