#!/usr/bin/env bash
# Explicit one-request acceptance; no restart, policy change or automatic retry.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
.venv/bin/python -m unittest discover -s tests -p test_world_paris_region_acceptance.py
.venv/bin/python tools/world_paris_region_acceptance.py
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
PARIS_BACKUP=$(mktemp -d "$HOME/chaos-paris-region-1635-XXXXXX")
printf 'Backup directory: %s\n' "$PARIS_BACKUP"
.venv/bin/python tools/world_paris_region_acceptance.py \
  --backup "$PARIS_BACKUP/poi_cache.sqlite3" \
  --execute --accept-variable-credit-cost
