# CHAOS — WORLD DISCOVERY ENGINE
## Koncepcja organicznego repozytorium świata i wielodostawczego pozyskiwania danych geograficznych

**Rodzaj dokumentu:** koncepcja produktowo-architektoniczna / materiał do przyszłej specyfikacji wykonawczej<br>
**Identyfikator roboczy:** `CHAOS.WORLD.DISCOVERY.CONCEPT`<br>
**Plan wykonawczy:** **Sprinty 161–163; historyczna nazwa pliku zachowana**<br>
**Data opracowania:** 20.10.2026<br>
**Stan:** **DRAFT / DO DYSKUSJI — BEZ ZGODY NA IMPLEMENTACJĘ ANI ROLLOUT**<br>
**Kontekst:** CHAOS, mapa Leaflet, skanowanie POI, GhostLab, MASA, infrastruktura 158, UX 159, częściowo wdrożony i wstrzymany sprint 160.

> **Idea główna:** CHAOS ma dostęp do całego świata, ale nie musi mieć lokalnej kopii całego świata. Gracze eksplorują dowolne miejsca, a system zapamiętuje wyłącznie te obszary i informacje, które rzeczywiście są potrzebne grze. Każda kontrolowana odpowiedź dostawcy wzbogaca wspólne repozytorium; następne skany korzystają z niego bez kolejnego HTTP — o ile mamy dowód kompletnego pokrycia wymaganego obszaru i kategorii.

---

## 0. Krótkie streszczenie decyzji

### Rozszerzenie z 23.10.2026 — geografia niezależna od POI

Silnik obejmuje rosnącą bazę rzeczywistej geografii, nie tylko markerów.
Poniższe ustalenia rozszerzają wcześniejszy zakres POI; nie oznaczają wdrożenia.
Plan wykonawczy: [161](../../sprints/sprint_161_world_contract_and_adapters.md),
[162](../../sprints/sprint_162_world_repository_local_read.md),
[163](../../sprints/sprint_163_world_discovery_operations_rollout.md).

| Profil warstwy | Zakres źródłowy | Reprezentacja docelowa |
| --- | --- | --- |
| `poi` | Dotychczasowe kategorie skanera | Punkt prezentacji oddzielony od pełnej geometrii obiektu |
| `roads` | `highway=*`, ulice i drogi | Linie; powierzchnie tylko gdy potwierdza je semantyka źródła |
| `waterways` | `waterway=*`, rzeki i kanały | Linie i potwierdzone powierzchnie, bez sztucznego nadawania szerokości |
| `inland_water` | `natural=water`, jeziora, stawy, zbiorniki | Polygon/MultiPolygon z otworami i podtypem ze źródła |
| `coastline` | `natural=coastline` | Kierunkowe fragmenty linii wraz z powiązaniami i kompletnością |
| `land_water` | Obszary ląd–woda, morza i oceany | Osobny wersjonowany produkt powierzchniowy ze źródła lub kontrolowanego przetwarzania coastline |

Profile mają niezależne capability, coverage, świeżość, prawa przechowywania,
budżety i stany dostępności. Jeden obiekt może należeć do kilku profili bez
duplikowania tożsamości. Brak dróg lub morza nie blokuje kompletnego skanu POI;
brak POI nie dowodzi pustej geografii. Limit 60 i deduplikacja markerów dotyczą
wyłącznie eksportu gameplayu. Nie stosować ich do geometrii świata.

Wspólny kontrakt obsługuje `Point`, `LineString`, `Polygon`, `MultiPolygon`
w WGS84, z kolejnością współrzędnych longitude/latitude. Geometria autorytatywna,
punkt markera i uproszczona geometria prezentacyjna są osobnymi polami/wersjami.
Zachować ID, tagi profilu, bounds, pochodzenie, wersję danych i przetwarzania,
kompletność oraz informację o clippingu. Dla innych typów źródłowych adapter
deklaruje udowodniony podział na części z relacją do rodzica albo UNSUPPORTED;
nie wolno ich spłaszczać do jednego punktu czy sklejać rozłącznych linii.

**Morze nie jest domkniętym lokalnym fragmentem coastline.** Osobny proces
rozstrzyga orientację, połączenia, wyspy, otwory, ujścia, granice wycinka i
antymeridian. Otwarte lub brakujące odcinki dają PARTIAL/UNKNOWN, nie domyślną
wodę ani ląd. Nie zamykać wybrzeża prostą przez bbox i nie traktować braku
`natural=water` jako braku oceanu. Dopuszczamy gotowy, legalnie przechowywalny
produkt ląd–woda w wycinkach; dostępność takiego źródła wymaga sprawdzenia.
Rekonstrukcja z linii wymaga dowodu zamknięcia topologii i kontekstu poza
regionem. Gdy kontekst przekracza budżet, odkładamy zadanie zamiast pobierać
cały kontynent. Derived geometry zachowuje lineage źródeł i algorytmu.

Podział prac: **161** kontrakt, walidacja i macierz zdolności osobno dla warstw;
**162** trwały zapis, indeks i odczyt przestrzenny; **163** stopniowe uzupełnianie
odwiedzanych regionów, niezależne włączanie warstw i kontrola kosztów.
Przywrócenie skanera POI pozostaje pierwszym celem 161; pozyskanie wszystkich
warstw nie jest warunkiem jego pilota. Pełny kontrakt geograficzny jest jednak
obowiązkowym wynikiem 161 przed przekazaniem storage do 162.

Zdarzenia zapotrzebowania nie wymagają znalezienia POI: odwiedzony region może
być drogą, pustkowiem albo morzem. Zapisujemy zagregowany popyt region/warstwa,
bez historii ruchu konkretnych graczy. Rozwój ma granice obszaru, czasu, liczby
zadań, geometrii i kosztu; brak rekurencyjnego pobierania całej planety.
To warstwa danych, nie zobowiązanie do zastąpienia kafelków Leaflet, routingu
drogowego, symulacji hydrologii ani zmiany mechanik PvP w tych sprintach.

Nie stawiamy od razu pełnego Overpassa ani nie importujemy planetarnego PBF. Nie budujemy też klasycznego scrapera stron HTML. Proponujemy **silnik pozyskiwania danych z udokumentowanych API** z adapterami MapLark, Geoapify, a w przyszłości dowolnego zatwierdzonego źródła kompatybilnego semantycznie z potrzebami CHAOS.

Jedna transakcja biznesowa „skanuj” rozdziela się na dwa procesy:

1. **Odpowiedź na skan gracza:** najpierw lokalny odczyt; gdy brakuje dowodu pokrycia, pojedyncze kontrolowane pozyskanie niezbędnych danych z dopuszczonego źródła, walidacja, zapis i wykonanie **dotychczasowego** gameplayu.
2. **Odkrywanie świata w tle:** zdarzenie odkrycia nowego obszaru daje ograniczone, deduplikowane zadanie uzupełniania sąsiednich sektorów, jeśli pozwalają na to polityka dostawcy, budżet, pojemność VPS i obciążenie gry.

**Repozytorium przechowuje kanoniczne dane świata i dowody kompletności, nie prywatne wyniki skanów, nie proceduralne NPC i nie historię położeń poszczególnych graczy.**

Początkowa grupa do około 100 aktywnych testerów nie jest powodem do ręcznego wyboru państw. Jest powodem, aby przyjąć model **globalny, przyrostowy i sterowany realnym zapotrzebowaniem**. Liczba 100 to kontekst planu testów, nie techniczny próg wyłączający limity.

---

## 1. Punkt wyjścia: stan faktyczny i granice zależności

### Uzupełnienie zakresu 23.10.2026 — kredyty i mapa poznanego świata

Rozszerzenie pozostaje w 161–163. 161 przygotowuje koszt pojedynczego skanu
i ograniczenia adaptera, 162 zapis coverage i pustych wyników, 163 pełny panel
budżetów, interaktywną mapę oraz statystyki. Nie wprowadzamy nowego sprintu.

Informacje operatora z kont, **do potwierdzenia dla planu i endpointu**:
MapLark — 30 000 kredytów miesięcznie, rate limit nieustalony;
Geoapify — 3 000 dziennie, 5 req/s, wskazane ograniczenie 10 km do wyjaśnienia.
Nie zakładać kredyt = request ani 10 km = promień skanera. To nie są jeszcze
zatwierdzone ustawienia produkcji ani zgoda na płatne nadwyżki.

Dwa niezależne liczniki: raportowane saldo/zużycie konta dostawcy oraz wewnętrzny
dzienny/miesięczny budżet CHAOS. Liczby mają źródło i czas aktualizacji; lokalne
szacunki nie udają rzeczywistego salda. Bez API metryk dopuszczamy ręczny odczyt
panelu z datą i statusem aktualności. Uwzględnić zużycie konta poza CHAOS.
Ostrzeżenia przy 70%, 85%, 95%; rezerwacja kosztu przed HTTP i wstrzymanie nowych
pobrań, gdy limit nie mieści operacji. Strony, retry, probe i tło dzielą budżet;
odczyt lokalny pozostaje dostępny. Szczegóły i dowody odbioru w 163.2-K.

Mapa admina pokazuje półprzezroczyste sektory/obrysy poznanych obszarów,
nie tysiące markerów. Warstwy: POI / Drogi / Rzeki i kanały / Jeziora i zbiorniki /
Wybrzeża / Ląd–morze. Zielony = kompletne świeże dane dopuszczone do lokalnego
odczytu; żółty = częściowe; pomarańczowy = wymagają aktualizacji; szary = nieznane.
Tekst/wzory uzupełniają kolor. Widok zbiorczy nie oznacza pełności wszystkich
warstw przez samą obecność jednej. Szczegóły i kryteria w 163.2-M.

