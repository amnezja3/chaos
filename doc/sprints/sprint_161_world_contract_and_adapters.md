# Sprint 161 — przywrócenie skanera POI przez alternatywnych dostawców

Data planu: 20.10.2026. Aktualizacja: 23.10.2026.
Status: **W REALIZACJI — komponenty offline, bez pilota i aktywacji produkcji**.
Wyniki i granice: [dowody 161](../audits/sprint_161_evidence.md).
Źródło: [koncepcja World Discovery](../prototypes/poi/CHAOS_WORLD_DISCOVERY_ENGINE_KONCEPCJA_BEZ_NUMERU.md).
Podział zatwierdzony do opracowania przez operatora: 161–163. To zastępuje brak
numeracji w koncepcji, ale nie stanowi zgody na implementację ani działania produkcyjne.
Kolejne etapy: [162](sprint_162_world_repository_local_read.md), [163](sprint_163_world_discovery_operations_rollout.md).

Aktualizacja priorytetów według decyzji operatora z 20.10.2026:
**najpierw przywracamy działający skaner, potem budujemy pamięć świata.**
Pierwotna aktualizacja obejmowała wyłącznie plan. Operator 23.10.2026 zlecił
rozpoczęcie implementacji do momentu wymagającego jego udziału. Nie ponawiamy
prób DE/VK. Pilot API, push/deploy i aktywacja wymagają wskazanego zakresu;
potwierdzenie kont Free nie jest jeszcze wykonaniem ani odbiorem próby.

## Cel i wynik sprintu

Przywrócić rzeczywiste skanowanie POI w CHAOS z wykorzystaniem MapLark lub
Geoapify, wybierając pierwszego dostawcę, który udowodni zgodność z wymaganym
profilem i zostanie dopuszczony do użycia. Minimalna kompletna ścieżka:

**CHAOS Scanner → Provider Adapter → Normalizacja → Istniejący Gameplay.**

Kontrakt i adaptery nadal stanowią fundament World Discovery, ale sprint nie
kończy się wyłącznie testami offline. Obejmuje plan małego pilota i odbioru
gracza w 161.6, po przejściu osobnych bramek technicznych i produkcyjnych.
Etapy A/B koncepcji oraz ograniczony pilot ścieżki live z etapu G trafiają do 161.
Nie czekamy na ukończenie wszystkich adapterów, repozytorium ani workera,
aby zweryfikować jedną zgodną ścieżkę.

Nie wymagamy trwałego repozytorium regionów, AREA_REUSABLE, union coverage,
szerokiego prefetchu ani odkrywania sąsiadów. Wykorzystujemy koordynację i
exact-cache 158 (tylko w dozwolonym zakresie przechowywania), MASA 159 i registry
160. 160 pozostaje częściowo wdrożony, bez pełnego PASS; ten plan nie wznawia
jego rollout’u world/wide/monitor. Pilot alternatywnego źródła wymaga osobnej zgody.

Artefakty docelowe: kontrakt `WorldObject`/`ProviderBatch`/`CoverageEvidence`,
wersjonowany profil gameplayu, capability matrix, fixture manifest, adaptery
MapLark i Geoapify, integracja wyboru źródła, raport parity oraz dowody pilota
jednego zatwierdzonego dostawcy. Nazwy nowych modeli są projektem, nie stanem kodu.

## Kolejność dostarczania

1. **161.0–161.1:** ustalić wymagany kontrakt z rzeczywistych konsumentów danych.
2. **161.2:** zweryfikować dokumentację obu kandydatów, zdolności, prawa i koszt;
   wybrać najkrótszą zgodną ścieżkę, bez domniemania pełności któregokolwiek API.
3. **161.3–161.4 dla pierwszego źródła:** adapter, bezpieczny transport, normalizacja
   i eksport do niezmienionego gameplayu; testy offline i PASS CONTRACT.
4. **161.5–161.6:** minimalna konfiguracja w istniejącym registry, akceptacja
   zakresu/budżetu i mały pilot: PASS PROVIDER → PASS LIVE SCANNER.
5. Dokończyć planowany drugi adapter i jego macierz ograniczeń; jego brak pełnego
   profilu nie blokuje odbioru pierwszego. Nie oznaczać niewykonanego adaptera
   jako ukończonego ani częściowego profilu jako pełnego zamiennika.

