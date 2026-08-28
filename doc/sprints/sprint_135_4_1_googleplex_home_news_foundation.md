# Sprint 135.4.1 — Googleplex Home + News Foundation

Status: `PLANNED / READY TO START`.

Sprint 135.4 jest zamknięty. Sprint 135.4.1 buduje lekką, bezpieczną
powierzchnię Googleplex Home/News, ale nadal nie publikuje graczom wyników
Ollamy.

## Wiążące materiały

Implementacja musi być zgodna jednocześnie z:

- `doc/sprints/googleplex_news_functional_spec.md` — kontrakt funkcjonalny;
- `doc/sprints/googleplex_news_visual_css_spec.md` — kontrakt wizualny i CSS;
- `doc/visual/ggpl_news.png` — zatwierdzona referencja kompozycji;
- `doc/architecture/profile_hot_path_contract_130_11_plus.md` — zakaz
  ciężkiego profilu w hot path.

Kolejność rozstrzygania niejasności:

```text
bezpieczeństwo i canonical gameplay
→ functional spec
→ visual/CSS spec
→ ggpl_news.png jako referencja kompozycji
```

Makieta nie jest źródłem literalnych tekstów, nazw, liczb ani nowych mechanik.
Określa hierarchię, proporcje, rytm i klimat interfejsu.

## Cel sprintu

Po otwarciu zakładki Googleplex przy pustym zapytaniu gracz otrzymuje
editorialowy Home/News pokazujący istniejące życie świata CHAOS. Wpisy:

- czytają bounded canonical projections i agregaty;
- nie są nowym source of truth;
- nie tworzą faktów ani zdarzeń gameplayowych;
- nawigują wyłącznie przez istniejące dispatchery;
- są backendowo ograniczone do audience bieżącego gracza;
- zachowują dzisiejszy katalog, wyszukiwanie, zakup i instalację.

Docelowy przepływ:

```text
canonical bounded stores / deterministic aggregates
→ audience-projected Googleplex News read model
→ Home snapshot (12–24 wpisy)
→ ACTIONABLE przez istniejący dispatcher
  albo STAMP_ONLY bez interakcji
```

## Nienegocjowalne invarianty

1. `query == ""` oznacza `HOME_MODE`.
2. `query != ""` uruchamia dotychczasowy `SEARCH_MODE` i dotychczasowe wyniki.
3. News tylko czyta, agreguje, porządkuje, prezentuje i nawiguje.
4. Frontend nie wymyśla akcji ani targetu.
5. Brak canonical action oznacza `STAMP_ONLY` i brak zachowania linku/buttona.
6. Otwarcie, refresh i polling Home nie tworzą taska LLM i nie wywołują Ollamy.
7. `accepted Inbox candidate != publication`. Kandydat bez przyszłego
   publication receipt ze Sprintu 135.5 nie może trafić do Home.
8. Audience jest projektowane w backendzie, nie ukrywane CSS-em.
9. News nie czyta ani nie zapisuje pełnego profilu.
10. Search Googleplex, News, Ghost Exchange i BlackNet zachowują niezależny stan.
11. Mobile ma jeden główny scroll.
12. `hero/large/medium/small` zmienia tylko prezentację, nigdy audience, truth,
    uprawnienia ani action.

## Punkt wyjścia w obecnym kodzie

Przed implementacją trzeba zapisać krótki audit aktualnego call chainu:

```text
openBrowser()
→ WebDragons / activeBrowserTab = googleplex
→ loadCatalog()
→ GET /api/profile + GET /api/catalog
→ renderCatalog()
→ empty query obecnie czyści results
```

Istniejące flow wyszukiwania i zakupu pozostaje canonical:

```text
search input
→ googleplexSearchText()
→ renderCatalog()
→ product card
→ showInstallAppProgress()
→ istniejący purchase/install/travel flow
```

Sprint zastępuje wyłącznie zachowanie pustego query i dodaje adaptery
nawigacyjne. Nie tworzy drugiego katalogu, purchase flow ani teleportera.

Boot Home trzeba odseparować od dzisiejszego `loadCatalog()`. Puste query nie
może automatycznie wykonywać ciężkiego `GET /api/profile` tylko po to, aby
zbudować News. Masthead/account context korzysta z istniejącego lekkiego
toolbar/desktop projection albo nowego bounded summary. Katalog jest lazy-loaded
dopiero po przejściu do Search/Product Detail, bez zmiany jego canonical
purchase/install semantics.

