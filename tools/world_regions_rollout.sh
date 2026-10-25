#!/usr/bin/env bash
# Offline regression/migration first. Only --execute changes collector runtime.
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:---check}
case "$mode" in --check|--execute) ;; *) echo 'Use --check or --execute'; exit 2;; esac
for pattern in test_world_discovery\*.py test_world_bounded_collector.py test_world_collection_prepare.py; do
  .venv/bin/python -m unittest discover -s tests -p "$pattern"
done
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs
.venv/bin/python tools/world_collection_prepare.py --bounded --cell 2036 5153
if [ "$mode" = --check ]; then
  echo 'Checks complete. No production writes or provider calls; existing worker unchanged.'
  exit 0
fi
umask 077
backup_dir=$(mktemp -d "$HOME/chaos-backups/163-regions-XXXXXX")
pm2 stop chaos-world-discovery-worker
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker stopped
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --apply --backup "$backup_dir/poi_cache.sqlite3"
.venv/bin/python tools/world_collection_prepare.py --bounded --cell 2036 5153 --apply
.venv/bin/python tools/world_collector_start.py --regions
sleep 2
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online
pm2 logs chaos-world-discovery-worker --lines 12 --nostream
echo 'Confirm a fresh idle/committed cycle, then pm2 save. Existing sector only; no automatic permit renewal.'
