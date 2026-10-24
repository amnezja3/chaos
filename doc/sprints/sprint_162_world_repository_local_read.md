# Sprint 162 — World Discovery: trwała pamięć świata i odczyt lokalny

Data: 20.10.2026. Aktualizacja: 24.10.2026. Status: **W REALIZACJI — magazyn i ograniczony pilot regionalny roads odebrane na VPS**.
Rozpoczęte 162.0–162.3: jawna migracja istniejących snapshot/member do v2,
kanoniczne obserwacje, ograniczony odczyt przecięć i planer jednego snapshotu.
Dowody exact query i certyfikowanej selekcji bbox zapisywane atomowo; certyfikaty
obszarowe sprawdzone na fixtures oraz w izolowanym pilocie jednego regionu roads
na VPS (75 dróg, lokalne wycinki 33/54, osobny proces, zero HTTP przy odczycie).
To empiryczny kontrakt jednego snapshotu, nie kwalifikacja wszystkich regionów.
MapLark radius nadal exact-only.
Opcjonalna integracja skanera za flagami OFF została sprawdzona lokalnie;
produkcja nadal bez ingest/read. Dowody: [162](../audits/sprint_162_evidence.md).
Wejście: [161](sprint_161_world_contract_and_adapters.md), istniejący kod 158–160,
[koncepcja](../prototypes/poi/CHAOS_WORLD_DISCOVERY_ENGINE_KONCEPCJA_BEZ_NUMERU.md).
Wyjście: [163](sprint_163_world_discovery_operations_rollout.md).
Etapy koncepcji C i D. Produkcyjny rollout 160 pozostaje wstrzymany.

## Cel i granica

Pełne dane pozyskane raz mają obsługiwać identyczny i sąsiedni skan bez HTTP,
jeśli istnieje dowód całego pokrycia, kategorii, geometrii i świeżości. Bez
planetarnego importu, nowych zasad rozgrywki i automatycznej ekspansji w tle.
161 musi zamrozić kontrakt przed migracją; mocki źródeł pozwalają pracować offline.
Nie jest wymagany wcześniejszy pełny PASS 160, ale konkretne przejęte bramki
geometrii, storage i integracji muszą uzyskać własne dowody przed produkcyjnym ON.

## 162.0 — migracja projektu 160, limity i benchmark bazowy

Potwierdzić jedną bazę POI i istniejące `world_schema`, `world_snapshot`,
`world_member`, `world_coverage`, `cache`, `leases` oraz registry/audit/health.
Nie tworzyć drugiej tabeli o tej samej roli tylko dlatego, że nazwa koncepcji
jest inna. Rozszerzenia zaplanować z migracją wersji, dry-run, SQLite backup API,
integrity/FK i testem idempotencji. Żadnych zmian w game.sqlite3.

Zmierz na fixtures miejskich/wiejskich/gęstych: bytes odpowiedzi, normalizacji,
indeksów i coverage, RAM peak, WAL, długość transakcji, czas odczytu i czyszczenia.
Obecne world 128 MiB/5000 snapshotów i limity repo/TTL są stanem kodu,
nie przyjętym budżetem nowego świata. Nie podnosić ich automatycznie.

Bramka: plan migracji zachowuje raw snapshoty, fencing, ordinal i możliwość
powrotu do exact-cache. Kopia DB plus WAL musi mieścić się w budżecie migracji.

## 162.1 — kanoniczny magazyn, indeks i pochodzenie

- Rozszerzyć storage 160 o kanoniczny obiekt i referencje źródłowe; snapshoty
  pozostają niezmienne, membership wiąże dowód z właściwym zestawem obiektów.
- Krótka transakcja publikuje obiekty + membership + coverage + provenance
  wyłącznie przy aktualnym lease i revision. HTTP i normalizacja poza transakcją.
- Częściowy batch może być użyteczny do uzupełnienia, ale nigdy nie zastępuje
  istniejącego kompletnego snapshotu ani nie generuje local success.
- Zachować konflikty obserwacji, jawny wybór wersji, usunięcia wyłącznie z pełnego
  porównywalnego dowodu. Fetched_at nie zastępuje source_dataset_at.
- Rozważyć R*Tree/bbox na istniejącym SQLite po sprawdzeniu builda i pomiarach;
  fallback do indeksu bounds ma być jawny. Brak pełnego ładowania miasta do RAM.
