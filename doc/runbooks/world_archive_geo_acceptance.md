# Odbiór archiwum i przygotowanie Geoapify — 161–163

Operator zaakceptował 25.10.2026 następny etap: retencja geometrii 7 dni oraz
jeden test kolektora Geoapify z rezerwacją 5 kredytów. Wcześniejsze nierozliczone
operacje pozostają zachowane. Nie oznacza to automatycznej aktywacji źródła,
rutingu ani ciągłego pobierania.

## Kod → wdrożenie → zbiorczy test

Na VPS:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_archive_geo_acceptance.sh
```

Nie wymaga restartu, kluczy API, migracji ani `pm2 save`. Zmiany tego pakietu
obejmują diagnostykę, testy i instrukcje; działający skaner pozostaje bez zmian.

Pakiet sprawdza na izolowanych bazach: publikację przez worker z retencją 7 dni,
ponowne otwarcie repozytorium, wygaśnięcie dostępności dla skanera po 30 minutach,
zachowanie archiwum do jego terminu oraz usunięcie bez osieroconych rekordów.
Upływ czasu jest symulowany w testach, nie zmieniamy zegara VPS ani terminów danych
produkcyjnych. Testy Geoapify i routingu używają atrap transportu.

Raport produkcyjny powstaje z tymczasowej, spójnej kopii SQLite, źródło otwierane
jest przez `mode=ro`. Nie zmienia ledgerów, snapshotów, uprawnień, kolejek, tras
ani PM2. Pokazuje:

- faktyczne brakujące uprawnienia MapLark/Geoapify i termin ich przeglądu;
- aktywne okna budżetu oraz zachowane nierozliczone operacje;
- blokadę przeniesienia nierozliczonych kosztów ze starego okresu;
- zapisane lub domyślne trasy, także celowo puste, i powody pominięcia źródeł;
- rzeczywiste rekordy dłuższej retencji.

`PASS` skryptu oznacza przejście testów i wykonanie raportu. Nie oznacza, że lista
`blockers` jest pusta ani że endpoint działa. `execution_authorized=false` jest
celowe: sam raport nigdy nie udziela zgody na zapytanie.

## Następny krok po raporcie

Na podstawie aktualnego rejestru przygotowujemy jeden ograniczony permit
Geoapify oraz budżet uwzględniający poprzednie rezerwacje. Nie zwiększamy starego
okna diagnostycznego, nie zerujemy 20 kredytów i nie wnioskujemy o koszcie
pojedynczego zapytania z sum w panelu dostawcy. Brak potwierdzonego kosztu nowego
zapytania zachowa pełną rezerwację 5 kredytów.

Geoapify zbiera obserwacje `commercial` / Point; nie zastępuje pełnego skanu
CHAOS, geometrii dróg ani dowodu pokrycia regionu. Po raporcie technicznym nadal
pozostają osobne etapy aktywacji routingu i ciągłego kolektora. Nie powtarzamy
udanego trzylayerowego pobrania MapLark tylko dla odtworzenia PASS.

Retencja 7 dni dotyczy nowej, jawnie dopuszczonej publikacji archiwalnej;
bieżący pakiet nie przedłuża już wygasłych snapshotów i nie zmienia świeżości
skanera (300/1800 s). Nie oznacza bezterminowego archiwum ani certyfikacji regionów.

## Zatwierdzony pojedynczy test — po odbiorze c8bdaf1

VPS potwierdził wszystkie 39 testów, MapLark revision 9 bez blokad retencji,
Geoapify revision 2 / disabled / small_probe oraz cztery stare niepewne
operacje o łącznej rezerwacji 20. Brak aktywnych okien Geoapify.

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_geo_archive_execute.sh --execute
```

Skrypt uruchamia 40 testów izolowanych, sprawdza baseline, pyta bez echa o
klucz Geoapify, wykonuje najwyżej jedno zapytanie `commercial` dla Warszawy
(52.2319,21.0067), promień 300 m, limit 100. Nie ma paginacji ani automatycznego
ponawiania. Plan bez wykonania: ten sam skrypt z `--plan`.

