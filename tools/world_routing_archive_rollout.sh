#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mode=${1:---check}
if [[ $# -gt 1 || ( "$mode" != --check && "$mode" != --execute ) ]]; then
  printf 'Usage: bash tools/world_routing_archive_rollout.sh [--check|--execute]\n' >&2
  exit 2
fi
.venv/bin/python tools/world_runtime_check.py --routing 0
for pattern in 'test_world_saved_retention.py' 'test_world_routing.py' \
               'test_world_release_package.py' 'test_world_activation_readiness.py'; do
  .venv/bin/python -m unittest discover -s tests -p "$pattern"
done
.venv/bin/python tools/world_activation_readiness.py --require-initial-route
.venv/bin/python tools/world_maplark_retain.py
if [[ "$mode" == --check ]]; then exit 0; fi
mkdir -p "$HOME/chaos-backups"
ROLLOUT_BACKUP=$(mktemp -d "$HOME/chaos-backups/routing-archive-XXXXXXXX")
git rev-parse HEAD > "$ROLLOUT_BACKUP/commit.txt"
.venv/bin/python tools/world_maplark_retain.py --apply --backup "$ROLLOUT_BACKUP/poi_cache.sqlite3"
# Recheck immediately before web reload; no granting scopes or editing saved routes.
.venv/bin/python tools/world_activation_readiness.py --require-initial-route
pm2 startOrReload ecosystem.web.config.js --only chaos --env routing --update-env
.venv/bin/python tools/world_runtime_check.py --routing 1
launch_ok=0
for attempt in {1..15}; do
  code=$(curl -sS --connect-timeout 3 --max-time 5 -o /dev/null -w '%{http_code}' https://chaos.re/launch) || code=000
  printf 'Launch HTTP: %s\n' "$code"
  if [[ "$code" == 200 ]]; then launch_ok=1; break; fi
  sleep 2
done
if [[ "$launch_ok" != 1 ]]; then
  printf 'Launch check failed. Roll back with --env baseline; do not pm2 save.\n' >&2
  exit 1
fi
printf 'Backup: %s\nNow verify one gameplay scan, inspect poi_route logs, then pm2 save.\n' "$ROLLOUT_BACKUP"
