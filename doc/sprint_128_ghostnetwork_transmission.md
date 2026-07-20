# Sprint 128 - GhostNetwork Transmission

## Cel

Sprint 128 uruchamia backendowa transmisje GhostSignalu z zamrozonego lock
snapshotu Sprintu 127. Frontend moze animowac final, ale decyzja, nagrody,
zuzycie czesci, restart i stabilizacja sa stanem backendu.

## Zrodlo prawdy

Transmisja korzysta wylacznie z `ghost_cycle_lock_snapshots`.

Pozniejsze zmiany terytoriow, wlascicieli albo zywych czesci nie zmieniaja:

* payloadu GhostSignalu,
* finalnych nagrod,
* archiwum historycznych wezlow,
* checksumu sygnalu.

## Wdrozone elementy

* `GhostTransmissionService`.
* Rekord `ghost_signals` z jednym sygnalem na cykl.
* Checksum payloadu GhostSignalu.
* Idempotentna transmisja po `cycle_id`.
* Koncowe nagrody w `ghost_reward_ledger`.
* Zuzycie 20 czesci przez istniejacy lifecycle.
* Archiwum `ghost_historical_nodes`.
* Usuniecie aktywnych polaczen cyklu.
* Eventy:
  * `ghost.signal_created`,
  * `ghost.signal_sent`,
  * `ghost.final_rewards_created`,
  * `ghost.parts_consumed`,
  * `ghost.connections_closed`,
  * `ghost.abilities_disabled`,
  * `ghost.version_changed`,
  * `ghost.restart_required`,
  * `ghost.stabilization_started`.
* Zmiana wersji GhostSystemu.
* Flaga restartu klienta na cyklu.
* Stabilizacja 15 minut przed kolejnym cyklem.
* Recovery przez `resume_interrupted_transmission(cycle_id)`.
* Health-check spojnosci transmisji.

## Warunki wejscia

Transmisja wymaga:

* cyklu w statusie `transmitting`,
* jednego poprawnego lock snapshotu,
* 20 aktywnych czesci w lock snapshocie,
* 20 polaczen w lock snapshocie,
* 4 maszyn online,
* poprawnego checksumu lock snapshotu,
* braku istniejacego sygnalu dla cyklu.

## Restart i stabilizacja

Po transmisji cykl przechodzi do `stabilizing`.

Ustawiane sa:

* `restart_required`,
* `restart_signal_id`,
* `restart_from_version`,
* `restart_to_version`,
* `restart_required_at`,
* `stabilization_until`.

Polaczenia cyklu sa usuwane, a czesci maja status `consumed`.

## Poza zakresem

* Brak odpowiedzi GhostSignalu z 2108.
* Brak rozstrzygania `outcome`.
* Brak finalnego archiwum gracza w UI.
* Brak nowego aktywnego cyklu po stabilizacji.
* Brak pelnej animacji frontendowej finalu.

## Walidacja

Uruchomiono:

* `python -m unittest tests.test_ghostnetwork_transmission tests.test_ghostnetwork_closure tests.test_ghostnetwork_lifecycle tests.test_ghostnetwork_rewards tests.test_ghostnetwork_conflicts`
* `python -m py_compile config.py database.py run.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\closure.py ghostnetwork\transmission.py ghostnetwork\__init__.py`
* `git diff --check`

Wynik: OK.
