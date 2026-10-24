# 162/163 — przygotowanie schematu i etap pasywny

## Wersja przedwdrożeniowa po odbiorze pilota — 24.10.2026

Ograniczony pilot exact-query odebrano na VPS: zapis, odczyt przez inny worker,
restart, wyłączenie, usunięcie jednego wygasłego snapshotu i udany skan w nowej
lokalizacji. PM2 zapisany. Nowy pakiet dodaje lokalną rotację sektorów
w bibliotece DiscoveryJobs, poprawia kontrolę rozmiaru WAL przy współbieżnym
zamykaniu połączeń SQLite oraz aktualizuje dowody. Nie uruchamia workera.

Konfiguracja docelowa pozostaje w `ecosystem.web.config.js`: MapLark ON,
ingest/read OFF, discovery passive, priority OFF, zakres pilota pusty/until 0.
Budżety 800/dobę UTC i 24000/31 dni pozostają w bazie. Nie zmieniać registry,
rewizji providera, sekretów ani scope. Nie wykonywać ponownie migracji świata.
Tabela world_discovery_cursor należy do jawnego initialize biblioteki zadań;
produkcja nie wywołuje tej biblioteki, więc ten pakiet nie wymaga migracji VPS.

Po osobnym wypchnięciu zatwierdzonego commita, preflight na VPS:

```bash
cd /home/johndoe/app/chaos &&
git pull --ff-only &&
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py' &&
.venv/bin/python -m unittest discover -s tests -p 'test_poi_*.py'
```

Testy korzystają z izolowanych baz i mocków, nie z produkcyjnych providerów.
Nie przechodzić dalej przy błędzie. Poprawka WAL dotyczy wspólnego Repository
używanego również przez skaner; po PASS przeładować proces web:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env
```

Sprawdzić /launch 200 po gotowości procesu oraz zachowanie panelu OFF/OFF/passive.
Po udanym odbiorze zapisać `pm2 save`. Nie włączać background ani world dla
wszystkich. Rollback tej wersji: wycofać pakiet przez revert
commita i wdrożyć ponownie; zachować obecną konfigurację OFF/OFF/passive i bazę.
Nie wracać do historycznego commita z aktywnym pilotem i nie odtwarzać księgi.

Przed osobnym uruchomieniem tła pozostają: integracja workera poza Gunicornem,
sprawdzenie scope/capabilities przy każdym zadaniu, kosztów i pojemności magazynu,
limity per warstwa, symulacja obciążenia oraz zatwierdzony region/budżet/okno.
Rotacja sektorów równoważy przydziały, nie koszty zapytań. Pełne sprinty 162/163
pozostają otwarte; wersja przedwdrożeniowa nie oznacza gotowości tła produkcyjnego.

## Historyczne checkpointy

Aktualizacja 24.10.2026: sekcje 1–3 poniżej opisują odebrany etap migracji
i uruchomienia passive. Nie powtarzać migracji ani nie wyłączać tego trybu.
Ingest/read pozostają OFF. Dalsza biblioteka `discovery_jobs.py` jest testowana
lokalnie; nie podłączono jej do produkcyjnego kolektora ani żadnego workera.

Następny checkpoint, po pobraniu nowego kodu: rozszerzony pomiar bez restartu,
bez migracji i bez HTTP, na tymczasowej bazie:

```bash
.venv/bin/python tools/world_storage_benchmark.py --counts 50 680
```

Nowe pola: `process_lifetime_peak_rss_bytes` (Linux, maksimum całego procesu),
`post_commit_wal_bytes` (obserwacja, nie szczyt), `publication_transactions`,
`max_transaction_entry_seconds` i `max_transaction_hold_and_close_seconds`.
Pomiar syntetyczny z tracemalloc nie zastępuje pilota na rzeczywistych danych.

Pomiar RSS/transakcji został już dostarczony przez operatora (patrz evidence 162).
Kolejny pakiet dodaje priorytet HTTP MapLark domyślnie OFF. Po pobraniu kodu
wykonać bez restartu/migracji, z izolowanymi bazami i mockowanym transportem:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_world_upstream_priority.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_shadow.py'
```

Oczekiwane 6 + 7 PASS. Nie ustawiać jeszcze `CHAOS_POI_PRIORITY_ENABLED=1`;
nie ma produkcyjnego workera background. Obecny skaner i passive działają dalej.
Po odbiorze Linux można przygotować osobny rollout priorytetu i pilot ingest.

