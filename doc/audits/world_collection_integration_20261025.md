# Lokalny pakiet zbierania świata — 2026-10-25

Zakres: kolekcja obserwacji i integracja istniejących modułów, bez włączania
geografii w gameplay i bez zmian produkcji.

## Wykonane

1. MapLark `sector-bbox-v1`: rzeczywisty prostokąt sektora zamiast domyślnego
   koła 300 m; stare pozwolenia i zadania zachowują poprzednią semantykę.
   Nowa tożsamość zadania, filtrowanie przy claim i jawny kontekst pobrania.
2. Poprawne niepełne wyniki sektora mogą być przechowywane jako PARTIAL,
   bez nadawania COMPLETE. Skaner live nadal odrzuca niepełne odpowiedzi.
3. Osobna retencja archiwum, bez przedłużania TTL odczytu skanera. Domyślna
   retencja bez zmian; przedłużenie wyłącznie jawne, ograniczone terminem
   przeglądu źródła i wymagające world_storage. Cleanup usuwa zależności FK.
4. Geoapify `geoapify-commercial-v1`: istniejący adapter/transport POST,
   wspólna kolejka i priorytet, własny ledger, zapis UNKNOWN, jedna strona
   100 wyników. Pusta obserwacja UNKNOWN nie staje się dowodem pustego regionu.
   Brak raportu kosztu pozostawia rezerwację, bez resetowania wcześniejszych
   niepewnych operacji. small_probe nie wystarcza do uruchomienia kolekcji.
5. Domyślna hierarchia routera live: dopuszczony Overpass → MapLark;
   najwyżej trzy źródła, osobne grupy operatorów, zachowane ręczne trasy,
   circuit breaker, deadline i cache. Geoapify nie udaje pełnego skanu POI.
6. Zbiorczy skrypt przygotowania VPS, kontrola collection_schema_ready,
   instrukcja migracji i rollbacku bez utraty ledgeru.

## Sprawdzenie

- World Discovery: 313 testów PASS / 204,661 s (po dodaniu Geoapify).
- Zmieniona hierarchia: osobno 13 testów PASS / 14,319 s po zmianie domyślnej
  kolejności i aktualizacji oczekiwania restore. Test potwierdza również
  fallback Overpass 502 → MapLark bez konfiguracji ręcznej trasy.
- POI: 92 testy PASS / 114,755 s po zmianach magazynu.
- Kolekcja: 75 testów discovery PASS / 63,074 s, obejmujące koszty,
  blokady, migrację, stare pozwolenia, Geoapify i zmianę uprawnień w locie.
- Playwright MCP, izolowany tools/poi_admin_fixture.py --world --routing:
  PL/EN, 1440/390 px, zmiana/zapis/przywrócenie hierarchii, brak overflow
  i pageErrors. Przeglądarka zamknięta, fixture zatrzymany.
- bash -n nowego skryptu i git diff --check PASS.

Testy korzystają z atrap dostawców i tymczasowych baz. Nie wykonano płatnych
zapytań, zmian VPS, migracji produkcji, włączenia flag ani push.
Sprawdzono publiczną dokumentację Geoapify Places:
https://apidocs.geoapify.com/docs/places/ — istniejący profil commercial,
filtr kołowy, paginacja oraz POST/x-api-key. Nie wyciągamy z tego równoważności
z całym kontraktem skanera ani potwierdzenia salda konta operatora.

## Granice i następny etap

Pakiet gotowy do wstępnego wdrożenia i przygotowania schematu; nie jest to
pełny PASS produkcyjny sprintów. Nadal wymagany jest odbiór ograniczonej
kolekcji na VPS z jawnymi sektorami, profilami, retencją i budżetami.
Geoapify wymaga dopuszczenia background_refresh/storage/world_storage;
wcześniejsze small_probe nie daje tych uprawnień.

Worker zbierania pełnej geometrii Overpass i produkt land_water nie zostały
dodane w tym pakiecie. Overpass obsługuje istniejący skan POI, MapLark cztery
profile geograficzne, Geoapify ograniczone obserwacje POI. Dalsze rozszerzenie
tych profili nie może być raportowane jako już działające.

