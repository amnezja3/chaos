# Sprint 163 — pierwszy etap pasywny, 23.10.2026

Status: etap pasywny odebrany na VPS 24.10.2026; dalsza implementacja lokalna,
nie pełny PASS 163.

Najnowszy pakiet lokalny: hierarchia źródeł per warstwa/live/background,
panel PL/EN, router skanera i diagnostyka Geoapify; routing domyślnie OFF.
[Szczegółowe dowody i granice](provider_hierarchy_geoapify_20261024.md).

`discovery_queue.py` ponownie wykorzystuje SQLite POI. Jawna inicjalizacja przez
`tools/poi_world.py --discovery`; brak migracji przy skanie gracza. Tryb domyślny
`CHAOS_POI_DISCOVERY_MODE=off`, opcjonalnie `passive`.

Zapotrzebowanie agreguje sektory 0,01 stopnia i sześć warstw, bez identyfikatora
gracza, sesji, dokładnej pozycji lub trasy. To przybliżona lokalizacja świata gry,
nie dowód coverage ani deklaracja pełnej anonimowości wobec korelacji z innymi
danymi. Maksymalnie 2000 wpisów, wygasanie 24 h od ostatniego zapotrzebowania,
czyszczenie do 100 wygasłych wpisów przy zapisie; bez rekurencyjnych sąsiadów.
Wygasłe wpisy nie są wyświetlane. Bez nowego ruchu fizycznie pozostają do prune.

Stan to tylko PENDING. Nie ma workera, retry, pobierania w tle ani kosztów API.
To fundament 163.1, nie realizacja całej kolejki opisanej w sprincie.

Panel istniejącego admina pokazuje snapshoty/freshness, flagi, księgę kredytów
i maksymalnie 100 ostatnich sektorów zapotrzebowania. Te sektory nie oznaczają
obszarów z kompletnymi danymi. Liczniki kredytów to wewnętrzna księga CHAOS,
nie saldo panelu dostawcy. Podgląd nie uruchamia HTTP do dostawcy.

5 testów kolejki: dedup sześciu warstw, TTL, limit bez ekspansji, cztery procesy
zapisujące ten sam sektor, podgląd bez zmiany księgi, granice współrzędnych.
Pełny World: 107 PASS (46,198 s), łącznie z magazynem i integracją.
Regresja POI: 87 PASS (87,644 s). Po rozszerzeniu kontroli niezmienności tabel
księgi: 5 testów kolejki PASS (4,158 s). `git diff --check` i składnia JavaScript
panelu oraz obu ecosystemów: PASS.

Playwright MCP na izolowanym `tools/poi_admin_fixture.py --world`:
- PL mobile 390×844 i EN desktop 1440×900: poprawne etykiety, brak overflow;
- 3 sektory, 18 wpisów warstw, budżety 0/800 i 0/24000;
- zrzut sekcji mobilnej obejrzany; mapa sektorów i liczby czytelne;
- końcowy przebieg EN: 0 błędów/ostrzeżeń konsoli. W fixture poprawiono 404 favicon;
- powtórny GET nie dowodzi identyczności całego JSON: granice ruchomego okna
  kredytów zależą od czasu. Brak mutacji tabel księgi sprawdza test jednostkowy.

Do następnych etapów pozostają: worker z lease/fencing/priorytetem live,
certyfikowane pobieranie warstw, szczegółowa mapa coverage, filtry i statystyki,
obserwacja zasobów na VPS oraz osobno zatwierdzony pilot background.
Nie uruchomiono API MapLark/Geoapify, nie zmieniono zgód ani limitów produkcji.

## Odbiór produkcyjnego etapu pasywnego — 24.10.2026

Operator przekazał: 107 testów World PASS (44,138 s), 87 POI PASS (72,296 s),
dry-run i migracja schema 2 z integrity/foreign_keys OK, network_calls 0.
Backup: `/home/johndoe/chaos-backups/162-163-20261024T053532Z`.
Po restarcie skan gry udany; panel potwierdził przygotowany magazyn i OFF/OFF/off.
Po wdrożeniu `8e73857` przez `ecosystem.web.config.js` i `pm2 save`: discovery
passive, ingest/read nadal OFF. Kolejny skan dał jeden sektor i 6 wpisów warstw.
Snapshoty 0, background disabled; budżety widoczne 8/800 oraz 32/24000.
To dowód zapisu zapotrzebowania, nie pobrania sześciu warstw ani local-world hit.

## 163.1 — trwały cykl zadania, lokalnie

`discovery_jobs.py` jest biblioteką bez workera i bez HTTP. Oddzielna tabela
`world_discovery_job` w bazie POI jest inicjalizowana jawnie; istniejący tryb
passive nie tworzy tabeli i nie enqueue'uje zadań. Nie dodano flagi produkcyjnej.

- Enqueue wymaga istniejącego, niewygasłego zapotrzebowania. Klucz zawiera
  demand key, dostawcę, revision i profil; brak generowania sąsiednich sektorów.
- Limit 2000 zadań i 3 przejęć; claim atomowy, losowy token właściciela, lease
  maksymalnie 120 s i nie dłuższy niż TTL zadania. Brak heartbeat rozciągającego
  bez końca operację. Przyszły transport musi zmieścić deadline w lease.
- Wygasły LEASED można przejąć ponownie. FETCHING/VALIDATING po wygaśnięciu
  trafia do POLICY_BLOCKED/outcome_unknown: brak automatycznego HTTP lub refund.
- Identyfikator operacji kosztowej zapisuje się przed FETCHING. Nie ma w nim
  klucza API, konta gracza ani treści zapytania. Sama biblioteka nie rezerwuje
  kredytów: przyszły worker musi użyć istniejącej księgi przed tym przejściem.
- RETRY_AFTER/DEFERRED tylko przed HTTP; brak bezpiecznego wyniku po HTTP
  blokuje zadanie do uzgodnienia. To celowo węższe niż docelowe retry workera.
- Ack wymaga istniejącego kanonicznego snapshotu z query_key równym job id,
  zgodnego dostawcy/revision/profilu i digestu. Crash po publikacji, przed ack
  daje możliwość potwierdzenia tego snapshotu bez ponownego pobrania.
  COMMITTED oznacza zapis obserwacji, nie certyfikację całego obszaru ani
  rozliczenie kredytów. Ledger trzeba uzgodnić osobno.
- Prune usuwa tylko wygasłe zadania terminalne; nie usuwa outcome_unknown.
  Nierozstrzygnięte zadania mogą zapełnić limit i zatrzymać nowe — bez utraty
  dowodu możliwego kosztu i bez wpływu na zwykły skaner graczy.

10 testów cyklu zadania PASS (2,556 s): dedup/capacity, 4 procesy/jeden owner,
restart przed HTTP i fencing, niepewny wynik bez retry/prune, crash po publikacji,
idempotentny ack, obcy snapshot/revision, opóźnienie i limit prób, wygasanie.
Pełny World: 117 PASS (18,835 s). Następnie dodano unikalny indeks identyfikatora
operacji kosztowej, żeby dwa zadania nie wskazywały tego samego naliczenia;
ukierunkowana regresja 11 testów zadań PASS (2,342 s), w tym rollback błędnego
przejścia przy konflikcie. `git diff --check`: PASS. UI nie zmieniano.

Nie jest to jeszcze D01–D04 w całości: priorytet live opisano poniżej; pozostaje fairness
regionów, worker adapterów i połączenie jego cyklu z księgą. Nie wolno uruchamiać
tej biblioteki jako produkcyjnego workera ani traktować claim jako zgody na HTTP.

## Wspólne dopuszczanie do HTTP — 24.10.2026

`upstream_priority.py` używa istniejącej tabeli leases i slotu `@upstream`.
Brak nowego schematu, osobnej równoległości i identyfikatorów graczy. Maksymalnie
256 krótkich biletów live, TTL 10 s, kolejność według wygaśnięcia i tokena.
Rejestracja biletu oraz przyznanie slotu są odrębnymi krótkimi transakcjami;
konkurujące przyznania slotu i sprawdzenie oczekujących live są atomowe.
Pierwszeństwo dotyczy już zarejestrowanych oczekujących, nie przyszłych skanów.