Puste kompletne wyniki zachowujemy jako małe dowody pokrycia per profil, obszar,
źródło i ważność. Nie powodują automatycznej ekspansji pustkowia. Można domyślnie
ukryć je na mapie, z widocznym filtrem i opcją pokazania; ukryte nie znaczy unknown.
Brak POI nie uzasadnia usunięcia użytecznych dróg czy wód. Statystyki pokazują
pokrycie, obiekty, zagregowany popyt, przyrost, rozmiar oraz udział skanów z trwałego
repo bez HTTP. Przykładowe liczby załącznika nie są pomiarami ani SLO CHAOS.
Mapa pozostaje administracyjna, bez punktów i tras graczy. Publiczna wizualizacja
to osobny przyszły backlog.

### 1.1. Stan produkcji według raportu z 20.10.2026

Ten dokument **nie może zakładać ukończonego sprintu 160**. Na podstawie najnowszego raportu z projektu:

| Obszar | Potwierdzony stan / ograniczenie |
|---|---|
| Infrastruktura 158 | Wdrożona i włączona; globalna koordynacja pobrań, cache, limity, circuit breaker. |
| UX MASA 159 | Włączony; fabularny interfejs awarii skanowania. |
| 160.0 | Audyt historyczny i referencje geometrii wykonane; brak stabilnego produkcyjnego baseline’u. |
| 160.1 | Repozytorium: snapshoty, membership, zabezpieczenia i schemat na VPS; **ingest produkcyjny OFF**. |
| 160.2 | Testy lokalnego odczytu w części zaliczone; **world read i wide fetch OFF**, szersza geometria nadal do odbioru. |
| 160.3 | Panel rejestru dostawców zapisuje kandydatów i decyzje; **registry nie steruje ruchem gameplayu**. |
| 160.4 | Obserwacje, ręczne probe i diagnostyka transportu dostępne; agregaty/coverage dashboard i odbiór monitoringu otwarte. |
| 160.5 | Pełna akceptacja, pilotaż na produkcji, rollback konfiguracji i część regresji pozostają otwarte; **brak pełnego PASS 160**. |

Zestaw 81 testów POI przeszedł w wskazanym zakresie, późniejsze poprawki miały osobne testy celowane; **nie jest to dowód kompletnej zgodności nowego silnika**. Poprawiono błąd odczytu całego HTTP 200. Transport CHAOS pobrał z VK 679 poprawnych obiektów, ale sukcesy nie były powtarzalne. DE zgłaszał przeciążenie, a VK sukcesy przeplatał błędami.

**Ostatni potwierdzony ruch produkcyjny:** gameplay nadal używa statycznej listy DE/LZ4; registry, ingest, world read, wide fetch i aktywny monitor pozostają wyłączone. Wobec ustalonego wstrzymania **nie wznawiamy prób API, pushy, deploya ani flag** przez sam fakt napisania tej koncepcji.

### 1.2. Fakty o obecnym kontrakcie skanera

- Punkt wejścia: istniejąca ścieżka `action == "scan"` i `fetcher.get_all(lat, lon, result_limit=60, scan_options=...)` w `run.py`.
- Historyczny promień `POIFetcher`: 300 m; właściwe promienie mogą zależeć od mechaniki i wymagają odczytu bieżącej wersji kodu przed implementacją.
- OSM Query: `node`, `way`, `relation` (`nwr`), tagi `shop`, `amenity`, `office`, `healthcare`, `atm=yes`, `man_made=surveillance`.
- `result_limit=60` to **lokalny limit gameplayu**, nie limit liczby obiektów pobranych od dostawcy.
- Gameplay po pobraniu korzysta z tagów, kategorii, ikon, oznaczonych celów, kamer, NPC, losowania i mechanik GhostLab.
- Dla `way/relation` środek obiektu nie jest tym samym co geometria potrzebna do weryfikacji, czy obiekt przecina promień skanu.

### 1.3. Czego nie robimy tym konceptem

- Podział 161–163 jest planem wykonawczym; nie oznacza zakończenia sprintu 160.
- Nie zastępujemy teraz produkcyjnego skanera ani nie wymuszamy zmiany gameplayu.
- Nie wybieramy automatycznie MapLark lub Geoapify jako zatwierdzonego dostawcy; weryfikacja prawna, techniczna i kosztowa to **osobne bramki**.
- Nie uruchamiamy ciągłego pobierania całych miast, krajów i kontynentów.
- Nie budujemy alternatywnego silnika mapy wizualnej (kafelki Leaflet). To odrębny problem od obiektów do skanowania.
- Nie obiecujemy braku zależności od zewnętrznego API **w nieodkrytym** regionie. Taki obszar nadal wymaga zatwierdzonego źródła.

---

## 2. Cel produktu i zasady nienaruszalne

**Cel:** każdy poprawny skan nowego terenu może zwiększać trwałą wiedzę geograficzną CHAOS; liczba zewnętrznych zapytań przypadających na skuteczny skan powinna z czasem maleć, przy zachowaniu prawidłowych markerów i zasad rozgrywki.

### Wymagania „MUST”

1. **Cały świat dostępny logicznie:** mechanizm nie zakłada ograniczonego kraju ani listy wcześniej przygotowanych miast.
2. **Local-first:** przed siecią sprawdzamy kompletność danych lokalnych dla dokładnego zakresu i profilu skanowania.
3. **Source-neutral:** `run.py` i gameplay nie znają dostawcy; adaptacja następuje w warstwie danych.
4. **No false completeness:** brak wpisów nie jest dowodem braku obiektów. HTTP 200 nie oznacza kompletnego zbioru.
5. **Gameplay parity:** wynik skanowania ma podlegać tym samym regułom co dotychczasowy, z zachowaniem geometrii `nwr`, sortowania/limitów i GhostLab.
6. **No amplification:** jeden klik nie rozpoczyna kilku niekontrolowanych pobrań; proces tła nie konkuruje o priorytet z graczami.
7. **Persistent + restart-safe:** cztery procesy aplikacji odczytują to samo repo, a restart nie usuwa zatwierdzonej wiedzy o terenie.
8. **Opt-in + rollback:** kolejny etap pozostaje domyślnie OFF; osobne przełączniki normalnego skanu, zapisu i workerów tła.
9. **Traceable provenance:** każdy rekord ma pochodzenie i informację o prawach do jego dalszego przechowywania.
10. **Minimum resource footprint:** weryfikujemy rzeczywiste zużycie RAM, miejsca, I/O i kredytów; nie wczytujemy w RAM całych miast.
11. **No player-data leakage:** zewnętrzny dostawca widzi zapytanie geograficzne, nie konto/klan/inwentarz gracza; nie utrzymujemy publicznej historii jego lokalizacji.
12. **MASA truthful:** fabularne zakłócenia występują tylko przy potwierdzonej niedostępności warstwy geograficznej, a nie przy błędzie aplikacji lub niepełnym kontrakcie.

### Wymagania „SHOULD”

- Skan w sąsiednim miejscu, znajdującym się w obszarze udowodnionego pokrycia, działa bez HTTP.
- Silnik może pobrać obszar większy niż pojedynczy skan, ale tylko gdy jest to opłacalne oraz dozwolone.
- Panel administracyjny pokazuje pokrycie mapy, szybkość jego wzrostu, koszty dostawców i liczbę skanów offline.
- Z czasem silnik wykorzystuje zdarzenia z aktywności testerów do priorytetyzacji pobrań, bez automatycznego „odkrywania całych miast”.

---

## 3. Definicje, które muszą być jednoznaczne

| Termin | Znaczenie |
|---|---|
| **Skan gameplayu** | Działanie konkretnego gracza z autoryzacją, kosztem, wynikiem i regułami gry. |
| **Odczyt świata** | Geograficzny zbiór obiektów źródłowych dla punktu/promienia/kategorii; bez informacji o graczu. |
| **CHAOS World Object** | Ujednolicony, minimalny rekord geograficzny niezależny od formatu dostawcy. |
| **Fetch envelope** | Geograficzny obszar pobrania z API; może być większy od skanu gameplayu. |
| **Coverage proof** | Weryfikowalny dowód kompletności konkretnego fragmentu, profilu tagów i geometrii. |
| **Sector / cell** | Jednostka indeksowania, priorytetyzacji i wizualizacji, np. komórka H3 lub inna siatka. |
| **Single-flight** | Wspólna operacja, którą może dołączyć wiele podobnych skanów bez dublowania requestów. |
| **Discovery task** | Niskopriorytetowe zadanie uzupełnienia brakującego pokrycia w sąsiednich komórkach. |
| **Provider adapter** | Sterownik tłumaczący nasze potrzeby na API dostawcy i jego odpowiedź na kontrakt świata. |
| **Capability profile** | Zdolność dostawcy do kompletnego pobrania określonych tagów, tożsamości i geometrii. |
| **Exact-query cache** | Już istniejąca w 158 pamięć odpowiedzi dokładnego zapytania; niezależna od repozytorium świata. |

---

## 4. Architektura docelowa

```text
                                [ GRACZ / MAPA CHAOS ]
                                          |
                                   action=scan
                                          v
                            [ SCAN FACADE / AUTH / GHOSTLAB ]
                                          |
                                          v
                               [ WORLD READ PLANNER ]
                                      /         \
                           pełne pokrycie      brak pokrycia
                                 |                    |
                                 v                    v
                           [ LOCAL WORLD ]    [ 158: SINGLE-FLIGHT ]
                                 |                    |
                                 |           [ 160: PROVIDER REGISTRY ]
                                 |                    |
                                 |          [ AUTHORIZED ADAPTER ]
                                 |                    |
                                 |           [ VALIDATE + PROVENANCE ]
                                 |                    |
                                 |           [ ATOMIC INGEST + COVERAGE ]
                                 |                    |
                                 +<-------------------+
                                 |
                       [ OSM-COMPATIBLE SCAN RESULT ]
                                 |
                    [ NIEZMIENIONY PIPELINE GAMEPLAY ]
                     mark / icon / camera / NPC / GhostLab
                                 |
                           [ WYNIK GRACZA ]

             [ EVENT: NEW COVERAGE DEMAND ] (bez konta gracza)
                                 |
                                 v
                  [ DEDUPLICATED DISCOVERY QUEUE ]
                                 |
                          [ BACKGROUND WORKER ]
                                 |
                     [ TEN SAM GLOBALNY BUDŻET 158 ]
                                 |
                    [ SECTORS + APPROVED PROVIDERS ]
                                 |
                        [ WORLD REPOSITORY ]

          [ ADMIN PANEL ] — providers / licenses / budgets / queue /
                           coverage / telemetry / kill switch
```

