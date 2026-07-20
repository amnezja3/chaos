# Sprint 123 - GhostNetwork Delta Sync

## Cel

Dodano lekki kanal synchronizacji GhostNetwork oparty o istniejacy delta-feed.
Zmiany czesci, polaczen, maszyn i cyklu moga docierac do mapy bez reloadu
iframe, bez pelnego profilu i bez osobnego pollera per aplikacja.

## Wdrozone

* `GhostNetworkDeltaPublisher` w `ghostnetwork/deltas.py`.
* Projekcja delt przez istniejaca warstwe widocznosci.
* Bezpieczny payload per odbiorca, bez filtrowania prywatnych danych w CSS.
* `snapshot_checksum` dla diagnostyki snapshotow i delt.
* `normalize_snapshot_view(...)` dla widokow `map`, `suite`,
  `territory_summary` i `status`.
* `rebuild_ghostnetwork_delta_projection(cycle_id, from_version=None)`.
* Publikacja eventow domenowych GhostNetwork do istniejacego `delta_bus`.
* Pola kontraktu delty przenoszone z payloadu na event:
  `event_id`, `cycle_id`, `state_version`, `audience_scope`,
  `transaction_id`, `transaction_index`, `transaction_size`.
* `window.GhostNetworkDeltaClient` dla mapy:
  dedupe, wersjonowanie, cycle mismatch recovery, version gap recovery,
  registry callbackow widokow i recovery scope GhostNetwork.
* Snapshot `GET /api/ghostnetwork/snapshot?view=...` bez `sync_session_profile()`.

## Decyzje

* Zrodlem prawdy pozostaje repository GhostNetwork i istniejaca projekcja
  widocznosci.
* Delta bus jest kanalem powiadomien, nie drugim magazynem stanu.
* Recovery dotyczy wylacznie scope `ghostnetwork`.
* Widok `suite` nie niesie geometrii linii mapy.
* Wewnetrzne rezerwacje nadal nie sa publikowane jako zwykle delty gracza.

## Poza zakresem

* Pelne GUI GhostNetwork Suite.
* Transmisja finalna GhostNetwork.
* Ollama i media.
* Retry publikacji z osobnej kolejki `pending/failed`.
* Rzadki sanity refresh - na razie nie jest dodany.

## Walidacja

* `node --check static/js/map/ghostnetwork.js`
* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py ghostnetwork/deltas.py`
* `python -m unittest tests.test_ghostnetwork_delta_publisher tests.test_ghostnetwork_map_snapshot_endpoint tests.test_ghostnetwork_map_layer_contract`

