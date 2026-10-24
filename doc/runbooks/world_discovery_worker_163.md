# Sprint 163 — kontrolowany proces discovery

Status 24.10.2026: implementacja lokalna, produkcyjna aktywacja OFF.
Nie jest to instrukcja włączenia pełnego regionalnego coverage.

## Pakiet do sprawdzenia na VPS — bez API

Po push/pull uruchomić:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_world_discovery*.py'
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs
```

Pierwsza komenda używa izolowanych baz i transportu testowego. Druga wykonuje
migrację na kopii tymczasowej, nie zmienia oryginalnej bazy i nie pobiera danych.
Nie potrzeba restartu web ani zmiany aktywnych flag dla tych dwóch kontroli.

## Przygotowanie schematu po odbiorze dry-run

Przed apply wykonać backup przez istniejący tools/poi_world.py:

```bash
umask 077
DISCOVERY_BACKUP="$HOME/chaos-backups/163-worker-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DISCOVERY_BACKUP"
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --apply --backup "$DISCOVERY_BACKUP/poi_cache.sqlite3"
```

Dodawane są tabele zadań i księgi limitów, bez konfiguracji kwot, scope,
zatwierdzeń dostawcy albo flag. Powtórzenie zachowuje dotychczasowe naliczenia.
Nie dotyka game.sqlite3. Nie przywracać starej całej bazy nad nowymi naliczeniami.

## Osobna decyzja: pilot sieciowy

Propozycja: MapLark, jedna komórka (2036,5153), warstwa roads, do jednej godziny,
jedno zadanie, rezerwacja 20, limit pilota 20 i warstwy 20, pod dotychczasowym
globalnym limitem 800/dzień i 24000/31 dni. Komórka obejmuje wcześniejszą
lokalizację robota; zapytanie obecnego adaptera ma środek komórki i promień
300 m, nie oznacza kompletnego pokrycia tej komórki. Konkretny obszar i budżet
operator zatwierdza przed przygotowaniem pozwolenia. Nie jest to aktywna zgoda.

Wymagania przed pierwszym HTTP:

- Aktualny provider MapLark: tested_ok, enabled, scopes background_refresh,
  storage i world_storage. Dotychczasowe normal_scan nie wystarcza.
- Wspólny priorytet aktywny w web i workerze; samo ustawienie w workerze
  nie powoduje zgłaszania oczekujących skanów web. Sprawdzić konfigurację PM2
  obu procesów przed pilotem. Skaner zachowuje obecne limity.
- Scope księgi `discovery:<budget_id>` i `discovery:<budget_id>:roads`,
  niezmienne okno starts/ends obejmujące pozwolenie, limity jak wyżej.
  `CreditBudget.configure_scope` nie zastępuje limitu globalnego.
- Istniejący, niewygasły popyt w tej komórce. Worker nie wymyśla popytu,
  nie dodaje sąsiadów i nie pozwala na land_water bez osobnego źródła.

Plik pozwolenia (prywatny JSON, bez sekretu) ma dokładnie pola:
cells: [[2036,5153]], profiles: ["roads"], until: timestamp UTC,
reservation: 20, budget_id: zatwierdzony identyfikator pilota.
Nie podano stałego until: musi wynikać z zatwierdzonego czasu startu, maks. 24 h.
Zmiana zakresu wymaga nowej kontroli; usunięcie pliku zatrzymuje admission
i publikację podczas trwającego żądania.

## Plan i wykonanie

Operator zatwierdził 24.10.2026 opisany pilot roads (2036,5153), jedna godzina,
wewnętrzny limit 20. Przygotowanie nie oznacza uruchomienia HTTP.
Po push/pull pakietu przygotowującego:

```bash
umask 077
DISCOVERY_PILOT_BACKUP="$HOME/chaos-backups/163-roads-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python tools/discovery_pilot_prepare.py --db data/poi_cache.sqlite3 --permit data/discovery-permit.json --backup "$DISCOVERY_PILOT_BACKUP/poi_cache.sqlite3"
```

Narzędzie tworzy spójną kopię SQLite i zapis poprzedniej konfiguracji dostawcy,
permit oraz dwa limity 20: cały pilot i roads (nie sumują się do 40).
Zachowuje aktywne skany i ich zakresy, dodaje background_refresh/world_storage,
nie zmienia globalnych limitów ani naliczeń. Zmiana rewizji dostawcy może
spowodować pominięcie wcześniejszego cache. Nie zmienia flag i nie uruchamia HTTP.
Wynik zawiera plan. Pusta lista jobs oznacza brak nowego kwalifikującego się popytu;
nie należy wtedy uruchamiać wykonania. Narzędzie nie tworzy sztucznego popytu.
Ponowienie nie przedłuża pozwolenia. Wygasłego lub usuniętego pozwolenia nie
odtwarza z nowym budżetem. Błąd częściowego przygotowania wymaga sprawdzenia
stanu, nie kasowania permitu ani wpisów księgi. Przed HTTP nadal potrzebne
włączenie priorytetu web i jednorazowe wykonanie; nie uruchamiać --serve.

```bash
.venv/bin/python tools/world_discovery_worker.py --db data/poi_cache.sqlite3 --permit data/discovery-permit.json
```

Bez --execute to wyłącznie plan, bez enqueue/claim/HTTP. Przed uruchomieniem
worker wymaga schematu i scope; nie inicjalizuje ich ukradkiem.
Najpierw pojedyncze wykonanie z --execute, dopiero po odbiorze --serve.
Dedykowany `ecosystem.discovery.config.js` zawiera nazwę procesu, bazę,
ścieżkę pozwolenia i wszystkie niesekretne flagi. Dla zatwierdzonego pilota
ustawiono worker/priority ON i pojedyncze --execute (bez --serve). Sekret API
z istniejącego prywatnego środowiska serwera. Web nadal w ecosystem.web.config.js.

Przy zatwierdzonej konfiguracji uruchamianie:

```bash
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --update-env
```

Konfiguracja wykonuje jeden cykl i kończy proces; stopped po zakończeniu jest
oczekiwane. Brak autorestart zapobiega odradzaniu błędnego/wygasłego pilota.
Nie włączono pętli --serve. Najpierw przeładować ecosystem.web.config.js,
aby oczekujące skany gry zgłaszały priorytet przed startem pilota.
Koszt/quota/termin pozwolenia są sprawdzane dalej przez istniejące mechanizmy.
PM2 kill_timeout 40 s pozostawia czas na ograniczone do 35 s żądanie.
Nie zapisywać nowej listy PM2 przed odbiorem prawidłowego zachowania.

## Odbiór i stop

Oczekiwane: jeden committed i snapshot z coverage UNKNOWN; drugi cykl idle,
bez drugiego HTTP i bez naliczenia. Jest to odbiór pozyskania obserwacji,
nie certyfikat regionalnego odczytu. Sprawdzić wzrost bazy, koszt zgłoszony
przez MapLark i opóźnienie równoległego skanu gracza. Przy błędzie możliwego
HTTP zadanie trafia do reconciliation_required, nie do automatycznego retry.

Stop: usunąć/wycofać pozwolenie albo wysłać `pm2 stop chaos-world-discovery-worker`.
Zachować DB, scope, operacje i snapshoty. Wyczerpanie/expiry nie resetuje
niepewnych kosztów. Wyłączyć worker w ecosystemie przed jego ponownym użyciem.
Nie zmieniać przy tym działającego adaptera MapLark, wieku ani Identity Gateway.

## Otwarte odbiory całych 161–163

Geoapify pozostaje odłożone: commercial technicznie działa, szeroki profil
i rozbieżne rozliczenie nie są rozwiązane. Nie przenosimy tych 20 rezerwacji
do MapLark ani nie zwiększamy limitów. Pierwszy dostawca nie wymaga Geoapify.

Nadal potrzebne: certyfikacja regionalnej selekcji źródła (MapLark radius jest
exact-only), źródło/kontrakt land_water, mapa dowodów coverage i pełne agregaty
panelu D13–D16, obciążenie cztery procesy + worker i produkcyjny odbiór
poszczególnych warstw. Ten pakiet zamyka proces uruchamiania i migrację kolejki,
nie wszystkie kryteria sprintów. Pełny PASS nie może wynikać wyłącznie z CLI.
