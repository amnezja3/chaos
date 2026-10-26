# Sprint 163.5 — domknięcie pamięci świata i integracji źródeł

Data: 26.10.2026. Status: **W REALIZACJI — pierwszy pakiet exact local-read lokalnie PASS; odbiór VPS otwarty**.

Postęp: [mapa wymagań i dowodów](../audits/sprint_163_5_traceability.md).
Przygotowany [odbiór pierwszego pakietu](../runbooks/world_global_exact_163_5.md).
Nie uruchomiono trybu globalnego na produkcji; pozostałe etapy nadal otwarte.

Drugi pakiet lokalny: regionalny Overpass pod aktywnym routerem i wspólny zapis
popytu skanera — 116 testów PASS. [Instrukcja](../runbooks/world_regional_read_163_5.md).
Regionalne MapLark/Geoapify, ruch bez skanu i halo pozostają do wykonania.

Dyspozycja operatora: zebrać w 163.5 pozostały zakres 161–163 i wykonać go
etapami: lokalny kod → wdrożenie → zbiorczy test → korekta → odbiór.
To kontynuacja zobowiązań 161–163, nie przeniesienie ich poza uzgodniony zakres.
Podstawa: [audyt rzeczywistego stanu](../audits/world_scope_reconciliation_161_163_20261026.md).
Dotychczasowy [odbiór podzakresu](../audits/world_acceptance_161_163_20261026.md)
pozostaje ważny w opisanych granicach.

## Cel końcowy

Zgodne dane pozyskane podczas skanowania lub zbierania regionów mogą obsłużyć
kolejny skan bez HTTP i opłaty dostawcy. Mechanizm działa dla wszystkich graczy,
przez aktywny router, z kontrolą pokrycia, świeżości i praw do danych.
Zapotrzebowanie na geografię wynika ze skanów i odwiedzania świata, niezależnie
od wybranego dostawcy. Panel pokazuje, co zebrano i co faktycznie nadaje się do użycia.

Nie wymagamy nowych mechanik rozgrywki wykorzystujących drogi, wodę czy morza.
Nie ogłaszamy gotowego repozytorium skanera na podstawie liczby snapshotów UNKNOWN.

## Punkt wyjścia i zasady

- Zachować działający skaner, ID OSM, kategorie, limit 60, hakowanie, PvP i terytoria.
- Wykorzystać istniejące adaptery, repozytorium, planer, router, kolejkę, księgę
  i panel; nie tworzyć drugiego równoległego mechanizmu.
- Świeżość skanera pozostaje 300 s / dopuszczalny stale 1800 s. Retencja archiwum
  7 dni jest osobną własnością. Odczyt nie odnawia wieku danych źródłowych.
- Zachować MapLark 800/dzień i 24 000/31 dni, Geoapify 2700/dzień i 83 700/31 dni,
  VK 120 prób/dzień i 3720/31 dni oraz istniejące nierozliczone operacje.
- Warstwa lokalna poprzedza nowe żądania sieciowe. Na wejściu zachowujemy kolejność
  fresh cache → zgodny world → network → dopuszczalny stale.
- Overpass wysoko w kolejności sieciowej tylko dla dopuszczonego profilu i zdrowego
  źródła; potem MapLark. Geoapify tylko tam, gdzie potwierdzono zgodność kontraktu.
- UNKNOWN, niepełna odpowiedź, niewspierana geometria lub niezgodny profil nie
  mogą być przedstawione jako kompletny skan. Poprawnie potwierdzony pusty wynik
  jest pełnoprawnym wynikiem i może zatrzymać fallback.
- Konfiguracja web w `ecosystem.web.config.js`, kolektora w jego istniejącym
  ecosystemie. Bez sekretów w repo i bez trwałych ustawień wyłącznie w powłoce.
- Identity Gateway i `CHAOS_ADULT_POLICY_ENABLED=0` pozostają bez zmian.

## 163.5.0 — mapa wymagań i materiałów

