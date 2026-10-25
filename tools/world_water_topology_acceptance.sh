#!/usr/bin/env bash
# Explicit one-request evidence capture. No activation, restart or automatic retry.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != '--execute' ) ]]; then
    printf 'Usage: bash tools/world_water_topology_acceptance.sh [--execute]\n' >&2
    exit 2
fi

# Small candidate near Lake Goreckie; full source geometry is requested.
# Published park description confirms islands, not API topology or coverage.
bounds=(16.79 52.26 16.80 52.27)
.venv/bin/python tools/world_region_probe.py --profile inland_water --water-bbox "${bounds[@]}"
if [[ $# -eq 0 ]]; then
    printf 'Plan only. --execute makes at most one MapLark request; no automatic retry.\n'
    exit 0
fi

(
    if [[ -z "${CHAOS_MAPLARK_API_KEY:-}" ]]; then
        read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
        printf '\n'
    fi
    export CHAOS_MAPLARK_API_KEY
    probe_dir=$(mktemp -d "$HOME/chaos-water-topology-XXXXXX")
    printf 'Capture directory: %s\n' "$probe_dir"
    .venv/bin/python tools/world_region_probe.py --db data/poi_cache.sqlite3 \
        --profile inland_water --water-bbox "${bounds[@]}" \
        --output "$probe_dir/capture" --execute --approve-bbox-probe --accept-variable-credit-cost
    # No second network call. Missing topology is evidence, never a retry trigger.
    topology_status=0
    .venv/bin/python tools/world_region_plan.py --layer inland_water --bbox "${bounds[@]}" \
        --body "$probe_dir/capture/body.json" --headers "$probe_dir/capture/headers.json" \
        --require-water-holes > "$probe_dir/topology.json" || topology_status=$?
    cat "$probe_dir/topology.json"
    exit "$topology_status"
)