W `acquire_maplark` opcjonalna flaga `CHAOS_POI_PRIORITY_ENABLED=1` uruchamia
tę ścieżkę. Domyślnie 0 w obu ecosystemach; produkcyjny passive bez zmian.
Live czeka do 2 s na istniejący slot, tło dostaje natychmiastową odmowę przy
oczekujących live. Rozpoczęte HTTP nie jest przerywane przez nowego gracza.
Transport ma dotychczasowy deadline 35 s, slot 42 s; czekanie poprzedza start
deadline transportu. Anulowanie biletu nie zwalnia slotu innego właściciela.

Po przyznaniu slotu nadal działa ta sama księga: rezerwacja przed HTTP,
idempotencja operation id, rozliczenie/uncertain po wyniku, wspólny circuit.
Ścieżka background odmawia działania bez flagi priorytetu. Sama flaga ani
parametr lane nie nadają praw do pobierania w tle — przyszły worker musi
sprawdzić scope, revision, zdolności warstwy i limity przed wywołaniem.
Nie podłączono background do żadnego procesu PM2 ani zadań produkcyjnych.

6 testów priorytetu PASS (3,085 s), w tym rzeczywiste 4 procesy live + 1 proces
symulujący tło, wspólna SQLite/księga, limit 30, operacje po 10:
wszystkie cztery dopuszczenia live przed tłem, łączne naliczenie 30, bez API.
Pozostałe dowody: FIFO, nieprzerywanie in-flight, wygasły bilet, współdzielony
circuit, rzeczywisty acquire_maplark z mock HTTP i idempotencją kosztów.
Dodatkowy test skanera: poprawny world hit przy wyczerpanej księdze i zajętym
slocie HTTP, bez nowego pozyskania i bez zmiany naliczenia.

Pełna regresja World: **125 PASS, 19,922 s**. Składnia ecosystemów i
`git diff --check`: PASS. UI nie zmieniano; brak nowego testu przeglądarkowego.
To dowód mechanizmu dopuszczania MapLark, nie pełnego workera ani odbiór
priorytetu legacy Overpass. Fairness między regionami i obciążenie około 100
testerów nadal wymagają osobnego testu. Ingest/read/background na VPS OFF.
# Uzupełnienie 24.10.2026 — rotacja regionów offline

DiscoveryJobs.claim wybiera sektory round-robin, następnie najstarsze gotowe
zadanie w sektorze. Trwały jednoelementowy kursor jest aktualizowany atomowo
z lease w tej samej transakcji SQLite; restart nie resetuje kolejności.
Licznik popularności sektora nie podnosi priorytetu. Brak aktualnego popytu,
odroczenie i limit prób wykluczają zadanie z wyboru. Kolejka nie tworzy sąsiadów.
To sprawiedliwość przydziału zadań, nie równość kosztów/wierzchołków między regionami.
Pierwszeństwo live nadal należy do osobnego mechanizmu admission MapLark.

14 testów cyklu zadań PASS (3,074 s), w tym rotacja po restarcie, popularny
sektor, usunięty popyt, odroczony sektor i konkurencja czterech procesów.
Nowa tabela kursora powstaje wyłącznie przez jawne DiscoveryJobs.initialize;
nie ma migracji na VPS, aktywacji workera ani wywołań API. Integracja tła,
symulacja około 100 testerów i limity kosztów per warstwa pozostają otwarte.

## Przegląd przedwdrożeniowy — 24.10.2026

Pełna pierwsza regresja World ujawniła rzeczywisty wyścig w Repository.transaction:
plik WAL usunięty przez zamknięcie połączenia innego procesu między exists i stat
powodował FileNotFoundError. Wynik pierwszego przebiegu: 132 testy, 1 failure
(konkurencja 4 live + background). Nie uznano tego za PASS ani nie pominięto testu.
Kontrola używa teraz pojedynczego stat i obsługuje wyłącznie FileNotFoundError.
Limit WAL pozostaje taki sam, błędy uprawnień/I/O propagują się.
Trzy deterministyczne testy regresji WAL PASS (0,199 s).
Po poprawce pełne World: 132 PASS (54,767 s).
Pełne POI po poprawce: 90 PASS (85,838 s), w tym trzy nowe przypadki WAL.
node --check ecosystem.web.config.js oraz git diff --check: PASS.

Zakres pakietu: rotacja sektorów offline, poprawka wspólnego Repository,
udokumentowany odbiór pilota i runbook przedwdrożeniowy. Brak zmian UI;
w tym pakiecie nie wykonywano nowego testu Playwright. Nowa biblioteka zadań
nie jest wywoływana przez procesy produkcyjne. Nie dodano workera ani migracji
VPS. Konfiguracja ecosystem.web.config.js zachowuje OFF/OFF/passive, priority 0.

## Jednorazowy wykonawca discovery — 24.10.2026

`discovery_worker.py` łączy istniejące DiscoveryJobs, acquire_maplark,
CreditBudget, UpstreamPriority i CanonicalWorldRepository. Bez automatycznej
migracji, enqueue, pętli, CLI wykonującego HTTP ani procesu PM2. Domyślny callback
enabled zwraca false: brak claim, sekretów i HTTP. Jawny permit: maksymalnie
10 sektorów 0,01 stopnia, okno do 24 h, wybrane roads/waterways/inland_water/coastline.
Brak profilu land_water/POI i brak obietnicy kompletnego pokrycia regionu.

Jedno zadanie pobiera promień 300 m od środka sektora, limit 1000 obiektów.
To obserwacja, nie coverage komórki; publish bez dowodu coverage, status UNKNOWN.
Nie rozszerza kolejki na sąsiadów. Rezerwacja <=20, wspólne istniejące okna
kredytów, koszt nadal zmienny dostawcy; wymagane jawne accept_variable_cost.
Sprawdza miejsce na maksymalny payload przed HTTP; commit nadal atomowo sprawdza
rzeczywisty limit. Równoległy zapis może zużyć miejsce po preflight i zatrzymać
publikację po pobraniu — nie obiecujemy rezerwacji dysku przed HTTP.

Scope background_refresh/storage/world_storage, enabled, tested_ok, endpoint,
revision, popyt, lease, permit i kill callback są sprawdzane przed pozyskaniem
i w kolejnych kontrolach. Wymagany priority ON; oczekujące live odraczają tło.
Identyfikator operacji jest stały per job i zapisywany przed wejściem w transport.
Wspólna księga nie umożliwia ponownego pobrania tej samej operacji. Niepewny HTTP
zostaje POLICY_BLOCKED, z zachowanym kosztem/rezerwacją; nie ma automatycznego retry.
Awaria po publikacji może zostać uzgodniona istniejącym acknowledge bez HTTP.

13 nowych testów PASS (12,274 s): wyłączenie, zakres/polityka, pierwszeństwo live,
budżet, timeout, partial, cofnięcie revision/kill podczas HTTP, commit raz,
odzyskanie ack po awarii. Pierwsza próba ujawniła błąd fixture (próba zmiany
niezmiennego okna kredytów); fixture teraz wyczerpuje budżet prawidłowym naliczeniem.
Wszystkie żądania mockowane, wyłącznie tymczasowe bazy.
Pełna regresja World z wykonawcą: 145 PASS (75,840 s). Nie zmieniano UI ani
aktywnej ścieżki skanera; nie wykonywano nowego testu przeglądarkowego.

Przed tłem produkcyjnym nadal wymagane: ograniczony producent zadań, limity
kosztu per warstwa/okno pilota, bezpieczna obsługa nierozliczonych operacji,
superwizja/pętla i jawna migracja job schema, test obciążenia i osobne zatwierdzenie
regionu/warstw oraz background_refresh. Istniejące zgody na skaner/pilot exact
nie są zgodą na background. Żadna konfiguracja VPS ani ecosystemu nie została
w tym etapie zmieniona. Nie zamykamy 163.

## Odbiór testów wykonawcy na VPS — 24.10.2026

Po wdrożeniu pakietu 4c6322e operator przekazał wyniki:
- test_world_discovery_worker.py: 13 PASS, 10.288 s;
- test_world_discovery_jobs.py: 14 PASS, 7.570 s;
- test_world_upstream_priority.py: 6 PASS, 2.998 s.

