# 162/163 — przygotowanie schematu i etap pasywny

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
