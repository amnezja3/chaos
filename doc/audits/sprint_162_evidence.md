# Sprint 162 — magazyn obserwacji, 23.10.2026

## Kolejny etap — dowód selekcji i planer lokalny

`world_read.py`: `SelectionProof` i `WorldReadPlanner`. Dowód zapisuje się
atomowo z payloadem i membership w istniejącym `world_coverage`. Nie ma
osobnej tabeli coverage ani automatycznej migracji w żądaniu gracza.

- EXACT: tylko identyczny query key, profil, selekcja, adapter, revision,
  wersja datasetu i zatwierdzony odnośnik przechowywania. Kompletna odpowiedź
  MapLark radius nie awansuje do pokrycia obszarowego.
- AREA: wyłącznie `bbox-intersects-full-v1` dla roads/waterways/inland_water/
  coastline, pełna geometria i osobny certyfikat dostawca–adapter–warstwa–
  selekcja podany przez zaufaną konfigurację serwera. Żaden realny adapter
  nie otrzymał takiego certyfikatu. Testy korzystają z jawnych fixtures.
- Wybór jednego snapshotu obejmującego cały bbox; bez union, bez zastępowania
  around przecięciem bbox. Sąsiedni obszar jest obsługiwany tylko dla tego
  jawnego kontraktu geografii, nie jako nowa semantyka skanera POI.
- Pusty kompletny wynik ma dowód; brak dowodu to MISS. Partial, niewspierany
  antymeridian, land_water i otwarte wybrzeże nie tworzą fałszywego COMPLETE.
- Fresh/stale/expired z jawną zgodą na stale, końcowym sprawdzeniem expiry,
  anulowania, prawa storage i revision. Cofnięta zgoda wyklucza odczyt.
  Flaga pozyskiwania `enabled` sama nie unieważnia odrębnego prawa storage,
  ale w tym konserwatywnym wariancie zmiana revision daje MISS. Wyłączenie
  przez normalne registry zwiększa revision i też unieważnia dotychczasowy
  odczyt; nie obchodzimy tego. Fixture disabled używa niezmienionej revision.
- Znana wersja datasetu jest przypięta w zapytaniu i dowodzie. Późniejsze
  pobranie starszych danych nie wypiera nowszej wersji. Nieznana wersja nie
  jest porównywana jako starsza/nowsza i nie miesza się ze znaną.
- Najwyżej 64 kandydatów metadata / 8 MiB payloadów / 1000 wyników domyślnie.
  Przekroczenie limitu to MISS, nie ucięty sukces. Deadline 2 s jest sprawdzany
  kooperacyjnie między etapami i przed zwrotem, nie jest twardym zabijaniem
  procesu GEOS. Budżety geometrii magazynu nadal obowiązują.
- Test przechodzi przez rzeczywisty POIFetcher i export_maplark: 74 obiekty
  przed i po zapisie dają identyczne 60 markerów. Brak nowych żądań HTTP,
  kosztów dostawcy, zmian gameplay i UI. To nie jest odbiór `/map-action` na VPS.

Granica wdrożenia: opcjonalny shadow ingest/read-through jest teraz podłączony
do skanera za flagami OFF. Produkcyjna decyzja MapLark nadal zezwala wyłącznie
na exact-cache. Wymagane przed ON: osobna decyzja world storage/retencji,
pomiary zasobów na VPS i odbiór produkcyjny integracji.
Nie trzeba włączać nowych API ani rozszerzać budżetu, aby kontynuować testy.

Testy planera: 16 PASS (5,335 s); wcześniejsza pełna regresja przed ostatnimi
dwoma przypadkami: 94 PASS (34,930 s). Końcowy pełny przebieg
`test_world_*.py`: **96 PASS (30,779 s)**. `git diff --check`: PASS.

## Integracja skanera — 23.10.2026

`world_shadow.py` nie tworzy schematu i nie wykonuje HTTP. Istniejący cache ma
pierwszeństwo, potem dokładny odczyt świata, następnie dotychczasowe pozyskanie.
Zapis świata następuje po poprawnym zapisie cache; błąd opcjonalnego zapisu jest
logowany bez danych zapytania i nie psuje poprawnego skanu. Stale świata jest
fallbackiem na dotychczasowej ścieżce awarii, po stale cache.