33 testy PASS na VPS, izolowane bazy i mockowany transport. Nie jest to test
realnego background HTTP ani zgoda na jego włączenie. Ograniczony producent
zadań i limity per warstwa pozostają kolejnym etapem lokalnej implementacji.
Nie polecono migracji, restartu ani zmiany flag w ramach tego odbioru.

## Producent zadań i wspólne limity pilota/warstw — 24.10.2026

Dodano lokalną bibliotekę discovery_producer: plan domyślnie read-only,
opcjonalny zapis do 40 zadań z istniejącego popytu w maksymalnie 10 sektorach.
Nie tworzy sąsiadów, nie wykonuje HTTP, pomija istniejące zadania także przy
kolejnych małych partiach. Wymaga aktualnej polityki dostawcy oraz budżetów.

CreditBudget otrzymał dodatkowe scope pilota i warstw, egzekwowane atomowo
razem z dotychczasowym budżetem globalnym. Tabele allocation wskazują te same
operacje księgowe: settle/reconciliation nie wymaga podwójnego rozliczenia.
Niepewne naliczenie nie zwalnia rezerwacji; nadwyżka utrzymuje blokadę konta.
Okna scope są niezmienne, do 24 h. Wykonawca wymaga budget_id i kompletu
skonfigurowanych scope przed claim. Stary schemat bez tabel scope nadal obsługuje live.

Regresja lokalna World: **157 PASS, 57.421 s**, izolowane SQLite i mockowany HTTP.
Regresja skanera POI: **90 PASS, 72.329 s**. `git diff --check`: PASS.
Nowe scenariusze: czterech równoczesnych rezerwujących ostatnie środki warstwy,
limit globalny mimo wolnego budżetu warstwy, suma między warstwami, restart,
rozliczenie niepewnego kosztu, nadwyżka, wygasły/brakujący scope, kompatybilność
live ze starym schematem, plan bez zapisu, dedup i postęp ograniczonych partii,
cofnięta polityka i wygasły popyt. Pierwsze uruchomienie wykryło literówkę nazwy
parametru starts w walidacji okna; poprawiono ją przed pełną regresją.

Nie zmieniano UI, ecosystemu, bazy produkcyjnej ani flag. Brak nowych wywołań API.
Nadal otwarte przed background: nadzorowana pętla, jawna migracja, operacyjne
uzgadnianie niepewnych operacji, test obciążenia i zatwierdzenie parametrów pilota.
Nie jest to odbiór całego sprintu 163 ani aktywacja tła.
# Proces operacyjny i ograniczony claim — 24.10.2026

Dodano discovery_runtime, CLI world_discovery_worker i osobny ecosystem
z workerem domyślnie OFF. Domyślne CLI planuje bez enqueue/claim/HTTP;
--execute wymaga flagi, aktualnego pliku pozwolenia i istniejących budżetów.
--serve wykonuje pojedyncze cykle z oczekiwaniem i obsługą zakończenia.
Pozwolenie jest ponownie czytane przed HTTP/publikacją; usunięcie/zmiana
zatrzymuje pracę bez kasowania wykorzystanych kredytów. Proces nie tworzy
nowych zgód dostawcy, scope ani budżetu globalnego.

Poprawka claim: SQL filtruje komórki/warstwy pozwolenia przed przejęciem.
Wcześniej worker mógł przejąć cudzy sektor i dopiero potem oznaczyć zadanie
POLICY_BLOCKED. Teraz pozostawia je PENDING bez zwiększenia attempts.
Stary test oczekiwał policy_blocked; zmieniono oczekiwanie na idle + nietknięte
zadanie. Nie usunięto testu ani warunku bezpieczeństwa.

tools/poi_world.py --jobs rozszerza istniejący dry-run/backup/apply o tabele
kolejki i księgi scope. Wymaga --canonical, zachowuje naliczenia i nie aktywuje
workera. Runbook: [worker 163](../runbooks/world_discovery_worker_163.md).

Testy lokalne: discovery 52 PASS (14.596 s), końcowy runtime 8 PASS
(2.896 s), pełny World **190 PASS (42.318 s)**. Rzeczywiste izolowane SQLite,
HTTP mockowany. Składnia ecosystemu i diff-check poprawne. Wyłączony CLI:
disabled, network_calls=0. Brak wywołań publicznych API, zmian VPS i UI.
Żaden nowy odbiór przeglądarkowy nie jest deklarowany.

Geoapify rozliczenie pozostaje otwarte: raport panelu 3 Places/6 kredytów
i 1 Geocoding/1 kredyt nie odpowiada czterem operacjom Places w CHAOS.
Nie zwolniono rezerwacji i nie zresetowano limitów. Nie blokuje pakietu MapLark.

Nadal nie zamykamy całego 163: regionalne coverage, panel dowodów/agregatów,
land_water i pilot obciążenia/produkcji pozostają otwarte, jak w runbooku.
# Odbiór migracji workera na VPS — 24.10.2026

Operator potwierdził 53 testy PASS (33.248 s), następnie dry_run z
original_data_unchanged=true i schema_ready po --canonical --discovery --jobs
--apply z kopią SQLite w katalogu 163-worker. W obu wynikach: world_schema=2,
providers=7, snapshots=0, integrity/FK=ok, network_calls=0.
Nie przekazano ścieżki końcowego katalogu backupu, dlatego nie wpisujemy jej
na podstawie przypuszczenia. To odbiór schematu i izolowanych testów,
nie potwierdzenie uruchomienia procesu ani pozyskania geografii.

Kontynuacja lokalna: pasywna projekcja jobs w istniejącym admin API, counts
per state, ready_by_time (wyłącznie kryterium czasu, nie pozwolenie na HTTP),
expired_waiting/leases, unresolved oraz 20 ostatnich stanów. Brak tokenów
lease, operation ID i danych gracza. runtime=unknown: tabela zadań nie jest
dowodem działania procesu. Odczyt nie odzyskuje lease i nie inicjalizuje tabel.
Test 20 odczytów zachowuje POLICY_BLOCKED i księgę, bez HTTP. Runtime:
9 PASS, 5.513 s. Panel PL/EN pokazuje projekcję kolejki i jawnie niepotwierdzony
stan procesu zamiast stałego komunikatu o wyłączonym pobieraniu. Playwright MCP:
izolowana aplikacja, pusta przygotowana kolejka, odświeżenie, PL/EN oraz ekran
390x844 — brak overflow, błędów i ostrzeżeń konsoli; brak zasobów zewnętrznych.
Nie zmieniano stanu produkcji ani zgód na pobieranie danych.

## Zatwierdzony pilot roads — przygotowanie

Operator zatwierdził komórkę 2036/5153, roads, godzinę i wewnętrzny limit 20.
Dodano tools/discovery_pilot_prepare.py: backup SQLite + poprzedni provider,
permit i niezmienne scope limitów, zachowanie enabled/normal_scan, plan bez HTTP.
Nie resetuje naliczeń ani czasu przy ponowieniu, nie odtwarza usuniętego permitu
nad istniejącym budżetem i nie tworzy popytu. Trzy izolowane testy PASS (1.743 s).
Produkcja nadal wymaga uruchomienia przygotowania przez operatora; nie wykonano
HTTP, nie aktywowano procesu ani priorytetu na VPS.

Operator następnie potwierdził prepared, plan z jednym zadaniem roads revision 9,
network_calls=0, permit until=1792856596.6014156 i backup
/home/johndoe/chaos-backups/163-roads-20261024T144316Z/poi_cache.sqlite3.
Przygotowano ecosystemy do kolejnego kroku: priority ON w web i workerze,
worker --execute bez --serve, autorestart=false. Nie jest to dowód wykonania HTTP
ani uruchomienia nowej konfiguracji na VPS. Składnia i ograniczenie jednego cyklu
sprawdzone przez Node.

### Pierwsze wykonanie roads na VPS — PASS pobrania i zapisu

