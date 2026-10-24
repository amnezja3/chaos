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