Projektowanie obu adapterów należy do 161. Wykonanie pełnej ścieżki pierwszego
źródła ma pierwszeństwo przed rozbudową wspólnej platformy. Jeśli żaden kandydat
nie pokryje wymagań, raportujemy konkretny blocker, zamiast zmieniać gameplay.

## 161.0 — baza zależności i przejęcie otwartych dowodów 160

1. Sprawdzić stan HEAD, schemat i rzeczywiste użycie modułów z macierzy poniżej.
2. Utrwalić fixtures i kontrakt skanera, bez zmiany limitu 60, kolejności i RNG.
3. Uzgodnić rejestr dowodów 160 → 161/162/163. Przeniesienie zadania nie oznacza PASS.
4. Oddzielić stan kodu, testy lokalne, kod pobrany na VPS i funkcje aktywne.

| Obecna zdolność | Ponowne użycie | Brak do wykonania | Dowód / właściciel |
| --- | --- | --- | --- |
| `poiFetchClass.py`: fasada, kategoryzacja, dedup | Zachować publiczne metody | Pełna lista konsumentów tagów i eksport kontraktu | 161.1/161.4 |
| `service.py`: deadline, proces potomny, retry | Jedyny wspólny budżet pozyskiwania | Minimalny live routing, budżet stron i kosztów | 161.3/161.5; rozszerzenia 162.3 |
| `repository.py`: SQLite, lease, circuit, exact cache | Wspólna koordynacja bez drugiego limitera | Rezerwacja budżetu potrzebna do pilota; priorytet wobec tła dopiero później | 161.5 → 163.1 |
| `world.py`: snapshot/member/coverage | Rozszerzenie istniejącej bazy POI | Obiekt kanoniczny, provenance pól, capability i indeks | 162.1 |
| `geometry.py`: konserwatywne around i kontrolowane fixtures | Punkt odniesienia, exact fallback | Szersza domena, pełność obszaru i zgodny union | 162.2 |
| `providers.py`: revision, scopes, decyzje | Jeden registry i audit trail | Typ adaptera, secret refs, capabilities i live/cache scope | 161.2/161.5; trwały zapis 162 |
| `secure_transport.py`: public DNS, pinning, TLS | Zachować zabezpieczenia | Bezpieczne GET/POST i ścieżki inne niż interpreter | 161.3 przed pierwszym live |
| Admin 160 + health + monitor CLI | Istniejąca autoryzacja, formularze, historia | Minimalny wybór/config źródła teraz; agregaty/coverage/queue później | 161.5 → 163.2/163.3 |
| MASA 159 i GhostLab | Zachować kontrakt | Regresja już dla pilota live, nie dopiero dla world | 161.4/161.6; rozszerzenia 162/163 |

Bramka: nie powstaje drugi fetcher, registry ani osobna konkurencyjna baza.
Wstępny odczyt kodu wykonano przy planowaniu; pełny audyt wszystkich konsumentów
tagów pozostaje zadaniem 161.1, a nie deklaracją ukończoną przez tę tabelę.

## 161.1 — kanoniczny profil i granica gameplayu

Profil pierwszego skanu obejmuje POI obecnego skanera. Aktualizacja 23.10.2026
rozszerza kontrakt świata o niezależne drogi, cieki, wody powierzchniowe,
wybrzeża i obszary ląd–woda. Ich pobieranie nie blokuje pilota POI.
Budynki nie otrzymują osobnego profilu w tym rozszerzeniu.