Instrukcja: ../runbooks/world_collection_sector_upgrade.md.

## Korekta po pierwszym przebiegu VPS

Operator uruchomił `world_collection_acceptance.sh --prepare` na b9de0da.
Baseline PASS; 315 testów World zakończyło się jednym błędem:
`test_background_hierarchy_requires_layer_selection_and_rechecks_changes`,
`KeyError: priority`. Minimalny wpis dostawcy w fixture workera nie zawierał
pola porządkującego. Nowy domyślny routing odczytywał je bez wartości zastępczej.
To błąd finalnego pakietu, nie potwierdzona różnica działania Windows/Linux.
Wcześniejszy lokalny PASS nie stanowił pełnej regresji końcowego b9de0da.

Skrypt zakończył się w testach, przed dry-run, backupem i migracją produkcji.
Raport VPS: `/home/johndoe/chaos-world-acceptance-jYi0eY`.
Poprawka daje brakującemu priorytetowi najniższy ranking 100 i nie przelicza
domyślnych kandydatów podczas odczytu zapisanej trasy. Dodano regresję obu
przypadków; istniejący test workera nadal odtwarza pierwotny przypadek.
Nie zmieniono uprawnień źródeł ani flag aktywacji.

Końcowa regresja poprawki: 317 testów `test_world*.py` PASS / 196,548 s.
Kod nie był zmieniany w trakcie tego przebiegu. `git diff --check` PASS.
Na VPS powtórzyć dotychczasowy skrypt `world_collection_acceptance.sh --prepare`;
nie omijać jego testów ani nie uruchamiać workera przed przygotowaniem schematu.

## Potwierdzony odbiór przygotowania VPS — a480269

Operator przekazał pełny wynik `world_collection_acceptance.sh --prepare`:

- 317 testów World PASS / 147,065 s; 92 testy POI PASS / 77,170 s.
- Baseline PM2 zgodny: web online, discovery worker stopped; routing/ingest/
  world read OFF, discovery passive, age flag 0.
- Dry-run: original_data_unchanged true; migracja: schema_ready.
- Końcowy raport: integrity/FK ok, collection_schema_ready true,
  metrics_schema_ready true, world_schema 2.
- Przed/po: 2 snapshoty, 135186 logicznych bajtów, 104 elementy; jedno stare
  zadanie COMMITTED, brak nierozstrzygniętych zadań i wygasłych leases.
- MapLark: 23/800 dziennie, 99/24000 rolling, 0 unresolved. Geoapify:
  brak aktywnego okna, zachowane 4 wcześniejsze niepewne operacje / 20 rezerwacji.
- Backup: `/home/johndoe/chaos-backups/collection-4vrQG8Os`.
- Raporty: `/home/johndoe/chaos-world-acceptance-38D2M4`.

Początkowe collection_schema_ready false pochodzi z kontroli przed migracją;
końcowe true potwierdza przygotowanie. Nie jest to błąd przebiegu.
Skrypt nie restartował web, nie uruchamiał workera, nie wykonywał zapytań
do dostawców i nie zmieniał środowiska. Reload web i odbiór aktywnej kolekcji
pozostają oddzielnymi, jeszcze niepotwierdzonymi etapami.

Operator następnie potwierdził reload web: baseline_matches, HTTP 200 i pm2 save.
Web online, routing/ingest/read OFF, discovery passive, worker stopped.
Przygotowano następny odbiór: trzy warstwy MapLark (roads, waterways,
inland_water) w sektorze 2036/5153, do trzech requestów, 60 kredytów wspólnie,
20 na warstwę, jedno pozwolenie godzinne, retencja 1800 s. Bez zmiany rejestru,
limitów konta i konfiguracji PM2. Nowe narzędzia mają domyślny tryb planowania,
backup przed zmianami i nie odnawiają istniejących limitów/pozwolenia.

## Odbiór trzech warstw na VPS — 84e68bd, PASS

Operator przekazał wynik `world_collection_execute.sh --execute`:

- 5 testów przygotowania PASS / 8,540 s; baseline zgodny przed i po.
- Sektor 2036/5153; trzy nowe zadania COMMITTED, po jednej próbie.
- inland_water: 4 obiekty; roads: 76; waterways: 2. Łącznie 82 obiekty
  w trzech nowych snapshotach observations/UNKNOWN.
