# 163.5 — mapa wymagań i dowodów

26.10.2026. To mapa pokrycia i pozostałych odbiorów, nie deklaracja PASS wszystkich
historycznych scenariuszy. Nazwy testów wskazują istniejący materiał do weryfikacji;
wykonane zestawy są zapisywane osobno. Dowody VPS: odbiory i capture 161–163.

| Wymagania pierwotne | Materiał / wykonanie 163.5 | Pozostały odbiór |
| --- | --- | --- |
| C01, C02 | test_world_contract, adaptery, test_world_maplark_candidate | Macierz pełnego profilu Geoapify w 163.5.2 |
| C03, C07 | test_world_maplark_pilot, eksporty, odebrana gra na dwóch kontach | Regresja po globalnym local-read, A11 |
| C04, C05 | test_world_contract, test_world_geoapify, test_world_region_compare | Regionalny POI nie jest jeszcze potwierdzony, 163.5.2 |
| C06 | test_world_transport, test_poi_secure_transport, test_world_routing | Regresja uprawnień i rewizji w pakiecie A08 |
| C08 | test_world_credit_budget, test_world_upstream_priority, test_world_concurrency_benchmark | Zbiorczy odbiór współbieżności i dwóch kont A04/A11 |
| C09 | test_poi_masa, test_poi_masa_route, dotychczasowy odbiór mapy | Regresja komunikatów przy local/miss/fallback |
| G01–G04 | test_world_contract, test_world_land_water, rzeczywiste water holes i roads | W oryginale opisane łącznie: kontrakt, izolacja profili, topologia, lineage. Realny multipart i produkt land_water: 163.5.4 |
| R01 | test_world_storage, dotychczasowe migracje/backupy VPS | Pierwszy pakiet nie zmienia schematu; kontrola backup/restore A01/A12 |
| R02 | test_world_storage, test_world_discovery_jobs | Regresja lease, niepełnego batch i awarii opcjonalnego zapisu |
| R03 | test_poi_geometry, test_world_read, test_world_region_reference | Regionalny POI i jawny brak union, 163.5.2 |
| R04 | test_world_global_access: exact MapLark/Overpass, pause sieci, niezależne instancje | Sąsiedni POI nadal otwarty; VPS A03–A05; pause sieci nie jest cofnięciem prawa do danych |
| R05 | test_world_read, test_world_global_access | Pusty exact i expiry lokalnie; regionalne braki kategorii w 163.5.2 |
| R06 | test_world_concurrency_benchmark, test_world_routing, wspólne lease/budżety | Cztery procesy/20 żądań dla nowej ścieżki, oddzielnie od testu czterech instancji w jednym procesie |
| R07, R09 | Potwierdzona gra po poprzednim rollout; testy/browser mapy | Nowy zbiorczy odbiór A11 i Playwright |
| R08 | test_poi_wal_guard, test_world_storage, test_world_shadow | Pomiary ograniczeń nowej ścieżki i monitoring 163.5.5 |
| R10–R13 | test_world_storage, test_world_read, test_world_land_water, regionalne capture | W oryginale opisane łącznie; realny produkt land_water, multipart i regionalny restart/restore A10 |
| R14 | test_world_read, test_world_region_pilot | Regionalne empty/expiry/izolacja warstw i A06 |
| R15 | test_world_dashboard, podgląd atlasu | Zapytania viewport/agregaty 163.5.5 |
| D01 | test_world_discovery_jobs, test_world_discovery_queue | Uzupełniony producent popytu 163.5.3, A09 |
| D02 | test_world_upstream_priority, test_world_discovery_budget | Wspólny test obciążenia i ograniczony halo 163.5.3 |
| D03 | test_world_credit_budget, test_world_acquisition, test_world_routing | Nowy pause skanera nie zastępuje stopu kolektora; sprawdzić oba osobno |
| D04 | test_world_routing, test_poi_admin, test_poi_secure_transport | A08/A12 dla nowego ogólnego trybu |
| D05 | Poprzedni odbiór panelu PL/EN desktop/mobile | Nowe stany i atlas: 163.5.5, bez HTTP dostawców |
| D06 | Dawny pilot exact VPS, nowe test_world_global_access | Globalny A02–A04/A12 nadal czeka na wdrożenie |
| D07 | Odbiór skan/hack/terytoria na obu kontach | Powtórzenie po nowym rollout, A11 |
| D08 | Istniejące pomiary syntetyczne i monitor kolektora | Ustalenie okna/progów SLO i obserwacja produkcyjna |
| D09–D12 | discovery queue/worker, regionalne pilotaże, land_water testy | W oryginale opisane łącznie: demand, priority, warstwy/restart, dependencies. Ruch bez skanu/halo/land_water: 163.5.3–4 |
| D13 | test_world_credit_budget, test_world_dashboard, zachowane uncertain | Ciągła obserwacja rozbieżności; nie zerować rezerwacji |
| D14 | Budżety atomowe, progi panelu, test_world_global_access | Współbieżny odbiór nowej ścieżki; local działa bez nowego kosztu |
| D15 | Dotychczasowy atlas i testy browser | Viewport i pełne stany 163.5.5 |
| D16 | Istniejące metryki skanera/dashboard | Agregaty unikalnych obiektów i przyrostu 163.5.5 |