| Pole / reguła | Potwierdzone użycie w kodzie | Plan kontraktu |
| --- | --- | --- |
| `lat`, `lon`, center | `_categorize_data`, zasięg i generowanie scen w run.py | Oddzielić punkt prezentacji od geometrii selekcji; WGS84 i finite |
| `osm_type`, `osm_id`, `node_id` | Fasada; ID wpływa także na kamery i attached ATM | Zachować prawdziwe typ/ID; brak ID nie może stać się zmyślonym OSM ID |
| `name` | Fasada i wynik markera | Opcjonalna nazwa źródłowa, bez wymyślonej lokalizacji |
| `shop`, `amenity`, `office`, `healthcare` | Filtry i priorytety ikon | Wersjonowany mapping, zachowanie kolejności reguł |
| `atm`, `man_made` | Bankomaty, prawdziwe kamery i generowane sceny | `unknown` nie oznacza false; brak kamery w odpowiedzi nie jest dowodem jej braku |
| `internet_access` | `assign_icon_and_type` | Zachować jako pole wejściowe, mimo że nie jest osobnym filtrem zapytania |
| Kontekst miejscowości i tożsamość kamery | `infer_scan_location`, `camera_marker`, dalsze markery | Prześledzić implementacje/importy i wszystkie odczyty tagów przed ich minimalizacją |
| Kolejność i limit | Nodes → ways → relations, pierwsza pasująca kategoria, limit kategorii i globalny | Zachować ordinal/porządek eksportu, nie sortować po ID bez testu |
| Deduplikacja | `_get_all`: `(lat, lon)` | Repo deduplikuje tożsamość; eksport zachowuje dotychczasową deduplikację gameplayu |

Specyfikacja modelu ma zawierać: schema/mapping/filter/geometry version,
world_object_id, zewnętrzne referencje, oryginalne potrzebne tagi, klasyfikację,
atrybuty trójwartościowe, geometrię i jej jakość, opcjonalny location z metodą,
provider/snapshot/license/attribution, fetched_at/source_dataset_at/ingested_at.

OSM: klucz `osm:{type}:{id}`. Bez potwierdzonego OSM ID: odrębny namespace
`provider:{provider_id}:{external_id}`. Nie scalać po samej nazwie i odległości.
Brak stabilnego ID lub pełnej semantyki wyklucza eksport do profilu zależnego od
OSM ID; nie wstrzykiwać stringów do miejsc wymagających liczbowego OSM ID.
Ikony, NPC, kamery proceduralne, użytkownicy, koszty i odkrycia nie trafiają do repo świata.

Bramka: wszystkie wymagane pola mają wskazanego konsumenta/test; redukcja tagów
następuje dopiero po tym dowodzie. Mutacje markera nie zmieniają źródłowego obiektu.

### 161.1-G — kontrakt pełnych warstw geograficznych (23.10.2026)

- Zdefiniować profile `poi`, `roads` (`highway`), `waterways` (`waterway`),
  `inland_water` (`natural=water`), `coastline` (`natural=coastline`), `land_water`.
  Profile są niezależne od kategorii ikon. Obiekt może mieć kilka memberships;
  tag nie przesądza automatycznie, czy zamknięty way jest powierzchnią.
- Kontrakt `Point`, `LineString`, `Polygon`, `MultiPolygon`: WGS84 lon/lat,
  skończone współrzędne, linie z co najmniej dwoma punktami, zamknięte pierścienie,
  otwory, rozłączne powierzchnie, topologia, bounds i zakres wsparcia antymeridianu.
  Oddzielić geometrie źródłowe, clipping i uproszczenie do prezentacji.
  Punkt markera nie zastępuje przebiegu drogi ani granicy jeziora.
- Tożsamość źródłowa i części geometrii, geometry/profile/mapping version,
  tags, source_dataset_at, license/attribution i lineage produktu pochodnego.
  Dla MultiLineString/GeometryCollection: jawny, testowany podział z zachowaniem
  rodzica albo UNSUPPORTED; żadnego cichego gubienia części.
- `CoverageEvidence` osobno per warstwa/obszar/wersja danych i operacja selekcji.
  Pełność obiektów w wycinku różni się od pełności ich geometrii poza wycinkiem.
  Brak danych geograficznych nie zmienia PASS profilu POI ani nie uruchamia MASA POI.
- Kontrakt coastline zachowuje kierunek i końce fragmentów. `land_water` jest
  osobnym produktem: legalny regionalny dataset lub przetwarzanie ze zweryfikowaną
  topologią, wyspami/otworami i kontekstem spoza regionu. Nie domykać linii przez
  bbox. Luka daje UNKNOWN/PARTIAL. Limit kontekstu chroni przed importem planety.
- Rozszerzyć macierz obu dostawców o każdy profil, typ geometrii, clipping,
  kompletność, prawa trwałego zapisu i koszt. Wszystkie nowe zdolności początkowo
  NIEZWERYFIKOWANE. API Places nie jest domyślnie źródłem dróg czy oceanów;
  źródło geografii może być inne niż dostawca POI.