```text
Googleplex open + empty query
→ lightweight account context already available to desktop
→ GET bounded News snapshot
→ HOME_MODE
→ zero full-profile reads

first non-empty query / product navigation
→ lazy load existing catalog projection
→ SEARCH_MODE
```

## Tryby powierzchni i stan UI

Googleplex otrzymuje jawną maszynę trybów:

```text
HOME_MODE
SEARCH_MODE
PRODUCT_DETAIL_MODE
```

Przejścia:

```text
open Googleplex + empty query
→ HOME_MODE

HOME_MODE + wpisanie query
→ SEARCH_MODE
→ istniejące wyniki katalogu

SEARCH_MODE + wyczyszczenie query
→ HOME_MODE
→ odtworzenie bounded snapshotu i pozycji scrolla

ACTIONABLE product card
→ istniejący product detail/purchase surface
→ PRODUCT_DETAIL_MODE, jeżeli obecny UI go rozróżnia
```

Stan należy rozdzielić co najmniej na:

```text
googleplex_home_state
googleplex_search_state
googleplex_catalog_state
ghost_exchange_state
blacknet_state
```

Przełączenie zakładki nie kopiuje query, filtrów, aktywnego wpisu ani scrolla
między produktami. Cache Home jest viewer-bound i po zmianie sesji lub konta
zostaje unieważniony.

## Canonical Googleplex News read model

### Envelope snapshotu

Pierwsza implementacja udostępnia jeden bounded endpoint/read service. Dokładną
trasę trzeba potwierdzić podczas audytu routingu; preferowany kontrakt:

```text
GET /api/googleplex/news?view=home&limit=20&cursor=<opaque>
```

Odpowiedź:

```text
schema_version
view
state_version
generated_at
viewer_scope_revision
entries[]
global_stats[]
protocol_status
next_cursor
has_more
```

Home pobiera 12–24 wpisy i nie skanuje pełnego archiwum. Cursor jest opaque,
sortowanie stabilne po `published_at + news_id` z jednoznacznym tiebreakerem.
Payload nie zawiera promptów, raw outputu modelu, quarantine, ukrytych facts ani
wewnętrznych targetów.

### Rekord wpisu

Od początku rozdzielamy trzy warstwy:

```text
entry
├── content
│   ├── news_id
│   ├── source / source_ref
│   ├── category
│   ├── title / summary / published_at
│   ├── truth_class
│   └── audience_scope
├── presentation
│   ├── weight: hero | large | medium | small
│   ├── state / accent_role
│   ├── asset_id / asset_family
│   ├── asset_focus_x / asset_focus_y
│   ├── asset_scale / asset_rotation
│   └── primary_stat / secondary_stat
└── action
    ├── kind: ACTIONABLE | STAMP_ONLY
    ├── action_type
    ├── action_target
    └── action_payload_ref
```

Dla przyszłego wpisu LLM można przewidzieć `publication_receipt_id`, ale w
135.4.1 jest legalny wyłącznie dla danych z canonical publication store.
Deterministyczne wpisy foundation mają jawne `source/source_ref` i nie udają
publikacji LLM.

Dozwolone stany prezentacyjne:

```text
normal trending hot warning critical new verified stale disabled
```

Nieznana wartość, audience albo action jest fail-closed: wpis zostaje odrzucony
z projekcji albo staje się kontrolowanym `STAMP_ONLY`; nigdy nie otrzymuje
domyślnej mutującej akcji.

## Źródła foundation w 135.4.1

News używa wyłącznie lekkich, istniejących projekcji lub deterministycznego
fixture developerskiego. Dopuszczalne domeny:

- produkty i aplikacje Googleplex;
- BlackNet world signals jako teaser, nie kopia całego feedu;
- Ghost Exchange summary/trend;
- konflikty i regiony z bounded map projection;
- podróże;
- klany wyłącznie w granicach istniejącego audience;
- storage/dysk przez lekki canonical projection;
- pakiety/pliki przez bounded summary;
- Cyberner przez istniejący channel/source projection;
- system, maintenance i integrity;
- bounded global stats.

Nie każda domena musi wejść w pierwszym patchu. Każdy rzeczywisty provider wymaga
potwierdzenia source of truth, audience i kosztu. Brak bezpiecznego lekkiego
providera oznacza brak karty, nie fallback do pełnego profilu.

## Deterministyczna selekcja i hierarchia

Home zachowuje dokładnie cztery poziomy geometrii:

```text
1 × HERO
2 × LARGE
3 × MEDIUM
pozostałe × SMALL
```

Przy mniejszej liczbie wpisów layout degraduje się bez duplikowania treści.
Ranking i weight są stabilne dla tego samego `state_version`. Kolejność
odpowiedzi async ani szerokość viewportu nie mogą wybierać innego hero.

HERO jest tylko presentation weight. Nie poszerza audience, truth ani action.

## Canonical action bridge

Przed dodaniem adaptera trzeba zinwentaryzować realne action keys i dispatchery
w `static/js/terminal.js`, BlackNet, GX, mapie i Cybernerze. Istniejąca nazwa ma
pierwszeństwo przed nowym action key.

| Karta | Dozwolony efekt |
| --- | --- |
| produkt/aplikacja | istniejący Googleplex product detail/catalog focus |
| BlackNet | otwarcie BlackNetu, opcjonalnie canonical filter |
| Ghost Exchange | otwarcie GX, opcjonalnie canonical category/item focus |
| konflikt/region | otwarcie mapy i canonical focus |
| teleport | wyłącznie istniejący dispatcher z pełnymi guardami |
| podróż | mapa/travel surface bez automatycznej podróży |
| Cyberner | istniejący channel/thread/source |
| storage/paczka/plik | istniejący detail lub właściwa surface |
| system/statystyka | domyślnie STAMP_ONLY |

Call chain kliknięcia:

```text
news card
→ action.kind == ACTIONABLE
→ allowlisted action_type + opaque/canonical target z backendu
→ istniejący frontend dispatcher
→ istniejące backend validation/guards
→ istniejąca surface lub gameplay flow
```

Zakazane są: auto-purchase/install, transakcja GX, auto-download, ręcznie
składany target, obejście kosztu/cooldownu/entitlementu/map guards, zmiana filtra
innego produktu przed kliknięciem i duplikowanie dispatchera.

## Audience, privacy i cache

Obsługiwane scopes:

```text
public
clan
owner
```

Projection odbywa się przed serializacją. Klient publiczny nie otrzymuje
owner/clan record nawet wtedy, gdy UI mógłby go ukryć.

Cache key zawiera co najmniej:

```text
viewer identity/session generation
audience revision
view
cursor
state_version lub provider revisions
```

Session cutover unieważnia stan poprzedniego viewera. Publiczne assety nie mogą
zostać przypadkowo związane z account generation, ale News snapshot pozostaje
authenticated i viewer-bound.

## Warstwa wizualna zgodna z `ggpl_news.png`

### Kompozycja

```text
WebDragons browser chrome
→ Googleplex masthead + account context
→ product navigation
→ istniejąca wyszukiwarka Googleplex
→ editorial News grid
→ global status strip
→ protocol/integrity footer
```

Wyszukiwarka pozostaje na górze. Globalne statystyki trafiają pod grid i nie
stają się drugim dashboardem.

Desktop korzysta z 12-kolumnowego CSS Grid i `grid-auto-flow: dense`. Nie wolno
zastąpić go równą tabelą kart ani flexowym dashboardem.

Orientacyjne proporcje:

```text
HERO   35–42% dominacji, min-height około 500 px
LARGE  22–28%, min-height około 260 px
MEDIUM 18–24%, min-height około 210 px
SMALL  12–18%, min-height około 170 px
```

Pierwszy viewport ma czytać się jak okładka: hero, dwie duże historie i widoczny
drugi poziom narracji.

### Karty, assety i tekst

Każda karta pokazuje category/eyebrow, jeden tytuł, asset lub lekką
wizualizację, jeden główny komunikat, najwyżej jeden secondary data block i
najwyżej jedno CTA tylko dla `ACTIONABLE`.

Dozwolone `asset_family`:

```text
scene character tool map clan package storage market network system stamp
```

Wiążące formaty:

| Rodzina | Format i proporcja |
| --- | --- |
| `scene` | WebP, `16:9`/`4:3`, minimum około `1200×700` |
| `character` | transparent WebP/PNG, pionowe `3:4`/`4:5` |
| `tool` | transparent PNG/WebP, `1:1`, `256–512 px` |
| `map` | SVG/HTML/Canvas, statycznie WebP; `4:3`/`1:1` |
| `clan` | SVG, fallback transparent PNG; `1:1` |
| `package` | transparent PNG/WebP; `1:1` lub izometria |
| `storage` | transparent PNG/WebP; paski i procenty jako CSS/HTML |
| `market` | SVG/Canvas/HTML, nigdy screenshot dynamicznego wykresu |
| `network` | SVG/PNG, zwykle `1:1`, opcjonalnie lekki CSS motion |
| `system` | minimalistyczny SVG |
| `stamp` | mały, lekki SVG |