- [x] Przypisać każde kryterium C/G/R/D z planów 161–163 do: istniejącego dowodu,
  zadania poniżej albo jawnej zależności zewnętrznej. Nie zamykać przez pominięcie.
- [ ] Zinwentaryzować zapisane capture, fixture i wyniki VPS przed kolejnymi API.
- [ ] Oddzielić brak danych od braku adaptera, połączenia runtime i odbioru.
- [ ] Dopisać do ewidencji testów wersję kodu, profil, zakres dowodu i ograniczenia.

Odbiór: każdy brak z audytu ma zadanie i mierzalny warunek zakończenia.

## 163.5.1 — globalny zapis i odczyt identycznego skanu

Ponowne użycie: `world_pilot.py`, `maplark_pilot.py`, `world_shadow.py`,
`world_read.py`, `scan_router.py`, istniejące flagi ingest/read.

- [x] Wprowadzić jawny tryb ogólny, oddzielony od ograniczonego pilota. Nie usuwać
  ograniczeń pilota przez przypadkowe rozszerzenie jego warunku.
- [x] Zapisywać kwalifikujące się pełne wyniki MapLark i odczytywać je niezależnie
  od konta, z zachowaniem wersji selekcji, rewizji, provenance i pustych wyników.
- [x] Włączyć planer do aktywnej ścieżki Overpass; nie opierać odbioru na starej,
  omijanej gałęzi `Service.fetch()`.
- [x] Oddzielić zatrzymanie nowych pobrań od cofnięcia prawa do lokalnego użycia.
  Nie reinterpretować dotychczasowego `enabled=false` bez jawnej migracji zachowania.
- [x] Awaria zapisu nie psuje poprawnego wyniku sieciowego. Uszkodzony lub niezgodny
  snapshot nie trafia do gracza; przewidywalny fallback i ograniczone logowanie.
- [x] Zapewnić niezależne wyłączenie ingest/read i powrót do istniejącego skanera.

Powyższe zaznaczenia oznaczają kod i testy lokalne. Nie oznaczają odbioru produkcyjnego.

Odbiór: skan konta A → odczyt world konta B i po restarcie, 0 HTTP i bez wzrostu
księgi. Test wymusza ominięcie wyłącznie wskazanego cache odpowiedzi, aby wynik
`source=world` rzeczywiście dowodził odczytu repozytorium.

## 163.5.2 — regionalne POI i zgodność źródeł

Ponowne użycie: kontrakty WorldObject/ProviderBatch, SelectionProof,
regionalne kandydaty, adaptery i testy graniczne 161–163.

- [ ] Zdefiniować wersjonowany regionalny profil wszystkich kategorii skanera,
  predykat selekcji i przeliczenie pozycji markerów zgodne z profilem źródła.
- [ ] Rozszerzyć zbieranie o pełny profil POI tam, gdzie źródło go obsługuje.
- [ ] Dodać odczyt POI z jednego potwierdzonego obszaru obejmującego całe zapytanie.
  Najpierw jeden snapshot; brak dowodu łączenia snapshotów oznacza MISS, nie union.
- [ ] Zweryfikować krawędzie regionów, obiekty przecinające granicę, relacje,
  deduplikację, limity/paginację, puste wyniki i niespójne wersje danych.
- [ ] Domknąć kwalifikację Geoapify: macierz kategorii, tożsamość OSM, geometria,
  selekcja i kompletność. Sam commercial ani punkty reprezentacyjne nie dowodzą
  zgodności pełnego skanu. Nie dopuszczać cichego zubożenia wyniku.
- [ ] Pokazać obsługiwane profile i przyczynę pominięcia źródła w panelu/routerze.

Odbiór: skan przesunięty względem pierwotnego zapytania, w całości wewnątrz
kwalifikowanego regionu, daje zgodny wynik lokalny bez HTTP. Brak pokrycia uruchamia
fallback. Jeśli dostawca nie zapewnia wymaganych danych, kwalifikacja pozostaje
jawną zależnością; nie oznaczamy całego pełnego fallbacku jako ukończonego.

