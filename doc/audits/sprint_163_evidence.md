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