**Opis diagramu:** ścieżka gracza ma najwyższy priorytet i zawsze kończy się w istniejącej mechanice skanera. Repozytorium może zwrócić zweryfikowany wynik lokalny, a przy braku danych korzysta z uzgodnionego transportu 158 oraz rejestru dostawców z 160. Tło korzysta z **tych samych ograniczeń** i nie jest alternatywnym sposobem omijania limiterów.

### 4.1. Warstwy odpowiedzialności

- **Game / Scan Facade:** walidacja sesji, dystansu, polityki gracza, GhostLab, kosztów i gameplayu. Żadnej wiedzy o API zewnętrznych.
- **World Read Planner:** ustala wymagany zakres, filtr, wersję semantyki i dowód pokrycia; dokonuje wyboru local/read-through/fallback.
- **World Repository:** obiekty kanoniczne, identyfikatory źródłowe, geometria, snapshoty, membership, coverage i indeks przestrzenny.
- **Provider Router:** wybiera dopuszczonego dostawcę według zdolności, stanu, kosztu, limitów i zakresu uprawnień.
- **Adapters:** MapLark / Geoapify / Overpass — każdy ma własny kontrakt walidacyjny i testy.
- **Discovery Queue + Worker:** lokalna kolejka zadań, pobrania w tle, dopuszczalny radius, idempotencja, cooldown.
- **Observability + Admin:** podgląd faktów i decyzje administratora; brak bezpośredniego obchodzenia bramek bezpieczeństwa.

### 4.2. Zależności od obecnych modułów

- **158:** single-flight, exact-query cache, rate limit, deadline, retry, circuit breaker, zbiorczy limit upstream.
- **159:** `READY`, `DEGRADED`, `BLOCKED`, `RECOVERING`, `RESTORED` tylko ze stanów prawdziwych; reszta `OTHER_ERROR`.
- **160:** repozytorium, snapshoty, provider registry, operator approval, monitoring, indeks/pokrycie i strategia rollbacku — **rozszerzamy, nie tworzymy drugiej konkurencyjnej bazy bez uzasadnienia**.
- **`poiFetchClass.py` / `run.py`:** zachowujemy podpis metody i wynik zgodny z dotychczasową ścieżką skanowania.

---

## 5. Model danych: CHAOS World Object Contract

### 5.1. Zasada normalizacji

**Źródło może mówić „amenity=bank”, „commercial.bank” albo zwracać własną nazwę kategorii. CHAOS ma otrzymywać spójny typ i atrybuty, ale musi wiedzieć, skąd dana informacja pochodzi i jakie znaczenie miała w źródle.**

W kontrakcie rozdzielamy:

- **Tożsamość obiektu:** stabilny klucz własny oraz zewnętrzne identyfikatory.
- **Minimalny zestaw gry:** nazwa, reprezentatywne współrzędne, kategoria, podtyp i ważne atrybuty.
- **Geometria:** tylko gdy wymagana do prawidłowego skanowania lub wybranego profilu świata; z informacją o jakości.
- **Kontekst lokalizacyjny:** miasto/region/kraj **opcjonalne** — wiele POI nie ma tych pól w samym OSM, więc nie wymyślamy ich na podstawie najbliższego napisu.
- **Pochodzenie:** źródło, OSM ID, licencja, snapshot, czas obserwacji, dostępność danych i wersja adaptera.

### 5.2. Przykładowy rekord kontraktowy (przykład schematyczny, nie stan produkcji)

```json
{
  "schema_version": "chaos.world_object.v1",
  "world_object_id": "osm:node:123456789",
  "identity": {
    "osm_type": "node",
    "osm_id": 123456789,
    "provider_refs": [
      { "provider": "maplark", "external_id": "node/123456789" }
    ]
  },
  "name": "Przykładowy Bank",
  "position": { "lat": 50.0617, "lon": 19.9373 },
  "location": { "city": "Kraków", "country_code": "PL", "method": "verified_context" },
  "classification": {
    "chaos_type": "bank",
    "subtype": "bank_branch",
    "source_tags": { "amenity": "bank", "atm": "yes" }
  },
  "attributes": { "atm": true, "surveillance": null },
  "geometry": { "type": "Point", "coordinates": [19.9373, 50.0617], "quality": "point" },
  "provenance": {
    "provider_id": "maplark",
    "snapshot_id": "EXAMPLE-SNAPSHOT",
    "osm_base_at": null,
    "fetched_at": "2026-10-20T12:00:00Z",
    "source_license": "ODbL",
    "mapping_version": "world-adapter-v1"
  }
}
```

**Opis rekordu:** `world_object_id` określa tożsamość obiektu świata; `classification` zawiera dane używane przez gameplay; `geometry` jest punktem tylko w przykładzie (dla `way/relation` zachowujemy adekwatne linie/poligony albo blokujemy rozszerzone lokalne pokrycie); `provenance` pozwala audytować import. `null` oznacza **brak wiedzy**, nie `false`. Nazwa i współrzędne są przykładowe, a zapis miasta musi mieć własne wiarygodne źródło.

### 5.3. Minimalne pola i semantyka braków

| Pole | Kontrakt / zachowanie |
|---|---|
| `world_object_id` | Preferowane `osm:{node\|way\|relation}:{id}`; dla nie-OSM identyfikator w osobnej przestrzeni nazw, np. `provider:{id}`. |
| `name` | Tekst opcjonalny; brak nazwy nie usuwa obiektu, jeśli gameplay dopuszcza marker bez nazwy. |
| `lat`, `lon` | Konieczne do dotychczasowego wyniku markerowego, walidacja zakresu i finite. |
| `chaos_type` | Typ kanoniczny z wersjonowanej mapy; jeśli nieudowodniony, `unknown`, bez zgadywania. |
| `source_tags` | **Minimalne, ale wystarczające** do odtworzenia aktualnych kategorii, kamer i przyszłych reguł określonych w profilu. |
| `attributes` | Trójwartościowe lub `unknown`; `atm=false` tylko gdy źródło rzeczywiście potwierdziło brak. |
| `geometry` | Punkt/linia/poligon/multipoligon wraz ze stopniem kompletności i wariantem CRS; wewnętrznie WGS84. |
| `osm_type`, `osm_id` | Zachowane osobno od ID dostawcy, kiedy źródło je faktycznie dostarcza. |
| `city` | Opcjonalne z podanym sposobem wyznaczenia; nie jest kluczem spójności ani warunkiem skanu. |
| `fetched_at` | Czas pobrania **nie jest** automatycznie datą aktualizacji OSM. |
| `source_license` | Wersjonowany identyfikator zasad i atrybucji; bez domyślnego „dowolne użycie”. |

### 5.4. Wersjonowany mapping gameplayu

Musi istnieć jawny **`CHAOS_OBJECT_PROFILE`**: lista tagów, klas, pól i wersja reguł. Na start odpowiada to faktycznie używanym kategoriom `shop`, `amenity`, `office`, `healthcare`, `atm=yes`, `man_made=surveillance`, bez dopisywania przyszłych mechanik.

| Dane źródłowe | Obiekt CHAOS | Uwaga |
|---|---|---|
| `amenity=bank` | `bank` | Zachować `atm` jeżeli istnieje, ale nie zakładać, że każdy bank posiada bankomat. |
| `amenity=atm` lub `atm=yes` | `atm` / atrybut bankomatu | Zgodnie z aktualną logiką; nie scalać automatycznie banku i osobnego bankomatu. |
| `shop=*` | `shop` + rozróżnienie branży | Ikony i przypadki szczególne nadal ustala dotychczasowy gameplay. |
| `amenity=restaurant`, `cafe`, `pharmacy`… | Podtypy usług | Potwierdzić dokładne mapowanie obecnym `assign_icon_and_type`. |
| `man_made=surveillance` | Rzeczywista kamera OSM | Oddzielna od kamer proceduralnych generowanych przez CHAOS. |
| `office=*`, `healthcare=*` | Odpowiednia klasa | Nie zgubić oryginalnych tagów wymaganych przez obecne reguły. |

**Kluczowy warunek:** nie przechowujemy jedynie `name + lat + lon + type`, jeśli w obecnej mechanice do poprawnych kamer, podtypów lub geometrycznego dopasowania potrzebne są dodatkowe tagi. Oszczędzamy miejsce na nieużywanych polach, nie na informacjach niezbędnych do odtworzenia gry.

### 5.5. Kompatybilność wsteczna

- Nowa warstwa eksportuje do `POIFetcher` / adaptera końcowego taki zestaw obiektów i tagów, jaki rozumie obecny skaner, a dopiero potem limituje do 60.
- Porządek wyników musi być deterministyczny i zgodny z rzeczywistymi zasadami gry; wynik API nie może przypadkowo zmieniać kolejności preferencji.
- Osobna kopia obiektu na każde żądanie gracza; mutacje `icon`, `source_type`, `generated` nigdy nie wracają do wspólnego repozytorium.
- Zmiana kontraktu i mapowania wymaga podniesienia wersji `classification_profile_version` i ponownej oceny kompletności starszych sektorów.

---

## 6. Adaptery dostawców i ich ograniczenia

### 6.1. Provider abstraction

Każdy adapter musi udostępniać logicznie:

```text
capabilities() -> CapabilityMatrix
estimate_cost(geo_area, filter_profile, geometry_profile) -> Estimate
fetch(geo_area, filter_profile, geometry_profile, budget) -> ProviderBatch
normalize(ProviderBatch) -> NormalizedBatch
validate_completeness(ProviderBatch, requested_scope) -> CoverageEvidence
```