## 163.5.3 — zapotrzebowanie, sąsiedzi i odświeżanie

Ponowne użycie: DemandQueue, `regular_discovery.py`, `discovery_worker.py`,
istniejące lease/fencing, priorytet gracza, harmonogram i wspólna księga.

- [x] Przenieść rejestrację sektora do wspólnej ścieżki skanera, także dla trafień
  cache/world i Overpass, bez podwójnego naliczania z gałęzi MapLark.
- [x] Lokalnie: rejestracja odwiedzenia sektora bez skanu, bez tras i identyfikatorów
  graczy w kolejce regionalnej; deduplikacja i ograniczenie częstości zapisu.
- [x] Lokalnie: ograniczony halo sąsiadów, niżej od bezpośredniego zapotrzebowania.
  Ustalić i udokumentować limit sektorów na cykl przed aktywacją; bez rekurencyjnego
  rozszerzania świata i bez osobnego niekontrolowanego budżetu.
  Limit: 8 nowych sektorów/cykl, 480 wpisów halo. Flagi wizyt i halo OFF;
  odbiór VPS pozostaje otwarty. Instrukcja: `doc/runbooks/world_visits_halo_163_5.md`.
- [ ] Rozdzielić odświeżanie archiwum geografii od brakującego aktualnego pokrycia
  POI. Odświeżać według popytu i kosztu, nie wszystkie rekordy co pięć minut.
- [ ] Zachować odporność na restart, zmianę rewizji, retry/backoff i równoległe
  procesy; nie dublować kosztu zadania ani ogłaszać utraconego lease sukcesem.

Odbiór: odwiedzenie nowego sektora tworzy ograniczone zadania, powtórzenie nie
powiela pracy, ruch gracza ma pierwszeństwo, restart nie powtarza zatwierdzonego pobrania.

## 163.5.4 — brakujące dane geograficzne

Ponowne użycie: kolektory roads/waterways/inland_water/coastline, `land_water.py`,
lokalny planer geometrii, zapisane rzeczywiste próbki i testy topologii.

- [ ] Uzupełnić dowód rzeczywistego MultiPolygon, najpierw sprawdzając istniejące
  capture; zachować części, otwory i pełne geometrie.
- [ ] Wybrać rzeczywisty produkt ląd–woda możliwy do regionalnego wykorzystania,
  potwierdzić pochodzenie, wersję, licencję, atrybucję i zasady przechowywania.
- [ ] Podłączyć ograniczony importer/adapter do istniejącego kontraktu; brak
  zamkniętej powierzchni nie uprawnia do uznania coastline za powierzchnię morza.
- [ ] Obsłużyć jawnie brakujące zależności, częściowe regiony i niewspierane
  przypadki topologii. Nie wymagać importu całej planety.

Odbiór: rzeczywisty regionalny produkt zapisany i odczytany lokalnie z provenance;
brak danych pozostaje UNKNOWN. Wykorzystanie geografii przez gameplay poza zakresem.

## 163.5.5 — panel i obserwowalność domknięcia

- [ ] Wykorzystać obecny panel i jego UX: osobno zbieranie, archiwum, świeżość,
  pokrycie skanera, prawa lokalnego odczytu i stan procesów.
- [ ] Dodać odpytywanie atlasu według viewportu i ograniczone agregaty zamiast
  przedstawiania ostatnich 100 snapshotów jako pełnego obrazu świata.
- [ ] Uzupełnić brakujące metryki: unikalne obiekty i wzrost dzienny, WAL,
  wiek kolejki/p95, przyczyny MISS/fallback i pominiętych dostawców.
- [ ] Stan workera opierać na heartbeat z czasem ważności; brak aktualnego
  sygnału prezentować jako nieznany. Czytelnie pokazać niepewne rozliczenia.
- [ ] Ustalić progi SLO przed odbiorem na podstawie istniejących pomiarów,
  z uwzględnieniem 4 workerów web i timeoutu 120 s; nie wymyślać wyników.
- [ ] Zweryfikować panel przez Playwright: desktop/mobile, PL/EN, brak surowych
  JSON-ów, brak overflow, czytelne stany i komunikaty przy działaniach.

