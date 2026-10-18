# Sprint 159 — dowody odbioru

Aktualizacja 2026-10-18: operator potwierdził wizualny PASS w gameplayu po przeniesieniu MASA do Chaos Logu i cichym wygaszaniu glitcha. Zgłasza jednocześnie brak odpowiedzi używanych endpointów Overpass. Odbiór wizualny jest zamknięty; nie potwierdza dostępności upstream ani pełnego produkcyjnego PASS infrastruktury 158/159. Dalszy zakres: [plan 160](../sprints/sprint_160_poi_world_repository_provider_control.md). Poniższe wyniki lokalne i opis wcześniejszego pakietu pozostają historycznymi dowodami.

2026-10-18. Lokalna implementacja gotowa, produkcja niepotwierdzona. Nie wykonano push ani zmiany flag VPS. Pełny PASS 158/159 pozostaje otwarty.

## Zrealizowane

159.1: kontrakt i koszty opisane w [planie](../sprints/sprint_159_masa_scan_interference_ux.md). 159.2: request-local metadane, jawne stany, brak surowych wyjątków w publicznym status. 159.3: Chaos Log, lokalny countdown, brak automatycznych prób, blokada powtórzeń, PL/EN. 159.4: testy wieloprocesowe, endpoint, Playwright, flagi i rollback.

### Korekta prezentacji MASA — 2026-10-18

Usunięto osobną belkę. MASA korzysta z istniejącej nakładki glitcha i Chaos Logu w prawym dolnym rogu mapy. Aktywna blokada daje drugi poziom (`slow`), bez osłabiania cięższych efektów rzeczywistego ładowania. Po wygaśnięciu terminu wpis i efekt MASA znikają po cichu: bez tekstu o końcu blokady, bez auto-retry. Inne logi i efekty pozostają.

Playwright MCP: `tests/browser/poi_chaos_log.js` PASS dla 1440/390 px × PL/EN: pozycja i zawijanie logu, niewidoczna belka, poziomy glitcha, współistnienie z loaderem i ciche wygaśnięcie. Powtórzony `tests/browser/poi_masa.js`: osiem kombinacji zwykły/GhostLab × PL/EN × desktop/mobile PASS, bez dodatkowego HTTP i bez błędów JS/konsoli. Fixture używa teraz także produkcyjnych funkcji ładowania oraz CSS/JS glitcha; nadal zastępuje Leaflet. Screenshoty komponentu desktop/mobile obejrzane lokalnie. Kontrola składni zmienionego JS i `git diff --check` PASS. Nie wykonano wdrożenia na VPS.

## Testy

| Dowód | Wynik |
| --- | --- |
| POI, MASA i realny endpoint `/map-action` | końcowe 34/34 PASS (19.269 s), również nietypowy Retry-After poza zakresem dat |
| MASA — oddzielna regresja 7 testów | 7/7 PASS (5.186 s), obejmuje dodatkowy test failed probe |
| GhostLab | 17/17 PASS (32.205 s) |
| Python i18n | 6/6 PASS |
| Node i18n / runtime / map action | 3 pliki PASS |
| Cztery procesy, 20 żądań przy wspólnej blokadzie | 0 HTTP |
| Cztery procesy po cooldownie, różne zapytania | 1 kontrolowany probe; 3 recovering, 1 restored |
| Błąd ponownej próby z Retry-After | nowy termin z backendu; następne żądanie bez HTTP |
| Realny map-action | identyczne markery fresh/stale; api_error nie zapisuje snapshot; saldo niezmienione; range/token/session/RuntimeError bez MASA |

Playwright MCP uruchomiony na `tools/poi_browser_fixture.py`: produkcyjna funkcja mapAction i realny handler, izolowane konta/cache, lokalny transport. Skrypt powtórzenia: `tests/browser/poi_masa.js`. Osiem kombinacji 1440/390 px × PL/EN × zwykły/GhostLab: ready/degraded/blocked, zachowane markery, 10 dodatkowych kliknięć bez HTTP, odświeżenie bez automatycznego skanu, kolejny ręczny skan nadal respektuje wspólną blokadę.

Dodatkowo: timer przy celowo błędnym Date.now, wygaśnięcie bez auto-retry i bez fałszywego restored; recovering/restored; pusty wynik i malformed response; nieznany termin bez licznika; reduced motion; szerokość panelu w viewport; reset lokalnego stanu po zmianie skanera. Brak pageerror i błędów konsoli. Przeglądarka i fixture zamknięte po testach. Screenshot komponentu mobile obejrzany lokalnie.

## Ograniczenia dowodów

Fixture zastępuje Leaflet i część otoczenia gry: nie jest pełnym testem układu wszystkich kontrolek mapy ani odtworzeniem produkcyjnego Gunicorna. Cztery procesy testują współdzielenie SQLite/policy, nie konfigurację serwera HTTP. Brak obciążania publicznego Overpass. Pełny odbiór mapy na VPS i wznowione pomiary POI pozostają wymagane przed produkcyjnym PASS.

`BLOCKED` wymaga rzeczywistej blokady wszystkich kwalifikujących się źródeł dla danego skanera. Pojedynczy timeout poniżej progu istniejącej polityki pozostaje zwykłym api_error. `recovering` jest prezentowane żądaniom obserwującym już trwający probe; klient właściciela próby otrzymuje wynik po jej zakończeniu, bez dodatkowego polling. To świadome ograniczenie synchronicznego endpointu.

Telemetria `*_shown` to lokalne liczniki PoiMasa.metrics(), zdarzenia poi-ux i konsola przeglądarki. Nie są automatycznie przesyłane na VPS. Serwer nadal rejestruje rzeczywiste próby/czas/cache przez poi_fetch/poi_http; nie utożsamia wysłanej odpowiedzi z potwierdzeniem jej wyświetlenia.

## Kolejny krok

Publikacja pakietu, testy na VPS, restart z obiema flagami OFF. Następnie wspólnie uzgodnione kontrolowane ON według runbooku 158, odbiór MASA i obserwacja. Włączenie samej flagi MASA przy wyłączonej infrastrukturze nie aktywuje funkcji. Nie ma migracji game.sqlite3 ani wymogu czyszczenia cache.