Odbiór G01–G04: walidacja czterech typów i odrzucenie uszkodzonych geometrii;
niezależność profili i tożsamości części; fixture jeziora z wyspą, rzeki/drogi
przecinającej granicę, wybrzeża z luką i antymeridianu; lineage i brak fałszywego
morza z otwartego coastline. Kontrakt musi określić zachowanie wspierane i odmowę
dla przypadków nieobsługiwanych. G01–G04 wymagane do zamknięcia kontraktu sprintu,
nie do wykonania pierwszego pilota skanera. Implementacja storage w 162, tła w 163.

## 161.2 — kontrakt adaptera, capabilities i zakresy

Przed implementacją każdego adaptera sprawdzić aktualną oficjalną dokumentację
API i warunki właściwego planu: wersję endpointu, autoryzację, format odpowiedzi,
identyfikatory, tagi, geometrię, znaczenie selekcji przestrzennej, sortowanie,
paginację, limity odpowiedzi/requestów, koszty i dozwolone użycie live/cache.
Utrwalić datę, źródła oraz niewyjaśnione kwestie. Sama możliwość pobrania danych
nie jest dowodem kompatybilności ani zgody na produkcyjne wykorzystanie.

Ustalić interfejs capabilities → estimate → fetch plan → normalize → completeness.
Plan pobrania niesie obszar, profile, paginację, revision decyzji i wspólny budżet;
batch niesie źródłową odpowiedź, kompletność stron, truncation, koszt i provenance.
Normalizacja nie przyznaje automatycznie COMPLETE ani prawa do przechowywania.

Mapowanie do registry 160: `live_scan` → istniejące `normal_scan`,
`wide_fetch` → istniejące `wide_fetch`. Istniejącego `storage` nie uznawać
automatycznie za bezterminowy `permanent_store`. Rozdzielić retencję cache,
trwały zapis, refresh, nowe background_fill i ewentualną redystrybucję.
Migracja decyzji zachowuje wyłącznie udokumentowany zakres; nowe prawa domyślnie OFF.

| Adapter | Punkt wyjścia z koncepcji, nie nowe potwierdzenie dostawcy | Co trzeba wykazać przed live |
| --- | --- | --- |
| Overpass | Istniejący JSON nwr/out center i fixture pełnej closure | Exact kontra reusable; remark/partial; brakujące members; ograniczenia selektora 160 |
| MapLark | Kandydat GeoJSON/OSM Features; deklarowane wersje v3/v2 wymagają sprawdzenia | Typ i ID, tagi, pełna geometria, znaczenie radius/bbox, truncation i zakończenie stron |
| Geoapify | Kandydat Places z własnymi kategoriami | Mapping, obecność OSM ID, rzeczywista geometria, paginacja, brak obsługiwanych klas |

Na etapie tego planu nie zweryfikowano nowych zewnętrznych dokumentacji, cen ani
warunków kont. Nie przypisano źródłom nowych uprawnień. Przed implementacją
adaptera utrwalić wersję oficjalnej dokumentacji i manifest próbek; próbki
syntetyczne oznaczyć jako syntetyczne, nie dowód realnej usługi. Dokumentacja
może być sprawdzona bez odpytywania przeciążonych interpreterów. Brak materiału
blokuje certyfikację konkretnego adaptera, nie prace nad kontraktem ogólnym.

### 161.2-K — koszt pojedynczego skanu (23.10.2026)

Dane wejściowe operatora: MapLark 30 000 kredytów/miesiąc; Geoapify 3 000/dzień,
5 req/s i ograniczenie opisane jako 10 km. Przed konfiguracją potwierdzić plan,
endpoint, koszt stron/estimate/błędów, okres i strefę resetu, rate limit oraz
znaczenie 10 km. Nie zmieniać promienia gameplayu i nie zakładać kredyt = request.

