# Sprint 158 — dowody i stan odbioru

Aktualizacja po testach operatora 2026-10-18: VPS POI 26/26 PASS (14.596 s), GhostLab 17/17 PASS (98.102 s), restart OFF i Launch HTTP 200 potwierdzone. Dwa skany OFF zwróciły api_error po 8.8635 i 56.7548 s. Log dostawcy: timeouty i HTTP 502 z komunikatem o zajętych workerach i pełnej kolejce; brak wyniku końcowej próby Kumi w dostarczonym fragmencie. To początkowy baseline awarii, nie pomiar normalnej dostępności ani dowód regresji nowego cache. Na polecenie operatora dalszy odbiór POI nastąpi po przygotowaniu [159](../sprints/sprint_159_masa_scan_interference_ux.md). Flaga infrastruktury pozostaje OFF.

Data: 2026-10-18. Status: **lokalnie gotowe do przeglądu i publikacji pakietu OFF; brak pełnego PASS sprintu**.

## Implementacja

| Etap | Stan | Dowód / ograniczenie |
| --- | --- | --- |
| 158.1 Kontrakt i baseline | kontrakt lokalny gotowy; baseline produkcyjny otwarty | [Analiza kontraktu](sprint_158_1_contract_baseline.md), fixtures i regresje. Operator: 4 workery / 120 s. Brak rzeczywistych p95/QPS. |
| 158.2 Trwały cache | lokalny PASS | Oddzielna SQLite WAL; dokładny klucz zapytania; fresh/stale od udanego pobrania; checksum, kompletność i izolacja obiektów. |
| 158.3 Współbieżność | lokalny PASS | Test trzech procesów: jedno HTTP dla wspólnego klucza; globalny slot; fencing starego właściciela; odzyskanie wygasłego lease po śmierci procesu. |
| 158.4 Odporność / GhostLab | lokalny PASS | Retry-After, wspólny stan aliasów i cooldown, błędy/remark/parser, stale oraz bonus prób i anulowanie. |
| 158.5 Limity / telemetry | lokalny PASS, tuning produkcyjny otwarty | Skończone limity odpowiedzi/cache/WAL; po błędzie storage brak ominięcia koordynacji; strukturalne logi i CLI. Nie wykonano rzeczywistego zapełnienia dysku VPS. |
| 158.6 Integracja / rollout | lokalny PASS, akceptacja pełnej gry otwarta | Fasada POIFetcher, flaga OFF, runbook i komponentowa regresja przeglądarkowa. |
| 158.7 Produkcja | oczekuje | Push i wdrożenie, baseline OFF, kontrolowane ON, obserwacja 24–72 h i ocena rollbacku. |

## Weryfikacja lokalna

- `python -m unittest discover -s tests -p 'test_poi*.py' -v`: 24 testy PASS (21 nowych i 3 istniejące).
- `python -m unittest discover -s tests -p test_ghostlab_scanner.py -v`: 17 testów PASS.
- Playwright MCP: 24 scenariusze komponentowe — desktop 1440 / mobile 390, PL/EN, skan zwykły/GhostLab, upstream/stale/brak cache przy awarii. Sprawdzono wynik DOM, markery i komunikat błędu; brak błędów strony. Przeglądarka i serwer fixture zamknięte po testach.
- Fixture `tools/poi_browser_fixture.py` używa produkcyjnej funkcji `mapAction` i endpointu `/map-action`, izolowanych danych oraz lokalnego transportu POI. Rysowanie Leaflet i część kontekstu gry są zastąpione atrapami. To nie jest dowód pełnej regresji mapy, mobile ani gameplayu na VPS.
- Prawdziwy lokalny serwer HTTP: poprawna odpowiedź i przerwanie powolnej odpowiedzi przez deadline procesu transportu. Brak testów obciążenia publicznego Overpass.
- CLI cache: inicjalizacja, odczyt statusu, maintenance i checkpoint na osobnej testowej bazie; `quick_check=ok`.
- W testach wykryto i poprawiono konflikt inicjalizacji SQLite: gotowa baza nie wykonuje ponownie DDL, limit stron jest ustawiany w transakcji zapisu. Po poprawce suite przechodzi.

