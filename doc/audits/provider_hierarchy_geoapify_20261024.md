# 161–163: hierarchia, Geoapify, admin — 24.10.2026

Zakres polecenia: wspólny wybór źródeł, dokończenie przygotowania Geoapify,
sterowanie kolejnością w adminie; praca lokalna do próby wymagającej operatora VPS.

## Wykonane

- Routing dla warstwy/trybu, najwyżej trzy źródła, wersjonowanie, historia,
  przywracanie poprzedniej kolejności bez cofania zgód dostawców. Capability
  oddzielona od technicznej dostępności i prawa użycia.
- Rzeczywista ścieżka skanera za `CHAOS_POI_ROUTING_ENABLED=0`: cache wszystkich
  źródeł → zgodny świat → sieć w kolejności → dopuszczone stale. MapLark zachowuje
  obecne klucze/cache i ograniczenia pilota. Nowa ścieżka Overpass ma cache
  zależny od źródła i revision, bez niecertyfikowanego regionalnego odczytu.
- Jeden deadline skanu, pojedyncza próba na źródło, dotychczasowy slot HTTP,
  circuit breaker, budżet MapLark i sprawdzenie konfiguracji przed publikacją.
  Brak niejawnego powrotu do statycznych endpointów. Log i admin pokazują
  źródło wyniku oraz pominięcia/błędy bez danych lokalizacji graczy.
- Background routing jest sprawdzany przez producenta/wykonawcę, jeśli nowa
  flaga jest aktywna. Nie dodano daemona ani automatycznego enqueue.
- Geoapify Places: stały endpoint, POST z x-api-key, normalizacja bez tworzenia
  sztucznych OSM ID/tagów, limitowana paginacja 1–3 stron, jeden deadline 35 s,
  dedup, wykrycie powtarzającej się strony i limit 15 min między próbami.
  Rezerwacje po 5 kredytów/stronę w istniejącej księdze; brak dowodu ceny
  pozostaje uncertain. Nie przypisano Geoapify pełności skanu lub geografii.
- Narzędzia CLI: plan bez sieci; przygotowanie wyłączonego kandydata/budżetu;
  kontrolowany probe; osobna migracja routing z dry-run na kopii i backupem.
- Admin PL/EN: warstwa, tryb, trzy pozycje, przyczyny pominięcia, osobne
  budżety dostawców, historia i restore, komunikaty przy formularzu.
  Probe feature APIs jest oznaczony jako osobne narzędzie z budżetem.

## Dowody lokalne

- Pełny `test_world*.py`: **174 PASS, 67.249 s** (przed dwoma dodatkowymi
  scenariuszami cache/stale w routerze). Izolowane SQLite, mockowany HTTP.
- Pełny `test_poi*.py`: **91 PASS, 67.691 s**.
- Końcowy `test_world_routing.py`, w tym dodatkowe scenariusze cache/stale:
  **11 PASS, 9.154 s**.
- Test migracji: dry-run nie tworzy tabel w oryginale, backup zachowuje księgę,
  apply nie zmienia jej zużycia, istniejący backup nie jest nadpisywany.
- Plan CLI Geoapify: network_calls=0, max_network_calls=1, reservation=5,
  deadline=35, bez utworzenia bazy i odczytu klucza.
- Playwright MCP, rzeczywiste lokalne endpointy i izolowana sesja admina:
  PL desktop i mobile 390×844 oraz EN mobile; zapis Geoapify/MapLark/Overpass,
  widoczna blokada pełnego profilu Geoapify, restore do MapLark, odrzucenie
  duplikatów, osobna konfiguracja roads/background z komunikatem braku zgody.
  Brak poziomego overflow; zrzut mobilny obejrzany. Zwykłe akcje: 0 błędów
  i ostrzeżeń konsoli, 0 zewnętrznych zasobów w Resource Timing.