Operator przekazał wynik procesu chaos-world-discovery-worker:
status=committed, network_calls=1, coverage=UNKNOWN,
snapshot=e807da396a7015dcb3475e354d429b5848d5ce00e8f7bad8dacdb2f4172c0b28.
Operacja discovery:f4a9d8a703f9ef881e53394ce3bef7806e275e29d86bced79b6f1c57852790a6:
reported_credits=3, reserved_credits=20, billing_state=settled.
To potwierdza pojedyncze pobranie i publikację obserwacji oraz rozliczenie;
nie potwierdza pełnego regionalnego coverage, wykorzystania przez gameplay,
braku powtórki po restarcie ani opóźnień skanera przy konkurencyjnym ruchu.
Kolejny odbiór: pojedyncze ponowienie w ważnym oknie permitu powinno zwrócić
idle/network_calls=0. Nie odnawiać wygasłego pozwolenia do tego testu.

Operator potwierdził następnie nowy wpis po restarcie: status=idle,
network_calls=0. Odbiór deduplikacji po restarcie PASS; wcześniejszy committed
w tail logu jest wpisem historycznym, nie drugim pobraniem. Brak nowej operacji
HTTP w tym cyklu. Łączny zgłoszony koszt pierwszego pobrania: 3 kredyty.
Po odbiorze zaparkowano flagę workera w ecosystem.discovery.config.js na 0;
wdrożenie tej zmiany i zatrzymanie procesu na VPS pozostają po stronie operatora.
Priorytet skanów web pozostaje aktywny. Pełne 161–163 nie są jeszcze zamknięte:
regionalne pokrycie, pozostałe warstwy i odbiór konkurencyjnego obciążenia
nie wynikają z tego pilota roads.

## Pakiet panelu, metryk i odbioru — 24.10.2026

Gotowy lokalnie do wdrożenia, bez nowych wywołań dostawców:

- Atlas ograniczony do 100 snapshotów / 8 MiB / 2 s SQL. Oddziela dowody area
  od exact-query i obrysów UNKNOWN; filtry 6 warstw, kompletne puste wyniki,
  szczegóły zgody, pan/zoom i zakres ważności. Brak mapy tras graczy.
- Godzinowe agregaty POIFetcher.get_all: sukces/błąd/pusty wynik, rozłączne
  źródła, próby transportu, przedziały latencji. Opcjonalne zapisy fail-soft;
  4 procesy zapisujące równocześnie przeszły test bez utraty liczników.
- Ostrzeżenia 70/85/95% budżetu wewnętrznego. Ręczny, datowany odczyt konta
  dostawcy z CAS i CSRF nie rozlicza ani nie zwalnia rezerwacji Geoapify.
- Jawna migracja --metrics; read-only tools/world_release_check.py bada spójną
  kopię bazy, integralność, kolejkę, dowody, budżety i liczniki bez HTTP.
- Plan bbox i offline inspekcja warstw liniowych/powierzchniowych. Nie jest
  podłączony do skanera radius, nie nadaje certyfikatu regionalnej kompletności.

Walidacja finalna na Windows, izolowane bazy/transporty:

- test_world_*.py: **209 PASS, 115.561 s**.
- test_poi_*.py: **92 PASS, 104.613 s**.
- Playwright MCP: tests/browser/world_atlas.js, PL/EN, 1440 i 390 px,
  filtry, puste dowody, szczegóły, zoom/fit, próg 95%, brak overflow.
  Zero page errors, zero zewnętrznych requestów, konsola bez błędów/ostrzeżeń.
  Dodatkowo sprawdzono zapis ręcznej obserwacji i pan w izolowanym panelu.
- Node sprawdził składnię JS. Browser oraz lokalny fixture zamknięte po QA.

Procedura migracji, backupu, reloadu, testów po wdrożeniu i rollbacku:
[world_acceptance_161_163.md](../runbooks/world_acceptance_161_163.md).
VPS tego pakietu jeszcze nie potwierdził. Nie zmieniono produkcji ani naliczeń.
Otwarte pozostają realne dowody regionalne, piloci pozostałych warstw, źródło
land_water, pełny profil Geoapify i uzgodnienie kosztów jego diagnostyki.

## Zamknięcie odbioru technicznego pakietu 7e18c1d na VPS

24.10.2026 operator przekazał log wdrożenia oraz raport po zwykłym skanie.
To dowody dostarczone przez operatora, nie samodzielny dostęp agenta do VPS.

- Pull do 7e18c1d; World: 209 testów PASS / 92.940 s; POI: 92 PASS / 70.266 s.
- Migracja schema_ready, world_schema=2, integrity/foreign_keys=ok.
- Reload ecosystem.web.config.js, worker discovery zatrzymany, Launch HTTP 200,
  pm2 save potwierdzony. Nie uruchomiono stałego pobierania w tle.
- Raport po skanie: metrics prepared=true, attempts=1, successful=1,
  errors=0, empty_successes=0, sources.network=1, transport_attempts=1.
  p50/p95 upper=3 s to granica histogramu, nie dokładny czas ani miarodajny
  percentyl populacji na podstawie jednej próbki.
- MapLark: committed dzienny 31→34, rolling 55→58, operations 17→18,
  unresolved=0; koszt przyrostowy 3 kredyty. Pozostało 766/800 oraz 23942/24000.
- Roads: 29 obiektów, UNKNOWN, local_read_allowed=false. Nie ma dowodu
  kompletności regionu; historyczny snapshot nie jest aktywnym lokalnym źródłem.
- Geoapify: nadal 4 nierozliczone operacje i 20 zarezerwowanych kredytów.
  Alert 95 przy wykorzystaniu 100% dotyczy wewnętrznego budżetu diagnostycznego,
  nie wyczerpania planu dostawcy. Żadnych rezerwacji nie zwolniono.
- Raport kontrolny: network_calls=0, production_writes=0, integralność OK.
  Te zera dotyczą raportu, nie poprzedzającego go skanu gracza.
- Syntetyczny benchmark VPS: dla 3000 obiektów zapis 3.3942 s, odczyt 0.1387 s,
  transakcja hold+close 0.183781 s, lifetime RSS 90300416 B,
  post-commit WAL 4548512 B. Bez testu obciążenia współbieżnymi graczami.

Odbiór techniczny tego pakietu: **ZAMKNIĘTY / PASS**. Testy UI PL/EN desktop/mobile
pozostają dowodami lokalnymi; nie deklarujemy osobnego odbioru UI produkcyjnego.
Całe 161–163 pozostają w realizacji ze względu na otwarte bramki regionalne.
Polecenie offline z /prywatny/katalog/body.json zakończyło się FileNotFoundError:
była to ścieżka przykładowa, nie istniejący artefakt. Nie wykonano HTTP ani zapisu;
nie stanowi to wyniku testu bbox. Następny etap: rzeczywista próbka bbox i granice.

## Regionalne bbox — przygotowanie pojedynczej próby

Dodano tools/world_region_probe.py i
[instrukcję VPS](../runbooks/world_region_bbox_probe.md). Narzędzie domyślnie
planuje bez HTTP. Wykonanie wymaga jawnego zatwierdzenia pojedynczej próby
i zmiennego kosztu; korzysta z istniejących limitów MapLark oraz osobnego,
nieodnawianego okna 20 kredytów/1 h. Stała operacja zapobiega drugiemu żądaniu.
Diagnostyka ustępuje oczekującym skanom live, nie dodaje zadań do kolejki świata
i nie zmienia rejestru, flag, certyfikatów ani cache. Zapisuje prywatną próbkę
odpowiedzi i metadane rozliczenia, nie sekret ani nagłówki żądania.

Testy lokalne: test_world_region*.py **12 PASS / 4.271 s**;
test_world_acquisition.py **8 PASS / 2.549 s**. Obejmują koszt rzeczywisty,
timeout z zachowaniem rezerwacji, niekompletną odpowiedź, zmianę rewizji,
wygaśnięcie polityki/okna, brak zgody, brak budżetu, priorytet gracza,
odmowę nadpisania plików i brak ponownego HTTP.
Próba dostawcy pozostaje **NIEWYKONANA**; region_certified=false.

### Wynik pierwszego bbox roads na VPS