- Polityka czyszczenia nie usuwa jedynego dowodu pełności pozostawiając COMPLETE.
  Oddzielić retencję obiektu, źródłowego payloadu, audytu i ważność coverage.

Bramka: crash przed commit nie publikuje połowy świata; powtórzenie zadania
nie duplikuje rekordów; starsza odpowiedź nie wypiera nowszej bez rozstrzygnięcia.

## 162.2 — coverage i dowód selekcji przestrzennej

Coverage identyfikuje obszar/halo, wymagane warstwy, wersje profili i adaptera,
geometrię, snapshot, kompletność stron, świeżość, licencję i dopuszczenie użycia.
Oddzielić dowody danych od stanu zadania QUEUED/FETCHING/FAILED.

Stany danych: UNKNOWN, PARTIAL, COMPLETE_FRESH, COMPLETE_STALE, EXPIRED.
Pusty kompletny wynik jest poprawny; brak obiektów bez dowodu pozostaje UNKNOWN.
EXACT_QUERY_COMPATIBLE nie awansuje do AREA_REUSABLE przez sam zapis w komórce.

1. Rozszerzyć niezależne referencje 160 na granice, duże ways, direct i nested
   relations, dziury/multipoligony, brakujące members, antymeridian, bieguny.
2. Nie utożsamiać around z ogólnym polygon containment ani wyborem centroidu.
   Nieobsługiwane/niejednoznaczne przypadki pozostają bez certyfikacji obszarowej.
3. Indeks siatki/H3 wskazuje kandydatów, nie dowodzi pokrycia koła.
4. Union dozwolony wyłącznie po dowodzie braku luk i zgodności profili,
   snapshotów, jakości, czasu oraz praw źródłowych każdej warstwy. W pierwszym
   wariancie wolno ograniczyć odczyt do jednego dowiedzionego snapshotu; wtedy
   union oznaczyć UNSUPPORTED i pozostawić jawny fallback, nie pozorny PASS union.
5. Zmiana mapping/filter/geometry version unieważnia niezgodne dowody.
   Wygaśnięcie decyzji źródła nie oznacza automatycznie ani skasowania, ani prawa
   do dalszego użycia danych — obowiązuje utrwalony zakres i retencja.

Bramka: zero fałszywych local hits we wszystkich certyfikowanych profilach;
macierz obsługiwane/nieobsługiwane jest częścią wyniku sprintu, nie ukrytym wyjątkiem.

### 162.2-E — puste pokrycie i odczyt mapy admina (23.10.2026)

Kompletny pusty wynik zapisujemy jako mały dowód: obszar/semantyka selekcji,
profil/version, źródło/snapshot, kompletność stron, liczba obiektów 0,
daty, ważność i prawa użycia. Bez fikcyjnych obiektów i zbędnych kopii payloadu.
Geometria obszaru dowodu pozostaje potrzebna; brak POI nie pozwala usuwać
użytecznej geometrii innych warstw. Pusty wynik nie wyzwala ekspansji sąsiadów.

Zapewnić ograniczony odczyt coverage dla bbox/zoom/warstw i agregaty dla 163,
bez pełnych obiektów w przeglądarce i ładowania całego świata do RAM. Siatka
prezentacyjna nie powiększa dowiedzionego pokrycia; mieszany agregat nie udaje
COMPLETE. Filtr pustych wyników nie zmienia danych. Brak wpisu = unknown;
nie tworzyć wierszy dla każdego nieodkrytego sektora planety.

R14: powtórzony pusty skan na ważnym coverage → 0 HTTP, brak dowodu nie daje
sukcesu, expiry i izolacja warstw działają. R15: bbox/agregacja/filtr pustych
nie fałszują pełności, odczyt mieści się w ustalonym budżecie. Pełny odbiór
rozszerzonego 162 wymaga R01–R15.

### 162.2-G — zapis geometrii i odbiór

Zakres: `roads`, `waterways`, `inland_water`, `coastline`, `land_water` niezależnie
od `poi`. Przejąć kontrakt i G01–G04 z 161; wspólne repozytorium i provenance,
bez drugiej konkurencyjnej bazy i bez wymuszania formatu markera.

