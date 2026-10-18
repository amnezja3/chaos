# CHAOS — Sprint 160
## POI World Repository + Overpass Provider Control

**Identyfikator:** `160.poi.world.repository`  
**Status:** SPECYFIKACJA / do audytu i realizacji przez Codex  
**Data:** 18.10.2026  
**Aktualizacja:** 18.10.2026 — weryfikacja warunków dostawców (VK Maps), bramka dopuszczenia API do ruchu produkcyjnego i ewidencja dowodów  
**Zależności:** Sprint 158 — POI Infrastructure; Sprint 159 — MASA Scan Interference UX  
**Obszary:** Mapa, SCAN, GhostLab, administracja, infrastruktura geograficzna  
**Strategia:** rozszerzamy istniejące usługi, nie tworzymy drugiego równoległego silnika skanowania.

---

## 0. Decyzja projektowa

**Budujemy własne, trwałe repozytorium obiektów OpenStreetMap odkrywanych przez CHAOS.** Zewnętrzne Overpass API staje się **źródłem uzupełniania brakującego pokrycia i aktualizacji danych**, a nie obowiązkowym etapem każdego skanu gracza.

Skan w świecie CHAOS ma wykorzystywać lokalne dane, jeśli system posiada **kompletne i wystarczająco aktualne pokrycie wymaganego obszaru oraz zgodną semantykę filtrów**. Gdy takiego pokrycia brakuje, pojedyncza kontrolowana operacja pobiera **szerszy, ograniczony obszar OSM**, waliduje go, zapisuje wszystkie pasujące dane do repozytorium wraz z metadanymi pokrycia, po czym obsługuje żądanie gracza. Kolejne skany w tym obszarze mogą już pracować lokalnie.

Jednocześnie do panelu administracyjnego wprowadzamy **rejestr zaufanych dostawców Overpass, edycję ich adresów i polityk oraz monitoring rzeczywistej dostępności**, tak aby zwykła zmiana adresu usługi nie wymagała zmiany kodu i deploya.

> **Najważniejsza zasada:** repozytorium przechowuje OSM i dowód pokrycia geograficznego, a nie wyniki rozgrywki; gameplay jest wykonywany oddzielnie dla każdego gracza. Baza nie może „domyślać się” brakujących obiektów ani udawać kompletnego obszaru.

---

## 1. Dlaczego Sprint 160 jest potrzebny

### 1.1. Fakty ustalone w Sprintach 158–159 i diagnostyce

- CHAOS wykonuje zapytania do Overpass dla `node`, `way`, `relation`, promień skanowania w badanym fragmencie to **300 m**.
- Bazowe filtry: `shop`, `amenity`, `office`, `healthcare`, `atm=yes`, `man_made=surveillance`.
- `result_limit=60` ogranicza wynik **dopiero po pobraniu i kategoryzacji**; dostawca zwraca szerszy zbiór zgodnych obiektów.
- Punkt integracji: `run.py`, wywołanie `fetcher.get_all(...)` w ścieżce `action == "scan"` (w przeanalizowanej wersji około linii 24116).
- Sprint 158 działa na serwerze z **4 workerami**; zapewnia SQLite exact-query cache, globalne współdzielenie zapytań, ograniczenia, circuit breaker i telemetrykę.
- Sprint 159 jest aktywny i mapuje potwierdzoną niedostępność skanu na komunikaty MASA; nie wolno zamieniać błędów aplikacyjnych na „atak MASA”.
- W `poiFetchClass.py` lista endpointów była na stałe w kodzie, a zwykły skan brał domyślnie pierwsze dwa.
- W obserwowanych testach z VPS występowały timeout, HTTP 502, HTTP 500 i błąd DNS. Jeden kontrolowany test na `https://maps.mail.ru/osm/tools/overpass/api/interpreter` zwrócił HTTP 200, **53 obiekty w 15,14 s**. **To jest jeden udany pomiar, nie certyfikat stabilności ani zgoda dostawcy na ruch produkcyjny.**
- **VK Maps / status na dzień aktualizacji:** `TECHNICALLY_TESTED`, `POLICY_PENDING`, **niezatwierdzony do automatycznego ruchu produkcyjnego CHAOS**. OpenStreetMap Wiki zawiera przy VK Maps deklarację korzystania „w dowolnym projekcie” bez określonych limitów żądań, ale oficjalny regulamin usługi VK Maps w pkt 3.9 przewiduje odrębne udostępnianie **VK Maps API** na podstawie umowy. Nie potwierdzono, czy ten punkt obejmuje publiczną instancję **Overpass API** VK Maps; wymagamy wyjaśnienia zakresu u operatora. Źródła i procedura: § 11.1–11.6.

### 1.2. Cel produktu

Zmniejszyć zależność gry od publicznych API tak, aby **raz poprawnie pobrane dane geograficzne mogły służyć wielu przyszłym skanom**, również po restarcie serwera i przy przejściowej niedostępności wszystkich providerów. Z czasem CHAOS buduje **własną mapę poznanego świata**, ale nie miesza tego z indywidualnym stanem odkryć graczy.

### 1.3. Czego nie obiecujemy

- Nie pobieramy „całej planety” podczas jednego skanu ani nie kopiujemy rasterowych kafelków mapy.
- Nie zakładamy, że `out center` wystarczy do geometrycznie poprawnego filtrowania `way/relation` w dowolnym sąsiednim skanie.
- Nie uznajemy jednego `HTTP 200` z `/api/status` ani pojedynczego zapytania za pełną dostępność dostawcy.
- Nie obiecujemy, że repozytorium będzie od razu kompletne globalnie: rośnie obszar po obszarze, zgodnie z budżetem i polityką źródeł.

---

## 2. Docelowa architektura

```text
                           [ GRACZ / MAPA CHAOS ]
                                     |
                                     v
                         [ action=scan / run.py ]
                                     |
                                     v
                            [ POI FETCH FACADE ]
                                     |
                                     v
                       [ CHAOS POI WORLD SERVICE ]
                                     |
                    +----------------+----------------+
                    |                                 |
            [ COVERAGE INDEX ]                 [ QUERY POLICY ]
                    |                                 |
         kompletne pokrycie?                          |
               /         \                            |
              TAK        NIE                          |
               |          |                            |
               v          v                            |
       [ LOCAL OBJECTS ] [ SINGLE-FLIGHT + GLOBAL BUDGET ]
               |          |                            |
               |          v                            |
               |    [ PROVIDER REGISTRY ] <---- [ ADMIN PANEL ]
               |          |                   ustawienia / zdrowie
               |          v                            |
               |    [ OVERPASS API ] ---------> [ TELEMETRY / PROBES ]
               |          |
               |          v
               |   [ VALIDATE + ATOMIC INGEST ]
               |          |
               +----------+
                          v
                [ RAW OSM RESULT for requested scan ]
                          |
                          v
             [ EXISTING CHAOS SCANNER / GAMEPLAY ]
         marked_targets / GhostLab / ikony / NPC / kamery
                          |
                          v
                   [ MARKERS FOR PLAYER ]
```

**158 nie znika:** exact-query cache działa jako niezależna, bezpieczna warstwa kompatybilności i fallback. Nowe repozytorium przestrzenne wykorzystuje istniejący serwis, limity i polityki dostawców, a nie obchodzi ich nowym klientem HTTP.

---

## 3. Dwie warstwy danych — konieczne rozdzielenie

### A. Globalne dane OSM (wspólne)

- tożsamość `osm_type + osm_id` (`node`, `way`, `relation`), tagi, nazwy, geometryczne dane źródłowe lub kompletna reprezentacja do wiernego odtworzenia wyników;
- współrzędne, wersja/znacznik daty OSM o ile źródło je dostarcza;
- źródło pobrania, znacznik czasu, wersja zapytania, źródłowy JSON/hash, informacja o pokryciu i kompletności;
- metadane licencji OSM, stan aktualności, walidacja.