## Inwentarz danych do wykorzystania

- Fixture referencyjne Overpass i geometria graniczna już znajdują się w tests/fixtures/poi.
- Capture MapLark roads: pilot 75 obiektów po wykluczeniu envelope false positive;
  nie dowodzi regionalnego pokrycia pełnych kategorii POI.
- Rzeczywiste waterways/inland_water oraz Polygon z otworami: istniejące capture
  i testy world_region_water_reference / world_region_water_holes_reference.
- Geoapify commercial: rzeczywiste 63 Point, nie pełny profil CHAOS.
- Produkt powierzchni ląd–woda i realny multipart: brak potwierdzenia w audycie;
  najpierw przejrzeć wszystkie lokalne capture, potem kwalifikować źródło.
- Prywatne capture i pliki body/headers operatora pozostają poza tym commitem.

## Pierwszy pakiet kodu

Dodano jawny `CHAOS_POI_WORLD_ACCESS_MODE=pilot|global|off` (domyślnie pilot),
nie zmieniając warunku samego pilota. Ingest/read pozostają osobnymi flagami.
Globalny exact odczyt MapLark i aktywnego routera Overpass korzysta z istniejącego
WorldReadPlanner. Pauza `CHAOS_POI_SCAN_NETWORK_PAUSED=1` zatrzymuje nowe pobrania
skanera przy zachowaniu ważnych cache/world; nie zatrzymuje osobnego kolektora,
nie anuluje już wysłanego żądania i nie zmienia uprawnień źródła.
W globalnym trybie archiwizacja do 7 dni, ograniczona terminem decyzji źródła;
świeżość i dopuszczalny stale skanu nadal 300/1800 sekund.

Status: kod lokalny. Bez wdrożenia i bez nowego ruchu do dostawców.
Nie zamyka 163.5.2–163.5.5 ani całego 163.5.1 przed odbiorem VPS.

Wykonano 26.10: **87 testów PASS** — world_global_access (11), world_shadow,
world_pilot_scope, world_routing, world_read, world_maplark_pilot i poi_infrastructure.
Transport dostawców mockowany; test infrastruktury dodatkowo używa izolowanego
serwera loopback. Brak zewnętrznych wywołań dostawców. `git diff --check` PASS.
Nie wykonywano nowego testu UI: ten pakiet nie zmienia interfejsu.

## Drugi pakiet — regionalny Overpass i wspólny popyt

26.10.2026: `routed_region` łączy istniejącą pełną topologię i selektor 160 z
aktywnym routerem. Osobny profil, kontrola provider/revision/reference, atomowa
publikacja, bounded odczyt, retencja i wspólny fill lease. Sąsiednie zapytania
origin/nearby/edge/small/larger porównano z zapisanymi niezależnymi odpowiedziami
Overpass. Referencja empty leży poza regionem — poprawnie nie jest uznawana za
pokrytą. Osobny test pustej pełnej odpowiedzi sprawdza ponowny pusty wynik lokalny.

Test czterech procesów: jeden mockowany request fill i cztery poprawne odpowiedzi.
Regresja uszkodzenia danych i metadanych, odwołania uprawnień, expiry, wyłączenia
regionalnej flagi i awarii opcjonalnego zapisu. Wspólny popyt rejestrowany raz na
`Service.fetch`, także dla Overpass/world. Ruch bez skanu i halo nie są ukończone.

