# 163.5 — zbiorczy odbiór gotowego pakietu

Zakres: exact world między kontami/restartem, migracja popytu, wizyty i ograniczone
halo. Regionalny Overpass jest gotowy lokalnie, lecz wymaga odrębnej kwalifikacji
live/wide źródła. Nie jest to zamknięcie całego 163.5.

Nie włączamy regionalnego MapLark/Geoapify ani brakującego produktu ląd–woda.
Zbiorcze testy nie pobierają danych dostawców. Dopiero skan gracza lub aktywowany
kolektor wykonuje HTTP w ramach istniejących uprawnień i budżetów.

## 1. Jeden preflight — teraz

Po pushu przygotowanego wydania, na VPS:

```bash
cd ~/app/chaos && git pull --ff-only && bash tools/world_acceptance_163_5.sh preflight
```

Skrypt zapisuje commit, wyniki testów, dry-run migracji, inspekcję kopii SQLite,
wybrane flagi PM2 oraz sprawdza `/launch`. Nie restartuje ani nie zmienia bazy.
Oczekuje aktualnie odebranego routingu web=1 i workera online. Rozbieżność zatrzymuje
procedurę; nie wolno dopasowywać flag w ciemno. Nie wypisuje pełnego środowiska PM2.

W `storage.json`: integralność/FK OK, world schema 2, collection/metrics gotowe.
`visits_schema_ready=false` przed migracją jest dopuszczalne. Źródło MapLark
powinno być w `live_scan_sources` z `world_storage_allowed=true`. Brak tego prawa
nie jest naprawiany automatycznie; wymaga sprawdzenia istniejącej decyzji źródła.
Brak aktualnego świata (`snapshots=0`) nie jest błędem przygotowania.

## 2. Backup, migracja i sam zapis

Po przyjęciu preflight, w czystej powłoce bez testowych eksportów:

```bash
cd ~/app/chaos
umask 077
WORLD_BACKUP="$HOME/chaos-backups/163-5-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$WORLD_BACKUP"
git rev-parse HEAD > "$WORLD_BACKUP/commit.txt"
cp ecosystem.web.config.js ecosystem.discovery.config.js "$WORLD_BACKUP/"
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online > "$WORLD_BACKUP/runtime.json" &&
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics --apply --backup "$WORLD_BACKUP/poi_cache.sqlite3" &&
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_ingest --update-env &&
bash tools/world_acceptance_163_5.sh ingest
```

Migracja dodaje `origin`, zachowuje rozliczenia i stare wpisy. Nie zmienia bazy
graczy ani praw źródeł. Profil web ma global ingest=1, read=0, visits=0,
regional/wide=0, network pause=0, age=0. Kolektor pozostaje w dotychczasowym trybie.
Klucze zachowujemy w istniejącym prywatnym środowisku — nie wpisujemy do Git.

## 3. Jeden skan i odczyt drugiego konta

Wybrać uzgodniony punkt i promień 300 m dla obu kont. Przykładowy wcześniejszy
punkt operatora: 51.531034, 20.366130. Wykonać skan kontem A w grze. Wymagane
świeże pobranie oraz `poi_world_optional` ze `status=stored`, nie sam cache hit.

```bash
.venv/bin/python tools/world_storage_pilot.py --lat 51.531034 --lon 20.366130
```

