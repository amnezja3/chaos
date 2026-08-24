# Sprint 127 - GhostNetwork Closure Snapshot

## Cel

Sprint 127 domyka kompletny cykl GhostNetwork bez uruchamiania transmisji.
System wykrywa gotowa siec 20 czesci i 20 aktywnych polaczen, a potem
atomowo blokuje cykl jako `transmitting`.

W tym sprincie `transmitting` oznacza tylko: cykl zostal zamrozony i czeka na
Sprint 128. Nie powstaje jeszcze GhostSignal.

## Wdrozone elementy

* `GhostNetworkClosureService`.
* Readiness check dla pelnej sieci.
* Atomowy lock cyklu.
* Nieusuwalny snapshot blokady w `ghost_cycle_lock_snapshots`.
* Walidacja snapshotu przez checksum.
* Event `ghost.cycle_locked`.
* Fasada closure w `GhostNetworkService`.

## Warunki locka

Lock jest mozliwy tylko gdy:

* cykl ma status `active`;
* istnieje dokladnie 20 czesci;
* wszystkie czesci sa odkryte i maja `module_state = active`;
* kazda czesc ma stabilne terytorium swojego klanu;
* nie ma nierozstrzygnietych konfliktow strategicznych;
* istnieje dokladnie 20 aktywnych polaczen;
* topologia jest jednym zamknietym obwodem;
* checksum topologii jest poprawny;
* nie istnieje lock snapshot ani GhostSignal tego cyklu.

## Snapshot

Snapshot przechowuje zamrozony stan:

* cyklu;
* katalogu i checksumu katalogu;
* topologii i checksumu;
* 20 czesci z kotwicami, wlascicielami i terytoriami;
* polaczen;
* postepu maszyn;
* wkladu operatorow;
* reputacji klanowej;
* konfliktow, obron i historii transferow;
* operatora domykajacego;
* `state_version`, `locked_at` i checksum snapshotu.

Snapshot jest zrodlem prawdy dla Sprintu 128. Po locku pozniejsze zmiany
terytoriow lub czesci nie zmieniaja zamrozonego wyniku.

## Poza zakresem

* Brak transmisji GhostSignalu.
* Brak rekordu `ghost_signals`.
* Brak restartu cyklu.
* Brak zmiany wersji GhostSystemu.
* Brak finalnych nagrod za transmisje.

## Walidacja

Uruchomiono:

* `python -m unittest tests.test_ghostnetwork_closure`
* `python -m unittest tests.test_ghostnetwork_closure tests.test_ghostnetwork_topology tests.test_ghostnetwork_lifecycle tests.test_ghostnetwork_rewards tests.test_ghostnetwork_conflicts`
* `python -m py_compile config.py database.py run.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\closure.py ghostnetwork\__init__.py`
* `git diff --check`

Wynik: OK.