- Dokładnie 3 requesty po 3 kredyty settled: łącznie 9. MapLark dziennie
  23→32/800, rolling 99→108/24000, unresolved 0.
- Oddzielny proces planowania: jobs [], network_calls 0. Potwierdza brak
  ponownego przygotowania tych zadań; nie jest testem restartu demona PM2.
- Magazyn: 5 snapshotów, 245972 logicznych bajtów; integrity/FK ok;
  wszystkie 4 historyczne i nowe zadania COMMITTED, brak wygasłych leases
  i nierozstrzygniętych zadań.
- Web online, worker stopped; discovery passive; routing/ingest/read OFF,
  age 0. Geoapify zachował 4 stare niepewne operacje, bez aktywnego okna.
- Backup/permit: `data/collection-sector-2036-5153-v1/` na VPS.

Complete odpowiedzi dostawcy nie oznacza potwierdzonego pokrycia regionu.
76 dróg i 2 cieki to obiekty źródłowego wyniku, nie liczba po dokładnym
filtrowaniu przecięcia geometrii sektora. Wcześniejszy kwalifikowany pilot
odrzucał envelope false positives, dając 75 dróg/1 ciek. Collector zachowuje
materiał źródłowy bez dowodu area coverage; nie twierdzi, że false positives
zniknęły. Snapshoty zachowują pełne geometrie.

Odhaczono bounded collection → commit → raport administracyjny → osobny plan
bez nowych zadań → settled koszt → niezmieniony baseline. Nie ponawiać tych
trzech pobrań dla samego odtworzenia PASS. Retencja nadal 1800 s; nie deklarować
stale rosnącego archiwum ani aktywnego ciągłego uzupełniania.
Odbiór dłuższej retencji, Geoapify i aktywnej hierarchii pozostaje otwarty,
podobnie jak nieobsługiwane profile geograficzne Overpass i źródło land_water.

## Pakiet archiwum / Geoapify — przygotowanie lokalne

Operator zatwierdził 7 dni retencji oraz jeden test kolektora Geoapify z
rezerwacją 5 kredytów, z zachowaniem wcześniejszych kosztów niepewnych.
Nie aktywowano tych parametrów produkcyjnie.

Dodano `world_activation_readiness.py`: odczyt spójnej kopii SQLite, zestawienie
brakujących scopes, terminów review, budżetów, dawnych niepewnych operacji,
tras live/background i aktualnych rekordów retencji. Nie zmienia rejestru,
budżetu ani uprawnień; nie sprawdza sieci i nie deklaruje gotowości endpointu.

Test integracyjny retencji przechodzi przez publikację workerem, otwarcie
repozytorium z dysku, symulowane wygaśnięcie świeżości, zachowanie geometrii
w archiwum i końcowe usunięcie. Zegar produkcyjny nie jest zmieniany.
Lokalne zestawy: retencja 7, diagnostyka 5, Geoapify 5, routing 15,
sector collection 7 — łącznie 39 testów PASS. Transporty są atrapami.
Składnia skryptu Bash sprawdzona przez `bash -n`.

Zbiorcza instrukcja VPS: `doc/runbooks/world_archive_geo_acceptance.md`.
Nie uruchomiono jeszcze tego pakietu na VPS. Aktualny stan rejestru i budżetu
Geoapify potrzebny jest przed przygotowaniem wykonawczej zmiany; szczególnie
nie należy obchodzić `budget_previous_period_unresolved` nowym oknem ani
nadpisywać zapisanej, celowo pustej trasy.

### Odbiór VPS i wykonawcze przygotowanie Geoapify

VPS c8bdaf1: retencja 7/5.140s, readiness 5/3.368s, Geoapify
5/4.635s, routing 15/9.442s, sector 7/5.181s — 39 PASS.
Baseline przed i po zgodny; zero requestów i zapisów produkcyjnych.
MapLark revision 9 bez blokad; Geoapify revision 2: disabled/untested,
small_probe, brak aktywnego budżetu, 4 uncertain / 20 kredytów.
Retencja produkcyjna: 0 rekordów. Routing live domyślnie tylko MapLark;
Overpass nie jest faktycznie dopuszczony do tej trasy.