### B. Indywidualna rozgrywka (nigdy do wspólnego magazynu)

- cele i odkrycia gracza (`marked_targets`, `discovered_cameras`), stany frakcji/klanu;
- wynik działania GhostLab, `deep_scanner_token`, `still_active` i jego żywotność;
- `assign_icon_and_type`, lokalny limit 60, kolejność kategoryzacji oraz deduplikacja zgodna z dotychczasowym zachowaniem;
- kamery/NPC generowane proceduralnie, jitter, losowanie, nagrody, koszty, cooldowny oraz uprawnienia;
- dane sesji, aktualna pozycja/nick gracza i jego historia ruchu.

**Warunek izolacji:** dwa równoczesne skany tego samego terenu otrzymują niezależne, kopiowane obiekty wynikowe przed mutacją w `run.py`; żaden gracz nie może zatruć wspólnego źródła zmianą właściwości markera.

---

## 4. Repozytorium geograficzne: obiekty + dowód pokrycia

> Robocza nazwa modułu w kodzie: `poi_world_repository` (poprawna, bez spacji); nazwy tabel poniżej są propozycją do dopasowania do istniejącego schematu i migracji.

### 4.1. Dlaczego sama tabela POI nie wystarczy

Brak obiektów w bazie **nie oznacza braku obiektów w terenie**. Musimy osobno wiedzieć, że dla danego fragmentu mapy pobrano **kompletny wynik** obejmujący wymagane tagi, geometrię i wersję zapytania. Dopiero ten dowód uprawnia do odpowiedzi lokalnej, także pustej.

### 4.2. Proponowane encje

| Encja | Klucz / przykładowe pola | Rola |
|---|---|---|
| `poi_world_object` | `osm_type`, `osm_id`, `tags_json`, `geometry_json`, `center_lat`, `center_lon`, `source_revision`, `updated_at` | Globalny indeks aktualnie znanych obiektów OSM. |
| `poi_world_snapshot` | `snapshot_id`, `provider_id`, `query_version`, `query_hash`, `fetched_at`, `osm_base_timestamp`, `payload_hash`, `payload_size`, `validation_status` | Pochodzenie i integralność konkretnego pobrania. |
| `poi_world_coverage` | `coverage_id`, `cell_id`, `core_bounds`, `query_bounds`, `filter_version`, `geometry_mode`, `snapshot_id`, `complete`, `fresh_until`, `usable_until` | Dowód, że obszar można wiarygodnie obsłużyć lokalnie. |
| `poi_world_membership` | `snapshot_id`, `osm_type`, `osm_id` | Związek pobrania i obiektów; odróżnia zmianę/usunięcie obiektu od braku dostępu do API. |
| `poi_provider` | `provider_id`, `display_name`, `endpoint_url`, `operator_group`, `priority`, `enabled`, `technical_status`, `policy_status`, `config_version` | Trwale konfigurowalne źródła API; technika i warunki użycia w osobnych stanach. |
| `poi_provider_policy_evidence` | `provider_id`, `evidence_id`, `source_url`, `source_type`, `document_version`, `captured_at`, `verified_by`, `scope`, `notes`, `attachment_ref`, `superseded_at` | Audytowalna historia deklaracji, regulaminów i korespondencji — bez trzymania sekretów w UI. |
| `poi_provider_health` | `provider_id`, `checked_at`, `kind`, `http_status`, `latency_ms`, `result`, `failure_reason` | Historia monitoringu i pomiarów prawdziwego transportu. |
| `poi_provider_audit` | `actor_id`, `provider_id`, `action`, `before`, `after`, `at` | Audyt zmian administracyjnych. |

**Istotny problem wersji:** obiekty z różnych snapshotów/serwerów mogą być sprzeczne. Przy scalaniu zachowujemy pochodzenie, preferujemy nowszy wiarygodny snapshot i nie usuwamy obiektu tylko dlatego, że nie pojawił się w innym, mniejszym albo starszym pobraniu. Usunięcia OSM wymagają pełnego, porównywalnego pokrycia lub źródła zmian; brak elementu w niepełnym fetchu nie jest tombstone.

### 4.3. Magazyn fizyczny

- **Wersja początkowa:** SQLite na tym samym hoście, integracja z istniejącym `data/poi_cache.sqlite3` lub osobna baza uzasadniona analizą locków; WAL, indeksy przestrzenne (np. R*Tree dla bbox), ograniczone transakcje.
- **4 workery:** migracje jednokrotnie, atomowe upsert/commit, transakcje krótkie; HTTP **poza transakcją**. Współdzielone leasy z 158 pozostają nadrzędne.
- **Wielkość danych:** limity bajtów, obiektów, liczby komórek, retencja surowych snapshotów i kontrola zajętości dysku. Nie ograniczać bazowego repozytorium krótkim TTL exact-cache 158.
- **Backup i odtwarzanie:** repozytorium jest wartością rosnącą w czasie, więc trzeba je backupować spójnie wraz z indeksem pokrycia, sprawdzać restore i przewidzieć odbudowę indeksów.
- **W przyszłości:** migracja do PostGIS dopiero przy rzeczywiście zmierzonym obciążeniu lub skali; Sprint 160 nie instaluje nowego ciężkiego serwera bazodanowego.

---

## 5. Zasada „szerzej pobierz, lokalnie przytnij”

### 5.1. Dwa różne promienie

- `R_gameplay` — **zachowany** promień skanu (w obecnej integracji bazowo 300 m).
- `R_fetch` — promień uzupełnienia repozytorium **większy** od `R_gameplay` tylko wtedy, gdy udowodnimy, że zmniejsza liczbę zewnętrznych wywołań i mieści się w budżecie API.

Przydatne podejście: **siatka komórek geograficznych z buforem (halo)**. Gracz skanuje w dowolnym miejscu komórki; system może pobrać obszar obejmujący całą komórkę i dodatkowo jej otoczenie o `R_gameplay`. Po udanym i pełnym pobraniu zaznacza pokrycie **rdzenia komórki**, a nie bezpodstawnie całego dużego koła fetchu.

Przykładowa geometria (do benchmarków, nie narzucony parametr): komórka ok. **200 m × 200 m**, `R_gameplay = 300 m`; `R_fetch` liczony z największej odległości od środka komórki do jej narożnika **plus** 300 m i margines numeryczny. Baza zapisuje faktyczny ślad pokrycia, nie tylko zaokrąglony punkt.

**Nie pobieramy całego Overpass dla nieograniczonego obszaru.** Jeśli zapytanie „szerokie” przekracza limit czasu, pamięci lub danych, degraduje do mniejszego zakresu albo dotychczasowego exact-query fallback (158), zamiast zatykać kolejkę API. Rozmiary ustalić na benchmarkach miasta/wsi i różnych gęstości POI.

### 5.2. Najtrudniejszy warunek: `way` i `relation`

Obecne zapytanie używa `nwr(around:...) ...; out center;`, a `way` i `relation` mogą przecinać promień skanu **mimo że ich `center` jest daleko poza nim**. Współrzędne środka obiektu nie wystarczą do ustalenia, czy byłby zwrócony przez Overpass dla nowego środka skanu.

**Dlatego:**