Operator potwierdził 12 testów PASS / 5.474 s oraz pojedyncze pobranie:
region:roads-2036-5153-bbox-v1, provider revision=9, 76 obiektów,
completeness=complete według odpowiedzi, brak powodów niekompletności,
reported_credits=3, reserved_credits=20, billing_state=settled.
Artefakt: /home/johndoe/chaos-bbox-roads-oXi9gp/capture.
Nie zmieniono gameplayu, rejestru ani world ingest.

Kontrola granic **NIEZALICZONA**: invalid_objects=1; lewa połowa 33,
prawa 54, wspólne 12. Nie wnioskujemy z tych liczników, czy problem dotyczy
selekcji, klasyfikacji czy geometrii. Nie wystawiono certyfikatu regionu.
Rozszerzono inspekcję offline o ograniczoną listę OSM ID, konkretne przyczyny,
typ i bounds geometrii oraz rozróżnienie przecięcia obrysu od samej geometrii.
Raport nie wypisuje nazw/adresów obiektów. Kolejna kontrola używa zapisanych
body.json/headers.json, bez ponownego API i bez nowych kosztów.

### Wyjaśnienie odrzucenia granicy i lokalny filtr

Operator przekazał diagnozę: osm:way:201343570, LineString, highway=unclassified,
bounds=[20.3637689,51.5164428,20.3754074,51.5301756], geometry_outside_bbox,
envelope_intersects_bbox=true. Klasyfikacja roads jest poprawna; prostokąt
otaczający obiekt przecina region, lecz linia nie. Jest to zgodne z hipotezą
selekcji po obrysie, ale jedna próbka nie dowodzi implementacji dostawcy ani
braku pominiętych obiektów. W odpowiedzi pozostaje 75 obiektów przecinających
obszar; zgodność liczników: 33+54−12=75. Są to dane raportu operatora,
nie niezależna inspekcja pełnego pliku przez agenta.

Inspekcja offline rozdziela teraz surowe boundary_selection_pass od
local_filter.observed_geometry_pass. Lokalnie odrzucalne są wyłącznie poprawne
geometrie spoza bbox, których obrys go przecina. Błędna warstwa, geometria,
brak geometrii albo całkowicie obcy region pozostają blokadą. Filtr nie
przycina linii, nie zmienia pliku źródłowego, nie tworzy dowodu area i nie
udaje kontroli brakujących obiektów. Weryfikuje sumę sąsiednich wycinków.
Testy test_world_region*.py: **16 PASS / 5.609 s**, syntetyczne, bez API.
Do dalszej niezależnej walidacji potrzebne są zachowane body.json i headers.json;
nie ma potrzeby kolejnego pobierania tej próbki od dostawcy.

### Niezależna inspekcja plików i odczyt lokalny — PASS geometrii

Operator dostarczył body.json i headers.json do doc/audits. Agent odczytał
oba pliki lokalnie, bez HTTP. SHA-256 oryginałów zapisano w
tests/fixtures/poi/maplark_roads_bbox_20261024.metadata.json.
Próbka regresyjna zachowuje wszystkie 76 OSM ID i pełne geometrie; usuwa tagi
inne niż klasyfikacyjne. Pochodzenie MapLark/OSM i atrybucja są w metadanych.
Oryginalnych plików o ogólnych nazwach nie dodano do commita.

Potwierdzono: 76 wyników, dokładnie jeden envelope false positive
osm:way:201343570, 75 dokładnych przecięć, 0 blokujących błędów geometrii,
33/54/12 w sąsiednich wycinkach. Surowy boundary_selection_pass pozostaje false;
local_filter.observed_geometry_pass=true; region_certified=false.

Regresja na prawdziwych geometriach w tymczasowym SQLite:

- Zapis surowych obserwacji i ponowne otwarcie bazy nie odblokowują area read.
- Jawny certyfikat wyłącznie fixture pozwala przetestować silnik: po restarcie
  odczyty dwóch wycinków zwracają 33 i 54 obiekty, 12 wspólnych, suma 75.
  Każda geometria jest identyczna z pełną geometrią wejściową, bez clipowania.
- Wyjście poza granice snapshotu daje MISS.
- Próba publikacji area z nadmiarową linią jest odrzucana; po odfiltrowaniu
  nadal wymagany jest osobny certyfikat. Nie dopisano certyfikatu MapLark.

test_world_region*.py: **20 PASS / 7.430 s**, w tym 4 testy rzeczywistej próbki.
Ten etap zamyka odbiór geometrii i działania lokalnego silnika na próbce.
Nie dowodzi braku obiektów pominiętych przez API ani spójnej wersji źródła.
Następny etap kwalifikacji: porównanie selekcji niezależnych zapytań o sąsiednie
wycinki z lokalnymi wynikami i rozstrzygnięcie semantyki danych źródłowych.
Żadnych kolejnych zapytań dostawcy ani zmian VPS nie wykonano.

### Przygotowanie niezależnej kontroli sąsiednich wycinków

Rozszerzono istniejącą diagnostykę o dwa sztywno zdefiniowane warianty left/right.
Każdy ma własną stałą operację, oba wspólne nieodnawiane okno 40 kredytów/1 h,
rezerwację 20 na żądanie i współdzielone limity konta. Parent zachowuje poprzednią
tożsamość; nowe warianty nie umożliwiają ponowienia poprzedniego pobrania.
Nadal jest to ręczna diagnostyka o niższym priorytecie, bez ingest i aktywacji tła.

tools/world_region_compare.py odczytuje trzy istniejące katalogi, sprawdza
powiązanie raportów z bbox i rewizję, porównuje lokalne ID z niezależnymi
odpowiedziami oraz pełną topologię geometrii i highway. Braki, dodatkowe obiekty,
clipowanie, zmienione dane i niepełne odpowiedzi nie otrzymują PASS.
Przy zgodności próbek nadal region_certified=false i dataset_version_verified=false.

test_world_region*.py: **27 PASS / 9.220 s**. Nowe testy używają symulowanych
odpowiedzi wycinków opartych na prawdziwej geometrii; nie są to niezależne
odpowiedzi MapLark. Zweryfikowano też wspólny limit obu operacji i brak retry.
Runbook: [world_region_neighbors.md](../runbooks/world_region_neighbors.md).
Następna rzeczywiście potrzebna czynność operatora: push i dwa ograniczone
wywołania na VPS. Agent nie wykonał nowych HTTP ani nie zmienił produkcji.

### Niezależne wycinki na VPS — zgodność próbki PASS

Operator dostarczył log pull do fff8d1b oraz 27 testów PASS / 7.073 s.
Katalog odpowiedzi: /home/johndoe/chaos-bbox-neighbors-5Soi0x.

| Odpowiedź | Surowe obiekty | Dokładne przecięcie | Charge |
| --- | ---: | ---: | ---: |
| Parent (wcześniejsza) | 76 | 75 | 3 |
| Left (nowa) | 34 | 33 | 3 |
| Right (nowa) | 55 | 54 | 3 |

Każda odpowiedź zawierała ten sam jeden envelope false positive
osm:way:201343570. Po filtrze local_objects=independent_objects dla obu
wycinków; missing/additional/changed_full_geometry/changed_highway puste.
sample_comparison_pass=true, provider_revisions_match=true (revision 9).
Obie nowe operacje settled; 2 HTTP / 6 kredytów. Łącznie parent+left+right
3 HTTP / 9 kredytów. Porównanie offline: network_calls=0, production_changed=false.
region_certified=false oraz dataset_version_verified=false pozostają jawne.

SHA-256 body nowych odpowiedzi z raportu operatora:
- left: b0397dccbfe1c2d319bb9aa87efa7a05f70fa4d73ac528c5c3b9e1fe45ff9225
- right: de3ab38704f569b337dbd84db9a6dad487ba9c9aca8025edb87e1059b39d5ac2

Odbiór zgodności tych sąsiednich wycinków **ZAMKNIĘTY / PASS**.
Nie wymaga ponowienia zapytań. Wynik nie kwalifikuje innych warstw ani całej
planety; brak wersji datasetu nie jest zastępowany czasem pobrania/revision 9.

