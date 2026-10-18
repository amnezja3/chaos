# CHAOS — POI Infrastructure v1
## Koncepcja niezawodnego skanowania świata OSM

**Status:** koncepcja do implementacji i przeglądu technicznego  
**Data:** 17.10.2026  
**Projekt:** CHAOS  
**Obszar:** mapa / skanowanie POI / integracja OpenStreetMap / GhostLab  
**Proponowany identyfikator:** `CHAOS.POI.INFRASTRUCTURE.V1`  
**Założenie nadrzędne:** naprawiamy dostęp do danych geograficznych, **nie przebudowujemy gameplayu**.

---

## 1. Streszczenie decyzji

CHAOS wykorzystuje publiczne serwery Overpass API do pobierania obiektów OpenStreetMap (POI) w pobliżu miejsca skanowania. Publiczny dostawca okresowo zwraca timeouty i HTTP 502 (`All query workers are busy and the request queue is full`). Skanowanie stanowi podstawową czynność w grze, więc jego niezawodność nie może zależeć wyłącznie od chwilowej dostępności jednego zewnętrznego API.

**Proponujemy wydzielić logiczną warstwę `CHAOS POI Service`** pomiędzy istniejącym skanerem a Overpass API. Pierwsza wersja ma zapewnić trwały i współdzielony cache *surowych wyników OSM*, koordynację zapytań pomiędzy procesami, rozsądne retry i circuit breaker, obsługę danych nieświeżych podczas awarii oraz pomiary jakości działania.

Nie instalujemy na tym etapie własnego Overpassa. Nie zmieniamy reguł wykrywania obiektów, zasięgu graczy, GhostLab, kamer, NPC, oznaczania celów ani tworzenia znaczników. Współdzielimy **dane wejściowe OSM**, a nie **stan lub rezultat gry**.

**Kolejność:** poprawność → trwałość/cache → współbieżność → odporność na awarie → dopiero potem optymalizacja sąsiednich obszarów.

---

## 2. Potwierdzony stan systemu (na podstawie kodu i logów z 17.10.2026)

| Element | Stan aktualny | Konsekwencja |
|---|---|---|
| `run.py:175–176` | `tag_filters = ["shop", "amenity", "office", "healthcare", "atm=yes", "man_made=surveillance"]`; globalny `fetcher = POIFetcher(...)` | Jedna instancja na proces aplikacji; nie na całą flotę workerów. |
| `run.py:24111–24126` | Wywołanie `fetcher.get_all(lat, lon, result_limit=60, scan_options=...)` | Dobre miejsce graniczne dla infrastruktury, bez ruszania rozgrywki. |
| `run.py:24127+` | Interpretacja lokalizacji, ikony i typy, filtrowanie oznaczonych celów, generowanie kamer i NPC | Musi pozostać per żądanie/per gracz. |
| `poiFetchClass.py:15–23` | Promień domyślny `300 m`; request timeout `8 s`; cache świeży `300 s`; stale `1800 s` | Konfiguracja bazowa istnieje. |
| `poiFetchClass.py:63–69` | Cache w słowniku obiektu; klucz zaokrągla `lat/lon` do 4 miejsc | Niewspółdzielony między procesami; klucz może utożsamiać różne środki skanu. |
| `poiFetchClass.py:26–30` | 4 adresy Overpass | Rotacja nie oznacza niezależności przeciążenia. |
| `poiFetchClass.py:70–123` | Base `endpoint_limit=2`; dodatki GhostLab do 3 prób; stałe `0,25 s` między próbami (o ile brak `Retry-After`) | Brak exponential backoff i zarządzania obciążeniem globalnym. |
| `poiFetchClass.py:47–52` | Zapytanie `nwr(around:300,lat,lon) ...; out center;`; `[timeout:15]` | Pobiera node/way/relation; limit 60 jest stosowany **po pobraniu**. |
| `poiFetchClass.py:125–128` | Stale cache po wyczerpaniu prób; wyjątkowe błędy np. `ValueError` mogą ominąć fallback | Długie oczekiwanie i niepełna odporność na błędy. |
| `ghostlab_scanner.py:48–49` | Ulepszenia wpływają na `extra_retries`, `extra_timeout`, `still_active` | Należy zachować kontrakt i możliwość anulowania skanu. |
| Overpass, 17.10.2026 | HTTP 502 z treścią „at capacity”, timeouty | Potwierdzona niedostępność upstream w badanym momencie; nie dowodzi, że każda porażka to wyłącznie wina dostawcy. |

