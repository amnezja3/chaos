# Sprint 161 — stan realizacji 23.10.2026

## Najnowszy wynik — pakiet kontrolowanego pilota

Po decyzji operatora „zrób żeby było dobrze, potrzebujemy tego co ma CHAOS”
przyjęto osobny profil `maplark-radius-bounds-v1`. Nie wymaga identycznej
selekcji z Overpass: zapytanie promienia rozstrzyga MapLark, markery ways i
relations używają środka obwiedni geometrii. OSM ID, oryginalne tagi, porządek
node/way/relation + ID, kategoryzacja, limit 60, deduplikacja i mechaniki
konsumentów pozostają. Jest to świadoma semantyka dostawcy, nie „PASS parity”.
Niepełna odpowiedź, błędna geometria, antymeridian i nieobsługiwany typ geometrii
nadal dają błąd całego skanu. W szczególności MultiLineString nie jest jeszcze
obsługiwany; nie gubimy po cichu części relacji.

- Rzeczywista próbka: 680 obiektów -> 680 eksportowanych rekordów -> 60 markerów
  w niezmienionej fasadzie POIFetcher. Szczegóły w
  `sprint_161_maplark_profile_20261023.json`. Nie wykonano dodatkowego HTTP.
- Pilot jest domyślnie wyłączony i ograniczony do loginów z konfiguracji serwera.
  Klient nie wybiera dostawcy. Wymagane są istniejące decyzje registry, sprawny
  test dostawcy, storage scope, okno budżetu oraz jawna akceptacja kosztu zmiennego.
- Ponowne użycie: ta sama baza POI, exact-cache z odrębnym kluczem profilu/revision,
  lease zapytania i globalny upstream slot, circuit i deadline 35 s. Brak retry,
  background fetch i world ingest. Wyłączenie dostawcy blokuje także jego cache.
- Księga zapisuje rzeczywiste naliczenie także dla HTTP error i złej odpowiedzi;
  timeout/brak nagłówka zachowuje rezerwację. Naliczenie ponad rezerwację wstrzymuje
  następne zapytania. Rezerwacja nie jest limitem ceny wymuszonym u dostawcy.
- Narzędzie `tools/world_discovery_pilot.py`: dry-run domyślnie; prepare/probe/
  enable/disable/status. Prepare nie aktywuje dostawcy i nie resetuje okna przy
  ponownym uruchomieniu. Proponowany pilot: 24 h, 100 kredytów wewnętrznego budżetu,
  rezerwacja 20 na zapytanie; ustawienia do akceptacji przed uruchomieniem.

Weryfikacja lokalna: **51 testów World Discovery PASS; 87 regresji POI PASS**.
Playwright MCP na izolowanym `tools/poi_browser_fixture.py --maplark`:
produkcjny handler `/map-action` i JavaScript mapAction, kontrolowana odpowiedź
HTTP zastąpiona fixture. Zwykły skan pokazuje marker; ponowny skan i GhostLab
korzystają z cache (licznik pozostał 1). Odpowiedź ucięta daje api_error;
pusty kompletny wynik daje empty i usuwa markery. Brak błędów konsoli.
To test komponentu i ścieżki aplikacji, nie pełnej mapy Leaflet ani API live.

**Do wykonania na VPS: probe z rzeczywistym kluczem, aktywacja dla jednego konta,
odbiór skanu w grze. Globalny rollout nie jest aktywowany.** Instrukcja:
`doc/runbooks/world_discovery_maplark_pilot_161.md`.

Poniższa chronologia zachowuje wcześniejsze badanie ścisłej zgodności Overpass;
jego odrzucony podgląd nie jest już bramką nowego profilu MapLark.

## Aktualizacja po pierwszym pobraniu z VPS

Pakiet `4885c96` wypchnięty i pobrany na VPS. Operator przekazał wynik jednej
próby MapLark v3: HTTP 200, 3,097 s, raportowane 9 kredytów, 680 obiektów.
Dekoder: 417 Point, 2 LineString, 261 Polygon; 680 memberships POI, dodatkowo
1 roads i 1 inland_water (warstwy nakładają się, nie sumować ich jako obiektów).
Kompletność odpowiedzi według dekodera i nagłówków: complete, reasons=[];
`selection=maplark-radius-unverified`, `gameplay_approved=false`.
Jedno wywołanie API; bez aktywacji gameplayu i world ingest. Wewnętrzne
`inspection.network_calls=0` dotyczy analizy już pobranych danych, nie pobrania.

To dowód udanej pojedynczej próby transportu/dekodera, nie PASS PROVIDER,
PASS LIVE SCANNER ani pomiar stabilności. 9 kredytów pochodzi z odpowiedzi
dostawcy, nie niezależnego uzgodnienia salda konta. Nie utożsamiać 680 obiektów
z wcześniejszymi 679 Overpass: pomiary wykonano w różnych momentach, więc
różnica liczebności sama nie wskazuje regresji ani zgodności.

### Analiza otrzymanego pliku — 23.10.2026