1. Zapisywać i odczytywać `Point`, `LineString`, `Polygon`, `MultiPolygon`
   bez utraty części, otworów, kierunku coastline i tożsamości źródłowej.
   Oddzielić pełną geometrię od clipped fragmentu i wersji uproszczonej;
   utrwalić relację fragment–rodzic. Nie deduplikować dróg po centroidzie.
2. Indeks bbox wybiera kandydatów; dokładny predykat przecięcia obszaru
   rozstrzyga wynik. Osobno zdefiniować intersects/contains i clipping;
   nie zastępować nimi historycznej semantyki around dla skanera POI.
   Punkty w otworach nie należą do powierzchni wody. Długie linie z końcami
   poza regionem nadal mogą go przecinać. Dla antymeridianu stosować jawny
   podział indeksowania albo odmowę certyfikacji, nigdy błędne bounds.
3. Coverage, freshness, source revision i prawa użycia osobno per profil.
   Zapis jeziora nie dowodzi pokrycia oceanów ani POI. Atomowo publikować
   dowód warstwy; aktualizacja dróg nie unieważnia poprawnego snapshotu POI.
   Cache/read key zawiera warstwę i wersję selekcji. Osobny interfejs odczytu
   geografii poniżej gameplayu; brak limitu 60 markerów, ale jawne limity
   vertices/bytes/obiektów i paginacja bez pozornego kompletnego wyniku.
4. `land_water` przechowuje wersję datasetu/algorytmu i zależności od fragmentów
   coastline. Zmiana zależności unieważnia właściwy derived coverage.
   Gotowy regionalny produkt i wynik kontrolowanej rekonstrukcji mają różne
   provenance. Bez dowodu topologii lub danych spoza wycinka odczyt zwraca
   UNKNOWN/PARTIAL; nie domyślną wodę/ląd. Nie rekonstruować oceanu na żądanie
   w procesie Gunicorn. Plan zadań i limity kontekstu należą do 163.
5. Benchmarkować geometrię, nie tylko liczbę POI: wierzchołki, pierścienie,
   fragmenty, bytes, WAL, RAM, indeks i czas dokładnych predykatów. Limity
   per warstwa i globalne; brak ukrytego planetarnego importu. Sprzątanie
   usuwa/unieważnia także zależne dowody, nie pozostawia fałszywego COMPLETE.

Odbiór R10–R13: round-trip czterech typów, otworów i multipart po restarcie
i restore; przestrzenna selekcja na granicach/antymeridianie i długich liniach;
izolacja coverage POI–drogi–wody oraz invalidation derived coastline;
kompletny region każdej certyfikowanej warstwy przy dostawcach OFF → 0 HTTP.
Fixture obejmują wyspę w jeziorze, archipelag, ujście, otwarty brzeg i przecięcie
granicy sektora. Brak warstwy musi pozostać jawny. Dowody offline nie oznaczają
produkcyjnego pozyskania danych. Pełny odbiór 162 obejmuje R01–R15.

## 162.3 — World Read Planner i kontrolowany read-through

Zachować `fetcher.get_all` i pipeline run.py. Planer działa poniżej kategoryzacji:
exact cache / pełny world → dopuszczalne stale → kontrolowane pozyskanie na miss
według istniejącej polityki i budżetu. Kolejność stale vs sieć musi pozostać
zgodna z przyjętą polityką 158; nie zmieniać jej przypadkiem podczas refaktoru.

Router sprawdza jednocześnie capability, revision, technikę, scope, stan circuit,
koszt i budżet. Pusta lista dopuszczonych źródeł to błąd konfiguracji, nie powód
do ukrytego powrotu do hardcode. Źródło z brakującą warstwą nie zastępuje pełnego skanu.

Jedna operacja biznesowa może wymagać wielu stron API, ale każda strona,
estimate, zmiana źródła i fallback zużywa ten sam jawny budżet requestów,
kredytów, bytes, elementów i czasu. Brak budżetu = PARTIAL/defer/fallback,
nie reset limitu na każdą stronę. Żadnych równoległych niekontrolowanych fetchy.
Po anulowaniu GhostLab nie rozpoczynać kolejnych stron ani nie wydawać wyniku;
ukończony legalny snapshot może służyć innym graczom.

