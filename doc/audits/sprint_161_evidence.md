# Sprint 161 — stan realizacji 23.10.2026

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