Wymagane są osobne flagi oraz zakres `world_storage`, oprócz istniejących
`normal_scan` i `storage`. Nie nadano zakresu na produkcji. TTL pozostaje
300/1800 s według istniejącej konfiguracji; nie ustanowiono nowej długiej retencji.
Włączony magazyn nie poświadcza kompletności sąsiednich skanów MapLark.

6 testów integracji PASS: cache-only grant, world hit po usunięciu cache,
błąd zapisu (w tym symulowany brak miejsca), błąd odczytu, rollback flag,
wyłączenie dostawcy. Pełny zestaw `test_world_*.py`: **107 PASS, 46,198 s**.

Playwright MCP, izolowany `tools/poi_browser_fixture.py --maplark-global --world`:
- PL desktop: skan zapisuje snapshot i zwraca marker;
- usunięcie exact cache: ten sam marker ze świata, licznik upstream nadal 1;
- EN mobile 390×844: wymuszony błąd publikacji świata, skan nadal sukces;
- konsola mapy: 0 błędów/ostrzeżeń. Przeglądarka i fixture zamknięte po teście.

Fixture używa prawdziwej ścieżki `/map-action`, mockowanego dostawcy i uproszczonej
mapy Leaflet. Nie jest dowodem produkcyjnej wydajności ani pełnego GhostLab.
Instrukcja kolejnego etapu: [runbook](../runbooks/world_repository_162_163.md).

Poniższa sekcja opisuje wcześniejszy etap magazynu; jego stwierdzenie o braku
planera zostało zastąpione powyższą implementacją. Pozostałe granice są aktualne.

Implementacja offline na polecenie operatora kontynuowania 161–163 po uruchomieniu
skanera MapLark. Nie wykonano zmian na VPS ani nowych żądań API.

## Wykonany zakres

- `world_storage.py` rozszerza istniejące `world_snapshot`/`world_member` w tej
  samej bazie. Nie tworzy drugiej bazy ani konkurencyjnego membership.
- Jawna migracja v1 → v2 zachowuje stare kolumny/wartości i dodaje tożsamość,
  indeks obwiedni, maskę warstw i digest obserwacji. Identyfikatory spoza OSM
  mają namespace dostawcy i NULL w osm_type/osm_id, nie fałszywe numery OSM.
- Snapshot pozostaje niezmienny; konflikty zachowują osobne obserwacje. Odczyt
  wskazuje konkretny snapshot, nie rozstrzyga świeżości przez fetched_at.
- Zapis atomowy pod lease i revision registry, jawny odnośnik do decyzji
  trwałego przechowywania oraz pochodzenie/licencja. Dotychczasowa decyzja
  MapLark na exact-cache NIE stanowi automatycznej zgody na trwały ingest.
- Round-trip Point/LineString/Polygon/MultiPolygon, otwory i obiekty spoza OSM.
  Coastline zachowuje kierunek; przekroczenie antymeridianu jest zachowane,
  ale wyłączone z lokalnego indeksu i zgłaszane jako unsupported.
- Odczyt regionu: bbox kandydatów + dokładne intersects, niezależne warstwy,
  ograniczona liczba kandydatów/bytes/wierzchołków i jawne truncated. Wynik
  zawsze zawiera coverage=UNKNOWN. Nie jest odpowiedzią kompletnego skanera.
- Limity bez podnoszenia: 128 MiB logicznego world, 5000 snapshotów; pojedynczy
  zapis ≤8 MiB (payload plus członkowie), ≤10000 obiektów/200000 wierzchołków.
  Odczyt ≤1000 kandydatów, ≤4 MiB/100000 wierzchołków. Indeks zwykły SQLite,
  bez założenia dostępności R*Tree. Limit fizyczny/WAL nadal z Repository 158.
- Istniejący `tools/poi_world.py --canonical` wykonuje domyślnie dry-run na
  kopii. Apply wymaga backupu istniejącej bazy; nie dotyka game.sqlite3,
  księgi kredytów, flag, sesji ani źródeł API.

