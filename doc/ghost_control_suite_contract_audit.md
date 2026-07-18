# Ghost Control Suite - Sprint 104 Audit

Status: Sprint 104, audit and shared contract.

Scope:

* Victim Picker already exists and stays the first app of the family.
* Territory Control and Operation Control are not implemented in this sprint.
* This document defines where the next apps must connect to the current engine.
* No second territory, operation, security, incident or file runtime is allowed.

## Required Source Artifacts

Before implementing Sprint 105+ read:

* `doc/game_play_180726.md`;
* `doc/incidents_npc_technical_architecture.md`;
* `doc/incidents_npc_gameplay.md`;
* `doc/runtime_slowdown_audit_blacknet.md`;
* this document;
* `run.py`;
* `database.py`;
* `templates/map_template.html`;
* `static/js/terminal.js`.

## Product Family Contract

Ghost Control Suite apps remain normal Googleplex products:

```text
type: pro-system-tool
category: pro-system-tools
family_id: ghost_control_suite
icon_pack: ghost_control
```

The family is presentation metadata only. Googleplex install, inventory, desktop
icons and `/tools` must continue to use the existing app/product flow.

Family members:

* `Victim Picker` - target selection without opening Leaflet;
* `Territory Control` - management of owned territory clusters and captured
  objects;
* `Operation Control` - management of active operations, generated files, risk
  and incidents.

## Territory Cluster Source Of Truth

The current cluster is the existing `player_areas` record stored by
`TerritoryStore`.

Current path:

```text
captured_targets
-> TerritoryStore.build_player_areas()
-> TerritoryStore.rebuild_player_areas()
-> player_areas
-> /api/map/player-areas
```

Current storage:

* `captured_targets` table stores owned captured objects with full target JSON;
* `player_areas` table stores generated area records;
* `TerritoryStore.list_player_areas()` returns area rows with `id`,
  `owner_username`, `vertices`, centroid, area size, edge distance and status.

Stable cluster id:

```text
player_areas.id
```

Important lifecycle rule:

* a cluster can exist only after at least three valid stationary captured
  targets form a valid territory polygon;
* one or two captured targets are not a cluster;
* loose captured targets may be displayed later as `alone`, but must not be
  promoted into fake clusters.

Territory Control must consume this model. It must not create a second cluster
model or infer clusters from frontend marker order.

## Pillar And Inner Contract

Current builder stores only hull vertices in `player_areas.vertices`.

Canonical rule:

* `pillar` - captured target whose normalized coordinate matches one of
  `cluster.vertices`;
* `inner` - captured target owned by the same player, stationary, inside the
  polygon, but not one of the hull vertices;
* `alone` - captured target not assigned to any active cluster.

Future shared helper:

```text
resolve_territory_node_role(cluster, target)
```

The helper must be backend-side and coordinate based. The frontend must not
decide role from display order, icon shape or CSS class.

Inner target lifecycle after cluster collapse:

* inner objects remain captured targets;
* they do not automatically become pillars;
* they are reassigned only by the next canonical territory rebuild.

## Threat State Contract

Backend computes one canonical cluster threat state:

```text
neutral
collision
attacked
```

Priority:

```text
attacked > collision > neutral
```

Meaning:

* `neutral` - no active conflict touches the cluster;
* `collision` - this cluster intersects another active area, but no owned
  pillar is currently captured, lost or actively contested;
* `attacked` - active conflict includes an owned pillar, captured/lost pillar
  status or active contest against the cluster.

Current data sources:

* `detect_territory_conflicts(...)`;
* `territory_conflict_store`;
* `get_active_conflicts_for_player(username)`;
* `enrich_conflict_payload(conflict)`;
* `find_contested_targets_for_player(username, areas)`;
* `/api/map/player-areas`.

CSS may color a card green/orange/red, but it must not determine the state.

## Captured Object Security

Current map paths:

```text
POST /target-security-status
POST /secure-action
POST /secure-preset
```

Current helpers:

* `find_owned_hacked_target(profile, username, lat, lng)`;
* `save_owned_hacked_security(username, lat, lng, security)`;
* `build_security_preset(current_security, preset)`.

Canonical presets:

```text
open
low
regular
secure
all
```

Territory Control must use the same preset semantics:

* `open` - all boolean security off and numeric security at low/zero level;
* `low` - minimal security;
* `regular` - mid security;
* `secure` - high security;
* `all` - maximum security.

Security changes must persist through existing captured target/profile/store
paths. They must not be temporary frontend toggles.

## Abandon Captured Object

Canonical abandon must be backend-side.

Required lifecycle:

```text
remove captured target
-> remove/sync profile hacked entry
-> clear aimed_target if it points to the abandoned object
-> rebuild player areas
-> detect territory conflicts
-> publish territory/map deltas
-> return whether the previous cluster still exists
```

Existing low-level primitive:

```text
TerritoryStore.remove_captured_target(username, lat, lng, label=None)
```

Sprint 105 must expose abandon through a controlled endpoint. It must not delete
only a frontend row.

## Operation Source Of Truth

Current operation path:

```text
tool launch / map action / desktop app
-> create_operations_for_app_action()
-> build_operation_instance()
-> profile.operations
-> refresh_operations_runtime()
-> /api/operations
```

Operation summary endpoint:

```text
GET /api/operations?summary=1
```

Cancel endpoint:

```text
POST /api/operations/cancel
```

Canonical cancel helper:

```text
cancel_profile_operation(profile, operation_id, cancelled_by=...)
```

Operation Control must use these paths. Group cancel may call the same cancel
path per operation or a future backend group endpoint that still uses the same
helper.

## Operation Family Mapping

Operation family must not be inferred from Polish display labels.

Inputs:

* `operation_type`;
* `map_action_id`;
* `resource_types`;
* generated file category.

Recommended v0 mapping:

| family | operation/resource indicators |
| --- | --- |
| `gps` | `vehicle_tracking`, `generic_trace`, `gps_logs`, `location_history`, `gps` |
| `device` | `device_tracking`, `device_logs`, `device` |
| `camera` | `camera_stream`, `camera_shutdown`, `camera_dump`, `video_material`, `camera` |
| `audio` | `microphone_sniffer`, `audio_interference`, `audio_transcript`, `audio` |
| `network` | `wifi_scanner`, `persistent_sniffer`, `wifi_networks`, `hotspot_database`, `network` |
| `atm` | `atm_log_extraction`, `atm_dump`, `atm` |
| `vehicle` | `vehicle_ecu`, `vehicle_diagnostics`, `vehicle` |
| `implant` | `persistent_sniffer`, `implant_timer`, long-running installed sniffer operations |
| `recon` | `generic_trace`, `internal_recon_state`, `system` |
| `other` | fallback only |

Sprint 107 should centralize this as a helper instead of duplicating mappings in
JS and Python.

## Generated Files Mapping

Operation finalizers already write files through `append_runtime_file_if_space`.

Current examples:

* `vehicle_tracking` -> `/data/gps`, `files.gps`;
* `device_tracking` -> `/data/device` or `/data/personal`;
* `camera_stream` -> `/data/camera`, fragments;
* `atm_log_extraction` -> `/data/atm` and `/data/financial`;
* `persistent_sniffer` -> credentials, financial, device and system artifacts;
* `wifi_scanner` -> `/data/network`;
* `audio_interference` -> `/data/audio`;
* `vehicle_ecu` -> `/data/vehicle`;
* `generic_trace` -> `/data/gps` or recon/system style artifacts.

Operation Control should show generated file summaries from
`operation.resource_buffer.files`, `operation_output_size_mb(operation)` and the
File Manager inventory. It must not scan the whole profile when summary data is
enough.

## Operation To Incident Link

Response Network already attaches incident/risk state to operations.

Relevant fields:

* `operation_risk_meter`;
* `risk_state`;
* `incident_id`;
* warning state;
* operation status and cancel state.

Public incident source:

```text
GET /api/map/incidents
```

NPC capsules source:

```text
GET /api/map/incident-npc-capsules
```

Operation Control may show incident state, but must not expose private suspect
data beyond what the existing operation owner already sees.

## Shared Icon Contract

The next apps should use one icon dictionary:

```text
GHOST_CONTROL_ICONS
```

Common:

* `back`
* `refresh`
* `map`
* `teleport`
* `distance`
* `bike`
* `warning`
* `incident`
* `security`
* `abandon`
* `cancel`
* `cancelGroup`
* `timer`
* `file`
* `loading`
* `error`

Territory:

* `territory`
* `cluster`
* `pillar`
* `inner`
* `collision`
* `attacked`
* `neutral`
* `alone`

Operations:

* `operations`
* `recon`
* `gps`
* `device`
* `camera`
* `audio`
* `network`
* `atm`
* `vehicle`
* `implant`
* `other`

Use `currentColor` icons so threat/risk color comes from state classes.

## Planned Endpoint Shape

Sprint 104 does not implement endpoints. Sprint 105+ should prefer these shapes:

```text
GET  /api/ghost-control/territory
POST /api/ghost-control/territory/security
POST /api/ghost-control/territory/security-preset
POST /api/ghost-control/territory/abandon

GET  /api/ghost-control/operations
POST /api/ghost-control/operations/cancel
POST /api/ghost-control/operations/cancel-group
```

Rules:

* endpoints return light read models;
* snapshots remain recovery;
* no `sync_session_profile()` for read-only lists unless a write path needs it;
* write endpoints reuse existing profile/store helpers;
* deltas and current delta bus remain the only live update channel.

## Test Plan For Sprint 105+

Territory Control:

* cluster id comes from `player_areas.id`;
* two captured pillars do not create a cluster;
* third valid pillar creates a cluster after rebuild;
* pillar/inner role is backend-derived;
* `threat_state` priority is `attacked > collision > neutral`;
* every security preset matches map behavior;
* abandon clears aimed target when needed;
* abandon rebuilds territory and conflicts.

Operation Control:

* operation families do not depend on display labels;
* operation summaries match `/api/operations?summary=1`;
* cancel uses `cancel_profile_operation`;
* group cancel is idempotent;
* generated output summary matches `resource_buffer.files`;
* incident link follows operation `incident_id`.

Performance:

* read endpoints do not call full map boot;
* read endpoints do not render Leaflet/Folium;
* snapshot is start/recovery, not an aggressive poller.

## Sprint 104 DoD Check

Confirmed:

* no second territory system is needed;
* no second captured-object list is needed;
* no new security model is needed;
* no second incident system is needed;
* no alternative operation cancellation mechanism is needed;
* Sprint 105 can build on existing sources of truth with light read models.

Open for Sprint 105:

* implement explicit territory read model;
* expose `node_role` and `threat_state`;
* implement controlled abandon endpoint;
* add `Territory Control` Googleplex product.
