#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:---check}
case "$mode" in --check|--execute) ;; *) echo 'Use --check or --execute'; exit 2;; esac
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi_providers.py'
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics
.venv/bin/python tools/world_regular_setup.py
if [ "$mode" = --check ]; then
  echo 'Local checks complete; no production writes or provider requests.'
  exit 0
fi
umask 077
mkdir -p "$HOME/chaos-backups"
backup_dir=$(mktemp -d "$HOME/chaos-backups/163-regular-XXXXXX")
git rev-parse HEAD > "$backup_dir/commit"
pm2 stop chaos-world-discovery-worker
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker stopped
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics --apply --backup "$backup_dir/poi_cache.sqlite3"
.venv/bin/python tools/world_regular_setup.py --apply
started=$(.venv/bin/python -c 'import time; print(time.time())')
.venv/bin/python tools/world_collector_start.py --regular --prompt-secrets
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-monitor
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online
.venv/bin/python tools/world_collection_monitor.py --since "$started"
curl --fail --silent --show-error --connect-timeout 3 --max-time 10 -o /dev/null -w 'Launch HTTP: %{http_code}\n' https://chaos.re/launch
pm2 logs chaos-world-discovery-worker --lines 12 --nostream
printf 'Backup: %s\n' "$backup_dir"
echo 'Review the fresh cycle and provider result, then pm2 save. Web has not been reloaded.'