**88 + 28 = 116 testów PASS**: routed_region, poi_wide_fetch, poi_world,
global_access, routing, shadow, discovery_queue, poi_infrastructure oraz
poi_geometry_storage, world_storage, archive_retention, collection_retention.
Bez wywołań dostawców; transport mockowany/loopback. Nowa konfiguracja OFF.
Instrukcja: [regionalny odbiór](../runbooks/world_regional_read_163_5.md).
Nie deklarujemy pełnego odbioru R04/R06 na produkcji ani regionalnego MapLark/Geoapify.

## Trzeci pakiet — wizyty i jeden pierścień sąsiadów

26.10.2026: dodano popyt po zatwierdzonym zapisie pozycji oraz przy odczycie
kanonicznej pozycji do profilu, bez wymogu skanu. Agregacja sektor/warstwa,
60 sekund deduplikacji również pomiędzy procesami, bez danych kont i tras.
Jawna migracja dodaje `origin`; stary schemat nadal przyjmuje bezpośredni popyt.
Halo wymaga migracji i osobnej flagi: czterech sąsiadów, maksymalnie 8 nowych
sektorów/cykl, maksymalnie 480 wpisów halo w istniejącej kolejce. Brak rekurencji,
odnawiania halo przez ekspansję i osobnej księgi kosztów. Odwiedzony sektor jest
promowany; rotacja zachowuje pierwszeństwo bezpośrednich zadań.

Testy obejmują zapis po sukcesie/odrzuceniu ruchu, cztery równoległe procesy,
granice współrzędnych, limity kolejki, expiry, brak HTTP w planie, jedną próbę
sieciową na cykl i regresję dotychczasowego kolektora. **60 testów PASS** w
zestawie visits_halo, discovery_queue, regular_collection, discovery_producer,
discovery_worker, collection_retention i detention_movement.

Pełny zestaw z `world_local_read_acceptance_163_5.sh`: **163 testy PASS**
(86,9 s lokalnie). Dostawcy mockowani, jeden serwer loopback; brak wywołań
zewnętrznych API. Node potwierdził wyłączone nowe flagi w obu ecosystemach.

Nowe flagi OFF w ecosystem web/discovery. Bez aktywacji i odbioru VPS.
Instrukcja: [wizyty i halo](../runbooks/world_visits_halo_163_5.md).
Nie zamyka to regionalnego pełnego POI ani pozostałych danych geograficznych.

## Pakiet odbioru — 27.10.2026

Przygotowano jeden preflight: testy izolowane, dry-run migracji, inspekcja kopii
SQLite, allowlista PM2 i gotowość HTTP. Nowe profile ecosystem web rozdzielają
ingest/read/visits/rollback; wszystkie zachowują regional/wide/pause=0 i age=0.
Zwykły reload nie aktywuje nowego trybu. Kontrola stage odrzuca inną konfigurację
i nie wypisuje sekretów. Kolektor ma pozostać w odebranym trybie regular.

34 testy PASS: acceptance_163_5, release_package, dashboard, bounded_collector,
discovery_sector. Sprawdzono Node'em rzeczywiste cztery profile ecosystem oraz
składnię obu skryptów Bash. Nie wykonano PM2/reload na lokalnym Windows ani
odbioru produkcji. Brak zmian UI; bez nowego testu przeglądarkowego.

Pełny aktualny zestaw izolowanego odbioru: **171 testów PASS, 77,3 s**.
Transport dostawców mockowany; test deadline używa serwera loopback i może
zalogować zamknięcie połączenia przez klienta. Bez rzeczywistych wywołań API.

Źródło world wykazywane w inspekcji jako osobne uprawnienie, nie wywnioskowane
z liczby snapshotów. Instrukcja wymaga world hit tego samego klucza po usunięciu
wyłącznie jego cache, drugiego konta i restartu. Stare nierozliczone operacje
pozostają w księdze. [Instrukcja zbiorcza](../runbooks/world_acceptance_163_5.md).

## VPS preflight — 27.10.2026, 87ee955

Operator przekazał wynik `world_acceptance_163_5.sh preflight`:
171 testów PASS (169,421 s), dry-run bez zmiany danych, integrity/FK OK,
schema v2, metrics/collection gotowe. `visits_schema_ready=false` zgodne ze
stanem przed migracją. MapLark revision 9 ma normal_scan i world_storage.
Web i worker online, routing=1, ingest/read=0, age=0, HTTP 200.
Raporty: `/home/johndoe/chaos-163-5-acceptance-60qJey`.

