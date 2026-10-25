#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mode=${1:---check}
if [[ $# -gt 1 || ( "$mode" != --check && "$mode" != --execute ) ]]; then
  printf 'Usage: bash tools/world_bounded_collector_rollout.sh [--check|--execute]\n' >&2
  exit 2
fi
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker stopped
for pattern in 'test_world_bounded_collector.py' 'test_world_collection_prepare.py' \
               'test_world_discovery*.py' 'test_world_release_package.py'; do
  .venv/bin/python -m unittest discover -s tests -p "$pattern"
done
.venv/bin/python tools/world_collection_prepare.py --bounded
if [[ "$mode" == --check ]]; then exit 0; fi
# Exclusive backup + immutable scopes/permit. Never replaces previous runs.
.venv/bin/python tools/world_collection_prepare.py --bounded --apply
.venv/bin/python tools/world_collector_start.py
online=0
for attempt in {1..5}; do
  if .venv/bin/python tools/world_runtime_check.py --routing 1 --worker online; then online=1; break; fi
  sleep 1
done
if [[ "$online" != 1 ]]; then
  printf 'Worker did not become ready. Inspect its logs; do not delete the permit or reset budgets.\n' >&2
  exit 1
fi
sleep 2
pm2 logs chaos-world-discovery-worker --lines 12 --nostream
printf 'Bounded collector started. Confirm a new idle/committed log before pm2 save. Permit expires in 24h; no automatic renewal.\n'