- Dodatkowo EN desktop: brak overflow. Celowo błędny CSRF wysłany przez XHR
  dał 403; konflikt revision dał 409 i komunikat przy formularzu. Te dwie
  celowo wywołane odpowiedzi pojawiły się jako błędy HTTP w konsoli, bez
  nieobsłużonego błędu JS. Sesje Playwright i serwery fixture zamknięte.
- Pierwszy test CSRF bez nagłówków otrzymał 200, ponieważ klient fixture
  automatycznie dodaje poprawny token. Test poprawiono na jawny błędny token.
  Analogicznie przeglądarkowy wrapper fetch nadpisuje token poprawnym; test
  XHR potwierdził rzeczywiste odrzucenie przez serwer. Nie zmieniano ochrony CSRF.

## Granica odbioru

### Wynik operatora i przygotowanie porównania

Operator potwierdził po poprawce: captured_not_approved, 1 wywołanie,
1 obiekt z OSM ID, jedna krótka strona, koszt niezgłoszony (rezerwacja 5),
gameplay/world_ingest false. Tag keys zawierały tourism/building, ale nie
shop/amenity/office/healthcare/atm/man_made. To nie wystarcza do ustalenia
przyczyny ani pełności. Raport nie zawierał parametrów query; historyczne
680 MapLark nie stanowi jeszcze kontrolowanego porównania.

Sprawdzono https://apidocs.geoapify.com/docs/places/ — POST z kategoriami,
circle lon/lat/radius i nagłówkiem x-api-key odpowiada opisanemu kontraktowi.
Nie potwierdzono hipotezy błędnego łączenia kategorii; nie zmieniano transportu
na podstawie przypuszczenia. Dodano jawne profile diagnostyczne commercial
i catering oraz parametry query i agregaty typów geometrii/tagów. Następna
próba: wyłącznie commercial, 300 m, 52.2319/21.0067, jedna strona. Te same
limity i księga; nic nie aktywuje źródła w grze.

Testy diagnostyki: 7 PASS, 2.540 s. Brak wywołań API podczas implementacji.
Pozostaje test VPS; nie deklarujemy zakończenia certyfikacji Geoapify.

### Korekta po pierwszej próbie VPS

Operator otrzymał `geoapify_osm_identity_unverified`. Ta ścieżka oznacza HTTP
200 przed normalizacją, ale surowej odpowiedzi nie zachowano, więc dokładny
odrzucony rekord pozostaje nieznany. Adapter nie obsługiwał udokumentowanych
skrótów `n/w/r` w `datasource.raw.osm_type`; dodano ścisłe mapowanie do
`node/way/relation`. Nie poluzowano walidacji identyfikatorów ani dopuszczenia
Geoapify do gameplay. Źródło formatu:
https://apidocs.geoapify.com/how-to/place-discovery/place-details-by-id-or-coordinates

Testy po poprawce: kontrakt 18 PASS (0.939 s), pozyskiwanie Geoapify 5 PASS
(2.813 s), z fixture używającym `n`. Brak nowych wywołań sieciowych.
Wcześniejsza próba VPS zachowuje rezerwację nieznanego kosztu; nie resetujemy
księgi ani 15-minutowego limitu. Potrzebny ponowny kontrolowany odbiór na VPS.

Brak wywołań API danych MapLark/Geoapify/Overpass w tej pracy. Odczytano
publiczną [oficjalną dokumentację Geoapify Places](https://apidocs.geoapify.com/docs/places/).
Nie ma jeszcze realnej próbki Geoapify ani dowodu zgodności wszystkich
kategorii CHAOS, więc źródło jest pomijane z `geoapify_contract_unverified`.
Integracja pozyskiwania jest gotowa do diagnostyki, nie do zastąpienia skanera.
Koniec paginacji nie jest potwierdzeniem pełności świata.

W obu ecosystemach routing OFF. Ingest/read, polityka wieku, aktywne budżety
MapLark i konfiguracja produkcyjna bez zmian. Pozostaje kontrolowana próba
Geoapify oraz odbiór routera na VPS przed ON; nie zamykamy całych 161–163.
Instrukcja: [runbook](../runbooks/provider_hierarchy_geoapify_161_163.md).