Przygotowano jednorazowy `world_geo_archive_execute.sh`: backup, jawne
carry-forward kosztów, maksymalnie jeden request, kwalifikacja techniczna
na podstawie odpowiedzi, obserwacyjny zapis 7 dni i kontrola odczytu.
Wspólne acquire_features i CanonicalWorldRepository, bez nowego transportu.
Nie nadaje normal_scan/background_refresh, nie uruchamia ciągłego workera.
Nowy scenariusz integracyjny 8 PASS; budżety 17 PASS (w tym kontrola zwykłego
nowego okna, które nadal nie może ukryć starych kosztów); acquisition 10 PASS;
readiness 5 PASS. Łącznie pakiet 40 testów. Testy izolowane z atrapami HTTP;
wykonanie nowego skryptu z prawdziwym Geoapify pozostaje do odbioru na VPS.

### VPS fa7fc69 — Geoapify i archiwum 7 dni: PASS

Operator dostarczył wynik `world_geo_archive_execute.sh --execute`:

- Testy izolowane: 8/7.092s, budżety 17/4.622s, acquisition 10/2.753s,
  readiness 5/3.101s — łącznie 40 PASS.
- Dokładnie jeden request commercial, Warszawa 52.2319/21.0067, 300 m,
  limit 100; 63 obiekty, `archived_observations`, `local_readback_pass=true`.
- Snapshot `ec02e02699468cc52cb18c0211ffbf52bcccd363d6b5d217f809f9ae7ec7f806`,
  coverage UNKNOWN, 604800 s retencji, retain_until 1793538509.4345217.
- Raport potwierdza jeden aktywny rekord retencji. Nie jest to obserwacja
  rzeczywistego upływu siedmiu dni; wygaśnięcie i cleanup sprawdzono testami.
- Carry-forward: zachowano 4 stare uncertain / 20 kredytów; dodano jedną
  uncertain / 5. Łącznie 5 operacji / 25 rezerwacji, bez wymyślonego kosztu.
  Okno godzinne ma 0 dostępnych kredytów. Jego 100% oznacza wykorzystanie
  wewnętrznego limitu tego testu, nie wyczerpanie planu Geoapify.
- Geoapify revision 5: dopuszczenie do zapisu obserwacji, bez normal_scan
  i background_refresh. Pozostałe blokady background_refresh i budżetu
  są oczekiwanym wynikiem ograniczonego zakresu, nie błędem odbioru.
- MapLark nadal revision 9, 32/800 dziennie, 108/24000 rolling, bez uncertain.
- Baseline przed i po zgodny: web online, worker stopped, routing/read/ingest
  OFF, discovery passive, age 0. Nie wykonano restartu PM2.
- Backup i report: `data/geo-archive-7d-20261025-v1/` na VPS.

Nie ponawiać zapytania dla samego potwierdzenia PASS ani zwiększać limitu
testowego. Odhaczono rzeczywiste pobranie Geoapify → zachowanie kosztów →
zapis 7 dni → kontrolę odczytu. Nie odhaczono ciągłego workera Geoapify,
automatycznej hierarchii skanera ani siedmiodniowej retencji kolekcji MapLark.
Następny pakiet obejmuje te odrębne konfiguracje w granicach już ustalonych
limitów i regionów; dalsze wydatki Geoapify wykraczają poza ten pojedynczy test.

### Lokalnie — retencja istniejącego MapLark i profil routingu

Dodano atomowe retain_saved dla maksymalnie 10 jawnych identyfikatorów;
CLI tego wdrożenia obejmuje dokładnie trzy wcześniej odebrane snapshoty.
Waliduje digest, bieżącą rewizję MapLark, scopes storage/world_storage,
termin review i wiek danych. Zapisuje decyzję w istniejącej world_retention,
bez zmiany payloadu, pochodzenia, świeżości, kosztów lub pokrycia.
Deadline to fetched + 7 dni; idempotencja nie przedłuża terminu.
Brak snapshotu lub sprzeczna decyzja zatrzymuje całość bez refetch.