**Opis interfejsu:** silnik pyta adapter o obsługiwane kategorie, koszt i możliwość udowodnienia kompletności; dopiero potem pobiera dane. Wynik przechodzi normalizację i walidację. To interfejs koncepcyjny — konkretne sygnatury, klasy i nazwy funkcji trzeba dopasować do kodu 160.

### 6.2. MapLark — kandydat do pełnego źródła OSM

Według dokumentacji dostępnej przy opracowywaniu koncepcji MapLark oferuje OSM Features API v3, filtrowanie po tagach OSM, identyfikatory obiektów i geometrię GeoJSON. Wspiera `node`, `way`, `relation`, promień lub bounding box i zwraca sygnały związane z wielkością odpowiedzi/limitami. **To dobry kandydat do odwzorowania kontraktu Overpass, ale nie mamy jeszcze testu zgodności w CHAOS ani zatwierdzonej polityki systematycznego gromadzenia danych.**

Sprawdzić w audycie adaptera:

- czy dostępne są wszystkie oryginalne tagi wymagane przez gameplay, w tym monitoring;
- czy ID OSM ma prawidłowy typ i jest stabilne;
- czy geometria jest pełna (nie obcięta granicami zapytania);
- czy `location+radius` i `bbox` wybierają odpowiedniki `nwr(around)`;
- czy odpowiedź jest kompletna czy ucięta przez tier (`X-Has-More`, `result_too_large`, inne pola/limity);
- czy ograniczenia wielkości promienia, kategorii i kredytów umożliwiają **wide fetch**;
- czy polityka rzeczywiście dopuszcza **trwałą bazę i zautomatyzowane uzupełnianie sektorów**, nie tylko pojedyncze odczyty.

**Ważne:** dokumentacja MapLark opisuje API v3 i równocześnie może zawierać starsze przykłady v2. Adapter musi być pisany pod **zweryfikowaną wersję kontraktu**, nie pod historyczny przykład.

### 6.3. Geoapify — kandydat do określonych kategorii POI

Places API używa własnych kategorii, przestrzennych filtrów kołowych/prostokątnych i paginacji (`limit` / `offset`). Dokumentacja usługodawcy dopuszcza cache, przechowywanie i redystrybucję wyników Places, pod warunkiem wymaganych atrybucji; darmowy plan wymaga także oznaczenia Geoapify. Nie oznacza to, że automatyczne pobieranie całych miast jest nielimitowane lub że API ma wszystkie tagi OSM.

Przygotować **macierz zgodności kategorialnej**; kategorię `man_made=surveillance` lub inny brakujący profil oznaczyć jako `UNSUPPORTED`, a nie jako „w sektorze nie znaleziono kamer”. Sprawdzić maksymalną liczbę wyników, paginację, dostępność identyfikatorów OSM, geometrię i aktualność.

### 6.4. Overpass DE / VK / Private.coffee

Zachowujemy jako potencjalne typy adapterów **tylko w zatwierdzonym zakresie**. W raporcie z 20.10.2026 brak powtarzalnej dostępności DE/VK i prace są wstrzymane. **Nie generujemy nowych requestów do tych publicznych instancji z samego wdrażania koncepcji**, nie obchodzimy ich limitów i nie próbujemy masowo „rozgrzać” cache.

### 6.5. Fallback nie jest tym samym co substytucja

Przykład: MapLark może dostarczyć komplet obiektów z kamerami, Geoapify — tylko sklepy i usługi. Przełączenie na Geoapify może uzupełnić część świata, ale **nie pozwala oznaczyć całego profilu CHAOS jako kompletny**. Mieszanie danych różnych źródeł jest możliwe wyłącznie z zachowaniem semantyki, atrybucji i dowodów kompletności każdej warstwy.

### 6.6. Dopuszczenie źródeł — dwie bramki, osobne uprawnienia

Dostawca jest dostępny dla zadanej akcji tylko gdy:

- ma `TECHNICAL_OK` w odpowiednim scenariuszu i wydolność zmierzona z VPS;
- ma `POLICY_APPROVED` dla **konkretnego** zakresu: `live_scan`, `wide_fetch`, `permanent_store`, `background_fill`, `refresh`, ewentualnie `redistribute`;
- mieści się w limicie budżetu i zdrowiu circuit breaker;
- ma znany profil jakości i odpowiedni **coverage capability**.

Dla MapLark **nie przypisujemy automatycznie** prawa do ciągłego harvestingu na podstawie darmowego planu; dla Geoapify potwierdzamy bieżący regulamin i jego zakres. Brak odpowiedzi operatora to brak zgody tam, gdzie takiej zgody potrzebujemy. Szerszy fetch może być OFF przy włączonym normalnym fetchu.

---

## 7. Coverage: najważniejszy kontrakt prawdy o świecie

### 7.1. Dlaczego lista obiektów nie wystarcza

Baza ma 40 obiektów w dzielnicy — ale czy to wszystkie obiekty? Tylko te, które dostawca zwrócił w pierwszej stronie? Tylko gastronomia? Obszar był kołem czy prostokątem? Czy znamy `way/relation` przecinające promień od zewnątrz? Bez tych odpowiedzi nie możemy bezpiecznie użyć lokalnego repo zamiast API.

### 7.2. Pokrycie opisujemy wielowymiarowo

Każdy dowód musi zawierać:

- **geometrię obszaru** i halo, nie tylko `cell_id`;
- **profil tagów** (`filter_profile_version`) i jawnie wspierane podprofile;
- **profil geometrii** (`point`, `center_only`, `nwr_full_geom`, inne zatwierdzone);
- **kompletność:** pełne strony API, brak limitu wyników, poprawna walidacja;
- **świeżość:** `fetched_at`, `source_dataset_at` jeśli znane, TTL i dopuszczalność stale;
- **identyfikator snapshotu**, dostawcę, zakres jego uprawnień i licencję;
- **stan jakości:** dowiedziony / częściowy / historyczny / nieudowodniony;
- **wersję kontraktu:** filtr, klasyfikacja, predykat przestrzenny i adapter.

### 7.3. Stany pokrycia

| Stan | Znaczenie | Czy może samodzielnie obsłużyć skan? |
|---|---|---|
| `UNKNOWN` | Brak danych i brak dowodu negatywnego. | Nie. |
| `QUEUED` | Region oczekuje na pracę w tle. | Nie. |
| `FETCHING` | Aktywne pobranie; wynik jeszcze niezatwierdzony. | Nie, można współdzielić oczekiwanie. |
| `PARTIAL` | Zapisano użyteczne obiekty, lecz brak kompletnej warstwy/strony/geometry. | **Nie jako pełny skan**; można wykorzystać dla późniejszego uzupełnienia. |
| `COMPLETE_FRESH` | Pełny dowód wymaganych kategorii i geometrii, świeżość w polityce. | Tak. |
| `COMPLETE_STALE` | Dawniej pełny dowód; obecnie poza fresh TTL, lecz jeszcze akceptowalny dla stale. | Tak, w trybie degradacji, zgodnie z 158/159. |
| `EXPIRED` | Brak prawa do obsługi skanu jako aktualny/stale. | Nie. |
| `FAILED` | Błąd pozyskania lub walidacji. | Nie; nie kasuje starszego poprawnego pokrycia. |

**Pusty, ale kompletny sektor** jest prawidłowym wynikiem: zero POI to wynik tylko wtedy, gdy sprawdzono i potwierdzono pokrycie.

### 7.4. Matematyczna bramka lokalnego odczytu

Lokalne wykonanie pełnego skanu jest dozwolone tylko wtedy, gdy **cały obszar zapytania** mieści się w sumie zwalidowanych obszarów pokrycia wymaganych warstw, bez luk i z zgodnym profilem geometrii oraz wieku. To wymaga testu geometrii/union, a nie sprawdzenia, czy punkt środkowy trafił do jednej komórki. Indeks komórek jest przyspieszeniem, nie dowodem.

### 7.5. `node` kontra `way/relation`

Dla `node` odległość od współrzędnych pozwala rozstrzygnąć obecność w promieniu. Dla dróg, budynków i relacji konieczna jest **geometria obiektu lub matematycznie równoważny dowód dopasowania**. Przykładowy budynek może przecinać promień skanowania, podczas gdy jego środek leży poza nim. W takim przypadku `center_only` daje fałszywy negatyw.

Obecny Overpass zwraca `out center`, ale selekcja `nwr(around)` odbywa się po geometrii. Przy przejściu na lokalny odczyt **nie wolno zastąpić selekcji po geometrii selekcją po centroidzie**.

Na start można dopuścić **dwa poziomy certyfikacji**: `EXACT_QUERY_COMPATIBLE` (dla identycznego punktu i parametrów działa cache 158) oraz `AREA_REUSABLE` (dowiedzione skany w dowolnym punkcie obszaru). Nie udajemy, że pierwszy automatycznie zapewnia drugi.

---

## 8. Scenariusz Kraków: od pierwszego skanu do znajomej dzielnicy

### 8.1. Pierwszy kontakt

Gracz testowy ląduje w nieznanym fragmencie Krakowa i skanuje obszar 300 m (przykładowy promień z obecnego fetchera).

1. Gra sprawdza uprawnienia, pozycję i GhostLab jak dziś.
2. World Planner sprawdza `exact-query cache` i lokalne kompletne pokrycie.
3. Repozytorium nie posiada wystarczających danych.
4. Router wybiera dostawcę **zatwierdzonego do tego zakresu i kategorii**.
5. Jedna kontrolowana operacja pobiera *np.* 600–900 m, **jeśli** limit i koszt to uzasadniają; w bardzo gęstym centrum może pobierać mniej. **To zakres roboczy do benchmarku, nie ustalona wartość produkcyjna.**
6. Adapter normalizuje **wszystkie wymagane obiekty**, nie tylko 60 markerów wynikowych.
7. Walidacja ustala kompletność poszczególnych profili; pełny batch trafia atomowo do bazy.
8. Gracz otrzymuje skan wykonany **tymi samymi regułami gameplayu**, co dawniej.
9. Zapisujemy zagregowany sygnał „zapotrzebowanie na sąsiednie sektory”, bez publicznej historii podróży gracza.

