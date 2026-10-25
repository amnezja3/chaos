# Zbieranie sektorów — lokalny pakiet integracyjny

Status: kod przygotowany lokalnie do wstępnego wdrożenia; nie jest to
ogłoszenie ukończenia odbioru produkcyjnego 161–163.

## Co zmienia ten blok

- Domyślny routing live POI: dopuszczony Overpass (różne grupy operatorów),
  następnie MapLark. Maksymalnie trzy źródła, wspólny deadline i istniejący
  circuit breaker. Zapisana trasa administratora, również pusta, ma pierwszeństwo.
  Router pozostaje opt-in; ten pakiet nie włącza flagi na produkcji.
- `acquisition: sector-bbox-v1` pobiera prostokąt sektora 0,01° × 0,01°.
  Stare pozwolenia bez tego pola nadal oznaczają `radius-300-v1` (300 m).
- Kolejka rozróżnia oba kontrakty. Nowy worker nie przejmuje zadania starego
  kontraktu; ukończone/niepewne operacje nie są resetowane.
- Zapis zawiera sektor zapotrzebowania i parametry rzeczywistego pobrania.
  Nie zapisujemy kluczy API, nagłówków uwierzytelnienia ani identyfikatorów graczy.
- `acquisition: geoapify-commercial-v1` używa osobnego konta/budżetu Geoapify,
  warstwy `poi`, koła 300 m i maksymalnie 100 wyników kategorii `commercial`.
  Korzysta z tej samej kolejki, kontroli priorytetu i magazynu; nie uruchamia
  automatycznej paginacji ani nie zastępuje pełnego skanu gry. Brak nagłówka
  kosztu pozostawia rezerwację, także po poprawnym zapisie. Dotychczasowe
  nierozstrzygnięte operacje Geoapify nie są kasowane.
- Niepełna poprawna odpowiedź może zostać zachowana jako obserwacja `PARTIAL`.
  Nie otrzymuje dowodu kompletności regionu. Nie następuje automatyczne
  pobieranie kolejnych stron. Skaner live nadal wymaga kompletnej odpowiedzi.
- Opcjonalne `retention_seconds` oddziela przechowywanie od przydatności
  skanera: fresh 300 s / usable 1800 s pozostają bez zmian. Brak pola oznacza
  dotychczasowe 1800 s. Techniczny limit pola to 31 dni, **nie zatwierdzona
  polityka retencji dostawcy**. Dłuższy czas wymaga jawnego ustawienia,
  `world_storage` i terminu przeglądu źródła późniejszego niż koniec retencji.
- Limit bajtów i liczby snapshotów pozostaje aktywny; retencja go nie zwiększa.

## Włączenie do jednego okna wdrożeniowego

Nie wykonywać osobnego płatnego testu tylko dla tej zmiany. Poniższe kroki
włączyć do końcowego pakietu razem z pozostałą integracją źródeł.

Zbiorcza komenda przygotowania (testy, baseline, dry-run, backup, migracja,
kontrola nowego schematu; bez restartu, aktywacji i zapytań do API):

```bash
bash tools/world_collection_acceptance.sh --prepare
```

Bez `--prepare` skrypt wyłącznie testuje i wykonuje dry-run. Poniżej znajdują
się odpowiedniki ręczne do diagnostyki; nie trzeba wykonywać ich ponownie
po poprawnym zakończeniu skryptu.

1. Zatrzymać worker zbierania; zachować działający web i jego konfigurację.
2. Pull, lokalne testy na VPS i dry-run istniejącym narzędziem:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_world*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi*.py'
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics
```

3. W tym samym oknie wykonać backup i addytywną migrację:

```bash
umask 077
COLLECTION_BACKUP="$HOME/chaos-backups/collection-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$COLLECTION_BACKUP"
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics --apply --backup "$COLLECTION_BACKUP/poi_cache.sqlite3"
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics --require-collection
```

Oczekiwane: integrity/FK ok, `collection_schema_ready: true`. Migracja dodaje
kolumnę `world_discovery_job.acquisition` i tabelę `world_retention`. Zachowuje
istniejące stany zadań, klucze, operacje kosztowe i snapshoty. Brak aktywacji
HTTP, źródeł czy geometrii w gameplay.

4. Dopiero po przygotowaniu wspólnego pozwolenia uruchomić wybrane regiony
i warstwy. Nie przerabiać starego pilota na nowy zakres przez nadpisanie pliku.
Nowe pozwolenie musi korzystać z istniejących, ważnych limitów konta i zakresu.
5. Odbiór zbiorczy: request → obserwacja → lokalny odczyt administracyjny →
restart → brak drugiego requestu → kontrola kosztu → stop. `PARTIAL` albo
`UNKNOWN` są prawidłowym opisem obserwacji, nie dowodem pełnego pokrycia.
6. Zmiany trwałych flag wyłącznie w odpowiednich plikach ecosystem;
web używa `ecosystem.web.config.js`. Ten blok sam nie zmienia żadnej flagi.

## Wycofanie

Zatrzymać worker i przywrócić poprzednie flagi. Nie cofać całej bazy przez
kopiowanie backupu po wykonaniu płatnych zapytań — utraciłoby to ledger.
Zachować addytywną kolumnę/tabelę oraz nowe rekordy. Dla rollbacku kodu używać
wersji obsługującej dodatkową kolumnę (starsze INSERT bez listy kolumn nie są
zgodne). Zatrzymany worker i działający skaner to bezpieczny stan bazowy.

## Nadal otwarte przed finalnym odbiorem 161–163

Aktywacja ograniczonego profilu Geoapify po nadaniu zakresów zbierania,
konfiguracja docelowych regionów/retencji oraz zbiorczy test wykonania na VPS.
Overpass działa w routerze skanera POI; zbieranie pełnej geometrii dróg/wód
przez Overpass nie jest w tym workerze zaimplementowane. Geoapify zbiera
wyłącznie wskazany profil POI. Morza/land_water nadal wymagają osobnego źródła.
Nie oznaczać tych nieobsługiwanych profili jako PASS ani uruchomionego fallbacku.

Geoapify Places udostępnia wyszukiwanie według kategorii i obszaru oraz
stronicowanie. Integracja zachowuje dotychczasowy sprawdzony transport POST
z kluczem w nagłówku, bez dopisywania klucza do URL. Dokumentacja sprawdzona
2026-10-25: <https://apidocs.geoapify.com/docs/places/>. To nie jest dowód
równoważności kategorii Geoapify z całym kontraktem skanera CHAOS.