Fetch envelope dobierać z pomiarów; 600–900 m z koncepcji i 1500 m z 160 to
warianty do porównania, nie nowe domyślne promienie gameplayu. Miss przy krawędzi
pozyskuje brak tylko gdy semantyka scalenia jest udowodniona; inaczej kontrolowany
pełny fetch/exact fallback. Ścieżka live mieści się w dotychczasowym deadline
≤110 s i pozostawia budżet na parser, zapis i gameplay przy Gunicorn 120 s.

Bramka: 4 procesy współdzielą fill, błąd opcjonalnego shadow zapisu nie niszczy
poprawnego bieżącego wyniku, nieznany obszar nie zwraca pustego pozornego sukcesu.

## 162.4 — eksport, GhostLab i MASA

Wynik z repo przechodzi przez tę samą kategoryzację/ikony/markery i prywatne
odkrycia. Zachować limit 60, kolejność i dedup po współrzędnych; repo może mieć
więcej obiektów niż markerów. RNG pod kontrolą fixture, dwa izolowane konta.

Mapowanie: local fresh → normalny wynik; dopuszczalne stale → istniejąca
degradacja; fetching → istniejący skaner; partial → brak pełnego sukcesu.
BLOCKED wyłącznie przy dowodzie niedostępności dopuszczonych źródeł i braku
używalnych danych. Brak approval, zły adapter, baza, sesja i konfiguracja są
błędem technicznym. To rozstrzyga nieprecyzyjne „brak dozwolonego źródła” z §14
koncepcji na rzecz niezmiennika MASA truthful i kontraktu 159.

Chaos Log, poziom glitcha i ciche wygaśnięcie pozostają bez zmian.

## 162.5 — macierz dowodów i przekazanie do 163

| ID | Test odbioru |
| --- | --- |
| R01 | Migracja, powtórzenie, backup/restore, spójność FK, zgodność starego exact-cache |
| R02 | Ingest atomowy, crash/lease loss, starszy snapshot, partial i usunięcia |
| R03 | Referencja nwr, way center poza kołem, relacje, luki union i zakres odmowy |
| R04 | Ten sam i sąsiedni kompletnie pokryty skan, restart, dostawcy OFF → 0 HTTP |
| R05 | Puste kompletne coverage, brak kategorii, obcięta strona, expiry w oczekiwaniu |
| R06 | 4 procesy/20 żądań, wspólny fill/budżet, cancellation i fallback bez amplifikacji |
| R07 | Dwa konta: koszty, snapshoty, kamery/NPC, znaczniki i GhostLab bez regresji |
| R08 | Disk full/busy/corruption, ograniczenia RAM/WAL i sprzątanie bez fałszywej pełności |
| R09 | Playwright MCP: mapa PL/EN desktop/mobile, local/stale/error i ciche wygaśnięcie MASA |

Dowody docelowo: `doc/audits/sprint_162_evidence.md`. API wyłącznie fixture/lokalne
referencje; żaden PASS offline nie staje się odbiorem VPS. Otwarte parametry
TTL, retencji i wielkości envelope rozstrzygnąć na podstawie pomiarów przed pilotem.

## Flagi i rollback

Ponownie użyć `CHAOS_POI_WORLD_INGEST_ENABLED`, `CHAOS_POI_WORLD_REPOSITORY_ENABLED`,
`CHAOS_POI_WIDE_FETCH_ENABLED` i `CHAOS_POI_PROVIDER_REGISTRY_ENABLED`. Nie tworzyć
duplikatów `CHAOS_WORLD_*` bez brakującej zdolności. Schemat może istnieć przy OFF.
Wersję profilu/adaptera wybiera konfiguracja z walidacją, nie przypadkowa kolejność importów.

Rollback funkcji nie kasuje wiedzy. Wyłączyć nowe pozyskiwanie i odłączyć warstwę,
zachowując starszy czytelny kontrakt; migracja musi mieć plan zgodności starego kodu
lub przywrócenia kopii w nowej ścieżce. Nie resetować aktywnych lease w ciemno.
Powrót do 158 nie gwarantuje dostępności DE/VK. Aktywacja i rollout pamięci świata
dopiero w 163; nie dotyczy wcześniejszego pilota adaptera POI w 161.
Nowe profile geograficzne mają niezależną konfigurację ingest/read domyślnie OFF;
nie włączać ich automatycznie flagą dotychczasowego repozytorium POI.