Operator przekazał nagłówki oraz pełny FeatureCollection w załączniku tekstowym.
Oba dokumenty sparsowano offline; po FeatureCollection nie pozostały żadne
niebiałe znaki. Wyniki i skróty źródła zapisano w
`doc/audits/sprint_161_maplark_sample_20261023.json`. Nie wykonano kolejnego HTTP.

- Nagłówki: X-Returned=680, X-Has-More=false, X-Usage-Units-Charged=9.
  Normalizacja przyjęła 680 unikalnych tożsamości: 417 node i 263 way.
- Geometrie: 417 Point, 2 LineString, 261 Polygon, łącznie 2232 wierzchołki.
  W tej próbce nie ma relation ani MultiPolygon; nie potwierdza ich obsługi live.
- Zachowane tagi obejmują 3 surveillance, 6 amenity=atm, 2 internet_access,
  29 addr:city. 579 obiektów nie ma name — nie wolno usuwać ich z tego powodu.
  Próbka nie potwierdza wariantu atm=yes.
- Sprawdzenie odległości punktów i granic geometrii istniejącymi funkcjami
  sferycznymi nie wykazało obiektu poza promieniem 300 m. Nie jest to dowód
  pełnej równoważności selekcji dostawcy: brakuje referencji tego samego snapshotu
  oraz przypadków relacji i geometrii granicznych.
- Kolejność MapLark nie jest rosnąca po OSM ID. Diagnostyczny eksport punktów
  i środków bounding box dla ways przepuszczono przez rzeczywisty POIFetcher:
  wariant kolejności dostawcy i wariant type/ID zwróciły po 60 markerów, lecz
  miały tylko 59 wspólnych ID i różną kolejność. To porównanie dwóch wariantów
  na tej samej próbce, nie porównanie z żywą odpowiedzią Overpass.

Wniosek: transport i dekoder mają dowód na rzeczywistych danych. Przed eksportem
do gameplayu trzeba ustalić zgodną kolejność, selekcję i środki geometrii;
przekazanie listy dostawcy bez normalizacji zmienia wynik limitu 60. Eksport
diagnostyczny nie zmienił adaptera produkcyjnego ani nie nadał zatwierdzenia.
Następny etap to testy regresji adaptera na zapisanych danych, bez ponownego
pobierania tej próbki. PASS PROVIDER i PASS LIVE SCANNER pozostają otwarte.

### Adapter kompatybilności offline

Dodano `poi_infrastructure/maplark_candidate.py`, bez podłączenia do runtime.
Wykorzystuje GeometrySnapshot ze sprintu 160: identyczne filtry, sortowanie
node/way po ID, sferyczny dystans do punktów/odcinków i bbox-center zaokrąglony
do 7 miejsc. Współrzędne wierzchołków nie są podszywane pod źródłowe OSM ID:
wewnętrzne odwołania są usuwane przed podglądem. Oryginalne tagi zostają.
Relacje, nietypowe ways, niekompletne odpowiedzi i niepewne geometrie odrzucają
cały podgląd, zamiast po cichu usuwać obiekty. Nie nadaje to coverage ani
uprawnienia `ProviderBatch.export_overpass`.

Testy porównują projekcję node/way sześciu niezależnych odpowiedzi Overpass
ze sprintu 160 oraz wynik rzeczywistego POIFetcher. Obejmują odwrócony porządek,
limit 60, oryginalne tagi, polygon otaczający skan (wnętrze nie oznacza bliskości
granicy), odrzucenie relacji i granic niepewnych. To nie test live MapLark.

Rzeczywista próbka nie przeszła rygorystycznego podglądu: cztery obiekty są
0,23–0,60 m od granicy promienia od wewnątrz. Istniejący margines 1 m zgłasza
`candidate_boundary_uncertain`. Szczegóły:
`doc/audits/sprint_161_maplark_candidate_20261023.json`. Wcześniejsze stwierdzenie
„brak obiektów poza 300 m” pozostaje prawdziwe, ale nie oznacza braku niepewności.
Nie zmniejszono marginesu i nie zmieniono konfiguracji produkcji.

Inspektor obsługuje `--preview LAT LON RADIUS`; używa wyłącznie zapisanych
plików. Dalsze otwarte zadania: zgodność selekcji dostawcy na granicy zapytania,
topologia relacji, integracja budżetu i dopiero później kontrolowany pilot gry.

Poniższe sekcje zachowują historyczny stan przygotowania przed tą próbą.

**W toku, offline. Brak PASS PROVIDER i PASS LIVE SCANNER.** Operator zlecił
implementację i potwierdził oba konta Free. Nie udostępnił kluczy i nie zatwierdził
jeszcze wykonania konkretnego pobrania. Kod oraz plany pozostają lokalne.

## Wynik i granice

- `world_contract.py`: wersje profilu, niemutowalne rekordy, źródłowe ID/tagi,
  oddzielne warstwy, geometria Point/LineString/Polygon/MultiPolygon, dowody
  coverage i daty ważności. Brak danych jest odróżniony od wyniku pustego.
- Shapely 2.1.2 sprawdza topologię płaską (m.in. otwory/samoprzecięcia).
  Antymeridian zachowuje geometrię jako structural_only; nie uzyskuje certyfikacji
  odczytu przestrzennego. Nie budujemy morza z otwartej linii brzegowej.