Operacyjny manifest, lista brakujących grafik, cztery stany
`neutral/danger/victory/defence`, logo, ikonografia oraz deterministyczne grupy
rotacyjne są prowadzone w:

`static/images/googleplx/readme.md`.

Sprint nie może dodawać assetu poza tym kontraktem ani pozwalać modelowi na
wymyślanie ścieżki. Ollama może w przyszłości wybrać tylko `asset_ref` z
bounded `allowed_asset_refs`; backend pozostaje właścicielem walidacji i
fallbacku.

`asset_family` mówi, czym jest asset i jaki format jest legalny.
`presentation_weight` niezależnie określa ekspozycję:

```text
HERO   → cover / pełna powierzchnia
LARGE  → około 45–58% karty
MEDIUM → około 30–45% karty
SMALL  → około 64–120 px
```

Asset jest lokalny albo allowlisted. `asset_id` rozwiązuje code-owned registry
z metadanymi formatu, wymiarów, aspect ratio i przezroczystości; nie może być
arbitrary URL-em. Dynamiczne wykresy, statystyki, heatmapy i paski powstają z
danych w CSS/SVG/Canvas/HTML, a nie jako gotowe rastry.

Każdy asset obsługuje `asset_focus_x`, `asset_focus_y`, `asset_scale` i
`asset_rotation`, dzięki czemu jeden plik może mieć bezpieczny crop dla różnych
wag prezentacyjnych. Parametry są deterministyczne. Brak assetu, niedozwolony
format lub błędna proporcja daje stabilny placeholder bez zmiany geometrii.

Styl:

- czarna terminalowa baza CHAOS;
- editorial/comic: halftone, grunge, diagonalne cięcia, mocny crop;
- semantyczne akcenty: zielony normal, czerwony konflikt, pomarańczowy
  commerce/package, fioletowy underground/tool, cyan network/Cyberner, żółty
  warning;
- maksymalnie font mono i condensed display;
- 80–90% powierzchni pozostaje ciemne;
- bez pasteli, glassmorphismu, blur, emoji i SaaS rounded cards.

Limity presentation:

```text
hero title <= 72 znaków, summary <= 220
large title <= 54, summary <= 130
medium title <= 44, summary <= 90
small title <= 32, body <= 48
CTA <= 22
```

Read model dostarcza bezpieczny excerpt; klient nie zmienia canonical treści.

### Interakcja, motion i CSS

Hover, pointer cursor, comic slash i CTA występują wyłącznie dla `ACTIONABLE`.
`STAMP_ONLY` nie udaje przycisku. Motion jest krótkie, bez layout shift;
`prefers-reduced-motion` wyłącza dekoracje. Zakazane jest stałe glitchowanie,
mocny shake i miganie dużych powierzchni.

Preferowany namespace i podział:

```text
gp-home-* / gp-news-*
googleplex-news.tokens.css
googleplex-news.layout.css
googleplex-news.cards.css
googleplex-news.assets.css
googleplex-news.states.css
googleplex-news.motion.css
googleplex-news.responsive.css
```

Jeśli bundling wymaga mniejszej liczby plików, zachowujemy logiczne sekcje i
namespace. Nie dodajemy generycznych `.card`, `.title`, `.grid` do globalnego CSS.

## Responsive i accessibility

Breakpoints wynikają z szerokości okna WebDragons/containera:

```text
desktop >= 1200: 12 kolumn, pełne XL/L/M/S
tablet 768–1199: 8 kolumn, XL=8, L=4, M=4, S=2–4
mobile < 768: 1 kolumna, HERO → LARGE → MEDIUM → SMALL
```

Mobile ma jeden scroll contentu, zero horizontal overflow, zwarty masthead,
bezpieczne touch targets i zachowany scroll po powrocie. Wymagane są semantyczne
button/link tylko dla realnych actions, widoczny focus, klawiatura, poprawna
kolejność fokusu oraz ukrycie dekoracyjnych assetów przed accessibility tree.

## Loading, empty, stale i error

Home nie może zablokować wyszukiwarki ani katalogu:

- loading: lekki skeleton/scanline bez agresywnego shimmer;
- empty: 1–3 kontrolowane stamp cards, bez udawanych danych;
- stale: ostatni bezpieczny snapshot z jawnym stanem i bounded retry;
- error: systemowy panel bez stack trace, search/catalog nadal działa;
- błąd jednego providera nie usuwa całego Home, jeśli inne są poprawne.

Retry nie tworzy pętli requestów ani tasków LLM.

## Performance i zakaz ciężkiego profilu

Nowy read path nie korzysta z:

- `load_profile*`, `get_profile()`, `list_profiles()`;
- skanu wszystkich kont;
- parsowania `profile_json` per karta, provider lub odbiorca;
- pełnego profile read/write dla identity, audience, entitlementu lub walletu;
- cache pełnego profilu jako source of truth;
- synchronicznego ciężkiego agregowania przy każdym renderze.

Dozwolone są lekkie identity/audience projections, bounded stores, indeksowane
batch lookupy, gotowe summary i wersjonowane snapshots.

Fixture profilu >=35 MB musi wykazać:

```text
profile_full_read = 0
profile_full_write = 0
profile_bytes = 0
all_user_profile_scan = 0
per_recipient_profile_read = 0
ollama_calls = 0
llm_tasks_enqueued = 0
```

Telemetryka może zawierać czas, liczbę wpisów, provider status i cache hit/miss,
ale nie profile, pełne payloady ani ukryte facts.

## Plan implementacji

### Etap A — audit i kontrakty

1. Potwierdzić `openBrowser/loadCatalog/renderCatalog`.
2. Zinwentaryzować dispatchery Googleplex, BlackNet, GX, mapy, travel i Cybernera.
3. Dla każdego providera zapisać source of truth, audience i koszt.
4. Zatwierdzić schema snapshotu oraz action/asset allowlist.
5. Oddzielić kompozycję `ggpl_news.png` od nowych funkcji.

### Etap B — lekki backend read surface

1. Zbudować audience-projected, bounded read service.
2. Podłączyć wyłącznie providerów z lekkim store.
3. Dodać stabilny ranking, weights, cursor i state version.
4. Zabezpieczyć content/action/asset allowlisty i fail-closed projection.
5. Udowodnić brak Inbox/Outbox/Ollamy i pełnego profilu.

### Etap C — Home/Search i action bridge

1. Puste query kieruje do Home, nie pustego results ani ciężkiego profilu.
2. Katalog jest lazy-loaded przy pierwszym Search/Product Detail.
3. Niepuste query zachowuje katalog i instalację.
4. Powrót przywraca snapshot i scroll.
5. Actionable deleguje do istniejącego dispatchera.
6. Stamp-only pozostaje nieinteraktywne.

### Etap D — visual/CSS

1. Namespaced tokeny i 12-kolumnowy editorial grid.
2. Hero/large/medium/small i asset families.
3. Masthead, dolny status strip i protocol footer.
4. Loading/empty/stale/error.
5. Tablet/mobile z jednym scrollem i reduced motion.

### Etap E — regresja i manual

1. Read model, audience, cache i heavy-profile.
2. Tryby, dispatch i izolacja produktów.
3. Geometria, interakcje, responsive i accessibility.
4. Katalog/purchase/install/travel/GX/BlackNet regression.
5. Walidacja statyczna i manual serwerowy.

## Obowiązkowa macierz testów

### Read model i audience

- Home ma 12–24 wpisy; duży zbiór nie uruchamia pełnego skanu;
- stabilna kolejność, cursor i brak duplikatów;
- public/clan/owner otrzymują wyłącznie dozwolone wpisy;
- zmiana konta/generation nie wykorzystuje starego cache;
- nieznane audience/action/asset są fail-closed;
- brak promptu, raw outputu, quarantine i hidden facts;
- accepted/quarantined/rejected candidate nie pojawia się w Home;
- open/refresh: zero Ollama calls i zero LLM enqueue.

### Tryby i istniejący Googleplex

- pusty query → Home;
- pusty query nie wykonuje `GET /api/profile` ani eager catalog load;
- query → dotychczasowe wyniki;
- pierwsze query lazy-loaduje katalog najwyżej raz na okno/session state;
- clear → Home i zachowany scroll/snapshot;
- purchase/install/travel nadal przechodzi canonical flow;
- błąd Home nie blokuje search/catalog;
- malformed payload nie powoduje `catalog.filter is not a function`;
- Home/Search/Catalog/GX/BlackNet nie przenoszą filtrów ani tabs.

### Action safety