Kontrakt kosztu: provider/account ref bez sekretu, jednostka, cennik/version,
operation/request ID, okres rozliczeniowy, estimated/reserved/observed cost,
źródło i czas obserwacji. Raportowane zużycie dostawcy i licznik CHAOS są różne;
brak raportu = unknown, nie zero. W 161 wykorzystać istniejące limity i zapewnić
minimalną rezerwację kosztu całej operacji/stron pod współdzielonym budżetem,
bez czekania na panel 163. Timeout nie zwalnia automatycznie całej rezerwacji,
jeśli nie wiadomo, czy dostawca naliczył opłatę.

Przed pilotem dowód: współbieżne procesy nie przekraczają limitu, brak budżetu
nie uruchamia HTTP, strony/fallback nie resetują kosztu, unknown cena blokuje
płatne pobranie. Zweryfikowane limity i fixture rachunku skanu przekazać do 163;
nie deklarować automatycznej synchronizacji salda bez dostępnego API.

### Plan MapLark — wykonanie

1. Potwierdzić rzeczywistą wersję OSM Features API; nie mieszać przykładów v2/v3.
2. Zmapować pełny profil CHAOS na parametry API; sprawdzić definicję radius/bbox
   i selekcję way/relation, nie tylko obecność GeoJSON w odpowiedzi.
3. Opracować dekoder ID i typu OSM, wszystkich wymaganych tagów, geometrii,
   nazwy oraz dostępnego kontekstu administracyjnego. Braki zachować jawnie.
4. Ustalić zakończenie danych: paginacja, has-more, ograniczenia planu, obcięcia
   geometrii i result-too-large. Limit 60 markerów nie ogranicza pobrania do 60 POI.
5. Normalizować do WorldObject, następnie eksportować do formatu obsługiwanego
   przez istniejący POIFetcher. Nie przebudowywać run.py pod dostawcę.
6. Dowieść zgodności na zapisanych odpowiedziach i kontrolowanym snapshotcie;
   następnie dopuścić jeden pilot dopiero po akceptacji źródła i budżetu.

### Plan Geoapify Places

1. Zweryfikować kontrakt Places: kategorie, filtry przestrzenne, limit/offset,
   identyfikatory, geometrię, ranking/sortowanie i zasady kompletności.
2. Przygotować jawne mapowanie kategorii i pól do profilu CHAOS. Własna kategoria
   dostawcy nie staje się automatycznie oryginalnym tagiem OSM.
3. Zachować pochodzenie mapowania, unknown, prawdziwe ID i administracyjny
   kontekst dostępny w odpowiedzi. Brak OSM ID nie uprawnia do jego generowania.
4. Pobierać wszystkie wymagane strony w jednym budżecie; przerwana paginacja
   lub ranking bez gwarancji kompletności wykluczają pełny wynik skanera.
5. Wyeksportować tylko udowodniony profil do istniejącej fasady. Jeśli brakuje
   kamer, bankomatów, tagów lub selekcji nwr, nie używać jako pełnego fallbacku.
6. Osobno odebrać adapter offline i jego dopuszczalny profil. Nie czekać na
   Geoapify przed pilotem MapLark, jeśli tylko MapLark spełni wszystkie wymagania,
   ani nie zakładać z góry, że MapLark je spełni.

### Macierz zgodności kategorii do wypełnienia dowodami

Poniższe statusy są **NIEZWERYFIKOWANE**, nie deklarują funkcji usług. Przed
pilotem każda komórka otrzymuje SUPPORTED / PARTIAL / UNSUPPORTED / UNKNOWN
z odnośnikiem do dokumentacji i fixture. UNKNOWN nie dopuszcza pełnego profilu.

| Warstwa wymagana przez CHAOS | MapLark | Geoapify | Dowód wymagany |
| --- | --- | --- | --- |
| `shop=*`, podtypy i nazwa | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Mapping i zachowanie scen sklepowych |
| `amenity=*`, bank/usługi/parking itd. | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Wszystkie używane priorytety ikon, nie wyłącznie gastronomia |
| `office=*`, `healthcare=*` | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Pokrycie kategorii i wymaganych podtypów |
| `amenity=atm`, `atm=yes` | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Osobny ATM kontra atrybut rodzica; unknown nie jest false |
| `man_made=surveillance` | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Prawdziwe kamery; brak warstwy nie oznacza pustego terenu |
| `internet_access` i pozostałe odczyty tagów | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Pełna lista z 161.1, bez cichej redukcji |
| Typ/ID, selekcja nwr i punkt markera | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Stabilna tożsamość i równoważność skanu |
| Administracyjna lokalizacja | NIEZWERYFIKOWANE | NIEZWERYFIKOWANE | Opcjonalna, z pochodzeniem; brak bez zgadywania |