Pakiet dodaje kanoniczny magazyn, odczyt dokładnego zapytania i pasywny rejestr
zapotrzebowania. Nie oznacza pełnego odbioru sprintów ani zgody na background.
W pierwszym wdrożeniu pozostawić ingest/read OFF i discovery off.
Aktualny skaner MapLark oraz budżety 800/dzień i 24000/31 dni zostają bez zmian.

## 1. Kod i testy na VPS

Po pushu pakietu, w `/home/johndoe/app/chaos`:

```bash
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi_*.py'
.venv/bin/python tools/world_storage_benchmark.py --counts 50 680
```

Benchmark używa tymczasowej bazy i danych syntetycznych, bez API. Nie mierzy
pełnego RSS ani szczytu WAL. Nie zastępuje odbioru wydajności rzeczywistych danych.
Nie restartować aplikacji, jeśli testy nie przejdą. Wyniki z VPS są checkpointem
przed migracją; nie należy automatycznie przechodzić do ON.

## 2. Dry-run i przygotowanie schematu

Potwierdzić rzeczywistą ścieżkę `CHAOS_POI_CACHE_PATH`; poniższy przykład zakłada
`data/poi_cache.sqlite3`. Nigdy nie podawać `game.sqlite3`.

```bash
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery
```

Wynik wymagany: dry_run, world_schema 2, integralność i klucze obce OK,
original_data_unchanged true, network_calls 0. Następnie w uzgodnionym krótkim
oknie zatrzymać proces web (i inne procesy faktycznie zapisujące tę bazę).

```bash
umask 077
export WORLD_BACKUP="$HOME/chaos-backups/162-163-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$WORLD_BACKUP"
git rev-parse HEAD > "$WORLD_BACKUP/commit"
pm2 jlist > "$WORLD_BACKUP/pm2-before.json"
pm2 stop chaos
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --apply --backup "$WORLD_BACKUP/poi_cache.sqlite3"
```

Backup API SQLite uwzględnia WAL. Po migracji wymagana integralność OK i schema 2.
W prywatnym ecosystemie zachować istniejące ustawienia, sekrety i flagi MapLark;
dodać tylko nowe wartości:

```javascript
CHAOS_POI_WORLD_INGEST_ENABLED: "0",
CHAOS_POI_WORLD_REPOSITORY_ENABLED: "0",
CHAOS_POI_DISCOVERY_MODE: "off",
```

Uruchomić **właściwy produkcyjny** ecosystem dla `--only chaos --update-env`.
Nie zastępować całego prywatnego pliku przykładem repozytorium — zawiera również
inne ustawienia. Sprawdzić `/launch` 200 po starcie, panel World Discovery,
logowanie i pojedynczy zwykły skan; potem `pm2 save` po pozytywnym odbiorze.

## 3. Następny mały pilot

Po odbiorze OFF można ustawić w prywatnym ecosystemie tylko
`CHAOS_POI_DISCOVERY_MODE: "passive"`. To zapis agregatów zapotrzebowania,
bez nowego pobierania. Ingest/read nadal 0. Obserwować czas skanów, blokady
SQLite, rozmiar bazy i panel; błąd opcjonalnego zapisu nie powinien blokować gry.
Wyłączenie trybu zatrzymuje nowe wpisy, istniejące wygasają logicznie po 24 h.

Ingest/read wymagają odrębnego zakresu `world_storage`, potwierdzenia warunków
przechowywania i retencji oraz pomiarów zasobów. Bieżąca zgoda exact-cache nie
jest automatycznie rozszerzana. Nie ustawiać tych flag ani nie zmieniać zakresu
w ramach powyższego przygotowania. Nie ma jeszcze workera background do startu.

## Rollback

Wyłączyć nowe flagi w właściwym ecosystemie i przeładować tylko chaos.
Zachować kod kompatybilny ze schematami 1/2. Nie nadpisywać aktualnej bazy kopią
sprzed migracji po nowych skanach: cofnięcie księgi usunęłoby naliczone kredyty.
Nie kasować snapshotów, cache ani księgi jako sposobu na odblokowanie skanera.
Przy nieudanej migracji zachować backup i log, nie aktywować nowych funkcji.
