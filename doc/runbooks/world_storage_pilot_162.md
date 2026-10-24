# Ograniczony pilot ingest/local — odbiór trwałości i rollback

## Aktualny etap — 24.10.2026

Pilot robot / 51.531034,20.366130 / 300 m przeszedł odczyt world przez innego
workera i po restarcie; operator zapisał PM2. Dowód w sprint_162_evidence.md.
Repo przygotowuje teraz flagi OFF w ecosystem.web.config.js. Produkcja pozostaje
w poprzednim stanie do wykonania poniższego reloadu przez operatora.

Po wypchnięciu zmian, na VPS:

```bash
cd /home/johndoe/app/chaos &&
git pull --ff-only &&
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env
```

Potwierdzić /launch HTTP 200, panel Ingest OFF / Read OFF / discovery passive,
jeden zwykły udany skan w grze i `pm2 save`. Nie zmieniać revision/scopes
MapLark przed sprzątaniem; nie przywracać starej bazy ponad aktualną księgę.

Po 1800 s od ostatniego ingest, przy wyłączonym pilocie:

```bash
.venv/bin/python tools/world_storage_pilot.py --lat 51.531034 --lon 20.366130 --prune-expired --apply
```

Oczekiwane network_calls=0, ledger_unchanged=true, removed_cache_entries=0.
pruned_snapshots>0 potwierdza usunięcie; zero przed wygaśnięciem jest poprawnym
no-op, nie dowodem sprzątnięcia. Wynik world_state opisuje odczyt PRZED prune.
Kolejna inspekcja bez flag mutujących powinna wykazać MISS dla usuniętego wyniku.
Nie uruchamiać dodatkowych skanów API wyłącznie do testowania sprzątania.

## Historyczna procedura przygotowania

24.10.2026. Produkcja: discovery passive, ingest/read OFF. Priorytet live
przeszedł na VPS 6 testów (3,494 s); shadow 7 (7,148 s). Nie oznacza to zgody
na zakres world_storage ani uruchomienia workera.

## Konkretny zakres do zatwierdzenia

Jedno konto, jeden punkt `lat,lon` z dokładnością do 6 miejsc, promień **300 m**,
maksymalnie 24 h. Konto i punkt wybiera operator; brak wartości blokuje pilota.
Inne konta, punkty i promienie korzystają z normalnego skanera. Konto pochodzi
z serwerowej sesji, nie pola w POST. Nie jest dodawane do kluczy cache ani
payloadów świata. Po wygaśnięciu okna odczyt/zapis świata automatycznie ustaje.

Świeżość maksymalnie 300 s, używalność 1800 s. To okres używalności, nie
automatycznego fizycznego usunięcia: sprzątanie wygasłych danych ma osobny krok.
Zapis pełnego oryginalnego wyniku normalnego skanu, bez szerszego promienia,
prefetch, retry i nowych wywołań wynikających z samego zapisu. Budżety pozostają
800/dobę UTC i 24000/31 dni, rezerwacja 20. Koszt zapytania ustala dostawca;
wewnętrzna rezerwacja nie jest jego gwarantowaną ceną maksymalną.