### 8.2. Drugi skan w tym samym rejonie

Sektor, odpowiedni filtr i geometria są kompletne. Gra pobiera obiekty lokalnie, filtruje po prawidłowej geometrii, wykonuje gameplay. **Zero HTTP do źródła.** Jeśli dane są stare, użycie regulują 158/159 i polityka age.

### 8.3. Trzeci skan przy krawędzi

Skan wychodzi o 80 m poza dowiedziony obszar. CHAOS **nie** udaje kompletności. Najpierw znajduje brakujące fragmenty, następnie jedną operacją pozyskuje tylko niezbędny zakres — jeżeli dostawca dopuszcza taki kształt zapytania i ich semantyka może zostać scalona. W przeciwnym razie wykonuje kontrolowany, pełny nowy fetch lub exact-query fallback.

### 8.4. Awaria wszystkich dostawców

- W kompletnym, jeszcze dopuszczalnym sektorze gracz skanuje lokalnie.
- W nieznanym/niekompletnym sektorze skan podlega istniejącemu stanowi MASA `BLOCKED`, bez kolejnych HTTP wywołanych klikaniem.
- Nie usuwamy weryfikowanych snapshotów z powodu nieudanej próby odświeżenia.
- GhostLab nie omija przerw i limitów globalnych.

---

## 9. Rozwijanie świata w tle: Discovery Worker

### 9.1. Co wywołuje task?

Wyłącznie potwierdzone, ograniczone zdarzenie zapotrzebowania, np. `world.coverage_demand` po skanie z obszaru bez lokalnych danych. Zadanie **nie** reprezentuje gracza ani jego stałej pozycji; dotyczy sektora i profilu danych.

### 9.2. Proponowany kształt zadania

```json
{
  "kind": "world.coverage_fill",
  "cell_id": "EXAMPLE-CELL",
  "coverage_profile": "chaos-poi-core-v1",
  "priority": "background",
  "reason": "recent_scan_demand",
  "attempts": 0,
  "earliest_start_at": "2026-10-20T12:05:00Z",
  "dedupe_key": "coverage:EXAMPLE-CELL:chaos-poi-core-v1"
}
```

**Opis zadania:** kolejkowane jest uzupełnienie konkretnego sektora dla określonego profilu; nie zapisujemy `user_id`, tokenu sesji, nicku czy pozycji ruchu. `dedupe_key` sprawia, że wiele skanów tej samej okolicy nie tworzy wielu robotów odpytywających to samo API. Wartości są wyłącznie ilustracyjne.

### 9.3. Zasady działania workera

- Działa **poza request workerami Gunicorna** i poza krytyczną ścieżką gry.
- Ma niski priorytet i **wspólny globalny budżet** z 158. Brak wolnego slotu = nie wykonuje HTTP.
- Nigdy nie uruchamia pobrania u dostawcy bez uprawnienia `background_fill` / `wide_fetch`.
- Nie przetwarza nieskończonej kolejki; ma maksymalną liczbę oczekujących i politykę starzenia.
- Kolejne sektory wybiera tylko według ograniczonego promienia ekspansji i ponownego zainteresowania graczy.
- Każdy task jest idempotentny, obsługuje lease, anulowanie, cooldown i bezpieczne wznowienie po restarcie.
- Nie ponawia natychmiast błędów 429/500/502/503/504 w pętli; przestrzega Retry-After i globalnego circuit breakera.
- Dla jednego obszaru i profilu obowiązuje **jedna aktywna próba**, niezależnie od liczby workerów i restartów.
- Zadanie o dużym koszcie może być podzielone na mniejsze lub odłożone, ale nie może „zaliczyć” pokrycia częściowym wynikiem.

### 9.4. Zasięg ekspansji

**Nie pobieramy automatycznie całego miasta.** Początkowo możliwe są dwa tryby:

- `PASSIVE`: tylko skan gracza tworzy pokrycie; kolejka zapisuje kandydatów, niczego sama nie odpytuje.
- `BOUNDED_PREFETCH`: po udowodnionym sukcesie lokalnym można wzbogacić *niewielki* pierścień sąsiednich komórek, w granicach dziennego budżetu i polityki API.

Docelowa decyzja o stopniu ekspansji wymaga danych o hit-rate i kosztach. Domyślnie **worker background OFF**.

### 9.5. Scheduler pod pierwszych ~100 testerów

Testerzy mogą lądować w Krakowie, Warszawie, USA, Japonii albo losowym punkcie mapy. Priorytetyzacja powinna więc być geograficznie neutralna. Proponowana kolejność: (a) aktywne żądanie gracza, (b) powtórne zapotrzebowanie na ten sam sektor, (c) sąsiedni sektor przy rosnącym lokalnym ruchu, (d) okresowy refresh popularnego obszaru, (e) prefetch spekulacyjny.

Wprowadzamy *fairness*: jeden bardzo aktywny region nie może pochłonąć całego przydziału i blokować nowych testerów na innych kontynentach. Szczegółową wagę przydziału wybieramy po benchmarkach; brak sztywnych magicznych współczynników w tej koncepcji.

### 9.6. Współbieżność i stan

Proponowane stany zadania: `PENDING → LEASED → FETCHING → VALIDATING → COMMITTED`, oraz `DEFERRED`, `RETRY_AFTER`, `POLICY_BLOCKED`, `FAILED_TERMINAL`, `CANCELLED`. Nieudany task nie obniża wcześniej zatwierdzonego `COMPLETE_FRESH` / `COMPLETE_STALE` dla innego snapshotu.

---

## 10. Jak wybierać wielkość pobrania bez przepalania kredytów

### 10.1. Dwa obszary

- `gameplay_area`: realny skan z mechaniki CHAOS.
- `fetch_area`: obszar zapytania dostawcy, zwykle większy, ale z limitami.

Parametry dobierane adaptacyjnie na podstawie gęstości POI, przewidywanego kosztu, geometrii, wspieranych filtrów, maksymalnej odpowiedzi, timeoutu, historii poprawnych wyników oraz obciążenia systemu. W zatłoczonym centrum miasta nie wolno wybierać tych samych wartości, co na terenach wiejskich, bez testów.

### 10.2. Cost estimate i paginacja

Jeżeli dostawca pozwala oszacować liczbę obiektów / kredyty przed pobraniem, wykorzystujemy tę możliwość **z limitem częstotliwości**. Jeśli konieczna jest paginacja, pobranie jest pełne tylko po zweryfikowanym zakończeniu wszystkich stron. `limit=500`, `X-Has-More`, `result_too_large` lub ucięcie odpowiedzi oznaczają brak prawa do wpisania `COMPLETE`.

### 10.3. Warunek minimalnego opłacenia szerokiego skanu

Porównujemy rzeczywisty koszt `wide_fetch` z oczekiwaną liczbą oszczędzonych przyszłych zapytań. Jeśli wide fetch jest zbyt drogi, używamy mniejszego zakresu. **Nie uruchamiamy masowego skanera tylko dlatego, że API oferuje darmowy plan.** Darmowe kredyty również podlegają limicie i polityce użytkowania.

### 10.4. Granica czasu live scan

Jeżeli lokalnego pokrycia brakuje, request może poczekać na **jedno kontrolowane pobranie** tylko w istniejącym deadline skanera i polityce GhostLab. Jeśli upstream nie zdąży lub jest zajęty, poprawnie obsługujemy fallback/stan MASA. **Nie blokujemy czterech workerów na długie, rozbudowane zadania background.**

---

## 11. Repozytorium: encje, tożsamość, upsert, aktualizacja

### 11.1. Rozszerzenie istniejącego schematu 160

**Najpierw audyt istniejących tabel 160.1.** Docelowo potrzebujemy co najmniej następujących funkcji logicznych (nazwy robocze, nie polecenie zakładania duplikatów):

| Model | Co przechowuje |
|---|---|
| `world_object` | Kanoniczne pola i minimalny tag payload obiektu. |
| `world_object_source_ref` | Powiązanie obiektu ze źródłowym OSM ID i ID providera. |
| `world_snapshot` | Każde pobranie i jego integralność; data źródłowa, profil, hash. |
| `world_snapshot_membership` | Które obiekty rzeczywiście wystąpiły w konkretnym zwalidowanym pobraniu. |
| `world_coverage` | Dowody pokrycia obszarów i profili, fresh/stale i geometry proof. |
| `world_coverage_capability` | Które kategorie konkretny snapshot weryfikuje jako kompletne. |
| `world_discovery_task` | Trwała kolejka, lease, retry-after, status i dedupe key. |
| `world_provider_adapter_registry` | Wersje adapterów i ich macierze zdolności; korzysta z admin registry 160. |
| `world_ingest_audit` | Pochodzenie, konflikty, walidacje, odrzucenia i metryki importu. |

### 11.2. Wariant magazynu

Na start preferujemy **istniejący SQLite + transakcje WAL + R*Tree/bbox** (jeśli audyt potwierdzi, że nie tworzy nadmiernej kontencji); oddzielna baza SQLite tylko przy mierzalnych powodach. Nie proponujemy PostGIS, Redis i kolejnego serwera jako obowiązkowych warunków MVP.

Cztery workery Gunicorna i jeden niskopriorytetowy worker tła korzystają z jednej logicznej koordynacji. HTTP wykonywany poza transakcjami SQLite; transakcje zapisu krótkie. Ograniczenia rozmiaru repo i retencji snapshotów są jawne.

### 11.3. Dedup i konflikty

