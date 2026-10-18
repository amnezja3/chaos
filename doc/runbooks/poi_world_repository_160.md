# Sprint 160 — kontrolowane wdrożenie POI

Stan 2026-10-18: integracja lokalna przetestowana, **pierwsze wdrożenie wyłącznie
z flagami 160 OFF**. Nie jest to pełny produkcyjny PASS sprintu. Nie zmieniamy
efektywnych flag infrastruktury 158, UX 159, sesji, Identity Gateway ani wieku.

## Przed wysłaniem kodu

Commit obejmuje moduły i testy POI, integrację `poiFetchClass.py`/`run.py`, panel
administracyjny, narzędzia i dokumentację 160 oraz fixture referencyjne w tests.
Nie dodawać lokalnych baz, ZIP-ów z `artifacts`, sekretów ani automatycznych zrzutów
`.playwright-mcp`. Obejrzeć `git diff --stat` i `git status --short` przed commitem.

Dowody lokalne: 69 testów `test_poi*.py` PASS (65,309 s); cztery procesy współdzielą
jedno pobranie; niezależna referencja Overpass; Playwright admin PL/EN, 1440/390 px.
Nie wykonano aktywacji dostawcy produkcyjnego ani publicznego warmupu.

## Na VPS po push/pull

Sprawdzić commit, stan PM2 i ścieżkę faktycznie używanej bazy POI. Poniższy przykład
zakłada domyślne `data/poi_cache.sqlite3`. Jeżeli `CHAOS_POI_CACHE_PATH` wskazuje
inną ścieżkę, użyć jej. Nie podawać narzędziu bazy `game.sqlite3`.

```bash
cd ~/app/chaos
git pull --ff-only
git log -1 --oneline
.venv/bin/python -m unittest discover -s tests -p 'test_poi*.py'
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3
```

Przy dry-run oczekujemy `original_data_unchanged: true`, integrity i foreign keys
`ok`. Narzędzie nie pobiera danych i nie aktywuje żadnej flagi.

```bash
umask 077
export POI160_BACKUP="$HOME/chaos-backups/160-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$POI160_BACKUP"
git rev-parse HEAD > "$POI160_BACKUP/commit"
pm2 jlist > "$POI160_BACKUP/pm2-before.json"
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 \
  --apply --backup "$POI160_BACKUP/poi_cache.sqlite3"
```

Backup korzysta z SQLite backup API (uwzględnia zatwierdzony WAL). Dla nowej,
nieistniejącej bazy nie powstaje pozorny backup; narzędzie tworzy schemat.
Migracja dotyczy dodatkowych tabel w bazie POI; nie migruje kont ani świata gry.

Pierwszy restart web:

```bash
CHAOS_POI_WORLD_INGEST_ENABLED=0 \
CHAOS_POI_WORLD_REPOSITORY_ENABLED=0 \
CHAOS_POI_WIDE_FETCH_ENABLED=0 \
CHAOS_POI_PROVIDER_ADMIN_ENABLED=0 \
CHAOS_POI_PROVIDER_REGISTRY_ENABLED=0 \
CHAOS_POI_PROVIDER_MONITOR_ENABLED=0 \
pm2 restart chaos --update-env
```

Poczekać na `https://chaos.re/launch` HTTP 200, potwierdzić normalne wejście i
skanowanie. Niedostępność publicznego Overpass odróżnić od regresji aplikacji.
Nie traktować restartu web jako aktualizacji środowiska pozostałych workerów.
Monitor CLI pozostaje nieuruchomiony. `pm2 save` dopiero po odbiorze konfiguracji.

## Aktywacja w oddzielnym kroku

1. Włączyć wyłącznie `CHAOS_POI_PROVIDER_ADMIN_ENABLED=1` na web. Otworzyć panel
   deweloperski → POI. Sam odczyt panelu nie wysyła żądań do dostawców.
2. Operator zatwierdza źródło: URL, wspólna grupa operatora, warunki, dowód i termin
   przeglądu. Scope probe, normal_scan, storage i wide_fetch są niezależne.
   VK pozostaje pending bez rozstrzygnięcia. Poprawny probe nie zastępuje decyzji.
3. Probe wykonać dopiero po zatwierdzeniu jego scope. Następnie jawnie włączyć
   dostawcę. Alias tego samego operatora musi mieć tę samą grupę limitu/circuit.
4. Dopiero mając aktywne źródło zatwierdzone do normal_scan, przełączyć registry.
   Pusta lista registry nie wraca do starych adresów. Następnie osobno shadow
   ingest i odczyt world. Wide pozostaje OFF aż do decyzji o pilotażu.
5. Wide wymaga jednocześnie 158, registry, ingest i world read. Zakres skanera nie
   rośnie: pobranie obejmuje 1500 m wokół kotwicy komórki 0,002°, a wynik nadal
   jest filtrowany do pierwotnego promienia. Obsługiwany lokalnie promień ≤1000 m.
6. Brakująca/nieobsługiwana geometria powoduje exact fallback w pozostałym budżecie
   prób i z tym samym deadline. Nie przyznajemy dodatkowych prób. Zapis coverage
   jest chroniony osobnym lease komórki i transakcją; transport używa slotu 158.
7. Pilotaż wymaga odbioru VPS: skan → sąsiedni skan bez HTTP → restart → odczyt
   bez HTTP, koszty/tokeny GhostLab, właściwe markery i cichy koniec glitcha 159.
   Odbiór poza domeną geometrii objętą testami, realny rozmiar/WAL i wydajność
   pozostają otwarte. Nie włączać masowego zapełniania mapy.

## Limity i retencja

Aktualnie world przejmuje fresh/stale TTL istniejącego skanera. Domyślnie to
300/1800 s, o ile produkcja ich nie zmieniła. Trwałość po restarcie nie oznacza
bezterminowej zgody na stare dane. Dłuższy okres wymaga osobnej decyzji.
Sprzątanie usuwa wyłącznie wygasłe snapshoty, do 20 przy inicjalizacji world
w skanie; FK atomowo usuwa membership i coverage. Nie wykonuje VACUUM w żądaniu.
Limity istniejącego pliku SQLite/WAL pozostają bez podwyższenia. Wybranie kandydata
coverage poprzedza wczytanie payloadu, nie ładujemy całej bazy do RAM.

## Wycofanie

Wyłączyć sześć flag 160 i restartować web z `--update-env`. To zachowuje 158/159
i dane do diagnozy. Nie usuwać bazy ani plików WAL na działających procesach.
Jeśli konieczny restore: zatrzymać wszystkich użytkowników bazy POI, zachować
bieżący plik wraz z WAL/SHM w osobnym katalogu, odtworzyć sprawdzony backup SQLite
do nowej ścieżki, sprawdzić integrity/foreign_keys i skierować konfigurację na
ten plik. Nie nadpisywać aktywnej bazy i nie wykonywać rollbacku bazy graczy.

## Otwarte przed pełnym PASS

Zatwierdzenie rzeczywistych dostawców; pilotaż VPS i dane eksploatacyjne;
szersza geometria; pełne metryki p50/p95 i coverage, wersjonowany rollback
konfiguracji panelu oraz odbiór schedulera monitora. Te pozycje nie są oznaczone
jako wykonane przez sam lokalny PASS ani wdrożenie z flagami OFF.