1. Badamy, jak dla wybranych filtrów pobrać **kompletną geometrię** lub bezstratny ekwiwalent potrzebny do lokalnego predykatu przestrzennego, zgodnego z `around` dla `node/way/relation`.
2. Prowadzimy automatyczne testy porównawcze: odpowiedź lokalna kontra oryginalne dokładne zapytanie Overpass dla **tego samego snapshotu danych**. Osobno granice komórek, linie przecinające koło, duże budynki, relacje wieloczęściowe, puste wyniki.
3. **Bez udowodnionej zgodności geometria nie jest certyfikowana**: w takim przypadku nie korzystamy z sąsiedniego pokrycia do rozstrzygania pełnego skanu i wracamy do bezpiecznej ścieżki exact-query cache / upstream z 158. Nie filtrujemy wyłącznie po `center`.
4. Jeżeli `out geom` okaże się za ciężkie, wprowadzamy osobny profil zapytań z kontrolowaną selekcją geometrii lub odkładamy współdzielenie sąsiednich pozycji do dalszego etapu — bez pozornej kompletności.

### 5.3. Co konkretnie zapisujemy

**Wszystkie** zwalidowane obiekty pobrane zgodnie z profilem pokrycia, nie tylko pierwsze 60 i nie tylko markery, które faktycznie zobaczył gracz; również obiekty niewykorzystane w danym skanie (ale zgodne z zakresem filtrów), metadane powierzchni, daty i źródła.

Po odczycie lokalnym uruchamiamy **ten sam istniejący** pipeline `POIFetcher._categorize_data()` / `get_all()` i kod gameplay w `run.py`, zachowując kolejność kategorii, obecne limity i deduplikację.

### 5.4. Aktualizacja i konflikty

- Osobne `freshness` danych OSM i `retention` w repozytorium. Rekord może pozostać na dysku długo, nawet jeśli wymaga odświeżenia.
- Rozróżnić: kompletne aktualne pokrycie / kompletne historyczne pokrycie / częściowy zapis / brak pokrycia.
- Przy awarii i **kompletnym historycznym pokryciu** można obsłużyć skan w trybie degraded według jawnej polityki i informować 159. Nie wyświetlać jako świeże.
- Przy niekompletnym pokryciu i braku upstream: `BLOCKED` MASA, chyba że exact-cache 158 rzeczywiście zawiera kompletną odpowiedź dla dokładnego zapytania.
- Rozważ odświeżanie wyłącznie popularnych komórek z ograniczonym budżetem, a nie globalny robot pobierający bez końca. Refresh ma niski priorytet wobec rzeczywistego skanu.

---

## 6. Algorytm wykonania skanu

```text
SCAN(lat, lon, scanner_options)
  1. Zachowaj dotychczasową autoryzację, dystans i reguły GhostLab.
  2. Ustal canonical query + parametry R_gameplay i wersję filtrów.
  3. Spróbuj exact-query cache z 158, jeśli jest świeży i poprawny.
  4. Zapytaj POI World Repository o pokrycie CAŁEGO obszaru skanu.
     4a. Pokrycie kompletne, zgodna geometria i akceptowana aktualność:
         -> zrekonstruuj pełny rezultat OSM i przejdź do gameplay.
     4b. Pokrycie niekompletne lub nieudowodnione:
         -> przejmij shared lease na geograficzny obszar pobierania.
  5. Sprawdź limity, aktywnych i dozwolonych providerów z admin registry.
  6. Wykonaj jedno kontrolowane pobranie obszaru + halo (jeśli opłacalne),
     respektując dostępny globalny slot, deadline, circuit breaker i retry 158.
  7. Sprawdź HTTP/JSON/OSM, limit wielkości, kompletność geometrii,
     query version; nie publikuj niepełnego pokrycia.
  8. Atomowo zapisz snapshot, obiekty, membership, coverage.
  9. Zapisane dane wykorzystaj do rekonstrukcji wyników żądanego skanu;
     jeśli potrzeba, wykonaj zgodny fallback exact-query 158 (w budżecie).
 10. Przekaż niezależną kopię surowego OSM do obecnego gameplay.
 11. Przy awarii skorzystaj z pełnego stale / 158; jeśli się nie da,
     zwróć prawdziwy stan MASA 159 bez spamowania API.
```

**Kolejność odczytów 158 vs repozytorium** może zostać zoptymalizowana w implementacji, ale musi gwarantować poprawność, bezpieczeństwo i brak dodatkowego upstream dla już pokrytego obszaru. `still_active` i anulowanie muszą działać w każdej fazie, również oczekiwania na lease.

---

## 7. Rejestr dostawców API w panelu admina

### 7.1. Cel

Administrator potrafi **zmienić URL istniejącego dostawcy lub dodać nowy sprawdzony endpoint bez edytowania Pythona, `~/.bashrc` czy restartowania całego CHAOS**. Zmiana konfiguracji w bazie staje się widoczna workerom dzięki wersjonowanej konfiguracji z krótkim lokalnym TTL / invalidacją; nie dodawać wywołania SQL z ciężkim odczytem do każdego markera.

### 7.2. Dane dostawcy

- Nazwa wyświetlana i stabilny `provider_id`.
- Dokładny `endpoint_url` (`/api/interpreter`) i opcjonalny endpoint statusowy (`/api/status`).
- Grupa operatora/infrastruktury — różne hosty tej samej infrastruktury **nie udają niezależnych źródeł**.
- Priorytet/rola: `primary`, `fallback`, `disabled` (plus osobno weryfikacja).
- **Dwa niezależne stany:** `technical_status` (`untested`, `testing`, `tested_ok`, `tested_failed`) i `policy_status` (`unknown`, `public_declaration_only`, `operator_confirmation_pending`, `approved_for_defined_use`, `restricted`, `rejected`, `expired_review`). `verified_by_chaos` jest **decyzją wewnętrzną** wynikającą z obu bramek, nie tytułem/certyfikatem operatora.
- **Polityka użycia / licencja / data weryfikacji:** URL źródła regulaminu/deklaracji, wersja lub data źródła, kto sprawdził, kiedy sprawdził, data następnego przeglądu, kontakt do operatora, identyfikator pisemnej zgody/odpowiedzi (jeśli istnieje), notatka prawno-operacyjna.
- **Zakres dopuszczonego użycia:** serwer–serwer, automatyczne skanowanie multiplayer, testy aktywne, pojedyncze/wiele zapytań, szersze pobieranie, trwałe lokalne magazynowanie OSM, aktualizacje/redistribucja, ewentualne limity i wymagane oznaczenia; dokumentować ograniczenia zamiast zakładać zgodę na wszystko.
- **Oddzielić licencję danych OSM (ODbL) od regulaminu/zgody operatora instancji API.** Prawo do przetwarzania danych OSM nie gwarantuje prawa do nielimitowanego używania cudzego serwera.
- Limit równoczesności, timeouty, budżety wywołań, cooldown i circuit breaker — **w granicach globalnej polityki** 158, bez rozszczelnienia.
- Ostatni udany test `interpreter`, ostatni realny błąd, opóźnienie, czas aktualizacji OSM (jeśli dostarczony), data weryfikacji przez operatora CHAOS.
- Informacja, czy dostawca akceptuje taki model ruchu (polityka, kontakt, ewentualna umowa); notatka operacyjna.

`verified_by_chaos` oznacza **naszą wewnętrzną akceptację techniczno-operacyjną**, a nie certyfikat wystawiony przez OpenStreetMap lub gwarancję SLA.

### 7.3. Workflow admina

```text
Dodaj / edytuj endpoint
       |
       v
[ walidacja URL + bezpieczeństwa ]
       |
       v
[ kandydat: bez ruchu graczy ]
       |
       v
[ test techniczny: status + mały rzeczywisty interpreter ]
       |
       v
[ TECHNICALLY_TESTED; bez automatycznego ruchu produkcyjnego ]
       |
       v
[ dowody polityki + określenie zakresu użycia ]
       |
       +---- niejasność / brak zgody? ----> [ POLICY_PENDING / DISABLED ]
       |
       v
[ decyzja operatora CHAOS: APPROVED dla jawnego zakresu ]
       |
       v
[ zatwierdzenie przez uprawnionego admina ]
       |
       v
[ aktywuj primary/fallback; wersja konfiguracji++ ]
       |
       v
[ monitoring / degradacja / disable / rollback ]
```