## 161.3 — minimalna integracja live, adaptery i bezpieczeństwo transportu

Overpass jako adapter referencyjny, MapLark i Geoapify jako kandydaci z jawnymi
UNSUPPORTED/UNKNOWN per warstwa. Sam centroid nie daje AREA_REUSABLE.
Brak kamer lub ATM w możliwościach API nie może dawać kompletności całego profilu.
HTTP 200, wynik równy limitowi, has_more, zgubiona strona lub pętla cursorów
nie mogą dawać COMPLETE. Sprzeczne dane zachowują lineage, starsze nie wygrywają
samą datą pobrania, brak w częściowym batchu nie usuwa obiektu.

Obecny transport dopuszcza tylko ścieżki `/api/interpreter`. Zaprojektować
wersjonowane allowlisty endpointów i metod per adapter zamiast znoszenia kontroli.
Wspólne DNS/public-IP/TLS/redirect/proxy, limit bytes/elements/czasu; parametry
zapytania tylko z adaptera. Sekrety przez istniejący wzorzec serwerowy,
bez kluczy w fixture, logu, URL raportu i przeglądarce. Brak dowolnego URL od gracza.

Zachować publiczny interfejs POIFetcher, szczególnie `get_all()`, oraz mechanikę
w run.py. Warstwa poniżej fasady wybiera adapter, normalizuje i eksportuje wynik;
nie tworzymy osobnego gameplayu MapLark/Geoapify. Zachować `extra_retries`,
`extra_timeout`, `still_active`, generację tokenu i przerwanie skanu GhostLab.

Paginacja, estimate i fallback dzielą istniejący deadline, single-flight, globalny
slot, circuit oraz limit requestów i kosztu. Jedno kontrolowane pobranie w pilocie
oznacza jedną ograniczoną operację; jeśli API wymaga stron, ich maksymalna liczba
i koszt muszą być wcześniej zatwierdzone. Nie uruchamiać kilku pełnych budżetów.
Single-flight/cache key musi odróżniać profil, geometrię, wersję adaptera i
semantykę odpowiedzi; nie używać odpowiedzi niezgodnego dostawcy pod starym kluczem.
Jeśli plan zabrania cache, ścieżka musi respektować zakaz albo pozostaje wyłączona.

Warunkiem live jest zgodność **selekcji bieżącego skanu**, nawet gdy nie budujemy
jeszcze AREA_REUSABLE dla sąsiadów. Zwrócone centroidy wystarczą tylko wtedy,
gdy dostawca dowodzi równoważnego wyboru obiektów; nie wolno usuwać wymogu nwr
pod pretekstem odłożenia repozytorium do 162.

## 161.4 — testy i odbiór offline

| ID | Oczekiwany dowód |
| --- | --- |
| C01 | Wszystkie wymagane pola, unknown/false, bank+ATM, surveillance, internet_access, brak nazwy |
| C02 | OSM type+ID, namespace, konflikt i brak automatycznego merge bliskich obiektów |
| C03 | Kategorie/limity/porządek/dedup zgodne z fasadą na wspólnym snapshotcie |
| C04 | Obcięcie, brak strony, 429/5xx, remark, brak geometrii nie dają pełności |
| C05 | Reprezentatywny punkt nie zastępuje geometrii around |
| C06 | Redakcja sekretów, nieprawidłowe endpointy, prywatny DNS, redirect i zmiana revision |
| C07 | Eksport przez get_all: kamery/ATM/sklepy/NPC i marked targets zgodne z istniejącym gameplayem przy kontrolowanym RNG |
| C08 | GhostLab, anulowanie, koszty, dwa konta, single-flight i wspólny budżet stron/prób |
| C09 | Dotychczasowe MASA: brak approval lub błąd adaptera nie udaje awarii świata |

