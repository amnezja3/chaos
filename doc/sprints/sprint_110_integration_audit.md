# Sprint 110 - GhostNetwork Integration Audit

Status: contract/audit only. No runtime change.

## Required Artifacts

Sprint 110 was checked against:

* `doc/overview/clans_machines.md`
* `doc/systems/ghostnetwork/ghostnetwork_architecture.md`
* `doc/history/game_play_180726.md`

Hard rule for Sprint 110-130: every GhostNetwork sprint must first verify
consistency with `clans_machines.md` and `ghostnetwork_architecture.md`. If a
sprint conflicts with those artifacts, the work stops at a decision note and
contract update. The fix must not be hidden as a local code exception.

## Scope Boundary

GhostNetwork is a global world module. It must not become another profile cache,
another territory store, or another map runtime.

Profile may keep only:

* clan/profession identity,
* RSP/LVL effects,
* achievements,
* permanent participation history.

Profile must not keep current GhostNetwork cycle state, active parts, topology,
connections, reservations, or media narrative state.

## Current Sources Of Truth

* Clan/profession: `profile.clan`, `profile.fraction`, future normalized
  `profile.profession`.
* Target identity: `build_operation_target_id(target)` in `run.py`.
* Current target: `profile.aimed_target`.
* Hack action and map selection: `/hack-action`, Victim Picker aim endpoint,
  player target aim endpoint, desktop/terminal app launch on `aimed_target`.
* Operation runtime: `refresh_operations_runtime(...)` and app launch/final
  success paths in `run.py`.
* Territories: `TerritoryStore`, `TerritoryConflictStore`,
  `TerritoryEncirclementResolver`, territory delta publisher.
* Delta feed: existing `GameStateDeltaBus`.
* Media: BlackNet deterministic publisher, Cyberner/mail store/system messages,
  Ghost Hack Radio, Ollama inbox/outbox contracts.

## Clan And Profession Audit

Current onboarding writes faction names such as `Echo Wolnosci`, `VIREX` and
`Siatka Widmo`. The GhostNetwork canon requires stable codes:

* `virex`
* `echo_freedom`
* `phantom_mesh`
* `sentinel_order`

Finding: a future normalizer is required before gameplay decisions depend on
clan identity. Sprint 110 does not change onboarding, but Sprint 111/112 must
avoid scattering `if clan` checks and should provide a single clan/profession
adapter.

Contract:

```text
normalize_ghost_clan(profile) -> clan_code
normalize_ghost_profession(profile) -> profession_code
```

These helpers read existing profile fields but do not mutate profile during
read-only flows.

## Target Aiming Hook

Observed target-setting paths:

* map `/hack-action` when target is selected or action is confirmed;
* Victim Picker aim endpoint;
* player target aim endpoint;
* Territory/Victim utilities that use `build_operation_target_id`;
* desktop/terminal app launch that updates the current `aimed_target`.

Future hook:

```text
ghostnetwork.on_target_aimed(player, target)
```

Rules:

* runs after existing target identity is known;
* does not change `profile.aimed_target`;
* does not start operations;
* does not modify target security;
* does not reveal reservations;
* is best-effort and never blocks target selection.

Recommended integration point: one future adapter around the existing
`aimed_target` write/update paths, not separate logic in map, Victim Picker and
terminal flows.

## Successful Hack Hook

GhostNetwork part emission must happen only after confirmed success, not after
tool launch, operation start, target selection, or visual progress.

Future hook:

```text
ghostnetwork.on_target_hacked(player, target, operation)
```

Candidate boundary: the current success path that confirms target capture or
fully completed action and persists the target/operation result. Operation start
and app launch are too early.

Rules:

* one confirmed success can confirm at most one reservation;
* idempotency key must be based on cycle id, target id and operation/action id;
* retries cannot duplicate a discovered part;
* cancelled, timed out or failed operations do not emit parts.

## Eligible Target Contract

Future helper:

```text
is_ghostnetwork_eligible_target(target) -> bool
```

