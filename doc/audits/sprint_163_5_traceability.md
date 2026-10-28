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

### Halo — pierwszy cykl produkcyjny PASS, 27.10.2026

Materiał operatora: `3214b36c-7266-4bb2-b4bc-058074c82be8/Pasted text.txt`.
Po zmianie PID kolektora z 23610 na 178484 cykl at=1793117642.9086847:
`halo_enabled=true`, `halo_added_cells=8`, `demand_origin=halo`,
`status=committed`, `network_calls=1`, provider Geoapify, profil POI.
Następny wpis jest `waiting`; liczba regionów wzrosła z 11 do 19.
Snapshot: `67d7a4d45c1cd2d8c553ed8febf01eb7ccfdc5a50c7a77b3be104578b4c2fcdb`.
Potwierdza aktywację halo, ograniczoną ekspansję i rzeczywisty zapis odpowiedzi.
Nie dowodzi samodzielnie pierwszeństwa direct przy równoczesnym zaległym popycie
ani zachowania wszystkich limitów w długotrwałym obciążeniu.

Monitor: 74 snapshoty, 1038076 bajtów, 53 COMMITTED / 3 FAILED_TERMINAL;
brak warnings. Przyczyn trzech historycznych niepowodzeń ten wycinek nie podaje.
Budżet dzienny: Geoapify 73/2700, MapLark 82/800, VK 4/120 prób.
Nowa operacja Geoapify ma rezerwację 6 i `estimated_upper_bound`, bez raportu
rzeczywistej ceny; pięć dawnych niepewnych operacji (25 kredytów) zachowano.
Coverage i kompletność Geoapify nadal UNKNOWN, gameplay_approved=false:
to archiwum obserwacji, nie dopuszczenie tego źródła do skanera gry.
W załączniku nie ma wyniku runtime checker ani `pm2 save`; utrwalenie profilu
po kontroli konfiguracji pozostaje krokiem operatora.

### Kolejny pakiet lokalny — heartbeat kolektora

Dodano odrębną, addytywną tabelę sygnału życia przez istniejącą migrację
`poi_world --canonical --jobs`. Tylko aktywny daemon --execute --serve rejestruje
instancję i odnawia sygnał. Plan i jednorazowe CLI nie przejmują wpisu.
Właściciel jest sprawdzany przy aktualizacji; stary proces nie nadpisze nowego.
Po utracie sygnału wynik unknown, nie domniemane online na podstawie zadań.
Brak tabeli i błędy telemetrii nie zatrzymują zbierania. Monitor read-only
i job_summary udostępniają stan bez tokenu właściciela i sekretów.

Lokalnie 27.10: **57 testów PASS, 27,781 s**. Pakiet: worker_heartbeat, regular_collection, bounded_collector,
discovery_runtime, dashboard, acceptance_163_5, release_package. Pokrywa
wygaśnięcie, zmianę właściciela, brak schematu, plan/CLI, zakończenie, błąd,
odczyt read-only i bramkę migracji. Bez ruchu do dostawców.
Instrukcja: `doc/runbooks/world_heartbeat_163_5.md`.
Prezentacja heartbeat w UI oraz pozostałe metryki/atlas nadal otwarte.

### Pakiet regionalny i atlas — 27.10.2026, lokalnie

Powyższy status UI zastępuje ten wpis. Wdrożenie/odbiór VPS nadal oczekuje.

| Element | Przygotowane i sprawdzone lokalnie | Granica potwierdzenia |
| --- | --- | --- |
| Atlas | Bbox przed limitem 100 snapshotów, stare regiony, puste certyfikaty, PL/EN/mobile | Nie jest mapą kompletności całej planety |
| Monitoring | Heartbeat w UI, unikalne zachowane identyfikatory, DB/WAL, p95 wieku oczekujących zadań | Przyrost dotyczy pierwszego wystąpienia w zachowanym archiwum, nie historii od początku gry |
| Regionalny Overpass | Wspólny budżet prób live/collector, lokalne odczyty bez zużycia, jawne rozszerzenie praw, profil ecosystem | Odbiór live/sąsiad na VPS przed zamknięciem A05 |
| Pełne POI w archiwum MapLark | Sześć filtrów CHAOS w bbox; commercial Geoapify nie zastępuje pełnego profilu | Obserwacja UNKNOWN, bez deklarowania równoważności radius |
| Ląd–morze | Ekstraktor przypiętego Natural Earth 5.1.1, rzeczywiste dwuczęściowe MultiPolygon, walidacja podziału | Uogólnienie 1:10 mln, bez użycia w grze; nie dowód inland_water MapLark |

