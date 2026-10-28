#!/usr/bin/env bash
# Explicit one-request acceptance; no restart, policy change or automatic retry.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
diagnostic_args=()
case "${1:-}" in
  '') ;;
  --diagnostic-v2) diagnostic_args+=(--diagnostic-v2) ;;
  *) printf 'Expected no argument or --diagnostic-v2\n' >&2; exit 2 ;;
esac
.venv/bin/python -m unittest discover -s tests -p test_world_paris_region_acceptance.py
.venv/bin/python tools/world_paris_region_acceptance.py "${diagnostic_args[@]}"
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
PARIS_BACKUP=$(mktemp -d "$HOME/chaos-paris-region-1635-XXXXXX")
printf 'Backup directory: %s\n' "$PARIS_BACKUP"
if [ "${1:-}" = --diagnostic-v2 ]; then
  printf 'Response diagnostics: %s/poi_cache.sqlite3.diagnostics\n' "$PARIS_BACKUP"
fi
.venv/bin/python tools/world_paris_region_acceptance.py \
  --backup "$PARIS_BACKUP/poi_cache.sqlite3" \
  --execute --accept-variable-credit-cost "${diagnostic_args[@]}"