Przygotowano profile ecosystem.web.config.js routing/baseline i jawne
oczekiwanie --routing 0/1 w runtime checkerze. Domyślny profil nadal OFF;
wdrożeniowy skrypt wymaga początkowej trasy wyłącznie MapLark i nie zmienia
decyzji o dostawcach. Nie wykonano jeszcze reloadu produkcyjnego.

Lokalnie: saved retention 7 PASS (7.229s), release package 4 PASS (0.114s),
readiness 6 PASS (4.186s), routing 15 PASS (12.079s): 32 PASS.
Sprawdzono bash -n i node --check ecosystem.web.config.js.
Brak zmian UI, żądań do dostawców i produkcyjnych mutacji w lokalnym teście.
Instrukcja wspólnego wdrożenia/odbioru/rollbacku w world_archive_geo_acceptance.md.
Retencja przyszłych permitów i ciągłe uruchomienie workera pozostają osobnym
nieodebranym etapem; ten pakiet ich nie oznacza jako wdrożonych.

### VPS c1f4608 — retencja MapLark i routing odebrane

32 testy PASS: saved retention 7/6.299s, routing 15/9.678s,
release package 4/0.028s, readiness 6/4.233s. Trzy wskazane snapshoty
MapLark zachowano do fetched+604800 bez nowego HTTP, zmian ledgeru,
payloadu lub świeżości. Raport: cztery aktywne rekordy retencji wraz z Geoapify.
Backup: `/home/johndoe/chaos-backups/routing-archive-G9Hzl4li/poi_cache.sqlite3`.
Reload web z profilem routing: routing=1, web online, worker stopped,
pozostałe flagi zgodne. Launch: trzy timeouty 000, następnie HTTP 200.
Operator potwierdził skan 37 nowych obiektów i dwa wpisy poi_route revision 0,
maplark/result success/source upstream. Jest to PASS skanu przez aktywny router;
nie dowód działania Overpass. Nie otrzymano osobnego potwierdzenia pm2 save.

### Lokalnie — ograniczony proces kolektora

Rozszerzono istniejące prepare o --bounded: ten sam sektor/profil, nowy
permit do 24 h, retencja 7 dni, cap 60/20, niezmienione limity konta.
Nie zmienia identyfikatorów istniejących zadań i nie odtwarza COMMITTED.
Kolektor --serve wykorzystuje tę samą kolejkę i transport; ma jawny profil
bounded w ecosystem.discovery.config.js, autorestart false. PermitExpired
kończy proces normalnie bez odnowienia. Dodano pid/at do logów cykli.

Launcher waliduje baseline routingu, zakres permitu, budżety i kolejność
background, po czym przekazuje klucz MapLark z weba do środowiska workera
bez drukowania wartości/PM2 JSON. Runtime checker ma jawne --worker online
lub stopped i weryfikuje włączony priorytet/routing workera oraz jego cwd.

Testy lokalne: bounded collector 6 PASS (10.806s), dawny collection prepare
5 PASS (13.411s), discovery 75 PASS (70.562s), release package 4 PASS (0.143s).
Łącznie 90 testów z izolowanymi bazami i atrapami HTTP. Scenariusze: trzy
stare COMMITTED pozostają idle po nowym permicie/restarcie; nowa publikacja
ma 7 dni; expiry kończy proces; brak sekretu/pusta trasa blokuje start.
Składnia ecosystemu i skryptu Bash sprawdzona. Nie uruchomiono jeszcze tego
profilu na VPS. Odbiór online → nowy idle/committed → restart/stop pozostaje
produkcyjnym krokiem w world_archive_geo_acceptance.md.

### VPS 07fd761 — start ograniczonego kolektora odebrany

Operator uruchomił world_bounded_collector_rollout.sh --execute.
Testy: bounded collector 6 PASS (6.937s), collection prepare 5 PASS
(6.606s), discovery 75 PASS (58.318s), release package 4 PASS (0.029s).
Łącznie 90 PASS. Przygotowano permit i backup w
`/home/johndoe/app/chaos/data/collection-daemon-2036-5153-v1/`.
Plan zawierał jobs=[]: zachowano wcześniejsze wykonane zadania.