- **OSM ID + typ** to najbezpieczniejsza tożsamość dla prawdziwych obiektów OSM.
- Obiekt bez OSM ID dostaje namespaced key dostawcy, lecz **nie jest automatycznie łączony** z pobliskim OSM POI na podstawie samej nazwy i współrzędnych.
- Jeśli MapLark i Geoapify podają to samo zweryfikowane ID OSM, możemy scalać potwierdzone pola z zachowaniem pochodzenia poszczególnych wartości.
- Sprzeczne dane z różnych źródeł — zachowujemy wersje/obserwacje, nie nadpisujemy bez audytu jakości.
- Usunięcie OSM obiektu jest dopuszczalne tylko z wiarygodnego dowodu pełnego, porównywalnego pokrycia / źródła zmian. **Brak w częściowym wyniku nie oznacza usunięcia.**
- Zachowujemy `unknown` osobno od `false`, `no`, pustej nazwy i `[]`.

### 11.4. Data freshness i wersje

Repo może zawierać dane z różnych momentów i od różnych dostawców. `fetched_at` mówi, kiedy CHAOS pytał, nie kiedy OSM było aktualne. Używamy osobnych pól `source_dataset_at` (jeśli potwierdzone) i `ingested_at`. Nie mieszamy ich w jeden „czas mapy”.

Aktualizacja nie może nadpisać nowszych danych starszym snapshotem ani deklarować świeżości całego sektora przez aktualizację pojedynczej kategorii. Weryfikacja po migracji wersji filtrów ponownie ocenia status pokrycia.

### 11.5. Retencja i budżet dysku

- Przechowujemy **minimalne pola gameplayu plus dane potrzebne do geometrii i dowodu**; surowe payloady mogą mieć ograniczoną retencję, o ile zachowujemy audyt zgodności.
- Stare snapshoty mogą być kompresowane albo usuwane z zachowaniem wymaganej lineage/membership.
- Przed automatycznym sprzątaniem weryfikujemy, czy nie znika jedyny dowód kompletności.
- Nie ustalamy docelowej liczby GB „na cały świat” bez benchmarku; system rośnie popytowo i ma limity podlegające zmianie.

---

## 12. Kontrakt wyniku i gameplay: regresja zerowa

### 12.1. Co pozostaje bez zmian

- odległość do awatara, zasięg akcji, zablokowanie skanu poza zasięgiem;
- GhostLab (`extra_retries`, `extra_timeout`, `still_active`, token i jego generacja);
- priorytet ikon i typów, limit wyniku, brak podwójnych obiektów;
- kamery prawdziwe i kamery generowane, NPC, jitter, zasady nagród i zasobów;
- marked targets, klany, capture anchor i pochodne mechaniki korzystające z kanonicznych markerów;
- indywidualność i izolacja skanów dwóch graczy;
- `MASA` jako komunikacja **realnych** stanów infrastruktury, nie nowa losowa mechanika.

### 12.2. Krytyczne testy zgodności

Testy muszą porównywać wynik **z tego samego kontrolowanego snapshotu źródłowego** dla każdej gałęzi: dokładny fetch starym kontraktem, ten sam fetch znormalizowany i zapisany w repo, potem lokalny odczyt z innego punktu i ten sam pipeline gameplay. Rzeczywiste publiczne API może się zmienić między próbami i nie nadaje się na jedyne źródło prawdy w regresji.

Warunek szczególny: `way/relation` przechodzą przez granicę promienia skanu. Jeżeli adapter nie potrafi udowodnić zgodności, takie pokrycie nie jest dopuszczone jako `AREA_REUSABLE`; zostaje bezpieczny exact-query cache.

### 12.3. Kolejność i deduplikacja

Obecny `get_all()` ogranicza wynik po kategoryzacji i deduplikuje obiekty po współrzędnych. Trzeba to przetestować na obiektach o takich samych współrzędnych, ale różnych OSM ID. **Nie zmieniamy ukradkiem logiki deduplikacji**, nawet jeśli nowe repozytorium deduplikuje wewnętrznie według ID. Refaktor tej zasady byłby odrębną decyzją gameplayową.

---

## 13. Panel administratora: „poznany świat” i gospodarka providerami

### 13.1. Widok operacyjny

Proponowane bloki admina (rozbudowa istniejącego panelu 160.3/160.4):

1. **Stan warstw:** ile obszarów `COMPLETE_FRESH`, `COMPLETE_STALE`, `PARTIAL`, `UNKNOWN`, jakość geometrii i lista wspieranych filtrów.
2. **Mapa pokrycia:** komórki świata z możliwością podglądu konkretnych dowodów, granic i wersji profilu; bez publicznej historii konkretnego gracza.
3. **Wzrost repo:** liczba obiektów, przyrost dzienny, zapisy, deduplikacje, rozmiar bazy, zużycie WAL, retencja.
4. **Źródła:** MapLark / Geoapify / Overpass jako *kandydaci*, status techniczny, status prawny, dopuszczalny zakres, wersja adaptera, zmiana URL i secret refs.
5. **Koszty i limity:** zużycie kredytów/API, liczba zapytań, response size, szacowany koszt pobrania i procent budżetu.
6. **Kolejka discovery:** pending/deferred/failed/running, liczba zadań, aktywne leasy, źródło tasku bez danych osobowych.
7. **Stabilność:** czas odpowiedzi, timeouty, 429/5xx, circuit open/half-open, data ostatniego potwierdzonego sukcesu, próbki i okres.
8. **Sterowanie:** oddzielne przełączniki live fetch / ingest / local read / background prefetch / source disable / global kill switch.

### 13.2. Zasada bezpieczeństwa interfejsu

Admin może wybrać zatwierdzonego providera i jego dozwolony endpoint, ale nie może ustawić dowolnego adresu localhost/VPS jako „API mapy”. Obowiązują bramki SSRF, TLS, DNS-rebinding, zakaz redirectów, kontrola DNS/IP po połączeniu, redakcja tokenów, ograniczenia RBAC/CSRF, historia zmian i rollback. Konfiguracja API jest wersjonowana i propagowana do wszystkich czterech workerów.

### 13.3. Monitoring nie może sam zużywać usługi

Pierwszeństwo mają **pasywne pomiary rzeczywistego ruchu**, następnie status/capability i dopiero rzadki mały aktywny probe zatwierdzonego dostawcy. Każdy probe podlega własnemu budżetowi, ten sam transportowi i circuit breakerowi. Nie testujemy publicznego DE w pętli, gdy zgłasza pełną kolejkę i ograniczenie automatycznego użycia.

---

## 14. Stany dla użytkownika i MASA

| Backend | Co znaczy | UX |
|---|---|---|
| `WORLD_LOCAL_FRESH` | Pełny skan z aktualnego repo. | Normalny skan, bez technicznego komunikatu. |
| `WORLD_LOCAL_STALE` | Kompletne dane historyczne w ramach zaakceptowanej polityki. | Subtelne zakłócenia MASA / ostatni zapis terenu, zgodnie z 159. |
| `WORLD_FETCHING` | Dozwolone pobranie jeszcze trwa. | Stan oczekiwania skanera, bez fikcyjnego odzyskania sygnału. |
| `WORLD_FETCHED` | Udało się pobranie i kompletna rekonstrukcja skanu. | Normalny wynik skanu. |
| `WORLD_PARTIAL` | Mamy tylko część danych; brak prawa do pełnego skanu. | Brak „fałszywie pełnej” listy markerów. |
| `WORLD_UPSTREAM_BLOCKED` | Brak dopuszczalnego lokalnego zapisu i brak dozwolonego źródła. | MASA `BLOCKED` wg 159, bez ponowień od kliknięć. |
| `WORLD_INTERNAL_ERROR` | Błąd konfiguracji, sesji, walidacji, SQLite lub adaptera. | Błąd techniczny/systemowy, **nie udajemy działania MASA**. |

**Nie tworzymy nowej narracji MASA ponad 159**; warstwa rozpoznania przekazuje już ustalone semantyczne stany, a istniejący UX renderuje je w logach mapowych. Jeśli potrzebne są nowe tłumaczenia, obowiązuje osobna walidacja PL/EN i mobile/desktop.

---

## 15. Limity wydajności, bezpieczeństwo i koszty

### 15.1. Założenia o VPS

Nie zakładamy wolnego RAM ani dysku. CHAOS działa na 4 workerach, a serwer ma inne usługi, w tym obciążające CPU/RAM zadania lokalnych modeli. Dlatego:

- repo jest **dyskowe**, z indeksem przestrzennym; brak globalnego wczytywania obiektów do RAM;
- worker tła wyłączony do czasu benchmarku i może dostać niski priorytet CPU/I/O;
- limit rozmiaru odpowiedzi, elementów, zadania i dziennego przyrostu danych;
- limit liczby aktywnych procesów pobierania — początkowo na poziomie istniejącego budżetu 158;
- automatyczne wygaszanie zadania, gdy gracze przestają odwiedzać obszar;
- przegląd WAL, indeksów i backupu; wolne miejsce potrzebne również na migracje oraz snapshot/rollback;
- brak gwarancji wydajności bez rzeczywistych pomiarów.

### 15.2. Co mierzymy zamiast zgadywać GB

Dla wybranego zestawu fixture'ów obszarów o różnej gęstości liczymy: `bytes_in`, `normalized_bytes`, `index_bytes`, `sqlite_wal_bytes`, `unique_objects`, `memberships`, `coverage_bytes`, RAM peak, czas normalizacji, czas lokalnego skanu P50/P95, czas transakcji i liczba żądań upstream. Na tej podstawie wyznaczymy koszt „jednego kompletnego km²” dla różnych profili — nie zakładamy, że wszystkie regiony świata są jednakowo gęste.

### 15.3. Ryzyka licencyjne i prywatności