## 163.5.6 — pakiet wdrożenia i zbiorczy odbiór VPS

Najpierw lokalnie zakończyć wszystkie niezależne prace, testy i instrukcje.
Potrzebę nowego capture blokującego kwalifikację źródła zgłosić jednym pakietem.
Nie czekać na niego z kodem, który od tego capture nie zależy.

Pakiet wydania musi zawierać:

- [ ] Jedną instrukcję: commit → testy offline → backup → migracja dry-run/apply
  (jeśli potrzebna) → reload właściwych ecosystemów → gotowość HTTP → aktywacja.
- [ ] Skrypt testów offline i inspekcji read-only, osobny jawny etap sieciowy
  z planem liczby wywołań/rezerwacji, bez automatycznych kosztownych ponowień.
- [ ] Etapy aktywacji: zapis → kontrolowany odczyt → odczyt ogólny → regionalny
  odczyt → rozszerzenia kolektora; niezależne przełączniki i rollback.
- [ ] Kontrolę konfiguracji po reload, statusu procesów i zapis PM2 po odbiorze.

| ID | Scenariusz | Wymagany dowód |
| --- | --- | --- |
| A01 | Baseline i migracja | Integralność/FK, backup, zgodne flagi, HTTP 200 |
| A02 | Pierwszy zgodny skan | Poprawny wynik gry, zapis, rozliczone pojedyncze pobranie |
| A03 | Ten sam skan z drugiego konta | World hit po pominięciu wskazanego cache, 0 HTTP, koszt bez zmian |
| A04 | Restart / 4 workery | Ten sam poprawny odczyt, brak zależności od pamięci procesu |
| A05 | Sąsiedni skan | Wynik zgodny z selekcją wewnątrz dowiedzionego regionu, 0 HTTP |
| A06 | Pusto / częściowo / poza regionem | Pusty kompletny wynik poprawny; niepełny lub poza pokryciem daje MISS |
| A07 | Wiek i wersje | Fresh/stale/expired, zmiana profilu/rewizji, brak pozornej aktualizacji wieku |
| A08 | Awaria / budżet / prawa | Odczyt bez nowej sieci, jeśli dozwolony; cofnięcie prawa blokuje użycie |
| A09 | Popyt i kolektor | Ruch i każdy provider, dedup, ograniczony halo, restart, priorytet live |
| A10 | Geografia i panel | Topologia, lineage, lokalny odczyt, atlas i czytelne stany |
| A11 | Regresja gry | Skan, hakowanie, terytoria na starym i nowym koncie |
| A12 | Rollback | Powrót do działającego skanera bez usuwania księgi i danych graczy |

Destrukcyjne błędy magazynu i awarie transportu testować lokalnie lub na kopii,
nie przez psucie produkcyjnej bazy. Upływ czasu testować deterministycznie lokalnie;
na VPS potwierdzić konfigurację i reprezentatywny cykl bez serii zbędnych oczekiwań.

## Zamknięcie i utrzymanie

Każdy etap ma osobne statusy: kod / lokalne testy / wdrożenie / odbiór VPS.
Zielone testy komponentów nie zamykają brakującej integracji ani niepotwierdzonego źródła.
Pełne zamknięcie wymaga mapy C/G/R/D i dowodów A01–A12; częściowe odbiory opisujemy
z nazwy. Zewnętrzna blokada pozostaje jawna, bez samodzielnego wykreślenia wymagania.

Po wdrożeniu osobno biegnie obserwacja naturalnego cyklu 7 dni, kosztów, stabilności
API i terminów przeglądu źródeł. Nie blokuje lokalnej implementacji. Pozostałe
nierozliczone operacje Geoapify nie znikają przez reset księgi.

Pierwsze zadanie wykonawcze: **163.5.0 + 163.5.1**, następnie 163.5.2–163.5.5
w zakresie możliwym lokalnie; dopiero gotowy pakiet 163.5.6 przekazujemy na VPS.