Przed mutacjami zapisuje spójną kopię bazy do
`data/geo-archive-7d-20261025-v1/poi_cache.sqlite3`. Wynik i stan przerwanej
operacji są w `report.json` w tym samym katalogu. Nie zapisuje klucza ani
nagłówków uwierzytelniania. Nie usuwać katalogu ani pozycji ledgeru, aby
ponawiać zapytanie: identyfikator operacji i budżetu jest jednorazowy.

Okno carry-forward trwa godzinę. Zawiera stare nierozliczone operacje przez
odwołania do tych samych rekordów, plus 5 kredytów nowego limitu. Przy obecnym
stanie to limit 25, zajęte 20, dostępne 5. Nie powstaje budżet cykliczny.
Późniejsze rzeczywiste rozliczenie operacji aktualizuje także przeniesiony koszt.
Zwykłe utworzenie nowego okna nadal nie omija blokady starych kosztów.

Po poprawnej odpowiedzi i normalizacji skrypt zapisuje rzeczywisty wynik testu
technicznego i decyzję o 7-dniowym archiwum. Rejestr Geoapify otrzyma stan
enabled wyłącznie z zakresami small_probe/storage/world_storage. **Nie otrzyma
normal_scan ani background_refresh**: router i kolejka automatyczna nadal je
pominą. Zapis jest obserwacją UNKNOWN, bez dowodu kompletności obszaru.
To test pobrania i archiwizacji, nie odbiór ciągłego workera Geoapify.

Oczekiwany wynik: `archived_observations`, `local_readback_pass: true`,
network_calls 1, retencja 604800 s; bez kosztu raportowanego przez dostawcę nowa
operacja pozostaje uncertain z rezerwacją 5. Powtórzenie narzędzia zwraca
`already_attempted_inspect_saved_report` bez sieci. Błąd nie uprawnia do resetu
rezerwacji. Gra, PM2 i flagi środowiskowe pozostają bez zmian; tymczasowy
priorytet tła dotyczy wyłącznie procesu testowego.

## Kolejny pakiet — zachowanie MapLark i włączenie routingu

Po PASS Geoapify przygotowano `world_routing_archive_rollout.sh`. Nie wykonuje
zapytań do dostawców. Wykorzystuje trzy dokładne identyfikatory snapshotów
odebranych wcześniej w sektorze 2036/5153 (roads, waterways, inland_water).

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_routing_archive_rollout.sh --execute
```

Pakiet: kontrola baseline OFF → 32 testy izolowane → weryfikacja trasy live
`[maplark]` → kontrola istniejących snapshotów → backup SQLite → retencja
tych trzech snapshotów → ponowna kontrola trasy → reload wyłącznie web
z profilem `routing` → kontrola flag → Launch HTTP 200.
Wariant `--check` kończy się przed backupem i mutacjami.

Retencja biegnie przez 7 dni **od pierwotnego pobrania**, nie od wykonania
polecenia. Można zachować nadal istniejącą obserwację, której przydatność dla
skanera już wygasła: fresh_until, usable_until, payload, digest, provenance,
ledger i dowody coverage pozostają nietknięte. Decyzja archiwalna trafia do
istniejącej tabeli world_retention. Ponowienie nie odnawia zegara. Wszystkie
trzy snapshoty muszą przejść walidację przed zapisem; brak jednego zatrzymuje
pakiet przed reloadem i nie powoduje pobrania zastępczego.

To uzupełnia wcześniejszą zasadę „nie przedłużamy wygasłych snapshotów”:
nie przywracamy świeżości wyniku ani usuniętych danych. Zachowujemy wyłącznie
jeszcze obecne, poprawne obserwacje mieszczące się w zatwierdzonym okresie
archiwalnym. Zmiana nie ustawia automatycznie retencji przyszłych permitów
kolektora i nie uruchamia pobierania w tle.

Konfiguracja jest zapisana w `ecosystem.web.config.js`:

- `--env routing`: routing 1;
- `--env baseline`: routing 0, wycofanie aktywacji;
- pozostałe flagi (world ingest/read OFF, passive discovery, age 0) bez zmian.

Zwykły reload bez `--env routing` wraca do bazowej konfiguracji OFF.
Po odbiorze routingu używać tego profilu przy kolejnych reloadach.
Runtime checker dla nowego stanu: `tools/world_runtime_check.py --routing 1`.

Po HTTP 200 wykonać jeden skan w grze i odczytać:

```bash
pm2 logs chaos --lines 80 --nostream 2>&1 | grep 'poi_route'
```

Oczekiwany wpis z dostawcą maplark i result success. Test może korzystać z
cache albo wykonać zwykłe płatne pobranie w ramach dotychczasowego budżetu.
Po poprawnym skanie: `pm2 save`. Nie deklarować działania Overpass tylko
dlatego, że router jest ON: aktualny rejestr dopuszcza wyłącznie MapLark.
Nie nadajemy nowych scopes, nie nadpisujemy zapisanych tras ani nie aktywujemy
Geoapify w skanerze.

Rollback routingu (zachowuje archiwum i ledger):

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env baseline --update-env
.venv/bin/python tools/world_runtime_check.py --routing 0
```