Oczekiwane `COMPLETE_FRESH`. Jeśli MISS, nie czyścić całego cache ani zmieniać praw:
sprawdzić log zapisu/rewizję i faktyczne współrzędne. Następnie:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_read --update-env &&
bash tools/world_acceptance_163_5.sh read &&
.venv/bin/python tools/world_storage_pilot.py --lat 51.531034 --lon 20.366130 --evict-cache --apply
```

Narzędzie usuwa tylko cache tego dokładnego zapytania, wymaga świeżego świata i
nie usuwa snapshotu/księgi. Kontem B wykonać ten sam skan przed końcem 300 s.
W logu tego klucza musi być `source=world`, a markery i interakcje poprawne:

```bash
pm2 logs chaos --lines 100 --nostream 2>&1 | grep -E 'poi_maplark_cache|poi_route|poi_world_optional'
```

Reload powyżej już sprawdza przetrwanie snapshotu po restarcie procesu.
Dodatkowy restart/odczyt można połączyć z etapem wizyt, ponownie usuwając tylko
exact cache. Nie utrzymywać pozornej świeżości: po 300 s wynik może być stale,
po 1800 s wymagany fallback. Te granice sprawdzają deterministyczne testy lokalne.
Nie pauzujemy sieci wszystkim graczom podczas tego odbioru.

Nie porównywać wyłącznie sumy kredytów konta: kolektor pracuje niezależnie.
Dowodem jest źródło world dla danego klucza/skanu, nie wzrost liczby markerów.

Jeśli współrzędne faktycznego skanu różnią się od przykładu, użyć klucza z logu:
`tools/world_storage_pilot.py --key-prefix KLUCZ_12_ZNAKOW --evict-cache --apply`.
To alternatywa dla `--lat/--lon`, nie wyszukiwanie najnowszego skanu dowolnego
gracza. Wymaga jednego jednoznacznego klucza MapLark i świeżego zgodnego świata;
stary/niezgodny snapshot nie pozwala usunąć cache. Całą sekwencję skan → usunięcie
jednego cache → identyczny skan wykonać w 300 s, bez oczekiwania na odpowiedź
w rozmowie pomiędzy tymi krokami. Inny klucz nie jest testem exact world.

## 4. Wizyty, halo i odbiór gry

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_visits --update-env &&
bash tools/world_acceptance_163_5.sh visits
```

Odwiedzić nowy sektor bez skanu; panel popytu powinien pokazać sektor. Kolejne
odświeżenia profilu w ciągu minuty nie powielają zapisów. Potwierdzić skan,
hakowanie i terytoria na nowym i starym koncie.

Po odbiorze wizyt zmienić wyłącznie `CHAOS_POI_WORLD_HALO_ENABLED` z 0 na 1 w
`ecosystem.discovery.config.js` (zachować zmianę w repo), potem:

```bash
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --env regular --update-env &&
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-discovery-worker --lines 15 --nostream
```

Przy następnym naturalnym cyklu: `halo_added_cells` najwyżej 8; zadania direct
przed halo; nadal najwyżej jedno wywołanie/cykl. Brak zapytania jest poprawny,
gdy dane są już zebrane, brak praw, budżetu lub aktywnego popytu. Nie wymuszać
dodatkowych kosztów tylko dla uzyskania zielonego logu. Potwierdzić online/HTTP
i dopiero po odbiorze `pm2 save`.

Kolejne reloady web muszą wskazywać zaakceptowany profil `world_read` lub
`world_visits`. Zwykłe załadowanie domyślnego ecosystemu wyłącza nowe funkcje.

## Rollback i zakres dalszych prac

Wyłączyć halo w jego ecosystemie i przeładować worker z profilem regular.
Web: `pm2 startOrReload ecosystem.web.config.js --only chaos --env world_rollback
--update-env`, potem `bash tools/world_acceptance_163_5.sh rollback` i `pm2 save`.
Profil zachowuje działający routing=1, wyłącza ingest/read/visits/regional/wide.
Nie odtwarzać starego backupu nad nowymi operacjami księgi.

Odbiór A01–A04, A08–A09, A11–A12 dotyczy powyższych scenariuszy, nie całego sprintu.
A05 regionalny Overpass: osobny runbook i zatwierdzony live/wide zakres źródła.
Pełny regionalny MapLark/Geoapify, rzeczywisty MultiPolygon, produkt ląd–woda oraz
rozszerzenia atlasu/metryk z 163.5.5 pozostają otwarte. Nie ukrywa ich wynik PASS
tego pakietu ani udany skan z exact world.