**Uwaga dot. środowiska:** liczby procesów Gunicorn, częstotliwości skanowania, aktualnego QPS i rzeczywistego współdzielenia pamięci **nie zmierzono**. Nie traktować ich jako ustalonych faktów. Skalę poprawy ustalić na podstawie telemetryki.

---

## 3. Problem i wymagania

### 3.1. Obecny łańcuch

```text
Gracz → akcja SCAN → run.py → POIFetcher → publiczny Overpass
                                           ↳ timeout / 502 → próby → api_error
                               → wynik OSM → mechanika CHAOS → markery
```

### 3.2. Docelowy łańcuch

```text
                              ┌─────────────────────────────────────┐
Gracz → SCAN → run.py ───────→ │ CHAOS POI Service                    │
                              │ 1. sprawdź poprawny, świeży cache   │
                              │ 2. sprawdź trwające pobranie         │
                              │ 3. przejmij lease / limit ruchu      │
                              │ 4. odpytaj Overpass i zweryfikuj     │
                              │ 5. zapisz atomowo kompletne dane     │
                              │ 6. przy awarii użyj stale cache      │
                              └───────────────┬─────────────────────┘
                                              │
                                        surowe dane OSM
                                              │
                         prywatne przetwarzanie skanu w run.py
                      ┌────────────────────────────────────────┐
                      │ cele gracza, GhostLab, kamery, NPC,    │
                      │ ikony, losowość, markery, stan świata  │
                      └────────────────────────────────────────┘
```

### 3.3. Wymagania funkcjonalne

**F1 — pełny wynik OSM:** dla tej samej pozycji, promienia, filtrów i wersji zapytania nowy system zwraca semantycznie te same obiekty co aktualny Overpass (przy tym samym snapshotcie danych).

**F2 — brak przecieku stanu:** cache nie przechowuje `existing_targets`, wyników GhostLab, ikon i wygenerowanych NPC/kamer; każdy skan dostaje odrębne mutowalne obiekty Python.

**F3 — trwałość:** cache przetrwa restart procesu i jest współdzielony między workerami Gunicorn działającymi na tym samym hoście.

**F4 — deduplikacja:** identyczne zapytania przychodzące równocześnie nie skutkują równoległym odpytywaniem upstream.

**F5 — degradowanie kontrolowane:** timeout, 429, 502, 503, 504 lub błąd sieci nie uruchamiają lawiny retry; przy dostępnych **kompletnych** danych historycznych skan może zostać obsłużony.

**F6 — kompatybilność:** kontrakty metod, parametry `scan_options`, odpowiedzi `scan_outcome` i reguły rozgrywki pozostają zgodne.

**F7 — operacyjność:** operator potrafi stwierdzić z logów i metryk, czy odpowiedź pochodziła z `fresh`, `upstream`, `stale`, czy zakończyła się błędem.

### 3.4. Niefunkcjonalne

- Mały narzut CPU/RAM na istniejącym VPS, także przy obciążeniu Ollamą i pozostałymi modułami CHAOS.
- Żadnych długich transakcji blokujących bazę w trakcie żądania HTTP do Overpass.
- Twarde limity rozmiaru wyniku i miejsca na dysku, okresowe sprzątanie.
- Brak wrażliwych danych użytkownika w współdzielonym cache; tylko surowe dane OSM i metadane techniczne.
- Możliwość wyłączenia nowej warstwy flagą konfiguracji bez cofania pozostałych zmian.

---

## 4. Granica gameplay / infrastruktura — kontrakt nienaruszalny

**Wejście infrastruktury**: `lat`, `lon`, `radius`, `tag_filters`, `query_version`, opcje czasu/prób oraz `still_active`.

**Wyjście infrastruktury**: kompletny zestaw surowych elementów OSM w dotychczasowym formacie (`node`, `way`, `relation`, identyfikatory, tagi, współrzędne/center) albo jednoznaczny błąd. Informacja o źródle danych jest telemetrią, a nie elementem ekonomii gry.

**Zostaje poza warstwą POI:**

