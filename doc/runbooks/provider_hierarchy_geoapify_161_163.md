# Hierarchia źródeł i Geoapify — pakiet przed próbą VPS

24.10.2026. Kod lokalny; brak aktywacji lub nowych wywołań API dostawców.

## Co zmienia pakiet

`CHAOS_POI_ROUTING_ENABLED=0` w obu ecosystemach zachowuje obecną ścieżkę.
Po osobnym włączeniu router obsługuje pełne skany POI: świeży exact cache
wszystkich dopuszczonych źródeł, zgodny odczyt świata, źródła sieciowe w zadanej
kolejności, a następnie dozwolone starsze dane. Odczyt kanonicznego świata jest
obecnie zintegrowany dla MapLark i zachowuje dotychczasowe ograniczenia pilota.
Nie wykorzystujemy niecertyfikowanych snapshotów Overpass jako zgodnych danych.

Najwyżej trzy źródła i jedna próba sieciowa na źródło, jeden deadline skanu
do 110 s, najwyżej 35 s na wywołanie. MapLark zachowuje wspólną księgę,
slot HTTP, scope, cache, limity i allowlistę pilota. Overpass korzysta z tego
samego slotu, circuit breaker i bezpiecznego transportu. Nie ma automatycznego
powrotu do adresów spoza skonfigurowanej listy. Pusty kompletny wynik jest
sukcesem, nie powodem do próby kolejnego dostawcy. Błąd konfiguracji/cofnięcie
zgody/anulowanie nie są traktowane jak awaria pozwalająca ominąć zabezpieczenie.

Zmiana route revision w trakcie skanu przerywa jego publikację. Cache Overpass
nowej ścieżki jest rozdzielony po źródle i rewizji. MapLark zachowuje swój obecny
klucz cache; ustawienie domyślne jest zgodne z dotychczasowym wyborem MapLark.
Log `poi_route` i obserwacje admina pokazują wybór/pominięcie/błąd bez pozycji gracza.

Admin ma po trzy pozycje dla sześciu warstw i dwóch trybów: live/background.
Zapis może przygotować niedostępne źródło, ale pokazuje przyczynę jego pominięcia.
Geoapify nie może zostać pełnym skanerem przez samo ustawienie priorytetu.
Przywrócenie poprzedniej kolejności nie przywraca uprawnień ani kluczy dostawców.
Budżety widoczne w panelu to księga CHAOS, nie saldo konta dostawcy.
Konfiguracja background jest respektowana przez przygotowane biblioteki
producenta i wykonawcy po włączeniu routing; nie uruchamia daemona ani nowego HTTP.
Drogi/cieki/jeziora/coastline nadal wymagają osobnego pilota; land_water niewspierane.

## Geoapify: możliwości i granica odbioru

Oficjalna [dokumentacja Places](https://apidocs.geoapify.com/docs/places/), odczyt
24.10.2026, opisuje kategorie, offset/limit, POST z filtrem i nagłówkiem x-api-key
oraz koszt zależny od liczby wyników. Implementacja używa POST i nagłówka:
klucz nie trafia do URL, raportów ani logów. Transport zachowuje publiczny DNS,
pinning, TLS, blokadę przekierowań i proxy oraz limit odpowiedzi.

Próba obejmuje do trzech stron po 100 wyników, wspólne 35 s i 15 minut odstępu
między próbami. Każda strona rezerwuje 5 kredytów we wspólnej księdze konta
geoapify; domyślna próba ma jedną stronę. Brak potwierdzonego charge header
pozostawia koszt niepewny, także po sukcesie. Nie przypisujemy taryfowego szacunku
do pola rzeczywistego naliczenia. Nierozliczone koszty nie znikają przy zmianie dnia.

Koniec krótkiej strony nie dowodzi pełnego profilu CHAOS. Raport podaje liczbę
obiektów, obecność ID OSM, klucze tagów, powtarzanie stron i truncation. Nie
tworzymy sztucznych tagów z kategorii ani geometrii dróg z punktów Places.
Brak pełnego kontraktu daje `gameplay_approved=false` i
`geoapify_contract_unverified` w hierarchii. To przygotowana integracja pobierania
i diagnostyki, nie odebrany zamiennik skanera. Rzeczywista próbka VPS pozostaje
potrzebna przed ustaleniem dopuszczalnego profilu i jego eksportu do gameplayu.

## Kolejność na VPS — dopiero po puszu pakietu

1. Pobrać kod i uruchomić regresję na izolowanych bazach:

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi*.py'
```

2. Sprawdzić właściwą ścieżkę POI (poniżej domyślna), wykonać dry-run,
a następnie przygotowanie z nową kopią SQLite. Narzędzie nie zmienia flag,
księgi, game.sqlite3 ani konfiguracji dostawców istniejących w rejestrze.

```bash
umask 077
.venv/bin/python tools/provider_routing.py --db data/poi_cache.sqlite3
.venv/bin/python tools/provider_routing.py --db data/poi_cache.sqlite3 \
  --backup-dir "$HOME/chaos-backups/provider-routing-$(date -u +%Y%m%dT%H%M%SZ)"
```

3. Pozostawić routing=0, ingest/read=0, discovery=passive, wiek bez zmian.
Przeładować właściwy plik i sprawdzić /launch oraz admin:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env
```

4. Przygotować kandydata Geoapify (domyślnie wyłączony) i budżet diagnostyczny
20 kredytów do końca dnia UTC. Powtórzenie nie zeruje zużycia:

```bash
.venv/bin/python tools/geoapify_probe.py --db data/poi_cache.sqlite3 --prepare-budget
```

W istniejącym formularzu decyzji admina zatwierdzić wyłącznie small_probe,
z referencją do powyższej dokumentacji i zakresem tej ograniczonej próby.
Nie włączać normal_scan ani background. Klucz CHAOS_GEOAPIFY_API_KEY musi być
w środowisku procesu uruchamiającego CLI; nie wkładać klucza do argumentów,
repozytorium, zrzutów PM2 ani rozmowy. Klucz zapisany wyłącznie w prywatnej
konfiguracji PM2 nie jest automatycznie dostępny w powłoce SSH.

```bash
.venv/bin/python tools/geoapify_probe.py --db data/poi_cache.sqlite3
.venv/bin/python tools/geoapify_probe.py --db data/poi_cache.sqlite3 --execute
```

Pierwszy raport to plan bez sieci; drugi to jedna kontrolowana strona.
Przekazać sam raport JSON. Błąd lub wynik niepełny nie uzasadnia pętli prób.
Przed kolejną próbą rozstrzygnąć przyczynę i ewentualny niepewny koszt.

5. Osobno odebrać nową hierarchię z jednym MapLark, dopiero potem fallback.
Geoapify pozostaje pomijane do odbioru zgodności. Nie włączać ponownie publicznych
Overpassów wyłącznie dlatego, że istnieją na liście. Ich aktualne zgody i testy
muszą odpowiadać wykorzystaniu. Po odbiorze konfiguracji wykonać pm2 save.

Rollback: ustawić routing=0 w ecosystem.web.config.js i przeładować tylko chaos.
Nie odtwarzać starej bazy nad aktualną księgą kosztów. Przywrócenie kolejności
w adminie jest osobną operacją i nie zeruje historii ani opłat.