Zmiana URL istniejącego provider ID powoduje **nową weryfikację techniczną** nowego adresu; nie dziedziczy automatycznie zatwierdzenia, niezależnie od dotychczasowej nazwy. Jeżeli zmienia się operator, domena, warunki albo zakres użycia, ponownie wymagana jest też akceptacja polityki. Opcjonalnie zachowujemy historię poprzednich URL i przycisk bezpiecznego rollbacku po rewalidacji.

### 7.3a. Reguła aktywacji: brak milczącej zgody

- `enabled_for_gameplay = true` **wyłącznie** po `technical_status=tested_ok` **oraz** `policy_status=approved_for_defined_use` obejmującym daną funkcję; sam zielony probe nie wystarcza.
- Rozdzielić uprawnienia/budżety dla: `small_probe`, `normal_scan`, `wide_fetch`, `background_refresh`. Zatwierdzenie normalnych zapytań nie oznacza automatycznego zatwierdzenia większego pobierania i trwałego seedowania repozytorium.
- `POLICY_PENDING` nie trafia do aktywnej listy źródeł dla graczy i nie jest oznaczane w panelu jako „certyfikowane”. Dozwolone mogą być wyłącznie ręczne, pojedyncze testy diagnostyczne po akceptacji operatora CHAOS i w zgodzie z publicznymi zasadami usługi — z osobnym budżetem.
- Gdy operator nie odpowiedział, pozostawiamy status oczekujący; brak odpowiedzi **nie oznacza zgody**. Przegląd warunków po zmianie regulaminu, zakresu użycia lub w określonym terminie; po utracie ważności przeglądu blokować nowe aktywacje, a w razie potrzeby wstrzymać ruch.
- W panelu przy każdym providerze widoczne są osobno: **TECHNIKA**, **WARUNKI**, **DOZWOLONY ZAKRES**, **DECYZJA**, **DATA I ŹRÓDŁO**. Wszystkie zmiany audytowane.

### 7.4. Warunek krytyczny: ochrona przed SSRF

Panel konfiguracji zewnętrznych URL-i jest potencjalną furtką do wewnętrznej sieci VPS. Wymagania:

- Tylko wąska rola administracyjna i istniejąca autoryzacja, CSRF dla zapisów, dziennik audytu `kto/co/kiedy`; żadnych zmian z publicznego klienta gry.
- Wyłącznie HTTPS z poprawnym TLS i ściśle ustaloną ścieżką endpointu, bez userinfo, portów niestandardowych bez jawnej polityki i bez podawania nagłówków/autoryzacji przez admina.
- Rozwiązywanie DNS i sprawdzanie adresów **przy dodaniu i przy każdym połączeniu**: odrzucać loopback, prywatne, link-local, metadata IP, zastrzeżone zakresy IPv4/IPv6; chronić przed DNS rebinding i proxy środowiskowym. Nie wystarczy `startswith('https')`.
- Wyłączone przekierowania HTTP; limit rozmiaru odpowiedzi, timeout i globalna kolejka również dla testów; blokada podejrzanych domen.
- Zapisywany, zatwierdzony `provider_id` i allowlista operatorów/domen; nowe domeny wymagają jawnej akceptacji, nie automatycznego „testuj dowolny URL”.
- Tajne tokeny (jeżeli kiedyś pojawią się płatni providerzy) poza bazą dostępnej UI; maskowanie i izolacja sekretów.

**Nie pozwalać użytkownikom z panelu budować dowolnych Overpass QL**: zdrowie badamy sztywnym, małym, niewrażliwym zapytaniem.

---

## 8. Monitoring dostępności API w panelu admina

### 8.1. Widok „POI / Dostawcy i zdrowie”

Dla każdego providera pokazać:

- status **ACTIVE / DEGRADED / CIRCUIT OPEN / UNREACHABLE / DISABLED / UNVERIFIED**;
- osobny badge **POLICY_PENDING / APPROVED_SCOPE / RESTRICTED / REVIEW_EXPIRED**, link do zasad korzystania, datę i autora weryfikacji oraz informację, czy dopuszczono `normal_scan`, `wide_fetch`, `background_refresh`; **technicznie UP nie oznacza prawnie zatwierdzone**;
- czas ostatniego testu, czas ostatniego udanego **rzeczywistego** zapytania, rozróżnienie testu od ruchu graczy;
- HTTP status (np. 200, 429, 500, 502), DNS, timeout, TLS, błędy JSON/schematu;
- opóźnienie ostatnie oraz p50/p95 w oknie z odpowiednią liczbą próbek, procent sukcesów w ostatniej godzinie / 24 h; nie wyświetlać wymyślonych wartości przy braku danych;
- stan circuit breaker, planowany najwcześniejszy probe (`Retry-After`/cooldown), grupę operatora;
- liczbę prób API, hitów repozytorium, exact-cache, stale, rozmiar i pokrycie bazy;
- ostatni błąd w formie administracyjnej, ale bez ujawniania sekretów czy danych graczy.

**Monitoring ma odpowiadać na pytania:** czy potrafimy pobrać POI z naszego VPS, jaki mamy stan własnego pokrycia i czy gracze skanują z bazy, czy czekają na Overpass?

### 8.2. Jak testować, żeby sam monitoring nie spamował API

- **Pasywny monitoring**: metryki prawdziwych wywołań z 158 — domyślne i podstawowe źródło prawdy.
- **Aktywny probe**: pojedynczy mały, z góry określony query do `/api/interpreter` (nie tylko `/api/status`) wykonywany przez **jeden** skoordynowany background job, nie przez każde odświeżenie panelu / gracza.
- Proponowane pierwsze ustawienie: nie częściej niż **co 15 minut na niezależną grupę dostawcy**, dostosowane do jego zasad. Nie odpalać probe, gdy niedawno był udany ruch rzeczywisty i wynik nadal aktualny.
- Każdy probe respektuje ten sam globalny budżet zapytań, circuit breaker, `Retry-After` i limity providerów; administracyjne „Sprawdź teraz” ma osobny rate limit, kontrolę uprawnień i nie omija blokady.
- `HTTP 200 /api/status` oznacza jedynie, że endpoint statusowy odpowiedział. **Zielony dostęp do POI** wymaga poprawnego JSON z testu interpreter, walidacji wyniku i informacji o czasie.
- Health check nie zużywa zasobów gracza i nie generuje zakłóceń MASA; MASA 159 sygnalizuje brak obsługi **konkretnego skanu** po uwzględnieniu cache i providerów.

### 8.3. Alerty i UX panelu

- Gdy wszystkie zatwierdzone provider groups są niedostępne: czerwony alarm **UPSTREAM DOWN**, ale osobna informacja **LOCAL REPOSITORY AVAILABLE** i stopień pokrycia.
- Gdy jeden provider pada, a fallback lub baza działa: ostrzeżenie, nie globalna awaria gry.
- Możliwe notyfikacje do administratora / webhook w przyszłości; brak spamowania alertami przy każdym skanie.
- Status panelu nie jest fabularnym ekranem gracza: **admin widzi rzeczywiste HTTP i nazwy operatorów; gracz widzi odpowiednie komunikaty MASA tylko wtedy, gdy skanu nie można obsłużyć**.

---

## 9. Zarządzanie awarią i komunikaty MASA (kontynuacja 159)