Po odbiorze dodano world_region_candidate.py, używany przez porównywarkę offline:
roads only, ścisły plan bbox, kompletny batch, jedno źródłowe snapshot/dataset,
zachowanie całych obiektów i provenance. Odrzuca tylko envelope false positives,
blokuje braki geometrii, obce warstwy, częściowość i mieszanie źródeł.
Selection maplark-bbox-local-filter-v1 celowo nie jest AREA_SELECTION i nie
przechodzi jako certyfikat do SelectionProof. Brak połączenia z gameplayem,
workerem czy publikacją produkcyjną. To gotowy adapter kandydujący, nie rollout.

Walidacja lokalna: 32 testy regionalne PASS / 9.760 s; po podłączeniu adaptera
do porównywarki ponownie 5 testów porównania PASS / 1.099 s. Żadnych nowych API.
Warunki single-snapshot są technicznie obsługiwane przez obecny planner, który
nie łączy snapshotów; kwalifikacja źródła/zakresu i osobny pilot area nadal otwarte.

### 2026-10-24 — pakiet ograniczonego pilota regionalnego roads

Przygotowano `tools/world_region_pilot.py` i runbook
`doc/runbooks/world_region_storage_pilot.md`. Domyślny plan: zero HTTP/zapisów.
Jawne wykonanie wymaga akceptacji pojedynczego regionu i zmiennego kosztu,
aktualnych storage/world_storage, istniejącej schema v2 oraz nowego backupu.
Spójny SQLite backup przed mutacją; jeden request, stałe ID operacji,
nieodnawiane okno 20/1 h, wspólne limity konta i priorytet skanów graczy.

Kwalifikacja jest ograniczona do operator-controlled empirical pilot:
jeden świeży snapshot roads w bbox 20.36,51.53,20.37,51.54. Izolowany adapter
`maplark-roads-single-region-pilot-v1` zapobiega odczytowi przez normalny
adapter produkcyjny. Nie jest to poświadczenie dostawcy ani globalny certyfikat.
Nieznany source_dataset_at pozostaje nieznany. Brak łączenia źródłowych wersji.
Automatyczny filtr nie tworzy certyfikatu; jawne wykonanie CLI akceptuje tylko
ten ograniczony profil pilota, na podstawie odebranego porównania wycinków.

Testy na rzeczywistych geometriach zapisanej próbki: 76 raw / 75 stored;
left 33 / right 54, pełne geometrie i suma ID zachowane po ponownym otwarciu
bazy. Zwykły adapter oraz zapytanie poza bbox dają MISS. Błąd częściowości,
pusta próbka, zmiana rewizji, brak world_storage i powtórzenie operacji nie
publikują danych; koszty wykonanego requestu nie są cofane. Wygaśnięcie daje
MISS bez sieci. Backup nie jest nadpisywany. Inspekcja --check używa mode=ro.

Walidacja lokalna: 40 testów regionalnych PASS (9.852 s), 16 testów odczytu
PASS (4.524 s), 8 testów acquisition PASS (2.596 s); łącznie 64. CLI plan PASS,
network_calls=0. Wszystkie transporty testowe izolowane; zero prawdziwych API.
Nie zmieniono flag, ecosystem, rejestru ani routingu gry.

**Gotowe do push i jednorazowego odbioru na VPS; wykonanie pilota VPS nadal
niepotwierdzone.** Ten etap nie zamyka innych warstw ani stałego rolloutu.

### 2026-10-24 — odbiór regionalnego pilota roads na VPS: PASS

Operator przekazał pełny wynik aktualizacji fff8d1b → 21f62b5 i wykonania
procedury. Testy VPS: regionalne 40 PASS / 15.140 s, odczyt 16 PASS / 5.640 s,
acquisition 8 PASS / 3.638 s. Razem 64 PASS. Plan: zero HTTP.

- Artefakty: `/home/johndoe/chaos-region-storage-Bzz83O/capture`.
- Backup: `/home/johndoe/chaos-region-storage-Bzz83O/poi_cache.sqlite3`.
- Snapshot: `015779ba722f850f2fd85ef4c484096c1210f77c1c24d2e30004a50411df5285`.
- Operacja: `region:roads-2036-5153-storage-pilot-v1`.
- Pozyskanie: jeden request, reserved 20 / reported 3, billing settled.
- Raw 76 / stored 75; wykluczony wyłącznie `osm:way:201343570`.
- Publikacja: `published_pilot`; wszystkie odczyty COMPLETE_FRESH,
  reason single_snapshot. Parent 75, left 33, right 54; ten sam snapshot.
- Pełne geometrie i suma ID: `full_geometry_and_union_pass=true`.
- Osobny proces CLI: `local_pilot_pass`, network_calls=0, production_writes=0.
- Gameplay, environment i registry unchanged. Global_region_certified=false,
  dataset_version_verified=false; nie nadano szerszej kwalifikacji.

Zamknięto odbiór trwałego zapisu i lokalnego wyboru podobszarów **tego jednego
profilu/regionu**. Dowód ponownego procesu CLI nie jest restartem PM2 ani restore
produkcyjnego backupu. Nie ponawiać tej płatnej operacji. Źródłem potwierdzenia
są wyniki przesłane przez operatora, nie bezpośrednia sesja SSH agenta.

Kolejność pozostałej pracy: kwalifikacja profili cieku i jeziora z otworami,
następnie osobny kontrakt wybrzeża/land_water oraz szerszy rollout per warstwa.
Geoapify pozostaje bez pełnej kwalifikacji gameplay i bez uzgodnienia czterech
niepewnych operacji; niniejszy odbiór nie zmienia jego księgi. Infrastruktura
może być rozwijana offline bez ponawiania zaakceptowanych prób roads.

### 2026-10-24 — przygotowane profile cieku i powierzchni wód

Wspólny regionalny kandydat obejmuje roads, waterways i inland_water; nigdy
nie wystawia samodzielnie SelectionProof. Powierzchnie wód wymagają Polygon
lub MultiPolygon, nie punktu zastępującego geometrię. Zachowuje całe części,
otwory i pochodzenie; partial, mieszane źródła i coastline pozostają odrzucone.
Inspekcja zapisanej odpowiedzi pokazuje typy, części, otwory oraz jawny stan
kandydata; brak otworów nie jest odbiorem jeziora z wyspą.

Rozszerzono istniejące world_region_probe o dwa profile parent w tym samym
ograniczonym bbox. Osobne stałe operacje, wspólny nieodnawiany limit 40/1 h,
maksymalnie dwa HTTP, po 20 rezerwacji; wspólna księga i priorytet graczy.
Nie zmieniono wcześniejszych operacji ani pilota roads. Wodne profile nie
mogą użyć pilota roads ani jego certyfikatu, nie publikują do magazynu świata.
Procedura: [dwie odpowiedzi wodne](../runbooks/world_region_water_probe.md).

Nowe testy syntetyczne: 9 PASS. Obejmują przecinającą granicę linię, pełny
MultiPolygon z otworem i częścią poza bbox, backup/restore SQLite, lokalny
pusty wynik wewnątrz otworu, MISS poza dowodem, izolację warstw, brak area
approval oraz wspólne rozliczenie dwóch profili i brak powtórki operacji.
Łącznie regionalne 49 PASS / 10.944 s, read 16 PASS / 3.880 s,
acquisition 8 PASS / 2.046 s. Po doprecyzowaniu nazwy pola otworów ponownie
9 testów wodnych PASS / 1.940 s. Nie wykonano prawdziwych wywołań dostawcy.
Pozyskanie tych odpowiedzi na VPS i rzeczywisty odbiór jeziora z wyspą
pozostają otwarte. Nie zmieniono flag produkcyjnych ani zakresu kwalifikacji.

### 2026-10-24 — rzeczywiste odpowiedzi waterways i inland_water odebrane

Źródło: kompletny log operatora z VPS, pull 21f62b5 → fc8a3dd. Testy:
49 regionalnych PASS / 16.612 s, 16 read PASS / 7.124 s, 8 acquisition PASS /
2.884 s; łącznie 73 PASS. Oba plany bez HTTP; potem dwa pojedyncze pobrania.
Nie była to sesja SSH agenta; pełne geometrie pozostają w plikach na VPS.