- sprawdzenie odległości gracza od punktu akcji i zasięgu skanera;
- walidacja uprawnień oraz tokenu GhostLab;
- indywidualne `marked_targets`, `discovered_cameras` i kontrola TTL zapisanych kamer;
- `infer_scan_location`, `assign_icon_and_type`;
- proceduralne generowanie kamer, osób i obiektów pomocniczych;
- reguły deduplikacji i globalny limit 60 elementów **po** kategoryzacji;
- wszystkie dalsze działania i nagrody w świecie CHAOS.

**Ważne:** obecna implementacja `get_all()` zwraca listę złożoną po kategoriach i deduplikuje wpisy na podstawie `(lat, lon)`. W v1 zachowujemy dokładnie to zachowanie, nawet jeśli później będzie warte osobnej korekty.

---

## 5. Model cache — v1 (konserwatywnie poprawny)

### 5.1. Dane cache'owane

Przechowujemy **surową, zwalidowaną odpowiedź JSON Overpass** lub równoważną bezstratną reprezentację wraz z metadanymi, a nie obiekty po przeróbkach z `run.py`.

- `elements[]`: obiekty node / way / relation, tagi, center, identyfikatory i typy;
- parametry zapytania i jego wersję;
- informację o czasie udanego pobrania;
- hash integralności / rozmiar odpowiedzi;
- identyfikator źródła na potrzeby diagnostyki.

Wynik musi przejść walidację schematu (`elements` jest listą itp.). Prawidłowy **pusty** wynik jest cache'owalny; błąd / częściowy JSON / HTML z kodem 502 **nie** jest cache'owalny.

### 5.2. Klucz cache

```text
sha256(
  canonical_json({
    "query_version": "poi-ql-v1",
    "latitude": <kanoniczny zapis pozycji żądania>,
    "longitude": <kanoniczny zapis pozycji żądania>,
    "radius_m": 300,
    "tags": ["shop", "amenity", "office", "healthcare",
             "atm=yes", "man_made=surveillance"],
    "response_format": "out-center-v1"
  })
)
```

**Nie używamy bez dowodu obecnego zaokrąglenia do 4 miejsc po przecinku** jako równoważności obszarów: dwa pobliskie środki skanu mogą mieć inne wyniki na granicy promienia. W v1 klucz musi jednoznacznie odzwierciedlać rzeczywiście wysłany środek i parametry zapytania; wspólne skanowanie z identycznych współrzędnych daje cache hit bez ryzyka zmiany geometrii.

Po zmianie semantyki zapytania zwiększamy `query_version`, aby nie mieszać niezgodnych wyników.

### 5.3. Okresy życia

Wstępnie zachowujemy obecne wartości, konfigurowalne:

- **fresh TTL: 300 s** — wynik używany od razu;
- **stale TTL: 1800 s** — kompletna starsza odpowiedź może być wykorzystana **wyłącznie** jako tryb awaryjny (zgodnie z przyjętą polityką);
- **retention / cleanup:** fizyczne usunięcie po okresie użytkowym ustalonym na podstawie zajętości; nie mieszać TTL z retencją.

Stale TTL liczony jest od ostatniego **udanego pobrania**, nie od momentu awaryjnego użycia. Nie przedłużamy jego ważności samymi odczytami. Jeśli brak kompletnego wpisu, zachowujemy obecny `scan_outcome = api_error` i tłumaczenie `map.result.upstream`.

### 5.4. Przechowywanie

**Rekomendacja na obecny pojedynczy VPS:** oddzielna baza SQLite z WAL (`poi_cache.sqlite3`) na lokalnym dysku, krótkimi transakcjami, `busy_timeout`, indeksami po kluczu i terminach ważności. Nie dokładać intensywnych zapisów do tabel profili graczy.

Struktura logiczna (orientacyjna, nie finalny DDL):