Po potwierdzeniu działania wersji bazowej można wykonać `pm2 save`. Nie
przywracać całej starej bazy POI dla wycofania flagi — cofnęłoby to nowe koszty.

## Ograniczony kolektor w tle — 24 h, sektor 2036/5153

Po potwierdzonym skanie 37 obiektów i logach poi_route/maplark/success
przygotowano uruchomienie osobnego procesu PM2. Web pozostaje na profilu
routing, bez reloadu i bez zmian age/ingest/read.

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_bounded_collector_rollout.sh --execute
```

Skrypt sprawdza runtime routing=1/worker stopped i testy izolowane, a następnie
przygotowuje nowy, **nieodnawialny automatycznie** permit:

- bbox sektora 20.36,51.53–20.37,51.54;
- roads, waterways, inland_water, acquisition sector-bbox-v1;
- do 24 godzin działania, retencja nowych publikacji 604800 s;
- 60 kredytów wspólnych / 20 na warstwę, rezerwacja 20 na operację;
- nadal obowiązuje limit konta MapLark 800/dzień i 24000/31 dni;
- brak nowych dopuszczeń źródeł, pobierania Geoapify i rozbudowy obszaru.

Backup i permit: `data/collection-daemon-2036-5153-v1/`.
Ponowne prepare nie przedłuża permitu, nie zeruje zakresów budżetu, nie
resetuje wykonanych ani niepewnych zadań. Po wygaśnięciu nie kasować katalogu,
aby automatycznie wznowić: nowa decyzja operacyjna wymaga osobnego zakresu.

Worker używa istniejącej kolejki, shared slot, pierwszeństwa graczy,
księgi kosztów i magazynu. Wykonane zadania dla obecnego sektora/rewizji są
zachowane. Zatem **idle z network_calls 0 jest poprawnym oczekiwanym wynikiem**,
nie wymaga sztucznego refetch ani usunięcia COMMITTED. Ten etap nie dodaje
harmonogramu odświeżania po siedmiu dniach ani samoczynnej ekspansji regionów.

Launcher pobiera w pamięci wyłącznie klucz MapLark z metadanych procesu web
i przekazuje go do środowiska potomnego procesu PM2. Nie wypisuje wartości,
nie zapisuje jej do kodu ani argumentów polecenia. Tak jak inne sekrety PM2,
wartość pozostaje w środowisku procesu i może trafić do chronionego dump.pm2
po pm2 save. Błąd web_maplark_credential_unavailable wymaga osobnej konfiguracji
klucza; nie wklejać go do rozmowy.

Wszystkie jawne flagi są w `ecosystem.discovery.config.js`, profil `bounded`;
autorestart false, jedna instancja, odstęp 30 s. Wygaśnięcie permitu kończy
proces kodem 0 i wpisem permit_expired. Sam restart PM2 go nie odnawia.
Logi cykli mają pid/at, dzięki czemu można odróżnić bieżący odbiór od dawnych
wpisów roads pilot. Status online nie jest jeszcze dowodem udanego cyklu.

Po nowym wpisie idle lub committed i braku błędów:

```bash
pm2 save
```

Odbiór restartu bez zmiany env/permitu, jeśli potrzebny:

```bash
pm2 restart chaos-world-discovery-worker
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online
pm2 logs chaos-world-discovery-worker --lines 12 --nostream
```

Nie używać bezpośredniego startOrReload z przypadkowej powłoki do odtwarzania
sekretu. Narzędzie world_collector_start.py kontroluje baseline, permit,
budżety i trasy przed startem. Zwykły pm2 restart zachowuje bieżące env.

Stop/rollback kolektora (web i jego routing pozostają aktywne):

```bash
pm2 stop chaos-world-discovery-worker
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker stopped
pm2 save
```

Nie przywracać backupu dla zatrzymania procesu: zniszczyłoby to nowsze wpisy
ledgeru. Przerwane zapytanie może pozostawić niepewny koszt, który zachowujemy.

## Następny pakiet — regiony i siedmiodniowe generacje

`world_discovery_refresh` przechowuje osobno ostatnią generację zadania
i termin następnego zbioru. Nie jest kasowana przy sprzątaniu zadań/snapshotów.
Odświeżenie dopuszcza wyłącznie COMMITTED po 604800 sekundach, aktualny popyt,
ważny permit i istniejące dopuszczenia/koszty. Nie resetuje historii zadania ani
księgi. Zegar liczy od potwierdzenia publikacji, nie od restartu lub zmiany permitu.
PENDING i niepewne/nieudane generacje nie są omijane przez kolejną generację.
Przy limicie wpisów planowanie zatrzymuje się bez usuwania historii.

Permity pozostają ważne do 24 h i nie odnawiają się automatycznie. Mechanizm
7 dni działa także pod późniejszym, oddzielnie dopuszczonym permitem;
obecne uruchomienie nie daje uprawnienia na stały, bezterminowy zbiór.
Stary permit z refresh_seconds=0 nie wykonuje nowych generacji odświeżania.

Zbiorcze sprawdzenie bez zatrzymania działającego kolektora:

```bash
cd ~/app/chaos
git pull --ff-only
bash tools/world_regions_rollout.sh --check
```

Wdrożenie tego samego sektora 2036/5153 (bez nowego obszaru):

```bash
bash tools/world_regions_rollout.sh --execute
```

Skrypt testuje, zatrzymuje tylko kolektor, tworzy backup SQLite, migruje przez
istniejące poi_world.py, przygotowuje `data/collection-regions-v1/permit.json`
i startuje profil `regions` z ecosystem.discovery.config.js. Web/age/read/ingest
pozostają niezmienione. Popyt nie jest sztucznie odnawiany: idle jest poprawnym
wynikiem przy świeżych danych lub braku bieżącego popytu. Po świeżym cyklu:

```bash
pm2 save
```

Dla przyszłego rozszerzenia jawna lista maksymalnie 10 komórek trafia do
`world_collection_prepare.py --bounded --cell X Y [--cell X Y ...]`.
Najpierw plan, potem --apply. Bez nowych komórek w poleceniu pozostaje tylko
obecny sektor. Wszystkie komórki dzielą te same 60 kredytów / 20 na warstwę;
limit konta 800/24000 również nadal obowiązuje. Brak rekurencyjnych sąsiadów.
Istniejący permit nie może być nadpisany ani rozszerzony tym samym ID.
Geoapify i Overpass nie są aktywowane przez ten pakiet.

Rollback: `pm2 stop chaos-world-discovery-worker`, kontrola runtime
`--routing 1 --worker stopped`, następnie `pm2 save`. Nie przywracać bazy
ani starego kodu workera nad nowszą kolejką, nie usuwać receiptów odświeżania.
Restart bieżącego profilu przez pm2 restart zachowuje permit i historię;
nie odnawia terminu jego ważności.

## Regularne zbieranie — pakiet do wdrożenia 25.10.2026

Operator zatwierdził regularne zbieranie, integrację Overpass i Geoapify
(plan 3000 kredytów/dzień, allowance 93000), delegując dobór odświeżania.
Poniższy pakiet zastępuje codzienne ręczne permity polityką obserwacji
przeglądaną po 30 dniach. Nie zmienia gry w konsumenta geometrii.

Parametry:

- Najwyżej jeden request kolektora w cyklu 60 s; wspólny slot z priorytetem gry.
- Do 100 ostatnio odwiedzanych komórek z ważnego anonimowego popytu.
  Rotacja zadań zapisana w SQLite; bez sąsiadów i skanowania całej planety.
- Roads, waterways, inland_water, coastline: dopuszczony Overpass, następnie
  MapLark. Geoapify: osobna obserwacja POI commercial/100, nie pełny skan gry.
- Retencja 7 dni, odświeżanie 7 dni od publikacji, tylko przy aktualnym popycie.
  Lokalne niedawne obserwacje dopuszczonego źródła hamują duplikaty między źródłami.
  Dane nie dostają certyfikatu COMPLETE regionu. Coastline nie tworzy oceanu.
- MapLark: niezmienione 800/dzień i 24000/31 dni; background najwyżej 200/dzień.
- Geoapify: wewnętrznie 2700/dzień i 83700/31 dni; background 200/dzień.
  Zapas względem limitu konta nie gwarantuje salda po użyciu innych aplikacji/API.
- Dla nowej, poprawnej strony Geoapify do 100 wyników pozostaje całe 6 jednostek
  rezerwacji jako `estimated_upper_bound`, bez wpisywania reported_credits.
  Szacunek liczy się w oknie dnia i 31 dni. Niepowodzenia i wszystkie stare
  uncertain nadal pozostają zarezerwowane do osobnego rozliczenia.
  Dostarczone sumy panelu 6 requests / 15 credits nie są mapowane na operacje.
- Overpass: 120 prób/dzień na dopuszczony endpoint, 3720/31 dni, jednostką
  są request_attempts, nie płatne kredyty. Timeout 25 s w QL, odczyt 30 s,
  wspólny deadline 35 s, odpowiedź do 4 MiB i 1001 obiektów z sygnałem limitu.
  Błąd daje przynajmniej godzinę cooldownu (dłuższy Retry-After zachowany).
  Późniejsza próba ma nowe ID i zużywa limit; fallback jest w kolejnym cyklu.
- Oddzielny `chaos-world-monitor` czyta SQLite mode=ro co 300 s, raportuje
  budżety, stan kolejki, szacowane/niepewne koszty, pojemność i nieświeży cykl.

Źródła interpretacji kontraktu: [Geoapify Places](https://apidocs.geoapify.com/docs/places/),
[Geoapify pricing details](https://www.geoapify.com/pricing-details/),
[Overpass full geometry](https://dev.overpass-api.de/overpass-doc/en/full_data/osm_types.html).
Przyjęto konserwatywne 6, mimo przykładu 1/20 wyników, zamiast udawać nagłówek
z rzeczywistym kosztem. Potwierdzona geometria obejmuje linie, zamknięte obszary
i relacje multipolygon z otworami. Niekompletne/zagnieżdżone/nieobsługiwane
relacje pozostają oznaczone jako niepełne; nie fabrykujemy brakujących części.

### Jedno wdrożenie i zbiorczy odbiór

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_regular_rollout.sh --execute
```