Katalog: `/home/johndoe/chaos-water-region-ZLZnBM`, podkatalogi waterways
i inland_water, każdy body.json / headers.json / report.json.
Oba raporty: captured_not_certified, kompletność complete bez reasons,
provider_revision=9, po 3 reported credits / 20 reserved, settled.
Łącznie 2 HTTP / 6 kredytów. Rejestr, gameplay i world ingest bez zmian.

| Profil | Surowe | Kandydat po filtrze | Geometria | Lewy / prawy |
| --- | ---: | ---: | --- | --- |
| waterways | 2 | 1 | 2 LineString w odpowiedzi | 1 / 0 |
| inland_water | 4 | 4 | 4 Polygon, zero otworów | 3 / 1 |

Z waterways wykluczono `osm:way:1158230038` (waterway=ditch): sama geometria
poza bbox, envelope przecina bbox. Bounds raportu:
`[20.363869,51.5374067,20.3931653,51.5431479]`. To ten sam rodzaj nadmiarowej
selekcji jak w próbie roads. Raw boundary_selection_pass=false, filtr ma
blocking_objects=0 i observed_geometry_pass=true. Nie ukryto surowego błędu.
Inland_water: zero invalid_objects, boundary_selection_pass=true.
Oba candidate=prepared_not_certified; żaden wynik nie został dopuszczony
jako kompletny regionalny odczyt produkcyjny.

**Odbiór pozyskania obu odpowiedzi zamknięty.** Nie powtarzać tych operacji.
**Jezioro z wyspą pozostaje otwarte:** zero interior_rings w próbce. Odpowiedź
nie dostarcza także rzeczywistego MultiPolygon ani cieku przecinającego oba
wycinki. Nie przypisujemy tych przypadków do PASS na podstawie fixtures.
Następny krok: transfer istniejących artefaktów do ignorowanego lokalnego
instance/provider-captures, minimalizacja fixtures i testy offline na pełnych
geometriach. Sama liczebność raportu nie zastępuje dostępu do geometrii.

### 2026-10-24 — pełne geometrie wodne: fixtures i odtworzenie lokalne

Odczytano skopiowane artefakty z ignorowanego instance/provider-captures/
chaos-water-region-ZLZnBM. Zapisano minimalne fixtures obu profili, zachowując
wszystkie ID, współrzędne i tagi klasyfikacji; pominięto pomiary area_m2/length_m.
Metadata zawiera SHA-256 osobno body/headers/report, hash fixture z LF,
fetched_at, revision 9, nagłówki kompletności, ODbL i atrybucję OSM/MapLark.
Surowe pliki pozostają prywatne i nie są dodane do commita.

Nowy test_world_region_water_reference.py: 5 PASS / 1.120 s. Testy wykazały:
- waterways: właściwa linia osm:way:287683438 przecina bbox, choć oba końce
  znajdują się poza nim; cała linia zachowana, bez clippingu;
- nadmiarowy osm:way:1158230038 wykluczany dokładnym predykatem; nieprzefiltrowany
  batch nie przechodzi walidacji area i nie zostawia częściowego snapshotu;
- zapis i SQLite backup/restore do osobnej bazy zachowują pełne obiekty;
  podobszary waterways 1/0 i inland_water 3/1 odczytane bez HTTP;
- pusty prawy wycinek cieku jest pełnym pustym wynikiem w syntetycznym kontrakcie
  testu, a zapytanie poza dowodem lub o inną warstwę daje MISS;
- sam zapis obserwacji nie daje regionalnego odczytu bez jawnego certyfikatu.

Certyfikaty, provider fixture i czas publikacji w testach są syntetyczne.
Geometrie rzeczywiste. Nie odświeżono starych danych produkcyjnych ani nie
przeniesiono testowej zgody do MapLark. Żadnego nowego HTTP lub zapisu na VPS.
Brak otworów/multipart w rzeczywistej próbce pozostaje jawną luką odbioru.
Cały zestaw regionalny po dodaniu fixtures: **54 PASS / 24.230 s**.

## 25.10.2026 — odbiór pakietu i następny dowód wodny

Operator potwierdził skanowanie, hakowanie i łączenie w terytorium na nowym
oraz istniejącym koncie. Wcześniej przekazał 365 testów VPS PASS,
baseline_matches, HTTP 200 i pm2 save. Odbiór wdrożonego pakietu PASS;
nie oznacza to uruchomienia geografii ani zamknięcia wszystkich D01–D16.

Przygotowano jeden kolejny blok serwerowy dla brakującej geometrii wodnej:
`tools/world_water_topology_acceptance.sh`. Domyślnie plan bez DB/HTTP,
--execute najwyżej jeden request; prywatne capture i ocena offline, bez
ingest/registry/PM2. Bbox deterministycznie identyfikuje operację, niepewny
koszt pozostaje zarezerwowany, wspólne okno 40 kredytów nie odnawia się samo.
Stary region jest odrzucany na rzecz zapisanych odpowiedzi.

Naprawiono ocenę dowodów: otwór/MultiPolygon w obiekcie spoza bbox lub
niewłaściwej warstwy nie zalicza próby wybranej wody. Liczniki raw zachowano,
dodano selected IDs i osobne flagi holes/multipart. CLI --require-water-holes
i --require-water-multipart zwraca exit 2 przy braku dowodu, bez ponawiania API.
Otwór jest cechą pełnego wybranego obiektu; nie twierdzimy, że leży w bbox.

Walidacja lokalna: **8 nowych testów PASS (1.429 s)**, regresja regionalna
**54 PASS (7.739 s)**, bash -n oraz git diff --check PASS. Plan dla kandydata
16.79,52.26,16.80,52.27: zero HTTP, rezerwacja 20, deadline 35 s.
Żadnego produkcyjnego wywołania MapLark ani aktywacji. Źródła wyboru jeziora,
komendy i interpretacja wyniku: [instrukcja wodna](../runbooks/world_region_water_probe.md).

VPS na 4628c91: 8 testów nowej próby PASS (5.533 s), regionalne 54 PASS
(22.496 s). Wykonanie zatrzymało się na `background_priority_required`,
capture `/home/johndoe/chaos-water-topology-2bbMFJ`. Z kolejności kodu wynika
zatrzymanie przed reserve i transportem; nie jest to awaria dostawcy.
Naprawa: jawny priorytet w podpowłoce skryptu, kontrola konfiguracji przed
zapisami w capture. Regresja brak flagi → zero kosztów/wyjścia/scope →
wznowienie tej samej operacji: PASS. Lokalne zestawy po poprawce:
9 PASS (1.588 s) i 54 PASS (7.276 s). Wynik pobrania nadal oczekiwany.

## 25.10.2026 — rzeczywista powierzchnia wody z otworami, VPS PASS

Po ustawieniu priorytetu tylko dla CLI operator przekazał udaną próbę
`region:water-topology-v1:4620c4a60d067b8199ec124e`, revision 9.
Capture: `/home/johndoe/chaos-water-topology-wSpl56/capture`;
fetched_at 1792917291.8601255. Jeden request, 3 kredyty reported/settled
z rezerwacji 20. Brak zmiany gameplay, registry i world ingest.

Raport: bbox 16.79,52.26,16.8,52.27, natural=water, clipGeometry=false;
complete, jeden obiekt `osm:relation:3654250`, Polygon z dwoma otworami,
zero invalid/wykluczeń. Obiekt przecina obie połowy regionu; unia wyborów
zgodna z parent. `requested_topology_pass=true` w osobnym odczycie offline.
To dowód rzeczywistej odpowiedzi z otworami; nie MultiPolygon (liczba 0).
Pełność odpowiedzi nie certyfikuje selekcji regionalnej ani wersji datasetu.

Źródło tego odbioru: JSON-y przekazane przez operatora. Pliki body/headers/report
nie są jeszcze dostępne lokalnie; ich transfer jest potrzebny do utrwalenia
fixture z hashami i sprawdzenia rzeczywistych pierścieni po storage/restore.
Nie odtwarzać współrzędnych z samego raportu i nie ponawiać requestu.

### Otrzymane pliki — realne otwory i restore lokalny PASS

