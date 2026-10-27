#!/usr/bin/env bash
# Isolated databases and mocked providers; one test uses a local loopback server.
set -euo pipefail
for flag in ${!CHAOS_@}; do unset "$flag"; done
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/tests${PYTHONPATH:+:$PYTHONPATH}"
.venv/bin/python -m unittest \
  test_world_routed_region test_poi_wide_fetch test_poi_world \
  test_world_global_access test_world_routing test_world_shadow \
  test_world_discovery_queue test_poi_infrastructure \
  test_poi_geometry_storage test_world_storage \
  test_world_archive_retention test_world_collection_retention \
  test_world_acceptance_163_5 test_world_capture_inventory test_world_visits_halo test_world_regular_collection \
  test_world_discovery_producer test_world_discovery_worker test_world_worker_heartbeat