- `world_adapters.py`: plany i dekodery MapLark v3, Geoapify Places oraz eksport
  referencyjny Overpass. Zewnętrzni kandydaci nie eksportują do gameplayu,
  dopóki selekcja/porządek/tożsamość nie mają dowodu równoważności.
- `credit_budget.py`: atomowe rezerwacje w tej samej bazie POI, wiele okien
  budżetu, idempotencja, niepewne naliczenia, restart, blokada po naliczeniu
  ponad rezerwację. To wewnętrzny komponent, jeszcze nie podłączony do skanera
  ani panelu; nie odczytuje salda kont dostawców. Sam niczego nie migruje.
- Istniejący transport otrzymał osobną allowlistę GET i nagłówków auth dla
  dwóch API. Walidacja publicznych adresów, TLS, brak redirect/proxy oraz
  ograniczenie czasu/proces potomny pozostały wspólne. Klucz tylko z env,
  nigdy w querystring/raporcie. Obsługa Overpass pozostaje domyślna.
- Narzędzie inspekcji zapisanych odpowiedzi i jeden kontrolowany probe MapLark.
  Probe ma wspólny slot/circuit i 15-minutowy limit prób; nie używa registry
  do nadania scope i nie włącza gameplayu. Osobne potwierdzenie zmiennego kosztu
  jest wymagane: limit odpowiedzi nie stanowi gwarancji ceny u dostawcy.

## Kontrakt dotychczasowej gry

Zachowane bez edycji `run.py` i `poiFetchClass.py`: kolejność node/way/relation,
pierwsza kategoria, limit 60 i deduplikacja po współrzędnych. Zostają filtry
shop/amenity/office/healthcare/atm=yes/man_made=surveillance. `internet_access`
wpływa na ikony. `camera_marker` wykorzystuje osm_id/node_id oraz współrzędne;
nie można zastąpić ich zmyślonym ID lub innym centroidem bez zmiany skutków gry.
`infer_scan_location` w `ghostnetwork/llm/semantic_input.py` czyta addr:city,
city/is_in:city, odpowiedniki country/country_code i ISO3166-1:alpha2.
Adapter zachowuje otrzymane oryginalne tagi; nie ogranicza ich przed pełnym odbiorem.

Test referencyjnego eksportu przechodzi rzeczywistą fasadę POIFetcher na sześciu
zapisanych odpowiedziach Overpass ze sprintu 160. To nie dowodzi równoważności
innego dostawcy, odbioru pełnego run.py/GhostLab ani realnej dostępności API.

## Przejęcie 160

Schema i panel były wdrożone; operator potwierdził 70 testów na VPS. Późniejsze
diagnozy: [audyt regresji](sprint_157_160_scan_regression_audit.md),
[porównanie transportu](sprint_160_transport_comparison.md). HTTP 200 Python/VK
z poprawnymi 679 elementami przeplatało się z 504 curl; DE zgłaszał przeciążenie.
Ostatnia relacja operatora: pojedyncze skany działają, większość nadal nie.
Nie ma świeżego odczytu flag z VPS z 23.10.2026. Nie uznajemy wcześniejszych
wartości OFF za aktualnie sprawdzone. Nie aktywowano świata/wide/monitor ani wieku.
Otwarte storage/coverage/rollout 160 przejmują 162/163 zgodnie z ich planami.

## Walidacja lokalna

- `test_world*.py`: 29 testów PASS, 3,202 s (kontrakt, dekodery, budżet,
  transport, offline inspector i probe z atrapą transportu).
  Wspólny budżet sprawdzono na czterech procesach spawn, nie tylko wątkach.
- `test_poi*.py`: ponowienie po rozszerzeniu transportu: 87 PASS, 80,796 s.
- CLI probe bez --execute: plan, network_calls=0. CLI inspect: 3 syntetyczne
  obiekty, trzy profile, complete odpowiedzi i gameplay_approved=false.
- API danych MapLark/Geoapify/Overpass: 0 wywołań. Czytano tylko publiczne docs.
- UI nie zmieniono; nie wykonano odbioru przeglądarkowego ani produkcyjnego.

## Co nadal pozostało w 161

161.0/161.1: wykonany baseline i rdzeń kontraktu; finalny odbiór wszystkich
konsumentów/scen pozostaje otwarty. 161.2: [przegląd dostawców](sprint_161_provider_review.md),
brak realnej próbki. 161.3: dekodery i transport gotowe do diagnostyki, routing
gameplayu nadal niepodłączony. 161.4: lokalne testy komponentów PASS, nie pełne
C01–C09/G01–G04. 161.5–161.6: konfiguracja/pilot skanera dopiero po dowodach.

Przed dalszym podłączeniem źródła potrzebujemy kontrolowanej próbki MapLark
z nagłówkami, jej porównania z kontraktem oraz decyzji o kosztach. Nie wymyślamy
brakujących semantyk API ani nie upraszczamy gameplayu, żeby wymusić PASS.
Narzędzie i ograniczenia: [runbook](../runbooks/world_discovery_161.md).