| Stan infrastruktury 160 | Odpowiedź dla gry | Komunikat / zachowanie |
|---|---|---|
| Obszar kompletny i świeży w repozytorium | Normalny skan bez API | Brak MASA. |
| Obszar kompletny, historyczny, polityka pozwala na stale | Normalny wynik z metadanymi `degraded` | „Zakłócenia MASA. Odczytano ostatni dostępny zapis terenu.” |
| Brak kompletnego pokrycia, provider działa | Jedno pobranie uzupełniające, potem skan | Standardowy scan/loading. |
| Brak kompletnego pokrycia, wszystkie dopuszczalne źródła odcięte | `api_error` z potwierdzoną blokadą | „MASA zakłóca sieć rozpoznania…”; bez retry spam. |
| Jest tylko częściowo zapisany obszar | Nie udawać kompletnego skanu | Dokładny cache/upstream albo prawdziwa blokada; bez pożyczania kilku POI z sąsiedniej komórki jako pełnego wyniku. |
| Błąd uprawnień, tokenu, konfiguracji, storage | Odpowiedni błąd techniczny/gameplay | **Nie** tłumaczyć na MASA. |
| API wróciło, ale teren już mamy lokalnie | Normalny skan | Nie ogłaszać „sygnał odzyskany” bez faktycznie potwierdzonego odzyskania; brak zbędnego wywołania API. |

**Zasada ekonomii:** niedostępność dostawcy lub nieudany fill repozytorium nie może zużyć waluty/zasobu skanera, jeśli skan nie został faktycznie obsłużony. Wszelkie modyfikacje kosztów muszą być zgodne z istniejącym mechanizmem, nie tworzą nowych darmowych ścieżek.

---

## 10. Konfiguracja / wersjonowanie

**Nowe przełączniki (propozycja; dopasować do repozytorium):**

```text
CHAOS_POI_WORLD_REPOSITORY_ENABLED=0
CHAOS_POI_WIDE_FETCH_ENABLED=0
CHAOS_POI_PROVIDER_ADMIN_ENABLED=0
CHAOS_POI_PROVIDER_MONITOR_ENABLED=0
```

To **propozycje flag dla Codexa**, a nie istniejące zmienne, które można już bezpiecznie ustawić w PM2. Włączenie repozytorium jako zapisu i jako źródła odczytu może wymagać niezależnego sterowania. Sprint 158 (`CHAOS_POI_INFRASTRUCTURE_ENABLED=1`) i Sprint 159 (`CHAOS_POI_MASA_UX_ENABLED=1`) pozostają bez zmian.

Provider registry ma być bazą konfiguracji, z **wersją/epoch** odczytywaną i synchronizowaną przez wszystkie cztery workery; seed startowy pochodzi z istniejących endpointów, ale **nie nadaje im automatycznie statusu verified**. Po skonfigurowaniu panelu nie traktujemy starego hardcode jako niejawnej dodatkowej listy aktywnych providerów.

Nowy mechanizm nie wymaga deploymentu przy **bezpiecznej, zweryfikowanej zmianie samego URL**. Zmiany protokołu, formatu danych, query semantics czy dostawcy wymagającego nowego schematu autoryzacji mogą już wymagać prac programistycznych.

---

## 11. Bezpieczeństwo, prywatność, licencje

- Repozytorium OSM zawiera **wyłącznie publiczne dane geograficzne**, a nie listę ruchów graczy. Pokrycie zapisywać po komórkach, nie tworzyć publicznego katalogu pozycji pojedynczych użytkowników.
- Admin UI nie ujawnia tokenów ani szczegółów kont i ma kontrolę roli, CSRF, limity i log audytu.
- Zewnętrzny provider widzi współrzędne lub obszar zapytania i adres IP VPS. Dodatkowo ocenić operatora, jurysdykcję i politykę prywatności, w szczególności przy źródłach spoza UE.
- Dane OSM są na **ODbL**: zachować widoczne przypisanie „© OpenStreetMap contributors”, informację o licencji i pochodzeniu; przed udostępnieniem własnej pochodnej bazy sprawdzić obowiązki share-alike. Repozytorium CHAOS nie jest „własnością” w znaczeniu wyłącznej licencji na dane OSM — jest **naszą infrastrukturą ich przechowywania i serwowania**.
- Zweryfikować politykę publicznych endpointów, szczególnie dla automatycznego, szerokiego zapisu i ponawiania; pojedynczy udany test nie daje prawa do masowego pobierania. Unikać wysyłania danych kont lub użytkowników w nagłówkach/logach dostawcy.

**Referencje prawne:** https://www.openstreetmap.org/copyright oraz https://osmfoundation.org/wiki/Licence_and_Legal_FAQ .

### 11.1. Dwie różne zgody: OSM i instancja Overpass

1. **Dane:** OpenStreetMap są udostępniane na ODbL. Dopuszczalne wykorzystanie, utrzymywanie i publikacja własnego repozytorium wymaga atrybucji i rozstrzygnięcia obowiązków dla ewentualnej `Derivative Database`/`Produced Work` przy publicznym użyciu. Rozdział danych geograficznych i stanu gracza ułatwia zgodność, ale sam w sobie nie zwalnia z obowiązków licencyjnych.
2. **Serwer:** operator publicznego Overpass może narzucać politykę dla ruchu automatycznego i pobierania większych zakresów, niezależnie od ODbL. **Licencja ODbL nie jest umową SLA i nie daje bezwarunkowego prawa do przepustowości dowolnej instancji.**
3. **CHAOS:** osobno dokumentujemy akceptację `normal_scan`, `wide_fetch` i `background_refresh`, z deklarowanym budżetem żądań/danych. Jeśli nie da się potwierdzić dopuszczalności, nie aktywujemy providera dla tych zastosowań.

### 11.2. VK Maps — stan rozpoznania na 18.10.2026

| Obszar | Ustalenie | Status dowodowy |
|---|---|---|
| API Overpass VK Maps | Endpoint `https://maps.mail.ru/osm/tools/overpass/api/interpreter` zwrócił w pojedynczym teście CHAOS HTTP 200 i 53 obiekty (~15,14 s). | `TECHNICALLY_TESTED` — jeden sukces, bez SLA i testu trwałej dostępności. |
| Deklaracja publiczna | Na **OpenStreetMap Wiki / Overpass API** przy VK Maps operator deklaruje możliwość korzystania w dowolnym projekcie i brak aktualnie zadeklarowanych limitów zapytań. | **Deklaracja w wykazie społecznościowym**, nie indywidualna umowa z CHAOS. |
| Oficjalne warunki VK Maps | Regulamin VK Maps, **punkt 3.9**, opisuje osobne udostępnianie **VK Maps API** na podstawie umowy. Pkt 4.2 odnosi się do danych OSM. | **Nieustalony zakres**: nie przesądzamy, że pkt 3.9 obejmuje albo wyłącza odrębny publiczny endpoint Overpass. |
| Zastosowanie CHAOS | Automatyczny backend multiplayer, szerokie okresowe pobieranie, trwały magazyn POI. | `POLICY_PENDING`: przed produkcyjnym dopuszczeniem wymagane sprawdzenie polityki dla tego **konkretnego** użycia. |
| Operator / jurysdykcja | VK Maps: operator rosyjski; współrzędne żądań i IP VPS mogą zostać ujawnione serwerowi źródłowemu. | Osobna ocena bezpieczeństwa, ryzyka operacyjnego i prywatności. |

**Źródła do podpięcia w panelu jako dowody:**

