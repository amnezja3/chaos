#!/usr/bin/env bash
# Offline tests and read-only inspection. Activation is a separate operator step.
set -euo pipefail
cd "$(dirname "$0")/.."
stage=${1:-preflight}
case "$stage" in preflight|ingest|read|visits|rollback) ;; *) printf 'Expected preflight|ingest|read|visits|rollback\n' >&2; exit 2;; esac
umask 077
ACCEPTANCE_DIR=$(mktemp -d "$HOME/chaos-163-5-acceptance-XXXXXX")
printf 'Reports: %s\n' "$ACCEPTANCE_DIR"
git rev-parse HEAD > "$ACCEPTANCE_DIR/commit.txt"
if [ "$stage" = preflight ]; then
  if ! bash tools/world_local_read_acceptance_163_5.sh > "$ACCEPTANCE_DIR/tests.log" 2>&1; then
    tail -n 60 "$ACCEPTANCE_DIR/tests.log"; exit 1
  fi
  tail -n 6 "$ACCEPTANCE_DIR/tests.log"
  .venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics > "$ACCEPTANCE_DIR/migration-plan.json"
  cat "$ACCEPTANCE_DIR/migration-plan.json"
fi
storage_args=()
runtime_args=()
if [ "$stage" != preflight ]; then
  storage_args+=(--require-visits)
  runtime_args+=(--world-stage "$stage")
fi
if ! .venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics --require-collection "${storage_args[@]}" > "$ACCEPTANCE_DIR/storage.json"; then
  cat "$ACCEPTANCE_DIR/storage.json"; exit 1
fi
cat "$ACCEPTANCE_DIR/storage.json"
if ! .venv/bin/python tools/world_runtime_check.py --routing 1 --worker online "${runtime_args[@]}" > "$ACCEPTANCE_DIR/runtime.json"; then
  cat "$ACCEPTANCE_DIR/runtime.json"
  printf 'STOP: runtime differs from the expected accepted configuration. No automatic changes.\n'
  exit 2
fi
cat "$ACCEPTANCE_DIR/runtime.json"
code=000
for attempt in {1..12}; do
  code=$(curl --silent --show-error --connect-timeout 3 --max-time 10 -o /dev/null -w '%{http_code}' https://chaos.re/launch) || code=000
  printf 'Launch HTTP: %s\n' "$code"
  [ "$code" = 200 ] && break
  sleep 2
done
[ "$code" = 200 ] || exit 1
printf 'PASS: %s checks. No provider requests, database writes, restart or activation by this script. Gameplay acceptance remains separate.\n' "$stage"