Eligible:

* stable POI/marker targets with valid latitude and longitude;
* standard hackable objects that can be represented by stable target id;
* targets visible through existing map/Victim Picker flows.

Excluded:

* players and player actors;
* temporary UI-only markers;
* response NPC actors;
* active operation markers;
* incident markers;
* technical duplicate markers;
* invalid or missing coordinates;
* targets without a stable identity.

This helper must be pure and read-only.

## Target Identity Contract

Current base identity: `build_operation_target_id(target)`.

GhostNetwork should create an immutable anchor at reservation/discovery time:

```text
ghost_anchor_id
cycle_id
operation_target_id
lat
lng
source_type
source_id/osm_id if available
label_snapshot
created_at
```

The anchor protects GhostNetwork from later label changes, UI relabeling,
Victim Picker formatting, or map refresh differences.

## Territory Integration

GhostNetwork must listen to territory outcomes, not rescan the whole map.

Relevant current boundaries:

* territory areas rebuilt through the territory delta publisher;
* conflicts updated through `record_territory_conflict_delta`;
* encirclement takeover from Sprint 109.5;
* `territory.encirclement_resolved` as stable ownership source.

Future domain events:

```text
territory.stabilized
territory.contested
territory.released
territory.owner_changed
```

Rules:

* no full territory scan on every request;
* no full profile sync;
* affected parts are recalculated only inside changed territory scope;
* conflict/encirclement must be idempotent.

## Delta Contract

GhostNetwork gets one scope:

```text
ghostnetwork
```

Event fields:

```json
{
  "event_id": "ghostnetwork:cycle:target:event",
  "cycle_id": "ghostnetwork_0001",
  "state_version": 1,
  "event_type": "ghost.part_discovered",
  "entity_id": "ghost_anchor_id",
  "audience_scope": "public|clan|player",
  "payload": {},
  "created_at": "ISO-8601"
}
```

Initial event families:

* `ghost.part_reserved`
* `ghost.part_discovered`
* `ghost.part_visibility_changed`
* `ghost.part_contained`
* `ghost.part_activated`
* `ghost.connection_updated`
* `ghost.cycle_state_changed`

Payloads must not contain full profiles, full territory snapshots or private
operator data outside the selected audience scope.

## Media Bridge Contract

BlackNet, Cyberner, Radio and Ollama must consume prepared facts, not raw
GhostNetwork internals.

Media facts can describe:

* discovered public part;
* hidden/contained part without identity;
* territory containing a part;
* conflict around a part;
* machine progress;
* cycle progress;
* GhostSignal transmission.

Ollama remains a narrative daemon. It receives bounded JSON facts and returns
text/media suggestions. It cannot create parts, change ownership, resolve
conflicts or mutate world state.

## Performance Budget

GhostNetwork must preserve the map optimization direction from recent sprints.

Forbidden in normal runtime:

* `sync_session_profile()` for GhostNetwork polling;
* full `/api/profile` just to update GhostNetwork;
* full territory rebuild for every map refresh;
* media generation inside a player request;
* second polling loop parallel to the delta feed.

Required:

* read-only snapshots;
* delta events;
* affected-scope recalculation;
* recovery per GhostNetwork scope;
* deterministic replay for reservations and part discovery.

## Risks Before Sprint 111

1. Clan names are not yet canonical codes.
2. Multiple target write paths can drift unless wrapped by one adapter.
3. Operation start and hack success are easy to confuse; part emission must use
   the confirmed success boundary only.
4. Territory state is now event-capable, but GhostNetwork must not query it with
   map-heavy flows.
5. Media bridges must never become the source of truth.

## Sprint 110 DoD

* Integration points are identified.
* No runtime behavior was changed.
* `profile` boundary is explicit.
* Target aiming and confirmed hack hooks are specified.
* Eligible target rules are specified.
* Territory event boundaries are specified.
* Delta scope and event schema are specified.
* Media/Ollama boundaries are specified.
* Sprint 110-130 artifact consistency rule is recorded.
