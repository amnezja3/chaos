#!/usr/bin/env bash
# Grouped fixture tests + additive preparation. Never enables HTTP or workers.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mode=${1:---check}
if [[ $# -gt 1 || ( "$mode" != --check && "$mode" != --prepare ) ]]; then
  printf 'Usage: bash tools/world_collection_acceptance.sh [--check|--prepare]\n' >&2
  exit 2
fi
# Existing baseline requires the discovery worker stopped. Never change it here.
.venv/bin/python tools/world_runtime_check.py
bash tools/world_vps_acceptance.sh
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics
if [[ "$mode" == --check ]]; then
  printf 'PASS: tests and migration dry-run. No activation or production migration.\n'
  exit 0
fi
mkdir -p "$HOME/chaos-backups"
COLLECTION_BACKUP=$(mktemp -d "$HOME/chaos-backups/collection-XXXXXXXX")
git rev-parse HEAD > "$COLLECTION_BACKUP/commit.txt"
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics --apply --backup "$COLLECTION_BACKUP/poi_cache.sqlite3"
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics --require-collection
printf 'PASS: schema prepared. Backup: %s\nNo worker started, no provider request, no environment change.\n' "$COLLECTION_BACKUP"