Dowody zapisać docelowo w `doc/audits/sprint_161_evidence.md` po wykonaniu.
**PASS CONTRACT** wymaga C01–C09 i jawnej listy niecertyfikowanych capabilities
dla ocenianego adaptera/profilu. Testy na zapisanych odpowiedziach muszą mieć
manifest pochodzenia; syntetyczne fixture nie dowodzą działania realnego API.
Nie oznacza to TECHNICAL_OK na VPS ani zgody na użycie płatnej usługi.

## 161.5 — registry i konfiguracja pierwszego dostawcy

Rozszerzyć istniejący panel 160 tylko o niezbędny wybór typu adaptera, profilu,
zatwierdzonego endpointu, secret ref i budżetu. Administrator wybiera aktywnego
dostawcę i zmienia konfigurację bez edycji kodu. Wykorzystać revision, audit,
RBAC i CSRF; zmiana dociera do czterech workerów przed nowym wywołaniem.

TECHNICAL_OK, zatwierdzenie warunków/scope i enabled są osobnymi decyzjami.
Udany test nie włącza źródła. Zmiana URL lub kontraktu unieważnia stosowne dowody.
Brak pełnej capability blokuje wybór jako zamiennika profilu CHAOS.
Nie usuwać walidacji endpointów ani wprowadzać kluczy API do logów i przeglądarki.

Na pilot wymagane: normal_scan, zasady użycia exact-cache, liczba requestów/stron,
koszt i limit czasu. Nie wymagamy uprawnień permanent_store/background_fill,
ponieważ world ingest/read, wide i background pozostają OFF.
Minimalny rollback wyboru źródła i propagację sprawdzić przed pilotem 161;
rozbudowany panel kosztów/coverage/kolejki nadal należy do 163.

## 161.6 — mały pilot i trzy poziomy akceptacji

Rzeczywiste API dopiero po zgodzie operatora na warunki dostawcy, budżet i pilot.
Brak potwierdzenia oznacza pozostanie offline. Nie wysyłamy obecnie żadnych prób.

Plan jednego przebiegu:

1. Jeden zatwierdzony dostawca, jeden jawny profil obejmujący wymagany skaner,
   jedna lokalizacja i izolowane konto testowe.
2. Jedno kontrolowane pobranie w zatwierdzonym budżecie; bez prefetchu, tła
   i automatycznej serii prób. Zachować dowód kompletności i atrybucji.
3. Normalizacja oraz eksport odpowiedzi przez POIFetcher.
4. Wykonanie rzeczywistego skanu gracza przez istniejącą ścieżkę gry.
5. Odbiór markerów, prawdziwych i proceduralnych kamer, ATM, sklepów, NPC,
   GhostLab, kosztów, oznaczonych celów, kolejności i limitu wyników.
6. Zapis raportu; osobna decyzja o dalszym użyciu live. Gdy lokalizacja nie
   zawiera danego przypadku, nie raportować go jako sprawdzony produkcyjnie.
   Pozostaje dowód offline i jawna luka do celowanego odbioru.

| Poziom | Znaczenie | Czego nie oznacza |
| --- | --- | --- |
| **PASS CONTRACT** | Kontrakt, normalizacja, eksport i zabezpieczenia przechodzą testy offline dla wskazanej wersji adaptera/profilu | Dostępności API, akceptacji warunków ani działania gry na produkcji |
| **PASS PROVIDER** | Zatwierdzony dostawca zwraca kompletne dane wymagane przez wybrany profil, z poprawną selekcją, tożsamością i dozwolonym użyciem | Odbioru gameplayu lub trwałego repozytorium |
| **PASS LIVE SCANNER** | Gracz wykonuje rzeczywisty skan CHAOS, a wynik i skutki są poprawne bez regresji wymaganych mechanik | Gotowości world read/background ani stabilności globalnej |

Każdy PASS wskazuje dostawcę, wersję adaptera, profil, dowody, datę i ograniczenia.
PASS PROVIDER w wąskim profilu usług nie uprawnia do pełnego PASS LIVE SCANNER.
Pełny odbiór skanera wymaga całego bieżącego profilu CHAOS i udowodnionej
zgodności wymaganych mechanik; ograniczony sukces jednej kategorii jest wynikiem
cząstkowym. Braki oznaczamy jawnie, nie redukujemy kontraktu po nieudanym teście.

