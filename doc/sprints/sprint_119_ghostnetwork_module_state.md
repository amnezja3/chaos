# Sprint 119 - GhostNetwork module state

## Cel

Sprint 119 domyka kanoniczne strategiczne stany czesci GhostNetwork.
Warstwa nie tworzy nowego magazynu stanu. Czyta istniejace rekordy
`ghost_parts` i na ich podstawie rozstrzyga, czy modul jest neutralny,
blokowany albo aktywny.

## Zrodlo prawdy

Zrodlem prawdy pozostaja:

* `ghost_parts.status`,
* `ghost_parts.conflict_state`,
* pola terytorium zapisane przez Sprint 118,
* eventy lifecycle z `ghost_part_events`.

`GhostModuleStateService` jest read-modelem i warstwa agregacji. Nie zmienia
geometrii, wlasnosci terytoriow ani zasad konfliktu.

## Kanoniczne stany

| status czesci | module_state | ability_enabled |
| --- | --- | --- |
| `public` | `neutral` | false |
| `contained` | `blocked` | false |
| `active` | `active` | true |

Stany `pooled`, `reserved` i `consumed` nie sa strategicznymi stanami modulu.
Nie dostaja dodatkowych nazw typu `owned`, `captured` albo `secured`.

## Konflikt

Konflikt pozostaje nakladka:

```text
module_state = stan bazowy lub frozen_status
conflict_state = contested
```

Nie istnieje `module_state = contested`.

## API domenowe

Dodano `GhostModuleStateService` z metodami:

* `resolve_part_module_state(part)`,
* `resolve_part_viewer_relation(part, viewer)`,
* `resolve_cycle_module_states(cycle_id)`,
* `resolve_machine_progress(cycle_id, machine_code)`,
* `resolve_clan_machine_progress(cycle_id, clan_code)`,
* `resolve_cycle_progress(cycle_id)`,
* `record_machine_progress_if_changed(cycle_id, machine_code)`,
* `build_cluster_ghost_component_contract(cycle_id, territory_id, viewer)`,
* `get_modules_status_report(cycle_id, include_parts=False)`.

`GhostNetworkService` wystawia wrappery do tych metod, zeby przyszle sprinty
korzystaly z jednego wejscia domenowego.

## Progres maszyn

Kazda maszyna liczy 5 czesci:

```text
progress_percent = active_parts / 5 * 100
machine_online = active_parts == 5
```

Po realnej zmianie agregatu zapisywany jest event:

* `ghost.machine_progress_changed`,
* `ghost.machine_online`,
* `ghost.machine_offline`.

Eventy sa idempotentne przez fingerprint agregatu i `dedupe_key`.

## Progres cyklu

Cykl jest gotowy do przyszlej transmisji dopiero gdy:

```text
network_ready = parts_active == 20
```

Sprint 119 nie wykonuje transmisji i nie nadaje supermocy.

## Territory Control

Dodano wewnetrzny kontrakt klastra:

```text
ghost_components.total
ghost_components.neutral
ghost_components.blocked
ghost_components.active
ghost_components.contested
contains_own_clan_part
contains_foreign_clan_part
contains_active_part
contains_blocked_part
contains_ghost_part
ghost_anchor_protected
```

`ghost_anchor_protected` chroni komponent jako kotwice GhostNetwork. Nie blokuje
automatycznie rozpuszczania player area.

## Poza zakresem

* filtrowanie widocznosci dla gracza,
* markery mapy,
* linie i graf komponentow,
* supermoce,
* nagrody,
* BlackNet,
* Cyberner,
* Radio,
* transmisja GhostSignalu.

## Walidacja

Dodano `tests.test_ghostnetwork_module_state`, ktory sprawdza:

* `neutral`, `blocked`, `active`,
* aktywny i blokowany modul podczas konfliktu,
* relacje widza,
* wlaczanie i wylaczanie maszyny przy 5/5 oraz 4/5,
* `network_ready`,
* flagi klastra i ochrone kotwicy,
* wrappery `GhostNetworkService`.

## Spojnosc z artefaktami

Potwierdzono zgodnosc z:

* `doc/overview/clans_machines.md`,
* `doc/systems/ghostnetwork/ghostnetwork_architecture.md`,
* Sprintami 110-118 w `doc/history/game_play_180726.md`.