Natural Earth: [land 1:10m](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/),
[public domain](https://www.naturalearthdata.com/about/terms-of-use/).
Pełny plik pobrano do ignorowanego `instance/provider-captures`; Git zawiera
wyłącznie małą próbkę regionalną z manifestem, SHA-256 i źródłem wersji.

Testy: 42 testy nowych/zmienionych komponentów oraz 179 testów regresji PASS.
Playwright MCP: izolowana aplikacja, PL desktop i EN desktop/mobile 390 px,
zoom i odczyt viewportu, czytelne liczniki, brak poziomego overflow i błędów
konsoli. Przeglądarka i fixture zamknięte. Brak prób produkcyjnych dostawców.

Jedna instrukcja wdrożenia, aktywacji i rollbacku:
`doc/runbooks/world_completion_163_5.md`. Nie zamykać całego 163.5 przed
odbiorami i brakującą kwalifikacją źródeł; Geoapify nadal nie jest pełnym
fallbackiem skanera, MapLark bbox nie jest certyfikatem selekcji radius.

### VPS 28.10.2026 — blokada testu metryk

Załącznik `ae7c54c0-7f18-48ab-9b75-af5e002f6402`: pull do 2a86718,
223 testy / 219,341 s, jeden FAIL. Proces potomny testu czterech writerów
otrzymał `sqlite3.OperationalError: database is locked` przy BEGIN IMMEDIATE.
To izolowana baza testowa; wynik nie dowodzi uszkodzenia produkcyjnej bazy.
Łańcuch `&&` zatrzymał się przed migracją dry-run.

Poprawka: wyłącznie zapis opcjonalnych metryk ponawia przejściowe BUSY/LOCKED
maksymalnie trzy razy, po rollbacku i zamknięciu połączenia. Pozostaje bazowy
busy_timeout 500 ms; odstępy 25/50 ms. Nie ponawiamy braku tabeli, błędów I/O
ani limitu WAL. Po wyczerpaniu prób finish nadal pomija telemetrię bez psucia
wyniku skanu. Testy obejmują rollback przed ponowieniem (bez podwójnego
naliczenia), limit prób i brak ponawiania innych błędów. Odbiór VPS wymaga
ponownego uruchomienia tego samego zbiorczego skryptu przed migracją.

Lokalnie: 34 testy PASS / 21,410 s (`world_dashboard`, `world_viewport`,
`world_routing`), w tym cztery procesy oraz nowe przypadki rollback/retry.

### Aktywacja regionalna VPS i poprawka 28.10

225 testów PASS / 219,637 s, migracja schema_ready, integrity/FK ok,
HTTP 200, runtime regional/halo zgodny. Heartbeat waiting świeży.
Backup aktywacji: `163-5-regional-20261028T083418Z/poi_cache.sqlite3`.
Nowy skan route revision 2: VK skipped/disabled, MapLark upstream success
w 2,4519 s. To PASS fallbacku, nie regionalnego odczytu.

Przyczyna w narzędziu: Registry.decision ustawia enabled=False; aktywator
nie wykonał następującego po decyzji Registry.enable. Poprawiono sekwencję
i wynik CLI zawiera enabled. Wznowienie dostawcy już wyłączonego możliwe
wyłącznie gdy ostatni wpis audytu jest własną decyzją tego aktywatora.
Ręczne disable lub późniejszy wynik techniczny nie jest omijany.
Ponowne wykonanie wymaga nowego backupu i jawnego --approve-live-wide;
nie wykonuje HTTP ani nie zeruje circuit/budżetu.

### Następny pakiet dowodów MapLark — 28.10

Po poprawce aktywatora VK: circuit_open, następnie http_read_timeout;
MapLark fallback sukces, całość 28,9269 s. Operator zapisał live route revision 3
z samym MapLark; następny skan maplark/upstream/success. Regionalny VK pozostaje
nieodebrany, nie jest automatycznie przywracany do skanera.

Lokalny `instance/provider-captures` ma próbki waterways/inland_water/topology
oraz Natural Earth; nie ma tam kompletnej pary pełne bbox POI + niezależne radius.
Nie wnioskujemy z tego o zawartości produkcyjnego archiwum.

Przygotowano `world_poi_evidence_acceptance.sh`: izolowane testy, ograniczona
inspekcja mode=ro, prywatny eksport geometrii i klasyfikatorów, aktywne podlimity,
monitor kolektora. Bez migracji, resetów księgi, ruchu do dostawców i przełączania
źródeł. 18 testów PASS / 7,273 s: exact/bbox, digest, ograniczenie objętości,
brak zapisów źródła, brak sekretów/kontaktów w eksportach, istniejące testy
kolektora i kandydatów. Instrukcja: `doc/runbooks/world_maplark_evidence_163_5.md`.
Kolejna zależność od VPS to konkretne zapisane dane, nie kolejny test dostępności API.

Otrzymano `chaos-poi-bbox-1635-NwQQJw/capture`: SHA-256 body
`45e89d529d63fda01e4dc5e87e1dcca200624f7e1a21cce50b7be57762bb972c`,
23 POI (13 Point/10 Polygon), complete, brak niepoprawnych geometrii, koszt 3.
Przygotowano niezależną próbę radius 300 m dla 51.53357,20.365. Dwie hipotezy
lokalne dają 18/17 obiektów (różnica osm:way:1028355440), bez przypadków
w pasie 2 m przy progu. W centrum bbox obie dawały 9, więc taki test nie
rozróżniałby ich. Metryka przybliżona służy diagnostyce, bez aktywacji readera.
24 testy PASS / 5,821 s; jednorazowe rozliczenie, walidacja parametrów,
brak zmian runtime, porównanie niezależnych ID/tagów/geometrii. Następny pakiet:
`tools/world_poi_radius_acceptance.sh`; istniejącego bbox nie pobieramy ponownie.

### 28.10 — niezależna para MapLark POI odebrana lokalnie

Radius body SHA-256: 6a339164b5b85a1597ca99045c2cac14f4d7a843a66fe2afe1ffb5499a8eb376.
23 bbox / 18 radius; pełna geometria 18/18, środek bounds 17/18.
Regresja sprawdza hashe, ID, geometrie, tagi oraz eksport markerów gry.
Zmiana tagów lub rewizji unieważnia observed_sample_pass. Porównanie pozostaje
offline, bez zapisu do produkcji i bez certyfikacji regionalnego skanera.
Fixture zawiera niezależne odpowiedzi operatora z atrybucją OSM; nie zawiera
kluczy, nagłówków żądania, kont graczy ani księgi kosztów. Do generalizacji
pozostają semantyka granicy promienia i geometrie nieobecne w tej próbce.

### 28.10 — runtime regionalnego MapLark, przygotowanie wdrożenia

Dodano jawny profil chaos-maplark-region-geometry-v1 oraz odczyt w aktywnej
ścieżce maplark_pilot po exact world, przed API. Profil jest lokalnym kontraktem
CHAOS, nie zapewnieniem pełnej zgodności natywnego radius. Włączenie osobnym
profilem ecosystem.web.config.js: world_maplark_region. Domyślnie wyłączony.
Jedna kompletna odpowiedź bbox, pełny filtr, digest, rewizja, prawa i TTL;
niepewna granica, częściowość, zmiana wersji lub brak pokrycia uruchamia fallback.

8 testów regionalnych PASS: realna para, otwory/multipart, mixed-source,
niepełne i poza regionem, pusto, aktywny skaner bez HTTP, read-only, opt-in,
corruption i wygaśnięcie 300/1800. Regresje: exact world 10 PASS, planner 16 PASS,
routing 15 PASS; MapLark zestaw przed dodaniem ostatnich 3 testów 21 PASS.
Konfiguracja aktywacji/rollback sprawdzona przez Node, git diff --check PASS.
Bez zmian produkcji i bez wywołań dostawców.

Instrukcja: doc/runbooks/world_maplark_region_release_163_5.md.
Pakiet VPS: tools/world_maplark_region_acceptance.sh. Odbiór regionalnego runtime
wymaga osobnego logu poi_maplark_region oraz działania gry; sam source=world
z exact readera go nie zastępuje. Kwalifikacja pełnego skanera Geoapify pozostaje
zewnętrznym brakiem, nie oznaczamy całego 163.5 jako odebranego.

### 28.10 — zaakceptowany kontrakt CHAOS geometry-v2

Operator jawnie zatwierdził deterministyczną selekcję pełnej geometrii zamiast
odrzucania całego skanu przez obiekt w pasie 5 m. PROFILE zmieniony na
chaos-maplark-region-geometry-v2; wybór distance <= radius w opisanej lokalnej
metryce planarnej. Nie deklarujemy zgodności wszystkich przypadków z API radius.
Kontrole kompletności, bbox, provenance, rewizji, praw i TTL pozostają.
Margines pokrycia bbox zachowany. Flaga v1 nie włącza v2; aktywacja przez
istniejący profil env_world_maplark_region, rollback env_world_regional.

Włączono minimalny fixture Paryża: 826 pełnych geometrii/OSM ID z wyłącznie
klasyfikacyjnymi tagami; usunięto opisy i kontakty. Selekcja: 479/465 obiektów
w dwóch przesuniętych punktach, przed gameplay limit 60. Oryginalny capture
pozostaje w ignored instance/provider-captures, z SHA opisanym przy fixture.
44 testy PASS: regionalny reader 10, odbiór Paryża 9, router 15, exact world 10.
Sprawdzono shell syntax pakietu i aktywację/rollback ecosystem przez Node.
Zero wywołań API i zmian produkcyjnej bazy. Nie odmładzamy istniejących danych.
Odbiór live nadal wymaga świeżego regionu; nie uruchamiamy ponownie compact-v3.
