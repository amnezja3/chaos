#!/usr/bin/env bash
# Local fixture tests + read-only production inspection. No activation or probes.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
ACCEPTANCE_DIR=$(mktemp -d "$HOME/chaos-world-acceptance-XXXXXX")
printf 'Reports: %s\n' "$ACCEPTANCE_DIR"
git rev-parse HEAD > "$ACCEPTANCE_DIR/commit.txt"
for pattern in 'test_world_*.py' 'test_poi_*.py'; do
  case "$pattern" in
    test_world*) log="$ACCEPTANCE_DIR/world-tests.log" ;;
    *) log="$ACCEPTANCE_DIR/poi-tests.log" ;;
  esac
  if .venv/bin/python -m unittest discover -s tests -p "$pattern" > "$log" 2>&1; then
    tail -n 4 "$log"
  else
    tail -n 80 "$log"
    exit 1
  fi
done
if ! .venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics > "$ACCEPTANCE_DIR/storage.json"; then
  cat "$ACCEPTANCE_DIR/storage.json"
  exit 1
fi
cat "$ACCEPTANCE_DIR/storage.json"
if ! .venv/bin/python tools/world_runtime_check.py > "$ACCEPTANCE_DIR/runtime.json"; then
  cat "$ACCEPTANCE_DIR/runtime.json"
  printf 'STOP: inspect baseline differences; do not change flags automatically.\n'
  exit 2
fi
cat "$ACCEPTANCE_DIR/runtime.json"
printf 'PASS: fixture tests and read-only baseline. No provider requests, restart or production activation performed.\n'