- OSM jest na ODbL; należy zapewnić atrybucję, analizę obowiązków pochodnej bazy i ewentualne udostępnienie danych/metody odtworzenia, gdy licencja tego wymaga.
- Gra może być niekomercyjna, ale **to nie uchyla** warunków dostawców i licencji danych.
- Geoapify wymaga oznaczeń zgodnie z planem, na darmowym także własnej marki; MapLark wymaga weryfikacji aktualnych warunków i uprawnienia do zautomatyzowanego zbierania.
- Integracja danych różnych źródeł może rodzić odmienne wymagania atrybucji i redystrybucji; lineage musi być zachowane na poziomie snapshotu/obiektu.
- Zewnętrzne źródło widzi współrzędne lub obszar zapytania i IP VPS. Zapytania nie zawierają identyfikatorów sesji ani danych prywatnych gracza.
- Jeżeli zadania są wyzwalane zachowaniem graczy, minimalizujemy logi, stosujemy agregację i retencję, nie publikujemy szczegółowych śladów ruchu testera.
- Nie uruchamiamy „scrapera”, który obchodzi zabezpieczenia stron WWW albo kwoty API; to **zgodny z warunkami klient udokumentowanych usług**.

---

## 16. Strategia testów — bez zależności od niestabilnych publicznych API

### 16.1. Kontraktowe testy offline

- Fikstury Overpass JSON, MapLark GeoJSON, Geoapify Places — zapisane odpowiedzi z legalnie pozyskanych, niewrażliwych danych, z timestampem kontraktu.
- Tag mapping: bank z bankomatem, bank bez informacji o bankomacie, oddzielny ATM, sklep, biuro, apteka, monitoring, obiekt bez nazwy.
- `node`, `way`, `relation`; centroid daleko poza kołem, przecięcie granic komórek, multipoligon i droga przecinająca zakres skanu.
- Duplikaty z tej samej i różnych usług; wspólny OSM ID / różny provider ID; sprzeczne tagi i starszy snapshot.
- Strona API kończąca się limitem, `has_more=true`, błąd paginacji, przerwany JSON, 429/500/502/503/504 i długi timeout.
- Lokalny zwrot z bazy `0 HTTP`, poprawny skan pustego, ale kompletnego obszaru.
- Coverage zgodnie z profilem; Geoapify nie może dowodzić kompletności kamer, gdy nie zwraca takiej warstwy.
- Równoległe 4 procesy odpytywania tego samego sektora = jeden właściciel fetch, nikt nie zapisuje niedokończonej odpowiedzi.
- Restart w trakcie ingestu/lease → bez podwójnych obiektów i fałszywych statusów complete.
- Anulowanie GhostLab i wygaśnięcie tokenu → bez wstrzyknięcia wyniku po anulowaniu, bez zbędnego dalszego HTTP.
- Porównanie z dotychczasową ścieżką: ikony, kamery, NPC, kolejność, limit 60, zasoby gracza, oznaczone cele.

### 16.2. Testy przeglądarkowe

Panel admina PL/EN, desktop/mobile; admin map coverage; dodawanie kandydatów, brak możliwości aktywacji `POLICY_PENDING`, zmianę URL, bezpieczny rollback, usuwanie tasków, funkcjonowanie kill switch. Mapowy komunikat MASA ma pojawić się w istniejącym systemie logów, nie jako niepasująca centralna belka.

### 16.3. Testy z API dopiero po zgodzie

Należy przygotować **plan pilotu**, ale nie uruchamiać go teraz. Po dopuszczeniu źródła: mała próba techniczna z VPS, potem jeden ograniczony region testowy, porównanie z bazowym kontraktem, test zapis → odczyt lokalny bez HTTP → restart → odczyt, osobno pomiar kosztu i czasu. Każdy kolejny etap wymaga świadomej decyzji operatora CHAOS.

---

## 17. Etapy prac (celowo bez numerów sprintu)

### Etap A — Audyt bieżącej implementacji i kontraktów

**Zakres:** przeczytać aktualne klasy `poi_infrastructure`, tabelki 160, ścieżki skanowania, profile GhostLab, provider registry i UX MASA. Przygotować diagram zależności oraz listę braków. **Nie zmieniać produkcji.**

**Bramka:** wiadomo, które elementy 160 są realnie gotowe, które wymagają dokończenia, a które były tylko testowane w izolacji; nie ma duplikatów usług.

### Etap B — Kontrakt kanoniczny + adaptery offline

**Zakres:** wersjonowany `WorldObject`, znormalizowany wynik, mapping tagów, fixture'y MapLark/Geoapify/Overpass i macierz zdolności dostawców. Początkowo tylko testy offline.

**Bramka:** jeden model obsługuje wszystkie dostarczone formaty, zachowując `unknown`, ID i proveniencję; brak błędnych fałszywych kamer/bankomatów.

### Etap C — Dowody pokrycia i prawidłowa geometria

**Zakres:** proof of coverage dla profili i sektorów; testy przecięcia `way/relation`, union, freshness, walidacja paginacji i membership. Wykorzystać istniejącą implementację 160 zamiast tworzyć nowy storage.

**Bramka:** brak fałszywych local hits i brak pominięć geometrycznych w certyfikowanym zakresie. Jeśli zgodność nie jest dowiedziona, feature pozostaje OFF.

### Etap D — World Read Planner + fallback 158

**Zakres:** odczyt local-first, spójne stany i jego eksport do istniejącego gameplayu; izolacja danych graczy. Flaga domyślnie OFF.

**Bramka:** powtarzalne wyniki dla tych samych fixture'ów, zero HTTP na kompletnie pokrytych obszarach, poprawne anulowanie i MASA.

### Etap E — Kolejka i worker odkrywania świata

**Zakres:** dedup, lease, priorytety, fairness regionalny, limity, backoff, shutdown i konfiguracja admina. Początkowo `PASSIVE`, bez faktycznego automatycznego API ruchu.

**Bramka:** cztery procesy + worker zachowują jeden wspólny limit, brak pętli i niekontrolowanych pobrań.

### Etap F — Admin: monitoring i sterowanie

**Zakres:** uzupełnienie luk 160.3/160.4, podgląd sektorów, koszty, opcje ekspansji, bezpieczna aktywacja, historia zmian i rollback.

**Bramka:** operator widzi, dlaczego skan idzie lokalnie, a dlaczego do API; potrafi wstrzymać nowe pobrania jednym przełącznikiem.

### Etap G — Policy review + pilot z jednym źródłem

**Zakres:** potwierdzenie dozwolonego pozyskiwania/zapisu/prefetchu, test małego rzeczywistego zakresu, instrumentacja i odbiór gameplayu. **Nie blokować wcześniej faz offline z powodu awarii publicznych API.**

**Bramka:** legalne i powtarzalne zasilanie repo, zapis→odczyt bez HTTP, restart, odtworzenie, koszt i metryki z VPS.

### Etap H — Stopniowe użycie na testerach

**Zakres:** ograniczony opt-in użytkowników/obszarów, obserwacja obciążenia, wzrost repo w czasie, porównanie kosztów; dopiero potem bounded prefetch i szerszy rollout.

**Bramka:** zero regresji krytycznego gameplayu, zero niekontrolowanego ruchu do źródeł, procedura rollbacku przetestowana praktycznie.

---

## 18. Rollout, flaga i rollback

Nie narzucamy nazw zmiennych przed audytem istniejących flag 160. Poniższe nazwy są **wyłącznie propozycją**:

```text
CHAOS_WORLD_OBJECT_CONTRACT_ENABLED=0
CHAOS_WORLD_LOCAL_READ_ENABLED=0
CHAOS_WORLD_INGEST_ENABLED=0
CHAOS_WORLD_DISCOVERY_QUEUE_ENABLED=0
CHAOS_WORLD_BACKGROUND_FILL_ENABLED=0
CHAOS_WORLD_PROVIDER_ROUTING_ENABLED=0
```

**Opis przełączników:** pozwalają osobno wdrażać kontrakt/odczyt/zapis/kolejkę/tło/wybór dostawcy; domyślnie OFF, dzięki czemu migracje i kod mogą pojawić się bez zmiany źródła danych podczas gry. Na produkcji nie ustawiamy ich bez przejścia wszystkich bramek. W implementacji należy **wykorzystać flagi istniejącego sprintu 160**, jeśli zapewniają równoważne możliwości, zamiast mnożyć dublety.

### Procedura bezpiecznego wycofania

1. Zatrzymać nowe pobrania i worker tła; anulować leasy i zadania zgodnie z ich polityką.
2. Wyłączyć provider routing, ingest i lokalny read — powrót do ścieżki zgodnej z 158.
3. Nie usuwać zweryfikowanych danych, snapshotów i audit trail; odłączenie funkcji to nie kasowanie świata.
4. Sprawdzić funkcje skanu, UX MASA i stan bazy po restarcie.
5. Pamiętać: **rollback kodu nie przywraca dostępności DE/VK** — nieznane regiony nadal mogą być blokowane.

---

## 19. Mierniki sukcesu i pilotaż pierwszej grupy

**Obowiązkowe metryki (bez wpisywania wymyślonych progów):**

| Metryka | Pytanie, na które odpowiada |
|---|---|
| `world_local_hit_ratio` | Jaki procent pełnych skanów nie wymaga HTTP? |
| `poi_http_calls_per_successful_scan` | Czy koszty sieciowe maleją? |
| `new_complete_coverage_area` | Ile rzeczywiście przybyło dowiedzionego obszaru? |
| `coverage_partial_ratio` | Jak często API daje niekompletne dane? |
| `provider_spend_per_100_scans` | Ile kosztuje pierwsza setka interakcji w różnych warunkach? |
| `world_unique_objects` | Ile unikalnych rzeczywistych POI mamy? |
| `world_repo_bytes_per_object` | Czy rozmiar repo rośnie liniowo i przewidywalnie? |
| `scan_latency_p50_p95` | Czy lokalna ścieżka poprawia UX? |
| `scan_error_rate_by_reason` | API vs brak danych vs bug vs GhostLab vs MASA. |
| `worker_queue_age_p95` | Czy discovery nie zalega? |
| `upstream429_5xx` | Czy nie przeciążamy cudzych usług? |
| `backend_ram_peak`, `db_lock_wait` | Czy nowe moduły mieszczą się na VPS? |