```text
poi_cache_entry
  key                  TEXT PRIMARY KEY
  query_version        TEXT
  request_params_json  TEXT
  response_json        BLOB/TEXT      -- opcjonalnie skompresowany
  response_sha256      TEXT
  response_bytes       INTEGER
  provider             TEXT
  fetched_at_utc       TEXT
  fresh_until_utc      TEXT
  stale_until_utc      TEXT

poi_inflight
  key                  TEXT PRIMARY KEY
  lease_owner          TEXT
  lease_until_utc      TEXT
  started_at_utc       TEXT

poi_provider_state
  provider_id          TEXT PRIMARY KEY
  open_until_utc       TEXT
  failure_streak       INTEGER
  next_allowed_at_utc  TEXT
  last_error_class     TEXT

poi_global_budget
  budget_name          TEXT PRIMARY KEY
  ...                  ...           -- token/lease/budget model
```

Nie traktować zapisów do SQLite jako mutexa sieciowego na czas całej operacji: atomowe **zdobycie/odnowienie/zwolnienie lease'a** w krótkich transakcjach. Sprawdzić semantykę lease'ów po awarii workera, restartach, wygaśnięciu i równoczesnym przejęciu przez drugi proces. Zapis wyniku akceptować wyłącznie od aktualnego właściciela (fencing token / generacja lease'a).

Jeśli docelowo pojawi się więcej hostów aplikacji, storage i koordynator trzeba wymienić na współdzielone rozwiązanie (np. Redis + baza); lokalny SQLite na jednym VPS nie rozwiązuje wielohostowej synchronizacji.

---

## 6. Obsługa skanu — docelowy przebieg

```text
1. Walidacja i autoryzacja skanu (obecny run.py).
2. Wylicz klucz dokładnego zapytania OSM.
3. Jeżeli `still_active() == false` → anuluj zgodnie z kontraktem.
4. Fresh hit → odczytaj, zweryfikuj, utwórz prywatne obiekty → gameplay.
5. Cache miss → sprawdź trwające pobranie pod tym samym kluczem.
6. Jeżeli pobranie trwa → czekaj z limitem czasu i możliwością anulowania,
   następnie ponów odczyt cache; nie wykonuj duplikatu zapytania.
7. Jeśli brak pobrania → atomowo zdobądź lease.
8. Jeżeli circuit breaker / budżet nie pozwala → odczytaj kompletne stale
   albo zwróć kontrolowany błąd (bez ślepego odpytywania API).
9. Jeśli dozwolone → wyślij ograniczoną liczbę prób do aktywnego endpointu;
   sprawdzaj Retry-After, backoff, deadline i status skanera.
10. Po HTTP 200 zweryfikuj JSON i wynik; zapisz atomowo w trwałym cache.
11. Wydaj prywatną kopię danych; zwolnij lease.
12. Po błędzie lub timeout → jeżeli istnieje kompletne stale, użyj je;
    w przeciwnym razie `api_error` z czytelną telemetrią.
```

**Uwaga:** `still_active` jest związane z daną sesją/skanerem — anulowanie jednego oczekującego gracza nie może automatycznie kasować wspólnego pobierania, jeśli inni na nie czekają. Jednocześnie właściciel requestu musi mieć bezpieczną politykę kończenia pracy (deadline / limit upstream), także gdy jego klient zniknie.

---

## 7. Single-flight i limit równoległości

**Single-flight v1:** identyczny klucz → jedna operacja HTTP niezależnie od liczby równoległych żądań w różnych workerach na tym samym VPS.

**Globalna kontrola:** wprowadzamy centralny budżet liczby równoległych zapytań upstream i ewentualnie niewielki token bucket. Wartości początkowe do strojenia (np. konserwatywnie 1 aktywne żądanie Overpass na cały VPS), nie jako niezmienne limity kontraktu.

W oczekiwaniu na wolny slot stosujemy limit czasu i anulowanie. Bez nieograniczonej kolejki, która blokuje workery Gunicorna. Jeżeli aktualna synchroniczna architektura nie toleruje długiego czekania, należy przewidzieć krótkie okno oczekiwania i bezpieczne zakończenie `api_error`; nie wprowadzać asynchronicznego API endpointu bez osobnej decyzji.

**Brak cache stampede:** brak wpisu lub jego wygaśnięcie nie powoduje wielu równoległych żądań do tego samego źródła. Po zakończonym pobraniu pozostałe żądania odczytują gotowy wynik.

---

## 8. Polityka dostawców, retry i circuit breaker

### 8.1. Statusy i reakcje

| Stan | Reakcja |
|---|---|
| `200` + poprawny JSON | Zapisz i zwróć. |
| `200` + niepoprawny/niepełny JSON | Nie zapisuj; oznacz błąd odpowiedzi. |
| Timeout, DNS/network error | Ograniczony retry/backoff lub stale fallback. |
| `429`, `502`, `503`, `504` | Honoryzuj `Retry-After`; aktualizuj stan dostawcy; ogranicz próby. |
| `400`, `401`, `403`, `406` | Rozróżnij błąd requestu/identyfikacji/polityki; nie ponawiaj w pętli; zezwól na stale fallback. |
| Brak fresh i stale | Zachowaj kontrolowany `api_error`, a nie pustą listę udającą udany skan. |

### 8.2. Zasada retry

- **Exponential backoff z jitterem** zamiast stałych `250 ms`.
- Uznawaj `Retry-After` (sekundy lub data HTTP); nie próbuj wcześniej, niż sugeruje dostawca.
- Trzymaj się wspólnego budżetu czasu i limitu prób; nie pozwalaj pojedynczemu skanowi zablokować zasobów na nieprzewidywalnie długo.
- Po seriach 429/502/503 otwieraj circuit breaker dla odpowiedniego endpointu (lub grupy faktycznie współdzielącej infrastrukturę); po cooldownie sprawdzaj ostrożnie `half-open`.
- Nie zakładaj, że `overpass-api.de` i `lz4.overpass-api.de` to niezależne pule mocy obliczeniowej.
- Nie próbuj obchodzić jawnych limitów dostawcy rotacją adresów; respektuj zasady publicznych endpointów.
- Popraw nagłówek `User-Agent`: obecnie `haos-game-dev/0.1` (prawdopodobnie literówka). Stosuj jednoznaczną identyfikację aplikacji i **rzeczywisty** kontakt/operatora, jeśli go dodajemy.

### 8.3. Timeouty

Aktualnie klient domyślnie czeka **8 s**, a Overpass QL deklaruje `[timeout:15]`. W v1 trzeba rozdzielić `connect_timeout` i `read_timeout` i dobrać je do rzeczywistego SLA skanowania, limitu Gunicorna oraz zachowania publicznego API. Wyższy timeout nie jest samodzielnym rozwiązaniem przeciążenia.

### 8.4. GhostLab

`extra_retries` (0–3) i `extra_timeout` (0–10 s) pozostają aktywnym kontraktem gry. Dodatkowe możliwości skanera mogą wpływać na **maksymalny czas / liczbę dozwolonych prób**, ale **nie omijają** globalnego circuit breakera, `Retry-After` ani budżetu ochronnego upstream. Obowiązkowy test dowodzący, że ulepszony skaner nadal zapewnia obiecaną mechaniką korzyść w scenariuszach, w których wykonanie dodatkowej próby jest możliwe. W sytuacji całkowitej blokady upstream nie gwarantujemy sukcesu żadnemu skanerowi.

---

## 9. Geograficzny cache — etap drugi, osobny od v1

**Cel:** kilku graczy skanuje sąsiednie, nakładające się okręgi, a CHAOS potrafi skorzystać ze wspólnych danych bez każdorazowego pobierania.

**Zastrzeżenie krytyczne:** `nwr(around:R,lat,lon)` bierze pod uwagę **geometrię obiektu**. Wynik `out center` daje środek bounding box obiektu, **nie gwarantuje**, że punkt środka jest w promieniu skanu lub nawet wewnątrz obiektu. Dlatego:

- nie wolno zwracać „POI w promieniu” wyłącznie przez filtr odległości do `center`;
- nie wolno używać prostego zaokrąglenia środka skanu ani siatki geohash jako dowodu identyczności odpowiedzi;
- nie wolno dzielić większego obszaru na komórki bez udokumentowanej gwarancji pełnego pokrycia zapytania;
- nie wolno usuwać ways/relations tylko dlatego, że ich `center` jest daleko.

**Warunek wejścia do etapu II:** przygotować i przetestować dokładny algorytm superset + lokalna filtracja uwzględniający nodes, odcinki ways, geometrię relations i semantykę Overpass `around`; zapewnić brak brakujących obiektów oraz zachowanie istotnej kolejności i limitów wyników. Ponieważ `out geom` znacząco zwiększa ciężar odpowiedzi, osobno zmierzyć koszt w ruchu publicznym. Dopuszczalną alternatywą dla dużej skali jest lokalny import danych OSM do bazy przestrzennej.

**Decyzja dla pierwszej implementacji:** v1 realizuje bezpieczny cache **dokładnych zapytań**. Współdzielenie cache pomiędzy różnymi, sąsiadującymi współrzędnymi **nie jest jeszcze obiecanym efektem**. To chroni mechanikę gry przed subtelnym błędem geometrii.

---

## 10. Proponowany podział na moduły

```text
run.py                       # niezmieniony handler/gameplay; punkt integracji
poiFetchClass.py             # kompatybilny publiczny interfejs POIFetcher
poi_infrastructure/
  service.py                 # główna orkiestracja: cache / single-flight / provider
  query.py                   # kanoniczne zapytanie Overpass i query_version
  repository.py              # trwałe wpisy cache, lease'y i status dostawców
  overpass_client.py         # HTTP, timeout, retry, User-Agent, statusy
  provider_policy.py         # limity, circuit breaker, backoff
  telemetry.py               # liczniki, czasy, strukturalne logi
  errors.py                  # klasy błędów zewnętrznych
migrations/                  # jeśli projekt tak zarządza zmianami bazy
 tests/
  test_poi_infrastructure_*.py
```

To **propozycja organizacji**, nie wymóg tworzenia dokładnie tych nazw; przed refaktorem Codex powinien dopasować moduły do istniejących konwencji projektu. Dla minimalizacji ryzyka `POIFetcher.get_all(...)` może pozostać facade delegującym do serwisu. `run.py` nie powinien znać SQLite, endpointów Overpass ani systemu lease'ów.

---

## 11. Telemetria i kryteria jakości

**Metryki podstawowe:**

- `poi_scan_total{result=success|api_error|denied}`;
- `poi_fetch_source_total{source=fresh|upstream|stale}`;
- `poi_overpass_http_total{endpoint,status_class}`;
- `poi_overpass_timeout_total{endpoint}`;
- `poi_fetch_duration_seconds` (p50/p95/p99);
- `poi_upstream_attempts_per_scan`;
- `poi_singleflight_join_total`;
- `poi_inflight_active`, `poi_queue_wait_seconds`;
- `poi_circuit_state{endpoint}`;
- `poi_cache_entries`, `poi_cache_bytes`, `poi_cache_evictions_total`.

Log per scan powinien mieć losowy `scan_request_id`, skrót `query_key`, klasę błędu, czas i źródło odpowiedzi — **bez** identyfikatorów gracza ani prywatnych zasobów w globalnym cache. W logach operacyjnych nie trzeba wypisywać dokładnych współrzędnych każdego skanu, jeżeli nie są niezbędne do diagnostyki.

**Cel pomiarowy (nie obietnica):** zmniejszyć udział odpowiedzi `api_error` i liczbę żądań upstream na udany skan. Po 24–72 h zebrać baseline i realne wyniki, by określić, czy dalszą korzyść da geograficzny cache albo własne źródło danych OSM. Nie zakładać bez pomiarów „80–90% redukcji”.

---

## 12. Testy i bramki akceptacji

| ID | Test / warunek | Kryterium akceptacji |
|---|---|---|
| A01 | Identyczny środek, parametry i poprawny cached JSON | Cache hit; **0** dodatkowych żądań HTTP. |
| A02 | Dwa różne środki, które po zaokrągleniu do 4 miejsc byłyby równe | **Nie** używamy jednego wpisu bez dowodu ekwiwalencji. |
| A03 | Równoczesny identyczny skan z 2+ workerów | Jedno żądanie upstream; pozostali konsumują jego kompletny wynik. |
| A04 | Awaria workera/wygaśnięcie lease'a | Drugi worker bezpiecznie przejmuje pracę; spóźniony zapis nie nadpisuje nowszego wpisu. |
| A05 | Restart PM2/Gunicorn | Wpis fresh/stale pozostaje dostępny. |
| A06 | Overpass 502 / timeout, istnieje kompletne stale | Skan działa z fallbackiem w określonym budżecie czasu. |
| A07 | 406 / niepoprawny JSON / wyjątek parsera | Brak niekontrolowanej pętli retry; stale fallback nadal działa. |
| A08 | Brak jakiegokolwiek cache i API padło | `scan_outcome=api_error`; bez „udawanego” pustego sukcesu. |
| A09 | `Retry-After`, 429 i seria 502 | Szanowanie terminów, backoff, circuit breaker i limitów. |
| A10 | Zwykły skaner / ulepszony GhostLab | Zgodność wejścia/wyjścia, limitów i zachowania `still_active`. |
| A11 | Równocześni gracze — ten sam POI | Brak wzajemnego ujawniania oznaczonych celów, kamer czy NPC. |
| A12 | Wyniki node/way/relation na granicy promienia | Dokładny odpowiednik dotychczasowego wyniku `around`, bez filtracji po samym center. |
| A13 | Mutacja obiektu w `run.py` | Nie modyfikuje zapisanych danych OSM ani wyniku innego skanu. |
| A14 | Prawidłowa pusta lista `elements` | Cache'owana jako udany wynik; nie mylona z błędem sieciowym. |
| A15 | Ograniczenie rozmiaru bazy / sprzątanie | Bez utraty wpisów używanych przez aktywne lease'y; bez blokowania gry. |
| A16 | Dotychczasowe testy `test_ghostlab_scanner.py`, `test_poi_fetcher_geometry.py`, `test_poi_fetcher_latency_contract.py` | Wszystkie przechodzą, z aktualizacją tylko tych asercji, których kontrakt świadomie zmieniono. |

**Testy integracyjne** powinny wykorzystywać deterministyczne fixtures JSON Overpass (w tym wielkie ways i relations). Nie uzależniać CI od stanu publicznego API.

---

## 13. Plan wdrożenia, bez jednorazowej wielkiej migracji

### Etap 0 — Baseline i audyt

- Ustalić liczbę workerów, faktyczną konfigurację PM2/Gunicorn i timeouty.
- Policzyć QPS skanera, rozkład pozycji, liczbę 502/429/406/timeoutów, średni i p95 czas skanu.
- Sprawdzić bieżące testy i ograniczenia synchronicznego request handlera.
- Przygotować fixtures i test regresyjny obecnego outputu.

**Bramka:** znamy obecny czas skanu, częstość awarii i koszt upstream.

### Etap 1 — Trwały cache dokładnych zapytań

- Bezstratne dane OSM + poprawny klucz + TTL/stale + SQLite WAL.
- Bezpieczne kopie per skan; typy błędów; fallback także po błędach parsera i nietypowych HTTP.
- Integracja pod zachowanym `POIFetcher.get_all()`.

**Bramka:** A01, A02, A05, A06–A08, A11, A13, A14, A16.

### Etap 2 — Wspólna współbieżność i ochrona dostawcy

- Lease/single-flight, globalny budżet, retry/backoff, circuit breaker, `Retry-After`.
- Pomiar obciążenia API i latencji; właściwe wygaśnięcie oraz przejęcie lease'a.
- Spójny timeout i anulowanie `still_active`.

**Bramka:** A03, A04, A09, A10, A15 + testy obciążenia.

### Etap 3 — Wdrożenie kontrolowane

- Feature flag, ewentualny shadow mode porównujący wyniki (bez podwajania ruchu publicznego), canary na małej części skanów.
- Przegląd telemetrii, poziomu błędów i wpływu na CPU, RAM oraz I/O.
- Rollback do starej ścieżki po wyłączeniu flagi.

**Bramka:** mierzalna poprawa stabilności i brak regresji gameplayu.

### Etap 4 — Geograficzne współdzielenie danych (opcjonalnie)

- Osobny projekt i proof-of-correctness geometrii.
- Porównania wyników na miejskich i wiejskich obszarach, na granicach promienia, dla ways/relations.
- Pomiar narzutu `out geom` i obciążenia lokalnego.

**Bramka:** A12, testy zgodności na dużym korpusie, pozytywny bilans kosztu/korzyści.

---

## 14. Ryzyka i decyzje pozostające do potwierdzenia

1. **Globalny VPS vs wiele hostów:** zakładamy jeden host i lokalną bazę; trzeba to zweryfikować.
2. **Single-flight i sync Gunicorn:** długie oczekiwanie może blokować workery HTTP; wymagany realistyczny timeout i test obciążenia.
3. **Ważność danych mapowych:** stale ma ratować gameplay, ale nie może być bezterminowe. Użytkownik może zobaczyć POI usunięte z OSM; świadoma polityka produktu.
4. **Obiekt `Result` i mutowalność:** w pamięci między requestami nie przechowywać tych samych mutowalnych słowników wynikowych.
5. **Koszt przestrzenny:** trwała baza wymaga polityki rozmiaru/cleanup/backup (bez konieczności trzymania cache w pełnych backupach świata gry).
6. **Ograniczenia licencji OSM:** zachować odpowiednią atrybucję i zweryfikować obowiązki przy długoterminowym kopiowaniu/przetwarzaniu danych.
7. **Wartość GhostLab:** globalna ochrona upstream ma pierwszeństwo przed retry; użytkowa obietnica ulepszenia wymaga testów i ewentualnego doprecyzowania w UI.
8. **Caching sąsiednich obszarów:** bez geometrii nie wdrażać przybliżonej filtracji opartej na `center`.
9. **Endpointy Overpass:** utrzymywać listę tylko faktycznie działających, dozwolonych dostawców; polityka ich obciążania może się zmieniać.
10. **Przyczyny pozostałych błędów:** 502 w logu potwierdza problem dostawcy w tamtej chwili, ale potrzebujemy danych, żeby wykluczyć błędy lokalnej konfiguracji i szczyty ruchu CHAOS.

---

## 15. Instrukcja startowa dla Codexa

> **Zadanie: przygotuj implementację `CHAOS.POI.INFRASTRUCTURE.V1` zgodnie z niniejszą koncepcją.**
>
> Najpierw przeanalizuj aktualne `poiFetchClass.py`, wywołania w `run.py`, integrację `ghostlab_scanner.py`, testy skanera i konfigurację serwera. Zapisz krótką diagnozę oraz plan zmian. Nie ruszaj mechaniki skanowania, uprawnień, generowania NPC, kamer ani stanu gracza. W pierwszej kolejności wykonaj bezpieczny trwały cache **dokładnych zapytań** i regresję wyników OSM; potem wdrożenie lease/single-flight i polityki limitowania Overpass; dopiero na końcu opcjonalną optymalizację geograficzną. Wszystkie zmiany zabezpiecz testami i flagą rollbacku. Nie zakładaj, że `out center` pozwala bezpiecznie filtrować ways/relations po odległości. Przed wdrożeniem produkcyjnym przedstaw diff, wyniki testów, plan migracji i rollback.

---

## 16. Definicja sukcesu

Projekt jest gotowy, gdy:

- ponowne identyczne skany obsługiwane są z trwałego cache;
- równoczesne identyczne skany nie bombardują Overpass;
- chwilowe 502/timeouty częściej kończą się skutecznym skanowaniem dzięki kompletnym danym stale;
- pojedynczy skan nie generuje niekontrolowanej serii prób;
- GhostLab i per-graczowe wyniki pozostają odizolowane;
- zachowana jest semantyka `nwr(around)` i wyniki node/way/relation;
- po restarcie serwera / workerów wpisy cache nie giną;
- można wskazać z metryk, jak bardzo zmniejszyła się zależność CHAOS od publicznego Overpass.

**Decyzja:** realizować etapowo. Najpierw solidna infrastruktura i brak regresji rozgrywki, potem ewentualnie geograficzna optymalizacja i/lub własne źródło danych OSM.

---

## Źródła techniczne i materiały wejściowe

**Materiały projektu:** `poiFetchClass.py` (wydruk 1–238), `run.py` (fragment 150–190, 24050–24185), wyniki `grep` dla `POIFetcher`, GhostLab oraz logi HTTP 502 / timeout z 17.10.2026.

**Dokumentacja Overpass / OpenStreetMap:**

- Overpass QL — `around`, `nwr`, `out`, `center`: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
- Overpass API — data formats i rozróżnienie `center` vs `geom`: https://dev.overpass-api.de/overpass-doc/en/targets/formats.html
- Overpass API — geometryczne działanie `around`: https://dev.overpass-api.de/overpass-doc/en/full_data/polygon.html

*Dokument koncepcyjny, nie opis wdrożonego stanu produkcyjnego. Parametry i nazwy nowych modułów są propozycją do walidacji w repozytorium.*