Operator skopiował `chaos-water-topology-wSpl56` do
`instance/provider-captures/`. Odczytano body/headers/report; oryginały
pozostały niezmienione i poza commitem. Minimalny fixture
`maplark_inland_water_holes_20261025.json` zachowuje OSM ID oraz wszystkie
współrzędne, tylko tagi natural/water/type; pomija nazwę, odnośniki i area_m2.
Metadane zawierają SHA-256 trzech źródeł oraz fixture, datę źródłową,
revision 9, nagłówki kompletności/kosztu i atrybucję ODbL/OSM/MapLark.

Rzeczywista geometria: Polygon, 608 punktów obrysu, otwory 40 i 46 punktów.
Pierwszy otwór leży poza bbox, drugi przecina bbox. Cztery nowe testy:

- tożsamość, dokładne współrzędne, topology holes=true i multipart=false;
- publikacja w izolowanej bazie, ponowne otwarcie, SQLite backup/restore:
  obie połowy regionu zachowują cały obiekt z oboma otworami bez uproszczeń;
- mały bbox wewnątrz części wyspy objętej dowodem zwraca COMPLETE_FRESH
  z pustą wodą; bbox drugiej wyspy poza dowodem daje MISS; bbox w wodzie
  zwraca pełne jezioro, zapytanie o land_water nie przejmuje coverage;
- prawdziwe otwory nie nadają certyfikatu regionalnego: bez certyfikatu
  publikacja area jest odrzucana, same obserwacje nie dają local hit.

Certyfikat, provider i zegar publikacji są testowe; nie odświeżono snapshotów
produkcyjnych. Żadnego HTTP, użycia kluczy ani zmiany PM2. Testy nowej próbki:
4 PASS (0.466 s); cała regresja regionalna: **58 PASS (8.434 s)**.
Zamknięto brak rzeczywistej próbki Polygon z otworami i jej lokalny storage/restore.
Rzeczywisty MultiPolygon, kwalifikacja źródła/wersji i aktywacja pozostają osobno.

## 25.10.2026 — seria 100 acquisition i kontrola budżetu, offline

Dodano `tools/world_concurrency_benchmark.py`: cztery procesy acquisition,
jeden background, izolowana tymczasowa SQLite, rzeczywisty kod admission
i rezerwacji/rozliczenia z wbudowanym transportem testowym. 100 prób live,
jedna próba tła konkurująca i dziewięć po zakończeniu procesów live.
Ograniczenia CLI: 4–100 live, 2–10 tła, budżet 20–1000; brak parametru bazy.
Procesy są sprzątane także przy błędzie/watchdogu. Zero HTTP i produkcyjnych zapisów.

Windows, oddzielne przebiegi, transport pusty 20 ms, koszt 3, rezerwacja 20:

| Budżet | Live sukces / budget / busy | Tło sukces / budget / busy | Naliczono | Czas całkowity |
| --- | --- | --- | ---: | ---: |
| 100 | 27 / 72 / 1 | 0 / 9 / 1 | 81 | 34.000 s |
| 500 | 95 / 0 / 5 | 9 / 0 / 1 | 312 | 59.547 s |

W obu próbach checks wszystkie true: 110 wyników, max_inflight=1,
naliczenia = 3 × wywołania transportu = 3 × operacje, bez przekroczenia budżetu,
bez pozostawionych lease, integrity OK. Pozostałe 19 przy limicie 100 nie
wystarcza na rezerwację 20, więc odmowy są oczekiwane. PASS dotyczy tych
niezmienników, nie gwarancji sukcesu każdego skanu.

P50/P95 wszystkich prób (łącznie z odmowami): dla limitu 100 live 1.063/2.141 s,
tło 0.078/0.109 s; limit 500 live 2.281/2.704 s, tło 0.219/0.266 s.
To nie SLO: brak serwera web, rzeczywistego HTTP, geometrii, 100 jednoczesnych
użytkowników i produkcyjnej maszyny. Priorytet FIFO i fairness wymagają
odrębnych testów; benchmark ich nie dowodzi. Nie zmieniono limitów produkcji.

Testy narzędzia: 2 PASS (2.399 s), w tym pięć procesów przy budżecie 20,
jeden transport/3 kredyty i brak tworzenia bazy dla niepoprawnych limitów.
Komendy do następnego wspólnego odbioru dodano do runbooka fazy 4;
nie wymagają klucza API, restartu ani aktywacji discovery.

Regresja `test_world_upstream_priority.py`: 6 PASS (2.345 s), obejmuje FIFO,
pierwszeństwo oczekujących live, in-flight bez preempcji, cztery procesy+tło
i wspólny budżet. Łącznie z nowym narzędziem 8 testów PASS.

## 25.10.2026 — odroczenie admission nie zużywa prób pobrania

Przegląd po benchmarku wykazał błąd: claim zwiększa attempts, a każda odmowa
admission trafiała do ogólnego DEFERRED. Trzy ustąpienia graczom mogły zakończyć
zadanie FAILED_TERMINAL bez HTTP. Test regresyjny najpierw odtworzył błąd
(attempts 1 zamiast 0), następnie przeszedł po poprawce.

Dodano atomową ścieżkę `defer_admission`: dla sześciu jawnych powodów
braku slotu/circuit/pojemności/budżetu oddaje wyłącznie bieżącą próbę claim,
zachowuje historyczne próby i expires, ustawia 60 s oczekiwania oraz reason.
Warunki: aktualny owner, LEASED, ważny lease/popyt, brak operation w zadaniu
i brak `discovery:<job>` w księdze kosztów. Worker wywołuje ją wyłącznie przy
zero wywołań transportu i znanym błędzie POI/kontraktu. Nie obniża licznika
po możliwym HTTP; kwarantanna, koszt i limit rzeczywistych prób nie są resetowane.

Testy: pięć kolejnych ustąpień live, potem pojedynczy commit; wielokrotne
oczekiwanie na budżet z wcześniejszą próbą i niezmiennym expires; odmowa
odroczenia po rezerwacji, w FETCHING, przy złym ownerze i wygasłym popycie;
błąd o nazwie upstream_busy rzucony przez transport nadal daje kwarantannę.
Cały discovery: **63 PASS (20.275 s)**. Bez migracji, zmian flag, HTTP ani VPS.
Historycznych FAILED_TERMINAL nie przywraca się automatycznie.

Pełna regresja `test_world_*.py` po zmianie: **294 PASS (67.996 s)**.

## 2026-10-25 — zbiorczy odbiór sektora na VPS

Pakiet a480269: 317 World + 92 POI PASS, migracja i reload web potwierdzone.
Pakiet 84e68bd: roads/waterways/inland_water, trzy COMMITTED, 82 obiekty,
9 kredytów settled, osobny proces planowania bez nowych zadań, integralność
bazy i końcowy baseline PASS. Szczegóły: `world_collection_integration_20261025.md`.
Collector jednorazowy, worker PM2 stopped, retencja 1800 s. Nie oznacza to
aktywacji stałego archiwum, pełnego pokrycia ani ukończenia całego 161–163.

## 2026-10-25 — Geoapify: rzeczywisty zapis archiwalny

VPS fa7fc69: 40 testów PASS, jeden request Geoapify, 63 obserwacje POI,
7 dni retencji i kontrola odczytu PASS. Zachowano stare 20 kredytów uncertain,
nowe 5 pozostaje uncertain; 25/25 dotyczy wyłącznie jednorazowego okna.
Baseline produkcyjny bez zmian. Szczegóły i identyfikator snapshotu:
`world_collection_integration_20261025.md`, sekcja „VPS fa7fc69”.
Źródło nie ma uprawnień normal_scan/background_refresh; nie deklarować
uruchomienia Geoapify jako fallbacku gry ani ciągłego kolektora.

## 2026-10-25 — VPS 07fd761: ograniczony kolektor online

90 testów PASS. Permit 24 h dla sektora 2036/5153 i trzech warstw,
retencja 7 dni, budżet zakresu 60/20. Zachowano wcześniejsze COMMITTED:
plan jobs=[]; świeży cykl idle/network_calls=0, pid=4086017,
at=1792935684.944692. Runtime web i workera zgodny; stderr pusty.
Odhaczono start i cykl procesu. Nie wykonano nowego pobrania ani ekspansji;
brak automatycznego odnawiania permitu i harmonogramu odświeżania 7 dni.
Szczegóły i ograniczenia: world_collection_integration_20261025.md.