Skrypt uruchamia całą regresję `test_world_*.py` i `test_poi_providers.py`, dry run migracji i plan,
zatrzymuje tylko kolektor, wykonuje backup, migruje i zapisuje politykę.
Setup rozszerza istniejące przetestowane MapLark/Geoapify o zgodę operatora
na obserwacje w tle i retencję; nie nadaje Geoapify uprawnienia normal_scan.
Ustawia wyłącznie trasy background. Live routing i web pozostają bez reloadu.
Klucz MapLark bierze w pamięci z procesu web; Geoapify z web/env, a jeśli go
nie ma, pyta ukrytym promptem. Kluczy nie wklejać do rozmowy. Pozostają w
chronionym środowisku PM2 i jego dump po save, nie w repozytorium.

Profil `regular` jest w ecosystem.discovery.config.js. Polityka:
`data/world-collection-policy.json`. Ponowne setup nie odnawia review ani
nie czyści kosztów. Codzienne zakresy budżetu tworzy kolektor, account ledger
przenosi wcześniejsze koszty. Po 30 dniach potrzebny przegląd; nie następuje
ciche przedłużenie polityki. Monitor ma odrębny proces i nie pobiera danych API.

Skrypt czeka do 100 s na świeży zapis cyklu, drukuje raport i Launch HTTP.
Odbiór: 200; runtime zgodny; nowy cykl committed lub idle; przy committed
zapis UNKNOWN i koszt jawny. `reconciliation_required`/monitor warnings
oznaczają wynik do analizy, nie PASS dostawcy. Nie uruchamiać w pętli nowych
testów na publicznym API. Wklejenie całego wyniku wystarczy do oceny etapu.