### Hipotezy do zweryfikowania

- Rzeczywiste skany testerów klastrują się w kilku obszarach, co daje powtarzalność i oszczędności.
- Szeroki fetch obniża liczbę requestów na skan, **ale** nie musi obniżać liczby kredytów; mierzymy oba efekty.
- Niewielka kanoniczna baza POI przyrasta wolniej niż repo pełnych payloadów OSM, przy zachowaniu wymaganej geometrii.
- W miarę dojrzewania repo szansa skanu local-first rośnie, lecz nowe regiony nadal wymagają zewnętrznego źródła.

**Kryterium odbioru:** nie ustalać arbitralnego „90% offline” przed danymi z pilotażu; najpierw baseline, dopiero mierzalne SLO i plan pojemnościowy. Jedna działająca dzielnica nie dowodzi globalnej zgodności.

---

## 20. Rejestr najważniejszych ryzyk

| Ryzyko | Skutek | Ochrona |
|---|---|---|
| Dostawca zabrania trwałego harvesting albo go ogranicza | Blokada integracji / naruszenie warunków | Oddzielna akceptacja `permanent_store` i `background_fill`, wersjonowane dowody. |
| MapLark i Geoapify nie zwracają tych samych klas | Fałszywe COMPLETE, znikające kamery | Capability matrix, coverage per category, `unknown > guess`. |
| Selekcja tylko po centrum obiektu | Pominięcie dużych obiektów OSM | Pełna geometria i testy przecięcia, safe fallback. |
| Limit/paginacja API | Niekompletny świat oznaczony jako pełny | Walidacja pełnego końca danych, brak COMPLETE. |
| Różne wersje map w API | Złe merge/usunięcia | Snapshot provenance, ostrożne merge, pełne porównywalne coverage. |
| Zbyt szerokie prefetch | Koszty, throttling, nadmiar dysku | OFF domyślnie, adaptacyjny radius, budżety i kill switch. |
| Kilku graczy prosi o ten sam sektor | Lawina HTTP | Shared lease, single-flight, identyczny globalny limit 158. |
| Awaria VPS podczas zapisu | Uszkodzone pokrycie | Atomowy snapshot+membership+coverage i testy restartu. |
| Stare dane podają nieaktualne obiekty | Błędne realne punkty | Data freshness, przyjęta polityka stale i refresh. |
| Przejęcie panelu admina / podmiana API URL | SSRF, kradzież danych, DoS | Walidacja URL/DNS/IP/TLS, RBAC, CSRF, audyt, allowlista. |
| Mix danych OSM i własnych danych graczy | Ryzyko licencji i prywatności | Separacja warstw, provenance, ograniczona retencja telemetryki. |
| Częściowy sprint 160 uznany za „skończony” | Niebezpieczny rollout | Osobne gates produkcyjne, testy evidence, rollback, brak PASS bez pilota. |

---

## 21. Decyzje otwarte, które trzeba rozstrzygnąć przed specyfikacją implementacyjną

1. Które dokładnie tagi i atrybuty są **naprawdę** czytane przez cały aktualny gameplay poza widoczną metodą `assign_icon_and_type()`? Kontrakt musi wynikać z audytu, nie z pamięci.
2. Czy w pierwszym wydaniu wspieramy **wyłącznie POI**, a geometria dróg/budynków pozostaje oddzielnym, opcjonalnym profilem? Wstępnie: tak, jeśli nie jest używana przez bieżący skaner.
3. Które źródło i które uprawnienia przejdą formalny `POLICY_APPROVED` na wide fetch, trwały zapis i background filling? Brak decyzji = background OFF.
4. Jakie są rzeczywiste limity i koszty MapLark/Geoapify po przeliczeniu pojedynczego skanu miasta/wsi oraz prawdziwego profilu kategorii?
5. Czy można odtworzyć pełną geometrię potrzebną do równoważności `nwr(around)` ze wszystkich wybranych usług?
6. Jakie są preferowane rozmiary sektorów? H3 ma być indeksem, a nie wymuszeniem błędnego kwadratowego pokrycia.
7. Czy backlog discovery ma przechowywać tylko sektory, czy także wersję żywotnego zainteresowania regionem (zagregowany licznik)?
8. Która baza SQLite i tabela z 160.1 jest autorytatywna; czy nowy profil obiektu wymaga migracji?
9. Czy własny magazyn ma udostępniać repozytorium geograficzne innym modułom CHAOS (np. AI), czy na start pozostaje prywatnym serwisem skanera?
10. Jakie SLO stawiamy dla skanów local-first, maksymalnego przyrostu DB, kolejki i budżetu po benchmarku?
11. Które elementy obecnego, wstrzymanego 160 muszą zostać zamknięte **przed** wejściem tego konceptu do produkcji? Wstępnie: zakresy providerów, geometria, odczyt lokalny, metryki i rollback.

---

## 22. Polecenie projektowe dla Codexa — etap analizy, nie implementacji

> Przeanalizuj dokument `CHAOS.WORLD.DISCOVERY.CONCEPT` jako przyszły moduł rozwoju CHAOS bez numeru sprintu. Najpierw zinwentaryzuj aktualny kod 158/159/160 oraz stan produkcyjny i potwierdź, czego nie wolno zmieniać. Nie wykonuj push, deploy, prób przeciążonych publicznych API ani aktywacji flag. Opracuj osobną macierz `current capability → reuse → missing implementation → evidence` oraz kanoniczny kontrakt obiektów na podstawie faktycznie czytanych pól gameplayu. Porównaj offline MapLark, Geoapify i Overpass pod kątem identyfikatorów, tagów, geometrii, paginacji, możliwości dowiedzenia pokrycia i dopuszczalnego zastosowania licencyjnego. Następnie rozpisz etapowe działania, testy, telemetrię, bramki bezpieczeństwa i rollback tak, aby wykorzystać istniejące repozytorium 160, a nie tworzyć drugiego. Zatrzymaj się na projekcie i zgłoś otwarte decyzje do zatwierdzenia.

**Opis instrukcji:** to brief do **audytu i zaprojektowania szczegółów**, nie zgoda na kodowanie lub ruch produkcyjny; wymaga dowodów zgodności i jawnego domknięcia niedokończonych elementów 160 przed wdrożeniem kolejnej warstwy.

---

## 23. Definicja sukcesu przyszłego wdrożenia (nie aktualny PASS)

Za ukończone będzie można uznać dopiero rozwiązanie, które udowodni łącznie:

1. Jeden skan nowego, niewypełnionego obszaru legalnie pobiera i zapisuje **kompletne wymagane dane** od zatwierdzonego dostawcy.
2. Ten sam i sąsiedni **w pełni pokryty** skan działa po lokalnym odczycie bez HTTP, także po restarcie procesu i VPS; geometryczna i gameplayowa zgodność potwierdzona fixture'ami i pomiarem.
3. `way/relation`, pusty komplet, niepełna paginacja, braki kategorii, `unknown` i konflikty snapshotów nie prowadzą do fałszywego wyniku.
4. Wiele procesów równoczesnych nie dubluje requestów; worker nie narusza budżetu i można go w każdej chwili wyłączyć.
5. Działają uzgodnione koszty, limity, provenance, licencje, alerty, panel administracyjny i bezpieczna zmiana źródła.
6. Gameplay, GhostLab, markery, kamery, NPC, klany, koszty i MASA zachowują istniejący kontrakt.
7. Rollout ma uznany baseline, test na rzeczywistym VPS, tryb kontrolowanego wycofania oraz komplet dowodów; **nie domniemywa PASS z samych testów lokalnych**.

---

## 24. Dokumentacja zewnętrzna do weryfikacji w audycie

Poniższe źródła służą do **oceny kontraktu technicznego i licencji**; nie są automatyczną zgodą operatorów na długotrwałe masowe pobieranie.

- **MapLark — OSM Features API / overview:** https://wiki.openstreetmap.org/wiki/Maplark ; https://maplark.com/developer
- **Geoapify — Places API, filtry i paginacja:** https://apidocs.geoapify.com/docs/places/index.html
- **Geoapify — warunki przechowywania i atrybucji wyników Places:** https://www.geoapify.com/places-api/
- **OpenStreetMap Foundation — ODbL / FAQ:** https://osmfoundation.org/wiki/Licence_and_Legal_FAQ
- **OpenStreetMap Foundation — Attribution Guidelines (w tym gry):** https://osmfoundation.org/wiki/Attribution_Guidelines
- **OSM — przykłady użycia baz pochodnych:** https://wiki.openstreetmap.org/wiki/License/Use_Cases
- **Aktualne repo CHAOS / dokumenty wewnętrzne:** `poiFetchClass.py`, `poi_infrastructure/service.py`, `run.py`, `ghostlab_scanner.py`, runbooki i audyty sprintu 160. Pierwszeństwo ma rzeczywisty kod i dowody z bieżącego środowiska, nie historyczne tytuły dokumentów.

---

## 25. Ostateczna decyzja koncepcyjna

**CHAOS nie potrzebuje własnej kopii całej planety — potrzebuje własnej, wiarygodnej pamięci geograficznej świata odwiedzanego przez graczy.** Każdy sektor ma być opisywany przez prawdziwe obiekty, sprawdzalną geometrię, pochodzenie i dowód kompletności, a nie przez samą listę markerów. Dostawców traktujemy jako wymienne kanały pozyskiwania danych, nie jako część silnika gry.

Rozwijamy istniejące prace 158–160, chronimy gameplay i zasoby VPS, zaczynamy od pierwszych rzeczywistych testerów i rozszerzamy repozytorium wyłącznie tam, gdzie potrzebne, opłacalne i dozwolone jest pozyskanie danych.

**Status końcowy dokumentu: koncepcja do akceptacji, bez numeru sprintu, bez wznowienia wstrzymanego rollout’u 160 i bez autoryzacji działań produkcyjnych.**
