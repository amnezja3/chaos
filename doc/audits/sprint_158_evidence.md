# Sprint 158 — dowody i stan odbioru

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

Nowa warstwa jest domyślnie OFF. Nie wykonano push, wdrożenia, migracji bazy gry ani zmian flag Identity/AI/wieku. Dotychczasowa ścieżka pozostaje dostępna po OFF. Nie obiecuje się procentowej poprawy bez pomiarów. Harmonogram maintenance i alarmowanie nie zostały zainstalowane na VPS.

Przed ON potrzebne są odczyty topologii i typu workerów, pomiar ruchu OFF, potwierdzenie wspólnego lokalnego pliku cache i aktualnych endpointów. Następnie smoke w pełnej grze, pomiary ON oraz obserwacja. Sposób wykonania i rollback: [runbook](../runbooks/poi_infrastructure_158.md).