Warunki [MapLark](https://maplark.com/terms-of-service), odczytane 24.10.2026,
odsyłają dla danych OSM do ODbL i wymaganej atrybucji, zabraniają obchodzenia
limitów. Nie zawierają osobnej gwarancji tego zastosowania ani liczbowej retencji.
Zakres world_storage wymaga zatwierdzenia operatora; nie włączamy go automatycznie
na podstawie tego przeglądu. Nie wnioskujemy z tego zgody na masowe pobieranie,
permanentny repozytorium całego świata czy nową publiczną dystrybucję bazy.
Atrybucja OSM pozostaje wymagana. Ingest/local dotyczy exact query, nie pokrycia
sąsiednich zapytań ani odtworzenia mórz/dróg.

## Kolejność uruchomienia po zgodzie

1. Potwierdzić login, punkt i datę końca; przygotować konkretne wartości w
   `ecosystem.web.config.js`. Nie używać `Date.now()` do wyliczania końca przy
   każdym restarcie — okno ma mieć stały timestamp UTC w sekundach.
2. Sprawdzić aktualną decyzję MapLark i backup SQLite POI; zachować oryginalne
   scopes, evidence, revision i review_due_at. Nie zerować księgi.
3. Istniejący registry ma otrzymać dodatkowy scope `world_storage` z dowodem
   tego ograniczonego pilota, bez background/wide. Decyzja registry domyślnie
   wyłącza providera: przygotować ponowne enable od razu; nie pozostawić go OFF.
   Zmiana revision unieważnia poprzednie klucze cache: możliwe dodatkowe normalne
   missy graczy. Ten krok wykonać wspólnie w krótkim uzgodnionym oknie.
4. Ustawić ingest/read na 1, user/center/until według zatwierdzenia. Discovery
   pozostaje passive; priority może pozostać 0, ponieważ nie uruchamiamy tła.
5. `pm2 startOrReload ecosystem.web.config.js --only chaos --update-env`,
   `/launch` 200, jeden normalny skan zatwierdzonym kontem w tym punkcie.
6. Potwierdzić `poi_world_optional` store/stored i poprawny wynik gameplayu.

Konfiguracja będzie miała postać (obecnie w repo wartości puste i flagi 0):

```javascript
CHAOS_POI_WORLD_INGEST_ENABLED: "1",
CHAOS_POI_WORLD_REPOSITORY_ENABLED: "1",
CHAOS_POI_WORLD_PILOT_USER: "ZATWIERDZONY_LOGIN",
CHAOS_POI_WORLD_PILOT_CENTER: "LAT,LON",
CHAOS_POI_WORLD_PILOT_UNTIL: "STALY_TIMESTAMP_UTC",
```

## Dowód odczytu lokalnego

Przed upływem 300 s, podając ten sam punkt:

```bash
.venv/bin/python tools/world_storage_pilot.py --lat LAT --lon LON
```

Oczekiwany świeży wynik lokalny i 0 HTTP. Następnie kontrolowane usunięcie
**tylko jednego wpisu zwykłego cache** (bez zmian świata i księgi):

```bash
.venv/bin/python tools/world_storage_pilot.py --lat LAT --lon LON --evict-cache --apply
```

Narzędzie odmawia bez poprawnego świeżego wyniku świata, przy zmianie revision
i gdy dla tego klucza trwa skan. Ponowić skan tym samym kontem bez poruszania się.
W logu wymagane `poi_maplark_cache source=world`, poprawne markery i brak nowego
naliczenia za ten skan. Sam obraz mapy nie dowodzi braku HTTP.
Po restarcie sprawdzić ponownie w oknie świeżości. Inne konta pozostają na cache/API.

## Stop, rollback i sprzątanie

Natychmiast wyłączyć ingest/read w ecosystemie, jeśli zmieniają się markery,
naliczenia dublują się lub pojawiają się błędy SQLite. Proponowany próg czasu
do odbioru pilota: zatrzymać przy dodatkowych ponad 2 s względem zwykłego skanu
w trzech kolejnych pomiarach tego samego punktu. To manualny próg stop pilota,
nie automatyczny limit ani SLO gameplayu; mała próbka nie daje rzetelnego p95.

Rollback: obie flagi 0, user/center puste, until 0, startOrReload tylko chaos.
Zwykły skaner i księga pozostają. Nie przywracać starej bazy ponad nowe naliczenia.
Po 30 minutach od ostatniego ingest, przy niezmienionej revision providera:

```bash
.venv/bin/python tools/world_storage_pilot.py --lat LAT --lon LON --prune-expired --apply
```

Usuwa maksymalnie 100 wygasłych snapshotów tego query key, wraz z membership
i coverage przez FK. Nie usuwa innych punktów, cache ani kredytów. Przy większej
liczbie powtarzać do zera; zmiana revision wymaga osobnego wskazania starego klucza,
nie globalnego kasowania bazy. Snapshoty w backupie znikają według retencji backupu.
Po odebraniu zwykłego skanu i panelu: `pm2 save`.

Przed ON pozostają: zgoda na opisany pilot i scope, login/punkt oraz stały koniec
okna ustawiony przy wdrożeniu. Brak tych wartości nie blokuje gry ani trybu passive.