Po poprawnym odbiorze:

```bash
pm2 save
```

Odczyt stanu bez requestów:

```bash
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-monitor --lines 2 --nostream
```

Restart/stop są możliwe bez ruszania gry i baz:

```bash
pm2 restart chaos-world-discovery-worker
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online
# rollback uruchomienia, bez cofania kosztów:
pm2 stop chaos-world-discovery-worker chaos-world-monitor
pm2 save
```

Nie wykonuj stop/rollback razem z restartem jako jednego zestawu poleceń;
wybierz działanie odpowiednie do odbioru. Restart nie resetuje częstotliwości,
terminów, historii ani kosztów. Kod nie uruchamia ponownie zakończonego
odświeżania po restarcie.

### Overpass: gotowy wykonawca a dopuszczenie instancji

Setup wypisuje `overpass_eligible` i `overpass_skipped`. Nie rozszerza zgody
small_probe do background_refresh/storage/world_storage i nie włącza
wyłączonych instancji. [Operator DE](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)
odradza użycie publicznych instancji jako stałego backendu aplikacji.
Nie przedstawiać wcześniejszego testu 200 jako zgody na regularny ruch.

Instancja dopuszczona w registry do tych trzech zakresów, tested_ok, enabled
i z review obejmującym retencję wejdzie na początek trasy po ponownym jawnym
setup --apply. Pozostałe pozostają pomijane, MapLark działa dalej. Kod i testy
Overpass można odebrać lokalnie, rzeczywisty request dopiero dla dopuszczonej
instancji. Brak dopuszczonego endpointu jest jedyną osobną decyzją źródłową
tego pakietu; nie blokuje uruchomienia regularnego MapLark/Geoapify.

Nowy Registry pozwala włączyć źródło przeznaczone wyłącznie do archiwizacji
z trzema zakresami background_refresh/storage/world_storage, bez normal_scan.
Setup korzysta z tego od razu przez CLI. Panel web załaduje tę zmianę przy
najbliższym reloadzie ecosystem.web.config.js; ten rollout nie restartuje gry.
