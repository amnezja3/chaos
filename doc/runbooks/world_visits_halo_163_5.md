# 163.5.3 — wizyty i ograniczony pierścień sąsiadów

Pakiet lokalny, bez aktywacji na produkcji. Korzysta z obecnej DemandQueue,
kolektora, routingu, księgi, lease i potwierdzeń odświeżania.

## Zachowanie

- `CHAOS_POI_WORLD_VISITS_ENABLED=1` w `ecosystem.web.config.js` oraz tryb
  discovery `passive`: zapis po zatwierdzeniu pozycji przez wspólną funkcję
  aktualizacji oraz przy nałożeniu pozycji kanonicznej na profil. Alternatywne
  ścieżki ruchu są zauważane przy kolejnym wczytaniu profilu.
- Kolejka zawiera sektor 0,01 stopnia i warstwy, bez konta, sesji, trasy czy
  dokładnych współrzędnych. Powtórne wizyty sektora scalane przez 60 sekund,
  również pomiędzy workerami. Skan nadal rejestruje bezpośredni popyt niezależnie.
- `CHAOS_POI_WORLD_HALO_ENABLED=1` w `ecosystem.discovery.config.js`: regularny
  kolektor dodaje maksymalnie 8 sektorów na cykl, wyłącznie czterech bezpośrednich
  sąsiadów odwiedzonych sektorów. Nie rozwija sąsiadów sąsiadów.
- Maksymalnie 480 wpisów halo (80 sektorów przy sześciu warstwach), w ramach
  istniejącego limitu 2000 wpisów kolejki. Halo nie usuwa bezpośredniego popytu.
  Wizyta promuje sektor halo do bezpośredniego. Termin halo nie przekracza
  terminu sektora źródłowego; ekspansja nie odnawia istniejących wpisów.
- Zadania bezpośrednie mają pierwszeństwo; rotacja działa wewnątrz poziomów.
  Nadal maksymalnie jedno zapytanie dostawcy na cykl, istniejące limity budżetu,
  retencja i odświeżanie archiwum 7 dni. Halo nie stanowi dowodu pokrycia.
- Obie nowe flagi domyślnie `0`. Brak tabeli lub błąd kolejki nie blokuje ruchu.
  Plan kolektora nie tworzy sąsiadów i nie wykonuje HTTP.

## Zbiorczy odbiór po wdrożeniu kodu

1. Uruchomić `bash tools/world_local_read_acceptance_163_5.sh` — izolowane bazy,
   mockowane źródła, bez kredytów i bez zmiany konfiguracji produkcji.
2. Przeprowadzić istniejący dry-run `tools/poi_world.py --db data/poi_cache.sqlite3
   --canonical --discovery --jobs`, następnie tę samą migrację z `--apply`
   i `--backup` wskazującym nowy plik. Dodawana jest kolumna `origin`, stare
   wpisy pozostają bezpośrednie. Migracja nie włącza funkcji ani źródeł.
3. W osobnym etapie aktywować wizyty w ecosystem web, przeładować proces przez
   właściwy ecosystem i odwiedzić nowy sektor bez skanu. Sprawdzić przyrost
   popytu, brak przypisania kont oraz brak powielania wpisów przy odświeżaniu.
4. Aktywować halo w ecosystem discovery dopiero po migracji; przeładować worker
   z profilem `regular_halo`. Profil `regular` jawnie wyłącza halo i służy też
   do wycofania tej aktywacji. Monitor pokazuje `halo_added_cells` oraz
   `demand_origin` dla wybranego zadania. Potwierdzić limity i pierwszeństwo
   skanowania gracza. Nie nadawać przy tym nowych uprawnień dostawcom.
5. Wycofanie: obie flagi `0`, przeładowanie odpowiednich ecosystemów. Istniejące
   halo nie jest wybierane przez regularny kolektor; wpisy wygasają normalnie.

Ten pakiet nie włącza odczytu świata ani regionalnego skanera. Odbiór produkcyjny
wizyt/halo jest osobny od lokalnych testów. UI nie zmieniono.