Pilot obejmuje Playwright MCP PL/EN desktop/mobile na izolowanym środowisku
przed produkcją: wybór dostawcy, błędy przy przyciskach, skan i MASA; realny odbiór
VPS zapisujemy osobno. Nie wykonujemy testów UI ani prób API w ramach tej aktualizacji planu.

Warunki przerwania: partial jako pełny wynik, zmyślone ID/tagi, regresja kosztów
lub markerów, ujawnienie sekretu, przekroczenie zatwierdzonego budżetu.
Rollback wyłącza nowe wywołania wybranego adaptera i przywraca wcześniej sprawdzoną
konfigurację, bez kasowania danych i resetowania lease. Powrót do DE/LZ4 nie
gwarantuje przywrócenia dostępności. Procedurę rollbacku przećwiczyć przed ON.

## Krótka analiza wykonalności i najkrótsza ścieżka

| Pytanie | Stan / działanie |
| --- | --- |
| Co już mamy? | Fasada POIFetcher, pipeline gameplayu, cache/lease/circuit/deadline 158, MASA 159, registry/admin/audit i zabezpieczony transport 160 |
| Co wykorzystujemy bez zmiany zasad? | Autoryzacja i gameplay run.py, kategoryzacja/dedup/limit 60, GhostLab, komunikacja MASA, wspólny mechanizm koordynacji |
| Co trzeba dopisać? | Kontrakt i eksport, adaptery/mapowania, walidacja kompletności, transport udokumentowanych endpointów, secret refs, routing i minimalna konfiguracja panelu |
| Co nie blokuje pierwszego skanu? | Trwałe regiony, indeks przestrzenny świata, union obszarów, worker, discovery queue i dashboard pokrycia |
| Co może blokować? | Brak tagów/OSM ID/geometrii, niezgodna selekcja lub kolejność, niepełna paginacja, niejasne prawa live/cache, koszt/kwoty albo niedostępność źródła |

Pierwszy działający skan planujemy **w 161, po jednej kompletnej ścieżce adaptera**,
a nie po 162/163 ani po ukończeniu całej platformy wszystkich dostawców.
Najkrótszy ciąg: audyt pól → zweryfikowany kontrakt API → adapter i eksport →
offline parity → konfiguracja/akceptacja → jedno pobranie i skan gracza.
Na etapie planu nie ma uczciwej liczby godzin/dni: nie potwierdzono jeszcze
dokumentacji, danych i warunków wybranego planu. Po 161.2 oszacować pozostałą
pracę na podstawie rzeczywistych luk, oddzielając czas implementacji od oczekiwania
na akceptację/klucz. Nie obiecywać szybkiego live kosztem brakujących kategorii.

## Decyzje i wyjście

Przed implementacją: domknąć listę pól, manifest dokumentacji/fixtures i semantykę
adapterów. Przed ruchem realnym **w 161.6**: wybrać źródło, plan, secret refs,
prawa, budżet i uzyskać zgodę na pilot. Przed ON potwierdzić wymagane atrybucje,
zasady cache i obowiązki dotyczące przekazywanego obszaru zapytania; nie deklarować
niepotwierdzonych umów ani praw do trwałego harvestingu.
Nie wymagamy zakupu planu do samego projektu i syntetycznych testów offline.
Nie zmieniamy polityki wieku, Identity Gateway ani mechaniki run.py.

162 nadal odpowiada za trwałe repozytorium i lokalne skanowanie; 163 za kolejkę,
rozbudowany panel operacyjny i kontrolowany rollout świata/tła. Przekazujemy
im te same adaptery i kontrakt bez osobnej implementacji fetchera.
Niniejsza decyzja zmienia wcześniejsze odesłanie pierwszego live dopiero do 163:
pilot przywrócenia skanera jest w 161, a pilot pamięci świata pozostaje późniejszy.
Nie przenosi to PASS 160 ani nie uruchamia jego wyłączonych funkcji.

Aktualizacja 23.10.2026 obejmuje koncepcję i plany 161–163; rozszerza zakres
kontraktu geograficznego bez odsuwania pierwszego pilota POI.
Implementację rozpoczęto na późniejsze zlecenie operatora; jej aktualny stan
opisuje raport dowodów. Nie wykonano pusha/deploya ani zmian flag produkcji.
