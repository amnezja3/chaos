# Sprint 117 - GhostNetwork: lifecycle czesci i zdarzenia domenowe

## Zakres wdrozony

Sprint 117 przeniosl cykl zycia czesci GhostNetwork do jawnego serwisu domenowego.
Repozytorium pozostaje warstwa zapisu, ale reguly przejsc, blokady terminalne,
overlay konfliktu i idempotencja zdarzen sa obslugiwane przez jeden kontrakt.

Wdrozone elementy:

* `GhostPartLifecycleService`;
* przejscia `reserve_part`, `release_reservation`, `discover_part`,
  `contain_part`, `activate_part`, `reveal_part`, `freeze_for_conflict`,
  `resolve_after_conflict`, `deactivate_part`, `consume_part`;
* pomocnicze/adminowe `migrate_anchor` i `replay_part_history`;
* rozdzielenie bazowego `status` od `conflict_state`;
* overlay konfliktu przez `conflict_state=contested`, `frozen_status`,
  `conflict_id` i `contested_at`;
* terminalny status `consumed`;
* nowe pola czasu lifecycle: `contained_at`, `revealed_at`, `contested_at`,
  `conflict_resolved_at`, `consumed_at`, `last_activated_at`,
  `last_deactivated_at`;
* trwaly `consumed_signal_id`;
* `territory_state_version`;
* `patch_part_lifecycle(...)` jako transakcyjny zapis stanu i eventu;
* idempotencja przez `dedupe_key`;
* health checki dla niespojnych stanow lifecycle;
* testy regresyjne lifecycle.

## Status i konflikt

Kanoniczne statusy czesci:

```text
pooled
reserved
public
contained
active
consumed
```

`contested` nie jest juz normalnym statusem. Konflikt jest nakladka:

```text
conflict_state = none | contested
```

Dzieki temu czesc moze pozostac `active` albo `contained`, a jednoczesnie byc
zamrozona w konflikcie. Rozwiazanie konfliktu przywraca bazowy stan bez
zgadywania.

## Zdarzenia domenowe

Nowe przejscia zapisują eventy:

```text
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_contested
ghost.part_conflict_resolved
ghost.part_anchor_migrated
ghost.part_consumed
```

Istniejace eventy rezerwacji i odkrycia pozostaja kompatybilne z replayem.

Payload lifecycle zawiera:

```text
previous_status
status
previous_conflict_state
conflict_state
player_id
player_clan
territory_id
territory_owner_id
territory_clan
reason
source_event_id
source_system
operation_id
conflict_id
previous_owner
new_owner
```

Repozytorium dopisuje `event_id`, `state_version` i `dedupe_key`.

## Reguly bezpieczenstwa

Zablokowano niedozwolone przejscia, m.in.:

* `pooled -> active`;
* `pooled -> contained`;
* `active -> pooled`;
* `contained -> reserved`;
* `consumed -> public`;
* `consumed -> active`;
* konflikt na czesci `pooled`, `reserved` albo `consumed`;
* konsumpcje czesci bez zapisanego `signal_id`.

`activated_at` jest pierwszym momentem aktywacji i nie jest nadpisywany.
Kolejne aktywacje zapisują `last_activated_at`.

## Spojnosc z artefaktami

Potwierdzono zgodnosc z:

* `doc/overview/clans_machines.md`;
* `doc/systems/ghostnetwork/ghostnetwork_architecture.md`;
* sprintami 110-116.

GhostNetwork nadal pozostaje globalnym modulem swiata. Stan czesci nie trafia
do profilu gracza, a lifecycle nie tworzy wlasnej geometrii terytoriow.

## Poza zakresem

Nadal nie wdrozono:

* integracji lifecycle z terytoriami;
* markerow czesci na mapie;
* widocznosci odbiorcow;
* linii topologii;
* delt GhostNetwork;
* supermocy;
* transmisji GhostSignalu;
* mediow BlackNet/Cyberner/Radio dla czesci.

## Walidacja

Uruchomiono:

```text
python -m py_compile ghostnetwork\enums.py ghostnetwork\errors.py ghostnetwork\repository.py ghostnetwork\lifecycle.py ghostnetwork\service.py
python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_topology tests.test_ghostnetwork_reservations tests.test_ghostnetwork_discovery tests.test_ghostnetwork_lifecycle
```

Wynik:

```text
OK - 60 testow GhostNetwork
```