## Granice i następny etap

Nie zamykamy 162: brak coverage certyfikującego sąsiedni skan, read planner,
automatycznego wyboru wersji/derived invalidation, shadow ingest, integracji
gameplay i panelu. Nie przyjmujemy, że MapLark radius daje dowód area-reusable.
Union i rekonstrukcja oceanów pozostają niewspierane. `land_water` nie powstaje
z samego coastline. Brak frontendowych zmian: w tym etapie nie wykonywano
nowych testów przeglądarki; wcześniejsze dowody UI należą do 161.

W następnym kroku: jawne dowody selekcji i praw per snapshot/warstwa, bounded
local planner oraz shadow zapis z niewpływającym na wynik skanu fallbackiem.
Kolejka/panel 163 następują po tych kontraktach. Nie ma jeszcze powodu wdrażać
schematu na VPS; obecny skaner działa niezależnie od tego rozszerzenia.

Rollback: nowy kod czyta schematy v1/v2; starszy kod sprzed tej zmiany odrzuca
world v2. Nie odtwarzać starej całej bazy na produkcji po nowych naliczeniach
kredytowych. Wyłączenie przyszłego world read/ingest zachowuje działający exact
cache i aktualną księgę; cofnięcie schematu wymaga osobnej migracji lub odtworzenia
kopii w izolowanej ścieżce. Nie zalecamy downgrade całej bazy.

## Weryfikacja

Testy obejmują migrację/idempotencję, stary odczyt/zapis, backup/restore,
przerwanie migracji i publikacji, fencing/revision/odwołanie zgody,
tożsamość dostawcy, cztery geometrie, dziurę jeziora i długą drogę,
antymeridian, partial/puste/unknown, konflikty, limity, corruption i cascade.
`test_world_*.py`: **79 PASS, 26,396 s** (63 dotychczasowe + 16 magazynu).
`test_poi_*.py`: **87 PASS, 86,450 s**. Po przeniesieniu przygotowania rekordów
poza transakcję i dodaniu sprawdzenia lease tuż przed commit: **17 testów magazynu
PASS, 11,672 s**, w tym rollback przy wygaśnięciu lease w trakcie publikacji.
Pełny wcześniejszy przebieg World miał 79 testów; z nowym przypadkiem zestaw ma
80 testów, ale nie raportujemy niewykonanego ponownego pełnego przebiegu jako PASS.
Pierwszy przebieg nowych testów ujawnił otwarte połączenia SQLite w fixture
na Windows; dodano jawne close w testach. Nie pominięto testów ani błędów.

`tools/world_storage_benchmark.py`, lokalnie Windows/Python, dane syntetyczne:

| Obiekty / wierzchołki | Normalizacja s | Publikacja s | Odczyt s | Payload + członkowie B | Strony bazy B | Python peak B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 / 250 | 0,9057 | 0,1239 | 0,0243 | 46091 | 167936 | 7078141 |
| 680 / 3400 | 0,6007 | 3,1281 | 0,2836 | 644079 | 1097728 | 5007995 |
| 3000 / 15000 | 6,3662 | 14,2185 | 0,5705 | 2867621 | 4583424 | 14771912 |

Tracemalloc mierzy alokacje Pythona, nie pełne RSS bibliotek natywnych. Publikacja
obejmuje walidację/serializację i transakcję; nie jest samym czasem blokady SQLite.
Pomiary wykonano przed przeniesieniem budowania rekordów poza transakcję;
stanowią baseline, a nie pomiar końcowej optymalizacji executemany.
WAL na końcu obserwacji: 0 B po zamykaniu połączeń; nie jest to pomiar szczytu WAL.
Pierwsza próbka obejmuje koszt importu geometrii. Dane nie są reprezentatywnymi
wycinkami miast ani gęstymi rzeczywistymi relacjami. Te pomiary NIE zamykają R08
ani benchmarku 162.0. Potrzebne dalsze pomiary czasu transakcji/RSS/WAL przed ON.
Nie zwiększono budżetu magazynu na podstawie tych wyników.