33 snapshoty obserwacyjne nie stanowią dowodu użycia świata przez skaner;
metryki wskazują 5 skanów sieciowych i zero world hits. Kolektor: 21 COMMITTED,
1 FAILED_TERMINAL (VK waterways / overpass_backoff), brak oczekujących lease
i nierozstrzygniętych zadań. Pięć niepewnych operacji Geoapify pozostaje w księdze.
Preflight odebrany; migracja, aktywacja ingest i dowód exact world nadal przed nami.

### Dalszy odbiór VPS

Migracja i ingest/read profiles przeszły kontrole; world schema v2 i visits schema
gotowe, integrity/FK OK, routing=1, access=global, ingest/read=1, age=0.
Backup: `/home/johndoe/chaos-backups/163-5-20261027T063503Z`.
Raporty ingest/read: `chaos-163-5-acceptance-dvnF65` / `chaos-163-5-acceptance-GIPQsn`.
Po timeoutach startowych ostatecznie HTTP 200; nie uznajemy tego za pomiar SLO.

Skan eaf380235e5e: store=stored, ręczny planner potwierdził COMPLETE_FRESH,
single_snapshot, 19 obiektów, 0 HTTP. Kolejny skan 33ef97af83f0 nastąpił po
310,474 s i miał inny klucz; upstream nie dowodzi usterki exact read.
Brakuje jeszcze world hit w rzeczywistym skanerze dla tego samego świeżego
zapytania, po selektywnym ominięciu cache. CLI otrzymało wybór po kluczu logu,
bez założenia współrzędnych i bez zmiany czasu świeżości.

### Exact world przez endpoint gry — PASS, 27.10.2026

Operator powtórzył identyczny POST `/map-action` dla uzgodnionego punktu:
klucz `3e284b592d56`, revision 9. Upstream: PID 125175, at 1793114396.153;
cache fresh: PID 125176, at 1793114507.429. Narzędzie usunęło dokładnie jeden
wpis cache, potwierdzając COMPLETE_FRESH / 5 obiektów i niezmienioną księgę/świat.
Następny skan: `source=world`, PID 125171, at 1793114586.571 (190,418 s od pobrania).
Odpowiedź przeglądarki: HTTP 200, `poi_data_mode=world`, 17 markerów odpowiedzi gry.
Liczba markerów gry nie jest liczbą surowych obiektów w snapshotcie.

Potwierdzono rzeczywistą ścieżkę endpointu gry i odczyt między różnymi workerami,
bez nowego pobrania POI dla tego skanu. Materiał nie potwierdza osobnego drugiego
konta ani restartu pomiędzy tą parą skanów. Nie stanowi też odbioru regionalnego
POI dla sąsiednich kliknięć. Kolejny etap: aktywacja/odbiór wizyt bez skanu.

### Profil wizyt — konfiguracja VPS PASS

Operator uruchomił `world_visits`: ingest/read/visits=1, access=global,
regional/wide/pause=0, age=0; web i kolektor online. Schema visits gotowe,
integrity/FK OK, 53 snapshoty. Po dwóch timeoutach startowych HTTP 200.
Raport: `/home/johndoe/chaos-163-5-acceptance-51TsjG`.
To odbiór konfiguracji; rzeczywiste odwiedzenie sektora bez skanu wymaga jeszcze
porównania kolejki przed i po ruchu konta testowego.

### Wizyta bez skanu — PASS, 27.10.2026

Operator potwierdził ruch konta testowego i odświeżenie mapy bez skanowania.
Sektor (2032, 5167): przed ruchem brak wpisów; po ruchu sześć warstw
`coastline`, `inland_water`, `land_water`, `poi`, `roads`, `waterways`, każda
z `origin=direct`, `hits=1`, `last_seen=1793115177.9316103`.
Potwierdza rejestrację popytu przez wizytę; nie jest dowodem pobrania warstw.

Następny etap: halo przez jawny profil `regular_halo` ecosystemu kolektora.
Profil zachowuje politykę i wspólne budżety `regular`; rollback do `regular`
ustawia halo=0. Kontrola PM2 przyjmuje `--halo 1` / `--halo 0`, bez ujawniania
sekretów. Lokalnie: 29 testów runtime/regular collection/visits/halo/release PASS.
Aktywacja i odbiór halo na VPS pozostają do wykonania.
