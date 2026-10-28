#!/usr/bin/env bash
# One independent radius response and offline comparison; no scanner changes.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
PARENT_CAPTURE=${1:?Pass the existing POI bbox capture directory}
PYTHONPATH="$PWD/tests${PYTHONPATH:+:$PYTHONPATH}" .venv/bin/python -m unittest test_world_poi_radius_compare test_world_region_probe test_world_water_topology_probe
.venv/bin/python tools/world_poi_radius_compare.py --parent "$PARENT_CAPTURE"
.venv/bin/python tools/world_region_probe.py --profile poi --poi-radius
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY CHAOS_POI_PRIORITY_ENABLED=1
trap 'unset CHAOS_MAPLARK_API_KEY' EXIT
RADIUS_CAPTURE=$(mktemp -d "$HOME/chaos-poi-radius-1635-XXXXXX")
.venv/bin/python tools/world_region_probe.py --profile poi --poi-radius \
  --output "$RADIUS_CAPTURE/capture" --execute --approve-bbox-probe --accept-variable-credit-cost
.venv/bin/python tools/world_poi_radius_compare.py --parent "$PARENT_CAPTURE" --radius "$RADIUS_CAPTURE/capture" > "$RADIUS_CAPTURE/comparison.json"
cat "$RADIUS_CAPTURE/comparison.json"
printf '\nKatalog: %s\n' "$RADIUS_CAPTURE"
