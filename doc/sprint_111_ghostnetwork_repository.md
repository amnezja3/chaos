# Sprint 111 - GhostNetwork repository foundation

Status: implemented as storage/domain foundation only.

## Artifacts checked

Sprint 111 was checked against:

* `doc/clans_machines.md`
* `doc/ghostnetwork_architecture.md`
* `doc/sprint_110_integration_audit.md`
* `doc/game_play_180726.md`

Consistency decision: implementation follows the GhostNetwork rule that the
module is global world state, not a profile cache, map runtime or media system.

## Implemented

Created isolated package:

```text
ghostnetwork/
├── __init__.py
├── contracts.py
├── enums.py
├── errors.py
├── events.py
├── models.py
├── repository.py
├── service.py
└── visibility.py
```

`GhostNetworkRepository` stores:

* `ghost_cycles`
* `ghost_parts`
* `ghost_part_reservations`
* `ghost_connections`
* `ghost_part_events`
* `ghost_signals`
* `ghost_contributions`
* `ghost_reward_ledger`
* `ghost_clan_reputation`
* `ghost_narrative_outbox`

The repository provides:

* explicit `transaction()` context;
* cycle creation/update/locking/listing;
* part creation/update/listing/target lookup;
* reservation creation/commit/release/expiry;
* connection creation with basic integrity checks;
* append-only event log with `dedupe_key`;
* monotonic `state_version`;
* internal recovery snapshot;
* health check.

`GhostNetworkService` provides the Sprint 111 entry point:

* `get_active_cycle()`
* `get_state_version()`
* `get_snapshot_for_viewer(viewer)`
* `health_check()`

Future hooks are explicit placeholders:

* `on_target_aimed()`
* `on_target_hacked()`
* `on_territory_event()`
* `resolve_part_state()`
* `attempt_transmission()`

## Deliberately not implemented

Sprint 111 does not implement:

* clan/machine/part catalog;
* automatic creation of 20 parts;
* drops;
* map endpoint;
* visibility projections for players;
* territory integration;
* topology validation beyond basic connection safety;
* media bridge;
* superpowers;
* transmission;
* profile writes.

## Safety notes

The package does not call `sync_session_profile()`, does not read full profiles,
does not rebuild map or territory layers and does not publish to
`GameStateDeltaBus` yet.

`profile` remains outside the active GhostNetwork state. It may later hold only
identity and permanent rewards/participation effects.

## Validation

Executed:

```text
python -m unittest tests.test_ghostnetwork_repository
python -m py_compile ghostnetwork\__init__.py ghostnetwork\contracts.py ghostnetwork\enums.py ghostnetwork\errors.py ghostnetwork\events.py ghostnetwork\models.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\visibility.py
```

Result: OK.
