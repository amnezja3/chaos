# Sprint 122 - GhostNetwork Topology Map

## Cel

Pokazac zywa topologie GhostNetwork na mapie jako polowki linii, pelne
polaczenia i lekka animacje przeplywu, bez dodawania nowego pollera i bez
liczenia stanu po stronie frontendu.

## Wdrozone

* Rozszerzono projekcje widocznosci GhostNetwork o polaczenia mapowe.
* Dodano stabilny `public_connection_id`.
* Dodano stany polaczen:
  * `inactive`,
  * `half_from_a`,
  * `half_from_b`,
  * `active`.
* Aktywna czesc z nieodkrytym endpointem nie pokazuje linii.
* Aktywna czesc z odkrytym, ale nieaktywnym endpointem pokazuje pol linii.
* Dwie aktywne czesci pokazuja pelne polaczenie.
* Konflikt nie rozrywa linii, tylko dodaje wariant wizualny `contested`.
* Frontend renderuje tylko gotowa projekcje z backendu.
* Dodano registry:
  * `window.ghostNetworkConnectionLayers`,
  * `window.ghostNetworkConnectionProjections`.
* Dodano funkcje mapy:
  * `renderGhostConnections()`,
  * `createGhostConnectionLayer()`,
  * `updateGhostConnectionLayer()`,
  * `removeGhostConnectionLayer()`,
  * `applyGhostConnectionDelta()`,
  * `animateGhostConnectionPulse()`.
* Dodano osobne panele Leafleta:
  * `ghostNetworkConnectionPane`,
  * `ghostNetworkPulsePane`.
* Linie sa krzywymi deterministycznymi, bez losowej zmiany bendu przy refreshu.
* Animacja przeplywu jest CSS/SVG i respektuje `prefers-reduced-motion`.

## Zasady bezpieczenstwa

* Frontend nie decyduje, czy polaczenie istnieje albo jaki ma stan.
* Frontend nie odkrywa ukrytego endpointu.
* Projekcja polaczenia nie jest drugim systemem topologii.
* Zrodlem prawdy pozostaja repository, topology, lifecycle i module state.
* Recovery odbudowuje tylko warstwe GhostNetwork connections.

## Poza zakresem

* Suite.
* Supermoce.
* Nagrody.
* Media.
* GhostSignal.
* BlackNet bridge.
* Nowy poller mapy.
* Nowa logika gameplayowa aktywacji modulow.

## Spojnosc z artefaktami

Potwierdzono zgodnosc z:

* `doc/clans_machines.md`,
* `doc/ghostnetwork_architecture.md`,
* Sprintem 120 - projekcja widocznosci,
* Sprintem 121 - mapa jako odbiorca bezpiecznej projekcji.

GhostNetwork nadal jest modulem strategicznym swiata, a mapa pokazuje tylko jego
readonly projekcje.

## Walidacja

* `node --check static/js/map/ghostnetwork.js`: OK.
* `node --check static/js/terminal.js`: OK.
* `python -m py_compile ghostnetwork\visibility.py ghostnetwork\topology.py ghostnetwork\service.py run.py`: OK.
* `python -m unittest tests.test_ghostnetwork_visibility tests.test_ghostnetwork_map_layer_contract tests.test_ghostnetwork_map_snapshot_endpoint`: OK.
* `python -m unittest tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_discovery tests.test_ghostnetwork_lifecycle tests.test_ghostnetwork_map_layer_contract tests.test_ghostnetwork_map_snapshot_endpoint tests.test_ghostnetwork_module_state tests.test_ghostnetwork_repository tests.test_ghostnetwork_reservations tests.test_ghostnetwork_territory tests.test_ghostnetwork_topology tests.test_ghostnetwork_visibility`: OK, 89 testow.
