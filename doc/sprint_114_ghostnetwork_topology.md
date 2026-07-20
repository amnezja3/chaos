# Sprint 114 - GhostNetwork topology

## Zakres

Sprint 114 dodal logiczna topologie pierwszego cyklu GhostNetwork jako jeden
zamkniety obwod 20 czesci i 20 polaczen.

Wdrozone:

* `GhostTopologyService`;
* kanoniczna topologia `V1 -> S5 -> ... -> P2 -> V1`;
* deterministyczny generator dla kolejnych cykli oparty o seed;
* walidator topologii wykrywajacy rozbite pierscienie, self-loop,
  duplikaty logicznych krawedzi, brak wezlow, bledny degree, polaczenia tego
  samego klanu i niezgodny checksum;
* `topology_checksum` na cyklu;
* wewnetrzny snapshot topologii z seed, checksum, ring_order, connections i
  validation;
* zdarzenie `ghost.topology_created`;
* blokade aktywacji cyklu bez poprawnej topologii.

## Kontrakt

Topologia jest wewnetrznym kontraktem administracyjnym. Nie ujawnia zwyklemu
klientowi:

* pelnej kolejnosci pierscienia;
* nieodkrytych sasiadow;
* przyszlych lokalizacji czesci;
* linii mapy.

Publiczna projekcja pozostaje poza zakresem.

## Zgodnosc z artefaktami

Sprawdzono zgodnosc z:

* `doc/clans_machines.md`;
* `doc/ghostnetwork_architecture.md`;
* `doc/sprint_110_integration_audit.md`;
* `doc/sprint_111_ghostnetwork_repository.md`;
* `doc/sprint_112_ghostnetwork_catalog.md`;
* `doc/sprint_113_ghostnetwork_cycle_service.md`.

Topologia pozostaje warstwa logiki GhostNetwork. Nie uruchamia dropow, mapy,
rezerwacji, transmisji, supermocy ani widocznych linii.

## Walidacja

Uruchomiono:

* `python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_topology`;
* `python -m py_compile` dla pakietu `ghostnetwork`;
* `git diff --check`.

