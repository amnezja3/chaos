#!/usr/bin/env bash
# Read-only production inspection and private local artifacts; no provider calls.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
PYTHONPATH="$PWD/tests${PYTHONPATH:+:$PYTHONPATH}" .venv/bin/python -m unittest \
  test_world_poi_evidence test_world_discovery_sector test_world_region_candidate
EVIDENCE_DIR=$(mktemp -d "$HOME/chaos-poi-evidence-1635-XXXXXX")
.venv/bin/python tools/world_poi_evidence.py --output "$EVIDENCE_DIR/samples" > "$EVIDENCE_DIR/report.json"
.venv/bin/python tools/world_collection_monitor.py > "$EVIDENCE_DIR/collection.json"
cat "$EVIDENCE_DIR/report.json"
printf '\nKatalog dowodow: %s\n' "$EVIDENCE_DIR"