- [OpenStreetMap Wiki — Overpass API, wiersz VK Maps](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [VK Maps — oficjalny regulamin, § 3.9 i 4.2](https://help.mail.ru/legal/terms/maps/terms/)
- [OSMF — Licence and Legal FAQ](https://osmfoundation.org/wiki/Licence_and_Legal_FAQ)
- [OSM — Copyright / ODbL](https://www.openstreetmap.org/copyright)

**Decyzja na dziś:** `technical_status=tested_ok` (jedynie podstawowa łączność), `policy_status=operator_confirmation_pending`, `enabled_for_gameplay=false`, `wide_fetch=false`, `background_refresh=false`. To stan **proponowany do zapisania w rejestrze Sprintu 160**, a nie twierdzenie, że VK już figuruje w naszej produkcyjnej bazie.

### 11.3. Procedura zatwierdzenia dostawcy

1. **Zidentyfikuj usługę i operatora**: konkretna domena + pełny endpoint `/api/interpreter`, niezależna grupa infrastruktury, kraj operatora.
2. **Zarchiwizuj źródła warunków**: adres, data odczytu, numer/wersja regulaminu, streszczenie i dowód (referencja do dokumentu lub korespondencji).
3. **Zapytaj operatora wprost**, czy jego publiczny Overpass API podlega pkt 3.9 regulaminu VK Maps i czy dopuszcza model użycia CHAOS. Odpowiedź powinna obejmować automatyczne żądania, ograniczenia ruchu, szersze skany, trwałe przechowywanie OSM, obowiązkową atrybucję, rejestrację/klucz i procedurę zmian.
4. **Oceń niezależnie ODbL** dla własnego repozytorium i publicznego interfejsu gry; zapisz decyzję. Potwierdzenie operatora serwera nie zastępuje analizy licencji OSM.
5. **Zatwierdź jawny zakres**, nie „API ogólnie”: limit/profil normalnych skanów i osobną decyzję o `wide_fetch`/`background_refresh`. Przy braku potwierdzenia nie aktywuj ruchu produkcyjnego.
6. **Przypisz dowody, właściciela i termin ponownej kontroli**, a dopiero potem nadaj status `approved_for_defined_use` i włącz odpowiednie role przez admina.

### 11.4. Kontakt i gotowa wiadomość do operatora VK Maps

**Kontakt wskazany w regulaminie VK Maps:** `support.maps@lists.vk.team` (weryfikować ponownie przed wysłaniem). Nie oznacza to, że ten adres musi być bezpośrednim administratorem instancji Overpass — prosimy o przekierowanie w razie potrzeby.

**Subject: VK Maps Overpass API — confirmation of usage terms for CHAOS**

```text
Hello,

I develop CHAOS (https://chaos.re), a non-commercial persistent multiplayer
browser game that uses OpenStreetMap POI data.

We are considering using your public Overpass API endpoint:
https://maps.mail.ru/osm/tools/overpass/api/interpreter

The OpenStreetMap Wiki describes this service as available for use in any
project without currently stated request limits. Your VK Maps terms (section
3.9) describe separate contractual access to the VK Maps API. Could you
please clarify whether that section applies to your public Overpass endpoint?

Could you confirm:
1. Whether automated server-to-server requests for a multiplayer game are
   permitted and whether registration, an API key or a separate agreement
   is required.
2. Applicable rate limits, concurrency limits and recommended backoff.
3. Whether wider-area fetches and long-term caching of retrieved OSM POI
   data in our own repository are acceptable under your service policy
   (we will independently comply with ODbL requirements).
4. Whether periodic low-frequency health checks and data refreshes are
   permitted and any preferred limits.
5. Whether there are regional restrictions or specific attribution and
   notification requirements applicable to this Overpass endpoint.

Our backend uses caching, shared request deduplication, rate limiting,
circuit breakers and exponential backoff to minimize traffic.

Thank you for your help. If this is not the correct team, please forward
our inquiry to the Overpass service operator.

Best regards,
CHAOS Development
https://chaos.re
```

**Operacyjnie:** mail jest **szablonem do wysłania**, nie został wysłany w ramach tego sprintu; dopóki nie mamy pisemnego stanowiska lub innego wystarczającego, udokumentowanego dowodu akceptacji konkretnego zakresu, status pozostaje `POLICY_PENDING`.

### 11.5. Rejestr dowodów: minimalny model i trwałość

Dla każdego providera przechowuj osobno:

- `terms_url`, `terms_version`, `terms_checked_at`, `evidence_source` (`official_terms`, `operator_reply`, `community_wiki`, `internal_test`), `evidence_reference`, `checked_by`;
- `operator_contact`, `operator_confirmation_at`, `confirmed_usage_scope`, `request_rate_policy`, `data_retention_policy`, `attribution_requirements`, `jurisdiction_risk`, `review_due_at`;
- historię decyzji (`approved_by`, `approved_at`, `approval_notes`, `revoked_at`) i wersjonowanie aktualnego `endpoint_url`;
- **oddzielne** metryki techniczne `last_http_status`, `latency_ms`, `last_valid_interpreter_at` — nie mieszaj ich z polem legalnego dopuszczenia.

Evidence może zawierać korespondencję/załącznik w bezpiecznym repozytorium administracyjnym, z kontrolą dostępu; log w publicznym API panelu ma tylko identyfikator referencyjny. Dla zmiany URL/domeny, warunków i zakresu ruchu wykonaj ponowną kontrolę oraz zapisz nową decyzję.

### 11.6. Kiedy dopuszczamy VK Maps do gry?

**Nie na podstawie samego HTTP 200.** Potrzebne: (a) formalna decyzja CHAOS dotycząca dopuszczalnego zakresu po ocenie dowodów, (b) potwierdzenie zgodności ODbL dla planowanej bazy, (c) ocena ryzyka operatora, (d) techniczne sprawdzenie stabilności i limitów, (e) konfiguracja budżetu, (f) możliwość natychmiastowego disable oraz rollbacku. Jeśli zgoda nie obejmuje szerokich zapytań, możliwe jest zatwierdzenie wyłącznie zwykłego skanowania — **bez** szerokiego pobierania i refreshu.

**To jest bramka wdrożeniowa Sprintu 160**, a nie zalecenie, by wbrew obecnej niepewności natychmiast przełączyć produkcję na VK Maps.

---

## 12. Kompatybilność i testy regresyjne

### 12.1. Regresje gameplay

- Ten sam kontrakt `fetcher.get_all(...)`, `run.py`, `scan_outcome`, markerów i i18n; nie naruszyć `GhostLab.extra_retries`, `extra_timeout`, `still_active`.
- Odkrycia, oznaczenia, kamery, NPC i losowość nie mogą zostać utrwalone we wspólnej bazie.
- Dwa skany tej samej lokalizacji przez różnych graczy: wspólne **surowe OSM**, różne **stany gry**.
- Poprawne działanie przy normalnych 300 m, wzmocnionym zasięgu i limitach elementów — tylko o ile rzeczywiste parametry gameplay zostały przeanalizowane.

### 12.2. Testy repozytorium i geometrii (obowiązkowe)

1. Pusty stan → jedno pobranie → poprawny zapis obiektów + kompletnego pokrycia.
2. Skan w tej samej komórce → **0 zewnętrznych wywołań** przy zatwierdzonej lokalnej zgodności.
3. Sąsiednia pozycja na granicy komórki → prawidłowy wynik i brak ukrytych ubytków.
4. `node/way/relation` przecinające 300 m, których `center` jest poza zakresem.
5. Relacje wieloczęściowe, obiekty bez danych, zmienne tagi, duże obiekty przekraczające komórkę.
6. Snapshot z poprawną pustą listą → kompletne **puste pokrycie**; HTTP 500, 502, HTML, JSON ucięty, za duży albo błąd geometrii → **żadnego complete=true**.
7. Nowsze/ starsze snapshoty, sprzeczne tagi, brak obiektu w mniejszym skanie → bez przypadkowego kasowania.
8. Przekroczenie budżetu szerokiego fetchu → kontrolowany fallback 158; brak deadlocka.
9. Cztery workery, 20 równoległych żądań jednego/ sąsiednich terenów → najwyżej jeden upstream dla tego samego lease, zgodne obiekty, nieprzekroczony budżet.
10. Restart app / reboot / restore bazy → odczyt prawidłowego pokrycia bez upstream.
11. Porównanie zbiorów `(osm_type, osm_id, tags, geometry/center)` dla danych z **tego samego snapshotu OSM**; jakość kolejności / ograniczeń 60 wg starej ścieżki.
12. Dwa workery nad tym samym obiektem: modyfikacja wyników w gameplay nie zmienia repozytorium ani odpowiedzi drugiego gracza.

### 12.3. Testy admina i providerów

- Uprawnienia: nie-admin nie widzi / nie zmienia providerów; CSRF i audyt zapisów.
- Zmiana URL i priorytetu propaguje się do **4 workerów bez deploya**; rollback działa.
- Provider `tested_ok` + `policy_pending` jest czytelny w UI, **nie może** trafić do produkcyjnego ruchu graczy; `wide_fetch` i `background_refresh` mają osobne zakresy zgody.
- Zmiana operatora/domeny lub regulaminu unieważnia poprzednią decyzję w odpowiednim zakresie, zachowując historię dowodów; brak odpowiedzi na zapytanie nie powoduje auto-approve.
- Widok admina pokazuje `terms_url`, `terms_checked_at`, `verified_by`, odpowiedź operatora (referencja), datę ponownej oceny i osobne statusy techniczny/polityki.
- Nieudany test nie aktywuje niezaufanego endpointu.
- SSRF: loopback, lokalne CIDR, metadata, DNS rebinding, IPv6, redirect i URL z poświadczeniami odrzucone.
- Dwa hosty w tej samej grupie operatora nie dostają niezależnych limitów.
- „Odśwież panel” nie wysyła nowych zapytań Overpass; aktywne probe zachowuje budżet.
- Health: status 200 z `/api/status`, ale HTTP 500 interpreter → admin widzi **niedostępny POI**.
- `429 Retry-After`, timeout, 500/502/503/504, DNS, zły JSON, TLS → prawidłowa klasyfikacja, circuit, MASA bez fałszywego RESTORED.

### 12.4. Przeglądarki i języki

- Desktop / portrait mobile; czytelne badge admina i stany MASA, PL/EN, brak ingerencji w układ mapy i mapowe logi glitch.
- Łatwe rozróżnienie „brak internetu do Overpass” od „lokalne dane są dostępne”.

---

## 13. Plan wykonawczy Sprintu 160

### 160.0 — Audyt i kontrakty (bramka obowiązkowa)

- Odczytać implementację Sprintu 158 (`poi_infrastructure/service.py`, repozytorium, policy, telemetria), Sprintu 159 (prezentacja) oraz istniejące API i autoryzację admina.
- Potwierdzić, że baza jest współdzielona między 4 workerami, gdzie i jak przechowywany jest config, jak faktycznie przekazywane są promienie i wyniki GhostLab.
- Zmierzyć baseline: hit rate exact-cache, realne requesty upstream, czasy, rozmiary, obecny rozmiar bazy i p95 skanu.
- Spisać testowalny kontrakt „kompletna lokalna odpowiedź = równoważna oryginalnemu zapytaniu”.
- Spisać status dostawców (technika vs warunki), szczególnie **VK Maps jako policy pending** mimo jednego udanego testu. Nie uruchamiać w produkcji pobierania w celu budowania repozytorium bez zgodnego zakresu użycia.

**Gate:** istnieje mały RFC/kontrakt i zestaw fixture'ów potwierdzających geometryczne edge-case'y.

### 160.1 — Model obiektów i pokrycia

- Tabele + migracje + indeksy, zapis surowych OSM, provenance, wersja zapytania, kompletność pokrycia, CRUD wewnętrzny i testy restartu.
- W pierwszym kroku **shadow ingest**: skany dalej czytają z 158, ale udane odpowiedzi mogą bezpiecznie budować repozytorium.
- Zero zmian w markerach/ekonomii gry.

**Gate:** trwały, poprawny zapis pełnych pobrań, brak fałszywego pokrycia.

### 160.2 — Szersze pobieranie i lokalne odtwarzanie

- Dobór komórek + halo, pełna geometria lub równoważny model, limit wielkości i czasu.
- Rekonstrukcja zbioru OSM dla dowolnego punktu w certyfikowanym rdzeniu.
- Porównania parity do Overpass na kontrolowanych snapshotach.
- Włączenie lokalnego odczytu wyłącznie dla komórek, których geometria/filter_version/coverage są zweryfikowane; reszta używa 158.

**Gate:** seria skanów w sąsiednich punktach działa lokalnie z **0 wywołań API** i zgodnym wynikiem.

### 160.3 — Provider Registry i administracja

- Migracja listy endpointów z kodu do rejestru zarządzanego przez admina.
- Edycja, walidacja, test, akceptacja wewnętrzna, aktywacja/dezaktywacja, kolejność, operator groups, historia i rollback.
- Dodać ewidencję warunków i akceptacji: `technical_status` + `policy_status`, `terms_url`, `terms_checked_at`, `usage_scope`, dowody (regulamin/odpowiedź operatora), data przeglądu i kontrola ponownej weryfikacji. **VK Maps pozostaje POLICY_PENDING**, dopóki nie rozstrzygniemy zastosowania pkt 3.9 i planowanego ruchu.
- Pełne zabezpieczenie SSRF/RBAC/CSRF/audytu.

**Gate:** zmiana zatwierdzonego URL możliwa bez edycji kodu i bez ręcznego restartu workerów; po zmianie wymagany ponowny test; **dwa oddzielne potwierdzenia (techniczne i dopuszczalność użycia)** są udokumentowane przed aktywacją.

### 160.4 — Health + panel operacyjny

- Realne metryki transportu, pasywne health, rzadkie kontrolowane aktywne probe, lokalne metryki repozytorium.
- Statusy i panel z błędami, opóźnieniami i pokryciem; read-only admin status niezależny od odpowiedzi API na żywo.
- Badge warunków: `POLICY_PENDING` / `APPROVED_SCOPE` / `RESTRICTED` / `REVIEW_EXPIRED`; link do regulaminu i potwierdzenia (dla uprawnionych), dozwolone rodzaje ruchu.
- Mapa stanu providerów nie generuje dodatkowego ruchu na każdy refresh.

**Gate:** admin może wskazać źródło, które działa, rzeczywisty poziom cache hit i ostatni błąd bez wchodzenia na VPS.

### 160.5 — Integracja 159, rollout i twarde testy

- Stany MASA zgodne z realną możliwością obsłużenia konkretnej lokalizacji.
- Full test run, obciążenie wieloworkerowe, odtworzenie bazy, testy bezpieczeństwa panelu.
- Rollout flagami zgodnie z sekcją 14.

**Gate:** przy awarii wszystkich źródeł skany na kompletnie zapisanych terenach **działają**, nowe nieznane tereny nie spamują API i dają prawdziwy komunikat MASA.

---

## 14. Rollout produkcyjny i rollback

1. **Deploy z flagami 160 = OFF** przy pozostawieniu 158/159 bez zmian. Migracja musi być kompatybilna wstecz; backup i test odtworzenia.
2. Uruchomić telemetrię i „shadow ingest” na małej, kontrolowanej próbce danych — bez zmiany zachowania graczy.
3. Przetestować admin registry oraz health na nieaktywnych kandydackich providerach. Nie uruchamiać niezweryfikowanych endpointów do gameplay.
4. Włączyć odczyt repozytorium dla zweryfikowanych coverage cells i ograniczonego ruchu; porównywać wyniki oraz latency z baseline.
5. Dopiero po walidacji włączyć szerszy fetch, zaczynając od małego rozmiaru komórek i konserwatywnego budżetu API.
6. Zwiększać zasięg etapami po pomiarach, bez masowego warmupu całej mapy; obserwować opóźnienia i wolne miejsce na dysku.
7. Rollback: wyłączyć odczyt i szerokie pobrania 160, pozostawiając dokładny mechanizm Sprintu 158, komunikaty 159 i dotychczasowy kontrakt skanowania. Nie usuwać tabel/bazy przy rollbacku.

**Ważne:** obecne publiczne endpointy mogą nadal nie działać. Rollback do 158 przy niedostępnym API **nie przywraca automatycznie skanowania w nieznanych rejonach**. Pierwsze zapełnienie repozytorium wymaga działającego, zaakceptowanego źródła danych.

---

## 15. Definicja ukończenia / PASS Sprintu 160

Sprint uznajemy za ukończony tylko gdy **łącznie**:

- [ ] Normalny skan, GhostLab, markery i gameplay mają zachowany kontrakt; regresje 158 i 159 przechodzą.
- [ ] Repozytorium zachowuje **wszystkie** zwalidowane elementy z poszerzonego zapytania, a nie tylko 60 wyników gracza.
- [ ] Pokrycie kompletne/puste/częściowe jest jednoznaczne i nie fałszuje wyników.
- [ ] Lokalny wynik `node/way/relation` ma potwierdzoną zgodność geometrii i filtrowania z Overpass dla tego samego snapshotu; w razie niezgodności bezpieczny fallback.
- [ ] Kilka skanów na tym samym pokrytym terenie nie wywołuje nowego API i ma mierzalnie niższy latency.
- [ ] Baza jest trwała, współdzielona między 4 workerami, monitorowana, backupowana i odtwarzalna.
- [ ] W adminie są edytowalne zatwierdzone endpointy + health i kontrola dostępu; zmiana URL nie wymaga deploya.
- [ ] Każdy aktywny provider ma osobne, audytowalne stany **techniczny i polityki użycia**, źródło warunków, datę sprawdzenia, zakres dozwolonego ruchu i decyzję operatora CHAOS; `POLICY_PENDING` nie wchodzi automatycznie do gameplay.
- [ ] VK Maps nie jest przedstawiany jako „certyfikowany” na podstawie pojedynczego HTTP 200 lub wpisu na OSM Wiki; niejasność dotycząca § 3.9 została udokumentowana i rozstrzygnięta przed produkcyjnym włączeniem odpowiedniego ruchu.
- [ ] Monitoring nie spamuje providerów, respektuje circuit breaker i nie myli `/status` z `interpreter`.
- [ ] Zablokowane źródła nie blokują skanowania z kompletnej lokalnej bazy; przy braku pokrycia działa MASA 159.
- [ ] Testy SSRF, autoryzacji, CSRF, rollbacku i budżetu API przechodzą.
- [ ] Istnieje runbook (backup, dodaj/zmień provider, incident, restore) oraz macierz dowodów z logów i testów produkcyjnych.

**Nie ogłaszać pełnego PASS po samym lokalnym test suite:** tak jak w 158, wymagane osobne potwierdzenie deploya, odczytu lokalnego, zachowania przy awarii i testów multiworker w środowisku produkcyjnym.

---

## 16. Otwarte decyzje do rozstrzygnięcia przez Codexa po audycie

1. Czy wykorzystać ten sam plik SQLite co Sprint 158 czy osobną bazę OSM z walidowaną synchronizacją transakcji?
2. Jaki profil geometrii (`out geom`, osobne zależności, strategia relacji) daje poprawność przy rozsądnej wielkości odpowiedzi i polityce dostawcy?
3. Jaki rozmiar komórki i halo daje najlepszą liczbę hitów dla map miejskich i mniej zabudowanych?
4. Jaki okres świeżości OSM jest akceptowalny dla normalnego skanu, a jaki dopuszczamy w trybie degraded? Nie mylić go z 5-minutowym exact-cache 158.
5. Jak admin auth, istniejące locale PL/EN, logi/glitch i API admina są już zorganizowane, żeby wykorzystać istniejące wzorce zamiast tworzyć równoległe moduły?
6. Jak konkretnie sprawdzić zgodność i politykę nowych providerów oraz jak migrować istniejącą statyczną listę bez automatycznego ich zatwierdzania? Dla VK Maps **wyjaśnić pkt 3.9 regulaminu VK Maps względem publicznego Overpass**, osobno uzgodnić ruch automatyczny, wider fetch, retencję danych i politykę limitów; dokumentować brak zgody/odpowiedzi.
7. Czy potrzebujemy ograniczonego preloadu popularnych obszarów, czy ruch naturalny wystarczy do tworzenia sensownej bazy — decyzja na danych z monitoringu, nie intuicyjnie.

---

## 17. Polecenie startowe dla Codexa

> Implementujemy **Sprint 160 — POI World Repository + Overpass Provider Control** jako kontynuację działających Sprintów 158 i 159. Najpierw zrób audyt istniejącego kodu `poiFetchClass.py`, `poi_infrastructure/`, `run.py`, GhostLab, MASA UX i panelu administracyjnego. Nie zmieniaj gameplay, kontraktów markerów, ekonomii, zasięgu, atrybucji OSM ani bezpieczeństwa.
>
> Docelowo przechowujemy wszystkie zwalidowane obiekty OSM z kontrolowanego szerszego pobrania wraz z **udowodnionym pokryciem** i serwujemy kolejne skany lokalnie. Nie wolno uznawać sąsiednich zapytań za równoważne na podstawie samych centrów `way/relation` ani zwracać częściowych wyników jako kompletnych. Gdy brak zweryfikowanego lokalnego pokrycia, użyj istniejącego exact-query 158 i ograniczonego upstream; w awarii zachowaj semantykę MASA 159.
>
> W panelu admina dodaj bezpieczny, audytowany rejestr zaufanych endpointów Overpass (zmiana URL i kolejności bez deploya) oraz zdrowie oparte na prawdziwych wywołaniach i rzadkich, skoordynowanych testach interpreter. Zabezpiecz konfigurację przed SSRF, ograniczając egress i uprawnienia. **Rozdziel techniczną dostępność od weryfikacji warunków korzystania i dozwolonego zakresu ruchu. VK Maps ma obecnie `POLICY_PENDING`; HTTP 200, wpis OSM Wiki i niejasny pkt 3.9 regulaminu nie uprawniają do automatycznego oznaczenia go jako zatwierdzonego. Zaimplementuj dowody (URL, data, odpowiedź operatora, ODbL, zakres) oraz fail-closed approval gate.**
>
> Realizuj etapami 160.0–160.5 z osobnymi bramkami, flagami startowo OFF, testami deterministycznymi i planem rollbacku. **Nie deklaruj PASS bez testów multiworker i produkcyjnych dowodów.**

---

## 18. Sens strategiczny

Dziś CHAOS **pyta zewnętrzny serwer, co znajduje się na mapie**. Po Sprincie 160 coraz częściej będzie pytał **własne repozytorium tego, co świat CHAOS już poznał**. Publiczne API będzie służyło przede wszystkim do rozszerzania i aktualizowania zasobu, nie do ciągłego odtwarzania tych samych danych. To uniezależnienie infrastruktury, nie zmiana reguł rozgrywki.

**Stan dokumentu:** koncept i kryteria — nie jest raportem z implementacji ani potwierdzeniem aktualnych uprawnień/licencji dostawców.