- product → detail bez auto-purchase;
- BlackNet teaser → BlackNet;
- GX teaser → GX bez transakcji;
- conflict → mapa/canonical focus;
- teleport → istniejący dispatcher i guards;
- Cyberner → istniejąca surface/channel;
- STAMP_ONLY → brak hover/button/request/mutacji;
- zmanipulowany action/target → fail-closed.

### Visual/CSS

- dokładnie cztery poziomy geometrii;
- pierwszy viewport ma hero, 2 large i drugi poziom narracji;
- global stats są pod gridem;
- CTA/hover tylko dla ACTIONABLE;
- stamp-only nie ma pointer cursor ani button semantics;
- focal point/rotation są deterministyczne;
- registry akceptuje wyłącznie formaty i proporcje przypisane do rodziny;
- nieznany asset/MIME/aspect ratio daje właściwy placeholder;
- dynamiczny market/storage/map state jest renderowany z danych, nie z rastra;
- ten sam `asset_id` działa w kilku presentation weights bez kopii pliku;
- długi tekst jest clampowany bez layout shift;
- brak assetu daje stabilny placeholder;
- desktop 12 kolumn, tablet 8, mobile 1;
- mobile: jeden scroll i zero horizontal overflow;
- reduced motion wyłącza dekoracje;
- focus/klawiatura obejmuje tylko realne akcje.

### Performance

- fixture >=35 MB: wszystkie heavy-profile metrics = 0;
- provider failure nie uruchamia full fallback scan;
- dwa równoległe loady nie tworzą lawiny requestów;
- reopen nie dubluje listenerów ani pollerów;
- niezmieniony `state_version` nie powoduje zbędnej pełnej przebudowy UI.

## Walidacja techniczna

- celowane testy News read model/provider/audience;
- Googleplex catalog, purchase, install i travel;
- BlackNet/GX/Googleplex state isolation;
- canonical action bridge do mapy i Cybernera;
- test 35 MB heavy-profile contract;
- frontend tests trybów, renderera i responsive;
- `py_compile` zmienionych modułów Python;
- `node --check` zmienionych plików JS;
- `git diff --check`.

## Manualna checklista serwerowa

1. Otwórz Googleplex bez query: Home jest widoczny.
2. Porównaj z `ggpl_news.png`: hero, 2 large, 3 medium, small, status strip,
   protocol footer.
3. Wyszukaj produkt: pojawiają się dotychczasowe wyniki.
4. Wyczyść query: wraca Home bez utraty pozycji.
5. Otwórz po jednej karcie Googleplex, BlackNet, GX, mapy i Cybernera.
6. Potwierdź, że stamp-only niczego nie uruchamia.
7. Potwierdź brak auto-purchase/install/sale/teleport.
8. Porównaj public/clan/owner na różnych kontach.
9. Zmień konto/session: brak kart poprzedniego viewera.
10. Desktop/tablet/mobile: jeden scroll, brak overflow.
11. Network/logi: open/refresh nie wywołuje Ollamy ani enqueue.
12. Istniejący purchase/install/travel nadal działa.

## Poza zakresem

- publikowanie accepted candidate — Sprint 135.5;
- bezpośredni odczyt Inbox/Outbox/quarantine/raw output;
- uruchamianie Ollamy z Home;
- kupowane narzędzie LLM — Sprint 135.4.2;
- dowolne prompty użytkownika;
- nowe mechaniki ekonomii, konfliktu, teleportu, klanów, inventory lub chat;
- przebudowa BlackNet, GX, mapy albo Cybernera;
- deploy, restart PM2, produkcyjne migracje i mutacje.

## Exit gate

Status `SPRINT 135.4.1 — READY FOR SERVER VALIDATION` jest dozwolony tylko gdy:

```text
EMPTY QUERY → HOME/NEWS
EXISTING SEARCH/PURCHASE/INSTALL → UNCHANGED
ACTIONABLE → CANONICAL DISPATCHER
STAMP_ONLY → ZERO ACTION
PUBLIC/CLAN/OWNER → BACKEND-PROJECTED
HEAVY PROFILE → ZERO
HOME OPEN/REFRESH → ZERO OLLAMA / ZERO LLM ENQUEUE
ACCEPTED CANDIDATE WITHOUT PUBLICATION RECEIPT → NOT VISIBLE
DESKTOP/TABLET/MOBILE → EDITORIAL HIERARCHY + ONE SCROLL
```

Po manualnym potwierdzeniu:

```text
SPRINT 135.4.1 — COMPLETE / READY FOR SPRINT 135.4.2
```
