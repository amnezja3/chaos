# Sprint 160.0 — kontrakt i początek realizacji

2026-10-18. Stan: prace lokalne, bez wdrożenia i bez ruchu do Overpass. Baseline istniejącego zestawu `test_poi*.py`: 34 testy PASS (26,734 s). Po pierwszym rozszerzeniu: 45 testów PASS (43,831 s); dodatkowo endpoint admina PASS i rozszerzony rejestr/probe 5 testów PASS. Nie są to dowody kompletnej realizacji sprintu.

## Potwierdzony kontrakt

`run.py` tworzy `POIFetcher` z filtrami shop/amenity/office/healthcare/atm=yes/man_made=surveillance. Promień domyślny 300 m. `/map-action` wywołuje `get_all(..., result_limit=60)` po autoryzacji i kontroli zasięgu. GhostLab przekazuje dodatkowe próby/czas oraz `still_active`, nie zmienia w tym adapterze promienia. Kategoryzacja i deduplikacja współrzędnych pozostają w istniejącej fasadzie. Dane źródłowe nie mogą przechowywać ikon, tokenów ani indywidualnych odkryć.

SQLite 158 ma osobną tabelę `providers` dla circuit breakerów. Nowy rejestr używa `poi_provider_config`; nie zmienia znaczenia istniejącej tabeli. Stan konfiguracji i techniki, warunki i scope pozostają oddzielne.

## Decyzja storage

Pierwszy magazyn jest w tym samym `poi_cache.sqlite3` co lease 158. To zmiana względem propozycji osobnego pliku w planie: kontrola właściciela, zapis niezmiennego snapshotu i jego membership mają jedną transakcję. Pozwala uniknąć luki fencing pomiędzy plikami. Nie zwiększono globalnego limitu głównego pliku infrastruktury; shadow przy braku miejsca nie niszczy poprawnej odpowiedzi skanu. Pomiar WAL/locków przy większym zasobie i docelowy budżet nadal wymagają odbioru.

Pierwszy format to `exact-center-v1`: pełny payload, hash, czas, źródło i wszystkie elementy w kolejności. Nie wpisuje nic do `world_coverage`; nie deklaruje kompletnego pokrycia komórki. Nowszy snapshot nie zmienia treści wcześniejszego. Odczyt zwraca niezależne obiekty. Fresh/usable na tym etapie zachowują TTL przekazane przez 158; dłuższa polityka world nie została samodzielnie ustanowiona.

## Bramka geometrii

Dokumentacja [Overpass — Polygon and Around](https://dev.overpass-api.de/overpass-doc/en/full_data/polygon.html) opisuje wybór obiektów względem odległości, a nie tylko środka prezentowanego markera. Dotychczasowy `out center` nie wystarcza do certyfikowania innego punktu skanu.

Przygotowano sztuczny zbiór `tests/fixtures/poi/geometry_source.osm` oraz `tools/poi_geometry_reference.py`: importer i rzeczywisty silnik Overpass na osobnej bazie, sześć dokładnych zapytań, zapis odpowiedzi i hashy wejścia/binarek. Skrypt nie wykonuje pobrań ani nie uruchamia serwera HTTP. Wymaga istniejących `update_database` i `osm3s_query`; nie był jeszcze wykonany na takim silniku.

Lokalnie nie znaleziono Dockera ani `osm3s_query`; `wsl --list --quiet` potwierdza brak zainstalowanego WSL. Poproszono operatora o izolowane środowisko Linux na VPS lub alternatywę. Do czasu niezależnego parity nie uruchamiamy lokalnego selektora sąsiednich punktów ani wide fetch. To otwarta bramka 160.2, nie PASS oparty na własnych oczekiwaniach testowych.

## Zakres wykonany i następny

- Magazyn exact, hash/limity/fencing, niezależne wyniki, odtwarzanie SQLite: 7 testów PASS.
- Registry, jawne decyzje, scope, rewizje, ponowna weryfikacja po zmianie URL, bez domyślnego seedowania zatwierdzeń.
- HTTPS z przypięciem połączenia do sprawdzonych publicznych adresów DNS; brak proxy środowiskowego i redirect; zachowana kontrola TLS/SNI. Testy jednostkowe odrzucają prywatne IPv4/IPv6, metadata i URL z poświadczeniami. Pełny test transportu TLS/rebinding wymaga dalszych dowodów.
- Admin GET/POST z istniejącą rolą admina i CSRF; panel PL/EN, komunikaty przy akcjach. Playwright 1440/390 × PL/EN: zapis kandydata, odrzucenie aktywacji bez zgody, odświeżanie bez nowych obserwacji transportu; brak pageerror i overflow. Odpowiedzi 400 celowo testowanych odmów są oczekiwanymi wpisami konsoli.
- Izolowany probe korzysta z globalnego slotu, limitu 15 min i deadline 8 s; niepoprawny JSON nie daje healthy. Monitoring automatyczny, agregaty, audyt widoczny w panelu, pełna propagacja wieloprocesowa i rollback konfiguracji nadal wymagają domknięcia.
- Nowe flagi mają domyślnie OFF. Nie wykonano push, wdrożenia, zmiany PM2, zatwierdzenia providera ani migracji produkcyjnej bazy.

Aktualizacja testów: rejestr/probe 6 PASS, w tym wyłączenie dostawcy widoczne w czterech już działających procesach. Secure transport 4 PASS: jedno rozwiązanie DNS, połączenie przypięte do sprawdzonego IP, TLS z oryginalnym hostname, odrzucenie mieszanego publicznego/prywatnego DNS, brak podążania za redirect. To izolowane testy transportu, nie pomiar publicznych usług. Ponowiony Playwright po poprawieniu HTML pattern i fixture obsługującego równoległe assety: 4 kombinacje PASS; jedyny oczekiwany błąd konsoli to HTTP 400 przy celowej próbie aktywacji bez zgody. Przeglądarkę i fixture zamknięto.
