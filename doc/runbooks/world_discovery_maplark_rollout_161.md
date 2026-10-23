# MapLark — uruchomienie skanera dla wszystkich

Operator zatwierdził uruchomienie oraz limity 800 kredytów na dobę UTC i
24 000 w ruchomych 31 dniach. To budżet CHAOS, nie odczyt salda ani harmonogram
resetu planu MapLark. Konto pozostaje Free. Rezerwacja 20 na wywołanie nie
gwarantuje maksymalnej opłaty dostawcy; wyższe naliczenie blokuje dalsze pobrania.
Nieznane naliczenia pozostają rezerwacją również po zmianie dnia/okna.
Wcześniejsze operacje pilota zapisane w księdze są wliczane. Wcześniejszy
ręczny capture poza księgą ani inne użycie klucza nie są saldem tego licznika.

## Wdrożenie

```bash
cd ~/app/chaos &&
git pull --ff-only &&
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py'
```

Przed zmianą konfiguracji kopia aktualnej bazy POI (obejmuje naliczenia pilota):

```bash
umask 077
.venv/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
source = Path('data/poi_cache.sqlite3').resolve()
assert source.is_file()
destination = Path.home()/'chaos-backups'/('161-rollout-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
destination.mkdir(parents=True,exist_ok=False)
with sqlite3.connect(source) as src, sqlite3.connect(destination/'poi_cache.sqlite3') as dst:
    src.backup(dst)
    assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('Backup:', destination)
PY
```

Użyć rzeczywistego CHAOS_POI_CACHE_PATH, jeśli jest inny od powyższego.
Następnie przygotowanie powtarzalnych budżetów i decyzji registry — zero API:

```bash
.venv/bin/python tools/world_discovery_rollout.py promote --apply --daily 800 --rolling 24000
```

Oczekiwane `configured`, `provider_enabled: true`, `account_hold: null`,
okna `utc_day` (800) oraz `rolling_31_days` (24000). Jeśli występuje hold albo
nierozliczone operacje, nie usuwać ich; ustalić rzeczywiste naliczenia.
Ponowna komenda nie zeruje zużycia ani nie zmienia revision bez potrzeby.
Decyzja dostawcy ma jawny przegląd po 365 dniach; nie odnawia się samoczynnie.

Po poprawnym wyniku (klucz już jest w środowisku PM2 z działającego pilota):

```bash
CHAOS_POI_INFRASTRUCTURE_ENABLED=1 \
CHAOS_POI_MAPLARK_ENABLED=1 \
CHAOS_POI_MAPLARK_PILOT_ENABLED=0 \
CHAOS_MAPLARK_ACCEPT_VARIABLE_COST=1 \
CHAOS_MAPLARK_CREDIT_RESERVATION=20 \
pm2 restart chaos --update-env
```

Nie zmieniać flag Identity Gateway, wieku, globalnego registry Overpass,
world ingest, wide fetch i monitorów. Nowa flaga obejmuje wszystkie zalogowane
konta, nie tylko `robot`. Nie wywołujemy dodatkowego API probe.

Sprawdzić HTTP /launch po rozruchu i zwykły skan na koncie innym niż robot.
Po poprawnym odbiorze `pm2 save` utrwala konfigurację PM2. Utrzymywać pliki PM2
z dotychczasowymi restrykcyjnymi prawami — zawierają również istniejące sekrety.

## Diagnostyka i granice

### Trwała konfiguracja ecosystem

`ecosystem.web.config.js` zawiera pięć flag uruchomienia MapLark z powyższej
komendy. W lokalnym, nieśledzonym `ecosystem.config.js` serwera należy zachować
te same wartości w `env` procesu `chaos`. Przykład deweloperski pozostaje wyłączony.
Klucz API należy przechowywać w prywatnej konfiguracji serwera, poza Git.
Limity 800/24000 i historia zużycia pozostają w bazie POI, nie w zmiennych ENV.

Nie zastępować całego produkcyjnego ecosystem plikiem web z repo bez porównania
pozostałych ustawień: zawiera on także wcześniejsze ustawienia staging/development.
Przeniesienie pozostałych historycznych ENV wymaga porównania z konfiguracją VPS;
ten krok utrwala wyłącznie pięć flag wdrożenia MapLark. Po odbiorze działającego
wdrożenia wykonać `pm2 save`.

```bash
.venv/bin/python tools/world_discovery_rollout.py status --apply
pm2 logs chaos --lines 100 --nostream 2>&1 | grep 'poi_maplark'
```

`poi_maplark_cache` zawiera source, skrót key, revision, TTL, PID i czas.
Nie zawiera loginu, współrzędnych ani klucza API. Różny key oznacza różne
zapytanie/wersję. Centrum skanu pochodzi z kliknięcia mapy, nie pozycji postaci.
Nie wprowadzać zaokrąglania centrum tylko dla uzyskania cache hit — zmieniłoby
to zasięg zapytania. Fresh cache nadal działa po wyczerpaniu budżetu. Przy
chwilowym błędzie/budżecie można użyć exact stale cache do dotychczasowego
stale TTL (domyślnie 1800 s). Wynik jest oznaczony `stale`/`degraded`.
Nowy punkt bez cache wymaga budżetu i działającego API. Nie ma offline mapy POI.
Globalna aktywacja bez konfiguracji cyklicznego budżetu odrzuca nowe pobrania.

To profil MapLark, nie gwarancja identyczności selekcji Overpass. Dotychczasowe
ograniczenia geometrii i limitu odpowiedzi 1000 pozostają; niepełne odpowiedzi
nie stają się pustym skanem. Repozytorium przestrzenne i Geoapify nie są aktywowane.

## Wycofanie

```bash
CHAOS_POI_MAPLARK_ENABLED=0 CHAOS_POI_MAPLARK_PILOT_ENABLED=0 pm2 restart chaos --update-env
```

Wycofanie wraca do poprzedniego routingu, nie gwarantuje działania Overpass.
Nie odtwarzać starej księgi budżetu ani nie usuwać naliczeń. Natychmiastowe
odcięcie dostawcy także od cache: `tools/world_discovery_rollout.py disable --apply`.
