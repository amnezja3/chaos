# Sprint 130 - GhostNetwork: archiwum, testy koncowe i uruchomienie endgame

## Cel

Domknac pierwszy produkcyjny etap GhostNetwork przez trwale archiwum
GhostSignali, lekkie endpointy odczytu, podstawowe osiagniecia oraz readiness
check przed dalszym endgame.

## Zasada architektury

Archiwum nie jest drugim systemem stanu.

Zrodlem prawdy pozostaja:

* `ghost_cycles`,
* `ghost_signals`,
* lock snapshot cyklu,
* `ghost_historical_nodes`,
* `ghost_contributions`,
* `ghost_reward_ledger`,
* `ghost_clan_reputation`.

`GhostArchiveService` buduje z nich read model dla UI, historii i diagnostyki.
Nie zmienia gameplayu, nie tworzy nowego cyklu i nie przyznaje nagrod poza
idempotentnymi osiagnieciami archiwalnymi.

## Wdrozono

* `GhostArchiveService`;
* tabele `ghost_achievements`;
* idempotentne osiagniecia:
  * `first_contact`,
  * `anchor`,
  * `module_online`,
  * `recovered_fragment`,
  * `unbroken_node`,
  * `defense_line`,
  * `signal_operator`,
  * `final_circuit`,
  * `ghostsystem_veteran`;
* finalizacje archiwum po `GhostNetworkService.start_transmission()`;
* publiczna liste sygnalow;
* szczegoly sygnalu z opcjonalna czescia prywatna;
* lekka historie gracza;
* lekka historie klanow;
* historyczna warstwe mapy jako read-only payload;
* readiness report endgame.

## Endpointy

```text
GET /api/ghostnetwork/archive/signals
GET /api/ghostnetwork/archive/signals/<signal_id>
GET /api/ghostnetwork/archive/player
GET /api/ghostnetwork/archive/clans
GET /api/ghostnetwork/archive/map
GET /api/ghostnetwork/archive/readiness
```

Endpointy korzystaja z lekkiego `load_profile_readonly(..., strip_sensitive=True)`
tylko do identyfikacji widza. Nie uruchamiaja `sync_session_profile()`.

## Readiness

`/api/ghostnetwork/archive/readiness` zwraca:

* stan zdrowia repozytorium,
* najnowszy sygnal,
* potwierdzenie szczegolow najnowszego sygnalu,
* liczbe zarchiwizowanych sygnalow,
* liste kodow osiagniec,
* flagi gotowosci.

Tryby UI Suite, kontrola Ollamy i automatyczne endgame UI pozostaja wylaczone.

## Poza zakresem

* Sprint 131 / GhostNetwork Suite UI;
* automatyczne rozstrzyganie pozniejszego outcome sygnalu;
* start kolejnego cyklu po `stabilization_until`;
* aktywna historyczna warstwa mapy w UI;
* realna odpowiedz z 2108;
* sterowanie mechanika przez Ollame.

## Walidacja

Wymagane:

```text
python -m py_compile ghostnetwork/repository.py ghostnetwork/archive.py ghostnetwork/service.py ghostnetwork/__init__.py run.py
python -m unittest tests.test_ghostnetwork_archive tests.test_ghostnetwork_transmission tests.test_ghostnetwork_narrative tests.test_ghostnetwork_repository
git diff --check
```