Runtime checker potwierdził worker online, poprawne cwd, worker_enabled=1,
priority=1 i routing=1. Web pozostał online z routing=1, ingest/read=0,
discovery=passive i age=0. Świeży cykl: idle, network_calls=0,
pid=4086017, at=1792935684.944692. Wyświetlony stderr był pusty.
Starszy wpis committed bez pid/at pochodzi z wcześniejszego pilota;
nie zaliczamy go do bieżących pobrań ani kosztów.

Odhaczono start procesu i rzeczywisty cykl bez powtórnego pobrania.
Permit wygasa o 1793022081.9930966, bez automatycznego odnowienia.
Zakres nadal obejmuje jeden sektor i trzy warstwy, retencję nowych
publikacji 7 dni oraz budżet zakresu 60/20. Nie jest to dowód nowego
pobrania przez daemon, automatycznego odświeżania ani ekspansji regionów.
Potwierdzenie pm2 save oraz restart/stop tego nowego profilu na VPS
nie zostały dostarczone. Nie oznaczamy całego 161–163 jako ukończonego.

### Lokalnie — generacje odświeżania i jawne dopuszczanie regionów

Dodano trwały, ograniczony pojemnością receipt ostatniej generacji dla
demand/provider/revision/profile/acquisition. Nowe ID zadania/kosztu po
siedmiu dniach od COMMITTED, bez resetowania poprzedniego. Niepewna generacja
blokuje następną; receipt przetrwa prune zadań. Przy braku ważnego popytu,
permitu lub dopuszczenia nie powstaje pobranie. Permity domyślnie mają
refresh_seconds=0; nowe jawne 604800 wymaga MapLark i retencji 7 dni.
Legacy permit nie może claimować wygenerowanego zadania odświeżania.

Przygotowanie regionów współdzieli istniejący prepare/ledger/worker i może
wskazać do 10 komórek, bez sztucznego record popytu. Nadal cap 60/20,
24 h bez odnowienia, account limits bez zmian. Dodano profil ecosystem regions
i zbiorczy rollout z backupem/migracją. Skrypt wdraża tylko obecny sektor;
brak aktywacji nowych regionów i brak zmian gameplay w lokalnej pracy.

Weryfikacja lokalna: discovery 81 PASS (82.012s); pełne test_world_*.py
358 PASS (271.336s). Po końcowej kontroli kosztu poprzedniej generacji
refresh 7 PASS (12.001s); po dodaniu odbioru launchera regionalnego bounded
collector 7 PASS (15.207s). Collection prepare 5 PASS (14.835s).
Sprawdzono bash -n, node --check i git diff --check. Testy korzystały z
izolowanych baz i atrap transportu/PM2; nie wykonano wdrożenia ani HTTP
do dostawców. Nowa tabela wymaga migracji przed startem nowego workera.

### VPS 9aa3ffb — profil regions odebrany

Operator wykonał world_regions_rollout.sh --execute. Testy: discovery
82 PASS (58.913s), bounded collector 7 PASS (7.268s), collection prepare
5 PASS (6.561s): łącznie 94 PASS. Dry run i migracja: integrity/FK ok,
6 snapshotów, 249 members, 342097 payload_bytes przed i po migracji.

Zatrzymano poprzedni kolektor, sprawdzono runtime, przygotowano permit
`data/collection-regions-v1/permit.json` i backup w tym samym katalogu.
Zakres: sektor 2036/5153, trzy warstwy, retencja/refresh 604800 s,
budżet 60/20, do 24 h, bez automatycznego odnowienia. Plan jobs=[].
Po starcie profil regions: worker online, routing/priority/enabled=1,
cwd poprawne. Web online, routing=1, ingest/read=0, discovery=passive,
age=0. Świeży cykl idle/network_calls=0 z NOWYM pid=4088154,
at=1792937083.874129; wcześniejsze wpisy pid=4086017 są historyczne.
Wyświetlony stderr pusty. Permit until=1793023481.2894413.

Odhaczono migrację, stop poprzedniego procesu, start nowego profilu i świeży
cykl bez zbędnego HTTP. Nie jest to produkcyjny test upływu siedmiu dni,
nowego pobrania ani rozszerzenia obszaru. pm2 save nie ma jeszcze potwierdzenia.