## Granice gotowości

### Ponowny test VPS — kontencja zapisu SQLite

Kolejny log operatora: 24 testy POI, 1 FAIL w `test_multiprocess_singleflight` (18.117 s). Dwa procesy zakończyły się `storage_unavailable` po około 0.5 s, trzeci zwrócił wynik po 2.63 s. GhostLab nie uruchomił się z powodu `&&`. Poprzedni PASS nie dowodził stabilności przy wolniejszym zapisie na VPS; odbiór pozostaje wstrzymany.

Poprawka acquire: istniejący aktywny lease jest najpierw sprawdzany odczytem bez blokady pisarza. Przejęcie nadal rozstrzyga atomowa transakcja. SQLITE_BUSY przy przejęciu wraca do ograniczonej czasowo pętli join; pozostałe błędy storage nadal przerywają operację. Czas ważności lease jest liczony po uzyskaniu transakcji. Bez podnoszenia limitu oczekiwania SQLite i bez ominięcia limitu HTTP.

Dodano test rzeczywistej blokady zapisu przez 0.8 s (dłużej niż busy timeout) i test dołączenia do istniejącego właściciela przy zablokowanym pisarzu. Lokalnie 26/26 testów POI PASS (12.753 s), następnie trzy dodatkowe powtórzenia testu wieloprocesowego PASS i pełne 17/17 GhostLab PASS (67.550 s). Wymagane ponowne uruchomienie na VPS po publikacji poprawki.

### Weryfikacja VPS po pobraniu a6ff305

Operator przekazał wynik: POI 24/24 PASS (16.538 s), GhostLab 16 testów, 8 FAIL (42.963 s). Wszystkie błędy endpointów miały HTTP 423 `ghostsystem_restart_required` / `document_epoch_replaced`. Fixture izolowało konta, ale nie `ghostsignal_show_db_path`, więc bramka odczytywała rzeczywisty restart cyklu serwera. To blokuje akceptację testów przed restartem aplikacji; nie jest podstawą do wyłączenia bramki gameplayu.

Poprawka: testy ScannerTest inicjalizują GhostNetworkRepository w tymczasowej bazie i podmieniają wyłącznie testową ścieżkę Show. Dodano regresję, która nadal wymaga właściwej epoki: 423 bez nagłówka, 200 z aktualnym nagłówkiem. Produkcyjny mechanizm bramki pozostaje bez zmian. Wcześniejsza liczba 17 testów GhostLab w raporcie nie odpowiadała pakietowi a6ff305 (16); po dodaniu regresji zestaw ma 17 testów. Powtórny wynik VPS wymaga potwierdzenia po pobraniu poprawki.

Lokalna weryfikacja poprawki: wszystkie 16 dotychczasowych testów przeszło; nowa regresja po korekcie testowego identyfikatora okna przeszła w osobnym uruchomieniu (1/1 PASS). `git diff --check` bez błędów. Poprawka testów oczekuje publikacji i ponownego uruchomienia zestawu na VPS.

Nowa warstwa jest domyślnie OFF. Operator pobrał pakiet a6ff305 na VPS; restart z nowym kodem i baseline nie zostały jeszcze potwierdzone. Nie wykonano migracji bazy gry ani zmian flag Identity/AI/wieku. Dotychczasowa ścieżka pozostaje dostępna po OFF. Nie obiecuje się procentowej poprawy bez pomiarów. Harmonogram maintenance i alarmowanie nie zostały zainstalowane na VPS.

Przed ON potrzebne są odczyty topologii i typu workerów, pomiar ruchu OFF, potwierdzenie wspólnego lokalnego pliku cache i aktualnych endpointów. Następnie smoke w pełnej grze, pomiary ON oraz obserwacja. Sposób wykonania i rollback: [runbook](../runbooks/poi_infrastructure_158.md).
