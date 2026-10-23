# Sprint 161 — kontrolowany pilot MapLark

Pakiet lokalny; przed poleceniami wymagane push i pobranie zatwierdzonego commitu.
Pilot nie oznacza globalnego uruchomienia. Geoapify pozostaje poza gameplayem.
Nie zmieniać flag wieku, Identity Gateway, world/wide/monitor ani registry rollout.

## Zakres do zatwierdzenia

Jedno konto testowe, 24 h. Budżet wewnętrzny 100 kredytów, rezerwacja 20 na
wywołanie. MapLark rozlicza zmienny koszt po odpowiedzi: 20 nie jest gwarantowanym
limitem ceny. Jeśli koszt go przekroczy, następne wywołania zostają wstrzymane;
rzeczywista pojedyncza opłata może przekroczyć rezerwację lub resztę budżetu.
Brak automatycznych powtórzeń. Naliczenia nieznane pozostają zarezerwowane.
Używać potwierdzonego konta Free. Budżet nie odczytuje salda panelu MapLark.

MapLark wybiera obiekty w promieniu. Ways/relations mają marker w środku
obwiedni źródłowej geometrii. Możliwe są różnice względem selekcji Overpass;
zachowane są ID, tagi, kategorie, limit 60 i dotychczasowe mechaniki CHAOS.
Odpowiedź ucięta na 1000 obiektów nie jest uznawana za pusty/poprawny skan.
Antymeridian, MultiLineString/GeometryCollection i nieprawidłowe geometrie
pozostają jawnie nieobsługiwane; nie uruchamiać globalnie przed odbiorem pilota.

## 1. Kod, testy i kopia bazy POI

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi_*.py'
umask 077
.venv/bin/python - <<'PY'
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
source = Path('data/poi_cache.sqlite3').resolve()
assert source.is_file(), 'Brak istniejącej bazy POI'
target = Path.home()/'chaos-backups'/('161-maplark-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
target.mkdir(parents=True, exist_ok=False)
with sqlite3.connect(source) as src, sqlite3.connect(target/'poi_cache.sqlite3') as dst:
    src.backup(dst)
    assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('Backup:', target)
PY
```

Jeśli proces używa innego CHAOS_POI_CACHE_PATH, użyć jego rzeczywistej ścieżki
w kopii i wszystkich poniższych poleceniach. Nie migrujemy game.sqlite3.

## 2. Przygotowanie i jedna próba

Po akceptacji powyższego zakresu:

```bash
.venv/bin/python tools/world_discovery_pilot.py prepare --apply
read -r -s -p 'MapLark API key: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
.venv/bin/python tools/world_discovery_pilot.py probe --apply --accept-variable-credit-cost
```

Oczekiwane `profile_probe_pass`, liczba obiektów oraz naliczenie. Probe nie
uruchamia gameplayu; w przypadku błędu zachować wynik, nie ponawiać w pętli.
`prepare` uruchamia 24-godzinne okno; nie powtarzać go w celu wyzerowania zużycia.

## 3. Aktywacja tylko wskazanego konta

W tej samej powłoce (klucz nadal w env), dopiero po udanej próbie:

```bash
.venv/bin/python tools/world_discovery_pilot.py enable --apply
read -r -p 'Dokładny login konta testowego CHAOS: ' CHAOS_POI_MAPLARK_PILOT_USERS
export CHAOS_POI_MAPLARK_PILOT_USERS
CHAOS_POI_INFRASTRUCTURE_ENABLED=1 \
CHAOS_POI_MAPLARK_PILOT_ENABLED=1 \
CHAOS_MAPLARK_ACCEPT_VARIABLE_COST=1 \
CHAOS_MAPLARK_CREDIT_RESERVATION=20 \
pm2 restart chaos --update-env
unset CHAOS_MAPLARK_API_KEY
```

Nie wklejać klucza w czacie/komendzie. Powyższe nie ustawia flagi globalnego
registry: pozostali gracze korzystają z dotychczasowej ścieżki. Odczyt cache
nie wymaga nowej rezerwacji. Po wygaśnięciu decyzji pilota także cache zostaje
wyłączony; rozszerzenie czasu lub rollout wymaga osobnej decyzji.

Sprawdzić HTTP /launch po rozruchu, następnie zwykły skan i GhostLab na koncie
testowym. Powtórzyć ten sam skan: status budżetu powinien pozostać bez zmian,
o ile działa świeży cache. Nie oznaczać samego HTTP 200 jako PASS LIVE SCANNER.

```bash
.venv/bin/python tools/world_discovery_pilot.py status --apply
```

## Wycofanie

```bash
.venv/bin/python tools/world_discovery_pilot.py disable --apply
CHAOS_POI_MAPLARK_PILOT_ENABLED=0 pm2 restart chaos --update-env
```

Nie usuwać księgi budżetu ani naliczeń. Wyłączenie flagi przywraca dla konta
dotychczasowy routing Overpass; nie gwarantuje dostępności publicznego API.