### Lokalnie — regularne zbieranie, Overpass i stały budżet Geoapify

Dyspozycja operatora: regularna kolekcja + Overpass + Geoapify 3000/dzień;
dobór odświeżania po stronie implementacji. Pakiet korzysta z istniejących
DiscoveryJobs/Worker, CreditBudget, Registry, Routing, UpstreamPriority i
CanonicalWorldRepository. Dodatkowy koordynator wybiera anonimowy popyt,
nie tworzy drugiego magazynu ani pobrań pełnej planety.

Polityka regular-world-v1: cykl 60 s, jeden request/cykl, 100 ostatnio
odwiedzanych aktywnych komórek, trwały kursor rotacji, retencja/refresh 7 dni,
review 30 dni bez automatycznego odnowienia. Background 200 kredytów/dzień
na MapLark i Geoapify, globalne MapLark 800/24000, Geoapify 2700/83700.
Codzienne scopes współdzielą istniejące konto, nigdy nie zerują ledgeru.
Nowy popyt może wznowić wyłącznie anulowane przed wysłaniem zadanie z nowym ID.
Niepewne płatne requesty pozostają zablokowane; starych kosztów nie rozliczamy
na podstawie sum z panelu.

Overpass: out body geom, pełne linie/poligony, multipolygon z otworami i
odłącznymi częściami, niepełne relacje oznaczone jawnie. Provenance zawiera
timestamp bazy OSM, jeśli obecny. Nie certyfikujemy bbox ani oceanów.
Limit 120 prób/dzień, 3720/31 dni (jednostka request_attempts, nie credits),
35 s deadline, 4 MiB, 1001 elementów, godzinny circuit lub dłuższy Retry-After.
Odczytowy błąd Overpass ma osobną generację po backoff; następny cykl może
wybrać MapLark. Jeden cykl nie robi serii requestów fallback.

Geoapify: nowa poprawna strona do 100 wyników zachowuje 6 jednostek jako
estimated_upper_bound, charged/reported_credits pozostają null. Szacunek
liczony w dniu i rolling31; niepewne błędy i stare operacje nadal przenoszone.
Nie jest to rozliczenie według panelu ani cena gwarantowana przez dostawcę.
Źródła dokumentacji i instrukcja: world_archive_geo_acceptance.md.

Osobny monitor SQLite mode=ro co 300 s: stan cyklu, kolejka, archiwum,
budżety z jednostkami, unresolved/estimated oraz ostrzeżenia. Profil regular
w ecosystem.discovery.config.js; klucze z web/env, opcjonalnie ukryty prompt
Geoapify, bez logowania sekretów. Live routes i wiek bez zmian.

Testy lokalne: Overpass geometry/worker 5 PASS (2.846s); refresh 8 PASS
(9.398s); discovery 82 PASS (69.431s); routing 16 PASS (17.314s); credit budget
6 PASS (3.614s). Pełne test_world_*.py: 373 PASS (268.603s). Po dopracowaniu
pochodzenia danych i przeglądu polityki regular collection 9 PASS (19.418s).
Bash syntax, Node syntax i diff whitespace PASS. Użyto syntetycznych baz,
atrap HTTP/PM2; brak wdrożenia i rzeczywistych requestów do API w tej pracy.

Gotowy tools/world_regular_rollout.sh --execute obejmuje testy, backup,
migrację, konfigurację, start, świeży raport i Launch. Setup nie rozszerza
small_probe Overpass do regularnego użycia. Raport overpass_eligible/skipped
jest warunkiem uczciwego odbioru źródła; lokalny PASS adaptera nie potwierdza
dostępności ani dopuszczenia instancji na VPS. Nie zamykamy całego 161–163
przed odbiorem tego pakietu i rozstrzygnięciem konkretnego źródła Overpass.

Końcowe sprawdzenie po rozszerzeniu Registry.enable o źródła wyłącznie
archiwalne: test_poi_providers 6 PASS (4.919s), Overpass collection 6 PASS
(3.532s), regular collection 9 PASS (14.893s). Włączenie archiwizacji nie
nadaje normal_scan. Zbiorczy skrypt VPS obejmuje również testy Registry.
