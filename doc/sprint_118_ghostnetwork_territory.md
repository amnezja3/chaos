# Sprint 118 - GhostNetwork Territory Adapter

## Cel

Podpiac stan czesci GhostNetwork pod istniejace, stabilne terytoria bez
tworzenia drugiego systemu klastrow, polygonow, filarow ani konfliktow.

## Zrealizowano

* Dodano `GhostTerritoryAdapter`.
* Dodano obsluge zdarzen:
  * `on_territory_stabilized(event)`,
  * `on_territory_contested(event)`,
  * `on_territory_released(event)`,
  * `on_territory_owner_changed(event)`.
* Dodano `resolve_part_territory(part, territories)`.
* Dodano `resolve_parts_in_changed_area(event)`.
* Dodano recovery `reconcile_parts_with_territories(cycle_id, apply=False)`.
* Dodano lekkie query repozytorium:
  * `list_discovered_parts_in_bounds(...)`,
  * `list_parts_by_territory(...)`.
* Podpieto adapter do `GhostNetworkService`.

## Reguly

* Terytorium stabilne wymaga wlasciciela, klanu, poligonu, minimum trzech
  filarow i braku aktywnego konfliktu.
* Czesci poza stabilnym terytorium wracaja do `public`.
* Czesci w stabilnym terytorium obcego klanu przechodza do `contained`.
* Czesci w stabilnym terytorium wlasnego klanu przechodza do `active`.
* Konflikt ustawia `conflict_state = contested`, ale nie zmienia statusu
  bazowego.
* Nakladajace sie stabilne terytoria roznych wlascicieli nie wybieraja losowego
  ownera. Czesc trafia w konflikt.
* Recovery jest domyslnie dry-run.

## Decyzje architektoniczne

* GhostNetwork nie tworzy geometrii terytoriow.
* GhostNetwork nie liczy klastrow ani konfliktow.
* Adapter korzysta z eventow i snapshotow obecnego systemu terytoriow.
* Punktowe przeliczenie uzywa bounds, a dopiero potem point-in-polygon.
* Pelne przeliczenie wszystkich czesci jest dostepne tylko jako recovery.

## Poza zakresem

* Brak markerow mapy GhostNetwork.
* Brak delt frontendowych GhostNetwork.
* Brak supermocy.
* Brak widocznosci w Cybernerze, Radiu i BlackNecie.
* Brak zmian gameplayu terytoriow.

## Walidacja

* `python -m py_compile ghostnetwork\territory.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\__init__.py`
* `python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_topology tests.test_ghostnetwork_reservations tests.test_ghostnetwork_discovery tests.test_ghostnetwork_lifecycle tests.test_ghostnetwork_territory`
* `git diff --check`
