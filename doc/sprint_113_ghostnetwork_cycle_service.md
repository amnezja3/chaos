# Sprint 113 - GhostNetwork Cycle Service

## Zakres wdrozenia

Sprint 113 uruchomil pierwszy domenowy lifecycle cyklu GhostNetwork bez
wlaczania dropow, mapy, terytoriow ani transmisji.

Wdrozone elementy:

* `GhostCycleService`;
* `ensure_active_ghostnetwork_cycle()`;
* atomowe utworzenie cyklu i dokladnie 20 czesci;
* zapis `catalog_version` i `catalog_checksum`;
* zapis `source_version` i `next_version` na cyklu;
* `catalog_version` na instancjach `ghost_parts`;
* statusy i blokady przejsc cyklu;
* agregat `parts_summary`;
* diagnostyka cyklu;
* rozszerzony `health_check()`.

## Lifecycle cyklu

Dozwolone przejscia domenowe:

```text
preparing -> active -> transmitting -> stabilizing -> closed
```

Awaryjnie dozwolone:

```text
preparing -> closed
```

Serwis blokuje:

* ponowna aktywacje cyklu `active`;
* cofanie `transmitting -> active`;
* cofanie `stabilizing -> transmitting`;
* otwieranie cyklu `closed`;
* zwiekszenie wersji GhostSystemu przed zamknieciem cyklu.

## Utworzenie cyklu

`create_cycle()` wykonuje w jednej transakcji:

1. Walidacje katalogu Sprintu 112.
2. Obliczenie checksum katalogu.
3. Utworzenie cyklu `preparing`.
4. Utworzenie 20 czesci ze statusem `pooled`.
5. Walidacje integralnosci zestawu.
6. Aktywacje cyklu.

Jezeli utworzenie czesci przerwie sie w srodku, transakcja wycofuje cykl i
czesci. Nie zostaje pol-aktywny GhostNetwork.

## Integralnosc zestawu

Walidator cyklu sprawdza:

* dokladnie 20 czesci;
* piec czesci na kazdy klan;
* piec czesci na kazda maszyne;
* unikalny `part_code`;
* zgodnosc `catalog_version` czesci z cyklem;
* brak kotwicy dla `pooled`;
* brak wlasciciela i terytorium dla `pooled`.

`health_check()` egzekwuje pelny kontrakt dla cykli z zapisanym katalogiem.
Legacy/surowe cykle bez `catalog_version` pozostaja ostrzezeniem, zeby nie
psuc starszych testow repozytorium.

## Zdarzenia

Sprint zapisuje zdarzenia domenowe:

* `ghost.cycle_created`;
* `ghost.parts_created`;
* `ghost.cycle_status_changed`;
* `ghost.cycle_activated`.

Publikacja do klienta pozostaje poza zakresem. Zdarzenia sa dziennikiem
audytowym, nie drugim magazynem stanu.

## Spojnosc z artefaktami

Potwierdzono zgodnosc z:

* `doc/clans_machines.md`;
* `doc/ghostnetwork_architecture.md`;
* `doc/sprint_110_integration_audit.md`;
* `doc/sprint_111_ghostnetwork_repository.md`;
* `doc/sprint_112_ghostnetwork_catalog.md`.

GhostNetwork nadal pozostaje globalnym modulem swiata. Cykle i czesci nie sa
zapisywane w profilu gracza.

## Poza zakresem

Sprint 113 nie implementuje:

* topologii polaczen;
* rezerwacji przy oznaczaniu celu;
* dropow;
* zakotwiczenia czesci w targetach;
* mapy;
* terytoriow;
* transmisji;
* supermocy;
* nagrod;
* mostow medialnych.

## Walidacja

Wykonane testy:

```text
python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service
```

Wynik: OK, 33 testy.

```text
python -m py_compile ghostnetwork\__init__.py ghostnetwork\catalog.py ghostnetwork\contracts.py ghostnetwork\cycles.py ghostnetwork\enums.py ghostnetwork\errors.py ghostnetwork\events.py ghostnetwork\models.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\visibility.py
```

Wynik: OK.
