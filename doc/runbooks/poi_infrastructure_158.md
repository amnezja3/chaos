# Wdrożenie POI Infrastructure 158

Status: pakiet lokalny do przeglądu. Najpierw wdrożenie z flagą OFF i baseline, następnie osobne kontrolowane włączenie. Nie zmieniać flag Identity, wieku ani AI. Brak migracji game.sqlite3.

## Konfiguracja

| Zmienna | Domyślnie | Granica |
| --- | --- | --- |
| CHAOS_POI_INFRASTRUCTURE_ENABLED | brak = OFF | tylko 1 włącza |
| CHAOS_POI_CACHE_PATH | data/poi_cache.sqlite3 względem repo | lokalny dysk jednego hosta, ta sama ścieżka workerów |
| CHAOS_POI_DEADLINE | 110 s | 1–110 |
| CHAOS_POI_JOIN_WAIT | 2 s | 0–10 |
| CHAOS_POI_CONNECT_TIMEOUT | 3 s | 0.1–5 |
| CHAOS_POI_MAX_RESPONSE | 4194304 B | 1024–16777216, po dekompresji |
| CHAOS_POI_MAX_ELEMENTS | 20000 | 1–50000 |
| CHAOS_POI_MAX_CACHE | 67108864 B | 1–256 MiB payloadów |
| CHAOS_POI_MAX_ENTRIES | 2000 | 1–5000 |
| CHAOS_OVERPASS_TIMEOUT_SECONDS | 8 s | istniejący read timeout + bonus GhostLab |
| CHAOS_POI_CACHE_TTL_SECONDS | 300 s | istniejący parametr |
| CHAOS_POI_STALE_CACHE_TTL_SECONDS | 1800 s | od udanego fetch, nie od odczytu |

Jedno globalne HTTP na lokalną bazę. Slot i query lease mają deadline + 5 s. SQLite busy timeout 500 ms. Główny plik ma limit stron odpowiadający około 2 × limit payloadów, minimum 1 MiB. Zapisy są zatrzymywane, gdy WAL przekroczy limit payloadów + 8 MiB; pojedyncza transakcja może przekroczyć ten próg. Nie jest to limit całego filesystemu. Krótkie odczyty, autocheckpoint 64 strony i journal_size_limit 1 MiB ograniczają typowy WAL; długotrwały zewnętrzny czytelnik może blokować checkpoint. Monitorować plik i wolne miejsce.

## 1. Pakiet OFF i pomiary

Przed restartem zachować hash poprzedniego wydania i prywatną konfigurację PM2. Potwierdzić jeden host, 4 workery / 120 s, prawa do data i zapas dysku. Repozytorium nie jest dowodem konfiguracji uruchomionego procesu.

```bash
# Po pobraniu zatwierdzonego commitu:
.venv/bin/python -m unittest discover -s tests -p 'test_poi*.py' -v
.venv/bin/python -m unittest discover -s tests -p test_ghostlab_scanner.py -v
CHAOS_POI_INFRASTRUCTURE_ENABLED=0 pm2 restart chaos --update-env
```

Zapisać OFF także w trwałej konfiguracji procesu. Zwykła ścieżka działa dalej, logi poi_scan dają baseline. Nie restartować niezwiązanych workerów dla samej publikacji tego kodu. Nie wykonywać ręcznie DELETE w bazie graczy.

## 2. Inicjalizacja i kontrolowane ON

Po baseline i zgodzie na włączenie:

```bash
umask 077
.venv/bin/python tools/poi_cache.py --initialize
.venv/bin/python tools/poi_cache.py
CHAOS_POI_INFRASTRUCTURE_ENABLED=1 pm2 restart chaos --update-env
```

Jeśli inny proces również używa POIFetcher, musi używać tego samego pliku i zatwierdzonej konfiguracji. Nie ma synchronizacji między hostami. Nie włączać części workerów przez przypadkowo różne pliki cache. Nie dodano canary per gracz.

Smoke: jeden zwykły skan, ponowienie identycznego punktu (fresh, 0 prób), skaner GhostLab, inny gracz, restart web i ponowienie skanu. Ocenić widoczne markery i uprawnienia. Nie wymuszać awarii publicznego Overpass; stale i błędy są testowane lokalnie.

## 3. Obserwacja i utrzymanie

```bash
.venv/bin/python tools/poi_cache.py
.venv/bin/python tools/poi_cache.py --maintenance
.venv/bin/python tools/poi_cache.py --log /sciezka/do/logu-chaos.log
```

Status domyślnie tylko odczytuje. --maintenance usuwa wygasłe lease i wpisy starsze od stale TTL poza aktywnymi lease, następnie wykonuje pasywny checkpoint, bez VACUUM. Wywołać okresowo istniejącym schedulerem operatora; zalecany interwał 5 minut. Harmonogram nie jest instalowany automatycznie. Ciągły ruch uruchamia również kontrolę pojemności przy zapisach. Cache jest odtwarzalny, nie musi trafiać do pełnych backupów świata.

Logi: poi_scan (wynik/czas, także OFF), poi_fetch (fresh/upstream/stale/error/cancelled, próby, czas i dołączenie do istniejącego zapytania), poi_http (grupa/status), poi_cache (evictions). Brak współrzędnych i danych kont w nowych zdarzeniach. Stare logi ścieżki OFF nadal mają historyczny format. Narzędzie podsumowuje p50/p95/p99 i liczebność, nie wylicza wiarygodnego QPS bez czasu obserwacji. Zachować granice okna pomiarowego.

Dane po ON obserwować 24–72 h, porównać z baseline. Alarmy: wzrost api_error, istotne pogorszenie p95, długie blokady SQLite, wzrost RAM/WAL, brak korzyści cache lub regresja GhostLab. Wyjaśnić wynik przed pełnym PASS.

## 4. Rollback

```bash
CHAOS_POI_INFRASTRUCTURE_ENABLED=0 pm2 restart chaos --update-env
```

Utrwalić OFF. Cache zostawić do diagnostyki; brak migracji do cofania. Kontrolować ruch starej ścieżki, która nie ma wspólnego limitu. Gdy sam plik jest uszkodzony, nie kasować go na pracującej aplikacji; przy OFF i zatrzymanych użytkownikach tego cache można zachować cały zestaw sqlite/WAL/SHM diagnostycznie i utworzyć nowy cache. Nigdy nie przenosić game.sqlite3 w tej procedurze.

## Dostawcy i ograniczenia

Lista endpointów pochodzi z dotychczasowej fasady. Alias lz4.overpass-api.de dzieli stan limitów z overpass-api.de; nie służy do omijania 429. Przed ON potwierdzić dozwolone i aktualne endpointy oraz rzeczywiste obciążenie. [Dokumentacja operatora Overpass](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) ostrzega przed traktowaniem publicznych instancji jako gwarantowanego backendu aplikacji. Cache nie zapewnia SLA dostawcy. Nie uruchamiano testów obciążenia publicznych serwerów.

[Opis out center](https://dev.overpass-api.de/overpass-doc/en/targets/formats.html) potwierdza, że to środek bounding box; v1 nie filtruje geometrii po tym punkcie. Atrybucja OSM na istniejącej mapie pozostaje. Dłuższa dystrybucja lub własna baza przestrzenna wymagają osobnego przeglądu warunków.
